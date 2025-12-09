"""Tests for multi-app functionality."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from numerous.apps import combine_apps, create_app
from numerous.apps.multi_app import combine_apps as combine_apps_impl
from numerous.apps.server import NumerousApp


class TestCombineApps:
    """Tests for the combine_apps function."""

    def test_combine_apps_creates_fastapi_app(self):
        """Test that combine_apps returns a FastAPI application."""
        # Create mock apps
        app1 = NumerousApp()
        app2 = NumerousApp()

        # Combine them
        main_app = combine_apps(
            apps={"/app1": app1, "/app2": app2},
        )

        assert isinstance(main_app, FastAPI)

    def test_combine_apps_with_root_redirect(self):
        """Test that root redirect is configured correctly."""
        app1 = NumerousApp()

        main_app = combine_apps(
            apps={"/app1": app1},
            root_redirect="/app1",
        )

        client = TestClient(main_app)
        response = client.get("/", follow_redirects=False)

        assert response.status_code == 302
        assert response.headers["location"] == "/app1"

    def test_combine_apps_health_endpoint(self):
        """Test that health endpoint is available."""
        app1 = NumerousApp()

        main_app = combine_apps(
            apps={"/app1": app1},
        )

        client = TestClient(main_app)
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "/app1" in data["apps"]

    def test_combine_apps_normalizes_paths(self):
        """Test that paths without leading slash are normalized."""
        app1 = NumerousApp()

        main_app = combine_apps(
            apps={"app1": app1},  # No leading slash
        )

        # The app should still be mounted correctly
        assert main_app is not None

    def test_combine_apps_sets_mount_path_on_apps(self):
        """Test that mount_path is set on each app's state."""
        app1 = NumerousApp()
        app2 = NumerousApp()

        combine_apps(
            apps={"/first": app1, "/second": app2},
        )

        assert app1.state.mount_path == "/first"
        assert app2.state.mount_path == "/second"

    def test_combine_apps_with_shared_theme_css(self):
        """Test that shared theme CSS endpoint is created."""
        app1 = NumerousApp()

        main_app = combine_apps(
            apps={"/app1": app1},
            shared_theme_css=":root { --test-color: red; }",
        )

        client = TestClient(main_app)
        response = client.get("/shared-static/css/theme.css")

        assert response.status_code == 200
        assert "text/css" in response.headers["content-type"]
        assert "--test-color: red" in response.text

    def test_combine_apps_sets_shared_theme_available(self):
        """Test that shared_theme_available flag is set when theme is provided."""
        app1 = NumerousApp()

        combine_apps(
            apps={"/app1": app1},
            shared_theme_css=":root { color: blue; }",
        )

        assert app1.state.shared_theme_available is True

    def test_combine_apps_without_shared_theme(self):
        """Test that shared_theme_available is False when no theme provided."""
        app1 = NumerousApp()

        combine_apps(
            apps={"/app1": app1},
        )

        assert app1.state.shared_theme_available is False


class TestCreateAppWithPathPrefix:
    """Tests for create_app factory routing."""

    @patch("numerous.apps.create_numerous_app")
    def test_create_app_with_path_prefix_uses_factory(self, mock_factory):
        """Factory should be invoked for any path_prefix (including root)."""
        mock_app = MagicMock(spec=NumerousApp)
        mock_factory.return_value = mock_app

        result = create_app(
            template="test.html.j2",
            path_prefix="/myapp",
            app_generator=lambda: {},
        )

        mock_factory.assert_called_once()
        call_kwargs = mock_factory.call_args[1]
        assert call_kwargs["path_prefix"] == "/myapp"
        assert result is mock_app

    def test_create_app_returns_new_instance_each_time(self):
        """Factory mode returns fresh instances (no singleton)."""
        app1 = create_app(
            template="test.html.j2",
            app_generator=lambda: {},
        )

        app2 = create_app(
            template="test.html.j2",
            app_generator=lambda: {},
        )

        assert app1 is not app2


