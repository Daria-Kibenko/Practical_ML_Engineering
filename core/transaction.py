from datetime import datetime
import uuid


class Transaction:
    def __init__(self, user_id: str, amount: float):
        self.__id = str(uuid.uuid4())
        self.__user_id = user_id
        self.__amount = amount
        self.__timestamp = datetime.utcnow()
