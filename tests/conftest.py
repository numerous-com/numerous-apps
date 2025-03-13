import pytest
from unittest.mock import patch

# This will track which tests need to bypass session checks
_BYPASS_SESSION_CHECKS = False

# Define a marker to indicate tests that need real session activity checks
def pytest_configure(config):
    config.addinivalue_line(
        "markers", "real_session_checks: mark test to use real SessionManager.is_active checks"
    )

# Create a hook to dynamically patch based on test markers
@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item):
    """Set up the test environment based on markers."""
    global _BYPASS_SESSION_CHECKS
    
    # Check if this test has the real_session_checks marker
    needs_real_checks = any(marker.name == "real_session_checks" for marker in item.iter_markers())
    
    # Set the bypass flag based on test needs
    _BYPASS_SESSION_CHECKS = not needs_real_checks

# Create a patch for is_active that consults the global bypass flag
from unittest.mock import patch
from numerous.apps.session_management import SessionManager

# Store the original method
original_is_active = SessionManager.is_active

# Create a function that decides whether to bypass checks
def conditional_is_active(self):
    if _BYPASS_SESSION_CHECKS:
        return True
    else:
        # For tests with real session checks, respect both running and connections
        # but make sure active_connections is empty unless explicitly set
        if not hasattr(self, '_active_connections'):
            self._active_connections = set()
        # Call the original method
        return original_is_active(self)

# Apply the conditional patch
SessionManager.is_active = conditional_is_active

# Restore original at teardown
def pytest_unconfigure(config):
    """Restore original methods after tests complete."""
    SessionManager.is_active = original_is_active 