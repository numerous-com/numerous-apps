import logging
import os
import multiprocessing
import time

import pytest
from fastapi.testclient import TestClient
from traitlets import Unicode
from unittest.mock import patch

from numerous.apps.app_server import AnyWidget, create_app
from numerous.apps.communication import MultiProcessExecutionManager
from numerous.apps.models import (
    TraitValue, 
    SetTraitValue,
    ActionRequestMessage,
    ActionResponseMessage
)
from numerous.apps.session_management import GlobalSessionManager, SessionId, SessionManager


@pytest.fixture(scope="session")
def test_dirs(tmp_path_factory):
    # Create temporary directories for testing
    base_dir = tmp_path_factory.mktemp("test_app")
    static_dir = base_dir / "static"
    templates_dir = base_dir / "templates"

    # Create required directories
    static_dir.mkdir(exist_ok=True)
    templates_dir.mkdir(exist_ok=True)

    # Create a basic template file
    with open(templates_dir / "base.html.j2", "w") as f:
        f.write(
            """
        <!DOCTYPE html>
        <html>
        <body>
            {{ test_widget }}
        </body>
        </html>
        """
        )

    # Create the error template file
    with open(templates_dir / "error.html.j2", "w") as f:
        f.write(
            """
        <!DOCTYPE html>
        <html>
        <body>
            <h1>{{ error_title }}</h1>
            <p>{{ error_message }}</p>
        </body>
        </html>
        """
        )

    # Create the error modal template
    with open(templates_dir / "error_modal.html.j2", "w") as f:
        f.write(
            """
        <div id="error-modal" class="modal">
            <div class="modal-content">
                <h2>Error</h2>
                <p id="error-message"></p>
            </div>
        </div>
        """
        )

    # Change to the test directory for the duration of the tests
    original_dir = os.getcwd()
    os.chdir(str(base_dir))

    yield base_dir

    # Cleanup: Change back to original directory
    os.chdir(original_dir)


# Define the widget class at module level
class TestWidgetWithTrait(AnyWidget):
    # Define the trait using traitlets
    value = Unicode("test").tag(sync=True)

    def __init__(self):
        super().__init__()
        self.module = "test-widget"
        self.html = "<div>Test Widget</div>"
        
    def traits(self, **kwargs):
        # Handle sync parameter and return all traits
        base_traits = super().traits(**kwargs)
        # Don't add our own traits - they're already defined at class level
        return base_traits


class TestWidgetWithAction(AnyWidget):
    """Test widget with an action."""
    value = Unicode("test").tag(sync=True)
    
    def __init__(self):
        super().__init__()
        self.module = "test-widget"
        self.html = "<div>Test Widget</div>"
    
    def test_action(self, arg1, kwarg1=None):
        """Test action method."""
        return f"Executed with {arg1} and {kwarg1}"
    
    def traits(self, **kwargs):
        # Handle sync parameter and return all traits
        base_traits = super().traits(**kwargs)
        # Don't add our own traits - they're already defined at class level
        return base_traits
    
    # Mark as action (simulating the @action decorator)
    #test_action._is_action = True

@pytest.fixture
def test_widget():
    return TestWidgetWithTrait()


def app_generator():
    # Create a widget class with an action
    

    # Return both the test widget and the original TestWidgetWithTrait
    return {
        "test_widget": TestWidgetWithAction(),
        "test_widget_with_trait": TestWidgetWithTrait()
    }


@pytest.fixture
def app(test_dirs):
    from numerous.apps.app_server import templates  # Import templates object
    import numerous.apps.server
    import numerous.apps.app_server

    # Add the test templates directory to Jinja2's search path
    templates.env.loader.searchpath.append(str(test_dirs / "templates"))

    app = create_app(
        template="base.html.j2",
        dev=True,
        app_generator=app_generator,
        allow_threaded=True,
    )
    
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


def test_home_endpoint(client, test_dirs):
    response = client.get("/")
    if response.status_code != 200:
        print("Error response:", response.text)
    assert response.status_code == 200
    assert 'id="test_widget"' in response.text
    assert '<script src="/numerous.js"></script>' in response.text


def test_get_widgets_endpoint(client, test_dirs):
    response = client.get("/api/widgets")
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert "widgets" in data


def test_numerous_js_endpoint(client, test_dirs):
    response = client.get("/numerous.js")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/javascript"


def test_websocket_endpoint(client, test_dirs):
    with client.websocket_connect("/ws/test-client/test-session") as websocket:
        # Just test that we can connect without errors
        data = websocket.receive_json()  # Wait for initial message
        assert isinstance(data, dict)  # Verify we got a valid response


def test_template_with_unknown_variables(client, test_dirs):
    # Create a template with undefined variables
    with open(test_dirs / "templates" / "bad.html.j2", "w") as f:
        f.write(
            """
        <!DOCTYPE html>
        <html><body>{{ undefined_var }}</body></html>
        """
        )

    app = create_app(template="bad.html.j2", dev=True, app_generator=app_generator)

    response = client.get("/")
    assert response.status_code == 500
    assert "Template Error" in response.text


