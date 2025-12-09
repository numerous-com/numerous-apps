"""Factory module for creating NumerousApp instances with all routes."""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from contextlib import suppress
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import jinja2
from fastapi import HTTPException, Request, WebSocket


if TYPE_CHECKING:
    from anywidget import AnyWidget

    from .session_management import GlobalSessionManager
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from jinja2 import FileSystemLoader, meta
from starlette.responses import HTMLResponse
from starlette.websockets import WebSocketDisconnect, WebSocketState

from .execution import _describe_widgets
from .models import (
    ActionRequestMessage,
    ActionResponseMessage,
    AppDescription,
    AppInfo,
    ErrorMessage,
    GetStateMessage,
    InitConfigMessage,
    MessageType,
    SessionErrorMessage,
    SetTraitValue,
    TemplateDescription,
    TraitValue,
    WebSocketBatchUpdateMessage,
    WebSocketMessage,
    WidgetUpdateMessage,
    WidgetUpdateRequestMessage,
    encode_model,
)
from .server import (
    NumerousApp,
    _get_template,
    _load_main_js,
)
from .session_management import SessionManager, WidgetId


logger = logging.getLogger(__name__)

# Session management constants
MAX_SESSIONS = 100
DEFAULT_SESSION_TIMEOUT = 24 * 60 * 60  # 24 hours in seconds
OVERFLOW_SESSION_TIMEOUT = 60 * 60  # 1 hour in seconds
CLEANUP_INTERVAL = 5 * 60  # Check for expired sessions every 5 minutes
STALE_SESSION_THRESHOLD = 120  # Consider session stale after 2 minutes of inactivity
NEW_SESSION_GRACE_PERIOD = 5.0  # Grace period for new sessions in seconds

# Package directory
PACKAGE_DIR = Path(__file__).parent


@dataclass
class SessionInfo:
    """Stores session information including timing data."""

    data: SessionManager
    last_active: float = field(default_factory=time.time)
    created_at: float = field(default_factory=time.time)
    connections: dict[str, WebSocket] = field(default_factory=dict)


@dataclass
class NumerousAppServerState:
    """Configuration state for a Numerous app server."""

    dev: bool
    main_js: str
    base_dir: str
    module_path: str
    template: str
    internal_templates: Jinja2Templates
    sessions: dict[str, SessionInfo]
    path_prefix: str = ""
    app_id: str = ""
    widgets: dict[str, AnyWidget] = field(default_factory=dict)
    allow_threaded: bool = False
    cleanup_task: asyncio.Task[None] | None = None
    # Auth configuration
    auth_enabled: bool = False
    login_template: str | None = None
    public_routes: list[str] = field(default_factory=list)
    protected_routes: list[str] | None = None
    # Theme configuration
    theme_css: str | None = None
    shared_theme_available: bool = False
    # Per-app session manager (factory-only)
    session_manager: GlobalSessionManager | None = None


async def _get_app_session(
    session_manager: GlobalSessionManager,
    allow_threaded: bool,
    session_id: str,
    base_dir: str,
    module_path: str,
    template: str,
    app_id: str,
    allow_create: bool = True,
) -> SessionManager:
    """Get or create a session using the provided per-app session manager."""
    import uuid

    from .communication import MultiProcessExecutionManager, ThreadedExecutionManager
    from .server import _app_process
    from .session_management import SessionId

    # Generate a session ID if one doesn't exist
    if session_id in ["", "null", "undefined"] or (
        not session_manager.has_session(SessionId(session_id))
    ):
        if not allow_create:
            raise ValueError("Session ID not found.")
        session_id = str(uuid.uuid4())

        if allow_threaded:
            execution_manager: MultiProcessExecutionManager | ThreadedExecutionManager
            execution_manager = ThreadedExecutionManager(
                target=_app_process,  # type: ignore[arg-type]
                session_id=session_id,
            )
        else:
            execution_manager = MultiProcessExecutionManager(
                target=_app_process,  # type: ignore[arg-type]
                session_id=session_id,
            )
        execution_manager.start(str(base_dir), module_path, template, app_id)

        # Create session in this app's session manager
        session_manager_inst = session_manager.create_session(
            SessionId(session_id), execution_manager
        )
        logger.info(f"Creating new session {session_id}.")
    else:
        session_manager_inst = session_manager.get_session(SessionId(session_id))

    return session_manager_inst


def _wrap_html(key: str) -> str:
    """Wrap widget ID in a container div."""
    return f'<div id="{key}" style="display: flex; width: 100%; height: 100%;"></div>'


