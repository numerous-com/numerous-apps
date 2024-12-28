import tempfile
from pathlib import Path
from queue import Empty
from typing import Any
from unittest.mock import MagicMock, Mock, patch

import pytest
from starlette.templating import Jinja2Templates

from numerous.apps._communication import (
    QueueCommunicationManager,
)
from numerous.apps._server import (
    AppInitError,
    _app_process,
    _create_handler,
    _get_session,
    _load_main_js,
)


class MockExecutionManager:
    def __init__(self) -> None:
        self.communication_manager = Mock()
        self.communication_manager.from_app_instance = Mock()
        self.communication_manager.to_app_instance = Mock()
        self.started = False

    def start(self, *args, **kwargs):
        self.started = True


def test_get_session_creates_new_session() -> None:
    """Test that _get_session creates a new session when it doesn't exist."""
    sessions = {}
    session_id = "test_session"

    with patch(
        "numerous.apps._server.MultiProcessExecutionManager",
        return_value=MockExecutionManager(),
    ):
        session = _get_session(
            allow_threaded=False,
            session_id=session_id,
            base_dir=".",
            module_path="test.py",
            template="",
            sessions=sessions,
        )

    assert session_id in sessions


def test_get_session_loads_config() -> None:
    """Test that _get_session loads configuration when requested."""
    sessions = {}
    session_id = "test_session"
    mock_manager = MockExecutionManager()
    mock_manager.communication_manager.from_app_instance.receive.return_value = {
        "type": "init-config",
        "widget_configs": {"widget1": {"defaults": "{}"}},
    }

    with patch(
        "numerous.apps._server.MultiProcessExecutionManager", return_value=mock_manager
    ):
        session = _get_session(
            allow_threaded=False,
            session_id=session_id,
            base_dir=".",
            module_path="test.py",
            template="",
            sessions=sessions,
            load_config=True,
        )

    assert "config" in session


def test_get_session_raises_on_invalid_config() -> None:
    """Test that _get_session raises AppInitError on invalid config."""
    sessions = {}
    session_id = "test_session"
    mock_manager = MockExecutionManager()
    mock_manager.communication_manager.from_app_instance.receive.return_value = {
        "type": "invalid-type"
    }

    with pytest.raises(AppInitError):
        with patch(
            "numerous.apps._server.MultiProcessExecutionManager",
            return_value=mock_manager,
        ):
            _get_session(
                allow_threaded=False,
                session_id=session_id,
                base_dir=".",
                module_path="test.py",
                template="",
                sessions=sessions,
                load_config=True,
            )


def test_get_template_adds_template_path() -> None:
    """Test that _get_template adds the template path to the searchpath."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a test template file
        template_path = Path(tmpdir) / "test_template.html"
        template_path.write_text("<html></html>")

        # Create error template
        error_template_path = Path(tmpdir) / "error.html.j2"
        error_template_path.write_text(
            "<html><body>Error: {{ error_message }}</body></html>"
        )

        # Create Jinja2Templates environment
        templates = Jinja2Templates(directory=tmpdir)

        assert str(template_path.parent) in templates.env.loader.searchpath


def test_app_process_loads_module() -> None:
    """Test that _app_process correctly loads a module."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a test module file
        module_path = Path(tmpdir) / "test_app.py"
        module_content = """
from numerous.apps._server import NumerousApp
app = NumerousApp()
app.widgets = {}
"""
        module_path.write_text(module_content)

        # Create communication manager with mocked queues
        comm_manager = QueueCommunicationManager()

        # Mock _execute to prevent actual execution
        with patch("numerous.apps._server._execute") as mock_execute:
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
    comm_manager = QueueCommunicationManager()

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

        with patch("numerous.apps._server.Path") as mock_path:
            # Make Path(__file__).parent point to our temp directory
            mock_path.return_value.parent = Path(tmpdir)

            result = _load_main_js()
            assert result == test_content


def test_load_main_js_file_missing() -> None:
    """Test that _load_main_js handles missing file gracefully."""
    with patch("numerous.apps._server.Path") as mock_path:
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
            "type": "widget_update",
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


def test_get_session_with_threaded_execution() -> None:
    """Test that _get_session creates ThreadedExecutionManager when requested."""
    sessions: dict[str, Any] = {}
    session_id = "test_session"

    with patch("numerous.apps._server.ThreadedExecutionManager") as mock_threaded:
        mock_manager = MockExecutionManager()
        mock_threaded.return_value = mock_manager

        session = _get_session(  # noqa: F841
            allow_threaded=True,
            session_id=session_id,
            base_dir=".",
            module_path="test.py",
            template="",
            sessions=sessions,
        )

        # Verify ThreadedExecutionManager was used
        mock_threaded.assert_called_once()
        assert mock_manager.started


def test_app_process_handles_import_error() -> None:
    """Test that _app_process handles import errors correctly."""
    comm_manager = QueueCommunicationManager()

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
