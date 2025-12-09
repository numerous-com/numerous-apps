"""Main entry point for root + management multi-app deployment.

This demonstrates combining a root app and management app:
- Root app: Accessible at / - no authentication required
- Management app: Accessible at /management - requires database authentication

This test case specifically reproduces the issue where WebSocket connections
fail in the second mounted app.
"""

import sys
from pathlib import Path

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from numerous.apps import combine_apps

# Import the individual apps
from root_app.app import app as root_app
from management_app.app import app as management_app


# Combine apps into a single server
# IMPORTANT: Both apps use path_prefix explicitly to trigger factory mode
main_app = combine_apps(
    apps={
        "": root_app,  # Root app at ""
        "/management": management_app,  # Management app at "/management"
    },
    root_redirect=None,
    title="Survey + Management Platform",
)


# Set up admin users on combined app startup
@main_app.on_event("startup")
async def setup_admin_users() -> None:
    """Create default admin user for the management app."""
    from management_app.app import auth_provider
    from numerous.apps.auth.exceptions import UserExistsError
    from numerous.apps.auth.models import CreateUserRequest

    try:
        await auth_provider.create_user(
            CreateUserRequest(
                username="admin",
                password="admin123",
                is_admin=True,
            )
        )
        print("Created default admin user: admin / admin123")
    except UserExistsError:
        pass  # User already exists


if __name__ == "__main__":
    import uvicorn

    print("=" * 60)
    print("Survey + Management Multi-App Server")
    print("=" * 60)
    print("Available apps:")
    print("  - http://127.0.0.1:8000/         (Public survey - no auth)")
    print("  - http://127.0.0.1:8000/management (Admin panel - login: admin/admin123)")
    print("=" * 60)

    uvicorn.run(main_app, host="127.0.0.1", port=8000)