def create_numerous_app(
    base_dir: Path,
    module_path: str,
    template: str,
    dev: bool = False,
    path_prefix: str = "",
    app_id: str | None = None,
    widgets: dict[str, AnyWidget] | None = None,
    allow_threaded: bool = False,
    auth_provider: Any | None = None,  # noqa: ANN401
    login_template: str | None = None,
    public_routes: list[str] | None = None,
    protected_routes: list[str] | None = None,
    theme_css: str | None = None,
) -> NumerousApp:
    """
    Create a new NumerousApp instance with all routes configured.

    This factory function creates a fresh FastAPI application with all necessary
    routes, middleware, and configuration for a Numerous app.

    Args:
        base_dir: Base directory for the app (for templates/static files)
        module_path: Path to the app module file
        template: Template file name
        dev: Whether to run in development mode
        path_prefix: URL path prefix for this app (e.g., "/app1")
        app_id: Unique identifier for this app instance
        widgets: Dictionary of widget instances
        allow_threaded: Whether to allow threaded execution
        auth_provider: Optional authentication provider
        login_template: Optional custom login template
        public_routes: Routes that don't require authentication
        protected_routes: Routes that require authentication
        theme_css: Optional CSS string for theme customization

    Returns:
        Configured NumerousApp instance

    """
    app = NumerousApp()

    if app_id is None:
        app_id = str(uuid.uuid4())[:8]

    if widgets is None:
        widgets = {}

    # Configure templates. Check multiple locations: base_dir, base_dir/templates/,
    # and package templates.
    template_dirs = [
        str(base_dir),  # Check base_dir first for templates in app root
        str(base_dir / "templates"),  # Then base_dir/templates/
        str(PACKAGE_DIR / "templates"),  # Finally package templates
    ]
    templates = Jinja2Templates(directory=template_dirs)
    templates.env.autoescape = False

    # Create a per-app session manager for multi-app isolation
    from .session_management import GlobalSessionManager

    app_session_manager = GlobalSessionManager()

    # Create app state configuration
    config = NumerousAppServerState(
        dev=dev,
        main_js=_load_main_js(),
        sessions={},
        base_dir=str(base_dir),
        module_path=module_path,
        template=template,
        session_manager=app_session_manager,
        internal_templates=templates,
        path_prefix=path_prefix,
        app_id=app_id,
        allow_threaded=allow_threaded,
        auth_enabled=auth_provider is not None,
        login_template=login_template,
        public_routes=public_routes or [],
        protected_routes=protected_routes,
        theme_css=theme_css,
    )

    app.state.config = config
    app.widgets = widgets

    # Mount static files
    _mount_static_files(app, base_dir)

    # Define all routes
    _define_routes(app, templates, path_prefix)

    # Setup authentication if provider is configured
    if auth_provider is not None:
        _setup_auth(
            app,
            auth_provider,
            templates,
            login_template,
            public_routes,
            protected_routes,
            base_path=path_prefix,
        )

    return app


def _mount_static_files(app: NumerousApp, base_dir: Path) -> None:
    """Mount static file directories for the app."""
    # App-specific static files
    static_dir = base_dir / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # Package static files (including base CSS)
    package_static = PACKAGE_DIR / "static"
    if package_static.exists():
        app.mount(
            "/numerous-static",
            StaticFiles(directory=str(package_static)),
            name="numerous_static",
        )