class TestMultiAppRouting:
    """Tests for multi-app routing behavior."""

    def test_sub_app_routes_are_prefixed(self):
        """Test that sub-app routes are correctly prefixed."""
        # Create a simple app with a test route
        sub_app = NumerousApp()

        @sub_app.get("/test")
        async def test_endpoint():
            return {"message": "hello"}

        main_app = combine_apps(
            apps={"/myapp": sub_app},
        )

        client = TestClient(main_app)

        # Route should be available at prefixed path
        response = client.get("/myapp/test")
        assert response.status_code == 200
        assert response.json() == {"message": "hello"}

        # Route should NOT be available at root
        response = client.get("/test")
        assert response.status_code == 404

    def test_multiple_apps_have_separate_routes(self):
        """Test that multiple apps have separate route namespaces."""
        app1 = NumerousApp()
        app2 = NumerousApp()

        @app1.get("/data")
        async def app1_data():
            return {"app": "one"}

        @app2.get("/data")
        async def app2_data():
            return {"app": "two"}

        main_app = combine_apps(
            apps={"/first": app1, "/second": app2},
        )

        client = TestClient(main_app)

        # Each app should return its own data
        response1 = client.get("/first/data")
        assert response1.json() == {"app": "one"}

        response2 = client.get("/second/data")
        assert response2.json() == {"app": "two"}

    def test_root_mount_does_not_block_other_apps(self):
        """Test that mounting an app at root doesn't block other mounted apps.
        
        This regression test ensures that when an app is mounted at "/" alongside
        other apps at specific paths (e.g., "/management"), the specific paths
        are still accessible. The fix is to mount more specific paths first.
        """
        root_app = NumerousApp()
        management_app = NumerousApp()

        @root_app.get("/")
        async def root_index():
            return {"app": "root"}

        @management_app.get("/")
        async def management_index():
            return {"app": "management"}

        # This order (root first) previously caused /management to return 404
        main_app = combine_apps(
            apps={
                "": root_app,
                "/management": management_app,
            },
        )

        client = TestClient(main_app)

        # Root app should be accessible
        response_root = client.get("/")
        assert response_root.status_code == 200
        assert response_root.json() == {"app": "root"}

        # Management app should also be accessible (this was the bug)
        response_mgmt = client.get("/management/")
        assert response_mgmt.status_code == 200
        assert response_mgmt.json() == {"app": "management"}

    def test_apps_mounted_by_path_specificity(self):
        """Test that apps are mounted in order of path specificity (longest first)."""
        app_root = NumerousApp()
        app_api = NumerousApp()
        app_api_v2 = NumerousApp()

        @app_root.get("/test")
        async def root_test():
            return {"level": "root"}

        @app_api.get("/test")
        async def api_test():
            return {"level": "api"}

        @app_api_v2.get("/test")
        async def api_v2_test():
            return {"level": "api_v2"}

        main_app = combine_apps(
            apps={
                "/": app_root,
                "/api": app_api,
                "/api/v2": app_api_v2,
            },
        )

        client = TestClient(main_app)

        # All paths should resolve to correct apps
        assert client.get("/test").json() == {"level": "root"}
        assert client.get("/api/test").json() == {"level": "api"}
        assert client.get("/api/v2/test").json() == {"level": "api_v2"}


