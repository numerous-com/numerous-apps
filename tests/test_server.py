import tempfile
from pathlib import Path
from queue import Empty
from typing import Any
from unittest.mock import MagicMock, Mock, patch
from threading import Event
from queue import Queue
import asyncio
import pytest
from starlette.templating import Jinja2Templates

from numerous.apps.communication import (
    QueueCommunicationManager,
)
from numerous.apps.server import (
    AppInitError,
    _app_process,
    _create_handler,
    _load_main_js,
)
from numerous.apps.app_factory import _get_app_session
from numerous.apps.session_management import SessionId, GlobalSessionManager


class MockCommunicationChannel:
    """Mock communication channel for testing."""
    
    def __init__(self) -> None:
        self._queue: list[dict[str, Any]] = []
        self.sent_messages: list[dict[str, Any]] = []

    def receive(self, timeout: float | None = None) -> dict[str, Any]:
        """Non-blocking receive implementation."""
        if not self._queue:
            raise Empty()
        return self._queue.pop(0)

    def receive_nowait(self) -> dict[str, Any]:
        """Non-blocking receive implementation."""
        if not self._queue:
            raise Empty()
        return self._queue.pop(0)

    def send(self, message: dict[str, Any]) -> None:
        """Send implementation."""
        self.sent_messages.append(message)

    def empty(self) -> bool:
        """Check if queue is empty."""
        return len(self._queue) == 0

    def put_message(self, message: dict[str, Any]) -> None:
        """Helper to put a message in the queue."""
        self._queue.append(message)


class MockExecutionManager:
    def __init__(self) -> None:
        self.from_app_instance = MockCommunicationChannel()
        self.to_app_instance = MockCommunicationChannel()
        self.communication_manager = Mock(
            from_app_instance=self.from_app_instance,
            to_app_instance=self.to_app_instance,
            stop_event=asyncio.Event()
        )
        self.started = False

    def start(self, *args: Any, **kwargs: Any) -> None:
        self.started = True

    async def stop(self) -> None:
        self.started = False
        self.communication_manager.stop_event.set()


@pytest.mark.asyncio
async def test_get_session_creates_new_session() -> None:
    """Test that per-app session creation works (no global manager)."""
    session_id = ""  # Empty session ID to trigger new session creation
    session_manager = GlobalSessionManager()

    with patch(
        "numerous.apps.communication.MultiProcessExecutionManager",
        return_value=MockExecutionManager(),
    ):
        session = await asyncio.wait_for(
            _get_app_session(
                session_manager=session_manager,
                allow_threaded=False,
                session_id=session_id,
                base_dir=".",
                module_path="test.py",
                template="",
            ),
            timeout=1.0,
        )
        assert session_manager.has_session(SessionId(session.session_id))


@pytest.mark.asyncio
async def test_get_session_loads_config() -> None:
    """Test that session creation loads configuration with per-app manager."""
    session_id = ""
    mock_manager = MockExecutionManager()
    session_manager = GlobalSessionManager()

    # Put the init-config message in the queue
    mock_manager.from_app_instance.put_message(
        {
            "type": "init-config",
            "widget_configs": {"widget1": {"defaults": "{}"}},
        }
    )

    with patch(
        "numerous.apps.communication.MultiProcessExecutionManager", return_value=mock_manager
    ):
        session = await asyncio.wait_for(
            _get_app_session(
                session_manager=session_manager,
                allow_threaded=False,
                session_id=session_id,
                base_dir=".",
                module_path="test.py",
                template="",
            ),
            timeout=1.0,
        )
        assert session is not None


@pytest.mark.asyncio
async def test_get_session_with_threaded_execution() -> None:
    """Test that threaded execution manager is used when requested."""
    session_id = ""
    session_manager = GlobalSessionManager()

    with patch("numerous.apps.communication.ThreadedExecutionManager") as mock_threaded:
        mock_manager = MockExecutionManager()
        mock_threaded.return_value = mock_manager

        session = await asyncio.wait_for(
            _get_app_session(
                session_manager=session_manager,
                allow_threaded=True,
                session_id=session_id,
                base_dir=".",
                module_path="test.py",
                template="",
            ),
            timeout=1.0,
        )

        # Verify ThreadedExecutionManager was used
        mock_threaded.assert_called_once()
        assert mock_manager.started
        assert session is not None


def test_app_process_loads_module() -> None:
    """Test that _app_process correctly loads a module."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a test module file
        module_path = Path(tmpdir) / "test_app.py"
        module_content = """
