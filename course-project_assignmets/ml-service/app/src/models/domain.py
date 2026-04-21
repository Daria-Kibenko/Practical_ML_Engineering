"""
Задание №1 — Объектная модель ML-сервиса.

Базовые сущности:
  - User           — пользователь с балансом и ролью
  - MLModel        — ML-модель со стоимостью предсказания
  - MLTask         — задача на предсказание
  - PredictionResult — результат предсказания
  - Transaction (ABC) / DepositTransaction / DebitTransaction — транзакции

Применены принципы ООП:
  - Инкапсуляция   : все поля приватные (_field), доступ через @property
  - Наследование   : Transaction → DepositTransaction / DebitTransaction
  - Полиморфизм    : метод apply() реализован по-разному в каждом подклассе
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Optional, List


# Перечисления
class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"


class TransactionType(str, Enum):
    DEPOSIT = "deposit"   # пополнение
    DEBIT = "debit"       # списание


class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# Транзакции (Наследование + Полиморфизм)
class Transaction(ABC):
    """Базовый абстрактный класс транзакции."""

    def __init__(self, amount: float, user_id: int, task_id: Optional[int] = None):
        self._amount: float = amount
        self._user_id: int = user_id
        self._task_id: Optional[int] = task_id
        self._created_at: datetime = datetime.utcnow()

    @property
    def amount(self) -> float:
        return self._amount

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def task_id(self) -> Optional[int]:
        return self._task_id

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @abstractmethod
    def apply(self, user: "User") -> None:
        raise NotImplementedError

    @abstractmethod
    def get_type(self) -> TransactionType:
        raise NotImplementedError


class DepositTransaction(Transaction):
    """Пополнение баланса."""

    def apply(self, user: "User") -> None:
        user.balance += self._amount

    def get_type(self) -> TransactionType:
        return TransactionType.DEPOSIT


class DebitTransaction(Transaction):
    """Списание кредитов с баланса."""

    def apply(self, user: "User") -> None:
        if user.balance < self._amount:
            raise ValueError("Недостаточно кредитов на балансе")
        user.balance -= self._amount

    def get_type(self) -> TransactionType:
        return TransactionType.DEBIT


# Пользователь
class User:
    """Пользователь системы."""

    def __init__(
        self,
        email: str,
        password_hash: str,
        role: UserRole = UserRole.USER,
        balance: float = 0.0,
        user_id: Optional[int] = None,
    ):
        self._id: Optional[int] = user_id
        self._email: str = email
        self._password_hash: str = password_hash
        self._role: UserRole = role
        self._balance: float = balance

    @property
    def id(self) -> Optional[int]:
        return self._id

    @property
    def email(self) -> str:
        return self._email

    @property
    def role(self) -> UserRole:
        return self._role

    @property
    def password_hash(self) -> str:
        return self._password_hash

    @property
    def balance(self) -> float:
        return self._balance

    @balance.setter
    def balance(self, value: float) -> None:
        if value < 0:
            raise ValueError("Баланс не может быть отрицательным")
        self._balance = value

    def deposit(self, amount: float) -> DepositTransaction:
        if amount <= 0:
            raise ValueError("Сумма пополнения должна быть положительной")
        tx = DepositTransaction(amount=amount, user_id=self._id)  # type: ignore[arg-type]
        tx.apply(self)
        return tx

    def debit(self, amount: float, task_id: Optional[int] = None) -> DebitTransaction:
        if amount <= 0:
            raise ValueError("Сумма списания должна быть положительной")
        tx = DebitTransaction(amount=amount, user_id=self._id, task_id=task_id)  # type: ignore[arg-type]
        tx.apply(self)
        return tx

    def is_admin(self) -> bool:
        return self._role == UserRole.ADMIN


# ML-модель
class MLModel:
    """Описание ML-модели, доступной для предсказаний."""

    def __init__(
        self,
        name: str,
        description: str,
        cost_per_prediction: float,
        model_id: Optional[int] = None,
    ):
        self._id: Optional[int] = model_id
        self._name: str = name
        self._description: str = description
        self._cost_per_prediction: float = cost_per_prediction

    @property
    def id(self) -> Optional[int]:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def cost_per_prediction(self) -> float:
        return self._cost_per_prediction

    def predict(self, input_data: dict) -> dict:
        """
        Выполнить предсказание (mock-реализация).
        В реальной системе здесь был бы вызов настоящей ML-модели.
        """
        values = list(input_data.values())
        numeric = [v for v in values if isinstance(v, (int, float))]
        score = (sum(numeric) / len(numeric)) if numeric else 0.5
        return {
            "model": self._name,
            "prediction": "positive" if score > 0 else "negative",
            "confidence": round(min(abs(score) / 10 + 0.5, 0.99), 2),
            "features_used": list(input_data.keys()),
        }


# ML-задача
class MLTask:
    """Задача на выполнение предсказания."""

    def __init__(
        self,
        user_id: int,
        model_id: int,
        input_data: dict,
        task_id: Optional[int] = None,
    ):
        self._id: Optional[int] = task_id
        self._user_id: int = user_id
        self._model_id: int = model_id
        self._input_data: dict = input_data
        self._status: TaskStatus = TaskStatus.PENDING
        self._created_at: datetime = datetime.utcnow()
        self._result: Optional["PredictionResult"] = None

    @property
    def id(self) -> Optional[int]:
        return self._id

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def model_id(self) -> int:
        return self._model_id

    @property
    def input_data(self) -> dict:
        return self._input_data

    @property
    def status(self) -> TaskStatus:
        return self._status

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def result(self) -> Optional["PredictionResult"]:
        return self._result

    def start_processing(self) -> None:
        self._status = TaskStatus.PROCESSING

    def complete(self, result: "PredictionResult") -> None:
        self._status = TaskStatus.COMPLETED
        self._result = result

    def fail(self) -> None:
        self._status = TaskStatus.FAILED


# Результат предсказания
class PredictionResult:
    """Результат выполнения ML-задачи."""

    def __init__(
        self,
        task_id: int,
        output_data: dict,
        credits_charged: float,
        result_id: Optional[int] = None,
    ):
        self._id: Optional[int] = result_id
        self._task_id: int = task_id
        self._output_data: dict = output_data
        self._credits_charged: float = credits_charged
        self._created_at: datetime = datetime.utcnow()

    @property
    def id(self) -> Optional[int]:
        return self._id

    @property
    def task_id(self) -> int:
        return self._task_id

    @property
    def output_data(self) -> dict:
        return self._output_data

    @property
    def credits_charged(self) -> float:
        return self._credits_charged

    @property
    def created_at(self) -> datetime:
        return self._created_at
