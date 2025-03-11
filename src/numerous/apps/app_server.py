"""Module containing the app for the Numerous app."""

import asyncio
import inspect
import json
import logging
import time
import uuid
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass, field
from inspect import getmembers
from pathlib import Path
from typing import Any

import jinja2
from anywidget import AnyWidget
from fastapi import HTTPException, Request, WebSocket
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from jinja2 import FileSystemLoader, meta
from starlette.responses import HTMLResponse
from starlette.websockets import WebSocketDisconnect, WebSocketState

from .builtins import ParentVisibility
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
    WebSocketMessage,
    WidgetUpdateMessage,
    WidgetUpdateRequestMessage,
    encode_model,
)
from .server import (
    NumerousApp,
    _get_session,
    _get_template,
    _load_main_js,
)
from .session_management import SessionManager


# Session management constants
MAX_SESSIONS = 100
DEFAULT_SESSION_TIMEOUT = 24 * 60 * 60  # 24 hours in seconds
OVERFLOW_SESSION_TIMEOUT = 60 * 60  # 1 hour in seconds
CLEANUP_INTERVAL = 5 * 60  # Check for expired sessions every 5 minutes
NORMAL_CLOSE_CODE = 1000  # WebSocket normal closure code


class AppProcessError(Exception):
    pass


# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_app = NumerousApp()

# Get the base directory
BASE_DIR = Path.cwd()

# Add package directory setup near the top of the file
PACKAGE_DIR = Path(__file__).parent

# Configure templates with custom environment
templates = Jinja2Templates(
    directory=[str(BASE_DIR / "templates"), str(PACKAGE_DIR / "templates")]
)
templates.env.autoescape = False  # Disable autoescaping globally


@dataclass
class SessionInfo:
    """Stores session information including timing data."""

    data: SessionManager
    last_active: float = field(default_factory=time.time)
    created_at: float = field(default_factory=time.time)
    connections: dict[str, WebSocket] = field(default_factory=dict)


@dataclass
class NumerousAppServerState:
    dev: bool
    main_js: str
    base_dir: str
    module_path: str
    template: str
    internal_templates: dict[str, str]
    sessions: dict[str, SessionInfo]
    widgets: dict[str, AnyWidget] = field(default_factory=dict)
    allow_threaded: bool = False
    cleanup_task: asyncio.Task[None] | None = None


def wrap_html(key: str) -> str:
    return f'<div id="{key}" style="display: flex; width: 100%; height: 100%;"></div>'


def _handle_template_error(error_title: str, error_message: str) -> HTMLResponse:
    return HTMLResponse(
        content=templates.get_template("error.html.j2").render(
            {"error_title": error_title, "error_message": error_message}
        ),
        status_code=500,
    )


@_app.get("/")  # type: ignore[misc]
async def home(request: Request) -> Response:
    template = _app.state.config.template
    template_name = _get_template(template, _app.state.config.internal_templates)

    # Create the template context with widget divs
    template_widgets = {key: wrap_html(key) for key in _app.widgets}

    try:
        # Get template source and find undefined variables
        template_source = ""
        if isinstance(templates.env.loader, FileSystemLoader):
            template_source = templates.env.loader.get_source(
                templates.env, template_name
            )[0]
    except jinja2.exceptions.TemplateNotFound as e:
        return _handle_template_error("Template Error", f"Template not found: {e!s}")

    parsed_content = templates.env.parse(template_source)
    undefined_vars = meta.find_undeclared_variables(parsed_content)

    # Remove request and title from undefined vars as they are always provided
    undefined_vars.discard("request")
    undefined_vars.discard("title")

    # Check for variables in template that don't correspond to widgets
    unknown_vars = undefined_vars - set(template_widgets.keys())
    if unknown_vars:
        error_message = f"Template contains undefined variables that don't match\
            any widgets: {', '.join(unknown_vars)}"
        logger.error(error_message)
        return _handle_template_error("Template Error", error_message)

    # Rest of the existing code...
    template_content = templates.get_template(template_name).render(
        {"request": request, "title": "Home Page", **template_widgets}
    )

    # Check for missing widgets
    missing_widgets = [
        widget_id
        for widget_id in _app.widgets
        if f'id="{widget_id}"' not in template_content
    ]

    if missing_widgets:
        logger.warning(
            f"Template is missing placeholders for the following widgets:\
                {', '.join(missing_widgets)}. "
            "These widgets will not be displayed."
        )

    # Load the error modal, splash screen, and session lost banner templates
    error_modal = templates.get_template("error_modal.html.j2").render()
    splash_screen = templates.get_template("splash_screen.html.j2").render()
    session_lost_banner = templates.get_template("session_lost_banner.html.j2").render()

    # Modify the template content to include all components
    modified_html = template_content.replace(
        "</body>",
        f'{splash_screen}{error_modal}{session_lost_banner}\
            <script src="/numerous.js"></script></body>',
    )

    return HTMLResponse(modified_html)


