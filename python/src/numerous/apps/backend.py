from fastapi import FastAPI, Request, WebSocket
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from typing import Dict
import json
import traitlets
import asyncio
import uvicorn

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
connections: Dict[str, WebSocket] = {}
widget_states = {}

class Backend:
    def __init__(self, widgets: dict, transformed_widgets: dict, template: str, dev: bool):
        self.widgets = widgets
        self.transformed_widgets = transformed_widgets
        self.template = template
        self.dev = dev

        

    def _initialize_widget_states(self):
        # Initialize widget states with defaults
        for widget_id, config in self.transformed_widgets.items():
            widget_states[widget_id] = config.get('defaults', {})
            print(f"[Backend] Initializing widget {widget_id} with defaults: {widget_states[widget_id]}")
            
            # Add observers to widget traitlets
            widget = self.widgets[widget_id]
            for trait in self.transformed_widgets[widget_id]['defaults'].keys():
                trait_name = trait
                print(f"[Backend] Adding observer for {widget_id}.{trait_name}")
                # Create a synchronous wrapper for the async broadcast
                def create_sync_handler(wid):
                    async def async_broadcast(change):
                        # Skip broadcasting for 'clicked' events to prevent recursion
                        if trait == 'clicked':
                            return
                        await broadcast_trait_change(wid, change)
                    def sync_handler(change):
                        loop = asyncio.get_event_loop()
                        loop.create_task(async_broadcast(change))
                    return sync_handler
                
                widget.observe(create_sync_handler(widget_id), names=[trait_name])
        
        async def broadcast_trait_change(widget_id: str, change):
            print(f"[Backend] Broadcasting trait change for {widget_id}: {change.name} = {change.new}")
            message = {
                'widget_id': widget_id,
                'property': change.name,
                'value': change.new
            }
            
            # Broadcast to all connected clients
            for client_id, conn in connections.items():
                try:
                    print(f"[Backend] Sending to client {client_id}: {message}")
                    await conn.send_text(json.dumps(message))
                except Exception as e:
                    print(f"[Backend] Error broadcasting to client {client_id}: {e}")


    def _get_template(self):
        print(f"[Backend] Template: {self.template}")
        if isinstance(self.template, str):
            # Extract just the filename from the path
            template_name = Path(self.template).name
            # Add the template directory to Jinja2's search path
            templates.env.loader.searchpath.append(str(Path(self.template).parent))
            return template_name
        return self.template

    def _generate_backend(self):
        print(f"[Backend] Initializing with widgets: {list(self.widgets.keys())}")
        
        @backend.get("/")
        async def home(request: Request):
            def wrap_html(key):
                return f"<div id=\"{key}\"></div>"
            
            return templates.TemplateResponse(
                self._get_template(),
                {"request": request, "title": "Home Page", **{key: wrap_html(key) for key in self.transformed_widgets.keys()}}
            )

        @backend.get("/api/widgets")
        async def get_widgets():
            return self.transformed_widgets

        @backend.websocket("/ws/{client_id}")
        async def websocket_endpoint(websocket: WebSocket, client_id: str):
            await websocket.accept()
            print(f"[Backend] New WebSocket connection from client {client_id}")
            connections[client_id] = websocket
            
            try:
                while True:
                    data = await websocket.receive_text()
                    message = json.loads(data)
                    print(f"[Backend] Received message from client {client_id}: {message}")
                    
                    widget_id = message.get('widget_id')
                    property_name = message.get('property')
                    new_value = message.get('value')
                    
                    if widget_id and property_name is not None:
                        print(f"[Backend] Updating widget {widget_id}.{property_name} = {new_value}")
                        if widget_id not in widget_states:
                            widget_states[widget_id] = {}
                        widget_states[widget_id][property_name] = new_value
                        
                        # Update the actual widget
                        widget = self.widgets[widget_id]
                        print(f"[Backend] Setting attribute on widget: {widget}.{property_name} = {new_value}")
                        setattr(widget, property_name, new_value)
                        
                        # Broadcast to other clients
                        for other_id, conn in connections.items():
                            if other_id != client_id:
                                try:
                                    print(f"[Backend] Broadcasting to client {other_id}")
                                    await conn.send_text(json.dumps({
                                        'widget_id': widget_id,
                                        'property': property_name,
                                        'value': new_value
                                    }))
                                except Exception as e:
                                    print(f"[Backend] Error broadcasting to client {other_id}: {e}")
                    
            except Exception as e:
                print(f"[Backend] WebSocket error for client {client_id}: {e}")
            finally:
                if client_id in connections:
                    print(f"[Backend] Client {client_id} disconnected")
                    del connections[client_id]

    def run(self):
        self._initialize_widget_states()
        self._generate_backend()
        uvicorn.run(backend, host="0.0.0.0", port=8000)