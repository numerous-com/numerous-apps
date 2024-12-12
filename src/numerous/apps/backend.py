from typing import Any, Dict, Optional, List, TypedDict, Union, Callable
from fastapi import FastAPI, Request, WebSocket
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import json
import asyncio
import uvicorn
import uuid
from multiprocessing import Process, Queue
import importlib
import logging
import numpy as np
from starlette.websockets import WebSocketDisconnect
from fastapi.responses import Response
from starlette.responses import HTMLResponse
from jinja2 import meta
import jinja2
import traceback
import sys
from jinja2 import FileSystemLoader

QueueType = Queue

class WidgetConfig(TypedDict):
    moduleUrl: str
    defaults: Dict[str, Any]
    keys: List[str]
    css: Optional[str]

class SessionData(TypedDict):
    process: Process
    send_queue: QueueType
    receive_queue: QueueType
    config: Dict[str, Any]

class NumpyJSONEncoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.bool_):
            return bool(obj)
        return super().default(obj)

class AppProcessError(Exception):
    pass

class AppInitError(Exception):
    pass

# Setup logging
logging.basicConfig()
logger = logging.getLogger(__name__)

backend = FastAPI()

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

# Optional: Configure static files (CSS, JS, images)
backend.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# Add new mount for package static files
backend.mount("/numerous-static", StaticFiles(directory=str(PACKAGE_DIR / "static")), name="numerous_static")

# Global state variables with type annotations
widget_states: Dict[str, Any] = {}