def _define_routes(  # noqa: C901
    app: NumerousApp, templates: Jinja2Templates, path_prefix: str
) -> None:
    """Define all HTTP and WebSocket routes for the app."""

    @app.get("/")  # type: ignore[misc]
    async def home(request: Request) -> Response:
        """Serve the main app page."""
        return await _render_home(app, templates, request, path_prefix)

    @app.get("/api/widgets")  # type: ignore[misc]
    async def get_widgets(request: Request) -> dict[str, Any]:
        """Get widget configurations for the session."""
        return await _handle_get_widgets(app, request)

    @app.get("/numerous.js")  # type: ignore[misc]
    async def serve_main_js() -> Response:
        """Serve the main JavaScript file."""
        return Response(
            content=app.state.config.main_js, media_type="application/javascript"
        )

    @app.get("/api/describe")  # type: ignore[misc]
    async def describe_app() -> AppDescription:
        """Return a complete description of the app."""
        return await _handle_describe_app(app, templates)

    @app.get("/api/widgets/{widget_id}/traits/{trait_name}")  # type: ignore[misc]
    async def get_trait_value(
        widget_id: str, trait_name: str, session_id: str
    ) -> TraitValue:
        """Get the current value of a widget's trait."""
        return await _handle_get_trait(app, widget_id, trait_name, session_id)

    @app.put("/api/widgets/{widget_id}/traits/{trait_name}")  # type: ignore[misc]
    async def set_trait_value(
        widget_id: str,
        trait_name: str,
        trait_value: SetTraitValue,
        session_id: str,
    ) -> TraitValue:
        """Set the value of a widget's trait."""
        return await _handle_set_trait(
            app, widget_id, trait_name, trait_value, session_id
        )

    @app.post("/api/widgets/{widget_id}/actions/{action_name}")  # type: ignore[misc]
    async def execute_widget_action(
        widget_id: str,
        action_name: str,
        session_id: str,
        args: list[Any] | None = None,
        kwargs: dict[str, Any] | None = None,
    ) -> Any:  # noqa: ANN401
        """Execute an action on a widget."""
        return await _handle_widget_action(
            app, widget_id, action_name, session_id, args, kwargs
        )

    @app.websocket("/ws/{client_id}/{session_id}")  # type: ignore[misc]
    async def websocket_endpoint(
        websocket: WebSocket, client_id: str, session_id: str
    ) -> None:
        """WebSocket endpoint for client-server communication."""
        await _handle_websocket(app, websocket, client_id, session_id)

    @app.on_event("startup")  # type: ignore[misc]
    async def start_cleanup_task() -> None:
        """Start the session cleanup task when the app starts."""
        app.state.config.cleanup_task = asyncio.create_task(
            _cleanup_expired_sessions(app)
        )

    @app.on_event("shutdown")  # type: ignore[misc]
    async def cleanup_all_sessions() -> None:
        """Clean up all sessions when the app shuts down."""
        await _shutdown_cleanup(app)


async def _render_home(
    app: NumerousApp,
    templates: Jinja2Templates,
    request: Request,
    path_prefix: str,
) -> Response:
    """Render the home page with widgets and injected JavaScript."""
    template = app.state.config.template
    template_name = _get_template(template, app.state.config.internal_templates)

    # Create the template context with widget divs
    template_widgets = {key: _wrap_html(key) for key in app.widgets}

    try:
        template_source = ""
        if isinstance(templates.env.loader, FileSystemLoader):
            template_source = templates.env.loader.get_source(
                templates.env, template_name
            )[0]
    except jinja2.exceptions.TemplateNotFound as e:
        return _handle_template_error(
            templates, "Template Error", f"Template not found: {e!s}"
        )

    parsed_content = templates.env.parse(template_source)
    undefined_vars = meta.find_undeclared_variables(parsed_content)
    undefined_vars.discard("request")
    undefined_vars.discard("title")

    # Check for undefined variables
    unknown_vars = undefined_vars - set(template_widgets.keys())
    if unknown_vars:
        error_message = (
            f"Template contains undefined variables: {', '.join(unknown_vars)}"
        )
        logger.error(error_message)
        return _handle_template_error(templates, "Template Error", error_message)

    # Render template
    template_content = templates.get_template(template_name).render(
        {"request": request, "title": "Home Page", **template_widgets}
    )

    # Check for missing widgets
    missing_widgets = [
        widget_id
        for widget_id in app.widgets
        if f'id="{widget_id}"' not in template_content
    ]

    if missing_widgets:
        logger.warning(
            f"Template is missing placeholders for: {', '.join(missing_widgets)}"
        )

    # Load component templates
    error_modal = templates.get_template("error_modal.html.j2").render()
    splash_screen = templates.get_template("splash_screen.html.j2").render()
    session_lost_banner = templates.get_template("session_lost_banner.html.j2").render()

    # Inject base path for JavaScript
    base_path_script = f'<script>window.NUMEROUS_BASE_PATH = "{path_prefix}";</script>'

    # Inject base CSS - use path_prefix for multi-app deployments
    base_css_link = (
        f'<link rel="stylesheet" '
        f'href="{path_prefix}/numerous-static/css/numerous-base.css">'
    )

    # Build modified HTML
    modified_html = template_content.replace(
        "</head>",
        f"{base_css_link}{base_path_script}</head>",
    )
    modified_html = modified_html.replace(
        "</body>",
        f"{splash_screen}{error_modal}{session_lost_banner}"
        f'<script src="{path_prefix}/numerous.js"></script></body>',
    )

    return HTMLResponse(modified_html)


def _handle_template_error(
    templates: Jinja2Templates, error_title: str, error_message: str
) -> HTMLResponse:
    """Handle template errors by returning an error page."""
    return HTMLResponse(
        content=templates.get_template("error.html.j2").render(
            {"error_title": error_title, "error_message": error_message}
        ),
        status_code=500,
    )


