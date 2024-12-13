from jinja2 import Environment, FileSystemLoader
from pathlib import Path
import sys
import traceback
import importlib
from multiprocessing import Queue
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from typing_extensions import TypedDict
import logging
from multiprocessing import Process, Queue
import json
from ._execution import _execute
from fastapi import FastAPI

class NumerousApp(FastAPI):
    pass

logger = logging.getLogger(__name__)


class AppInitError(Exception):
    pass


class SessionData(TypedDict):
    process: Process

def _get_session(session_id: str, base_dir: str, module_path: str, template: str, sessions: Dict[str, SessionData]) -> SessionData:
        # Generate a session ID if one doesn't exist
        

    if session_id not in sessions:
        logger.info(f"Creating new session {session_id}. Total sessions: {len(sessions) + 1}")
        
        send_queue = Queue()
        receive_queue = Queue()
        process = Process(
            target=_app_process, 
            args=(session_id, str(base_dir), module_path, send_queue, receive_queue, template)
        )
        process.start()

        sessions[session_id] = {
            "process": process,
            "send_queue": send_queue,
            "receive_queue": receive_queue,
            "config": {}
        }

        _session = sessions[session_id]

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
        sessions[session_id]["config"] = app_definition
    else:
        _session = sessions[session_id]

    return _session
    

def _get_template(template: str, templates: Environment) -> str:
    try:
        template_name = Path(template).name
        if isinstance(templates.env.loader, FileSystemLoader):
            templates.env.loader.searchpath.append(str(Path(template).parent))
        return template_name
            

    except Exception as e:
        return templates.get_template("error.html.j2").render({
            "error_title": "Template Error",
            "error_message": f"Failed to load template: {str(e)}"
        })
    
def _app_process(
    session_id: str,
    cwd: str,
    module_string: str,
    send_queue: Queue,
    receive_queue: Queue,
    template: str
) -> None:
    """Run the app in a separate process"""
    try:
        logger.debug(f"[Backend] Running app from {module_string}")

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
        module.__process__ = True
        spec.loader.exec_module(module)

        _app_widgets = None
        # Iterate over all attributes of the module
        for name, value in module.__dict__.items():
            if isinstance(value, NumerousApp):
                _app_widgets = value.widgets
                break

        if _app_widgets is None:
            raise ValueError("No NumerousApp instance found in the module")
        
        _execute(send_queue, receive_queue, session_id, _app_widgets, template)

    except (KeyboardInterrupt, SystemExit):
        logger.info(f"Shutting down process for session {session_id}")
        
    except Exception as e:
        logger.error(f"Error in process for session {session_id}: {e}, traceback: {str(traceback.format_exc())[:100]}")
        send_queue.put({
            "type": "error",
            "error_type": type(e).__name__,
            "message": str(e),
            "traceback": str(traceback.format_exc())[:100]
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

def _load_main_js() -> str:
        """Load the main.js file from the package"""
        main_js_path = Path(__file__).parent / "js" / "numerous.js"
        if not main_js_path.exists():
            logger.warning(f"numerous.js not found at {main_js_path}")
            return ""
        return main_js_path.read_text()

def _create_handler(wid: str, trait: str, send_queue: Queue) -> Callable[[Any], None]:
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