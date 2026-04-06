from typing import Optional, Dict
from datetime import datetime
import uuid


class TaskStatus:
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class Task:
    def __init__(self, user_id: str, corpus_id: str, model_name: str):
        self.__id = str(uuid.uuid4())
        self.__user_id = user_id
        self.__corpus_id = corpus_id
        self.__model_name = model_name
        self.__status = TaskStatus.PENDING
        self.__result: Optional[Dict] = None
        self.__created_at = datetime.utcnow()

    def set_status(self, status: str):
        self.__status = status

    def set_result(self, result: Dict):
        self.__result = result

    def get_result(self) -> Optional[Dict]:
        return self.__result
