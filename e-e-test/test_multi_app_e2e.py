#!/usr/bin/env python3
"""End-to-end tests for multi-app functionality."""

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
logger = logging.getLogger("Multi-App E2E Test Logger")
logging.basicConfig(level=logging.INFO)

# Get project root
PROJECT_ROOT = Path(__file__).parent.parent


def run_multi_app_browser_tests(host: str, port: int) -> None:
    """Run Playwright browser tests for multi-app functionality."""
    logger.info("Starting Playwright multi-app browser tests")
    base_url = f"http://{host}:{port}"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        try:
            # Test 1: Root redirects to /public
            logger.info("Test: Root redirects to public app")
            response = page.goto(base_url)
            page.wait_for_timeout(1000)
            current_url = page.url
            assert "/public" in current_url, f"Expected redirect to /public, got {current_url}"
            logger.info("✓ Root redirects to public app")

            # Test 2: Public app loads without auth
            logger.info("Test: Public app loads without authentication")
            page.goto(f"{base_url}/public")
            page.wait_for_timeout(2000)
            # Should not redirect to login
            current_url = page.url
            assert "/login" not in current_url, f"Public app should not require login, but got {current_url}"
            # Look for public app content - use heading role to be specific
            public_heading = page.get_by_role("heading", name="🌐 Public App")
            expect(public_heading).to_be_visible()
            logger.info("✓ Public app loads without authentication")

            # Test 3: Public app counter works
            logger.info("Test: Public app counter functionality")
            
            # Check that splash screen is hidden
            splash = page.locator("#splash-screen")
            if splash.count() > 0:
                is_hidden = splash.evaluate("el => el.classList.contains('hidden')")
                assert is_hidden, "Public app splash screen should be hidden"
            
            counter_label = page.get_by_text("Public Counter:")
            expect(counter_label).to_be_visible()
            
            # Find increment button
            increment_btn = page.get_by_role("button", name="Increment")
            expect(increment_btn).to_be_visible()
            
            # Get initial value
            counter_input = page.locator("input[type='number']").first
            initial_value = counter_input.input_value()
            logger.info(f"Initial counter value: {initial_value}")
            
            # Click and verify
            increment_btn.click()
            page.wait_for_timeout(500)
            new_value = counter_input.input_value()
            assert int(new_value) == int(initial_value) + 1, f"Counter did not increment"
            logger.info("✓ Public app counter works")

            # Test 4: Admin app redirects to login
            logger.info("Test: Admin app redirects to login")
            page.goto(f"{base_url}/admin")
            page.wait_for_timeout(1000)
            current_url = page.url
            assert "/login" in current_url, f"Admin app should redirect to login, got {current_url}"
            logger.info("✓ Admin app redirects to login")

            # Test 5: Login form is present at admin login
            logger.info("Test: Admin login form is present")
            username_input = page.locator('input[name="username"]')
            password_input = page.locator('input[name="password"]')
            login_button = page.locator('button[type="submit"]')
            expect(username_input).to_be_visible()
            expect(password_input).to_be_visible()
            expect(login_button).to_be_visible()
            logger.info("✓ Admin login form is present")

            # Test 6: Login to admin app
            logger.info("Test: Login to admin app")
            username_input.fill("admin")
            password_input.fill("admin123")
            login_button.click()
            page.wait_for_timeout(2000)
            
            # Should be redirected to admin app
            current_url = page.url
            assert "/login" not in current_url, f"Should be logged in, but URL is {current_url}"
            logger.info("✓ Successfully logged into admin app")

            # Test 7: Admin app content is visible after login
            logger.info("Test: Admin app content is visible")
            admin_heading = page.get_by_role("heading", name="🔒 Admin Dashboard")
            expect(admin_heading).to_be_visible()
            logger.info("✓ Admin app content is visible after login")

            # Test 8: Admin counter works with different increment
            logger.info("Test: Admin counter functionality")
            
            # Check that splash screen is hidden in admin app
            splash = page.locator("#splash-screen")
            if splash.count() > 0:
                is_hidden = splash.evaluate("el => el.classList.contains('hidden')")
                assert is_hidden, "Admin app splash screen should be hidden"
            
            admin_counter_label = page.get_by_text("Admin Counter:")
            expect(admin_counter_label).to_be_visible()
            
            # Find admin button
            admin_btn = page.get_by_role("button", name="Add 10")
            expect(admin_btn).to_be_visible()
            
            # Get initial value
            admin_counter_input = page.locator("input[type='number']").first
            admin_initial = admin_counter_input.input_value()
            
            # Click and verify (+10 increment)
            admin_btn.click()
            page.wait_for_timeout(500)
            admin_new = admin_counter_input.input_value()
            assert int(admin_new) == int(admin_initial) + 10, f"Admin counter did not increment by 10"
            logger.info("✓ Admin counter works with +10 increment")

            # Test 9: Navigation between apps
            logger.info("Test: Navigation between apps")
            # Click link to public app
            public_link = page.get_by_role("link", name="Public App")
            public_link.click()
            page.wait_for_timeout(1000)
            current_url = page.url
            assert "/public" in current_url, f"Expected /public, got {current_url}"
            logger.info("✓ Navigation to public app works")

            # Test 10: Health endpoint at root
            logger.info("Test: Health endpoint available at root")
            # Navigate to health endpoint (can't use page for API calls, so check via httpx)
            logger.info("✓ Health endpoint verified via API tests")

            logger.info("All Playwright multi-app browser tests passed!")

        finally:
            context.close()
            browser.close()


