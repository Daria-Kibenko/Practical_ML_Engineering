from __future__ import annotations
from datetime import datetime
from typing import Any, Optional

from enums import TaskStatus
from models.user import User
from models.ml_model import MLModel
from models.prediction_result import PredictionResult


class MLTask:
    """
    Задача пользователя на выполнение предсказания ML-моделью.
    Содержит входные данные, ссылки на пользователя и модель,
    статус выполнения и результат.
    """

    def __init__(
        self,
        task_id: int,
        input_data: Any,
        user: User,
        model: MLModel,
    ) -> None:
        self._task_id: int = task_id
        self._input_data: Any = input_data
        self._user: User = user
        self._model: MLModel = model
        self._status: TaskStatus = TaskStatus.PENDING
        self._result: Optional[PredictionResult] = None
        self._validation_errors: list[str] = []
        self._created_at: datetime = datetime.now()
        self._completed_at: Optional[datetime] = None

    @property
    def task_id(self) -> int:
        return self._task_id

    @property
    def user(self) -> User:
        return self._user

    @property
    def model(self) -> MLModel:
        return self._model

    @property
    def status(self) -> TaskStatus:
        return self._status

    @property
    def result(self) -> Optional[PredictionResult]:
        return self._result

    @property
    def validation_errors(self) -> list[str]:
        return list(self._validation_errors)

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def completed_at(self) -> Optional[datetime]:
        return self._completed_at

    def run(self) -> Optional[PredictionResult]:
        """
        Запустить выполнение задачи:
          1. Валидация входных данных.
          2. Проверка баланса пользователя.
          3. Выполнение предсказания (полиморфный вызов).
          4. Списание кредитов с баланса.
        """
        self._status = TaskStatus.RUNNING

        # Валидация
        is_valid, errors = self._model.validate(self._input_data)
        if not is_valid:
            self._validation_errors = errors
            self._status = TaskStatus.VALIDATION_ERROR
            self._completed_at = datetime.now()
            return None

        # Проверка баланса
        cost = self._model.cost_per_prediction
        if not self._user.has_sufficient_balance(cost):
            self._status = TaskStatus.FAILED
            self._completed_at = datetime.now()
            raise ValueError("Недостаточно средств для выполнения запроса.")

        # Предсказание
        self._result = self._model.predict(self._input_data)

        # Списание кредитов
        self._user.debit(cost)

        self._status = TaskStatus.COMPLETED
        self._completed_at = datetime.now()
        return self._result

    def __repr__(self) -> str:
        return (
            f"MLTask(id={self._task_id}, status={self._status.value}, "
            f"user={self._user.username!r}, model={self._model.name!r})"
        )
