#!/usr/bin/env python3

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

def copy_template(destination_path: Path) -> None:
    """
    Copy template directory to destination
    """
    if destination_path.exists():
            print("Skipping copy...")
            return

    try:
        template_path = Path(__file__).parent / "bootstrap_app"
        shutil.copytree(template_path, destination_path)
        print(f"Created new project at: {destination_path}")
    except Exception as e:
        print(f"Error copying template: {e}")
        sys.exit(1)

def install_requirements(project_path: Path) -> None:
    """
    Install requirements from requirements.txt if it exists
    """
    requirements_file = project_path / "requirements.txt"
    
    if not requirements_file.exists():
        print("No requirements.txt found, skipping dependency installation")
        return

    print("Installing dependencies from requirements.txt...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(requirements_file)], check=True)
        print("Dependencies installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"Error installing dependencies: {e}")
        sys.exit(1)

def run_app(project_path: Path) -> None:
    """
    Run the app
    """
    subprocess.run([sys.executable, "app.py"], cwd=project_path)

def main():
    parser = argparse.ArgumentParser(description="Bootstrap a new app project from our template")
    parser.add_argument("project_name", help="Name of the new project")
    
    parser.add_argument(
        "--skip-deps",
        action="store_true",
        help="Skip installing dependencies"
    )

    parser.add_argument(
        "--run-skip",
        action="store_true",
        help="Skip running the app after creation"
    )

    args = parser.parse_args()

    # Convert paths to Path objects

    project_path = Path(args.project_name)

    # Copy template to new project directory
    copy_template(project_path)

    # Install dependencies unless --skip-deps is specified
    if not args.skip_deps:
        install_requirements(project_path)

    print(f"\nProject '{args.project_name}' has been created successfully!")

    if not args.run_skip:
        run_app(project_path)

if __name__ == "__main__":
    main()
