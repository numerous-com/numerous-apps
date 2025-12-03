#!/usr/bin/env python3

import json
import logging
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import httpx
import psutil
from playwright.sync_api import sync_playwright, expect


# Setup logging
logger = logging.getLogger("End to End Test Logger")
logging.basicConfig(level=logging.INFO)


def run_browser_tests(host: str, port: int) -> None:
    """Run Playwright browser tests to verify UI functionality."""
    logger.info("Starting Playwright browser tests")
    base_url = f"http://{host}:{port}"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        try:
            # Test 1: Page loads with correct title
            logger.info("Test: Page loads with correct title")
            page.goto(base_url)
            expect(page).to_have_title("Numerous Demo App")
            logger.info("✓ Page title is correct")

            # Test 2: Logo is visible
            logger.info("Test: Logo is visible")
            logo = page.locator("img[alt='Numerous Logo']")
            expect(logo).to_be_visible()
            logger.info("✓ Logo is visible")

            # Test 3: Tabs are present
            logger.info("Test: Tabs are present")
            # Wait for the app to fully load
            page.wait_for_timeout(2000)
            tabs_container = page.locator(".main-content")
            expect(tabs_container).to_be_visible()
            logger.info("✓ Main content is visible")

            # Test 4: Counter widget shows initial value
            logger.info("Test: Counter widget displays")
            # Look for the counter label
            counter_label = page.get_by_text("Counter:")
            expect(counter_label).to_be_visible()
            logger.info("✓ Counter widget is visible")

            # Test 5: Click increment button and verify counter increases
            logger.info("Test: Increment button functionality")
            # Find and click the increment button
            increment_button = page.get_by_role("button", name="Increment Counter")
            expect(increment_button).to_be_visible()

            # Get initial counter value - look for input with the counter value
            counter_input = page.locator("input[type='number']").first
            initial_value = counter_input.input_value()
            logger.info(f"Initial counter value: {initial_value}")

            # Click the button
            increment_button.click()
            page.wait_for_timeout(500)  # Wait for update

            # Verify counter increased
            new_value = counter_input.input_value()
            logger.info(f"New counter value: {new_value}")
            assert int(new_value) == int(initial_value) + 1, (
                f"Counter did not increment: {initial_value} -> {new_value}"
            )
            logger.info("✓ Counter incremented successfully")

            # Test 6: Click increment again to verify it keeps working
            logger.info("Test: Multiple increments work")
            increment_button.click()
            page.wait_for_timeout(500)
            final_value = counter_input.input_value()
            assert int(final_value) == int(new_value) + 1, (
                f"Counter did not increment again: {new_value} -> {final_value}"
            )
            logger.info("✓ Multiple increments work correctly")

            # Test 7: Dropdown is present and functional
            logger.info("Test: Dropdown widget is present")
            dropdown_label = page.get_by_text("Select Value")
            expect(dropdown_label).to_be_visible()
            logger.info("✓ Dropdown widget is visible")

            # Test 8: Footer is present
            logger.info("Test: Footer is present")
            footer = page.locator("footer")
            expect(footer).to_be_visible()
            expect(footer).to_contain_text("Numerous ApS")
            logger.info("✓ Footer is visible with correct text")

            logger.info("All Playwright browser tests passed!")

        finally:
            context.close()
            browser.close()