@_app.get("/api/widgets")  # type: ignore[misc]
async def get_widgets(request: Request) -> dict[str, Any]:
    session_id = request.query_params.get("session_id")
    session = await _get_session(
        _app.state.config.allow_threaded,
        session_id,
        _app.state.config.base_dir,
        _app.state.config.module_path,
        _app.state.config.template,
    )

    logger.info(f"Session ID: {session_id}")

    _app_definition = await session.send(
        GetStateMessage(type=MessageType.GET_STATE).model_dump(),
        wait_for_response=True,
        timeout_seconds=10,
        message_types=[MessageType.INIT_CONFIG],
    )

    if _app_definition is None:
        raise HTTPException(status_code=500, detail="No app definition request failed.")

    for config in _app_definition["widget_configs"].values():
        if "defaults" in config:
            config["defaults"] = json.loads(config["defaults"])

    # Convert to InitConfigMessage if it's not already
    app_definition = InitConfigMessage(**_app_definition)

    return {
        "session_id": session.session_id,
        "widgets": app_definition.widget_configs,
        "logLevel": "DEBUG" if _app.state.config.dev else "ERROR",
    }


def _raise_websocket_disconnect(code: int) -> None:
    """Raise WebSocketDisconnect with a specific code."""
    raise WebSocketDisconnect(code=code)


@_app.websocket("/ws/{client_id}/{session_id}")  # type: ignore[misc]
async def websocket_endpoint(
    websocket: WebSocket, client_id: str, session_id: str
) -> None:
    """Handle WebSocket connections for real-time communication with clients."""
    await websocket.accept()
    logger.debug(f"New WebSocket connection from client {client_id}")

    # Get session or send error if not found
    session_data = await _get_session_or_error(websocket, session_id)
    if session_data is None:
        return

    # Initialize session info and track connection
    _register_connection(session_id, client_id, websocket, session_data)

    try:
        # Start the message handling tasks
        await asyncio.gather(
            _handle_client_messages(websocket, client_id, session_id, session_data),
            _handle_server_messages(websocket, client_id, session_data),
        )
    except WebSocketDisconnect as e:
        logger.debug(
            f"WebSocket disconnected for client {client_id} with code {e.code}"
        )
        _cleanup_connection(session_id, client_id)

        # Handle graceful closure
        if (
            session_id in _app.state.config.sessions
            and not _app.state.config.sessions[session_id].connections
            and e.code == NORMAL_CLOSE_CODE
        ):
            logger.info(
                f"Last client disconnected gracefully, cleaning up session {session_id}"
            )
            await cleanup_session(session_id)
    except asyncio.CancelledError:
        logger.debug(f"WebSocket tasks cancelled for client {client_id}")
        _cleanup_connection(session_id, client_id)

        # Log no-connection state for timeout cleanup
        if (
            session_id in _app.state.config.sessions
            and not _app.state.config.sessions[session_id].connections
        ):
            logger.debug(f"No more connections for session {session_id}")


