import logging
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from numerous.apps._bootstrap import copy_template, install_requirements, main, run_app


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
        mock_run.assert_called_once_with(
            [sys.executable, "app.py"], cwd=mock_project_path, check=False
        )


def test_main_basic_flow(caplog):
    caplog.set_level(logging.DEBUG)
    test_args = ["script_name", "test_project"]
    with (
        patch("sys.argv", test_args),
        patch("numerous.apps._bootstrap.copy_template") as mock_copy,
        patch("numerous.apps._bootstrap.install_requirements") as mock_install,
        patch("numerous.apps._bootstrap.run_app") as mock_run,
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
        patch("numerous.apps._bootstrap.copy_template") as mock_copy,
        patch("numerous.apps._bootstrap.install_requirements") as mock_install,
        patch("numerous.apps._bootstrap.run_app") as mock_run,
    ):
        main()
        mock_copy.assert_called_once()
        mock_install.assert_not_called()
        mock_run.assert_not_called()
