import logging
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from numerous.apps.bootstrap import (
    copy_template,
    export_templates,
    install_requirements,
    main,
    run_app,
)


@pytest.fixture
def mock_project_path():
    return Path("/fake/project/path")


def test_copy_template_when_destination_exists(mock_project_path, caplog):
    caplog.set_level(logging.INFO)
    with patch.object(Path, "exists", return_value=True):
        copy_template(mock_project_path)
        assert "Skipping copy" in caplog.text


def test_copy_template_success(mock_project_path, caplog):
    caplog.set_level(logging.INFO)
    with (
        patch.object(Path, "exists", return_value=False),
        patch("shutil.copytree") as mock_copytree,
    ):
        copy_template(mock_project_path)
        mock_copytree.assert_called_once()
        assert "Created new project" in caplog.text


def test_copy_template_failure(mock_project_path, caplog):
    caplog.set_level(logging.INFO)
    with (
        patch.object(Path, "exists", return_value=False),
        patch("shutil.copytree", side_effect=Exception("Copy failed")),
        pytest.raises(SystemExit) as exc_info,
    ):
        copy_template(mock_project_path)
    assert exc_info.value.code == 1
    assert "Error copying template." in caplog.text


def test_install_requirements_no_requirements(mock_project_path, caplog):
    caplog.set_level(logging.INFO)
    with patch.object(Path, "exists", return_value=False):
        install_requirements(mock_project_path)
        assert "No requirements.txt found" in caplog.text


def test_install_requirements_success(mock_project_path, caplog):
    caplog.set_level(logging.INFO)
    with (
        patch.object(Path, "exists", return_value=True),
        patch("subprocess.run") as mock_run,
    ):
        install_requirements(mock_project_path)
        mock_run.assert_called_once()
        assert "Dependencies installed successfully" in caplog.text


def test_install_requirements_failure(mock_project_path, caplog):
    caplog.set_level(logging.INFO)
    with (
        patch.object(Path, "exists", return_value=True),
        patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "cmd")),
        pytest.raises(SystemExit) as exc_info,
    ):
        install_requirements(mock_project_path)
    assert exc_info.value.code == 1
    assert "Error installing dependencies." in caplog.text


def test_run_app(mock_project_path):
    with patch("subprocess.run") as mock_run:
        run_app(mock_project_path)
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        # Check the command arguments
        assert call_args.kwargs["cwd"] == mock_project_path
        assert call_args.kwargs["check"] is False
        # Command should use sys.executable -m uvicorn
        cmd = call_args.args[0]
        assert "-m" in cmd
        assert "uvicorn" in cmd
        assert "app:app" in cmd
        assert "--port" in cmd
        assert "8000" in cmd
        assert "--host" in cmd
        assert "127.0.0.1" in cmd


def test_main_basic_flow(caplog):
    caplog.set_level(logging.DEBUG)
    test_args = ["script_name", "test_project"]
    with (
        patch("sys.argv", test_args),
        patch("numerous.apps.bootstrap.copy_template") as mock_copy,
        patch("numerous.apps.bootstrap.install_requirements") as mock_install,
        patch("numerous.apps.bootstrap.run_app") as mock_run,
    ):
        main()
        mock_copy.assert_called_once()
        mock_install.assert_called_once()
        mock_run.assert_called_once()


def test_main_with_skip_options(caplog):
    caplog.set_level(logging.INFO)
    test_args = ["script_name", "test_project", "--skip-deps", "--run-skip"]
    with (
        patch("sys.argv", test_args),
        patch("numerous.apps.bootstrap.copy_template") as mock_copy,
        patch("numerous.apps.bootstrap.install_requirements") as mock_install,
        patch("numerous.apps.bootstrap.run_app") as mock_run,
    ):
        main()
        mock_copy.assert_called_once()
        mock_install.assert_not_called()
        mock_run.assert_not_called()