async def _get_session_or_error(
    websocket: WebSocket, session_id: str
) -> SessionManager | None:
    """Get session data or send error if not found."""
    try:
        return await _get_session(
            allow_threaded=_app.state.config.allow_threaded,
            session_id=session_id,
            base_dir=_app.state.config.base_dir,
            module_path=_app.state.config.module_path,
            template=_app.state.config.template,
            allow_create=False,
        )
    except ValueError as e:
        logger.warning(f"Session not found for {session_id}: {e!s}")
        # Send session error message before closing
        error_msg = SessionErrorMessage()
        try:
            await websocket.send_text(encode_model(error_msg))
        except (ValueError, TypeError, WebSocketDisconnect):
            logger.exception("Failed to send session error message.")
        return None


def _register_connection(
    session_id: str, client_id: str, websocket: WebSocket, session_data: SessionManager
) -> None:
    """Register a new WebSocket connection and update session activity."""
    if session_id not in _app.state.config.sessions:
        _app.state.config.sessions[session_id] = SessionInfo(data=session_data)

    session_info = _app.state.config.sessions[session_id]
    session_info.connections[client_id] = websocket
    update_session_activity(session_id)


async def _handle_client_messages(
    websocket: WebSocket, client_id: str, session_id: str, session_data: SessionManager
) -> None:
    """Handle messages from the client to the server."""
    try:
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                # Normal closure has code 1000
                close_code = message.get("code", 0)
                logger.debug(f"Websocket disconnect with code {close_code}")
                _raise_websocket_disconnect(close_code)

            await handle_receive_message(websocket, client_id, session_data)
            update_session_activity(session_id)
    except (asyncio.CancelledError, WebSocketDisconnect):
        logger.debug(f"Receive task cancelled for client {client_id}")
        raise


async def _handle_server_messages(
    websocket: WebSocket, client_id: str, session_data: SessionManager
) -> None:
    """Handle messages from the server to the client."""
    try:
        # Register callback for all messages
        handle = session_data.register_callback(
            callback=lambda msg: handle_websocket_message(websocket, msg)
        )
        try:
            # Wait indefinitely until cancelled or disconnected
            await asyncio.Future()  # This future will never complete
        finally:
            # Clean up callback when done
            session_data.deregister_callback(handle)
    except (asyncio.CancelledError, WebSocketDisconnect):
        logger.debug(f"Send task cancelled for client {client_id}")
        raise


def _cleanup_connection(session_id: str, client_id: str) -> None:
    """Remove a client connection from a session."""
    if (
        session_id in _app.state.config.sessions
        and client_id in _app.state.config.sessions[session_id].connections
    ):
        logger.info(f"Client {client_id} disconnected")
        del _app.state.config.sessions[session_id].connections[client_id]


@_app.get("/numerous.js")  # type: ignore[misc]
async def serve_main_js() -> Response:
    return Response(
        content=_app.state.config.main_js, media_type="application/javascript"
    )


def create_app(  # noqa: PLR0912, C901
    template: str,
    dev: bool = False,
    widgets: dict[str, AnyWidget] | None = None,
    app_generator: Callable[[], dict[str, AnyWidget]] | None = None,
    **kwargs: dict[str, Any],
) -> NumerousApp:
    if widgets is None:
        widgets = {}

    for key, value in kwargs.items():
        if isinstance(value, AnyWidget):
            widgets[key] = value

    # Try to detect widgets in the locals from where the app function is called
    collect_widgets = len(widgets) == 0

    module_path = None

    is_process = False

    # Get the parent frame
    if (frame := inspect.currentframe()) is not None:
        frame = frame.f_back
        if frame:
            for key, value in frame.f_locals.items():
                if collect_widgets and isinstance(value, AnyWidget):
                    widgets[key] = value

            module_path = frame.f_code.co_filename

            if frame.f_locals.get("__process__"):
                is_process = True

    if module_path is None:
        raise ValueError("Could not determine app name or module path")

    allow_threaded = False
    if app_generator is not None:
        allow_threaded = True
        widgets = app_generator()

    logger.info(
        f"App instances will be {'threaded' if allow_threaded else 'multiprocessed'}"
    )
    if not is_process:
        # Optional: Configure static files (CSS, JS, images) only if directory exists
        static_dir = BASE_DIR / "static"
        if static_dir.exists():
            _app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

        # Add new mount for package static files
        package_static = PACKAGE_DIR / "static"
        if package_static.exists():
            _app.mount(
                "/numerous-static",
                StaticFiles(directory=str(package_static)),
                name="numerous_static",
            )

        config = NumerousAppServerState(
            dev=dev,
            main_js=_load_main_js(),
            sessions={},
            base_dir=str(BASE_DIR),
            module_path=str(module_path),
            template=template,
            internal_templates=templates,
            allow_threaded=allow_threaded,
        )

        _app.state.config = config

    if widgets:
        # Sort so ParentVisibility widgets are first in the dict
        widgets = {  # noqa: C416
            key: value
            for key, value in sorted(
                widgets.items(),
                key=lambda x: isinstance(x[1], ParentVisibility),
                reverse=True,
            )
        }

    _app.widgets = widgets

    return _app