async def _handle_get_widgets(app: NumerousApp, request: Request) -> dict[str, Any]:
    """Handle the get widgets API endpoint."""
    session_id = request.query_params.get("session_id")
    try:
        session = await _get_app_session(
            app.state.config.session_manager,
            app.state.config.allow_threaded,
            session_id,
            app.state.config.base_dir,
            app.state.config.module_path,
            app.state.config.template,
            app.state.config.app_id,
        )
        logger.debug(f"Session ID: {session_id}")

        # Fetch app definition with retries
        app_definition = await _fetch_app_definition_with_retry(session)

        # Process widget configs
        for config in app_definition["widget_configs"].values():
            if "defaults" in config:
                config["defaults"] = json.loads(config["defaults"])

        init_config = InitConfigMessage(**app_definition)

    except TimeoutError:
        logger.exception(f"Timeout getting app definition for session {session_id}")
        raise HTTPException(
            status_code=504,
            detail="Timeout waiting for application to initialize.",
        ) from None
    except Exception as e:
        logger.exception("Error getting widgets for session")
        raise HTTPException(
            status_code=500,
            detail="Failed to initialize application.",
        ) from e
    else:
        return {
            "session_id": session.session_id,
            "widgets": init_config.widget_configs,
            "logLevel": "DEBUG" if app.state.config.dev else "ERROR",
        }


async def _fetch_app_definition_with_retry(
    session: SessionManager,
) -> dict[str, Any]:
    """Fetch app definition with retry logic."""
    session_age = time.time() - session.last_activity_time

    if session_age > 1.0 and not session.is_active():
        raise ValueError(f"Session {session.session_id} is no longer active")

    return await _retry_fetch_app_definition(session)


async def _retry_fetch_app_definition(
    session: SessionManager,
) -> dict[str, Any]:
    """Retry fetching app definition with exponential backoff."""
    base_timeout = 8.0
    max_attempts = 3

    for attempt in range(1, max_attempts + 1):
        try:
            current_timeout = base_timeout * attempt
            logger.debug(
                f"Attempt {attempt}/{max_attempts} for app definition "
                f"(timeout: {current_timeout}s)"
            )

            if attempt > 1 and not session.is_active():
                raise ValueError(  # noqa: TRY301
                    f"Session {session.session_id} became inactive"
                )

            app_definition = await session.send(
                GetStateMessage(type=MessageType.GET_STATE).model_dump(),
                wait_for_response=True,
                timeout_seconds=current_timeout,
                message_types=[MessageType.INIT_CONFIG, MessageType.ERROR],
            )

            if app_definition is not None:
                return await _process_app_definition(app_definition)

        except TimeoutError:
            logger.warning(
                f"Timeout on attempt {attempt}/{max_attempts} for app definition"
            )
            if attempt == max_attempts:
                raise
            await asyncio.sleep(1.0)
        except ValueError:
            logger.exception("Session error")
            raise
        except Exception:
            logger.exception(
                f"Error on attempt {attempt}/{max_attempts} for app definition"
            )
            if attempt == max_attempts:
                raise
            await asyncio.sleep(1.0)

    raise TimeoutError(f"Maximum attempts ({max_attempts}) exceeded for app definition")


async def _process_app_definition(app_definition: dict[str, Any]) -> dict[str, Any]:
    """Process the app definition, handling error responses."""
    if app_definition.get("type") == "error":
        error_msg = app_definition.get("message", "Unknown error")
        error_traceback = app_definition.get("traceback", "No traceback")
        raise RuntimeError(
            f"Error in app process: {error_msg}\nTraceback: {error_traceback}"
        )
    return app_definition


async def _handle_describe_app(
    app: NumerousApp, templates: Jinja2Templates
) -> AppDescription:
    """Handle the describe app API endpoint."""
    template_name = _get_template(
        app.state.config.template, app.state.config.internal_templates
    )
    template_source = ""
    try:
        if isinstance(templates.env.loader, FileSystemLoader):
            template_source = templates.env.loader.get_source(
                templates.env, template_name
            )[0]
    except jinja2.exceptions.TemplateNotFound:
        template_source = "Template not found"

    parsed_content = templates.env.parse(template_source)
    template_variables = meta.find_undeclared_variables(parsed_content)
    template_variables.discard("request")
    template_variables.discard("title")

    return AppDescription(
        app_info=AppInfo(
            dev_mode=app.state.config.dev,
            base_dir=app.state.config.base_dir,
            module_path=app.state.config.module_path,
            allow_threaded=app.state.config.allow_threaded,
        ),
        template=TemplateDescription(
            name=template_name,
            source=template_source,
            variables=list(template_variables),
        ),
        widgets=_describe_widgets(app.widgets),
    )


