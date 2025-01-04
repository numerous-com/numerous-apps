#!/usr/bin/env python3
"""Bootstrap a new app project from our template."""

import argparse
import logging
import shutil
import subprocess
import sys
from pathlib import Path


# Set up basic logging configuration
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


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


def run_app(project_path: Path, port: int = 8000, host: str = "127.0.0.1") -> None:
    """Run the app."""
    subprocess.run(  # noqa: S603
        ["uvicorn", "app:app", "--port", str(port), "--host", str(host)],  # noqa: S607
        cwd=project_path,
        check=False,
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

    args = parser.parse_args()

    project_path = Path(args.project_name)

    # Copy template to new project directory
    copy_template(project_path)

    # Install dependencies unless --skip-deps is specified
    if not args.skip_deps:
        install_requirements(project_path)

    if not args.run_skip:
        run_app(project_path, args.port, args.host)


if __name__ == "__main__":
    main()
