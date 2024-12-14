from typing import Any, Dict, Optional, List, TypedDict, Union, Callable
from fastapi import Request, WebSocket
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import json
import asyncio
import uuid
from multiprocessing import Process, Queue
import logging
import numpy as np
from starlette.websockets import WebSocketDisconnect
from fastapi.responses import Response
from starlette.responses import HTMLResponse
from jinja2 import meta
import jinja2
import traceback
from jinja2 import FileSystemLoader
from dataclasses import dataclass, field
from ._server import _get_template, _get_session, SessionData
from anywidget import AnyWidget
import inspect
from ._builtins import ParentVisibility
from ._server import _load_main_js, NumerousApp
from ._execution import WidgetConfig
QueueType = Queue

class AppProcessError(Exception):
    pass



# Setup logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

_app = NumerousApp()

# Get the base directory
BASE_DIR = Path.cwd()

# Add package directory setup near the top of the file
PACKAGE_DIR = Path(__file__).parent

# Configure templates with custom environment
templates = Jinja2Templates(directory=[
    str(BASE_DIR / "templates"),
    str(PACKAGE_DIR / "templates")
])
templates.env.autoescape = False  # Disable autoescaping globally


@dataclass
class NumerousAppServerState:
    dev: bool
    main_js: str
    base_dir: str
    module_path: str
    template: str
    internal_templates: Dict[str, str]
    sessions: Dict[str, SessionData]
    connections: Dict[str, Dict[str, WebSocket]]
    widgets: Dict[str, AnyWidget] = field(default_factory=dict)

def wrap_html(key: str) -> str:
    return f"<div id=\"{key}\"></div>"
        
@_app.get("/")
async def home(request: Request) -> Response:
    session_id = str(uuid.uuid4())
    try:
        _session = _get_session(session_id, _app.state.config.base_dir, _app.state.config.module_path, _app.state.config.template, _app.state.config.sessions)

        if _session["config"].get("type") == "error":
            if _app.state.config.dev:
                response = HTMLResponse(content=templates.get_template("app_process_error.html.j2").render({    
                    "error_title": f"Error in App Process: {_session['config']['error_type']}",
                    "error_message": _session['config']['message'],
                    "traceback": _session['config']['traceback']
                }), status_code=500)
            else:
                response = HTMLResponse(content=templates.get_template("error.html.j2").render({    
                    "error_title": "Internal Error",
                    "error_message": "An internal error occurred while initializing the session."
                }), status_code=500)
            return response
    
        app_definition = _session["config"]
    except Exception as e:
        if _app.state.config.dev:
            response = HTMLResponse(content=templates.get_template("app_process_error.html.j2").render({    
                "error_title": "Error in App Process",
                "error_message": str(e),
                "traceback": traceback.format_exc()
            }), status_code=500)
        else:
            response = HTMLResponse(content=templates.get_template("error.html.j2").render({    
                "error_title": "Internal Error",
                "error_message": "An internal error occurred while initializing the session."
            }), status_code=500)
        return response
    

    template = app_definition["template"]
    template_name = _get_template(template, _app.state.config.internal_templates)

    # Create the template context with widget divs
    template_widgets = {key: wrap_html(key) for key in app_definition["widgets"]}
    
    try:
        # Get template source and find undefined variables
        template_source = ""
        if isinstance(templates.env.loader, FileSystemLoader):
            template_source = templates.env.loader.get_source(templates.env, template_name)[0]
    except jinja2.exceptions.TemplateNotFound as e:
        error_message = f"Template not found: {str(e)}"
        response = HTMLResponse(content=templates.get_template("error.html.j2").render({    
            "error_title": "Template Error",
            "error_message": error_message
        }), status_code=500)
        return response

    parsed_content = templates.env.parse(template_source)
    undefined_vars = meta.find_undeclared_variables(parsed_content)
    
    # Remove request and title from undefined vars as they are always provided
    undefined_vars.discard('request')
    undefined_vars.discard('title')
    
    # Check for variables in template that don't correspond to widgets
    unknown_vars = undefined_vars - set(template_widgets.keys())
    if unknown_vars:
        error_message = (
            f"Template contains undefined variables that don't match any widgets: {', '.join(unknown_vars)}"
        )
        logger.error(error_message)
        response = HTMLResponse(content=templates.get_template("error.html.j2").render({    
            "error_title": "Template Error",
            "error_message": error_message
        }), status_code=500)
        return response

    # Rest of the existing code...
    template_content = templates.get_template(template_name).render(
        {"request": request, "title": "Home Page", **template_widgets}
    )
    
    # Check for missing widgets
    missing_widgets = []
    for widget_id in app_definition["widgets"]:
        if f'id="{widget_id}"' not in template_content:
            missing_widgets.append(widget_id)
    
    if missing_widgets:
        logger.warning(
            f"Template is missing placeholders for the following widgets: {', '.join(missing_widgets)}. "
            "These widgets will not be displayed."
        )
    
    # Load the error modal template
    error_modal = templates.get_template("error_modal.html.j2").render()
    
    # Modify the template content to include the error modal
    modified_html = template_content.replace(
        '</body>', 
        f'{error_modal}<script src="/numerous.js"></script></body>'
    )
    
    response = HTMLResponse(content=modified_html)
    response.set_cookie(key="session_id", value=session_id)
    
    return response

