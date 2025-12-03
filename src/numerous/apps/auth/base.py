"""Authentication provider protocol and base classes."""

from typing import Any, Protocol, runtime_checkable

from .models import AuthResult, User


@runtime_checkable
class AuthProvider(Protocol):
    """
    Protocol defining the interface for authentication providers.

    Implement this protocol to create custom authentication backends.
    The framework provides two built-in implementations:

    - EnvAuthProvider: Simple environment variable based auth
    - DatabaseAuthProvider: Full-featured database backed auth

    Example custom implementation::

        class LDAPAuthProvider:
            def __init__(self, ldap_url: str):
                self.ldap_url = ldap_url

            async def authenticate(self, username: str, password: str) -> AuthResult:
                # Custom LDAP authentication logic
                ...

            # Implement other methods...
    """

    async def authenticate(self, username: str, password: str) -> AuthResult:
        """
        Authenticate a user with username and password.

        Args:
            username: The username to authenticate
            password: The password to verify

        Returns:
            AuthResult with success=True and user if valid,
            or success=False and error message if invalid.

        """
        ...

    async def get_user(self, user_id: str) -> User | None:
        """
        Retrieve a user by their unique ID.

        Args:
            user_id: The unique identifier of the user

        Returns:
            User object if found, None otherwise.

        """
        ...

    async def get_user_by_username(self, username: str) -> User | None:
        """
        Retrieve a user by their username.

        Args:
            username: The username to look up

        Returns:
            User object if found, None otherwise.

        """
        ...

    async def create_access_token(self, user: User) -> tuple[str, int]:
        """
        Create an access token for a user.

        Args:
            user: The user to create a token for

        Returns:
            Tuple of (token_string, expires_in_seconds)

        """
        ...

    async def create_refresh_token(self, user: User) -> str:
        """
        Create a refresh token for a user.

        Args:
            user: The user to create a refresh token for

        Returns:
            The refresh token string

        """
        ...

    async def validate_access_token(self, token: str) -> User | None:
        """
        Validate an access token and return the associated user.

        Args:
            token: The access token to validate

        Returns:
            User object if token is valid, None otherwise.

        """
        ...

    async def refresh_access_token(self, refresh_token: str) -> tuple[str, int] | None:
        """
        Generate a new access token using a refresh token.

        Args:
            refresh_token: The refresh token to use

        Returns:
            Tuple of (new_access_token, expires_in_seconds) if valid,
            None if the refresh token is invalid or expired.

        """
        ...

    async def revoke_refresh_token(self, refresh_token: str) -> bool:
        """
        Revoke a refresh token (used for logout).

        Args:
            refresh_token: The refresh token to revoke

        Returns:
            True if successfully revoked, False otherwise.

        """
        ...

    def get_settings(self) -> dict[str, Any]:
        """
        Get provider settings (for configuration display).

        Returns:
            Dictionary of non-sensitive configuration settings.

        """
        ...


class BaseAuthProvider:
    """
    Base class with common functionality for auth providers.

    Provides default implementations for token creation and validation
    using JWT. Subclasses must implement user storage methods.
    """

    def __init__(
        self,
        jwt_secret: str,
        access_token_expire_minutes: int = 15,
        refresh_token_expire_days: int = 7,
        algorithm: str = "HS256",
    ) -> None:
        """
        Initialize the base auth provider.

        Args:
            jwt_secret: Secret key for signing JWTs
            access_token_expire_minutes: Access token lifetime in minutes
            refresh_token_expire_days: Refresh token lifetime in days
            algorithm: JWT signing algorithm

        """
        self.jwt_secret = jwt_secret
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days
        self.algorithm = algorithm

        # Import jwt utilities lazily
        from .jwt_utils import JWTManager

        self._jwt = JWTManager(
            secret=jwt_secret,
            algorithm=algorithm,
            access_token_expire_minutes=access_token_expire_minutes,
            refresh_token_expire_days=refresh_token_expire_days,
        )

    async def create_access_token(self, user: User) -> tuple[str, int]:
        """Create an access token for a user."""
        token = self._jwt.create_access_token(user_id=user.id, username=user.username)
        return token, self.access_token_expire_minutes * 60

    async def create_refresh_token(self, user: User) -> str:
        """Create a refresh token for a user."""
        return self._jwt.create_refresh_token(user_id=user.id)

    async def validate_access_token(self, token: str) -> User | None:
        """Validate access token and return user."""
        payload = self._jwt.decode_access_token(token)
        if payload is None:
            return None

        user_id = payload.get("sub")
        if not user_id:
            return None

        return await self.get_user(user_id)

    async def refresh_access_token(self, refresh_token: str) -> tuple[str, int] | None:
        """Generate new access token from refresh token."""
        payload = self._jwt.decode_refresh_token(refresh_token)
        if payload is None:
            return None

        user_id = payload.get("sub")
        if not user_id:
            return None

        user = await self.get_user(user_id)
        if user is None:
            return None

        return await self.create_access_token(user)

    def get_settings(self) -> dict[str, Any]:
        """Get provider settings (non-sensitive)."""
        return {
            "access_token_expire_minutes": self.access_token_expire_minutes,
            "refresh_token_expire_days": self.refresh_token_expire_days,
            "algorithm": self.algorithm,
        }

    # Abstract methods that subclasses must implement
    async def authenticate(self, username: str, password: str) -> AuthResult:
        """Authenticate user - must be implemented by subclass."""
        raise NotImplementedError

    async def get_user(self, user_id: str) -> User | None:
        """Get user by ID - must be implemented by subclass."""
        raise NotImplementedError

    async def get_user_by_username(self, username: str) -> User | None:
        """Get user by username - must be implemented by subclass."""
        raise NotImplementedError

    async def revoke_refresh_token(self, refresh_token: str) -> bool:
        """Revoke refresh token - must be implemented by subclass."""
        raise NotImplementedError