async def _handle_get_trait(
    app: NumerousApp, widget_id: str, trait_name: str, session_id: str
) -> TraitValue:
    """Handle getting a widget trait value."""
    if widget_id not in app.widgets:
        raise HTTPException(status_code=404, detail=f"Widget '{widget_id}' not found")

    widget = app.widgets[widget_id]
    if trait_name not in widget.traits():
        raise HTTPException(
            status_code=404,
            detail=f"Trait '{trait_name}' not found on widget '{widget_id}'",
        )

    try:
        value = getattr(widget, trait_name)
        return TraitValue(
            widget_id=widget_id, trait=trait_name, value=value, session_id=session_id
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error getting trait value: {e!s}"
        ) from e


async def _handle_set_trait(
    app: NumerousApp,
    widget_id: str,
    trait_name: str,
    trait_value: SetTraitValue,
    session_id: str,
) -> TraitValue:
    """Handle setting a widget trait value."""
    session_manager = await _get_app_session(
        app.state.config.session_manager,
        app.state.config.allow_threaded,
        session_id,
        app.state.config.base_dir,
        app.state.config.module_path,
        app.state.config.template,
        app.state.config.app_id,
        allow_create=False,
    )

    if widget_id not in app.widgets:
        raise HTTPException(status_code=404, detail=f"Widget '{widget_id}' not found")

    widget = app.widgets[widget_id]
    if trait_name not in widget.traits():
        raise HTTPException(
            status_code=404,
            detail=f"Trait '{trait_name}' not found on widget '{widget_id}'",
        )

    update_message = WidgetUpdateRequestMessage(
        type=MessageType.WIDGET_UPDATE,
        widget_id=widget_id,
        property=trait_name,
        value=trait_value.value,
    )

    await session_manager.send(update_message.model_dump())

    return TraitValue(
        widget_id=widget_id,
        trait=trait_name,
        value=trait_value.value,
        session_id=session_id,
    )


async def _handle_widget_action(
    app: NumerousApp,
    widget_id: str,
    action_name: str,
    session_id: str,
    args: list[Any] | None,
    kwargs: dict[str, Any] | None,
) -> Any:  # noqa: ANN401
    """Handle executing a widget action."""
    try:
        session = await _get_app_session(
            app.state.config.session_manager,
            app.state.config.allow_threaded,
            session_id,
            app.state.config.base_dir,
            app.state.config.module_path,
            app.state.config.template,
            app.state.config.app_id,
            allow_create=False,
        )
    except Exception as e:
        raise HTTPException(
            status_code=404, detail="Session not found or expired"
        ) from e

    if widget_id not in app.widgets:
        raise HTTPException(status_code=404, detail=f"Widget '{widget_id}' not found")

    request_id = str(uuid.uuid4())
    action_request = ActionRequestMessage(
        type=MessageType.ACTION_REQUEST,
        widget_id=widget_id,
        action_name=action_name,
        args=tuple(args) if args is not None else None,
        kwargs=kwargs or {},
        request_id=request_id,
        client_id="api_client",
    )

    try:
        response = await session.send(
            action_request.model_dump(),
            wait_for_response=True,
            timeout_seconds=10,
            message_types=[MessageType.ACTION_RESPONSE],
        )
        if response is None:
            raise HTTPException(status_code=500, detail="No response from action")
        action_response = ActionResponseMessage(**response)
        if action_response.error:
            raise HTTPException(status_code=500, detail=action_response.error)
        return action_response.result  # noqa: TRY300
    except TimeoutError as e:
        raise HTTPException(
            status_code=504, detail="Timeout waiting for action response"
        ) from e


async def _handle_websocket(
    app: NumerousApp, websocket: WebSocket, client_id: str, session_id: str
) -> None:
    """Handle WebSocket connections."""
    try:
        await websocket.accept()
        logger.debug(f"WebSocket connection accepted: {client_id} -> {session_id}")

        session_data = await _get_session_or_error(app, websocket, session_id)
        if session_data is None:
            return

        # Check for stale sessions
        if session_id in app.state.config.sessions:
            session_info = app.state.config.sessions[session_id]
            current_time = time.time()
            inactive_time = current_time - session_info.last_active
            session_age = current_time - session_info.created_at

            if (
                inactive_time > STALE_SESSION_THRESHOLD
                and not session_data.is_active()
                and session_age > NEW_SESSION_GRACE_PERIOD
            ):
                logger.warning(f"Detected stale session {session_id}. Cleaning up.")
                await _cleanup_session(app, session_id)
                session_data = await _get_app_session(
                    app.state.config.session_manager,
                    app.state.config.allow_threaded,
                    session_id,
                    app.state.config.base_dir,
                    app.state.config.module_path,
                    app.state.config.template,
                    app.state.config.app_id,
                )

        _register_connection(app, session_id, client_id, websocket, session_data)
        _update_session_activity(app, session_id)

        await asyncio.gather(
            _handle_client_messages(
                app, websocket, client_id, session_id, session_data
            ),
            _handle_server_messages(websocket, client_id, session_data),
        )
    except WebSocketDisconnect:
        logger.debug(f"WebSocket disconnected: {client_id} -> {session_id}")
        _cleanup_connection(app, session_id, client_id)
    except Exception:
        logger.exception(f"WebSocket error: {client_id} -> {session_id}")
        _cleanup_connection(app, session_id, client_id)
        with suppress(Exception):
            await websocket.close()