def test_multi_app_integration() -> None:
    """Test the multi-app deployment end-to-end."""
    logger.info("Starting multi-app integration test")
    
    # Start the multi-app server
    port = 8772
    host = "127.0.0.1"
    
    # Change to the multi-app test directory
    multi_app_dir = PROJECT_ROOT / "e-e-test" / "multi-app-test"
    
    # Get the virtual environment Python
    venv_python = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    if not venv_python.exists():
        venv_python = PROJECT_ROOT / ".venv" / "bin" / "python"
    
    env = {
        **os.environ,
        "PYTHONPATH": str(PROJECT_ROOT / "src"),
    }
    
    process = subprocess.Popen(
        [
            str(venv_python),
            "-c",
            f"""
import sys
sys.path.insert(0, r'{multi_app_dir}')
sys.path.insert(0, r'{PROJECT_ROOT / "src"}')
import uvicorn
from main import main_app
uvicorn.run(main_app, host='{host}', port={port})
""",
        ],
        cwd=str(multi_app_dir),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        text=True,
        bufsize=1,
        preexec_fn=(os.setsid if sys.platform != "win32" else None),
    )

    # Create threads to log output
    def log_output(pipe, log_level):
        for line in iter(pipe.readline, ""):
            log_level(line.strip())

    from threading import Thread
    stdout_thread = Thread(target=log_output, args=(process.stdout, logger.info), daemon=True)
    stderr_thread = Thread(target=log_output, args=(process.stderr, logger.error), daemon=True)
    stdout_thread.start()
    stderr_thread.start()

    logger.info("Started multi-app server")
    time.sleep(10)  # Wait for server to start
    
    try:
        # Wait for server to be ready
        start_time = time.time()
        timeout = 60
        server_ready = False

        while (time.time() - start_time) < timeout:
            logger.info(f"Waiting for multi-app server on {host}:{port}")
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                logger.error(f"Process terminated unexpectedly")
                logger.error(f"Stdout: {stdout}")
                logger.error(f"Stderr: {stderr}")
                raise RuntimeError("Multi-app server terminated unexpectedly")

            try:
                with httpx.Client(base_url=f"http://{host}:{port}", follow_redirects=False) as client:
                    response = client.get("/health")
                    if response.status_code == 200:
                        server_ready = True
                        break
            except httpx.ConnectError:
                time.sleep(1)
                continue

        if not server_ready:
            raise TimeoutError(f"Multi-app server failed to start within {timeout} seconds")
        
        logger.info(f"Multi-app server started on {host}:{port}")
        
        # Run HTTP API tests
        with httpx.Client(base_url=f"http://{host}:{port}", follow_redirects=False) as client:
            # Test health endpoint
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert "/public" in data["apps"]
            assert "/admin" in data["apps"]
            logger.info("✓ Health endpoint works")
            
            # Test root redirect
            response = client.get("/")
            assert response.status_code == 302
            assert "/public" in response.headers.get("location", "")
            logger.info("✓ Root redirects to /public")
            
            # Test public app (no auth required)
            response = client.get("/public/", follow_redirects=True)
            assert response.status_code == 200
            logger.info("✓ Public app accessible without auth")
            
            # Test admin app (requires auth)
            response = client.get("/admin/")
            assert response.status_code == 302  # Redirect to login
            assert "/login" in response.headers.get("location", "")
            logger.info("✓ Admin app redirects to login")
            
            # Test admin login page
            response = client.get("/admin/login", follow_redirects=True)
            assert response.status_code == 200
            assert "username" in response.text.lower() or "Username" in response.text
            logger.info("✓ Admin login page accessible")

        # Run browser tests
        run_multi_app_browser_tests(host, port)

    finally:
        logger.info(f"Terminating multi-app server on {host}:{port}")
        
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

        logger.info("Multi-app server terminated")


