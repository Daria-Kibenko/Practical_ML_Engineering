from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any

from models.prediction_result import PredictionResult


class MLModel(ABC):
    """
    Абстрактная ML-модель.
    Задает контракт для конкретных реализаций (полиморфизм).
    """

    def __init__(
        self,
        model_id: int,
        name: str,
        description: str,
        cost_per_prediction: float,
    ) -> None:
        self._model_id: int = model_id
        self._name: str = name
        self._description: str = description
        self._cost_per_prediction: float = cost_per_prediction

    @property
    def model_id(self) -> int:
        return self._model_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def cost_per_prediction(self) -> float:
        return self._cost_per_prediction

    @abstractmethod
    def predict(self, input_data: Any) -> PredictionResult:
        """Выполнить предсказание над входными данными."""
        return 0

    @abstractmethod
    def validate(self, input_data: Any) -> tuple[bool, list[str]]:
        """
        Валидировать входные данные.
        Возвращает (is_valid, список_ошибок).
        """
        return 0

    def __repr__(self) -> str:
        return f"MLModel(id={self._model_id}, name={self._name!r})"


class ClassificationModel(MLModel):
    """Конкретная модель классификации."""

    def predict(self, input_data: Any) -> PredictionResult:
        return PredictionResult(
            predicted_label=str(input_data),
            confidence=0.95,
            raw_output={"label": str(input_data), "score": 0.95},
        )

    def validate(self, input_data: Any) -> tuple[bool, list[str]]:
        errors: list[str] = []
        if input_data is None:
            errors.append("Входные данные не могут быть None.")
        return len(errors) == 0, errors


class RegressionModel(MLModel):
    """Конкретная модель регрессии."""

    def predict(self, input_data: Any) -> PredictionResult:
        return PredictionResult(
            predicted_label=None,
            confidence=None,
            raw_output={"value": 0.0},
        )

    def validate(self, input_data: Any) -> tuple[bool, list[str]]:
        errors: list[str] = []
        if not isinstance(input_data, (list, dict)):
            errors.append("Ожидается список или словарь числовых признаков.")
        return len(errors) == 0, errors
