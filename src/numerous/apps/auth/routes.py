"""Authentication routes and endpoints."""

import logging
from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import (
    APIRouter,
    Cookie,
    Depends,
    HTTPException,
    Query,
    Request,
    Response,
    status,
)
from fastapi.responses import RedirectResponse
from starlette.templating import Jinja2Templates

from .dependencies import (
    AdminUser,
    CurrentUser,
    OptionalUser,
    get_auth_provider,
)
from .models import (
    CreateUserRequest,
    LoginCredentials,
    TokenResponse,
    UpdateUserRequest,
    User,
)


logger = logging.getLogger(__name__)

# Create router for auth endpoints
auth_router = APIRouter(prefix="/api/auth", tags=["authentication"])

# Create router for admin endpoints
admin_router = APIRouter(prefix="/admin", tags=["admin"])


# ============================================================================
# Authentication API Routes
# ============================================================================


@auth_router.post("/login", response_model=TokenResponse)  # type: ignore[misc]
async def login(
    credentials: LoginCredentials,
    response: Response,
    auth_provider: Any = Depends(get_auth_provider),
) -> TokenResponse:
    """
    Authenticate user and return tokens.

    Returns access token in response body and sets refresh token as httpOnly cookie.
    """
    if not auth_provider:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication not configured",
        )

    # Authenticate user
    result = await auth_provider.authenticate(
        credentials.username, credentials.password
    )

    if not result.success or not result.user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=result.error or "Invalid credentials",
        )

    user = result.user

    # Create tokens
    access_token, expires_in = await auth_provider.create_access_token(user)
    refresh_token = await auth_provider.create_refresh_token(user)

    # Set refresh token as httpOnly cookie
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        samesite="lax",
        max_age=7 * 24 * 60 * 60,  # 7 days
        path="/api/auth",  # Only sent to auth endpoints
    )

    # Also set access token as a cookie so browser sends it automatically
    # This is NOT httpOnly so JavaScript can also access it
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=False,  # Allow JS access for API calls
        secure=False,  # Set to True in production with HTTPS
        samesite="lax",
        max_age=expires_in,  # Match token expiry
        path="/",  # Sent to all routes
    )

    logger.info(f"User '{user.username}' logged in successfully")

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",  # noqa: S106 - Not a password, OAuth standard
        expires_in=expires_in,
        user=user,
    )


@auth_router.post("/refresh")  # type: ignore[misc]
async def refresh_token(
    response: Response,
    refresh_token: str | None = Cookie(None),
    auth_provider: Any = Depends(get_auth_provider),
) -> dict[str, Any]:
    """
    Refresh access token using refresh token cookie.

    Returns new access token if refresh token is valid.
    """
    if not auth_provider:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication not configured",
        )

    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No refresh token provided",
        )

    # Try to refresh
    result = await auth_provider.refresh_access_token(refresh_token)

    if not result:
        # Clear invalid refresh token cookie
        response.delete_cookie(key="refresh_token", path="/api/auth")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    new_access_token, expires_in = result

    return {
        "access_token": new_access_token,
        "token_type": "bearer",
        "expires_in": expires_in,
    }


@auth_router.post("/logout")  # type: ignore[misc]
async def logout(
    response: Response,
    refresh_token: str | None = Cookie(None),
    auth_provider: Any = Depends(get_auth_provider),
) -> dict[str, str]:
    """Logout user by revoking refresh token and clearing cookies."""
    if auth_provider and refresh_token:
        await auth_provider.revoke_refresh_token(refresh_token)

    # Clear cookies
    response.delete_cookie(key="refresh_token", path="/api/auth")
    response.delete_cookie(key="access_token", path="/")

    return {"message": "Logged out successfully"}


@auth_router.get("/me", response_model=User)  # type: ignore[misc]
async def get_current_user_info(user: CurrentUser) -> User:
    """Get current authenticated user's information."""
    return user


@auth_router.get("/check")  # type: ignore[misc]
async def check_auth(user: OptionalUser) -> dict[str, Any]:
    """Check if user is authenticated (does not require auth)."""
    if user:
        return {
            "authenticated": True,
            "username": user.username,
            "user_id": user.id,
            "roles": user.roles,
            "is_admin": user.is_admin,
        }
    return {"authenticated": False}


# ============================================================================
# Login Page Route (HTML)
# ============================================================================


def create_login_page_route(
    templates: Jinja2Templates,
    login_template: str | None = None,
    base_path: str = "",
) -> Callable[..., Coroutine[Any, Any, Response]]:
    """
    Create the login page route with the given templates.

    Args:
        templates: Jinja2Templates instance
        login_template: Custom login template name (optional)
        base_path: URL path prefix for multi-app deployments

    """

    async def login_page(
        request: Request,
        user: OptionalUser,
        next_url: str | None = Query(None, alias="next"),
    ) -> Response:
        """Render the login page."""
        # Default redirect should be to base_path root, not global root
        default_redirect = f"{base_path}/" if base_path else "/"

        # If already logged in, redirect to home or next URL
        if user:
            return RedirectResponse(url=next_url or default_redirect, status_code=302)

        template_name = login_template or "login.html.j2"

        return templates.TemplateResponse(
            template_name,
            {
                "request": request,
                "next": next_url or default_redirect,
                "title": "Login",
                "base_path": base_path,
            },
        )

    return login_page


# ============================================================================
# Admin Routes (require admin role)
# ============================================================================


@admin_router.get("/users")  # type: ignore[misc]
async def list_users(
    user: AdminUser,
    auth_provider: Any = Depends(get_auth_provider),
) -> list[User]:
    """List all users (admin only)."""
    if not auth_provider:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication not configured",
        )

    # Check if provider supports listing users
    if hasattr(auth_provider, "list_users"):
        users: list[User] = auth_provider.list_users()
        return users

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="User listing not supported by this auth provider",
    )


@admin_router.post("/users", response_model=User)  # type: ignore[misc]
async def create_user(
    user_data: CreateUserRequest,
    user: AdminUser,
    auth_provider: Any = Depends(get_auth_provider),
) -> User:
    """Create a new user (admin only)."""
    if not auth_provider:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication not configured",
        )

    # Check if provider supports creating users
    if hasattr(auth_provider, "create_user"):
        new_user: User = await auth_provider.create_user(user_data)
        return new_user

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="User creation not supported by this auth provider",
    )


@admin_router.put("/users/{user_id}", response_model=User)  # type: ignore[misc]
async def update_user(
    user_id: str,
    user_data: UpdateUserRequest,
    user: AdminUser,
    auth_provider: Any = Depends(get_auth_provider),
) -> User:
    """Update a user (admin only)."""
    if not auth_provider:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication not configured",
        )

    # Check if provider supports updating users
    if hasattr(auth_provider, "update_user"):
        updated_user: User = await auth_provider.update_user(user_id, user_data)
        return updated_user

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="User updates not supported by this auth provider",
    )


@admin_router.delete("/users/{user_id}")  # type: ignore[misc]
async def delete_user(
    user_id: str,
    user: AdminUser,
    auth_provider: Any = Depends(get_auth_provider),
) -> dict[str, str]:
    """Delete a user (admin only)."""
    if not auth_provider:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication not configured",
        )

    # Prevent self-deletion
    if user_id == user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )

    # Check if provider supports deleting users
    if hasattr(auth_provider, "delete_user"):
        await auth_provider.delete_user(user_id)
        return {"message": "User deleted successfully"}

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="User deletion not supported by this auth provider",
    )
