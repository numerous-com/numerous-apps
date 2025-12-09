"""Module for communication between app instances and the server."""

import multiprocessing
import multiprocessing.synchronize
import threading
from abc import ABC, abstractmethod
from collections.abc import Callable
from contextlib import suppress
from queue import Empty, Queue
from typing import Any


# Set start method to 'spawn' at the module level
if hasattr(multiprocessing, "set_start_method"):
    with suppress(RuntimeError):
        multiprocessing.set_start_method("spawn")


class CommunicationChannel(ABC):
    @abstractmethod
    def send(self, message: dict[str, Any]) -> None:
        """Send a message to the queue."""

    @abstractmethod
    def receive(self, timeout: float | None = None) -> Any:  # noqa: ANN401
        """Receive a message from the queue."""

    @abstractmethod
    def empty(self) -> bool:
        """Check if the queue is empty."""

    @abstractmethod
    def receive_nowait(self) -> dict[str, Any]:
        """Receive a message from the queue without waiting."""


class CommunicationManager(ABC):
    stop_event: threading.Event | multiprocessing.synchronize.Event
    from_app_instance: CommunicationChannel
    to_app_instance: CommunicationChannel

    def request_stop(self) -> None:
        """Request graceful termination of the execution."""
        if self.stop_event is not None:
            self.stop_event.set()


class ExecutionManager(ABC):
    communication_manager: CommunicationManager

    def request_stop(self) -> None:
        """Request graceful termination of the execution."""
        if (
            self.communication_manager is not None
            and self.communication_manager.stop_event is not None
        ):
            self.communication_manager.stop_event.set()

    @abstractmethod
    def is_connected(self) -> bool:
        """
        Check if the execution manager is still connected and operational.

        Returns:
            bool: True if connected and operational, False otherwise.

        """


class QueueCommunicationChannel(CommunicationChannel):
    def __init__(self, queue: Queue) -> None:  # type: ignore [type-arg]
        """Initialize the QueueCommunicationChannel."""
        self.queue = queue

    def send(self, message: Any) -> None:  # noqa: ANN401
        """Send a message to the queue."""
        self.queue.put(message)

    def receive(self, timeout: float | None = None) -> Any:  # noqa: ANN401
        """Receive a message from the queue."""
        return self.queue.get(timeout=timeout)

    def empty(self) -> bool:
        """Check if the queue is empty."""
        return self.queue.empty()

    def receive_nowait(self) -> Any:  # noqa: ANN401
        """Receive a message from the queue without waiting."""
        try:
            return self.queue.get_nowait()
        except Empty:
            return None


class QueueCommunicationManager(CommunicationManager):
    def __init__(
        self,
        stop_event: threading.Event | multiprocessing.synchronize.Event,
        queue_to_app: Queue,  # type: ignore [type-arg]
        queue_from_app: Queue,  # type: ignore [type-arg]
    ) -> None:
        """Initialize the QueueCommunicationManager."""
        super().__init__()
        self.to_app_instance = QueueCommunicationChannel(queue_to_app)
        self.from_app_instance = QueueCommunicationChannel(queue_from_app)
        self.stop_event = stop_event


class MultiProcessExecutionManager(ExecutionManager):
    process: multiprocessing.Process

    def __init__(
        self,
        target: Callable[[str, str, str, str, str, CommunicationManager], None],
        session_id: str,
    ) -> None:
        """Initialize the MultiProcessExecutionManager."""
        self.communication_manager: CommunicationManager = QueueCommunicationManager(
            stop_event=multiprocessing.Event(),
            queue_to_app=multiprocessing.Queue(),  # type: ignore [arg-type]
            queue_from_app=multiprocessing.Queue(),  # type: ignore [arg-type]
        )
        self.session_id = session_id
        self.target = target
        super().__init__()

    def is_connected(self) -> bool:
        """
        Check if the process is still running and connected.

        Returns:
            bool: True if the process exists and is alive, False otherwise.

        """
        return hasattr(self, "process") and self.process.is_alive()

    def start(
        self,
        base_dir: str,
        module_path: str,
        template: str,
        app_id: str = "",
    ) -> None:
        """Start the process."""
        if hasattr(self, "process") and self.process.is_alive():
            raise RuntimeError("Process already running")
        self.process = multiprocessing.Process(
            target=self.target,
            args=(
                self.session_id,
                base_dir,
                module_path,
                template,
                app_id,
                self.communication_manager,
            ),
            daemon=True,
        )
        self.process.start()

    def stop(self) -> None:
        """Stop the process."""
        if not hasattr(self, "process") or self.process is None:
            raise RuntimeError("Process not running")
        self.process.terminate()

    def join(self) -> None:
        """Join the process."""
        if not hasattr(self, "process") or self.process is None:
            raise RuntimeError("Process not running")
        self.process.join()
        del self.process


class ThreadedExecutionManager(ExecutionManager):
    thread: threading.Thread

    def __init__(
        self,
        target: Callable[[str, str, str, str, str, CommunicationManager], None],
        session_id: str,
    ) -> None:
        """Initialize the ThreadedExecutionManager."""
        self.communication_manager: CommunicationManager = QueueCommunicationManager(
            stop_event=threading.Event(),
            queue_to_app=Queue(),
            queue_from_app=Queue(),
        )
        self.session_id = session_id
        self.target = target

    def is_connected(self) -> bool:
        """
        Check if the thread is still running and connected.

        Returns:
            bool: True if the thread exists and is alive, False otherwise.

        """
        return hasattr(self, "thread") and self.thread.is_alive()

    def start(
        self,
        base_dir: str,
        module_path: str,
        template: str,
        app_id: str = "",
    ) -> None:
        """Start the thread."""
        if hasattr(self, "thread"):
            raise RuntimeError(
                "Thread already exists. Please join the thread before\
                starting a new one."
            )
        self.thread = threading.Thread(
            target=self.target,
            args=(
                self.session_id,
                base_dir,
                module_path,
                template,
                app_id,
                self.communication_manager,
            ),
            daemon=True,
        )
        self.thread.start()

    def stop(self) -> None:
        """Stop the thread."""
        if not hasattr(self, "thread") or self.thread is None:
            raise RuntimeError("Thread not running")
        self.communication_manager.stop_event.set()

    def join(self) -> None:
        """Join the thread."""
        if not hasattr(self, "thread") or self.thread is None:
            raise RuntimeError("Thread not running")
        self.thread.join()
        del self.thread
