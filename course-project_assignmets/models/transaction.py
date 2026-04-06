from __future__ import annotations
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from enums import TransactionType
from models.user import User

if TYPE_CHECKING:
    from models.ml_task import MLTask
    from models.user import AdminUser


class Transaction(ABC):
    """Базовый абстрактный класс транзакции."""

    def __init__(
        self,
        transaction_id: int,
        amount: float,
        user: User,
        ml_task: Optional["MLTask"] = None,
    ) -> None:
        self._transaction_id: int = transaction_id
        self._amount: float = amount
        self._user: User = user
        self._ml_task: Optional["MLTask"] = ml_task
        self._created_at: datetime = datetime.now()
        self._transaction_type: TransactionType = self._get_type()

    @property
    def transaction_id(self) -> int:
        return self._transaction_id

    @property
    def amount(self) -> float:
        return self._amount

    @property
    def user(self) -> User:
        return self._user

    @property
    def ml_task(self) -> Optional["MLTask"]:
        return self._ml_task

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def transaction_type(self) -> TransactionType:
        return self._transaction_type

    @abstractmethod
    def _get_type(self) -> TransactionType:
        """Вернуть тип транзакции (полиморфизм)."""
        return 0

    @abstractmethod
    def apply(self) -> None:
        """Применить транзакцию к балансу."""
        return 0

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(id={self._transaction_id}, "
            f"amount={self._amount}, user={self._user.username!r})"
        )


class DepositTransaction(Transaction):
    """Пополнение баланса самим пользователем."""

    def __init__(self, transaction_id: int, amount: float, user: User) -> None:
        super().__init__(transaction_id=transaction_id, amount=amount, user=user)

    def _get_type(self) -> TransactionType:
        return TransactionType.DEPOSIT

    def apply(self) -> None:
        self._user.deposit(self._amount)


class DebitTransaction(Transaction):
    """Списание кредитов за ML-запрос."""

    def __init__(
        self,
        transaction_id: int,
        amount: float,
        user: User,
        ml_task: "MLTask",
    ) -> None:
        super().__init__(
            transaction_id=transaction_id,
            amount=amount,
            user=user,
            ml_task=ml_task,
        )

    def _get_type(self) -> TransactionType:
        return TransactionType.DEBIT

    def apply(self) -> None:
        self._user.debit(self._amount)


class AdminDepositTransaction(Transaction):
    """Пополнение баланса пользователя администратором."""

    def __init__(
        self,
        amount: float,
        user: User,
        performed_by: "AdminUser",
        transaction_id: int = 0,
    ) -> None:
        self._performed_by: "AdminUser" = performed_by
        super().__init__(transaction_id=transaction_id, amount=amount, user=user)

    def _get_type(self) -> TransactionType:
        return TransactionType.ADMIN_DEPOSIT

    def apply(self) -> None:
        self._user.deposit(self._amount)

    @property
    def performed_by(self) -> "AdminUser":
        return self._performed_by
