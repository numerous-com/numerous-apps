from multiprocessing import Queue
from typing import Any, Dict, Optional, Callable
from abc import ABC, abstractmethod
import json
from multiprocessing import Process

class CommunicationChannel(ABC):
    @abstractmethod
    def send(self, message: Any) -> None:
        pass

    @abstractmethod
    def receive(self, timeout: Optional[float] = None) -> Any:
        pass

    @abstractmethod
    def empty(self) -> bool:
        pass

    @abstractmethod
    def receive_nowait(self) -> Any:
        pass

    @abstractmethod
    def serialize(self) -> Dict:
        pass

    @staticmethod
    @abstractmethod
    def deserialize(data: Dict) -> "CommunicationChannel":
        pass

class CommunicationManager(ABC):

    def __init__(self, session_id:str):
        self.session_id = session_id
    
    def serialize(self) -> Dict:
        return {"session_id": self.session_id,
                }
    
    @staticmethod
    @abstractmethod
    def deserialize(data: Dict) -> "CommunicationManager":
        pass

class ExecutionManager(ABC):
    def __init__(self, target: Callable, communication_manager: CommunicationManager|None=None):

        self.target = target
        self.communication_manager = communication_manager
    
    def start(self, *args, **kwargs):
        pass
    
    def stop(self):
        pass

    def join(self):
        pass

class QueueCommunicationChannel(CommunicationChannel):
    def __init__(self, queue: Queue=None):
        self.queue = queue if queue is not None else Queue()

    def send(self, message: Any) -> None:
        self.queue.put(message)
    
    def receive(self, timeout: Optional[float] = None) -> Any:
        return self.queue.get(timeout=timeout)
    
    def empty(self) -> bool:
        return self.queue.empty()  
    
    def receive_nowait(self) -> Any:
        return self.queue.get_nowait()

    def serialize(self) -> Dict:
        return {"queue": self.queue}
    
    @staticmethod
    def deserialize(data: Dict) -> "QueueCommunicationChannel":
        return QueueCommunicationChannel(data["queue"])


class QueueCommunicationManager(CommunicationManager):
    def __init__(self, session_id:str, to_app_instance: QueueCommunicationChannel=None, from_app_instance: QueueCommunicationChannel=None):
        super().__init__(session_id)
        self.to_app_instance = to_app_instance if to_app_instance is not None else QueueCommunicationChannel()
        self.from_app_instance = from_app_instance if from_app_instance is not None else QueueCommunicationChannel()
    
    def serialize(self) -> str:
        return {
            "session_id": self.session_id,
            "to_app_instance": self.to_app_instance.serialize(),
            "from_app_instance": self.from_app_instance.serialize(),
        }
    
    @staticmethod
    def deserialize(data: str) -> "QueueCommunicationManager":
        return QueueCommunicationManager(data["session_id"], 
                                         CommunicationChannel.deserialize(data["to_app_instance"]), 
                                         CommunicationChannel.deserialize(data["from_app_instance"]))


class MultiProcessExecutionManager(ExecutionManager):
    def __init__(self, target: Callable, communication_manager: CommunicationManager|None=None):
        self.process = None
        super().__init__(target, communication_manager)

    def start(self, *args, **kwargs):
        if self.process is not None:
            raise RuntimeError("Process already running")
        self.process = Process(target=self.target, args=args, kwargs=kwargs)
        self.process.start()

    def stop(self):
        if self.process is None:
            raise RuntimeError("Process not running")
        self.process.terminate()

    def join(self):
        if self.process is None:
            raise RuntimeError("Process not running")
        self.process.join()

    

