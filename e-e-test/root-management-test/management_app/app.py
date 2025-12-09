"""Management app module - requires database authentication."""

from typing import Any

import numerous.widgets as wi
from numerous.apps import create_app
from numerous.apps.auth.providers.database_auth import DatabaseAuthProvider
from pathlib import Path


def run_app() -> dict[str, Any]:
    """Create the management app widgets."""
    total_responses = wi.Number(default=150, label="Total Responses:", fit_to_content=True)

    def on_refresh(event: dict[str, Any]) -> None:  # noqa: ARG001
        total_responses.value += 5

    refresh_btn = wi.Button(label="Refresh Data", on_click=on_refresh)

    return {
        "total_responses": total_responses,
        "refresh_btn": refresh_btn,
    }


# Set up database authentication provider
auth_provider = DatabaseAuthProvider(
    database_url="sqlite+aiosqlite:///./management_auth.db",
    jwt_secret="management-dev-secret-key-change-in-production",
)

# Create the app with path prefix and auth
app = create_app(
    template="index.html.j2",
    dev=True,
    path_prefix="/management",
    app_generator=run_app,
    auth_provider=auth_provider,
    base_dir=Path(__file__).parent,
)


# Create default admin user if not exists (using startup event)
@app.on_event("startup")
async def setup_default_users() -> None:
    """Create default users for development."""
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

    uvicorn.run(app, host="127.0.0.1", port=8000)