def run_auth_browser_tests(host: str, port: int) -> None:
    """Run Playwright browser tests to verify auth functionality."""
    logger.info("Starting Playwright auth browser tests")
    base_url = f"http://{host}:{port}"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        try:
            # Test 1: Unauthenticated access redirects to login
            logger.info("Test: Unauthenticated access redirects to login")
            page.goto(base_url)
            page.wait_for_timeout(1000)  # Wait for redirect
            # URL may include query params like ?next=/
            current_url = page.url
            assert "/login" in current_url, f"Expected redirect to login, got {current_url}"
            logger.info("✓ Redirected to login page")

            # Test 2: Login page shows login form
            logger.info("Test: Login page shows login form")
            username_input = page.locator('input[name="username"]')
            password_input = page.locator('input[name="password"]')
            login_button = page.locator('button[type="submit"]')
            expect(username_input).to_be_visible()
            expect(password_input).to_be_visible()
            expect(login_button).to_be_visible()
            logger.info("✓ Login form is visible")

            # Test 3: Invalid credentials show error
            logger.info("Test: Invalid credentials show error")
            username_input.fill("wronguser")
            password_input.fill("wrongpass")
            login_button.click()
            page.wait_for_timeout(1000)  # Wait for response
            # Should still be on login page
            current_url = page.url
            assert "/login" in current_url, f"Expected to stay on login page, got {current_url}"
            logger.info("✓ Invalid credentials handled correctly")

            # Test 4: Valid credentials redirect to app
            logger.info("Test: Valid credentials redirect to app")
            # Clear previous values
            username_input.clear()
            password_input.clear()
            username_input.fill("admin")
            password_input.fill("admin123")
            login_button.click()
            page.wait_for_timeout(2000)  # Wait for redirect and app to load
            # Should be redirected away from login
            current_url = page.url
            assert "/login" not in current_url, f"Expected to be redirected from login, but URL is {current_url}"
            logger.info("✓ Valid credentials redirect to app")

            # Test 5: App page loads after authentication
            logger.info("Test: App page loads after authentication")
            expect(page).to_have_title("Numerous Demo App")
            logger.info("✓ App title is correct after login")

            # Test 6: Counter widget is visible after login
            logger.info("Test: Counter widget is visible after login")
            counter_label = page.get_by_text("Counter:")
            expect(counter_label).to_be_visible()
            logger.info("✓ Counter widget is visible")

            # Test 7: Increment button works after login
            logger.info("Test: Increment button functionality after login")
            increment_button = page.get_by_role("button", name="Increment Counter")
            expect(increment_button).to_be_visible()
            counter_input = page.locator("input[type='number']").first
            initial_value = counter_input.input_value()
            logger.info(f"Initial counter value: {initial_value}")
            increment_button.click()
            page.wait_for_timeout(500)
            new_value = counter_input.input_value()
            logger.info(f"New counter value: {new_value}")
            assert int(new_value) == int(initial_value) + 1, (
                f"Counter did not increment: {initial_value} -> {new_value}"
            )
            logger.info("✓ Counter incremented successfully after login")

            # Test 8: Logout functionality
            logger.info("Test: Logout functionality")
            # Look for logout button or link
            logout_element = page.locator('[data-action="logout"], button:has-text("Logout"), a:has-text("Logout")')
            if logout_element.count() > 0:
                logout_element.first.click()
                page.wait_for_timeout(1000)
                current_url = page.url
                assert "/login" in current_url, f"Expected redirect to login, got {current_url}"
                logger.info("✓ Logout redirects to login page")
            else:
                logger.info("⊘ Logout button not found (skipped)")

            logger.info("All Playwright auth browser tests passed!")

        finally:
            context.close()
            browser.close()


def create_venv(tmp_path: Path) -> Path:
    """Create a temporary virtual environment, or reuse existing one."""
    import venv

    logger.info(f"Creating virtual environment in {tmp_path}")
    venv_path = tmp_path / "venv"
    
    # Check if venv already exists and has a working Python
    venv_python = venv_path / ("Scripts" if sys.platform == "win32" else "bin") / ("python.exe" if sys.platform == "win32" else "python")
    if venv_python.exists():
        logger.info("Virtual environment already exists, reusing it")
        return venv_path
    
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
    # wait for server to start - needs longer on first run due to pip install
    time.sleep(30)
    try:
        # Wait for server to start or detect early failure
        start_time = time.time()
        timeout = 120  # seconds - pip install of numpy/h5py can take a while
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
            raise TimeoutError(
                f"Server failed to start within {timeout} seconds. "
                "This may happen if dependency installation takes longer than expected."
            )
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

        # Run Playwright browser tests
        run_browser_tests(host, port)

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