@_app.get("/api/widgets")
async def get_widgets(request: Request) -> Dict[str, WidgetConfig]:
    try:    
        session_id = request.cookies.get("session_id")
        if session_id is None:
            return {}
        _session = _get_session(session_id, _app.state.config.base_dir, _app.state.config.module_path, _app.state.config.template, _app.state.config.sessions)

        app_definition = _session["config"]
        widget_configs = app_definition.get("widget_configs", {})

        
        return widget_configs
    except Exception as e:
        raise ValueError("Error getting widget configs")

@_app.websocket("/ws/{client_id}/{session_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str, session_id: str) -> None:

    await websocket.accept()

    logger.debug(f"New WebSocket connection from client {client_id}")

    if session_id not in _app.state.config.connections:
        _app.state.config.connections[session_id] = {}

    # Store connection in session-specific dictionary
    _app.state.config.connections[session_id][client_id] = websocket

    session = _get_session(session_id, _app.state.config.base_dir, _app.state.config.module_path, _app.state.config.template, _app.state.config.sessions)
    async def receive_messages() -> None:
        try:
            while True:
                try:
                    data = await websocket.receive_text()
                    message = json.loads(data)
                    logger.debug(f"Received message from client {client_id}: {message}")
                    session['communication_manager'].to_app_instance.send(message)
                except WebSocketDisconnect:
                    logger.debug(f"WebSocket disconnected for client {client_id}")
                    raise  # Re-raise to trigger cleanup
        except (asyncio.CancelledError, WebSocketDisconnect):
            logger.debug(f"Receive task cancelled for client {client_id}")
            raise  # Re-raise to trigger cleanup
        except Exception as e:
            logger.debug(f"Receive error for client {client_id}: {e}")
            raise  # Re-raise to trigger cleanup

    async def send_messages() -> None:
        try:
            while True:
                try:
                    if not session['communication_manager'].from_app_instance.empty():
                        response = session['communication_manager'].from_app_instance.receive()
                        logger.debug(f"Sending message to client {client_id}: {response}")
                        
                        if response.get('type') == 'widget_update':
                            logger.debug("Broadcasting widget update to other clients")
                            update_message = {
                                'widget_id': response['widget_id'],
                                'property': response['property'],
                                'value': response['value']
                            }
                            for other_id, conn in _app.state.config.connections[session_id].items():
                                try:
                                    logger.debug(f"Broadcasting to client {other_id}: {str(update_message)[:100]}")
                                    await conn.send_text(json.dumps(update_message))
                                except Exception as e:
                                    logger.debug(f"Error broadcasting to client {other_id}: {e}")
                                    raise  # Re-raise to trigger cleanup
                        elif response.get('type') == 'init-config':
                            await websocket.send_text(json.dumps(response))
                        elif response.get('type') == 'error':

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
        await asyncio.gather(
            receive_messages(),
            send_messages()
        )
    except (asyncio.CancelledError, WebSocketDisconnect):
        logger.debug(f"WebSocket tasks cancelled for client {client_id}")
        
    finally:
        # Clean up connection from session-specific dictionary
        if session_id in _app.state.config.connections and client_id in _app.state.config.connections[session_id]:
            logger.info(f"Client {client_id} disconnected")
            del _app.state.config.connections[session_id][client_id]
            
            # If this was the last connection for this session, clean up the session
            if not _app.state.config.connections[session_id]:
                del _app.state.config.connections[session_id]
                if session_id in _app.state.config.sessions:
                    logger.info(f"Removing session {session_id}. Sessions remaining: {len(_app.state.config.sessions) - 1}")
                    _app.state.config.sessions[session_id]["process"].terminate()
                    _app.state.config.sessions[session_id]["process"].join()
                    del _app.state.config.sessions[session_id]

@_app.get("/numerous.js")
async def serve_main_js() -> Response:
    
    return Response(
        content=_app.state.config.main_js,
        media_type="application/javascript"
    )
    
def create_app(template: str, dev: bool = False, widgets: Dict[str, AnyWidget]|None = None, **kwargs: Dict[str, Any]) -> None:

    

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
    if not (frame := inspect.currentframe()) is None:
        frame = frame.f_back
        if frame:
            
            for key, value in frame.f_locals.items():
                if collect_widgets and isinstance(value, AnyWidget):
                    widgets[key] = value
                

            module_path = frame.f_code.co_filename

            if "__process__" in frame.f_locals and frame.f_locals["__process__"]:
                is_process = True
    
    if module_path is None:
        
        raise ValueError("Could not determine app name or module path")
    
    if not is_process:
        # Optional: Configure static files (CSS, JS, images)
        _app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

        # Add new mount for package static files
        _app.mount("/numerous-static", StaticFiles(directory=str(PACKAGE_DIR / "static")), name="numerous_static")


        config = NumerousAppServerState(dev=dev, main_js=_load_main_js(), sessions={}, 
                                        connections={}, base_dir=str(BASE_DIR), module_path=str(module_path), 
                                        template=template,
                                        internal_templates=templates
                                        )

        _app.state.config = config

    
    # Sort so ParentVisibility widgets are first in the dict# Sort so ParentVisibility widgets are first in the dict
    widgets = {
        key: value
        for key, value in reversed(sorted(widgets.items(), key=lambda x: isinstance(x[1], ParentVisibility)))
    }

    _app.widgets = widgets
    

    return _app
