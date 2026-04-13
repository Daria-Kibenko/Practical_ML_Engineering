from __future__ import annotations
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from enums import TransactionType
from models.user import User
from models.wallet import Wallet

if TYPE_CHECKING:
    from models.ml_task import MLTask
    from models.user import AdminUser


class Transaction(ABC):
    """Базовый абстрактный класс транзакции."""

    def __init__(
        self,
        transaction_id: int,
        amount: float,
        wallet: Wallet,
        ml_task: Optional["MLTask"] = None,
    ) -> None:
        self._transaction_id: int = transaction_id
        self._amount: float = amount
        self._wallet: Wallet = wallet
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
    def wallet(self) -> Wallet:
        return self._wallet

    @property
    def user(self) -> User:
        """Для обратной совместимости - получаем пользователя из кошелька."""
        raise NotImplementedError(
            "Доступ к пользователю через транзакцию удалён. Используйте свойство .wallet"
        )

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
        pass

    @abstractmethod
    def apply(self) -> None:
        """Применить транзакцию к кошельку."""
        pass

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(id={self._transaction_id}, "
            f"amount={self._amount}, wallet_id={self._wallet.wallet_id})"
        )


class DepositTransaction(Transaction):
    """Пополнение баланса самим пользователем (через его кошелёк)."""

    def __init__(self, transaction_id: int, amount: float, wallet: Wallet) -> None:
        super().__init__(transaction_id=transaction_id, amount=amount, wallet=wallet)

    def _get_type(self) -> TransactionType:
        return TransactionType.DEPOSIT

    def apply(self) -> None:
        self._wallet.deposit(self._amount)


class DebitTransaction(Transaction):
    """Списание кредитов за ML-запрос (из кошелька)."""

    def __init__(
        self,
        transaction_id: int,
        amount: float,
        wallet: Wallet,
        ml_task: "MLTask",
    ) -> None:
        super().__init__(
            transaction_id=transaction_id,
            amount=amount,
            wallet=wallet,
            ml_task=ml_task,
        )

    def _get_type(self) -> TransactionType:
        return TransactionType.DEBIT

    def apply(self) -> None:
        self._wallet.debit(self._amount)


class AdminDepositTransaction(Transaction):
    """Пополнение баланса пользователя администратором (через кошелёк пользователя)."""

    def __init__(
        self,
        transaction_id: int,
        amount: float,
        wallet: Wallet,
        performed_by: "AdminUser",
    ) -> None:
        self._performed_by: "AdminUser" = performed_by
        super().__init__(transaction_id=transaction_id, amount=amount, wallet=wallet)

    def _get_type(self) -> TransactionType:
        return TransactionType.ADMIN_DEPOSIT

    def apply(self) -> None:
        self._wallet.deposit(self._amount)

    @property
    def performed_by(self) -> "AdminUser":
        return self._performed_by