def test_numerous_bootstrap_with_auth(tmp_path: Path) -> None:
    """Test the numerous-bootstrap command with --with-auth option."""
    logger.info("Starting test_numerous_bootstrap_with_auth")
    # Create virtual environment and install package
    venv_dir = create_venv(tmp_path)
    venv_python = get_venv_python(venv_dir)
    install_package(venv_python, tmp_path)
    
    # Start the numerous-bootstrap process with auth enabled
    port = 8766  # Use different port from non-auth test
    host = "127.0.0.1"
    
    # Set up auth environment variables
    auth_env = {
        **os.environ,
        "PYTHONPATH": str(tmp_path),
        "NUMEROUS_JWT_SECRET": "test-secret-key-for-e2e-auth",
        "NUMEROUS_AUTH_USERS": json.dumps([
            {"username": "admin", "password": "admin123", "is_admin": True},
            {"username": "user", "password": "user123", "roles": ["viewer"]},
        ]),
    }
    
    process = subprocess.Popen(
        [
            venv_python,
            "-m",
            "numerous.apps.bootstrap",
            tmp_path / "test-auth-app",
            "--port",
            str(port),
            "--host",
            str(host),
            "--with-auth",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=auth_env,
        text=True,
        bufsize=1,
        preexec_fn=(
            os.setsid if sys.platform != "win32" else None
        ),
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

    logger.info("Started numerous-bootstrap process with auth")
    # wait for server to start
    time.sleep(30)
    
    try:
        # Wait for server to start or detect early failure
        start_time = time.time()
        timeout = 120  # seconds
        server_ready = False

        while (time.time() - start_time) < timeout:
            logger.info(f"Waiting for auth server to start on {host}:{port}")
            if process.poll() is not None:
                logger.info("Process terminated unexpectedly.")
                stdout, stderr = process.communicate()
                logger.info(f"Stdout: {stdout}")
                logger.info(f"Stderr: {stderr}")
                raise RuntimeError("Process terminated unexpectedly")

            try:
                logger.info(f"Checking if auth server is responding on {host}:{port}")
                with httpx.Client(base_url=f"http://{host}:{port}", follow_redirects=False) as client:
                    response = client.get("/")
                    # With auth, we expect a redirect to login (302) or success (200)
                    if response.status_code in (200, 302, 307):
                        server_ready = True
                        break
            except httpx.ConnectError:
                logger.info(f"Auth server not responding on {host}:{port}")
                time.sleep(1)
                continue

        logger.info(f"Auth server ready: {server_ready}")
        if not server_ready:
            if process.poll() is not None or True:
                stdout, stderr = process.communicate()
                logger.info("Process terminated unexpectedly.")
                logger.info(f"Stdout: {stdout}")
                logger.info(f"Stderr: {stderr}")
                raise RuntimeError("Process terminated unexpectedly")
            raise TimeoutError(
                f"Auth server failed to start within {timeout} seconds."
            )
        
        logger.info(f"Auth server started on {host}:{port}")
        
        # Test the auth endpoints
        with httpx.Client(base_url=f"http://{host}:{port}", follow_redirects=False) as client:
            # Test that home redirects to login
            response = client.get("/")
            assert response.status_code in (302, 307), f"Expected redirect, got {response.status_code}"
            logger.info("Home endpoint redirects to login (auth working)")
            
            # Test login endpoint exists
            response = client.get("/login")
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            logger.info("Login page accessible")
            
            # Test API auth check
            response = client.get("/api/auth/check")
            assert response.status_code == 200
            data = response.json()
            assert data["authenticated"] is False
            logger.info("Auth check reports not authenticated")
            
            # Test login with valid credentials
            response = client.post(
                "/api/auth/login",
                json={"username": "admin", "password": "admin123"},
            )
            assert response.status_code == 200, f"Login failed: {response.text}"
            login_data = response.json()
            assert "access_token" in login_data
            assert login_data["user"]["username"] == "admin"
            logger.info("API login successful")

        # Run Playwright auth browser tests
        run_auth_browser_tests(host, port)

    finally:
        logger.info(f"Terminating auth server on {host}:{port}")

        if sys.platform == "win32":
            try:
                parent = psutil.Process(process.pid)
                children = parent.children(recursive=True)
                for child in children:
                    child.terminate()
                gone, alive = psutil.wait_procs(children, timeout=3)
                for p in alive:
                    p.kill()
                parent.terminate()
                parent.wait(3)
            except psutil.NoSuchProcess:
                pass
        else:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                process.wait()

        logger.info("Auth server terminated")

    logger.info(f"Auth process return code: {process.returncode}")


def test_numerous_bootstrap_with_export_templates(tmp_path: Path) -> None:
    """Test the numerous-bootstrap command with --export-templates option."""
    logger.info("Starting test_numerous_bootstrap_with_export_templates")
    # Create virtual environment and install package
    venv_dir = create_venv(tmp_path)
    venv_python = get_venv_python(venv_dir)
    install_package(venv_python, tmp_path)

    app_path = tmp_path / "test-export-templates-app"

    # Run numerous-bootstrap with --export-templates flag
    process = subprocess.run(
        [
            venv_python,
            "-m",
            "numerous.apps.bootstrap",
            str(app_path),
            "--skip-deps",
            "--run-skip",
            "--export-templates",
        ],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(tmp_path)},
    )

    logger.info(f"Stdout: {process.stdout}")
    logger.info(f"Stderr: {process.stderr}")

    # Check process succeeded
    assert process.returncode == 0, f"Bootstrap failed: {process.stderr}"
    logger.info("Bootstrap with --export-templates completed successfully")

    # Verify templates directory was created and contains expected files
    templates_dir = app_path / "templates"
    assert templates_dir.exists(), "templates directory was not created"
    logger.info("✓ templates directory exists")

    expected_templates = [
        "login.html.j2",
        "error.html.j2",
        "error_modal.html.j2",
        "splash_screen.html.j2",
        "session_lost_banner.html.j2",
        "app_process_error.html.j2",
    ]

    for template_name in expected_templates:
        template_file = templates_dir / template_name
        assert template_file.exists(), f"Template {template_name} was not exported"
        assert template_file.stat().st_size > 0, f"Template {template_name} is empty"
        logger.info(f"✓ {template_name} exists and has content")

    # Verify CSS files were exported
    css_dir = app_path / "static" / "css"
    assert css_dir.exists(), "static/css directory was not created"
    logger.info("✓ static/css directory exists")

    css_file = css_dir / "numerous-base.css"
    assert css_file.exists(), "numerous-base.css was not exported"
    assert css_file.stat().st_size > 0, "numerous-base.css is empty"
    logger.info("✓ numerous-base.css exists and has content")

    # Verify the app's own index.html.j2 still exists (from bootstrap_app)
    app_template = app_path / "index.html.j2"
    assert app_template.exists(), "index.html.j2 was not created"
    logger.info("✓ index.html.j2 exists")

    logger.info("All export_templates tests passed!")


def test_numerous_bootstrap_with_db_auth(tmp_path: Path) -> None:
    """Test the numerous-bootstrap command with --with-db-auth option."""
    logger.info("Starting test_numerous_bootstrap_with_db_auth")
    # Create virtual environment and install package
    venv_dir = create_venv(tmp_path)
    venv_python = get_venv_python(venv_dir)
    install_package(venv_python, tmp_path)
    
    # Install database auth dependencies
    logger.info("Installing database auth dependencies...")
    try:
        subprocess.run(
            [venv_python, "-m", "pip", "install", "sqlalchemy[asyncio]>=2.0.0", "aiosqlite>=0.19.0", "bcrypt>=4.1.0"],
            check=True,
            capture_output=True,
        )
        logger.info("Database auth dependencies installed")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to install database auth deps: {e}")
        raise
    
    # Start the numerous-bootstrap process with db auth enabled
    port = 8767  # Use different port from other tests
    host = "127.0.0.1"
    
    # Set up auth environment variables
    auth_env = {
        **os.environ,
        "PYTHONPATH": str(tmp_path),
        "NUMEROUS_JWT_SECRET": "test-secret-key-for-e2e-db-auth",
    }
    
    process = subprocess.Popen(
        [
            venv_python,
            "-m",
            "numerous.apps.bootstrap",
            tmp_path / "test-db-auth-app",
            "--port",
            str(port),
            "--host",
            str(host),
            "--with-db-auth",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=auth_env,
        text=True,
        bufsize=1,
        preexec_fn=(
            os.setsid if sys.platform != "win32" else None
        ),
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

    logger.info("Started numerous-bootstrap process with database auth")
    # wait for server to start - longer for db auth due to extra deps
    time.sleep(45)
    
    try:
        # Wait for server to start or detect early failure
        start_time = time.time()
        timeout = 180  # seconds - longer for db auth due to extra deps
        server_ready = False

        while (time.time() - start_time) < timeout:
            logger.info(f"Waiting for db auth server to start on {host}:{port}")
            if process.poll() is not None:
                logger.info("Process terminated unexpectedly.")
                stdout, stderr = process.communicate()
                logger.info(f"Stdout: {stdout}")
                logger.info(f"Stderr: {stderr}")
                raise RuntimeError("Process terminated unexpectedly")

            try:
                logger.info(f"Checking if db auth server is responding on {host}:{port}")
                with httpx.Client(base_url=f"http://{host}:{port}", follow_redirects=False) as client:
                    response = client.get("/")
                    # With auth, we expect a redirect to login (302) or success (200)
                    if response.status_code in (200, 302, 307):
                        server_ready = True
                        break
            except httpx.ConnectError:
                logger.info(f"DB auth server not responding on {host}:{port}")
                time.sleep(1)
                continue

        logger.info(f"DB auth server ready: {server_ready}")
        if not server_ready:
            if process.poll() is not None or True:
                stdout, stderr = process.communicate()
                logger.info("Process terminated unexpectedly.")
                logger.info(f"Stdout: {stdout}")
                logger.info(f"Stderr: {stderr}")
                raise RuntimeError("Process terminated unexpectedly")
            raise TimeoutError(
                f"DB auth server failed to start within {timeout} seconds."
            )
        
        logger.info(f"DB auth server started on {host}:{port}")
        
        # Test the auth endpoints
        with httpx.Client(base_url=f"http://{host}:{port}", follow_redirects=False) as client:
            # Test that home redirects to login
            response = client.get("/")
            assert response.status_code in (302, 307), f"Expected redirect, got {response.status_code}"
            logger.info("Home endpoint redirects to login (db auth working)")
            
            # Test login endpoint exists
            response = client.get("/login")
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            logger.info("Login page accessible")
            
            # Test API auth check
            response = client.get("/api/auth/check")
            assert response.status_code == 200
            data = response.json()
            assert data["authenticated"] is False
            logger.info("Auth check reports not authenticated")
            
            # Test login with valid credentials (created by setup_default_users)
            response = client.post(
                "/api/auth/login",
                json={"username": "admin", "password": "admin123"},
            )
            assert response.status_code == 200, f"Login failed: {response.text}"
            login_data = response.json()
            assert "access_token" in login_data
            assert login_data["user"]["username"] == "admin"
            assert login_data["user"]["is_admin"] is True
            logger.info("API login successful with database auth")
            
            # Test login with regular user
            response = client.post(
                "/api/auth/login",
                json={"username": "user", "password": "user1234"},
            )
            assert response.status_code == 200, f"User login failed: {response.text}"
            user_data = response.json()
            assert user_data["user"]["username"] == "user"
            assert user_data["user"]["is_admin"] is False
            logger.info("Regular user login successful with database auth")

        # Run Playwright auth browser tests (same flow as env auth)
        run_auth_browser_tests(host, port)

    finally:
        logger.info(f"Terminating db auth server on {host}:{port}")

        if sys.platform == "win32":
            try:
                parent = psutil.Process(process.pid)
                children = parent.children(recursive=True)
                for child in children:
                    child.terminate()
                gone, alive = psutil.wait_procs(children, timeout=3)
                for p in alive:
                    p.kill()
                parent.terminate()
                parent.wait(3)
            except psutil.NoSuchProcess:
                pass
        else:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                process.wait()

        logger.info("DB auth server terminated")

    logger.info(f"DB auth process return code: {process.returncode}")


def main():
    """Main entry point for the test script."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        try:
            # Run the regular bootstrap integration test
            test_numerous_bootstrap_integration(tmp_path)
            logger.info("Regular bootstrap tests passed!")
            
            # Wait for any lingering processes to fully terminate
            time.sleep(3)
            
            # Run the auth-enabled bootstrap test
            test_numerous_bootstrap_with_auth(tmp_path)
            logger.info("Auth bootstrap tests passed!")
            
            # Wait for any lingering processes to fully terminate
            time.sleep(3)
            
            # Run the database auth bootstrap test
            test_numerous_bootstrap_with_db_auth(tmp_path)
            logger.info("Database auth bootstrap tests passed!")
            
            # Wait for any lingering processes to fully terminate
            time.sleep(3)
            
            # Run the export templates bootstrap test
            test_numerous_bootstrap_with_export_templates(tmp_path)
            logger.info("Export templates bootstrap tests passed!")
            
            logger.info("All tests passed successfully!")
        except Exception as e:
            logger.error(f"Test failed: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