@_app.get("/api/describe")  # type: ignore[misc]
async def describe_app() -> AppDescription:
    """
    Return a complete description of the app.

    Includes widgets, template context, and structure.
    """
    # Get template information
    template_name = _get_template(
        _app.state.config.template, _app.state.config.internal_templates
    )
    template_source = ""
    try:
        if isinstance(templates.env.loader, FileSystemLoader):
            template_source = templates.env.loader.get_source(
                templates.env, template_name
            )[0]
    except jinja2.exceptions.TemplateNotFound:
        template_source = "Template not found"

    # Parse template for context variables
    parsed_content = templates.env.parse(template_source)
    template_variables = meta.find_undeclared_variables(parsed_content)
    template_variables.discard("request")
    template_variables.discard("title")

    return AppDescription(
        app_info=AppInfo(
            dev_mode=_app.state.config.dev,
            base_dir=_app.state.config.base_dir,
            module_path=_app.state.config.module_path,
            allow_threaded=_app.state.config.allow_threaded,
        ),
        template=TemplateDescription(
            name=template_name,
            source=template_source,
            variables=list(template_variables),
        ),
        widgets=_describe_widgets(_app.widgets),
    )


@_app.get("/api/widgets/{widget_id}/traits/{trait_name}")  # type: ignore[misc]
async def get_trait_value(
    widget_id: str, trait_name: str, session_id: str
) -> TraitValue:
    """Get the current value of a widget's trait."""
    if widget_id not in _app.widgets:
        raise HTTPException(status_code=404, detail=f"Widget '{widget_id}' not found")

    widget = _app.widgets[widget_id]
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


@_app.put("/api/widgets/{widget_id}/traits/{trait_name}")  # type: ignore[misc]
async def set_trait_value(
    widget_id: str,
    trait_name: str,
    trait_value: SetTraitValue,
    session_id: str,
) -> TraitValue:
    """Set the value of a widget's trait."""
    session_manager = await _get_session(
        _app.state.config.allow_threaded,
        session_id,
        _app.state.config.base_dir,
        _app.state.config.module_path,
        _app.state.config.template,
        allow_create=False,
    )

    if widget_id not in _app.widgets:
        raise HTTPException(status_code=404, detail=f"Widget '{widget_id}' not found")

    widget = _app.widgets[widget_id]
    if trait_name not in widget.traits():
        raise HTTPException(
            status_code=404,
            detail=f"Trait '{trait_name}' not found on widget '{widget_id}'",
        )

    # Create widget update message using Pydantic model
    update_message = WidgetUpdateRequestMessage(
        type=MessageType.WIDGET_UPDATE,
        widget_id=widget_id,
        property=trait_name,
        value=trait_value.value,
    )

    # Send the message using the communication manager
    await session_manager.send(update_message.model_dump())

    # Return the updated trait value
    return TraitValue(
        widget_id=widget_id,
        trait=trait_name,
        value=trait_value.value,
        session_id=session_id,
    )


