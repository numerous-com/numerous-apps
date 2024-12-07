import anywidget, traitlets
from .backend import Backend
import uvicorn
from fastapi import Request
from ._builtins import ParentVisibility
from multiprocessing import Queue
from queue import Empty
import json

ignored_traits = [
            "comm",
            "layout",
            "log",
            "tabbable",
            "tooltip",
            "keys",
            "_esm",
            "_css",
            "_anywidget_id",
            "_msg_callbacks",
            "_dom_classes",
            "_model_module",
            "_model_module_version",
            "_model_name",
            "_property_lock",
            "_states_to_send",
            "_view_count",
            "_view_module",
            "_view_module_version",
            "_view_name",
        ]

def transform_widgets(widgets: dict[str, anywidget.AnyWidget]):
    transformed = {}
    for key, widget in widgets.items():
        widget_key = f"{key}"

        # Get all the traits of the widget
        args = widget.trait_values()
        traits = widget.traits()
        
        # Remove ignored traits
        for trait_name in ignored_traits:
            args.pop(trait_name, None)
            traits.pop(trait_name, None)

        json_args = {}
        for key, arg in args.items():
            try:
                _ = json.dumps(arg)
                json_args[key] = arg
            except:
                ...

        # Handle both URL-based and string-based widget definitions
        module_source = widget._esm
        #if isinstance(module_source, str) and not (module_source.startswith('http') or 
        #                                          module_source.startswith('./') or 
        #                                          module_source.startswith('/')):
            # If it's a string and not a URL, ensure it's a valid ES module
           # if not 'export default' in module_source:
           #     module_source = f"{module_source}\nexport default {{ render }};"

        transformed[widget_key] = {
            "moduleUrl": module_source,  # Now this can be either a URL or a JS string
            "defaults": json_args,
        }
    return transformed

class App:
    def __init__(self, widgets: dict, template: str, dev: bool):
        self.widgets = widgets
        self.transformed_widgets = transform_widgets(widgets)
        self.template = template
        self.dev = dev

    def execute(self, send_queue: Queue, receive_queue: Queue, session_id: str):
        """Handle widget logic in the separate process"""
        
        # Set up observers for all widgets
        for widget_id, widget in self.widgets.items():
            for trait in self.transformed_widgets[widget_id]['defaults'].keys():
                trait_name = trait
                print(f"[App] Adding observer for {widget_id}.{trait_name}")
                
                def create_handler(wid, trait):
                    def sync_handler(change):
                        # Skip broadcasting for 'clicked' events to prevent recursion
                        if trait == 'clicked':
                            return
                        print(f"[App] Broadcasting trait change for {wid}: {change.name} = {change.new}")
                        send_queue.put({
                            'type': 'widget_update',
                            'widget_id': wid,
                            'property': change.name,
                            'value': change.new
                        })
                    return sync_handler
                
                widget.observe(create_handler(widget_id, trait), names=[trait_name])

        # Send initial app configuration
        send_queue.put({
            "type": "init-config",
            "widgets": list(self.transformed_widgets.keys()),
            "widget_configs": self.transformed_widgets,
            "template": self.template
        })

        # Listen for messages from the main process
        while True:
            try:
                # Block until a message is available, with a timeout
                message = receive_queue.get(timeout=0.1)
                self._handle_widget_message(message, send_queue)
            except Empty:
                # No message available, continue waiting
                continue

    def _handle_widget_message(self, message: dict, send_queue: Queue):
        """Handle incoming widget messages and update states"""
        widget_id = message.get('widget_id')
        property_name = message.get('property')
        new_value = message.get('value')

        if widget_id and property_name is not None:
            # Update the widget state
            widget = self.widgets[widget_id]
            setattr(widget, property_name, new_value)

            # Send update confirmation back to main process
            send_queue.put({
                'type': 'widget_update',
                'widget_id': widget_id,
                'property': property_name,
                'value': new_value
            })

    

    def run(self):
        self.backend = Backend(self.widgets, self.transformed_widgets, self.template, self.dev)
        self.backend.run()

def app(widgets: dict, template: str, dev: bool):
    return App(widgets, template, dev)