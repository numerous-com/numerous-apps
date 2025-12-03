"""Authentication exceptions."""


class AuthError(Exception):
    """Base exception for authentication errors."""

    def __init__(self, message: str, status_code: int = 401) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class InvalidCredentialsError(AuthError):
    """Raised when login credentials are invalid."""

    def __init__(self, message: str = "Invalid username or password") -> None:
        super().__init__(message, status_code=401)


class InvalidTokenError(AuthError):
    """Raised when a token is invalid or expired."""

    def __init__(self, message: str = "Invalid or expired token") -> None:
        super().__init__(message, status_code=401)


class TokenExpiredError(InvalidTokenError):
    """Raised when a token has expired."""

    def __init__(self, message: str = "Token has expired") -> None:
        super().__init__(message)


class InsufficientPermissionsError(AuthError):
    """Raised when user lacks required permissions."""

    def __init__(self, message: str = "Insufficient permissions") -> None:
        super().__init__(message, status_code=403)


class UserNotFoundError(AuthError):
    """Raised when a user is not found."""

    def __init__(self, message: str = "User not found") -> None:
        super().__init__(message, status_code=404)


class UserExistsError(AuthError):
    """Raised when trying to create a user that already exists."""

    def __init__(self, message: str = "User already exists") -> None:
        super().__init__(message, status_code=409)


class UserInactiveError(AuthError):
    """Raised when an inactive user tries to authenticate."""

    def __init__(self, message: str = "User account is inactive") -> None:
        super().__init__(message, status_code=403)


class AuthProviderError(AuthError):
    """Raised when there's an error with the auth provider."""

    def __init__(self, message: str = "Authentication provider error") -> None:
        super().__init__(message, status_code=500)
