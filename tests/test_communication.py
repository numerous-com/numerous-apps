from numerous.apps._communication import QueueCommunicationManager as CommunicationManager, CommunicationChannel as CommunicationChannel
from multiprocessing import Process

def test_to_appcommunication():
    communication_manager = CommunicationManager("test_session_id")
    communication_manager.to_app_instance.send("test_message")
    assert communication_manager.to_app_instance.receive(timeout=1) == "test_message"

def test_from_app_communication():
    communication_manager = CommunicationManager("test_session_id")
    communication_manager.from_app_instance.send("test_message")
    assert communication_manager.from_app_instance.receive(timeout=1) == "test_message"

def _process_1(communication_manager: CommunicationManager):
        communication_manager.from_app_instance.send("test_to_main")

def test_communication_manager_from_app():
    communication_manager = CommunicationManager("test_session_id")  

    process_1 = Process(target=_process_1, args=(communication_manager,))
    process_1.start()
    assert communication_manager.from_app_instance.receive(timeout=3) == "test_to_main"

    process_1.join()

def _process_2(communication_manager: CommunicationManager):
    assert communication_manager.to_app_instance.receive(timeout=3) == "test_from_main"

def test_communication_manager_to_app():
    communication_manager = CommunicationManager("test_session_id")
    communication_manager.to_app_instance.send("test_from_main")
    process_2 = Process(target=_process_2, args=(communication_manager,))
    process_2.start()
    process_2.join()

