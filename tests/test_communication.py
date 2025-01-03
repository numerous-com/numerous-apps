import time
from multiprocessing import Process, Queue
from threading import Event
import pytest
import pickle

from numerous.apps._communication import (
    QueueCommunicationChannel as CommunicationChannel,
)
from numerous.apps._communication import (
    QueueCommunicationManager as CommunicationManager,
)
from numerous.apps._communication import ThreadedExecutionManager
from numerous.apps._communication import (
    QueueCommunicationChannel,
    QueueCommunicationManager,
    MultiProcessExecutionManager,
)


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


# Test QueueCommunicationChannel
def test_queue_communication_channel():
    channel = QueueCommunicationChannel()
    assert channel.empty() is True

    channel.send({"key": "value"})
    assert channel.empty() is False

    message = channel.receive(timeout=1)
    assert message == {"key": "value"}

    assert channel.empty() is True

    # Test receive_nowait
    assert channel.receive_nowait() is None


# Test QueueCommunicationManager
def test_queue_communication_manager():
    manager = QueueCommunicationManager()
    assert isinstance(manager.to_app_instance, QueueCommunicationChannel)
    assert isinstance(manager.from_app_instance, QueueCommunicationChannel)
    assert isinstance(manager.stop_event, Event)


def dummy_target(*args):
    pass


def _test_multi_process_execution_manager():
    manager = MultiProcessExecutionManager(target=dummy_target, session_id="test")
    manager.start("base_dir", "module_path", "template")

    with pytest.raises(RuntimeError):
        manager.start("base_dir", "module_path", "template")

    manager.stop()
    manager.join()

    with pytest.raises(RuntimeError):
        manager.stop()

    with pytest.raises(RuntimeError):
        manager.join()


# Test ThreadedExecutionManager
def test_threaded_execution_manager():
    def dummy_target(*args):
        pass

    manager = ThreadedExecutionManager(target=dummy_target, session_id="test")
    manager.start("base_dir", "module_path", "template")

    with pytest.raises(RuntimeError):
        manager.start("base_dir", "module_path", "template")

    manager.request_stop()
    manager.stop()
    manager.join()

    with pytest.raises(RuntimeError):
        manager.stop()

    with pytest.raises(RuntimeError):
        manager.join()


def _test_queue_communication_manager_pickle():
    manager = QueueCommunicationManager()

    # Serialize the manager
    pickled_manager = pickle.dumps(manager)

    # Deserialize the manager
    unpickled_manager = pickle.loads(pickled_manager)

    # Check that the unpickled manager is an instance of QueueCommunicationManager
    assert isinstance(unpickled_manager, QueueCommunicationManager)

    # Optionally, check that the attributes are correctly restored
    assert isinstance(unpickled_manager.to_app_instance, QueueCommunicationChannel)
    assert isinstance(unpickled_manager.from_app_instance, QueueCommunicationChannel)
    assert isinstance(unpickled_manager.stop_event, Event)
