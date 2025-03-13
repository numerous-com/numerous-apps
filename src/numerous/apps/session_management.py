"""Module for managing server sessions and communication."""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, NewType, Protocol


if TYPE_CHECKING:
    from collections.abc import Coroutine, Sequence

    from .communication import ExecutionManager

from .models import MessageType, WidgetUpdateMessage


logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

# Type aliases with NewType for better type safety
SessionId = NewType("SessionId", str)
WidgetId = NewType("WidgetId", str)
PropertyName = NewType("PropertyName", str)
CallbackHandle = NewType("CallbackHandle", str)


class MessageCallback(Protocol):
    """Protocol for message callback functions."""

    def __call__(self, message: dict[str, Any]) -> Coroutine[Any, Any, None]:
        """Call message callback."""


class MessageFilter(Protocol):
    """Protocol for message filtering functions."""

    def __call__(self, message: dict[str, Any]) -> bool:
        """Filter message."""


@dataclass
class WidgetState:
    """Represents the current state of a widget."""

    properties: dict[PropertyName, Any] = field(default_factory=dict)
    last_updated: float = field(default_factory=time.time)


@dataclass
class AppState:
    """Represents the complete state of all widgets in the app."""

    widget_states: dict[WidgetId, dict[PropertyName, Any]]
    timestamp: float


@dataclass
class CallbackRegistration:
    """Represents a registered callback."""

    callback: MessageCallback
    message_types: set[MessageType] | None
    filter_func: MessageFilter | None = None