async def _handle_action_response(
    response_queue: asyncio.Queue,  # type: ignore[type-arg]
    request_id: str,  # noqa: ARG001
) -> Any:  # noqa: ANN401
    """Handle the response from an action execution."""
    try:
        response = await asyncio.wait_for(response_queue.get(), timeout=10)
        action_response = ActionResponseMessage(**response)
        if action_response.error:
            raise HTTPException(status_code=500, detail=action_response.error)
        return action_response.result  # noqa: TRY300
    except TimeoutError as err:
        raise HTTPException(
            status_code=504,
            detail="Timeout waiting for action response",
        ) from err


@_app.post("/api/widgets/{widget_id}/actions/{action_name}")  # type: ignore[misc]
async def execute_widget_action(
    widget_id: str,
    action_name: str,
    session_id: str,
    args: list[Any] | None = None,
    kwargs: dict[str, Any] | None = None,
) -> Any:  # noqa: ANN401
    """Execute an action on a widget."""
    try:
        session = await _get_session(
            _app.state.config.allow_threaded,
            session_id,
            _app.state.config.base_dir,
            _app.state.config.module_path,
            _app.state.config.template,
            allow_create=False,
        )
    except Exception as e:
        # Return a specific 404 status code for session not found
        raise HTTPException(
            status_code=404, detail="Session not found or expired"
        ) from e

    if widget_id not in _app.widgets:
        raise HTTPException(status_code=404, detail=f"Widget '{widget_id}' not found")

    # Create a unique request ID
    request_id = str(uuid.uuid4())

    # Create and send the action request message
    action_request = ActionRequestMessage(
        type=MessageType.ACTION_REQUEST,
        widget_id=widget_id,
        action_name=action_name,
        args=tuple(args) if args is not None else None,
        kwargs=kwargs or {},
        request_id=request_id,
        client_id="api_client",  # Use a fixed client ID for API requests
    )

    try:
        # Send message and wait for response using session manager
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


def _get_widget_actions(widget: AnyWidget) -> dict[str, dict[str, Any]]:
    """Get all actions defined on a widget."""
    actions = {}
    for name, member in getmembers(widget.__class__):
        if hasattr(member, "_is_action"):  # Check for action decorator
            actions[name] = {
                "name": name,
                "doc": member.__doc__ or "",
            }
    return actions


async def cleanup_expired_sessions() -> None:
    """Periodically check for and cleanup expired sessions."""
    while True:
        try:
            current_time = time.time()
            session_count = len(_app.state.config.sessions)

            # Determine timeout based on session count
            timeout = (
                OVERFLOW_SESSION_TIMEOUT
                if session_count > MAX_SESSIONS
                else DEFAULT_SESSION_TIMEOUT
            )

            expired_sessions = []
            for session_id, session_info in _app.state.config.sessions.items():
                # Check if session has expired
                if current_time - session_info.last_active > timeout:
                    expired_sessions.append(session_id)

            # If we're over the limit, also remove oldest sessions
            if session_count > MAX_SESSIONS:
                # Sort sessions by last active time
                sorted_sessions = sorted(
                    _app.state.config.sessions.items(), key=lambda x: x[1].last_active
                )
                # Get the oldest sessions that put us over the limit
                excess_count = session_count - MAX_SESSIONS
                expired_sessions.extend(
                    session_id
                    for session_id, _ in sorted_sessions[:excess_count]
                    if session_id not in expired_sessions
                )

            # Cleanup expired sessions
            for session_id in expired_sessions:
                await cleanup_session(session_id)

        except (RuntimeError, asyncio.CancelledError):
            logger.exception("Error in session cleanup")

        await asyncio.sleep(CLEANUP_INTERVAL)


async def cleanup_session(session_id: str) -> None:
    """Clean up a specific session and its resources."""
    if session_id in _app.state.config.sessions:
        session_info = _app.state.config.sessions[session_id]

        # Close all websocket connections
        for websocket in session_info.connections.values():
            try:
                await websocket.close()
            except (RuntimeError, ConnectionError) as e:
                logger.debug(f"Error closing websocket: {e}")

        # Cleanup session data
        try:
            await session_info.data.stop()
        except (RuntimeError, asyncio.CancelledError, ConnectionError):
            logger.exception("Error cleaning up session data")

        # Remove session from state
        del _app.state.config.sessions[session_id]
        logger.info(f"Cleaned up session {session_id}")


