"""FastAPI dependencies for authentication."""

import logging
from typing import Annotated, Any

from fastapi import Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .models import User, UserContext


logger = logging.getLogger(__name__)

# HTTP Bearer token security scheme
bearer_scheme = HTTPBearer(auto_error=False)


async def get_auth_provider(request: Request) -> Any:
    """
    Get the auth provider from app state.

    Returns None if no auth provider is configured.
    """
    if hasattr(request.app.state, "auth_provider"):
        return request.app.state.auth_provider
    return None


async def get_token_from_request(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    token_query: str | None = Query(None, alias="token"),
) -> str | None:
    """
    Extract authentication token from request.

    Checks in order:
    1. Authorization: Bearer <token> header
    2. ?token=<token> query parameter
    3. access_token cookie

    Returns:
        Token string if found, None otherwise

    """
    # 1. Try Bearer token from header
    if credentials and credentials.credentials:
        token_str: str = credentials.credentials
        return token_str

    # 2. Try query parameter (useful for WebSocket)
    if token_query:
        return token_query

    # 3. Try cookie (fallback)
    token_cookie = request.cookies.get("access_token")
    if token_cookie:
        cookie_str: str = token_cookie
        return cookie_str

    return None


async def get_current_user(
    request: Request,
    token: str | None = Depends(get_token_from_request),
    auth_provider: Any = Depends(get_auth_provider),
) -> User:
    """
    Get the currently authenticated user.

    Raises HTTPException 401 if:
    - No token provided
    - Token is invalid or expired
    - User not found

    Usage in routes::

        @app.get("/protected")
        async def protected_route(user: User = Depends(get_current_user)):
            return {"message": f"Hello, {user.username}!"}
    """
    # If no auth provider, auth is disabled - this shouldn't happen
    # as protected routes should only be registered when auth is enabled
    if not auth_provider:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication not configured",
        )

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await auth_provider.validate_access_token(token)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is still active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    user_result: User = user
    return user_result


async def get_optional_user(
    request: Request,
    token: str | None = Depends(get_token_from_request),
    auth_provider: Any = Depends(get_auth_provider),
) -> User | None:
    """
    Get the current user if authenticated, None otherwise.

    Does not raise exception if user is not authenticated.
    Useful for routes that work for both authenticated and anonymous users.

    Usage::

        @app.get("/public")
        async def public_route(user: User | None = Depends(get_optional_user)):
            if user:
                return {"message": f"Hello, {user.username}!"}
            return {"message": "Hello, anonymous!"}
    """
    if not auth_provider or not token:
        return None

    try:
        validated_user = await auth_provider.validate_access_token(token)
        if validated_user and validated_user.is_active:
            result: User = validated_user
            return result
    except Exception:
        pass

    return None


async def get_user_context(
    user: User | None = Depends(get_optional_user),
) -> UserContext:
    """
    Get user context for exposing to app developers.

    Returns a UserContext object that can be passed to widgets/templates
    with the current user's info (or anonymous state).
    """
    if user:
        return UserContext.from_user(user)
    return UserContext.anonymous()


async def require_admin(
    user: User = Depends(get_current_user),
) -> User:
    """
    Require that the current user is an admin.

    Raises HTTPException 403 if user is not an admin.

    Usage::

        @app.get("/admin/users")
        async def admin_route(user: User = Depends(require_admin)):
            return {"admin": user.username}
    """
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


from collections.abc import Callable, Coroutine


def require_role(role: str) -> Callable[..., Coroutine[Any, Any, User]]:
    """
    Factory for creating role requirement dependencies.

    Args:
        role: The role name required

    Returns:
        FastAPI dependency that checks for the role

    Usage::

        @app.get("/reports")
        async def reports(user: User = Depends(require_role("analyst"))):
            return {"user": user.username}

    """

    async def role_dependency(user: User = Depends(get_current_user)) -> User:
        if not user.has_role(role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{role}' required",
            )
        return user

    return role_dependency


def require_any_role(roles: list[str]) -> Callable[..., Coroutine[Any, Any, User]]:
    """
    Factory for creating dependency that requires any of the specified roles.

    Args:
        roles: List of role names (user needs at least one)

    Returns:
        FastAPI dependency that checks for any of the roles

    Usage::

        @app.get("/data")
        async def data(user: User = Depends(require_any_role(["analyst", "admin"]))):
            return {"user": user.username}

    """

    async def roles_dependency(user: User = Depends(get_current_user)) -> User:
        if not user.has_any_role(roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"One of roles {roles} required",
            )
        return user

    return roles_dependency


# Type aliases for cleaner route signatures
CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_optional_user)]
AdminUser = Annotated[User, Depends(require_admin)]
AuthUserContext = Annotated[UserContext, Depends(get_user_context)]