async def _get_session_or_error(
    app: NumerousApp, websocket: WebSocket, session_id: str
) -> SessionManager | None:
    """Get session data or send error if not found."""
    try:
        return await _get_app_session(
            session_manager=app.state.config.session_manager,
            allow_threaded=app.state.config.allow_threaded,
            session_id=session_id,
            base_dir=app.state.config.base_dir,
            module_path=app.state.config.module_path,
            template=app.state.config.template,
            app_id=app.state.config.app_id,
            allow_create=False,
        )
    except ValueError as e:
        logger.warning(f"Session not found for {session_id}: {e!s}")
        error_msg = SessionErrorMessage()
        try:
            await websocket.send_text(encode_model(error_msg))
        except (ValueError, TypeError, WebSocketDisconnect):
            logger.exception("Failed to send session error message.")
        return None


def _register_connection(
    app: NumerousApp,
    session_id: str,
    client_id: str,
    websocket: WebSocket,
    session_data: SessionManager,
) -> None:
    """Register a new WebSocket connection."""
    if session_id not in app.state.config.sessions:
        app.state.config.sessions[session_id] = SessionInfo(data=session_data)

    session_info = app.state.config.sessions[session_id]
    session_info.connections[client_id] = websocket
    _update_session_activity(app, session_id)
    session_data.add_active_connection(client_id)


async def _handle_client_messages(
    app: NumerousApp,
    websocket: WebSocket,
    client_id: str,
    session_id: str,
    session_data: SessionManager,
) -> None:
    """Handle messages from the client."""
    try:
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                raise WebSocketDisconnect(  # noqa: TRY301
                    code=message.get("code", 0)
                )

            await _handle_receive_message(websocket, client_id, session_data)
            _update_session_activity(app, session_id)
    except (asyncio.CancelledError, WebSocketDisconnect):
        logger.debug(f"Receive task cancelled for client {client_id}")
        raise


async def _handle_server_messages(
    websocket: WebSocket, client_id: str, session_data: SessionManager
) -> None:
    """Handle messages from the server to the client."""
    try:
        handle = session_data.register_callback(
            callback=lambda msg: _handle_server_message_safely(
                websocket, msg, client_id
            )
        )
        try:
            await asyncio.Future()
        finally:
            session_data.deregister_callback(handle)
    except (asyncio.CancelledError, WebSocketDisconnect):
        logger.debug(f"Send task cancelled for client {client_id}")
        raise


async def _handle_server_message_safely(
    websocket: WebSocket, message: dict[str, Any], client_id: str
) -> None:
    """Safely handle server message."""
    try:
        if websocket.client_state == WebSocketState.CONNECTED:
            await _handle_websocket_message(websocket, message)
    except (WebSocketDisconnect, ConnectionError, RuntimeError) as e:
        logger.debug(f"Cannot send to client {client_id}: {e!s}")
    except Exception:
        logger.exception(f"Error sending message to client {client_id}")


def _cleanup_connection(app: NumerousApp, session_id: str, client_id: str) -> None:
    """Remove a client connection from a session."""
    if (
        session_id in app.state.config.sessions
        and client_id in app.state.config.sessions[session_id].connections
    ):
        del app.state.config.sessions[session_id].connections[client_id]

        if session_id in app.state.config.sessions:
            session_info = app.state.config.sessions[session_id]
            if hasattr(session_info.data, "remove_active_connection"):
                session_info.data.remove_active_connection(client_id)


def _update_session_activity(app: NumerousApp, session_id: str) -> None:
    """Update the last active timestamp for a session."""
    if session_id in app.state.config.sessions:
        app.state.config.sessions[session_id].last_active = time.time()


