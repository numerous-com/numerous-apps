"""
Environment variable based authentication provider.

This is a simple authentication provider that reads user credentials from
environment variables. Suitable for development and simple deployments.

Environment Variables:
    NUMEROUS_AUTH_USERS: JSON array of user objects, each with:
        - username (required): User's login name
        - password (required): User's password (plain text in env var)
        - email (optional): User's email
        - roles (optional): List of role names
        - is_admin (optional): Boolean for admin access

    NUMEROUS_JWT_SECRET: Secret key for signing JWTs (required in production)

Example:
    export NUMEROUS_AUTH_USERS='[
        {"username": "admin", "password": "admin123", "is_admin": true},
        {"username": "user", "password": "user123", "roles": ["viewer"]}
    ]'
    export NUMEROUS_JWT_SECRET='your-secret-key-here'

"""

import hashlib
import json
import logging
import os
import secrets
from typing import Any

from ..base import BaseAuthProvider
from ..models import AuthResult, User


logger = logging.getLogger(__name__)


class EnvAuthProvider(BaseAuthProvider):
    """
    Authentication provider using environment variables.

    This provider reads user credentials from the NUMEROUS_AUTH_USERS
    environment variable and provides simple username/password authentication.

    Features:
    - Simple setup via environment variables
    - In-memory refresh token storage
    - No external database required

    Limitations:
    - Not suitable for large user bases
    - User data is read-only at runtime
    - Refresh tokens are lost on server restart

    Example usage::

        from numerous.apps.auth import EnvAuthProvider
        from numerous.apps import create_app

        auth = EnvAuthProvider()
        app = create_app(template="index.html.j2", auth_provider=auth)
    """

    def __init__(
        self,
        users_env_var: str = "NUMEROUS_AUTH_USERS",
        secret_env_var: str = "NUMEROUS_JWT_SECRET",  # noqa: S107
        access_token_expire_minutes: int = 15,
        refresh_token_expire_days: int = 7,
    ) -> None:
        """
        Initialize the environment auth provider.

        Args:
            users_env_var: Environment variable name for users JSON
            secret_env_var: Environment variable name for JWT secret
            access_token_expire_minutes: Access token lifetime in minutes
            refresh_token_expire_days: Refresh token lifetime in days

        """
        # Load JWT secret from environment
        jwt_secret = os.getenv(secret_env_var)
        if not jwt_secret:
            # Generate a random secret for development (warn about it)
            jwt_secret = secrets.token_hex(32)
            logger.warning(
                f"No {secret_env_var} environment variable set. "
                "Using randomly generated secret. "
                "Set this variable for production use!"
            )

        super().__init__(
            jwt_secret=jwt_secret,
            access_token_expire_minutes=access_token_expire_minutes,
            refresh_token_expire_days=refresh_token_expire_days,
        )

        self.users_env_var = users_env_var
        self.secret_env_var = secret_env_var

        # Load users from environment
        self._users: dict[str, dict[str, Any]] = {}
        self._users_by_username: dict[str, str] = {}
        self._load_users()

        # In-memory refresh token storage: token_hash -> user_id
        self._refresh_tokens: dict[str, str] = {}

    def _load_users(self) -> None:
        """Load users from environment variable."""
        users_json = os.getenv(self.users_env_var, "[]")

        try:
            users_list = json.loads(users_json)
        except json.JSONDecodeError:
            logger.exception("Failed to parse %s", self.users_env_var)
            users_list = []

        if not isinstance(users_list, list):
            logger.error(f"{self.users_env_var} must be a JSON array")
            users_list = []

        for user_data in users_list:
            if not isinstance(user_data, dict):
                continue

            username = user_data.get("username")
            password = user_data.get("password")

            if not username or not password:
                logger.warning("Skipping user without username or password")
                continue

            # Generate a stable user ID from username
            user_id = hashlib.sha256(username.encode()).hexdigest()[:16]

            self._users[user_id] = {
                "id": user_id,
                "username": username,
                "password": password,  # Stored as-is (from env var)
                "email": user_data.get("email"),
                "roles": user_data.get("roles", []),
                "is_admin": user_data.get("is_admin", False),
                "is_active": user_data.get("is_active", True),
            }

            self._users_by_username[username] = user_id

        logger.info(f"Loaded {len(self._users)} users from {self.users_env_var}")

    def _hash_token(self, token: str) -> str:
        """Create a hash of a token for storage."""
        return hashlib.sha256(token.encode()).hexdigest()

    async def authenticate(self, username: str, password: str) -> AuthResult:
        """
        Authenticate a user with username and password.

        Args:
            username: The username to authenticate
            password: The password to verify

        Returns:
            AuthResult with success status and user info

        """
        user_id = self._users_by_username.get(username)
        if not user_id:
            logger.debug(f"Authentication failed: user '{username}' not found")
            return AuthResult.fail("Invalid username or password")

        user_data = self._users.get(user_id)
        if not user_data:
            return AuthResult.fail("Invalid username or password")

        # Check password (simple string comparison for env-based auth)
        if user_data["password"] != password:
            logger.debug(f"Authentication failed: wrong password for '{username}'")
            return AuthResult.fail("Invalid username or password")

        # Check if user is active
        if not user_data.get("is_active", True):
            logger.debug(f"Authentication failed: user '{username}' is inactive")
            return AuthResult.fail("User account is inactive")

        # Create User object
        user = User(
            id=user_data["id"],
            username=user_data["username"],
            email=user_data.get("email"),
            roles=user_data.get("roles", []),
            is_admin=user_data.get("is_admin", False),
            is_active=user_data.get("is_active", True),
        )

        logger.info(f"User '{username}' authenticated successfully")
        return AuthResult.ok(user)

    async def get_user(self, user_id: str) -> User | None:
        """
        Get a user by their ID.

        Args:
            user_id: The unique user identifier

        Returns:
            User object if found, None otherwise

        """
        user_data = self._users.get(user_id)
        if not user_data:
            return None

        return User(
            id=user_data["id"],
            username=user_data["username"],
            email=user_data.get("email"),
            roles=user_data.get("roles", []),
            is_admin=user_data.get("is_admin", False),
            is_active=user_data.get("is_active", True),
        )

    async def get_user_by_username(self, username: str) -> User | None:
        """
        Get a user by their username.

        Args:
            username: The username to look up

        Returns:
            User object if found, None otherwise

        """
        user_id = self._users_by_username.get(username)
        if not user_id:
            return None
        return await self.get_user(user_id)

    async def create_refresh_token(self, user: User) -> str:
        """
        Create a refresh token and store it.

        Args:
            user: The user to create a token for

        Returns:
            The refresh token string

        """
        token = await super().create_refresh_token(user)

        # Store token hash -> user_id mapping
        token_hash = self._hash_token(token)
        self._refresh_tokens[token_hash] = user.id

        return token

    async def refresh_access_token(self, refresh_token: str) -> tuple[str, int] | None:
        """
        Generate new access token from refresh token.

        Args:
            refresh_token: The refresh token to use

        Returns:
            Tuple of (new_access_token, expires_in_seconds) if valid

        """
        # First verify the token is in our storage
        token_hash = self._hash_token(refresh_token)
        user_id = self._refresh_tokens.get(token_hash)

        if not user_id:
            logger.debug("Refresh token not found in storage")
            return None

        # Then validate the JWT itself
        return await super().refresh_access_token(refresh_token)

    async def revoke_refresh_token(self, refresh_token: str) -> bool:
        """
        Revoke a refresh token.

        Args:
            refresh_token: The token to revoke

        Returns:
            True if revoked, False if not found

        """
        token_hash = self._hash_token(refresh_token)

        if token_hash in self._refresh_tokens:
            del self._refresh_tokens[token_hash]
            logger.debug("Refresh token revoked")
            return True

        return False

    def get_settings(self) -> dict[str, Any]:
        """Get provider settings (non-sensitive)."""
        settings = super().get_settings()
        settings.update(
            {
                "provider_type": "env",
                "users_count": len(self._users),
                "users_env_var": self.users_env_var,
            }
        )
        return settings

    def list_users(self) -> list[User]:
        """
        List all users (for admin interface).

        Returns:
            List of all configured users

        """
        return [
            User(
                id=data["id"],
                username=data["username"],
                email=data.get("email"),
                roles=data.get("roles", []),
                is_admin=data.get("is_admin", False),
                is_active=data.get("is_active", True),
            )
            for data in self._users.values()
        ]
