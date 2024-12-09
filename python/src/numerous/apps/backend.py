from fastapi import FastAPI, Request, WebSocket
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from typing import Dict
import json
import traitlets
import asyncio
import uvicorn
import uuid
from multiprocessing import Process, Queue
import importlib
import requests
import argparse
import os
import logging
import numpy as np
from starlette.websockets import WebSocketDisconnect
from fastapi.responses import Response
from starlette.responses import HTMLResponse
from jinja2 import meta
import jinja2
import traceback

class NumpyJSONEncoder(json.JSONEncoder):
    def default(self, obj):
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

from markupsafe import Markup

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

# Store active connections and their associated widget states
widget_states = {}

class Backend:
    def __init__(self, module_path: str, app_name: str, is_file: bool = False, dev: bool = False, log_level: str = 'INFO'):
        self.module_path = module_path
        self.app_name = app_name
        self.is_file = is_file
        self.dev = True if dev else False
        self.backend = backend
        self.sessions = {}  # Store active sessions
        self.connections = {}  # Add this line to store session-scoped connections
        
        # Set log level
        log_level = getattr(logging, log_level.upper())
        logging.getLogger().setLevel(log_level)
        if self.dev:
            logger.debug(f"Dev mode enabled!")
        
        self.main_js = self._load_main_js()
        
        self._setup_routes()

    def _get_session(self, session_id: str):
        # Generate a session ID if one doesn't exist
        

        if session_id not in self.sessions:
            logger.info(f"Creating new session {session_id}. Total sessions: {len(self.sessions) + 1}")
            
            send_queue = Queue()
            receive_queue = Queue()
            process = Process(
                target=self._app_process, 
                args=(session_id, self.module_path, self.app_name, send_queue, receive_queue, self.is_file)
            )
            process.start()

            self.sessions[session_id] = {
                "process": process,
                "send_queue": send_queue,
                "receive_queue": receive_queue
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
                self.sessions[session_id]["config"] = app_definition
            else:
                if app_definition.get("type") == "error":
                    raise AppProcessError(app_definition)
                else:
                    raise AppInitError("Invalid message type. Expected 'init-config'.")
        else:
            _session = self.sessions[session_id]

        return _session
    
    def _setup_routes(self):
        @self.backend.get("/")
        async def home(request: Request):
            session_id = str(uuid.uuid4())
            try:
                _session = self._get_session(session_id)
                app_definition = _session["config"]
            except Exception as e:
                if self.dev:
                    response = HTMLResponse(content=templates.get_template("app_process_error.html.j2").render({    
                        "error_title": f"Error in App Process",
                        "error_message": str(e),
                        "traceback": traceback.format_exc()
                    }), status_code=500)
                else:
                    response = HTMLResponse(content=templates.get_template("error.html.j2").render({    
                        "error_title": "Internal Error",
                        "error_message": "An internal error occurred while initializing the session."
                    }), status_code=500)
                return response
            
            def wrap_html(key):
                return f"<div id=\"{key}\"></div>"
            
            template = app_definition["template"]
            template_name = self._get_template(template)

            # Create the template context with widget divs
            template_widgets = {key: wrap_html(key) for key in app_definition["widgets"]}
            
            try:
                # Get template source and find undefined variables
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
            
            modified_html = template_content.replace('</body>', '<script src="/numerous.js"></script></body>')
            
            response = HTMLResponse(content=modified_html)
            response.set_cookie(key="session_id", value=session_id)
            
            return response

        @self.backend.get("/api/widgets")
        async def get_widgets(request: Request):
            session_id = request.cookies.get("session_id")
            _session = self._get_session(session_id)
            
            app_definition = _session["config"]
            return app_definition["widget_configs"]

        @self.backend.websocket("/ws/{client_id}/{session_id}")
        async def websocket_endpoint(websocket: WebSocket, client_id: str, session_id: str):
            await websocket.accept()
            logger.debug(f"New WebSocket connection from client {client_id}")
            
            # Initialize connections dict for this session if it doesn't exist
            if session_id not in self.connections:
                self.connections[session_id] = {}
            
            # Store connection in session-specific dictionary
            self.connections[session_id][client_id] = websocket
            
            session = self._get_session(session_id)

            async def receive_messages():
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

            async def send_messages():
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
        async def serve_main_js():
            return Response(
                content=self.main_js,
                media_type="application/javascript"
            )

    def _get_template(self, template: str):
        try:
            if isinstance(template, str):
                # Extract just the filename from the path
                template_name = Path(template).name
                # Add the template directory to Jinja2's search path
                templates.env.loader.searchpath.append(str(Path(template).parent))
            return template_name
        except Exception as e:
            # Render error template
            return templates.get_template("error.html.j2").render({
                "error_title": "Template Error",
                "error_message": f"Failed to load template: {str(e)}"
            })
    
    @staticmethod
    def _app_process(session_id: str, module_string: str, app_name: str, send_queue: Queue, receive_queue: Queue, is_file: bool = False):
        """Run the app in a separate process"""
        try:
            print(f"[Backend] Running app {app_name} from {module_string}")
            if is_file:
                # Load module from file path
                spec = importlib.util.spec_from_file_location("app_module", module_string)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
            else:
                # Load module from import path
                module = importlib.import_module(module_string)
            
            app = getattr(module, app_name)
            app.execute(send_queue, receive_queue, session_id)
        except (KeyboardInterrupt, SystemExit):
            logger.info(f"Shutting down process for session {session_id}")
        except Exception as e:
            logger.error(f"Error in process for session {session_id}: {e}")
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
                except:
                    pass
            while not receive_queue.empty():
                try:
                    receive_queue.get_nowait()
                except:
                    pass

    def run(self):
        """Start the FastAPI server"""
        try:
            uvicorn.run(self.backend, host="127.0.0.1", port=8000)
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

    def _load_main_js(self):
        """Load the main.js file from the package"""
        main_js_path = Path(__file__).parent / "js" / "numerous.js"
        if not main_js_path.exists():
            logger.warning(f"numerous.js not found at {main_js_path}")
            return ""
        return main_js_path.read_text()

    
