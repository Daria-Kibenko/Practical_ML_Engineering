from datetime import datetime
import uuid


class Prediction:
    def __init__(self, task_id: str, result: dict):
        self.__id = str(uuid.uuid4())
        self.__task_id = task_id
        self.__result = result
        self.__created_at = datetime.utcnow()

    def get_result(self) -> dict:
        return self.__result
