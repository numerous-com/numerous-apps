import time
from multiprocessing import Process, Queue
from threading import Event

from numerous.apps._communication import (
    QueueCommunicationChannel as CommunicationChannel,
)
from numerous.apps._communication import (
    QueueCommunicationManager as CommunicationManager,
)
from numerous.apps._communication import ThreadedExecutionManager


# Create shared queues at module level
to_app_queue = Queue()
from_app_queue = Queue()

msg_from_app = "test_from_app"
msg_from_main = "test_from_main"


def _process_1(communication_manager: CommunicationManager) -> None:
    """Help process that receives from main and sends back."""
    communication_manager.from_app_instance.send(msg_from_app)
    time.sleep(0.1)  # Give main process time to receive


def _process_2(communication_manager: CommunicationManager) -> None:
    """Help process that receives from main."""
    msg = communication_manager.to_app_instance.receive(timeout=1)
    assert msg == msg_from_main
    time.sleep(0.1)  # Give main process time to verify


def _test_communication_manager_from_app() -> None:
    """Test communication from app to main process."""
    # Create communication manager with shared queues
    communication_manager = CommunicationManager("test_session_id")
    communication_manager.to_app_instance = CommunicationChannel(to_app_queue)
    communication_manager.from_app_instance = CommunicationChannel(from_app_queue)
    communication_manager.stop_event = Event()

    # Start process
    process = Process(target=_process_1, args=(communication_manager,))
    process.start()

    # Wait for message
    try:
        msg = communication_manager.from_app_instance.receive(timeout=3)
        assert msg == msg_from_app
    finally:
        process.join(timeout=1)
        if process.is_alive():
            process.terminate()


def _test_communication_manager_to_app() -> None:
    """Test communication from main to app process."""
    # Create communication manager with shared queues
    communication_manager = CommunicationManager("test_session_id")
    communication_manager.to_app_instance = CommunicationChannel(to_app_queue)
    communication_manager.from_app_instance = CommunicationChannel(from_app_queue)
    communication_manager.stop_event = Event()

    # Start process
    process = Process(target=_process_2, args=(communication_manager,))
    process.start()

    # Send message after process has started
    time.sleep(0.1)  # Give process time to start
    communication_manager.to_app_instance.send(msg_from_main)

    # Wait for process to complete
    try:
        process.join(timeout=2)  # Increased timeout
        assert process.exitcode == 0
    finally:
        if process.is_alive():
            process.terminate()


def test_threaded_execution_manager() -> None:
    """Test communication using ThreadedExecutionManager."""

    def target_function(
        session_id: str,  # noqa: ARG001
        base_dir: str,  # noqa: ARG001
        module_path: str,  # noqa: ARG001
        template: str,  # noqa: ARG001
        communication_manager: CommunicationManager,
    ) -> None:
        # Simulate receiving and responding to a message
        msg = communication_manager.to_app_instance.receive(timeout=5)
        assert msg == msg_from_main
        communication_manager.from_app_instance.send(msg_from_app)

    # Create and start the execution manager
    execution_manager = ThreadedExecutionManager(
        target=target_function, session_id="test_session_id"
    )
    execution_manager.start(
        base_dir="test_base_dir",
        module_path="test_module_path",
        template="test_template",
    )

    try:
        # Send message to thread
        execution_manager.communication_manager.to_app_instance.send(msg_from_main)

        # Wait for response
        response = execution_manager.communication_manager.from_app_instance.receive(
            timeout=5
        )
        assert response == msg_from_app

    finally:
        # Clean up
        execution_manager.request_stop()
        execution_manager.stop()
