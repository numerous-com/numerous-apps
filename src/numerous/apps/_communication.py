from abc import ABC, abstractmethod
from collections.abc import Callable
from multiprocessing import Process, Queue
from threading import Event, Thread
from typing import Any


class CommunicationChannel(ABC):
    @abstractmethod
    def send(self, message: Any) -> None:  # noqa: ANN401
        pass

    @abstractmethod
    def receive(self, timeout: float | None = None) -> Any:  # noqa: ANN401
        pass

    @abstractmethod
    def empty(self) -> bool:
        pass

    @abstractmethod
    def receive_nowait(self) -> Any:  # noqa: ANN401
        pass


class CommunicationManager(ABC):
    stop_event: Event
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


class QueueCommunicationChannel(CommunicationChannel):
    def __init__(self) -> None:
        self.queue = Queue()  # type: ignore [var-annotated]

    def send(self, message: Any) -> None:  # noqa: ANN401
        self.queue.put(message)

    def receive(self, timeout: float | None = None) -> Any:  # noqa: ANN401
        return self.queue.get(timeout=timeout)

    def empty(self) -> bool:
        return self.queue.empty()

    def receive_nowait(self) -> Any:  # noqa: ANN401
        return None


class QueueCommunicationManager(CommunicationManager):
    def __init__(self) -> None:
        super().__init__()
        self.to_app_instance = QueueCommunicationChannel()
        self.from_app_instance = QueueCommunicationChannel()
        self.stop_event = Event()


class MultiProcessExecutionManager(ExecutionManager):
    process: Process

    def __init__(
        self,
        target: Callable[[str, str, str, str, CommunicationManager], None],
        session_id: str,
    ) -> None:
        self.communication_manager: CommunicationManager = QueueCommunicationManager()
        self.session_id = session_id
        self.target = target
        super().__init__()

    def start(
        self,
        base_dir: str,
        module_path: str,
        template: str,
    ) -> None:
        if self.process is not None:
            raise RuntimeError("Process already running")
        self.process = Process(
            target=self.target,
            args=(
                self.session_id,
                base_dir,
                module_path,
                template,
                self.communication_manager,
            ),
        )
        self.process.start()

    def stop(self) -> None:
        if self.process is None:
            raise RuntimeError("Process not running")
        self.process.terminate()

    def join(self) -> None:
        if self.process is None:
            raise RuntimeError("Process not running")
        self.process.join()


class ThreadedExecutionManager(ExecutionManager):
    thread: Thread

    def __init__(
        self,
        target: Callable[[str, str, str, str, CommunicationManager], None],
        session_id: str,
    ) -> None:
        self.communication_manager: CommunicationManager = QueueCommunicationManager()
        self.session_id = session_id
        self.target = target

        self.stop_event = Event()

    def start(
        self,
        base_dir: str,
        module_path: str,
        template: str,
    ) -> None:
        if hasattr(self, "thread") and self.thread.is_alive():
            raise RuntimeError("Thread already running")
        self.thread = Thread(
            target=self.target,
            args=(
                self.session_id,
                base_dir,
                module_path,
                template,
                self.communication_manager,
            ),
            daemon=True,
        )
        self.thread.start()

    def stop(self) -> None:
        self.thread.join()

    def join(self) -> None:
        self.thread.join()
