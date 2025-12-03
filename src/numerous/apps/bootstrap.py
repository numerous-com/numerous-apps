#!/usr/bin/env python3
"""Bootstrap a new app project from our template."""

import argparse
import json
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path


# Set up basic logging configuration
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Package directory for internal templates and static files
PACKAGE_DIR = Path(__file__).parent


def copy_template(destination_path: Path) -> None:
    """Copy template directory to destination."""
    if destination_path.exists():
        logging.info("Skipping copy...")
        return

    try:
        template_path = Path(__file__).parent / "bootstrap_app"
        shutil.copytree(template_path, destination_path)
        logging.info(f"Created new project at: {destination_path}")
    except Exception:
        logging.exception("Error copying template.")
        sys.exit(1)


def export_templates(project_path: Path) -> None:
    """
    Export internal templates to the project directory for customization.

    Copies the internal Jinja2 templates (login, error pages, splash screen, etc.)
    and static CSS files to the project directory so developers can customize them.

    Args:
        project_path: Path to the project directory where templates will be exported.

    """
    templates_source = PACKAGE_DIR / "templates"
    templates_dest = project_path / "templates"
    static_css_source = PACKAGE_DIR / "static" / "css"
    static_css_dest = project_path / "static" / "css"

    # Export template files
    if templates_source.exists():
        templates_dest.mkdir(parents=True, exist_ok=True)
        for template_file in templates_source.glob("*.j2"):
            dest_file = templates_dest / template_file.name
            if dest_file.exists():
                logging.info(f"Template already exists, skipping: {template_file.name}")
            else:
                shutil.copy2(template_file, dest_file)
                logging.info(f"Exported template: {template_file.name}")

    # Export static CSS files (numerous-base.css)
    if static_css_source.exists():
        static_css_dest.mkdir(parents=True, exist_ok=True)
        for css_file in static_css_source.glob("*.css"):
            dest_file = static_css_dest / css_file.name
            if dest_file.exists():
                logging.info(f"CSS file already exists, skipping: {css_file.name}")
            else:
                shutil.copy2(css_file, dest_file)
                logging.info(f"Exported CSS file: {css_file.name}")

    logging.info(
        f"Templates exported to {templates_dest}. "
        "You can now customize these files for your app."
    )


def setup_auth(project_path: Path) -> None:
    """
    Set up authentication for the app.

    Modifies app.py to include EnvAuthProvider and sets up default users.
    """
    app_file = project_path / "app.py"

    if not app_file.exists():
        logging.error("app.py not found in project directory")
        return

    # Read the current app.py content
    content = app_file.read_text()

    # Add auth imports
    auth_imports = """from numerous.apps.auth.providers.env_auth import EnvAuthProvider
"""

    # Insert auth imports after the existing imports
    if "from numerous.apps import create_app" in content:
        content = content.replace(
            "from numerous.apps import create_app",
            "from numerous.apps import create_app\n" + auth_imports,
        )

    # Modify create_app call to include auth_provider
    old_create_app = (
        'app = create_app(template="index.html.j2", dev=True, app_generator=run_app)'
    )
    new_create_app = """# Set up authentication provider
auth_provider = EnvAuthProvider()

app = create_app(
    template="index.html.j2",
    dev=True,
    app_generator=run_app,
    auth_provider=auth_provider,
)"""

    content = content.replace(old_create_app, new_create_app)

    # Write back the modified content
    app_file.write_text(content)
    logging.info("Added authentication to app.py")

    # Create a .env.example file with auth configuration
    env_example = project_path / ".env.example"
    env_content = """# Authentication Configuration
# Copy this file to .env and modify the values

# JWT secret key (generate a secure random string for production)
NUMEROUS_JWT_SECRET=your-secure-secret-key-here

# Users configuration (JSON array)
# Each user can have: username, password, roles (array), is_admin (bool)
NUMEROUS_AUTH_USERS='[{"username": "admin", "password": "admin123", "is_admin": true}]'
"""
    env_example.write_text(env_content)
    logging.info("Created .env.example with auth configuration")

    # Create a .env file with default development values
    env_file = project_path / ".env"
    env_dev_content = """# Development Authentication Configuration
NUMEROUS_JWT_SECRET=dev-secret-key-change-in-production
NUMEROUS_AUTH_USERS='[{"username": "admin", "password": "admin123", "is_admin": true}]'
"""
    env_file.write_text(env_dev_content)
    logging.info("Created .env with default development credentials")

    # Add python-dotenv to requirements.txt if not present
    req_file = project_path / "requirements.txt"
    if req_file.exists():
        req_content = req_file.read_text()
        if "python-dotenv" not in req_content:
            req_content += "\npython-dotenv\n"
            req_file.write_text(req_content)

    # Modify app.py to load .env file
    content = app_file.read_text()
    dotenv_import = """try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not installed, using environment variables directly

"""
    # Add dotenv loading at the top after docstring
    if "from dotenv import load_dotenv" not in content:
        # Insert after the module docstring
        docstring_parts = 3
        if '"""' in content:
            parts = content.split('"""', 2)
            if len(parts) >= docstring_parts:
                content = (
                    parts[0]
                    + '"""'
                    + parts[1]
                    + '"""'
                    + "\n\n"
                    + dotenv_import
                    + parts[2]
                )
        app_file.write_text(content)
        logging.info("Added dotenv loading to app.py")


