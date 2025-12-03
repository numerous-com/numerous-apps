"""Authentication middleware for route protection."""

import logging
from collections.abc import Callable, Sequence
from typing import Any

from fastapi import Request, Response
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


logger = logging.getLogger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware for protecting routes with authentication.

    This middleware:
    1. Checks if the requested route requires authentication
    2. Validates the access token from the request
    3. Redirects to login page for unauthenticated HTML requests
    4. Returns 401 for unauthenticated API requests

    Configuration:
    - public_routes: Routes that don't require authentication
    - protected_routes: Routes that require authentication (if None, all non-public)
    - login_path: Path to redirect unauthenticated users
    """

    def __init__(
        self,
        app: ASGIApp,
        auth_provider: Any,
        public_routes: Sequence[str] | None = None,
        protected_routes: Sequence[str] | None = None,
        login_path: str = "/login",
    ) -> None:
        """
        Initialize the auth middleware.

        Args:
            app: The ASGI application
            auth_provider: The authentication provider instance
            public_routes: Routes that don't require authentication
            protected_routes: Routes that require authentication
            login_path: Path to the login page

        """
        super().__init__(app)
        self.auth_provider = auth_provider
        self.login_path = login_path

        # Default public routes (auth-related and static)
        self.public_routes = set(public_routes or [])
        self.public_routes.update(
            {
                "/login",
                "/api/auth/login",
                "/api/auth/logout",
                "/api/auth/refresh",
                "/api/auth/check",
                "/numerous.js",
                "/static",
                "/numerous-static",
                "/favicon.ico",
            }
        )

        # Protected routes (None means all non-public routes are protected)
        self.protected_routes = set(protected_routes) if protected_routes else None

    def _is_public_route(self, path: str) -> bool:
        """Check if a route is public (doesn't require auth)."""
        # Exact match
        if path in self.public_routes:
            return True

        # Prefix match (for static files, etc.)
        for public_route in self.public_routes:
            if path.startswith(public_route + "/"):
                return True
            # Handle routes ending with / like /static/
            if public_route.endswith("/") and path.startswith(public_route):
                return True

        return False

    def _is_protected_route(self, path: str) -> bool:
        """Check if a route requires authentication."""
        # If public, never protected
        if self._is_public_route(path):
            return False

        # If protected_routes is set, only those routes are protected
        if self.protected_routes is not None:
            for protected_route in self.protected_routes:
                if path == protected_route or path.startswith(protected_route + "/"):
                    return True
            return False

        # If protected_routes is None, all non-public routes are protected
        return True

    def _is_api_request(self, request: Request) -> bool:
        """Check if this is an API request (vs browser/HTML request)."""
        path = request.url.path

        # API paths
        if path.startswith("/api/"):
            return True

        # WebSocket upgrade
        if request.headers.get("upgrade", "").lower() == "websocket":
            return True

        # Check Accept header for JSON preference
        accept = request.headers.get("accept", "")
        if "application/json" in accept:
            return True

        # XHR requests
        if request.headers.get("x-requested-with", "").lower() == "xmlhttprequest":
            return True

        return False

    def _get_token_from_request(self, request: Request) -> str | None:
        """Extract token from request headers or cookies."""
        # Authorization header
        auth_header = request.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer "):
            token: str = auth_header[7:]
            return token

        # Query parameter (for WebSocket)
        token_param = request.query_params.get("token")
        if token_param:
            return str(token_param)

        # Cookie
        cookie_token = request.cookies.get("access_token")
        return str(cookie_token) if cookie_token else None

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Response],
    ) -> Response:
        """Process the request through the middleware."""
        path = request.url.path

        # Skip authentication check for public routes
        if not self._is_protected_route(path):
            return await call_next(request)

        # Get token and validate
        token = self._get_token_from_request(request)
        user = None

        if token:
            try:
                user = await self.auth_provider.validate_access_token(token)
            except Exception as e:
                logger.warning(f"Token validation failed: {e}")

        # If authenticated, attach user to request state and continue
        if user:
            request.state.user = user
            return await call_next(request)

        # Not authenticated - handle based on request type
        if self._is_api_request(request):
            # API request: return 401 JSON response
            from fastapi.responses import JSONResponse

            return JSONResponse(
                status_code=401,
                content={"detail": "Not authenticated"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Browser request: redirect to login
        next_url = str(request.url.path)
        if request.url.query:
            next_url += f"?{request.url.query}"

        login_url = f"{self.login_path}?next={next_url}"
        return RedirectResponse(url=login_url, status_code=302)


def create_auth_middleware(
    auth_provider: Any,
    public_routes: Sequence[str] | None = None,
    protected_routes: Sequence[str] | None = None,
    login_path: str = "/login",
) -> type[AuthMiddleware]:
    """
    Factory function to create configured AuthMiddleware class.

    This is useful when you need to pass configuration to the middleware
    via FastAPI's add_middleware method.

    Args:
        auth_provider: The authentication provider
        public_routes: Routes that don't require auth
        protected_routes: Routes that require auth (None = all non-public)
        login_path: Path to login page

    Returns:
        Configured AuthMiddleware class

    """

    class ConfiguredAuthMiddleware(AuthMiddleware):
        def __init__(self, app: ASGIApp):
            super().__init__(
                app=app,
                auth_provider=auth_provider,
                public_routes=public_routes,
                protected_routes=protected_routes,
                login_path=login_path,
            )

    return ConfiguredAuthMiddleware
