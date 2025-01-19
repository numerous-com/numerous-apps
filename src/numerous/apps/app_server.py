"""Module containing the app for the Numerous app."""

import asyncio
import inspect
import json
import logging
import uuid
from collections.abc import Callable
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
from starlette.websockets import WebSocketDisconnect

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
    SessionData,
    _get_session,
    _get_template,
    _load_main_js,
)
from .session_management import SessionManager


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
class NumerousAppServerState:
    dev: bool
    main_js: str
    base_dir: str
    module_path: str
    template: str
    internal_templates: dict[str, str]
    sessions: dict[str, SessionData]
    connections: dict[str, dict[str, WebSocket]]
    widgets: dict[str, AnyWidget] = field(default_factory=dict)
    allow_threaded: bool = False


def wrap_html(key: str) -> str:
    return f'<div id="{key}"></div>'


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


@_app.websocket("/ws/{client_id}/{session_id}")  # type: ignore[misc]
async def websocket_endpoint(
    websocket: WebSocket, client_id: str, session_id: str
) -> None:
    await websocket.accept()
    logger.debug(f"New WebSocket connection from client {client_id}")

    try:
        session = await _get_session(
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

        except (ValueError, TypeError, WebSocketDisconnect) as e:
            logger.exception("Failed to send session error message.")

        return

    if session_id not in _app.state.config.connections:
        _app.state.config.connections[session_id] = {}

    _app.state.config.connections[session_id][client_id] = websocket

    async def receive_messages() -> None:
        try:
            while True:
                await handle_receive_message(websocket, client_id, session)
        except (asyncio.CancelledError, WebSocketDisconnect):
            logger.debug(f"Receive task cancelled for client {client_id}")
            raise

    async def send_messages() -> None:
        """Handle sending messages to websocket clients."""
        try:
            # Register callback for all messages
            handle = session.register_callback(
                callback=lambda msg: handle_websocket_message(websocket, msg)
            )

            try:
                # Wait indefinitely until cancelled or disconnected
                await asyncio.Future()  # This future will never complete
            finally:
                # Clean up callback when done
                session.deregister_callback(handle)

        except (asyncio.CancelledError, WebSocketDisconnect):
            logger.debug(f"Send task cancelled for client {client_id}")
            raise

    try:
        await asyncio.gather(receive_messages(), send_messages())
    except (asyncio.CancelledError, WebSocketDisconnect):
        logger.debug(f"WebSocket tasks cancelled for client {client_id}")
    finally:
        cleanup_connection(session_id, client_id)


async def handle_receive_message(
    websocket: WebSocket, client_id: str, session: SessionManager
) -> None:
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
            raise TypeError("Message type is not a string")  # noqa: TRY301

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

        await websocket.send_text(encode_model(model))
    except (ValueError, TypeError, WebSocketDisconnect, json.JSONDecodeError):
        logger.debug("Failed to send message - client may be disconnected")
        raise


def cleanup_connection(session_id: str, client_id: str) -> None:
    if (
        session_id in _app.state.config.connections
        and client_id in _app.state.config.connections[session_id]
    ):
        logger.info(f"Client {client_id} disconnected")
        del _app.state.config.connections[session_id][client_id]


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
            connections={},
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
