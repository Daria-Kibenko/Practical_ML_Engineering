from abc import ABC, abstractmethod
from typing import Dict


class BaseModel(ABC):

    @abstractmethod
    def analyze(self, tokens: list[str]) -> Dict[str, float]:
        pass

    @abstractmethod
    def name(self) -> str:
        pass
