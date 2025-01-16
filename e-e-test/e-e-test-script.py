#!/usr/bin/env python3

import logging
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import httpx
import psutil


# Setup logging
logger = logging.getLogger("End to End Test Logger")
logging.basicConfig(level=logging.INFO)


def create_venv(tmp_path: Path) -> Path:
    """Create a temporary virtual environment."""
    import venv

    logger.info(f"Creating virtual environment in {tmp_path}")
    venv_path = tmp_path / "venv"
    venv.create(venv_path, with_pip=True)
    return venv_path


def get_venv_python(venv_dir: Path) -> str:
    """Get the Python executable path for the virtual environment."""
    logger.info("Getting Python executable path for virtual environment")
    if sys.platform == "win32" or sys.platform == "win64":
        return str(venv_dir / "Scripts" / "python.exe")
    return str(venv_dir / "bin" / "python")


def install_package(venv_python: str, tmp_path: Path) -> None:
    """Install the package in the virtual environment."""
    project_root = Path(__file__).parent.parent
    logger.info("Installing package in virtual environment")
    try:
        output = subprocess.run(
            [venv_python, "-m", "pip", "install", str(project_root)],
            check=True,
            capture_output=True,
        )
        logger.info("Package installed successfully")
        logger.info(f"Stdout: {output.stdout.decode()}")
        logger.info(f"Stderr: {output.stderr.decode()}")

    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to install package in virtual environment: {e}")
        logger.error(f"Stdout: {e.stdout.decode()}")
        logger.error(f"Stderr: {e.stderr.decode()}")
        raise


def test_numerous_bootstrap_integration(tmp_path: Path) -> None:
    """Test the numerous-bootstrap command end-to-end."""
    logger.info("Starting test_numerous_bootstrap_integration")
    # Create virtual environment and install package
    venv_dir = create_venv(tmp_path)
    venv_python = get_venv_python(venv_dir)
    install_package(venv_python, tmp_path)
    # Start the numerous-bootstrap process
    port = 8765
    host = "127.0.0.1"
    process = subprocess.Popen(
        [
            venv_python,
            "-m",
            "numerous.apps.bootstrap",
            tmp_path / "test-app",
            "--port",
            str(port),
            "--host",
            str(host),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**os.environ, "PYTHONPATH": str(tmp_path)},
        text=True,  # Use text mode instead of bytes
        bufsize=1,  # Line buffered
        preexec_fn=(
            os.setsid if sys.platform != "win32" else None
        ),  # Create new process group on Unix
    )

    # Create thread to continuously read and log output
    def log_output(pipe, log_level):
        for line in iter(pipe.readline, ""):
            log_level(line.strip())

    from threading import Thread

    stdout_thread = Thread(
        target=log_output, args=(process.stdout, logger.info), daemon=True
    )
    stderr_thread = Thread(
        target=log_output, args=(process.stderr, logger.error), daemon=True
    )
    stdout_thread.start()
    stderr_thread.start()

    logger.info("Started numerous-bootstrap process")
    # wait for server to start
    time.sleep(10)
    try:
        # Wait for server to start or detect early failure
        start_time = time.time()
        timeout = 10  # seconds
        server_ready = False

        while (time.time() - start_time) < timeout:
            logger.info(f"Waiting for server to start on {host}:{port}")
            if process.poll() is not None:
                # Process has terminated
                logger.info("Process terminated unexpectedly.")
                stdout, stderr = process.communicate()
                logger.info(f"Stdout: {stdout}")
                logger.info(f"Stderr: {stderr}")
                raise RuntimeError("Process terminated unexpectedly")

            # Check if server is responding
            try:
                logger.info(f"Checking if server is responding on {host}:{port}")
                with httpx.Client(base_url=f"http://{host}:{port}") as client:
                    response = client.get("/")
                    if response.status_code == 200:
                        server_ready = True
                        break
            except httpx.ConnectError:
                logger.info(f"Server not responding on {host}:{port}")
                time.sleep(1)
                continue

        logger.info(f"Server ready: {server_ready}")
        if not server_ready:
            if process.poll() is not None or True:
                # Process has terminated
                stdout, stderr = process.communicate()
                logger.info("Process terminated unexpectedly.")

                logger.info(f"Stdout: {stdout}")
                logger.info(f"Stderr: {stderr}")
                raise RuntimeError("Process terminated unexpectedly")
            # If we got here, we timed out waiting for the server
            raise TimeoutError(f"Server failed to start within {timeout} seconds.\n")
        logger.info(f"Server started on {host}:{port}")
        # Test the endpoints
        with httpx.Client(base_url=f"http://{host}:{port}") as client:
            # Test home endpoint
            response = client.get("/")
            assert response.status_code == 200
            # assert "Test App" in response.text
            logger.info("Test App endpoint responded with status code 200")
            logger.info(f"Response: {response}")

            # Test widgets endpoint
            widgets_response = client.get("/api/widgets")
            assert widgets_response.status_code == 200
            # assert "session_id" in widgets_response.json()
            # assert "widgets" in widgets_response.json()
            logger.info("Widgets endpoint responded with status code 200")
            logger.info(f"Response: {widgets_response}")

    finally:
        logger.info(f"Terminating server on {host}:{port}")

        if sys.platform == "win32":
            # On Windows, we need to be more aggressive with process termination
            try:
                parent = psutil.Process(process.pid)
                children = parent.children(recursive=True)
                for child in children:
                    child.terminate()
                # Give them some time to terminate gracefully
                gone, alive = psutil.wait_procs(children, timeout=3)
                for p in alive:
                    p.kill()  # Force kill if still alive
                parent.terminate()
                parent.wait(3)
            except psutil.NoSuchProcess:
                pass
        else:
            # Unix systems can use process groups
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                process.wait()

        logger.info("Server terminated")

    logger.info(f"Process return code: {process.returncode}")
    # assert process.returncode in (0, -15)  # -15 is SIGTERM


def main():
    """Main entry point for the test script."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        try:
            test_numerous_bootstrap_integration(tmp_path)
            logger.info("All tests passed successfully!")
        except Exception as e:
            logger.error(f"Test failed: {e}")


if __name__ == "__main__":
    main()