class Backend:
    def __init__(self, module_path: str|Path, app_name: str, 
                 dev: bool = False, log_level: str = 'INFO',
                 host: str = '127.0.0.1', port: int = 8000) -> None:
        self.module_path = module_path
        self.app_name = app_name
        self.dev = True if dev else False
        self.backend = backend
        self.sessions: Dict[str, SessionData] = {}
        self.connections: Dict[str, Dict[str, WebSocket]] = {}
        self.host = host
        self.port = port
        
        # Set log level
        log_level = getattr(logging, log_level.upper())
        logging.getLogger().setLevel(log_level)
        if self.dev:
            logger.debug("Dev mode enabled!")
        
        self.main_js = self._load_main_js()
        self._setup_routes()

    def _get_session(self, session_id: str) -> SessionData:
        # Generate a session ID if one doesn't exist
        

        if session_id not in self.sessions:
            logger.info(f"Creating new session {session_id}. Total sessions: {len(self.sessions) + 1}")
            
            send_queue = QueueType()
            receive_queue = QueueType()
            process = Process(
                target=self._app_process, 
                args=(session_id, str(BASE_DIR), self.module_path, self.app_name, send_queue, receive_queue)
            )
            process.start()

            self.sessions[session_id] = {
                "process": process,
                "send_queue": send_queue,
                "receive_queue": receive_queue,
                "config": {}
            }

            _session = self.sessions[session_id]

            # Get the app definition
            app_definition = _session["send_queue"].get()

            # Check message type
            if app_definition.get("type") == "init-config":
                # deserialize the config["defaults"]
                for widget_id, config in app_definition["widget_configs"].items():
                    if "defaults" in config:
                        config["defaults"] = json.loads(config["defaults"])
                
            elif app_definition.get("type") != "error":
                raise AppInitError("Invalid message type. Expected 'init-config'.")
            self.sessions[session_id]["config"] = app_definition
        else:
            _session = self.sessions[session_id]

        return _session
    
    def _setup_routes(self) -> None:
        def wrap_html(key: str) -> str:
            return f"<div id=\"{key}\"></div>"
        
        @self.backend.get("/")
        async def home(request: Request) -> Response:
            session_id = str(uuid.uuid4())
            try:
                _session = self._get_session(session_id)
                if _session["config"].get("type") == "error":
                    if self.dev:
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
                if self.dev:
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
            template_name = self._get_template(template)

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

        @self.backend.get("/api/widgets")
        async def get_widgets(request: Request) -> Dict[str, WidgetConfig]:
            session_id = request.cookies.get("session_id")
            if session_id is None:
                return {}
            _session = self._get_session(session_id)
            app_definition = _session["config"]
            widget_configs = app_definition.get("widget_configs", {})
            return dict(widget_configs)  # Use dict() instead of Dict[]

        @self.backend.websocket("/ws/{client_id}/{session_id}")
        async def websocket_endpoint(websocket: WebSocket, client_id: str, session_id: str) -> None:
            await websocket.accept()
            logger.debug(f"New WebSocket connection from client {client_id}")
            
            # Initialize connections dict for this session if it doesn't exist
            if session_id not in self.connections:
                self.connections[session_id] = {}
            
            # Store connection in session-specific dictionary
            self.connections[session_id][client_id] = websocket
            
            session = self._get_session(session_id)

            async def receive_messages() -> None:
                try:
                    while True:
                        try:
                            data = await websocket.receive_text()
                            message = json.loads(data)
                            logger.debug(f"Received message from client {client_id}: {message}")
                            session['receive_queue'].put(message)
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
                            if not session['send_queue'].empty():
                                response = session['send_queue'].get()
                                logger.debug(f"Sending message to client {client_id}: {response}")
                                
                                if response.get('type') == 'widget_update':
                                    logger.debug("Broadcasting widget update to other clients")
                                    update_message = {
                                        'widget_id': response['widget_id'],
                                        'property': response['property'],
                                        'value': response['value']
                                    }
                                    for other_id, conn in self.connections[session_id].items():
                                        try:
                                            logger.debug(f"Broadcasting to client {other_id}: {update_message}")
                                            await conn.send_text(json.dumps(update_message))
                                        except Exception as e:
                                            logger.debug(f"Error broadcasting to client {other_id}: {e}")
                                            raise  # Re-raise to trigger cleanup
                                elif response.get('type') == 'init-config':
                                    await websocket.send_text(json.dumps(response))
                                elif response.get('type') == 'error':
                                    print(response)
                                    if self.dev:
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
                if session_id in self.connections and client_id in self.connections[session_id]:
                    logger.info(f"Client {client_id} disconnected")
                    del self.connections[session_id][client_id]
                    
                    # If this was the last connection for this session, clean up the session
                    if not self.connections[session_id]:
                        del self.connections[session_id]
                        if session_id in self.sessions:
                            logger.info(f"Removing session {session_id}. Sessions remaining: {len(self.sessions) - 1}")
                            self.sessions[session_id]["process"].terminate()
                            self.sessions[session_id]["process"].join()
                            del self.sessions[session_id]

        @self.backend.get("/numerous.js")
        async def serve_main_js() -> Response:
            return Response(
                content=self.main_js,
                media_type="application/javascript"
            )

    def _get_template(self, template: str) -> str:
        try:
            if isinstance(template, str):
                template_name = Path(template).name
                if isinstance(templates.env.loader, FileSystemLoader):
                    templates.env.loader.searchpath.append(str(Path(template).parent))
                return template_name
            return ""
        except Exception as e:
            return templates.get_template("error.html.j2").render({
                "error_title": "Template Error",
                "error_message": f"Failed to load template: {str(e)}"
            })
    
    @staticmethod
    def _app_process(
        session_id: str,
        cwd: str,
        module_string: str,
        app_name: str,
        send_queue: QueueType,
        receive_queue: QueueType,
    ) -> None:
        """Run the app in a separate process"""
        try:
            logger.debug(f"[Backend] Running app {app_name} from {module_string}")

            # Add cwd to a path so that imports from BASE_DIR work
            sys.path.append(cwd)

            # Check if module is a file

            if not Path(module_string).exists():
                raise FileNotFoundError(f"Module file not found: {module_string}")

            # Load module from file path
            spec = importlib.util.spec_from_file_location("app_module", module_string)
            if spec is None or spec.loader is None:
                raise ImportError(f"Could not load module: {module_string}")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            
            app = getattr(module, app_name)
            app.execute(send_queue, receive_queue, session_id)
        except (KeyboardInterrupt, SystemExit):
            logger.info(f"Shutting down process for session {session_id}")
        except Exception as e:
            logger.error(f"Error in process for session {session_id}: {e}, traceback: {traceback.format_exc()}")
            send_queue.put({
                "type": "error",
                "error_type": type(e).__name__,
                "message": str(e),
                "traceback": traceback.format_exc()
            })
        finally:
            # Clean up queues
            while not send_queue.empty():
                try:
                    send_queue.get_nowait()
                except Exception:
                    pass
            while not receive_queue.empty():
                try:
                    receive_queue.get_nowait()
                except Exception:
                    pass

    def run(self) -> None:
        """Start the FastAPI server"""
        try:
            uvicorn.run(self.backend, host=self.host, port=self.port)
        except KeyboardInterrupt:
            logger.info("Shutting down server...")
            # Clean up all sessions and their processes
            for session_id, session in self.sessions.items():
                logger.debug(f"Terminating process for session {session_id}")
                session["process"].terminate()
                session["process"].join()
            
            # Clear all connections and sessions
            self.connections.clear()
            self.sessions.clear()
            logger.info("Server shutdown complete")

    def _load_main_js(self) -> str:
        """Load the main.js file from the package"""
        main_js_path = Path(__file__).parent / "js" / "numerous.js"
        if not main_js_path.exists():
            logger.warning(f"numerous.js not found at {main_js_path}")
            return ""
        return main_js_path.read_text()

    def create_handler(self, wid: str, trait: str, send_queue: QueueType) -> Callable[[Any], None]:
        def sync_handler(change: Any) -> None:
            # Skip broadcasting for 'clicked' events to prevent recursion
            if trait == 'clicked':
                return
            logger.debug(f"[App] Broadcasting trait change for {wid}: {change.name} = {change.new}")
            send_queue.put({
                'type': 'widget_update',
                'widget_id': wid,
                'property': change.name,
                'value': change.new
            })
        return sync_handler

    
