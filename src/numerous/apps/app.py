"""Module containing the app for the Numerous app."""

import asyncio
import inspect
import json
import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import jinja2
from anywidget import AnyWidget
from fastapi import Request, WebSocket
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from jinja2 import FileSystemLoader, meta
from starlette.responses import HTMLResponse
from starlette.websockets import WebSocketDisconnect

from ._builtins import ParentVisibility
from ._execution import NumpyJSONEncoder
from ._server import (
    NumerousApp,
    SessionData,
    _get_session,
    _get_template,
    _load_main_js,
)


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

    # Load the error modal template
    error_modal = templates.get_template("error_modal.html.j2").render()

    # Modify the template content to include the error modal
    modified_html = template_content.replace(
        "</body>", f'{error_modal}<script src="/numerous.js"></script></body>'
    )

    return HTMLResponse(content=modified_html)


@_app.get("/api/widgets")  # type: ignore[misc]
async def get_widgets(request: Request) -> dict[str, Any]:
    session_id = request.query_params.get("session_id")
    if session_id in {"undefined", "null", None}:
        session_id = str(uuid.uuid4())
    logger.info(f"Session ID: {session_id}")

    _session = _get_session(
        _app.state.config.allow_threaded,
        session_id,
        _app.state.config.base_dir,
        _app.state.config.module_path,
        _app.state.config.template,
        _app.state.config.sessions,
        load_config=True,
    )

    app_definition = _session["config"]
    widget_configs = app_definition.get("widget_configs", {})

    return {"session_id": session_id, "widgets": widget_configs}


@_app.websocket("/ws/{client_id}/{session_id}")  # type: ignore[misc]
async def websocket_endpoint(  # noqa: PLR0915, C901
    websocket: WebSocket, client_id: str, session_id: str
) -> None:
    await websocket.accept()

    logger.debug(f"New WebSocket connection from client {client_id}")

    if session_id not in _app.state.config.connections:
        _app.state.config.connections[session_id] = {}

    # Store connection in session-specific dictionary
    _app.state.config.connections[session_id][client_id] = websocket

    session = _get_session(
        _app.state.config.allow_threaded,
        session_id,
        _app.state.config.base_dir,
        _app.state.config.module_path,
        _app.state.config.template,
        _app.state.config.sessions,
    )

    async def receive_messages() -> None:
        try:
            while True:
                try:
                    data = await websocket.receive_text()
                    message = json.loads(data)
                    logger.debug(f"Received message from client {client_id}: {message}")
                    if (
                        session[
                            "execution_manager"
                        ].communication_manager.to_app_instance
                        is not None
                    ):
                        session[
                            "execution_manager"
                        ].communication_manager.to_app_instance.send(message)
                except WebSocketDisconnect:
                    logger.debug(f"WebSocket disconnected for client {client_id}")
                    raise  # Re-raise to trigger cleanup
        except (asyncio.CancelledError, WebSocketDisconnect):
            logger.debug(f"Receive task cancelled for client {client_id}")
            raise  # Re-raise to trigger cleanup
        except Exception as e:
            logger.debug(f"Receive error for client {client_id}: {e}")
            raise  # Re-raise to trigger cleanup

    async def send_messages() -> None:  # noqa: C901
        try:
            while True:
                try:
                    if not session[
                        "execution_manager"
                    ].communication_manager.from_app_instance.empty():
                        response = session[
                            "execution_manager"
                        ].communication_manager.from_app_instance.receive()
                        logger.debug(
                            f"Sending message to client {client_id}: {response}"
                        )

                        if response.get("type") == "widget_update":
                            logger.debug("Broadcasting widget update to other clients")
                            update_message = {
                                "widget_id": response["widget_id"],
                                "property": response["property"],
                                "value": response["value"],
                            }
                            for other_id, conn in _app.state.config.connections[
                                session_id
                            ].items():
                                try:
                                    if (
                                        "client_id" in update_message
                                        and update_message["client_id"] == client_id
                                    ) or ("client_id" not in update_message):
                                        logger.debug(
                                            f"Broadcasting to client {other_id}: \
                                                {str(update_message)[:100]}"
                                        )
                                        await conn.send_text(
                                            json.dumps(
                                                update_message, cls=NumpyJSONEncoder
                                            )
                                        )
                                except Exception as e:
                                    logger.debug(
                                        f"Error broadcasting to client {other_id}: {e}"
                                    )
                                    raise  # Re-raise to trigger cleanup
                        elif response.get("type") == "init-config":
                            await websocket.send_text(json.dumps(response))
                        elif response.get("type") == "error":
                            if _app.state.config.dev:
                                await websocket.send_text(json.dumps(response))
                    await asyncio.sleep(0.01)
                except WebSocketDisconnect:
                    logger.debug(f"WebSocket disconnected for client {client_id}")
                    raise  # Re-raise to trigger cleanup
        except (asyncio.CancelledError, WebSocketDisconnect):
            logger.debug(f"Send task cancelled for client {client_id}")
            raise  # Re-raise to trigger cleanup
        except Exception as e:
            logger.debug(f"Send error for client {client_id}: {e}")
            raise  # Re-raise to trigger cleanup

    try:
        # Run both tasks concurrently
        await asyncio.gather(receive_messages(), send_messages())
    except (asyncio.CancelledError, WebSocketDisconnect):
        logger.debug(f"WebSocket tasks cancelled for client {client_id}")

    finally:
        # Clean up connection from session-specific dictionary
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