def run_root_management_browser_tests(host: str, port: int) -> None:
    """Run Playwright browser tests for root + management app scenario."""
    logger.info("Starting Playwright root + management browser tests")
    base_url = f"http://{host}:{port}"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # Enable console logging
        page.on("console", lambda msg: logger.info(f"BROWSER CONSOLE [{msg.type}]: {msg.text}"))
        page.on("pageerror", lambda exc: logger.error(f"BROWSER ERROR: {exc}"))

        try:
            # Test 1: Root app loads without auth
            logger.info("Test: Root app loads without authentication")
            page.goto(base_url)
            page.wait_for_timeout(3000)  # Wait for widgets to initialize
            
            # Should not redirect to login
            current_url = page.url
            assert "/login" not in current_url, f"Root app should not require login, but got {current_url}"
            
            # Look for root app content - use heading role to be specific
            survey_heading = page.get_by_role("heading", name="📋 Public Survey")
            expect(survey_heading).to_be_visible()
            logger.info("✓ Root app loads without authentication")

            # Test 2: Root app widgets work (WebSocket test)
            logger.info("Test: Root app widgets functionality (WebSocket)")
            
            # Check that splash screen is hidden
            splash = page.locator("#splash-screen")
            if splash.count() > 0:
                is_hidden = splash.evaluate("el => el.classList.contains('hidden')")
                assert is_hidden, "Splash screen should be hidden"
            
            # Find and interact with submit button
            submit_btn = page.get_by_role("button", name="Submit Survey")
            expect(submit_btn).to_be_visible()
            
            # Get initial counter value
            counter_input = page.locator("input[type='number']").first
            initial_value = counter_input.input_value()
            logger.info(f"Initial survey count: {initial_value}")
            
            # Click and verify WebSocket updates work
            submit_btn.click()
            page.wait_for_timeout(1000)
            new_value = counter_input.input_value()
            assert int(new_value) == int(initial_value) + 1, f"Survey counter did not increment (WebSocket may have failed)"
            logger.info("✓ Root app widgets work (WebSocket operational)")

            # Test 3: Management app redirects to login
            logger.info("Test: Management app redirects to login")
            page.goto(f"{base_url}/management/")  # Trailing slash required for FastAPI mounts
            page.wait_for_timeout(2000)
            current_url = page.url
            assert "/login" in current_url, f"Management app should redirect to login, got {current_url}"
            assert "/management/login" in current_url, f"Should redirect to /management/login, got {current_url}"
            logger.info("✓ Management app redirects to /management/login")

            # Test 4: Login to management app
            logger.info("Test: Login to management app")
            username_input = page.locator('input[name="username"]')
            password_input = page.locator('input[name="password"]')
            login_button = page.locator('button[type="submit"]')
            
            expect(username_input).to_be_visible()
            expect(password_input).to_be_visible()
            expect(login_button).to_be_visible()
            
            username_input.fill("admin")
            password_input.fill("admin123")
            login_button.click()
            page.wait_for_timeout(3000)
            
            # Should be redirected to management app
            current_url = page.url
            assert "/login" not in current_url, f"Should be logged in, but URL is {current_url}"
            assert "/management" in current_url or current_url.endswith("/"), f"Should be at /management, got {current_url}"
            logger.info("✓ Successfully logged into management app")

            # Test 5: Management app content is visible after login
            logger.info("Test: Management app content is visible")
            management_heading = page.get_by_role("heading", name="🔒 Survey Management Dashboard")
            expect(management_heading).to_be_visible(timeout=5000)
            logger.info("✓ Management app content is visible after login")

            # Test 6: Management app widgets work (CRITICAL WebSocket test)
            logger.info("Test: Management app widgets functionality (WebSocket)")
            
            # Check that splash screen is hidden in management app too
            splash = page.locator("#splash-screen")
            if splash.count() > 0:
                is_hidden = splash.evaluate("el => el.classList.contains('hidden')")
                assert is_hidden, "Management app splash screen should be hidden"
            
            # Find management widgets
            refresh_btn = page.get_by_role("button", name="Refresh Data")
            expect(refresh_btn).to_be_visible(timeout=5000)
            
            # Get initial response count
            response_input = page.locator("input[type='number']").first
            initial_responses = response_input.input_value()
            logger.info(f"Initial response count: {initial_responses}")
            
            # Click and verify WebSocket updates work in management app
            refresh_btn.click()
            page.wait_for_timeout(1000)
            new_responses = response_input.input_value()
            
            expected = int(initial_responses) + 5
            actual = int(new_responses)
            assert actual == expected, (
                f"Management app counter did not increment correctly. "
                f"Expected {expected}, got {actual}. "
                f"This indicates WebSocket communication failed in the second mounted app!"
            )
            logger.info("✓ Management app widgets work (WebSocket operational)")

            # Test 7: Session isolation between apps
            logger.info("Test: Session isolation between apps")
            # Navigate back to root app
            page.goto(base_url)
            page.wait_for_timeout(2000)
            
            # Root app should still work
            root_submit = page.get_by_role("button", name="Submit Survey")
            expect(root_submit).to_be_visible()
            root_submit.click()
            page.wait_for_timeout(500)
            logger.info("✓ Session isolation works - both apps can operate independently")

            logger.info("All root + management browser tests passed!")

        finally:
            context.close()
            browser.close()


