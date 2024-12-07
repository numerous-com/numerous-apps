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

backend = FastAPI()

# Get the base directory
BASE_DIR = Path.cwd()

from markupsafe import Markup

# Configure templates with custom environment
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
templates.env.autoescape = False  # Disable autoescaping globally

# Optional: Configure static files (CSS, JS, images)
backend.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# Store active connections and their associated widget states
widget_states = {}

class Backend:
    def __init__(self, module_path: str, app_name: str, is_file: bool = False, dev: bool = False):
        self.module_path = module_path
        self.app_name = app_name
        self.is_file = is_file
        self.dev = dev
        self.backend = backend
        self.sessions = {}  # Store active sessions
        self.connections = {}  # Add this line to store session-scoped connections
        self._setup_routes()

    def _get_session(self, session_id: str):
        # Generate a session ID if one doesn't exist
        

        if session_id not in self.sessions:

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
                self.sessions[session_id]["config"] = app_definition
            else:
                raise ValueError("Invalid message type. Expected 'init-config'.")  
        else:
            _session = self.sessions[session_id]

        return _session
    
    def _setup_routes(self):
        @self.backend.get("/")
        async def home(request: Request):
            
            session_id = request.cookies.get("session_id", str(uuid.uuid4()))

            _session = self._get_session(session_id)
            app_definition = _session["config"]
            
            def wrap_html(key):
                return f"<div id=\"{key}\"></div>"
            
            template = app_definition["template"]

            response = templates.TemplateResponse(
                self._get_template(template),
                {"request": request, "title": "Home Page", **{key: wrap_html(key) for key in app_definition["widgets"]}}
            )
            
            # Set the session ID cookie if it's new
            if "session_id" not in request.cookies:
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
            print(f"[Backend] New WebSocket connection from client {client_id}")
            
            # Initialize connections dict for this session if it doesn't exist
            if session_id not in self.connections:
                self.connections[session_id] = {}
            
            # Store connection in session-specific dictionary
            self.connections[session_id][client_id] = websocket
            
            session = self._get_session(session_id)

            async def receive_messages():
                try:
                    while True:
                        data = await websocket.receive_text()
                        message = json.loads(data)
                        print(f"[Backend] Received message from client {client_id}: {message}")
                        session['receive_queue'].put(message)
                except Exception as e:
                    print(f"[Backend] Receive error for client {client_id}: {e}")
                    return

            async def send_messages():
                try:
                    while True:
                        if not session['send_queue'].empty():
                            response = session['send_queue'].get()
                            print(f"[Backend] Sending message to client {client_id}: {response}")
                            
                            if response.get('type') == 'widget_update':
                                print(f"[Backend] Broadcasting widget update to other clients")
                                # Strip the 'type' field before sending to clients
                                update_message = {
                                    'widget_id': response['widget_id'],
                                    'property': response['property'],
                                    'value': response['value']
                                }
                                # Broadcast to other clients in the same session
                                for other_id, conn in self.connections[session_id].items():
                                    if True: #other_id != client_id:  # Only send to other clients
                                        try:
                                            print(f"[Backend] Broadcasting to client {other_id}: {update_message}")
                                            await conn.send_text(json.dumps(update_message))
                                        except Exception as e:
                                            print(f"[Backend] Error broadcasting to client {other_id}: {e}")
                            elif response.get('type') == 'init-config':
                                # Send initialization data only to the connecting client
                                await websocket.send_text(json.dumps(response))
                        await asyncio.sleep(0.01)
                except Exception as e:
                    print(f"[Backend] Send error for client {client_id}: {e}")
                    return

            try:
                # Run both tasks concurrently
                await asyncio.gather(
                    receive_messages(),
                    send_messages()
                )
            finally:
                # Clean up connection from session-specific dictionary
                if session_id in self.connections and client_id in self.connections[session_id]:
                    print(f"[Backend] Client {client_id} disconnected")
                    del self.connections[session_id][client_id]
                    
                    # If this was the last connection for this session, clean up the session
                    if not self.connections[session_id]:
                        del self.connections[session_id]
                        if session_id in self.sessions:
                            self.sessions[session_id]["process"].terminate()
                            self.sessions[session_id]["process"].join()
                            del self.sessions[session_id]

    def _get_template(self, template: str):
            if isinstance(template, str):
                # Extract just the filename from the path
                template_name = Path(template).name
                # Add the template directory to Jinja2's search path
                templates.env.loader.searchpath.append(str(Path(template).parent))
            return template_name
    
    @staticmethod
    def _app_process(session_id: str, module_string: str, app_name: str, send_queue: Queue, receive_queue: Queue, is_file: bool = False):
        """Run the app in a separate process"""
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

    def run(self):
        """Start the FastAPI server"""
        uvicorn.run(self.backend, host="127.0.0.1", port=8000)

    
