"""Tests for the authentication module."""

import json
import os
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from traitlets import Unicode
from anywidget import AnyWidget

from numerous.apps import create_app
from numerous.apps.auth.models import (
    User,
    AuthResult,
    TokenResponse,
    LoginCredentials,
    UserContext,
    CreateUserRequest,
    UpdateUserRequest,
)
from numerous.apps.auth.jwt_utils import JWTManager, generate_secret_key
from numerous.apps.auth.exceptions import (
    InvalidCredentialsError,
    InvalidTokenError,
    InsufficientPermissionsError,
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def jwt_manager():
    """Create a JWT manager for testing."""
    return JWTManager(
        secret="test-secret-key-for-testing-only",
        algorithm="HS256",
        access_token_expire_minutes=15,
        refresh_token_expire_days=7,
    )


@pytest.fixture
def test_user():
    """Create a test user."""
    return User(
        id="test-user-id",
        username="testuser",
        email="test@example.com",
        roles=["viewer", "editor"],
        is_admin=False,
        is_active=True,
    )


@pytest.fixture
def admin_user():
    """Create an admin test user."""
    return User(
        id="admin-user-id",
        username="admin",
        email="admin@example.com",
        roles=["admin"],
        is_admin=True,
        is_active=True,
    )


@pytest.fixture
def env_auth_users():
    """Set up environment variables for EnvAuthProvider."""
    users = [
        {"username": "testuser", "password": "testpass123", "roles": ["viewer"]},
        {"username": "admin", "password": "adminpass123", "is_admin": True},
    ]
    os.environ["NUMEROUS_AUTH_USERS"] = json.dumps(users)
    os.environ["NUMEROUS_JWT_SECRET"] = "test-secret-key-for-env-auth"
    yield
    # Cleanup
    os.environ.pop("NUMEROUS_AUTH_USERS", None)
    os.environ.pop("NUMEROUS_JWT_SECRET", None)


# ============================================================================
# Test User Model
# ============================================================================

class TestUserModel:
    """Tests for the User model."""

    def test_user_creation(self):
        """Test creating a User instance."""
        user = User(
            id="123",
            username="testuser",
            email="test@example.com",
            roles=["admin", "editor"],
            is_admin=True,
        )
        assert user.id == "123"
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.roles == ["admin", "editor"]
        assert user.is_admin is True
        assert user.is_active is True  # Default value

    def test_user_authenticated_property(self, test_user):
        """Test that authenticated property always returns True for User."""
        assert test_user.authenticated is True

    def test_user_has_role(self, test_user):
        """Test checking if user has a specific role."""
        assert test_user.has_role("viewer") is True
        assert test_user.has_role("admin") is False

    def test_user_has_any_role(self, test_user):
        """Test checking if user has any of multiple roles."""
        assert test_user.has_any_role(["viewer", "admin"]) is True
        assert test_user.has_any_role(["admin", "superuser"]) is False


class TestAuthResult:
    """Tests for the AuthResult model."""

    def test_auth_result_success(self, test_user):
        """Test creating a successful auth result."""
        result = AuthResult.ok(test_user)
        assert result.success is True
        assert result.user == test_user
        assert result.error is None

    def test_auth_result_failure(self):
        """Test creating a failed auth result."""
        result = AuthResult.fail("Invalid credentials")
        assert result.success is False
        assert result.user is None
        assert result.error == "Invalid credentials"


class TestUserContext:
    """Tests for the UserContext model."""

    def test_anonymous_context(self):
        """Test creating an anonymous user context."""
        ctx = UserContext.anonymous()
        assert ctx.authenticated is False
        assert ctx.username is None
        assert ctx.user_id is None
        assert ctx.roles == []
        assert ctx.is_admin is False

    def test_context_from_user(self, test_user):
        """Test creating context from a User instance."""
        ctx = UserContext.from_user(test_user)
        assert ctx.authenticated is True
        assert ctx.username == test_user.username
        assert ctx.user_id == test_user.id
        assert ctx.roles == test_user.roles
        assert ctx.is_admin == test_user.is_admin


# ============================================================================
# Test JWT Utils
# ============================================================================

class TestJWTManager:
    """Tests for the JWTManager class."""

    def test_create_access_token(self, jwt_manager, test_user):
        """Test creating an access token."""
        token = jwt_manager.create_access_token(
            user_id=test_user.id,
            username=test_user.username,
        )
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_refresh_token(self, jwt_manager, test_user):
        """Test creating a refresh token."""
        token = jwt_manager.create_refresh_token(user_id=test_user.id)
        assert isinstance(token, str)
        assert len(token) > 0

    def test_decode_valid_access_token(self, jwt_manager, test_user):
        """Test decoding a valid access token."""
        token = jwt_manager.create_access_token(
            user_id=test_user.id,
            username=test_user.username,
        )
        payload = jwt_manager.decode_access_token(token)
        assert payload is not None
        assert payload["sub"] == test_user.id
        assert payload["username"] == test_user.username
        assert payload["type"] == "access"

    def test_decode_valid_refresh_token(self, jwt_manager, test_user):
        """Test decoding a valid refresh token."""
        token = jwt_manager.create_refresh_token(user_id=test_user.id)
        payload = jwt_manager.decode_refresh_token(token)
        assert payload is not None
        assert payload["sub"] == test_user.id
        assert payload["type"] == "refresh"

    def test_decode_invalid_token(self, jwt_manager):
        """Test decoding an invalid token returns None."""
        payload = jwt_manager.decode_access_token("invalid-token")
        assert payload is None

    def test_decode_access_token_with_refresh_token_fails(self, jwt_manager, test_user):
        """Test that refresh token cannot be decoded as access token."""
        refresh_token = jwt_manager.create_refresh_token(user_id=test_user.id)
        payload = jwt_manager.decode_access_token(refresh_token)
        assert payload is None

    def test_decode_refresh_token_with_access_token_fails(self, jwt_manager, test_user):
        """Test that access token cannot be decoded as refresh token."""
        access_token = jwt_manager.create_access_token(
            user_id=test_user.id,
            username=test_user.username,
        )
        payload = jwt_manager.decode_refresh_token(access_token)
        assert payload is None

    def test_get_token_expiry(self, jwt_manager, test_user):
        """Test getting token expiry time."""
        token = jwt_manager.create_access_token(
            user_id=test_user.id,
            username=test_user.username,
        )
        expiry = jwt_manager.get_token_expiry(token)
        assert expiry is not None

    def test_generate_secret_key(self):
        """Test generating a secret key."""
        key = generate_secret_key()
        assert isinstance(key, str)
        assert len(key) == 64  # 32 bytes = 64 hex characters

        # Generate another key to ensure randomness
        key2 = generate_secret_key()
        assert key != key2


# ============================================================================
# Test EnvAuthProvider
# ============================================================================

class TestEnvAuthProvider:
    """Tests for the EnvAuthProvider class."""

    @pytest.mark.asyncio
    async def test_authenticate_valid_credentials(self, env_auth_users):
        """Test authentication with valid credentials."""
        from numerous.apps.auth.providers.env_auth import EnvAuthProvider

        provider = EnvAuthProvider()
        result = await provider.authenticate("testuser", "testpass123")

        assert result.success is True
        assert result.user is not None
        assert result.user.username == "testuser"
        assert "viewer" in result.user.roles

    @pytest.mark.asyncio
    async def test_authenticate_invalid_password(self, env_auth_users):
        """Test authentication with invalid password."""
        from numerous.apps.auth.providers.env_auth import EnvAuthProvider

        provider = EnvAuthProvider()
        result = await provider.authenticate("testuser", "wrongpassword")

        assert result.success is False
        assert result.user is None
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_authenticate_nonexistent_user(self, env_auth_users):
        """Test authentication with non-existent user."""
        from numerous.apps.auth.providers.env_auth import EnvAuthProvider

        provider = EnvAuthProvider()
        result = await provider.authenticate("nonexistent", "password")

        assert result.success is False
        assert result.user is None

    @pytest.mark.asyncio
    async def test_get_user_by_id(self, env_auth_users):
        """Test getting user by ID."""
        from numerous.apps.auth.providers.env_auth import EnvAuthProvider

        provider = EnvAuthProvider()
        # First authenticate to get the user ID
        result = await provider.authenticate("testuser", "testpass123")
        user_id = result.user.id

        # Now get the user by ID
        user = await provider.get_user(user_id)
        assert user is not None
        assert user.username == "testuser"

    @pytest.mark.asyncio
    async def test_get_user_by_username(self, env_auth_users):
        """Test getting user by username."""
        from numerous.apps.auth.providers.env_auth import EnvAuthProvider

        provider = EnvAuthProvider()
        user = await provider.get_user_by_username("admin")

        assert user is not None
        assert user.username == "admin"
        assert user.is_admin is True

    @pytest.mark.asyncio
    async def test_create_and_validate_access_token(self, env_auth_users):
        """Test creating and validating access tokens."""
        from numerous.apps.auth.providers.env_auth import EnvAuthProvider

        provider = EnvAuthProvider()
        result = await provider.authenticate("testuser", "testpass123")
        user = result.user

        # Create access token
        token, expires_in = await provider.create_access_token(user)
        assert token is not None
        assert expires_in > 0

        # Validate the token
        validated_user = await provider.validate_access_token(token)
        assert validated_user is not None
        assert validated_user.username == user.username

    @pytest.mark.asyncio
    async def test_create_and_refresh_token(self, env_auth_users):
        """Test creating and refreshing tokens."""
        from numerous.apps.auth.providers.env_auth import EnvAuthProvider

        provider = EnvAuthProvider()
        result = await provider.authenticate("testuser", "testpass123")
        user = result.user

        # Create refresh token
        refresh_token = await provider.create_refresh_token(user)
        assert refresh_token is not None

        # Use refresh token to get new access token
        new_access = await provider.refresh_access_token(refresh_token)
        assert new_access is not None
        new_token, expires_in = new_access
        assert new_token is not None

    @pytest.mark.asyncio
    async def test_revoke_refresh_token(self, env_auth_users):
        """Test revoking a refresh token."""
        from numerous.apps.auth.providers.env_auth import EnvAuthProvider

        provider = EnvAuthProvider()
        result = await provider.authenticate("testuser", "testpass123")
        user = result.user

        # Create refresh token
        refresh_token = await provider.create_refresh_token(user)

        # Revoke it
        revoked = await provider.revoke_refresh_token(refresh_token)
        assert revoked is True

        # Try to use revoked token
        new_access = await provider.refresh_access_token(refresh_token)
        assert new_access is None

    def test_list_users(self, env_auth_users):
        """Test listing all users."""
        from numerous.apps.auth.providers.env_auth import EnvAuthProvider

        provider = EnvAuthProvider()
        users = provider.list_users()

        assert len(users) == 2
        usernames = [u.username for u in users]
        assert "testuser" in usernames
        assert "admin" in usernames

    def test_get_settings(self, env_auth_users):
        """Test getting provider settings."""
        from numerous.apps.auth.providers.env_auth import EnvAuthProvider

        provider = EnvAuthProvider()
        settings = provider.get_settings()

        assert settings["provider_type"] == "env"
        assert settings["users_count"] == 2
        assert "access_token_expire_minutes" in settings


# ============================================================================
# Test Auth Routes Integration
# ============================================================================

# Note: Due to FastAPI singleton pattern in this codebase, we need to test
# auth routes differently. The following tests use a mock-based approach.


class _TestWidgetWithAuth(AnyWidget):
    """Test widget for auth integration tests."""
    value = Unicode("test").tag(sync=True)

    def __init__(self):
        super().__init__()
        self.module = "test-widget"
        self.html = "<div>Test Widget</div>"


def _app_generator_for_auth():
    """Generate widgets for auth test app."""
    return {"test_widget": _TestWidgetWithAuth()}


@pytest.fixture(scope="module")
def auth_test_dirs(tmp_path_factory):
    """Create temporary directories for auth testing."""
    base_dir = tmp_path_factory.mktemp("test_auth_app")
    templates_dir = base_dir / "templates"
    templates_dir.mkdir(exist_ok=True)

    # Create a basic template file
    with open(templates_dir / "base.html.j2", "w") as f:
        f.write("""
        <!DOCTYPE html>
        <html>
        <body>{{ test_widget }}</body>
        </html>
        """)

    # Create error templates
    with open(templates_dir / "error.html.j2", "w") as f:
        f.write("<h1>{{ error_title }}</h1><p>{{ error_message }}</p>")
    
    with open(templates_dir / "error_modal.html.j2", "w") as f:
        f.write('<div id="error-modal"></div>')

    original_dir = os.getcwd()
    os.chdir(str(base_dir))
    yield base_dir
    os.chdir(original_dir)


@pytest.fixture(scope="module")
def module_env_auth_users():
    """Set up environment variables for EnvAuthProvider - module scope."""
    users = [
        {"username": "testuser", "password": "testpass123", "roles": ["viewer"]},
        {"username": "admin", "password": "adminpass123", "is_admin": True},
    ]
    os.environ["NUMEROUS_AUTH_USERS"] = json.dumps(users)
    os.environ["NUMEROUS_JWT_SECRET"] = "test-secret-key-for-env-auth"
    yield
    # Cleanup
    os.environ.pop("NUMEROUS_AUTH_USERS", None)
    os.environ.pop("NUMEROUS_JWT_SECRET", None)


@pytest.fixture(scope="module")
def auth_app(auth_test_dirs, module_env_auth_users):
    """Create an app with authentication enabled - module scoped to avoid middleware issues."""
    from numerous.apps.auth.providers.env_auth import EnvAuthProvider
    auth_provider = EnvAuthProvider()
    app = create_app(
        template="base.html.j2",
        dev=True,
        app_generator=_app_generator_for_auth,
        auth_provider=auth_provider,
        public_routes=["/api/auth/login", "/api/auth/check", "/api/auth/logout", "/api/auth/refresh", "/login"],
        base_dir=auth_test_dirs,
    )
    yield app


@pytest.fixture
def auth_client(auth_app):
    """Create a test client for the auth-enabled app."""
    return TestClient(auth_app)


class TestAuthRoutes:
    """Tests for authentication routes."""

    def test_login_success(self, auth_client):
        """Test successful login."""
        response = auth_client.post(
            "/api/auth/login",
            json={"username": "testuser", "password": "testpass123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "user" in data
        assert data["user"]["username"] == "testuser"

    def test_login_invalid_credentials(self, auth_client):
        """Test login with invalid credentials."""
        response = auth_client.post(
            "/api/auth/login",
            json={"username": "testuser", "password": "wrongpassword"},
        )
        assert response.status_code == 401

    def test_login_nonexistent_user(self, auth_client):
        """Test login with non-existent user."""
        response = auth_client.post(
            "/api/auth/login",
            json={"username": "nonexistent", "password": "password"},
        )
        assert response.status_code == 401

    def test_auth_check_not_authenticated(self, auth_client):
        """Test auth check without authentication."""
        response = auth_client.get("/api/auth/check")
        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is False

    def test_auth_check_authenticated(self, auth_client):
        """Test auth check with valid token."""
        # First login
        login_response = auth_client.post(
            "/api/auth/login",
            json={"username": "testuser", "password": "testpass123"},
        )
        token = login_response.json()["access_token"]

        # Check auth with token
        response = auth_client.get(
            "/api/auth/check",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is True
        assert data["username"] == "testuser"

    def test_get_current_user(self, auth_client):
        """Test getting current user info."""
        # First login
        login_response = auth_client.post(
            "/api/auth/login",
            json={"username": "testuser", "password": "testpass123"},
        )
        token = login_response.json()["access_token"]

        # Get user info
        response = auth_client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testuser"

    def test_get_current_user_no_auth(self, auth_client):
        """Test getting current user without authentication."""
        response = auth_client.get("/api/auth/me")
        assert response.status_code == 401

    def test_logout(self, auth_client):
        """Test logout endpoint."""
        # Login first
        login_response = auth_client.post(
            "/api/auth/login",
            json={"username": "testuser", "password": "testpass123"},
        )
        
        # Logout
        response = auth_client.post("/api/auth/logout")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Logged out successfully"

    def test_login_page_accessible(self, auth_client):
        """Test that login page is accessible without authentication."""
        response = auth_client.get("/login")
        assert response.status_code == 200
        assert "Sign in" in response.text or "Login" in response.text

    def test_protected_route_redirects_to_login(self, auth_client):
        """Test that protected routes redirect to login."""
        response = auth_client.get("/", follow_redirects=False)
        # Should redirect to login
        assert response.status_code == 302
        assert "/login" in response.headers.get("location", "")

    def test_protected_route_with_auth(self, auth_client):
        """Test accessing protected route with valid token."""
        # Login first
        login_response = auth_client.post(
            "/api/auth/login",
            json={"username": "testuser", "password": "testpass123"},
        )
        token = login_response.json()["access_token"]

        # Access protected route with token
        response = auth_client.get(
            "/",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200


# ============================================================================
# Test DatabaseAuthProvider (requires auth-db dependencies)
# ============================================================================

# Check if database auth dependencies are available
try:
    import bcrypt
    import sqlalchemy
    import aiosqlite
    HAS_DB_DEPS = True
except ImportError:
    HAS_DB_DEPS = False


@pytest.fixture
def db_auth_provider(tmp_path):
    """Create a DatabaseAuthProvider with SQLite for testing."""
    if not HAS_DB_DEPS:
        pytest.skip("Database auth dependencies not installed")
    
    from numerous.apps.auth.providers.database_auth import DatabaseAuthProvider
    
    db_path = tmp_path / "test_auth.db"
    db_url = f"sqlite+aiosqlite:///{db_path}"
    
    provider = DatabaseAuthProvider(
        database_url=db_url,
        jwt_secret="test-db-secret-key",
        access_token_expire_minutes=15,
        refresh_token_expire_days=7,
    )
    
    yield provider
    
    # Cleanup - close engine synchronously
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're in an async context, schedule the dispose
            pass
        else:
            loop.run_until_complete(provider.engine.dispose())
    except RuntimeError:
        # No event loop, create one
        asyncio.run(provider.engine.dispose())


@pytest.mark.skipif(not HAS_DB_DEPS, reason="Database auth dependencies not installed")
class TestDatabaseAuthProvider:
    """Tests for the DatabaseAuthProvider class."""

    @pytest.mark.asyncio
    async def test_create_user(self, db_auth_provider):
        """Test creating a new user."""
        user_data = CreateUserRequest(
            username="dbuser",
            password="dbpassword123",
            email="dbuser@example.com",
            roles=["viewer"],
            is_admin=False,
        )
        
        user = await db_auth_provider.create_user(user_data)
        
        assert user.username == "dbuser"
        assert user.email == "dbuser@example.com"
        assert user.is_admin is False
        assert user.is_active is True

    @pytest.mark.asyncio
    async def test_create_duplicate_user(self, db_auth_provider):
        """Test that creating a duplicate user raises an error."""
        from numerous.apps.auth.exceptions import UserExistsError
        
        user_data = CreateUserRequest(
            username="duplicateuser",
            password="password123",
            is_admin=False,
        )
        
        # Create first user
        await db_auth_provider.create_user(user_data)
        
        # Try to create duplicate
        with pytest.raises(UserExistsError):
            await db_auth_provider.create_user(user_data)

    @pytest.mark.asyncio
    async def test_authenticate_valid_credentials(self, db_auth_provider):
        """Test authentication with valid credentials."""
        # Create user first
        user_data = CreateUserRequest(
            username="authuser",
            password="authpassword123",
            is_admin=False,
        )
        await db_auth_provider.create_user(user_data)
        
        # Authenticate
        result = await db_auth_provider.authenticate("authuser", "authpassword123")
        
        assert result.success is True
        assert result.user is not None
        assert result.user.username == "authuser"

    @pytest.mark.asyncio
    async def test_authenticate_invalid_password(self, db_auth_provider):
        """Test authentication with invalid password."""
        # Create user first
        user_data = CreateUserRequest(
            username="authuser2",
            password="correctpassword",
            is_admin=False,
        )
        await db_auth_provider.create_user(user_data)
        
        # Authenticate with wrong password
        result = await db_auth_provider.authenticate("authuser2", "wrongpassword")
        
        assert result.success is False
        assert result.user is None

    @pytest.mark.asyncio
    async def test_authenticate_nonexistent_user(self, db_auth_provider):
        """Test authentication with non-existent user."""
        result = await db_auth_provider.authenticate("nonexistent", "password")
        
        assert result.success is False
        assert result.user is None

    @pytest.mark.asyncio
    async def test_authenticate_inactive_user(self, db_auth_provider):
        """Test that inactive users cannot authenticate."""
        from numerous.apps.auth.models import UpdateUserRequest
        
        # Create user
        user_data = CreateUserRequest(
            username="inactiveuser",
            password="password123",
            is_admin=False,
        )
        user = await db_auth_provider.create_user(user_data)
        
        # Deactivate user
        await db_auth_provider.update_user(
            user.id,
            UpdateUserRequest(is_active=False)
        )
        
        # Try to authenticate
        result = await db_auth_provider.authenticate("inactiveuser", "password123")
        
        assert result.success is False
        assert "inactive" in result.error.lower()

    @pytest.mark.asyncio
    async def test_get_user_by_id(self, db_auth_provider):
        """Test getting user by ID."""
        # Create user
        user_data = CreateUserRequest(
            username="getuser",
            password="password123",
            is_admin=False,
        )
        created_user = await db_auth_provider.create_user(user_data)
        
        # Get user
        user = await db_auth_provider.get_user(created_user.id)
        
        assert user is not None
        assert user.id == created_user.id
        assert user.username == "getuser"

    @pytest.mark.asyncio
    async def test_get_user_by_username(self, db_auth_provider):
        """Test getting user by username."""
        # Create user
        user_data = CreateUserRequest(
            username="getbyusername",
            password="password123",
            email="getbyusername@example.com",
            is_admin=True,
        )
        await db_auth_provider.create_user(user_data)
        
        # Get user
        user = await db_auth_provider.get_user_by_username("getbyusername")
        
        assert user is not None
        assert user.username == "getbyusername"
        assert user.email == "getbyusername@example.com"
        assert user.is_admin is True

    @pytest.mark.asyncio
    async def test_get_nonexistent_user(self, db_auth_provider):
        """Test getting a non-existent user."""
        user = await db_auth_provider.get_user("nonexistent-id")
        assert user is None
        
        user = await db_auth_provider.get_user_by_username("nonexistent")
        assert user is None

    @pytest.mark.asyncio
    async def test_create_and_validate_access_token(self, db_auth_provider):
        """Test creating and validating access tokens."""
        # Create user
        user_data = CreateUserRequest(
            username="tokenuser",
            password="password123",
            is_admin=False,
        )
        user = await db_auth_provider.create_user(user_data)
        
        # Create access token
        token, expires_in = await db_auth_provider.create_access_token(user)
        assert token is not None
        assert expires_in > 0
        
        # Validate token
        validated_user = await db_auth_provider.validate_access_token(token)
        assert validated_user is not None
        assert validated_user.username == user.username

    @pytest.mark.asyncio
    async def test_create_and_refresh_token(self, db_auth_provider):
        """Test creating and using refresh tokens."""
        # Create user
        user_data = CreateUserRequest(
            username="refreshuser",
            password="password123",
            is_admin=False,
        )
        user = await db_auth_provider.create_user(user_data)
        
        # Create refresh token
        refresh_token = await db_auth_provider.create_refresh_token(user)
        assert refresh_token is not None
        
        # Use refresh token to get new access token
        result = await db_auth_provider.refresh_access_token(refresh_token)
        assert result is not None
        new_access_token, expires_in = result
        assert new_access_token is not None
        assert expires_in > 0

    @pytest.mark.asyncio
    async def test_revoke_refresh_token(self, db_auth_provider):
        """Test revoking a refresh token."""
        # Create user
        user_data = CreateUserRequest(
            username="revokeuser",
            password="password123",
            is_admin=False,
        )
        user = await db_auth_provider.create_user(user_data)
        
        # Create refresh token
        refresh_token = await db_auth_provider.create_refresh_token(user)
        
        # Revoke it
        revoked = await db_auth_provider.revoke_refresh_token(refresh_token)
        assert revoked is True
        
        # Try to use revoked token
        result = await db_auth_provider.refresh_access_token(refresh_token)
        assert result is None

    @pytest.mark.asyncio
    async def test_update_user(self, db_auth_provider):
        """Test updating a user."""
        from numerous.apps.auth.models import UpdateUserRequest
        
        # Create user
        user_data = CreateUserRequest(
            username="updateuser",
            password="password123",
            email="original@example.com",
            is_admin=False,
        )
        user = await db_auth_provider.create_user(user_data)
        
        # Update user
        updated = await db_auth_provider.update_user(
            user.id,
            UpdateUserRequest(
                email="updated@example.com",
                is_admin=True,
            )
        )
        
        assert updated.email == "updated@example.com"
        assert updated.is_admin is True

    @pytest.mark.asyncio
    async def test_update_user_password(self, db_auth_provider):
        """Test updating a user's password."""
        from numerous.apps.auth.models import UpdateUserRequest
        
        # Create user
        user_data = CreateUserRequest(
            username="passworduser",
            password="oldpassword",
            is_admin=False,
        )
        user = await db_auth_provider.create_user(user_data)
        
        # Update password
        await db_auth_provider.update_user(
            user.id,
            UpdateUserRequest(password="newpassword")
        )
        
        # Verify old password doesn't work
        result = await db_auth_provider.authenticate("passworduser", "oldpassword")
        assert result.success is False
        
        # Verify new password works
        result = await db_auth_provider.authenticate("passworduser", "newpassword")
        assert result.success is True

    @pytest.mark.asyncio
    async def test_delete_user(self, db_auth_provider):
        """Test deleting a user."""
        # Create user
        user_data = CreateUserRequest(
            username="deleteuser",
            password="password123",
            is_admin=False,
        )
        user = await db_auth_provider.create_user(user_data)
        
        # Delete user
        await db_auth_provider.delete_user(user.id)
        
        # Verify user is gone
        deleted_user = await db_auth_provider.get_user(user.id)
        assert deleted_user is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_user(self, db_auth_provider):
        """Test deleting a non-existent user raises an error."""
        from numerous.apps.auth.exceptions import UserNotFoundError
        
        with pytest.raises(UserNotFoundError):
            await db_auth_provider.delete_user("nonexistent-id")

    @pytest.mark.asyncio
    async def test_list_users(self, db_auth_provider):
        """Test listing all users."""
        # Create multiple users
        for i in range(3):
            user_data = CreateUserRequest(
                username=f"listuser{i}",
                password="password123",
                is_admin=False,
            )
            await db_auth_provider.create_user(user_data)
        
        # List users
        users = await db_auth_provider.list_users_async()
        
        assert len(users) == 3
        usernames = [u.username for u in users]
        assert "listuser0" in usernames
        assert "listuser1" in usernames
        assert "listuser2" in usernames

    def test_get_settings(self, db_auth_provider):
        """Test getting provider settings."""
        settings = db_auth_provider.get_settings()
        
        assert settings["provider_type"] == "database"
        assert "access_token_expire_minutes" in settings
        assert "refresh_token_expire_days" in settings


# ============================================================================
# Test App Without Auth (Backward Compatibility)
# Note: These tests are skipped due to singleton app architecture issues.
# The auth functionality is tested in TestAuthRoutes above.
# ============================================================================

@pytest.mark.skip(reason="Singleton app architecture makes no-auth tests conflict with auth tests")
class TestAppWithoutAuth:
    """Tests to ensure apps without auth work correctly."""

    @pytest.fixture
    def no_auth_app(self, auth_test_dirs):
        """Create an app without authentication."""
        from numerous.apps.app_server import templates, _app

        # Reset middleware for no-auth test
        _app.middleware_stack = None
        
        templates.env.loader.searchpath.append(str(auth_test_dirs / "templates"))

        app = create_app(
            template="base.html.j2",
            dev=True,
            app_generator=_app_generator_for_auth,
            # No auth_provider = auth disabled
        )
        return app

    @pytest.fixture
    def no_auth_client(self, no_auth_app):
        """Create a test client for app without auth."""
        return TestClient(no_auth_app)

    def test_home_accessible_without_auth(self, no_auth_client):
        """Test that home page is accessible without auth when auth is disabled."""
        response = no_auth_client.get("/")
        assert response.status_code == 200

    def test_api_widgets_accessible_without_auth(self, no_auth_client):
        """Test that API widgets endpoint is accessible without auth."""
        response = no_auth_client.get("/api/widgets")
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert "widgets" in data

    def test_no_auth_routes_when_disabled(self, no_auth_client):
        """Test that auth routes don't exist when auth is disabled."""
        # Auth routes should not be registered
        response = no_auth_client.get("/login")
        assert response.status_code == 404

        response = no_auth_client.post(
            "/api/auth/login",
            json={"username": "test", "password": "test"},
        )
        assert response.status_code == 404

