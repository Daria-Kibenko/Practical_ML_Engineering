from abc import ABC, abstractmethod


class BaseMetric(ABC):

    @abstractmethod
    def calculate(self, tokens: list[str]) -> float:
        pass