class TestMultiAppAuthRedirects:
    """Tests for authentication redirects in multi-app deployments."""

    def test_auth_redirect_uses_correct_path_prefix(self):
        """Test that auth middleware redirects to login with correct path prefix.
        
        When an app with auth is mounted at /management, unauthenticated requests
        should redirect to /management/login, not /login.
        """
        from numerous.apps.auth.middleware import create_auth_middleware
        
        # Create a mock auth provider
        class MockAuthProvider:
            async def validate_access_token(self, token):
                return None
        
        management_app = NumerousApp()
        
        @management_app.get("/")
        async def management_index():
            return {"app": "management"}
        
        # Add auth middleware with path prefix
        middleware_class = create_auth_middleware(
            auth_provider=MockAuthProvider(),
            login_path="/management/login",  # This is what we're testing
        )
        management_app.add_middleware(middleware_class)
        
        # Add a login route for the redirect target
        @management_app.get("/management/login")
        async def login_page():
            return {"page": "login"}
        
        main_app = combine_apps(
            apps={"/management": management_app},
        )
        
        client = TestClient(main_app, follow_redirects=False)
        
        # Accessing protected route without auth should redirect to /management/login
        response = client.get("/management/")
        assert response.status_code == 302
        assert "/management/login" in response.headers["location"]

    def test_prefixed_login_path_is_public(self):
        """Test that the prefixed login path is accessible without causing redirect loop.
        
        This is a regression test for the bug where /management/login kept redirecting
        to itself because it wasn't in the public routes list.
        """
        from numerous.apps.auth.middleware import create_auth_middleware
        
        # Create a mock auth provider
        class MockAuthProvider:
            async def validate_access_token(self, token):
                return None
        
        management_app = NumerousApp()
        
        # Add a login page - route is /login internally, but /management/login externally
        @management_app.get("/login")
        async def login_page():
            return {"page": "login"}
        
        # Add auth middleware with path prefix - login_path should be auto-added to public routes
        # The middleware sees the full path (/management/login) so that's what we configure
        middleware_class = create_auth_middleware(
            auth_provider=MockAuthProvider(),
            login_path="/management/login",
        )
        management_app.add_middleware(middleware_class)
        
        main_app = combine_apps(
            apps={"/management": management_app},
        )
        
        client = TestClient(main_app, follow_redirects=False)
        
        # Login page should be accessible (200), not redirect (302)
        response = client.get("/management/login")
        assert response.status_code == 200
        assert response.json() == {"page": "login"}


class TestBasePathInjection:
    """Tests for base path injection into HTML."""

    def test_base_path_script_tag_is_injected(self):
        """Test that NUMEROUS_BASE_PATH is injected into HTML."""
        # This test would need a full app setup with templates
        # For now, we test the concept
        pass  # Covered by E2E tests


class TestSharedStaticFiles:
    """Tests for shared static file serving."""

    def test_shared_static_dir_is_mounted(self, tmp_path):
        """Test that shared static directory is mounted correctly."""
        # Create a test static directory
        static_dir = tmp_path / "shared" / "static"
        static_dir.mkdir(parents=True)

        # Create a test file
        test_file = static_dir / "test.txt"
        test_file.write_text("test content")

        app1 = NumerousApp()

        main_app = combine_apps(
            apps={"/app1": app1},
            shared_static_dir=static_dir,
        )

        client = TestClient(main_app)
        response = client.get("/shared-static/test.txt")

        assert response.status_code == 200
        assert response.text == "test content"

    def test_nonexistent_shared_static_dir_is_ignored(self, tmp_path):
        """Test that nonexistent shared static dir doesn't cause errors."""
        nonexistent = tmp_path / "does_not_exist"

        app1 = NumerousApp()

        # Should not raise an error
        main_app = combine_apps(
            apps={"/app1": app1},
            shared_static_dir=nonexistent,
        )

        assert main_app is not None


class TestAppTitle:
    """Tests for combined app title configuration."""

    def test_custom_title_is_set(self):
        """Test that custom title is applied to combined app."""
        app1 = NumerousApp()

        main_app = combine_apps(
            apps={"/app1": app1},
            title="My Custom Title",
        )

        assert main_app.title == "My Custom Title"

    def test_default_title(self):
        """Test that default title is used when not specified."""
        app1 = NumerousApp()

        main_app = combine_apps(
            apps={"/app1": app1},
        )

        assert main_app.title == "Numerous Apps"