class SessionManager:
    """Manages communication and state for a single session."""

    def __init__(
        self,
        session_id: SessionId,
        execution_manager: ExecutionManager,
    ) -> None:
        """Initialize the session manager."""
        self.session_id = session_id
        self._execution_manager = execution_manager
        self._callbacks: dict[CallbackHandle, CallbackRegistration] = {}
        self._widget_states: defaultdict[WidgetId, WidgetState] = defaultdict(
            lambda: WidgetState(properties={})
        )
        self._running = False
        self._processing_task: asyncio.Task[None] | None = None
        self._shutdown_event = asyncio.Event()
        self.last_activity_time = time.time()
        self._active_connections: set[str] = set()  # Client IDs with active connections

    def add_active_connection(self, client_id: str) -> None:
        """Track an active client connection."""
        self._active_connections.add(client_id)

    def remove_active_connection(self, client_id: str) -> None:
        """Remove a client connection that has disconnected."""
        self._active_connections.discard(client_id)

    def has_active_connections(self) -> bool:
        """Check if there are any active client connections."""
        return len(self._active_connections) > 0

    def is_active(self) -> bool:
        """Check if the session is still active."""
        # Consider a session active if it has running processes or active connections
        return self._running or self.has_active_connections()

    async def start(self) -> None:
        """Start processing messages."""
        if not self._running:
            self._running = True
            self._shutdown_event.clear()
            self._processing_task = asyncio.create_task(self._process_app_messages())

    async def stop(self) -> None:
        """Stop processing messages and clean up resources."""
        if self._running:
            # Signal shutdown
            self._running = False
            self._shutdown_event.set()

            # Cancel and wait for processing task
            if self._processing_task is not None:
                self._processing_task.cancel()
                try:
                    await self._processing_task
                except asyncio.CancelledError:
                    pass
                finally:
                    self._processing_task = None

            # Clear all callbacks
            self._callbacks.clear()

    def register_callback(
        self,
        callback: MessageCallback,
        message_types: Sequence[MessageType] | None = None,
        filter_func: MessageFilter | None = None,
    ) -> CallbackHandle:
        """Register a callback for specific message types."""
        handle = CallbackHandle(str(uuid.uuid4()))
        self._callbacks[handle] = CallbackRegistration(
            callback=callback,
            message_types=set(message_types) if message_types else None,
            filter_func=filter_func,
        )
        return handle

    def deregister_callback(self, handle: CallbackHandle) -> None:
        """Deregister a previously registered callback."""
        if handle in self._callbacks:
            del self._callbacks[handle]

    def get_widget_state(self, widget_id: WidgetId) -> dict[PropertyName, Any]:
        """Get the state of a specific widget."""
        return self._widget_states[widget_id].properties

    def get_app_state(self) -> AppState:
        """Get the complete state of the app."""
        return AppState(
            widget_states={
                wid: state.properties for wid, state in self._widget_states.items()
            },
            timestamp=time.time(),
        )

    def _update_widget_state(
        self,
        widget_id: WidgetId,
        property_name: PropertyName,
        value: Any,  # noqa: ANN401
    ) -> None:
        """Update the state of a widget."""
        self._widget_states[widget_id].properties[property_name] = value
        self._widget_states[widget_id].last_updated = time.time()

    async def _process_app_messages(self) -> None:  # noqa: PLR0912, C901
        """Process messages from app instance and distribute to callbacks."""
        try:
            while self._running:
                try:
                    # Use a longer timeout to reduce log spam
                    communication_manager = (
                        self._execution_manager.communication_manager
                    )
                    if not communication_manager.from_app_instance.empty():
                        message = communication_manager.from_app_instance.receive(
                            timeout=1.0
                        )
                    else:
                        await asyncio.sleep(0.1)
                        continue

                    self.last_activity_time = time.time()

                    # Handle widget updates
                    msg_type = message.get("type")
                    if msg_type == MessageType.WIDGET_UPDATE.value:
                        try:
                            update_msg = WidgetUpdateMessage(**message)
                            self._update_widget_state(
                                WidgetId(update_msg.widget_id),
                                PropertyName(update_msg.property),
                                update_msg.value,
                            )
                        except Exception as e:
                            logger.exception(
                                "Failed to parse WidgetUpdateMessage", exc_info=e
                            )

                    # Distribute to callbacks
                    tasks = []

                    for registration in self._callbacks.values():
                        should_call = True

                        if registration.message_types is not None:
                            message_type_values = {
                                t.value for t in registration.message_types
                            }
                            should_call = msg_type in message_type_values

                        if should_call and registration.filter_func is not None:
                            should_call = registration.filter_func(message)

                        if should_call:
                            tasks.append(registration.callback(message))

                    if tasks:
                        await asyncio.gather(*tasks)

                except TimeoutError:
                    # Check if we should shutdown
                    if self._shutdown_event.is_set():
                        break
                    continue
                except asyncio.CancelledError:
                    logger.debug("Session message processing cancelled")
                    break
                except Exception as e:
                    logger.exception("Error processing message", exc_info=e)
                    if self._shutdown_event.is_set():
                        break

        except asyncio.CancelledError:
            logger.debug("Session message processing cancelled")
        except Exception as e:
            logger.exception("Fatal error in message processing loop", exc_info=e)
        finally:
            self._running = False
            self._processing_task = None

    async def send(
        self,
        message: dict[str, Any],
        callback: MessageCallback | None = None,
        wait_for_response: bool = False,
        timeout_seconds: float | None = None,
        message_types: Sequence[MessageType] | None = None,
        correlation_id: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Send message to app instance.

        Args:
            message: Message to send
            callback: Optional async callback function to handle responses
            wait_for_response: Whether to wait for a response
            timeout_seconds: Maximum time to wait for response/callback
            message_types: Message types to filter response
            correlation_id: Correlation ID to match response

        Returns:
            Response message if wait_for_response is True, None otherwise

        Raises:
            asyncio.TimeoutError: If timeout occurs while waiting for response

        """
        self.last_activity_time = time.time()
        self._execution_manager.communication_manager.to_app_instance.send(message)

        if callback is not None:
            # Register callback with timeout if specified
            handle = self.register_callback(
                callback=callback,
                message_types=message_types,
            )

            if timeout_seconds is not None:

                async def cleanup_callback() -> None:
                    async with asyncio.timeout(timeout_seconds):
                        try:
                            await asyncio.sleep(timeout_seconds)
                        except TimeoutError:
                            pass
                        finally:
                            self.deregister_callback(handle)

                asyncio.create_task(cleanup_callback())  # noqa: RUF006
            return None

        if not wait_for_response:
            return None

        # Create future for response
        response_future: asyncio.Future[dict[str, Any]] = asyncio.Future()

        async def handle_response(msg: dict[str, Any]) -> None:
            if (
                correlation_id is not None
                and msg.get("correlation_id") != correlation_id
            ):
                return
            if not response_future.done():
                response_future.set_result(msg)

        # Register temporary callback
        handle = self.register_callback(
            callback=handle_response,  # type: ignore [arg-type]
            message_types=message_types,
        )

        try:
            if timeout_seconds is not None:
                async with asyncio.timeout(timeout_seconds):
                    return await response_future
            return await response_future
        finally:
            self.deregister_callback(handle)


class GlobalSessionManager:
    """Manages multiple sessions with global timeout and cleanup."""

    def __init__(
        self,
        session_timeout: float = 60.0,
        cleanup_interval: float = 60.0,
    ) -> None:
        """Initialize the global session manager."""
        self._sessions: dict[SessionId, SessionManager] = {}
        self._session_timeout = session_timeout
        self._cleanup_interval = cleanup_interval
        self._cleanup_task: asyncio.Task[None] | None = None
        self._lock = asyncio.Lock()
        self._shutdown_event = asyncio.Event()

    def create_session(
        self,
        session_id: SessionId,
        execution_manager: ExecutionManager,
    ) -> SessionManager:
        """Create a new session."""
        if session_id in self._sessions:
            raise ValueError(f"Session {session_id} already exists")

        session = SessionManager(
            session_id=session_id,
            execution_manager=execution_manager,
        )
        # Use the session's last_activity_time directly for timeout checks
        # instead of setting a non-existent _session_timeout attribute
        self._sessions[session_id] = session
        asyncio.create_task(session.start())  # noqa: RUF006
        return session

    def get_session(self, session_id: SessionId) -> SessionManager:
        """Get existing session."""
        if session_id not in self._sessions:
            raise ValueError(f"Session {session_id} not found")
        return self._sessions[session_id]

    async def remove_session(self, session_id: SessionId) -> None:
        """Remove a session."""
        async with self._lock:
            if session_id in self._sessions:
                logger.debug(f"Stopping session {session_id}")
                try:
                    session = self._sessions[session_id]
                    await session.stop()
                    del self._sessions[session_id]
                    logger.debug(f"Successfully removed session {session_id}")
                except Exception as e:
                    logger.exception(f"Error stopping session {session_id}", exc_info=e)
                    # Still remove from sessions dict even if stop fails
                    self._sessions.pop(session_id, None)
                    logger.debug(f"Forcibly removed session {session_id} after error")

    def has_session(self, session_id: SessionId) -> bool:
        """Check if session exists."""
        return session_id in self._sessions

    async def start_cleanup_task(self) -> None:
        """Start the session cleanup task."""
        if self._cleanup_task is None:
            self._shutdown_event.clear()
            self._cleanup_task = asyncio.create_task(self._cleanup_inactive_sessions())

    async def shutdown(self) -> None:
        """Shutdown the manager and all sessions."""
        logger.debug("Starting global manager shutdown")
        try:
            # Signal shutdown
            self._shutdown_event.set()

            # Stop cleanup task first
            if self._cleanup_task is not None:
                logger.debug("Cancelling cleanup task")
                self._cleanup_task.cancel()
                try:
                    await asyncio.wait_for(self._cleanup_task, timeout=0.5)
                except (TimeoutError, asyncio.CancelledError):
                    pass
                finally:
                    self._cleanup_task = None
                    logger.debug("Cleanup task stopped")

            # Stop all sessions with timeout
            async with self._lock:
                for session_id in list(self._sessions.keys()):
                    try:
                        logger.debug(f"Stopping session {session_id} during shutdown")
                        await asyncio.wait_for(
                            self.remove_session(session_id), timeout=0.5
                        )
                    except (TimeoutError, Exception):
                        logger.exception(f"Error stopping session {session_id}")
                        # Force remove
                        self._sessions.pop(session_id, None)

        finally:
            # Force clear sessions dict
            self._sessions.clear()
            logger.debug("Global manager shutdown complete")

    async def _cleanup_inactive_sessions(self) -> None:  # noqa: C901
        """Periodically clean up inactive sessions."""
        try:
            while not self._shutdown_event.is_set():
                try:
                    current_time = time.time()
                    logger.debug("Starting cleanup cycle")

                    # Create a list of sessions to remove
                    to_remove = []
                    async with self._lock:
                        for session_id, session in self._sessions.items():
                            inactive_time = current_time - session.last_activity_time
                            logger.debug(
                                f"Session {session_id}: \
                                    inactive for {inactive_time:.1f}s "
                                f"(timeout: {self._session_timeout}s)"
                            )
                            if inactive_time > self._session_timeout:
                                to_remove.append(session_id)

                    # Remove sessions outside the lock to prevent deadlocks
                    for session_id in to_remove:
                        if to_remove:
                            logger.info(f"Removing inactive session {session_id}")
                        try:
                            await self.remove_session(session_id)
                        except Exception as e:
                            logger.exception(
                                f"Failed to remove session {session_id}", exc_info=e
                            )
                            # Force remove from sessions dict
                            async with self._lock:
                                self._sessions.pop(session_id, None)
                                logger.debug(
                                    f"Forcibly removed session {session_id} after error"
                                )

                    # Wait for next cleanup interval or shutdown
                    try:
                        logger.debug(
                            f"Waiting {self._cleanup_interval}s for next cleanup cycle"
                        )
                        await asyncio.wait_for(
                            self._shutdown_event.wait(), timeout=self._cleanup_interval
                        )
                        if self._shutdown_event.is_set():
                            logger.debug("Shutdown event detected, stopping cleanup")
                            break
                    except TimeoutError:
                        continue  # Continue cleanup if no shutdown

                except Exception as e:
                    logger.exception("Error in cleanup loop", exc_info=e)
                    if self._shutdown_event.is_set():
                        break
                    await asyncio.sleep(0.1)  # Brief pause before retry

        except asyncio.CancelledError:
            logger.debug("Cleanup task cancelled")
        finally:
            logger.debug("Cleanup task stopped")
