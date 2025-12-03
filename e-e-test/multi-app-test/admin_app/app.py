"""Admin app module - requires database authentication."""

from typing import Any

import numerous.widgets as wi
from numerous.apps import create_app
from numerous.apps.auth.providers.database_auth import DatabaseAuthProvider


def run_app() -> dict[str, Any]:
    """Create the admin app widgets."""
    admin_counter = wi.Number(default=0, label="Admin Counter:", fit_to_content=True)

    def on_admin_click(event: dict[str, Any]) -> None:  # noqa: ARG001
        admin_counter.value += 10

    admin_btn = wi.Button(label="Add 10", on_click=on_admin_click)

    admin_message = wi.Text(
        default="Welcome to the admin dashboard!", label="Admin Message:"
    )

    secret_value = wi.Number(default=42, label="Secret Value:", fit_to_content=True)

    return {
        "admin_counter": admin_counter,
        "admin_btn": admin_btn,
        "admin_message": admin_message,
        "secret_value": secret_value,
    }


# Set up database authentication provider
auth_provider = DatabaseAuthProvider(
    database_url="sqlite+aiosqlite:///./admin_auth.db",
    jwt_secret="admin-dev-secret-key-change-in-production",
)

# Create the app with path prefix and auth
app = create_app(
    template="index.html.j2",
    dev=True,
    path_prefix="/admin",
    app_generator=run_app,
    auth_provider=auth_provider,
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

    try:
        await auth_provider.create_user(
            CreateUserRequest(
                username="viewer",
                password="viewer123",
                roles=["viewer"],
            )
        )
        print("Created default viewer user: viewer / viewer123")
    except UserExistsError:
        pass  # User already exists


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)