async def _cleanup_expired_sessions(app: NumerousApp) -> None:
    """Periodically check for and cleanup expired sessions."""
    while True:
        try:
            current_time = time.time()
            session_count = len(app.state.config.sessions)

            timeout = (
                OVERFLOW_SESSION_TIMEOUT
                if session_count > MAX_SESSIONS
                else DEFAULT_SESSION_TIMEOUT
            )

            expired_sessions = []
            for session_id, session_info in app.state.config.sessions.items():
                if current_time - session_info.last_active > timeout:
                    expired_sessions.append(session_id)

            if session_count > MAX_SESSIONS:
                sorted_sessions = sorted(
                    app.state.config.sessions.items(), key=lambda x: x[1].last_active
                )
                excess_count = session_count - MAX_SESSIONS
                expired_sessions.extend(
                    session_id
                    for session_id, _ in sorted_sessions[:excess_count]
                    if session_id not in expired_sessions
                )

            for session_id in expired_sessions:
                await _cleanup_session(app, session_id)

        except (RuntimeError, asyncio.CancelledError):
            logger.exception("Error in session cleanup")

        await asyncio.sleep(CLEANUP_INTERVAL)


async def _cleanup_session(app: NumerousApp, session_id: str) -> None:
    """Clean up a specific session and its resources."""
    if session_id in app.state.config.sessions:
        session_info = app.state.config.sessions[session_id]

        for client_id, websocket in list(session_info.connections.items()):
            with suppress(RuntimeError, ConnectionError):
                await websocket.close()
            session_info.connections.pop(client_id, None)

        try:
            await session_info.data.stop()
        except (RuntimeError, asyncio.CancelledError, ConnectionError):
            logger.exception("Error cleaning up session data")

        del app.state.config.sessions[session_id]


async def _shutdown_cleanup(app: NumerousApp) -> None:
    """Clean up all sessions when the app shuts down."""
    if app.state.config.cleanup_task:
        app.state.config.cleanup_task.cancel()
        with suppress(asyncio.CancelledError):
            await app.state.config.cleanup_task

    session_ids = list(app.state.config.sessions.keys())
    for session_id in session_ids:
        await _cleanup_session(app, session_id)


async def _handle_receive_message(
    websocket: WebSocket, client_id: str, session: SessionManager
) -> None:
    """Process incoming messages from the client websocket."""
    message = await websocket.receive_json()
    message_type = message.get("type")

    non_widget_types = ["get-widget-states", "get-widget-state"]
    if message_type not in non_widget_types and "widget_id" not in message:
        logger.error(f"Received message without widget_id: {message}")
        return

    if message_type == "get-widget-states":
        await _handle_get_widget_states(session)
    elif message_type == "get-widget-state":
        await _handle_get_widget_state(websocket, session, message.get("widget_id"))
    elif message_type == "widget-batch-update":
        await _handle_batch_update(websocket, session, message)
    elif message_type == "widget-update":
        await _handle_widget_update(websocket, session, message)
    elif message_type == "action-request":
        await _handle_action_request(session, message, client_id)
    else:
        logger.warning(f"Unknown message type: {message_type}")


async def _handle_get_widget_states(session: SessionManager) -> None:
    """Handle a request to get all widget states."""
    logger.debug("Client requested refresh of all widget states")
    await session.send(
        GetStateMessage(type=MessageType.GET_STATE).model_dump(),
        wait_for_response=True,
        timeout_seconds=10,
        message_types=[MessageType.INIT_CONFIG],
    )


async def _handle_get_widget_state(
    websocket: WebSocket, session: SessionManager, widget_id: str | None
) -> None:
    """Handle a request to get a specific widget's state."""
    if not widget_id:
        logger.error("Received get-widget-state without widget_id")
        return

    widget_state = session.get_widget_state(WidgetId(widget_id))

    for property_name, value in widget_state.items():
        update_msg = WidgetUpdateMessage(
            type=MessageType.WIDGET_UPDATE.value,
            widget_id=widget_id,
            property=property_name,
            value=value,
        )
        try:
            await _handle_websocket_message(websocket, update_msg.model_dump())
        except Exception:
            logger.exception(f"Error sending widget state update for {widget_id}")


async def _handle_batch_update(
    websocket: WebSocket, session: SessionManager, message: dict[str, Any]
) -> None:
    """Handle a batch update request."""
    widget_id = message.get("widget_id")
    properties = message.get("properties", {})
    request_id = message.get("request_id")

    if not widget_id or not properties:
        return

    for property_name, value in properties.items():
        update_msg = WidgetUpdateRequestMessage(
            type=MessageType.WIDGET_UPDATE,
            widget_id=widget_id,
            property=str(property_name),
            value=value,
        )
        await session.send(update_msg.model_dump(), wait_for_response=False)

    if request_id:
        confirmation_msg = WebSocketBatchUpdateMessage(
            type="widget-batch-update",
            widget_id=widget_id,
            properties=properties,
            request_id=request_id,
        )
        try:
            await websocket.send_text(encode_model(confirmation_msg))
        except Exception:
            logger.exception("Error sending batch update confirmation")


