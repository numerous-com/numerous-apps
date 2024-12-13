from multiprocessing import Queue
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from anywidget import AnyWidget
import logging
import traceback
from queue import Empty
import json
from typing import TypedDict
import numpy as np

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



class WidgetConfig(TypedDict):
    moduleUrl: str
    defaults: Dict[str, Any]
    keys: List[str]
    css: Optional[str]

class SessionData(TypedDict):

    send_queue: Queue
    receive_queue: Queue
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
        if isinstance(obj, dict) and 'css' in obj:
            obj_copy = obj.copy()
            if len(obj_copy.get('css', '')) > 100:
                obj_copy['css'] = '<CSS content truncated>'
            return obj_copy
        return super().default(obj)



def _transform_widgets(widgets: Dict[str, AnyWidget]) -> Dict[str, WidgetConfig]|Dict[str, Any]:
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
                json_args[key] = json.dumps(arg, cls=NumpyJSONEncoder)
            except Exception as e:
                logger.error(f"Failed to serialize {key}: {str(e)[:100]}")
                raise

        # Handle both URL-based and string-based widget definitions
        module_source = widget._esm

        transformed[widget_key] = {
            "moduleUrl": module_source,  # Now this can be either a URL or a JS string
            "defaults": json.dumps(args, cls=NumpyJSONEncoder),
            "keys": list(args.keys()),
            "css": widget._css,
        }
    return transformed


logger = logging.getLogger(__name__)

def _execute(send_queue: Queue, receive_queue: Queue, session_id: str, widgets: Dict[str, AnyWidget], template: str) -> None:
    """Handle widget logic in the separate process"""

    transformed_widgets = _transform_widgets(widgets)
    
    # Set up observers for all widgets
    for widget_id, widget in widgets.items():
        for trait in transformed_widgets[widget_id]['keys']:
            trait_name = trait
            #logger.debug(f"[App] Adding observer for {widget_id}.{trait_name}")
            def create_handler(wid: str, trait: str) -> Callable[[Any], None]:
                def sync_handler(change: Any) -> None:
                    # Skip broadcasting for 'clicked' events to prevent recursion
                    if trait == 'clicked':
                        return
                    #logger.debug(f"[App] Broadcasting trait change for {wid}: {change.name} = {change.new}")
                    send_queue.put({
                        'type': 'widget_update',
                        'widget_id': wid,
                        'property': change.name,
                        'value': change.new
                    })
                return sync_handler
            
            widget.observe(create_handler(widget_id, trait), names=[trait_name])


    #json_transformed_widgets = json.dumps(transformed_widgets, cls=NumpyJSONEncoder)
    # Send initial app configuration
    send_queue.put({
        "type": "init-config",
        "widgets": list(transformed_widgets.keys()),
        "widget_configs": transformed_widgets,#transformed_widgets,
        "template": template
    })

    # Listen for messages from the main process
    while True:
        try:
            # Block until a message is available, with a timeout
            message = receive_queue.get(timeout=0.1)
            _handle_widget_message(message, send_queue, widgets=widgets)
        except Empty:
            # No message available, continue waiting
            continue

def _handle_widget_message(message: Dict[str, Any], send_queue: Queue, widgets: Dict[str, AnyWidget]) -> None:
    """Handle incoming widget messages and update states"""
    widget_id = message.get('widget_id')
    property_name = message.get('property')
    new_value = message.get('value')

    if not all([widget_id, property_name is not None]):
        #logger.error("Invalid widget message format")
        return

    try:
        # Get widget and validate it exists
        widget = widgets.get(widget_id)
        if not widget:
            #logger.error(f"Widget {widget_id} not found")
            return

        # Update the widget state
        setattr(widget, property_name, new_value)

        # Send update confirmation back to main process
        send_queue.put({
            'type': 'widget_update',
            'widget_id': widget_id,
            'property': property_name,
            'value': new_value
        }, timeout=1.0)  # Add timeout
        
    except Exception as e:
        #logger.error(f"Failed to handle widget message: {e}")
        send_queue.put({
            'type': 'error',
            'error_type': type(e).__name__,
            'message': str(e),
            'traceback': ""#traceback.format_exc()
        }, timeout=1.0)