from numerous.apps.server import NumerousApp
app = NumerousApp()
app.widgets = {}
"""
        module_path.write_text(module_content)

        # Create communication manager with mocked queues
        comm_manager = QueueCommunicationManager(Event(), Queue(), Queue())

        # Mock _execute to prevent actual execution
        with patch("numerous.apps.server._execute") as mock_execute:
            # Run app process
            _app_process(
                session_id="test_session",
                cwd=tmpdir,
                module_string=str(module_path),
                template="",
                communication_manager=comm_manager,
            )

            # Verify _execute was called with correct arguments
            mock_execute.assert_called_once()
            args = mock_execute.call_args[0]
            assert args[0] == comm_manager  # communication_manager
            assert args[1] == {}  # widgets
            assert args[2] == ""  # template


def test_app_process_handles_missing_file() -> None:
    """Test that _app_process handles missing module file."""
    comm_manager = QueueCommunicationManager(Event(), Queue(), Queue())

    # Mock the queues with MagicMock
    comm_manager.from_app_instance = MagicMock()
    comm_manager.to_app_instance = MagicMock()

    # Configure the mock to return the error message once then raise Empty
    error_message = {
        "type": "error",
        "error_type": "FileNotFoundError",
        "message": "Module file not found: non_existent_file.py",
        "traceback": "",
    }
    comm_manager.from_app_instance.receive_nowait.side_effect = [error_message, Empty()]

    _app_process(
        session_id="test_session",
        cwd=".",
        module_string="non_existent_file.py",
        template="",
        communication_manager=comm_manager,
    )

    # The error message should be available immediately
    error_message = comm_manager.from_app_instance.receive_nowait()
    assert error_message["type"] == "error"
    assert error_message["error_type"] == "FileNotFoundError"


def test_load_main_js_file_exists() -> None:
    """Test that _load_main_js loads file content when file exists."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create mock numerous.js file
        js_dir = Path(tmpdir) / "js"
        js_dir.mkdir()
        js_file = js_dir / "numerous.js"
        test_content = "console.log('test');"
        js_file.write_text(test_content)

        with patch("numerous.apps.server.Path") as mock_path:
            # Make Path(__file__).parent point to our temp directory
            mock_path.return_value.parent = Path(tmpdir)

            result = _load_main_js()
            assert result == test_content


def test_load_main_js_file_missing() -> None:
    """Test that _load_main_js handles missing file gracefully."""
    with patch("numerous.apps.server.Path") as mock_path:
        # Make Path(__file__).parent point to a non-existent directory
        mock_path.return_value.parent = Path("/nonexistent")

        result = _load_main_js()
        assert result == ""


def test_create_handler() -> None:
    """Test that _create_handler creates appropriate event handler."""
    mock_channel = Mock()
    handler = _create_handler("test_widget", "value", mock_channel)

    # Create mock change event
    change = Mock()
    change.name = "value"
    change.new = 42

    # Call handler
    handler(change)

    # Verify correct message was sent
    mock_channel.send.assert_called_once_with(
        {
            "type": "widget-update",
            "widget_id": "test_widget",
            "property": "value",
            "value": 42,
        }
    )


def test_create_handler_ignores_clicked() -> None:
    """Test that _create_handler ignores 'clicked' events."""
    mock_channel = Mock()
    handler = _create_handler("test_widget", "clicked", mock_channel)

    # Create mock change event
    change = Mock()
    change.name = "clicked"
    change.new = True

    # Call handler
    handler(change)

    # Verify no message was sent
    mock_channel.send.assert_not_called()


def test_app_process_handles_import_error() -> None:
    """Test that _app_process handles import errors correctly."""
    comm_manager = QueueCommunicationManager(Event(), Queue(), Queue())

    # Mock the queues with MagicMock
    comm_manager.from_app_instance = MagicMock()
    comm_manager.to_app_instance = MagicMock()

    # Configure the mock to return the error message once then raise Empty
    error_message = {
        "type": "error",
        "error_type": "SyntaxError",
        "message": "invalid syntax",
        "traceback": "",
    }
    comm_manager.from_app_instance.receive_nowait.side_effect = [error_message, Empty()]

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create an invalid module file
        module_path = Path(tmpdir) / "invalid_app.py"
        module_path.write_text("this is not valid python")

        _app_process(
            session_id="test_session",
            cwd=tmpdir,
            module_string=str(module_path),
            template="",
            communication_manager=comm_manager,
        )

        # Verify error message was sent
        error_msg = comm_manager.from_app_instance.receive_nowait()
        assert error_msg["type"] == "error"
        assert "SyntaxError" in error_msg["error_type"]
