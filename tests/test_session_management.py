"""Tests for session management module."""

import asyncio
import time
from typing import Any, AsyncGenerator
from unittest.mock import AsyncMock, Mock, patch
import logging
import pytest
import pytest_asyncio
from typing_extensions import Protocol

from numerous.apps.models import MessageType, WidgetUpdateMessage
from numerous.apps.session_management import (
    AppState,
    CallbackHandle,
    GlobalSessionManager,
    PropertyName,
    SessionId,
    SessionManager,
    WidgetId,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class MockCommunicationChannel:
    """Mock communication channel for testing."""
    
    def __init__(self) -> None:
        self._queue: list[dict[str, Any]] = []
        self.sent_messages: list[dict[str, Any]] = []

    def receive(self, timeout: float | None = None) -> dict[str, Any]:
        """Non-blocking receive implementation."""
        if not self._queue:
            raise asyncio.QueueEmpty()
        return self._queue.pop(0)

    def receive_nowait(self) -> dict[str, Any]:
        """Non-blocking receive implementation."""
        if not self._queue:
            raise asyncio.QueueEmpty()
        return self._queue.pop(0)

    def send(self, message: dict[str, Any]) -> None:
        """Send implementation."""
        self.sent_messages.append(message)

    def empty(self) -> bool:
        """Check if queue is empty."""
        return len(self._queue) == 0

    def put_message(self, message: dict[str, Any]) -> None:
        """Helper to put a message in the queue."""
        self._queue.append(message)


class MockExecutionManager:
    """Mock execution manager for testing."""
    
    def __init__(self) -> None:
        self.from_app_instance = MockCommunicationChannel()
        self.to_app_instance = MockCommunicationChannel()
        self.communication_manager = Mock(
            from_app_instance=self.from_app_instance,
            to_app_instance=self.to_app_instance,
            stop_event=asyncio.Event()
        )
        self.started = False

    def start(self, *args: Any, **kwargs: Any) -> None:
        """Start the mock execution manager."""
        self.started = True

    async def stop(self) -> None:
        """Stop the mock execution manager."""
        self.started = False
        self.communication_manager.stop_event.set()


@pytest.fixture
def session_id() -> SessionId:
    """Fixture for session ID."""
    return SessionId("test_session")


@pytest_asyncio.fixture
async def session_manager(
    session_id: SessionId,
) -> AsyncGenerator[SessionManager, None]:
    """Fixture for session manager."""
    mock_execution_manager = MockExecutionManager()
    
    manager = SessionManager(
        session_id=session_id,
        execution_manager=mock_execution_manager
    )
    
    # Start the manager with a short timeout
    await asyncio.wait_for(manager.start(), timeout=1.0)
    
    try:
        yield manager
    finally:
        # Stop the manager with a short timeout
        try:
            await asyncio.wait_for(manager.stop(), timeout=1.0)
        except asyncio.TimeoutError:
            logger.warning("Timeout while stopping session manager")
        
        # Cancel any remaining tasks
        for task in asyncio.all_tasks():
            if task is not asyncio.current_task():
                task.cancel()
                try:
                    await asyncio.wait_for(task, timeout=0.1)
                except (asyncio.TimeoutError, asyncio.CancelledError):
                    pass


@pytest_asyncio.fixture
async def global_manager() -> AsyncGenerator[GlobalSessionManager, None]:
    """Fixture for global session manager."""
    manager = GlobalSessionManager(session_timeout=0.5, cleanup_interval=0.1)
    try:
        yield manager
    finally:
        try:
            await asyncio.wait_for(manager.shutdown(), timeout=1.0)
        except asyncio.TimeoutError:
            logger.warning("Timeout while shutting down global manager")


@pytest.mark.asyncio
async def test_session_message_processing(session_manager: SessionManager) -> None:
    """Test that session processes messages correctly."""
    received_messages: list[dict[str, Any]] = []
    message_received = asyncio.Event()
    
    async def callback(message: dict[str, Any]) -> None:
        received_messages.append(message)
        message_received.set()
    
    # Register callback
    handle = session_manager.register_callback(callback=callback)
    
    try:
        # Send test message through mock channel
        test_message = {"type": "test", "data": "value"}
        session_manager._execution_manager.from_app_instance.put_message(test_message)
        
        # Wait for message to be processed with timeout
        try:
            async with asyncio.timeout(1.0):
                await message_received.wait()
        except TimeoutError:
            pytest.fail("Timeout waiting for message to be processed")
        
        assert len(received_messages) == 1
        assert received_messages[0] == test_message
        
    finally:
        # Cleanup
        session_manager.deregister_callback(handle)


@pytest.mark.asyncio
async def test_global_manager_session_lifecycle(global_manager: GlobalSessionManager) -> None:
    """Test global manager session lifecycle."""
    session_id = SessionId("test_session")
    mock_execution_manager = MockExecutionManager()
    
    # Create session
    session = global_manager.create_session(
        session_id=session_id,
        execution_manager=mock_execution_manager
    )
    
    assert global_manager.has_session(session_id)
    assert global_manager.get_session(session_id) == session
    
    # Remove session with timeout
    try:
        await asyncio.wait_for(
            global_manager.remove_session(session_id),
            timeout=0.5
        )
    except asyncio.TimeoutError:
        logger.warning("Timeout while removing session")
    
    assert not global_manager.has_session(session_id) 