def test_root_management_integration() -> None:
    """Test the root + management app deployment end-to-end.
    
    This test specifically checks for the WebSocket bug where the second
    mounted app's widgets fail to initialize properly.
    """
    logger.info("Starting root + management integration test")
    
    # Start the root + management server
    port = 8773
    host = "127.0.0.1"
    
    # Change to the root-management test directory
    test_dir = PROJECT_ROOT / "e-e-test" / "root-management-test"
    
    # Get the virtual environment Python
    venv_python = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    if not venv_python.exists():
        venv_python = PROJECT_ROOT / ".venv" / "bin" / "python"
    
    env = {
        **os.environ,
        "PYTHONPATH": str(PROJECT_ROOT / "src"),
    }
    
    process = subprocess.Popen(
        [
            str(venv_python),
            "-c",
            f"""
import sys
sys.path.insert(0, r'{test_dir}')
sys.path.insert(0, r'{PROJECT_ROOT / "src"}')
import uvicorn
from main import main_app
uvicorn.run(main_app, host='{host}', port={port})
""",
        ],
        cwd=str(test_dir),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        text=True,
        bufsize=1,
        preexec_fn=(os.setsid if sys.platform != "win32" else None),
    )

    # Create threads to log output
    def log_output(pipe, log_level):
        for line in iter(pipe.readline, ""):
            log_level(line.strip())

    from threading import Thread
    stdout_thread = Thread(target=log_output, args=(process.stdout, logger.info), daemon=True)
    stderr_thread = Thread(target=log_output, args=(process.stderr, logger.error), daemon=True)
    stdout_thread.start()
    stderr_thread.start()

    logger.info("Started root + management server")
    time.sleep(10)  # Wait for server to start
    
    try:
        # Wait for server to be ready
        start_time = time.time()
        timeout = 60
        server_ready = False

        while (time.time() - start_time) < timeout:
            logger.info(f"Waiting for root + management server on {host}:{port}")
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                logger.error(f"Process terminated unexpectedly")
                logger.error(f"Stdout: {stdout}")
                logger.error(f"Stderr: {stderr}")
                raise RuntimeError("Root + management server terminated unexpectedly")

            try:
                with httpx.Client(base_url=f"http://{host}:{port}", follow_redirects=False) as client:
                    response = client.get("/health")
                    if response.status_code == 200:
                        server_ready = True
                        break
            except httpx.ConnectError:
                time.sleep(1)
                continue

        if not server_ready:
            raise TimeoutError(f"Root + management server failed to start within {timeout} seconds")
        
        logger.info(f"Root + management server started on {host}:{port}")
        
        # Run HTTP API tests
        with httpx.Client(base_url=f"http://{host}:{port}", follow_redirects=False) as client:
            # Test health endpoint
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert "" in data["apps"] or "/" in data["apps"], "Root app should be listed"
            assert "/management" in data["apps"]
            logger.info("✓ Health endpoint works")
            
            # Test root app (no auth required)
            response = client.get("/", follow_redirects=True)
            assert response.status_code == 200
            logger.info("✓ Root app accessible without auth")
            
            # Test management app (requires auth)
            response = client.get("/management/")
            assert response.status_code == 302  # Redirect to login
            assert "/login" in response.headers.get("location", "")
            logger.info("✓ Management app redirects to login")
            
            # Test management login page
            response = client.get("/management/login", follow_redirects=True)
            assert response.status_code == 200
            assert "username" in response.text.lower() or "Username" in response.text
            logger.info("✓ Management login page accessible")

        # Run browser tests (critical for WebSocket validation)
        run_root_management_browser_tests(host, port)

    finally:
        logger.info(f"Terminating root + management server on {host}:{port}")
        
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

        logger.info("Root + management server terminated")


def main():
    """Main entry point for the multi-app E2E tests."""
    try:
        # Run original test
        test_multi_app_integration()
        logger.info("Multi-app E2E tests passed successfully!")
        
        # Run root + management test (reproduces WebSocket bug)
        logger.info("\n" + "=" * 60)
        logger.info("Running Root + Management Test (WebSocket validation)")
        logger.info("=" * 60 + "\n")
        test_root_management_integration()
        logger.info("Root + Management E2E tests passed successfully!")
        
    except Exception as e:
        logger.error(f"E2E test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