def setup_db_auth(project_path: Path) -> None:
    """
    Set up database authentication for the app.

    Modifies app.py to include DatabaseAuthProvider with SQLite.
    """
    app_file = project_path / "app.py"

    if not app_file.exists():
        logging.error("app.py not found in project directory")
        return

    # Read the current app.py content
    content = app_file.read_text()

    # Add auth imports
    auth_imports = (
        "from numerous.apps.auth.providers.database_auth "
        "import DatabaseAuthProvider\n"
    )

    # Insert auth imports after the existing imports
    if "from numerous.apps import create_app" in content:
        content = content.replace(
            "from numerous.apps import create_app",
            "from numerous.apps import create_app\n" + auth_imports,
        )

    # Modify create_app call to include auth_provider
    old_create_app = (
        'app = create_app(template="index.html.j2", dev=True, app_generator=run_app)'
    )
    new_create_app = '''# Set up database authentication provider
auth_provider = DatabaseAuthProvider(
    database_url="sqlite+aiosqlite:///./app_auth.db",
    jwt_secret="dev-secret-key-change-in-production",
)

app = create_app(
    template="index.html.j2",
    dev=True,
    app_generator=run_app,
    auth_provider=auth_provider,
)

# Create default admin user if not exists (using startup event)
@app.on_event("startup")
async def setup_default_users():
    """Create default users for development."""
    from numerous.apps.auth.models import CreateUserRequest
    from numerous.apps.auth.exceptions import UserExistsError

    try:
        await auth_provider.create_user(CreateUserRequest(
            username="admin",
            password="admin123",
            is_admin=True,
        ))
        print("Created default admin user: admin / admin123")
    except UserExistsError:
        pass  # User already exists

    try:
        await auth_provider.create_user(CreateUserRequest(
            username="user",
            password="user1234",
            roles=["viewer"],
        ))
        print("Created default user: user / user1234")
    except UserExistsError:
        pass  # User already exists'''

    content = content.replace(old_create_app, new_create_app)

    # Write back the modified content
    app_file.write_text(content)
    logging.info("Added database authentication to app.py")

    # Add database auth dependencies to requirements.txt
    req_file = project_path / "requirements.txt"
    if req_file.exists():
        req_content = req_file.read_text()
        if "sqlalchemy" not in req_content.lower():
            req_content += (
                "\nsqlalchemy[asyncio]>=2.0.0\naiosqlite>=0.19.0\nbcrypt>=4.1.0\n"
            )
            req_file.write_text(req_content)
            logging.info("Added database auth dependencies to requirements.txt")


def install_requirements(project_path: Path) -> None:
    """Install requirements from requirements.txt if it exists."""
    requirements_file = project_path / "requirements.txt"

    if not requirements_file.exists():
        logging.info("No requirements.txt found, skipping dependency installation")
        return

    logging.info("Installing dependencies from requirements.txt...")
    try:
        subprocess.run(  # noqa: S603
            [sys.executable, "-m", "pip", "install", "-r", str(requirements_file)],
            check=True,
        )
        logging.info("Dependencies installed successfully")
    except subprocess.CalledProcessError:
        logging.exception("Error installing dependencies.")
        sys.exit(1)


def run_app(
    project_path: Path,
    port: int = 8000,
    host: str = "127.0.0.1",
    env: dict[str, str] | None = None,
) -> None:
    """Run the app."""
    run_env = os.environ.copy()
    if env:
        run_env.update(env)

    # Use sys.executable to ensure we run uvicorn from the same Python
    # environment that's running this script (important for venvs)
    subprocess.run(  # noqa: S603
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app:app",
            "--port",
            str(port),
            "--host",
            str(host),
        ],
        cwd=project_path,
        check=False,
        env=run_env,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bootstrap a new app project from our template"
    )
    parser.add_argument("project_name", help="Name of the new project")
    parser.add_argument(
        "--skip-deps", action="store_true", help="Skip installing dependencies"
    )
    parser.add_argument(
        "--run-skip", action="store_true", help="Skip running the app after creation"
    )
    parser.add_argument(
        "--port", type=int, default=8000, help="Port to run the server on"
    )
    parser.add_argument(
        "--host", type=str, default="127.0.0.1", help="Host to run the server on"
    )
    parser.add_argument(
        "--with-auth",
        action="store_true",
        help="Enable authentication with EnvAuthProvider",
    )
    parser.add_argument(
        "--with-db-auth",
        action="store_true",
        help="Enable authentication with DatabaseAuthProvider (SQLite)",
    )
    parser.add_argument(
        "--export-templates",
        action="store_true",
        help="Export internal templates (login, error pages, etc.) for customization",
    )

    args = parser.parse_args()

    project_path = Path(args.project_name)

    # Copy template to new project directory
    copy_template(project_path)

    # Set up authentication if requested
    if args.with_auth and args.with_db_auth:
        logging.error("Cannot use both --with-auth and --with-db-auth")
        sys.exit(1)

    if args.with_auth:
        setup_auth(project_path)
    elif args.with_db_auth:
        setup_db_auth(project_path)

    # Export templates if requested
    if args.export_templates:
        export_templates(project_path)

    # Install dependencies unless --skip-deps is specified
    if not args.skip_deps:
        install_requirements(project_path)

    if not args.run_skip:
        # Pass auth environment variables if auth is enabled
        env = None
        if args.with_auth:
            env = {
                "NUMEROUS_JWT_SECRET": "dev-secret-key-change-in-production",
                "NUMEROUS_AUTH_USERS": json.dumps(
                    [
                        {"username": "admin", "password": "admin123", "is_admin": True},
                        {
                            "username": "user",
                            "password": "user123",
                            "roles": ["viewer"],
                        },
                    ]
                ),
            }
        elif args.with_db_auth:
            env = {
                "NUMEROUS_JWT_SECRET": "dev-secret-key-change-in-production",
            }
        run_app(project_path, args.port, args.host, env)


if __name__ == "__main__":
    main()
