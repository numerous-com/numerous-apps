"""Main entry point for multi-app deployment.

This demonstrates combining multiple Numerous apps into a single server:
- /public - Public app (no authentication)
- /admin - Admin app (database authentication required)
"""

import sys
from pathlib import Path

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from numerous.apps import combine_apps

# Import the individual apps
from public_app.app import app as public_app
from admin_app.app import app as admin_app


# Combine apps into a single server
main_app = combine_apps(
    apps={
        "/public": public_app,
        "/admin": admin_app,
    },
    root_redirect="/public",
    title="Multi-App Demo",
)


if __name__ == "__main__":
    import uvicorn

    print("=" * 60)
    print("Multi-App Demo Server")
    print("=" * 60)
    print("Available apps:")
    print("  - http://127.0.0.1:8000/public  (No auth required)")
    print("  - http://127.0.0.1:8000/admin   (Login: admin/admin123)")
    print("=" * 60)

    uvicorn.run(main_app, host="127.0.0.1", port=8000)