async def _handle_widget_update(
    websocket: WebSocket, session: SessionManager, message: dict[str, Any]
) -> None:
    """Handle an update to a single widget property."""
    property_value = message.get("property", "")
    property_name = str(property_value) if property_value is not None else ""

    msg = WidgetUpdateRequestMessage(
        type=MessageType.WIDGET_UPDATE,
        widget_id=message["widget_id"],
        property=property_name,
        value=message.get("value"),
    )

    request_id = message.get("request_id")
    await session.send(msg.model_dump(), wait_for_response=False)

    if request_id:
        echo_msg = WidgetUpdateMessage(
            type=MessageType.WIDGET_UPDATE.value,
            widget_id=message["widget_id"],
            property=property_name,
            value=message.get("value"),
            request_id=request_id,
        )
        try:
            await websocket.send_text(encode_model(echo_msg))
        except Exception:
            logger.exception("Error sending update confirmation")


async def _handle_action_request(
    session: SessionManager, message: dict[str, Any], client_id: str
) -> None:
    """Handle a widget action request."""
    msg = ActionRequestMessage(
        type=MessageType.ACTION_REQUEST,
        widget_id=message["widget_id"],
        action_name=message.get("action_name", ""),
        args=message.get("args", []),
        kwargs=message.get("kwargs", {}),
        client_id=client_id,
        request_id=str(uuid.uuid4()),
    )
    await session.send(msg.model_dump(), wait_for_response=False)


async def _handle_websocket_message(
    websocket: WebSocket, message: dict[str, Any]
) -> None:
    """Handle incoming websocket messages."""
    try:
        msg_type = message.get("type")

        if not isinstance(msg_type, str):
            raise TypeError("Message type is not a string")  # noqa: TRY301

        model = _create_message_model(msg_type, message)
        if model is None:
            return

        await _send_websocket_message(websocket, model, msg_type)
    except (ValueError, TypeError):
        logger.exception("Error processing message")
        raise WebSocketDisconnect from None
    except (WebSocketDisconnect, json.JSONDecodeError):
        raise WebSocketDisconnect from None


def _create_message_model(  # noqa: PLR0911
    msg_type: str, message: dict[str, Any]
) -> WebSocketMessage | None:
    """Create the appropriate message model."""
    if msg_type == MessageType.WIDGET_UPDATE.value:
        return WidgetUpdateMessage(**message)
    if msg_type == MessageType.ACTION_RESPONSE.value:
        return ActionResponseMessage(**message)
    if msg_type == MessageType.INIT_CONFIG.value:
        return InitConfigMessage(**message)
    if msg_type == MessageType.ERROR.value:
        return ErrorMessage(**message)
    if msg_type == "widget-batch-update":
        return WebSocketBatchUpdateMessage(**message)
    if msg_type == MessageType.SESSION_ERROR.value:
        return SessionErrorMessage(**message)
    logger.warning(f"Unknown message type: {msg_type}")
    return None


async def _send_websocket_message(
    websocket: WebSocket,
    model: WebSocketMessage,
    msg_type: str,  # noqa: ARG001
) -> None:
    """Send a message to the client."""
    if websocket.client_state == WebSocketState.CONNECTED:
        try:
            encoded_model = encode_model(model)
            await websocket.send_text(encoded_model)
        except RuntimeError as e:
            if "websocket.close" in str(e):
                raise WebSocketDisconnect from e
            raise
    else:
        logger.debug(
            f"Cannot send message - websocket in state {websocket.client_state}"
        )


def _setup_auth(
    app: NumerousApp,
    auth_provider: Any,  # noqa: ANN401
    templates: Jinja2Templates,
    login_template: str | None = None,
    public_routes: list[str] | None = None,
    protected_routes: list[str] | None = None,
    base_path: str = "",
) -> None:
    """Set up authentication for the app."""
    from .auth.middleware import create_auth_middleware
    from .auth.routes import admin_router, auth_router, create_login_page_route

    app.state.auth_provider = auth_provider

    # Use full path for login redirect when app is mounted at a sub-path
    login_path = f"{base_path}/login" if base_path else "/login"

    middleware_class = create_auth_middleware(
        auth_provider=auth_provider,
        public_routes=public_routes,
        protected_routes=protected_routes,
        login_path=login_path,
        base_path=base_path,
    )
    app.add_middleware(middleware_class)

    app.include_router(auth_router)

    if hasattr(auth_provider, "list_users"):
        app.include_router(admin_router)

    login_page_handler = create_login_page_route(templates, login_template, base_path)
    app.add_api_route("/login", login_page_handler, methods=["GET"])

    logger.info("Authentication enabled")