def test_missing_widget_warning(client, test_dirs, caplog):
    # Create a template without the widget placeholder
    with open(test_dirs / "templates" / "missing.html.j2", "w") as f:
        f.write(
            """
        <!DOCTYPE html>
        <html><body>No widget here</body></html>
        """
        )


    with caplog.at_level(logging.WARNING):
        response = client.get("/")
        assert "widgets will not be displayed" in caplog.text


def test_websocket_error_in_dev_mode(client, test_dirs):


    with client.websocket_connect("/ws/test-client/test-session") as websocket:
        # Test error handling in dev mode
        data = websocket.receive_json()
        assert isinstance(data, dict)


@pytest.fixture(scope="session")
async def global_session_manager():
    """Create and start a global session manager for testing."""
    from numerous.apps.session_management import GlobalSessionManager
    
    # Create a new global session manager with shorter timeouts for testing
    manager = GlobalSessionManager(
        session_timeout=30.0,  # 30 seconds timeout
        cleanup_interval=5.0,  # Check every 5 seconds
    )
    
    # Start the cleanup task
    await manager.start_cleanup_task()
    
    yield manager
    
    # Cleanup after tests
    await manager.shutdown()

def test_widget_collection_from_locals(test_dirs):
    """Test that widgets are collected from locals when not explicitly provided."""
    # Create widgets in local scope
    test_widget1 = AnyWidget()
    test_widget1.module = "test-widget-1"
    test_widget1.html = "<div>Test Widget 1</div>"

    test_widget2 = AnyWidget()
    test_widget2.module = "test-widget-2"
    test_widget2.html = "<div>Test Widget 2</div>"

    # Create template with both widgets
    with open(test_dirs / "templates" / "two_widgets.html.j2", "w") as f:
        f.write(
            """
        <!DOCTYPE html>
        <html>
        <body>
            {{ test_widget1 }}
            {{ test_widget2 }}
        </body>
        </html>
        """
        )

    # Create app without explicitly providing widgets
    app = create_app(
        template="two_widgets.html.j2",
        dev=True,
        app_generator=None,
    )

    # Verify both widgets were collected
    assert "test_widget1" in app.widgets
    assert "test_widget2" in app.widgets


def test_describe_app_endpoint(client):
    """Test the /api/describe endpoint."""
    response = client.get("/api/describe")
    assert response.status_code == 200
    data = response.json()
    
    # Verify the structure of the response
    assert "app_info" in data
    assert "template" in data
    assert "widgets" in data
    
    # Verify app_info contents
    assert "dev_mode" in data["app_info"]
    assert "base_dir" in data["app_info"]
    assert "module_path" in data["app_info"]


def test_get_trait_value(client):
    """Test getting a trait value from a widget."""
    # First get a valid session ID
    session_response = client.get("/api/widgets")
    session_id = session_response.json()["session_id"]
    
    response = client.get(
        f"/api/widgets/test_widget/traits/value?session_id={session_id}"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["widget_id"] == "test_widget"
    assert data["trait"] == "value"
    assert "value" in data


def test_set_trait_value(client):
    """Test setting a trait value on a widget."""
    # First get a valid session ID
    session_response = client.get("/api/widgets")

 
    session_id = session_response.json()["session_id"]
   
    trait_value = SetTraitValue(value="new_test_value")
    response = client.put(
        f"/api/widgets/test_widget/traits/value?session_id={session_id}",
        json=trait_value.model_dump()
    )
    assert response.status_code == 200
    data = response.json()
    assert data["widget_id"] == "test_widget"
    assert data["trait"] == "value"
    assert data["value"] == "new_test_value"


def _test_execute_widget_action(client):
    """Test executing an action on a widget."""
    # First get a valid session ID
    session_response = client.get("/api/widgets")
    session_id = session_response.json()["session_id"]
    
    # Wait for the execution manager to be ready by polling the widget state
    max_retries = 10
    retry_delay = 0.2
    
    for _ in range(max_retries):
        # Try to get widget state
        response = client.get(f"/api/widgets/test_widget/traits/value?session_id={session_id}")
        if response.status_code == 200:
            break
        time.sleep(retry_delay)
    else:
        pytest.fail("Execution manager failed to initialize")
    
    # Set trait value
    trait_value = SetTraitValue(value="new_test_value")
    response = client.put(
        f"/api/widgets/test_widget/traits/value?session_id={session_id}",
        json=trait_value.model_dump()
    )
    assert response.status_code == 200
    
    # Test valid action
    response = client.post(
        f"/api/widgets/test_widget/actions/test_action?session_id={session_id}",
        json={"args": ["test_arg"], "kwargs": {"kwarg1": "test_kwarg"}}
    )
    assert response.status_code == 200
    assert "Executed with test_arg and test_kwarg" in response.json()

def _test_invalid_widget_action(client):
    """Test error handling for invalid widget actions."""
    # Get session ID
    session_response = client.get("/api/widgets")
    session_id = session_response.json()["session_id"]

    # Test non-existent widget
    response = client.post(
        f"/api/widgets/non_existent/actions/test_action?session_id={session_id}",
        json={"args": [], "kwargs": {}}
    )
    assert response.status_code == 404

    # Test non-existent action
    response = client.post(
        f"/api/widgets/test_widget/actions/non_existent?session_id={session_id}",
        json={"args": [], "kwargs": {}}
    )
    assert response.status_code == 404
