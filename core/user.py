from datetime import datetime
import uuid


class User:
    def __init__(self, username: str, email: str):
        self.__id = str(uuid.uuid4())
        self.__username = username
        self.__email = email
        self.__created_at = datetime.utcnow()

    @property
    def id(self) -> str:
        return self.__id

    @property
    def username(self) -> str:
        return self.__username
