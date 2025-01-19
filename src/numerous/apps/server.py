"""Module for running the server."""

import importlib
import logging
import sys
import time
import traceback
import uuid
from collections.abc import Callable
from importlib.machinery import ModuleSpec
from pathlib import Path
from typing import Any

from anywidget import AnyWidget
from fastapi import FastAPI
from jinja2 import Environment, FileSystemLoader, TemplateError, TemplateNotFound
from typing_extensions import TypedDict

from .communication import MultiProcessExecutionManager, ThreadedExecutionManager
from .communication import QueueCommunicationChannel as CommunicationChannel
from .communication import QueueCommunicationManager as CommunicationManager
from .execution import _execute
from .models import (
    ErrorMessage,
)
from .session_management import GlobalSessionManager, SessionId, SessionManager


class Jinja2Templates(Environment):  # type: ignore[misc]
    pass


class NumerousApp(FastAPI):  # type: ignore[misc]
    pass


logger = logging.getLogger(__name__)


class AppInitError(Exception):
    pass


class SessionData(TypedDict):
    execution_manager: MultiProcessExecutionManager | ThreadedExecutionManager
    config: dict[str, Any]


global_session_manager = GlobalSessionManager()


async def _get_session(
    allow_threaded: bool,
    session_id: str,
    base_dir: str,
    module_path: str,
    template: str,
    allow_create: bool = True,
) -> SessionManager:
    # Generate a session ID if one doesn't exist
    if session_id in ["", "null", "undefined"] or (
        not global_session_manager.has_session(SessionId(session_id))
    ):
        if not allow_create:
            raise ValueError("Session ID not found.")
        session_id = str(uuid.uuid4())

        if allow_threaded:
            execution_manager: (
                ThreadedExecutionManager | MultiProcessExecutionManager
            ) = ThreadedExecutionManager(
                target=_app_process,  # type: ignore [arg-type]
                session_id=session_id,
            )
        else:
            execution_manager = MultiProcessExecutionManager(
                target=_app_process,  # type: ignore [arg-type]
                session_id=session_id,
            )
        execution_manager.start(str(base_dir), module_path, template)

        # Create session in global manager and store in local sessions dict
        session_manager = global_session_manager.create_session(
            SessionId(session_id), execution_manager
        )
        sessions = global_session_manager._sessions  # noqa: SLF001
        logger.info(
            f"Creating new session {session_id}.\
                Total sessions: \
                    {len(sessions) + 1}"
        )
    else:
        session_manager = global_session_manager.get_session(SessionId(session_id))

    return session_manager


def _get_template(template: str, templates: Jinja2Templates) -> str:
    try:
        template_name = Path(template).name
        if isinstance(templates.env.loader, FileSystemLoader):
            templates.env.loader.searchpath.append(str(Path(template).parent))
    except (TemplateNotFound, TemplateError) as e:
        return str(
            templates.get_template("error.html.j2").render(
                {
                    "error_title": "Template Error",
                    "error_message": f"Failed to load template: {e!s}",
                }
            )
        )
    else:
        return template_name


def _app_process(
    session_id: str,
    cwd: str,
    module_string: str,
    template: str,
    communication_manager: CommunicationManager,
) -> None:
    """Run the app in a separate process."""
    if not isinstance(communication_manager, CommunicationManager):
        raise TypeError(
            "communication_manager must be an instance of CommunicationManager"
        )

    try:
        logger.debug(f"[Backend] Running app from {module_string}")

        # Add cwd to a path so that imports from BASE_DIR work
        sys.path.append(cwd)

        # Check if module is a file
        _check_module_file_exists(module_string)

        # Load module from file path
        spec = importlib.util.spec_from_file_location("app_module", module_string)  # type: ignore [attr-defined]
        _check_module_spec(spec, module_string)
        module = importlib.util.module_from_spec(spec)  # type: ignore [attr-defined]
        module.__process__ = True
        spec.loader.exec_module(module)

        _app_widgets = {}
        # Iterate over all attributes of the module
        for value in module.__dict__.values():
            if isinstance(value, NumerousApp):
                _app_widgets = value.widgets
                break

        _check_app_widgets(_app_widgets)
        _execute(communication_manager, _app_widgets, template)

    except (KeyboardInterrupt, SystemExit):
        logger.info(f"Shutting down process for session {session_id}")

    except Exception as e:
        logger.exception(
            f"Error in process for session {session_id},\
                traceback: {str(traceback.format_exc())[:100]}"
        )
        communication_manager.from_app_instance.send(
            ErrorMessage(
                type="error",
                error_type=type(e).__name__,
                message=str(e),
                traceback=str(traceback.format_exc())[:100],
            ).model_dump()
        )
    finally:
        # Clean up queues
        while not communication_manager.to_app_instance.empty():
            communication_manager.to_app_instance.receive_nowait()

        while not communication_manager.from_app_instance.empty():
            communication_manager.from_app_instance.receive_nowait()


def _load_main_js() -> str:
    """Load the main.js file from the package."""
    main_js_path = Path(__file__).parent / "js" / "numerous.js"
    if not main_js_path.exists():
        logger.warning(f"numerous.js not found at {main_js_path}")
        return ""
    return main_js_path.read_text()


def _create_handler(
    wid: str, trait: str, send_channel: CommunicationChannel
) -> Callable[[Any], None]:
    def sync_handler(change: Any) -> None:  # noqa: ANN401
        # Skip broadcasting for 'clicked' events to prevent recursion
        if trait == "clicked":
            return
        logger.debug(
            f"[App] Broadcasting trait change for {wid}: {change.name} = {change.new}"
        )
        send_channel.send(
            {
                "type": "widget-update",
                "widget_id": wid,
                "property": change.name,
                "value": change.new,
            }
        )

    return sync_handler


def _check_app_widgets(app_widgets: dict[str, AnyWidget] | None) -> None:
    if app_widgets is None:
        raise ValueError("No NumerousApp instance found in the module")


def _check_module_spec(spec: ModuleSpec, module_string: str) -> None:
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module: {module_string}")


def _check_module_file_exists(module_string: str) -> None:
    if not Path(module_string).exists():
        raise FileNotFoundError(f"Module file not found: {module_string}")


class FilteredReceiver:
    """Helper class to receive messages with filtering."""

    def __init__(
        self, queue: CommunicationChannel, filter_func: Callable[[dict[str, Any]], bool]
    ) -> None:
        self.queue = queue
        self.filter_func = filter_func

    def receive(self, timeout: float | None = None) -> dict[str, Any]:
        """Receive a message that matches the filter criteria."""
        start_time = time.monotonic()
        while timeout is None or (time.monotonic() - start_time) < timeout:
            if not self.queue.empty():
                message = self.queue.receive()
                if self.filter_func(message):
                    if not isinstance(message, dict):
                        raise ValueError("Message is not a dictionary")
                    return message
            time.sleep(0.01)
        raise TimeoutError("Timeout waiting for matching message")
