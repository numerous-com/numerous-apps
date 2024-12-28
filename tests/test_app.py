import logging
import os

import pytest
from fastapi.testclient import TestClient

from numerous.apps.app import AnyWidget, create_app


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


@pytest.fixture
def test_widget():
    widget = AnyWidget()  # Create instance first
    widget.module = "test-widget"  # Set attributes after creation
    widget.html = "<div>Test Widget</div>"
    widget.attributes = {"value": "test"}
    return widget


def app_generator():
    # This function will be called to create widgets in threaded mode
    widget = AnyWidget()  # Create instance first
    widget.module = "test-widget"  # Set attributes after creation
    widget.html = "<div>Test Widget</div>"
    widget.attributes = {"value": "test"}
    return {"test_widget": widget}


@pytest.fixture
def app(test_dirs):
    from numerous.apps.app import templates  # Import templates object

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

    app = create_app(template="missing.html.j2", dev=True, app_generator=app_generator)

    with caplog.at_level(logging.WARNING):
        response = client.get("/")
        assert "widgets will not be displayed" in caplog.text


def test_websocket_error_in_dev_mode(client, test_dirs):
    app = create_app(template="base.html.j2", dev=True, app_generator=app_generator)

    with client.websocket_connect("/ws/test-client/test-session") as websocket:
        # Test error handling in dev mode
        data = websocket.receive_json()
        assert isinstance(data, dict)
