"""Module for combining multiple Numerous apps into a single server."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.responses import Response


if TYPE_CHECKING:
    from .server import NumerousApp


logger = logging.getLogger(__name__)


def combine_apps(
    apps: dict[str, NumerousApp],
    shared_static_dir: Path | str | None = None,
    shared_theme_css: str | None = None,
    root_redirect: str | None = None,
    shared_auth_provider: Any | None = None,  # noqa: ANN401
    title: str = "Numerous Apps",
) -> FastAPI:
    """
    Combine multiple Numerous apps into a single FastAPI application.

    This function creates a parent FastAPI application and mounts each sub-app
    at its specified path. Apps can share static files, themes, and optionally
    authentication.

    Args:
        apps: Dictionary mapping path prefixes to NumerousApp instances.
              Example: {"/app1": app1, "/app2": app2}
        shared_static_dir: Optional path to directory with shared static files.
                          Will be mounted at /shared-static/
        shared_theme_css: Optional CSS string for shared theme customization.
                         Will be served at /shared-static/css/theme.css
        root_redirect: Optional path to redirect "/" to (e.g., "/app1")
        shared_auth_provider: Optional shared authentication provider for all apps.
                             If provided, enables shared login at root level.
        title: Title for the combined application.

    Returns:
        FastAPI application that can be passed to uvicorn.run()

    Example:
        ```python
        from numerous.apps import create_app, combine_apps

        app1 = create_app(
            template="app1/index.html.j2",
            path_prefix="/app1",
            app_generator=run_app1,
        )

        app2 = create_app(
            template="app2/index.html.j2",
            path_prefix="/app2",
            app_generator=run_app2,
        )

        main_app = combine_apps(
            apps={"/app1": app1, "/app2": app2},
            root_redirect="/app1",
        )

        if __name__ == "__main__":
            import uvicorn
            uvicorn.run(main_app, host="127.0.0.1", port=8000)
        ```

    """
    main_app = FastAPI(title=title)

    # Mount shared static files if provided
    if shared_static_dir is not None:
        shared_static_path = (
            Path(shared_static_dir)
            if isinstance(shared_static_dir, str)
            else shared_static_dir
        )
        if shared_static_path.exists():
            main_app.mount(
                "/shared-static",
                StaticFiles(directory=str(shared_static_path)),
                name="shared_static",
            )
            logger.info(f"Mounted shared static files from {shared_static_path}")

    # Serve shared theme CSS if provided as string
    if shared_theme_css is not None:

        @main_app.get("/shared-static/css/theme.css")  # type: ignore[misc]
        async def serve_shared_theme() -> Response:
            return Response(content=shared_theme_css, media_type="text/css")

        logger.info("Registered shared theme CSS endpoint")

    # Configure each app with shared settings and mount
    for path, app in apps.items():
        # Normalize path to ensure it starts with /
        normalized_path = path if path.startswith("/") else f"/{path}"

        # Store shared configuration in app state
        app.state.shared_theme_available = bool(shared_static_dir or shared_theme_css)
        app.state.shared_auth_provider = shared_auth_provider
        app.state.mount_path = normalized_path

        # Mount the sub-app
        main_app.mount(normalized_path, app)
        logger.info(f"Mounted app at {normalized_path}")

    # Setup shared authentication if provider is configured
    if shared_auth_provider is not None:
        _setup_shared_auth(main_app, shared_auth_provider, apps)

    # Add root redirect if specified
    if root_redirect is not None:

        @main_app.get("/")  # type: ignore[misc]
        async def redirect_root() -> RedirectResponse:
            return RedirectResponse(url=root_redirect, status_code=302)

        logger.info(f"Configured root redirect to {root_redirect}")

    # Add health check endpoint
    @main_app.get("/health")  # type: ignore[misc]
    async def health_check() -> dict[str, str]:
        return {"status": "healthy", "apps": str(list(apps.keys()))}

    return main_app


def _setup_shared_auth(
    main_app: FastAPI,
    auth_provider: Any,  # noqa: ANN401
    apps: dict[str, NumerousApp],  # noqa: ARG001
) -> None:
    """
    Set up shared authentication across all apps.

    This creates a single login endpoint at the root level that all apps share.

    Args:
        main_app: The parent FastAPI application
        auth_provider: The authentication provider
        apps: Dictionary of mounted apps (reserved for future use)

    """
    # Lazy import to avoid circular dependencies
    from .auth.routes import auth_router

    # Store auth provider in main app state
    main_app.state.auth_provider = auth_provider

    # Include auth routes at root level
    main_app.include_router(auth_router, prefix="/api/auth")

    logger.info("Shared authentication enabled at root level")


def get_base_path() -> str:
    """
    Get the base path for the current app context.

    This is useful for generating URLs that work correctly when an app
    is mounted at a sub-path.

    Returns:
        The base path string (e.g., "/app1" or "")

    """
    # This will be set by the app during request handling
    # For now, return empty string as default
    return ""
