"""Data models for authentication."""

from typing import Any

from pydantic import BaseModel, Field


class User(BaseModel):
    """
    Authenticated user representation.

    This model is exposed to app developers and contains the authenticated
    user's information including their roles and permissions.
    """

    id: str = Field(..., description="Unique user identifier")
    username: str = Field(..., description="Username for display and login")
    email: str | None = Field(default=None, description="User's email address")
    roles: list[str] = Field(default_factory=list, description="List of role names")
    is_admin: bool = Field(
        default=False, description="Whether user has admin privileges"
    )
    is_active: bool = Field(default=True, description="Whether user account is active")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional user metadata"
    )

    @property
    def authenticated(self) -> bool:
        """Always True for a User instance (convenience property)."""
        return True

    def has_role(self, role: str) -> bool:
        """Check if user has a specific role."""
        return role in self.roles

    def has_any_role(self, roles: list[str]) -> bool:
        """Check if user has any of the specified roles."""
        return bool(set(self.roles) & set(roles))


class AuthResult(BaseModel):
    """Result of an authentication attempt."""

    success: bool = Field(..., description="Whether authentication succeeded")
    user: User | None = Field(
        default=None, description="Authenticated user if successful"
    )
    error: str | None = Field(default=None, description="Error message if failed")

    @classmethod
    def ok(cls, user: User) -> "AuthResult":
        """Create a successful auth result."""
        return cls(success=True, user=user)

    @classmethod
    def fail(cls, error: str) -> "AuthResult":
        """Create a failed auth result."""
        return cls(success=False, error=error)


class TokenPair(BaseModel):
    """Access and refresh token pair."""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiry in seconds")


class TokenResponse(BaseModel):
    """Response returned after successful login."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiry in seconds")
    user: User = Field(..., description="Authenticated user info")


class LoginCredentials(BaseModel):
    """Login request payload."""

    username: str = Field(..., min_length=1, description="Username")
    password: str = Field(..., min_length=1, description="Password")


class CreateUserRequest(BaseModel):
    """Request to create a new user (admin only)."""

    username: str = Field(..., min_length=1, max_length=255)
    email: str | None = Field(default=None)
    password: str = Field(..., min_length=8)
    roles: list[str] = Field(default_factory=list)
    is_admin: bool = Field(default=False)


class UpdateUserRequest(BaseModel):
    """Request to update a user (admin only)."""

    email: str | None = None
    password: str | None = Field(default=None, min_length=8)
    roles: list[str] | None = None
    is_admin: bool | None = None
    is_active: bool | None = None


class UserContext(BaseModel):
    """
    User context exposed to app developers.

    This is the object that app developers can access to get info about
    the currently authenticated user (or anonymous state).
    """

    authenticated: bool = Field(
        default=False, description="Whether user is authenticated"
    )
    username: str | None = Field(default=None, description="Username if authenticated")
    user_id: str | None = Field(default=None, description="User ID if authenticated")
    roles: list[str] = Field(default_factory=list, description="User roles")
    is_admin: bool = Field(default=False, description="Whether user is admin")

    @classmethod
    def anonymous(cls) -> "UserContext":
        """Create an anonymous (unauthenticated) context."""
        return cls(authenticated=False)

    @classmethod
    def from_user(cls, user: User) -> "UserContext":
        """Create context from an authenticated user."""
        return cls(
            authenticated=True,
            username=user.username,
            user_id=user.id,
            roles=user.roles,
            is_admin=user.is_admin,
        )