class TestExportTemplates:
    """Tests for the export_templates function."""

    def test_export_templates_creates_directories(self, tmp_path, caplog):
        """Test that export_templates creates the templates and static/css directories."""
        caplog.set_level(logging.INFO)
        project_path = tmp_path / "test_project"
        project_path.mkdir()

        export_templates(project_path)

        # Check directories were created
        assert (project_path / "templates").exists()
        assert (project_path / "static" / "css").exists()
        assert "Templates exported" in caplog.text

    def test_export_templates_copies_template_files(self, tmp_path, caplog):
        """Test that export_templates copies all .j2 template files."""
        caplog.set_level(logging.INFO)
        project_path = tmp_path / "test_project"
        project_path.mkdir()

        export_templates(project_path)

        # Check that template files were copied
        templates_dir = project_path / "templates"
        expected_templates = [
            "login.html.j2",
            "error.html.j2",
            "error_modal.html.j2",
            "splash_screen.html.j2",
            "session_lost_banner.html.j2",
            "app_process_error.html.j2",
        ]
        for template_name in expected_templates:
            assert (templates_dir / template_name).exists(), (
                f"Template {template_name} was not exported"
            )

    def test_export_templates_copies_css_files(self, tmp_path, caplog):
        """Test that export_templates copies CSS files."""
        caplog.set_level(logging.INFO)
        project_path = tmp_path / "test_project"
        project_path.mkdir()

        export_templates(project_path)

        # Check that CSS files were copied
        css_dir = project_path / "static" / "css"
        assert (css_dir / "numerous-base.css").exists()

    def test_export_templates_skips_existing_files(self, tmp_path, caplog):
        """Test that export_templates does not overwrite existing files."""
        caplog.set_level(logging.INFO)
        project_path = tmp_path / "test_project"
        project_path.mkdir()

        # Create existing template file with custom content
        templates_dir = project_path / "templates"
        templates_dir.mkdir()
        existing_template = templates_dir / "login.html.j2"
        custom_content = "<!-- Custom login template -->"
        existing_template.write_text(custom_content)

        export_templates(project_path)

        # Verify the existing file was not overwritten
        assert existing_template.read_text() == custom_content
        assert "already exists, skipping: login.html.j2" in caplog.text

    def test_export_templates_skips_existing_css(self, tmp_path, caplog):
        """Test that export_templates does not overwrite existing CSS files."""
        caplog.set_level(logging.INFO)
        project_path = tmp_path / "test_project"
        project_path.mkdir()

        # Create existing CSS file with custom content
        css_dir = project_path / "static" / "css"
        css_dir.mkdir(parents=True)
        existing_css = css_dir / "numerous-base.css"
        custom_content = "/* Custom CSS */"
        existing_css.write_text(custom_content)

        export_templates(project_path)

        # Verify the existing file was not overwritten
        assert existing_css.read_text() == custom_content
        assert "already exists, skipping: numerous-base.css" in caplog.text


def test_main_with_export_templates(caplog):
    """Test that main() calls export_templates when --export-templates flag is set."""
    caplog.set_level(logging.INFO)
    test_args = [
        "script_name",
        "test_project",
        "--skip-deps",
        "--run-skip",
        "--export-templates",
    ]
    with (
        patch("sys.argv", test_args),
        patch("numerous.apps.bootstrap.copy_template") as mock_copy,
        patch("numerous.apps.bootstrap.install_requirements") as mock_install,
        patch("numerous.apps.bootstrap.run_app") as mock_run,
        patch("numerous.apps.bootstrap.export_templates") as mock_export,
    ):
        main()
        mock_copy.assert_called_once()
        mock_install.assert_not_called()
        mock_run.assert_not_called()
        mock_export.assert_called_once()


def test_main_without_export_templates(caplog):
    """Test that main() does not call export_templates when flag is not set."""
    caplog.set_level(logging.INFO)
    test_args = ["script_name", "test_project", "--skip-deps", "--run-skip"]
    with (
        patch("sys.argv", test_args),
        patch("numerous.apps.bootstrap.copy_template") as mock_copy,
        patch("numerous.apps.bootstrap.install_requirements") as mock_install,
        patch("numerous.apps.bootstrap.run_app") as mock_run,
        patch("numerous.apps.bootstrap.export_templates") as mock_export,
    ):
        main()
        mock_copy.assert_called_once()
        mock_export.assert_not_called()