def update_session_activity(session_id: str) -> None:
    """Update the last active timestamp for a session."""
    if session_id in _app.state.config.sessions:
        _app.state.config.sessions[session_id].last_active = time.time()


@_app.on_event("startup")  # type: ignore[misc]
async def start_cleanup_task() -> None:
    """Start the session cleanup task when the app starts."""
    _app.state.config.cleanup_task = asyncio.create_task(cleanup_expired_sessions())


@_app.on_event("shutdown")  # type: ignore[misc]
async def cleanup_all_sessions() -> None:
    """Clean up all sessions when the app shuts down."""
    if _app.state.config.cleanup_task:
        _app.state.config.cleanup_task.cancel()
        with suppress(asyncio.CancelledError):
            await _app.state.config.cleanup_task

    # Cleanup all remaining sessions
    session_ids = list(_app.state.config.sessions.keys())
    for session_id in session_ids:
        await cleanup_session(session_id)


async def handle_receive_message(
    websocket: WebSocket, client_id: str, session: SessionManager
) -> None:
    """Process incoming messages from the client websocket."""
    message = await websocket.receive_json()

    # First check if we have a message type
    message_type = message.get("type")

    if message_type in ["get-state", "get-widget-states"]:
        # Convert to proper GetStateMessage Pydantic model
        await session.send(
            GetStateMessage(type=MessageType.GET_STATE).model_dump(),
            wait_for_response=True,
            timeout_seconds=10,
            message_types=[MessageType.INIT_CONFIG],
        )
        return

    # For messages that require widget_id
    if "widget_id" not in message:
        logger.error(f"Received message without widget_id: {message}")
        return

    msg: WidgetUpdateRequestMessage | ActionRequestMessage
    # Convert to appropriate message type based on message_type
    if message_type == "widget-update":
        msg = WidgetUpdateRequestMessage(
            type=MessageType.WIDGET_UPDATE,
            widget_id=message["widget_id"],
            property=message.get("property"),
            value=message.get("value"),
        )
    elif message_type == "action-request":
        msg = ActionRequestMessage(
            type=MessageType.ACTION_REQUEST,
            widget_id=message["widget_id"],
            action_name=message.get("action_name", ""),
            args=message.get("args", []),
            kwargs=message.get("kwargs", {}),
            client_id=client_id,
            request_id=str(uuid.uuid4()),
        )
    else:
        logger.warning(f"Unknown message type: {message_type}")
        return

    await session.send(msg.model_dump(), wait_for_response=False)


async def handle_websocket_message(
    websocket: WebSocket, message: dict[str, Any]
) -> None:
    """Handle incoming websocket messages by sending them to all connected clients."""
    try:
        msg_type = message.get("type")
        if not isinstance(msg_type, str):
            # Use helper function to abstract the raise
            _raise_type_error("Message type is not a string")

        model: WebSocketMessage
        if msg_type == MessageType.WIDGET_UPDATE.value:
            model = WidgetUpdateMessage(**message)
        elif msg_type == MessageType.ACTION_RESPONSE.value:
            model = ActionResponseMessage(**message)
        elif msg_type == MessageType.INIT_CONFIG.value:
            model = InitConfigMessage(**message)
        elif msg_type == MessageType.ERROR.value:
            model = ErrorMessage(**message)
        else:
            logger.warning(f"Unknown message type: {msg_type}")
            return

        # Check if websocket is still connected before sending
        if websocket.client_state == WebSocketState.CONNECTED:
            try:
                await websocket.send_text(encode_model(model))
            except RuntimeError as e:
                if "websocket.close" in str(e):
                    logger.debug("Websocket already closed, cannot send message")
                    raise WebSocketDisconnect from e
                raise
    except (ValueError, TypeError, WebSocketDisconnect, json.JSONDecodeError):
        logger.debug("Failed to send message - client may be disconnected")
        raise WebSocketDisconnect from None


def _raise_type_error(message: str) -> None:
    """Raise TypeError with the provided message."""
    raise TypeError(message)
