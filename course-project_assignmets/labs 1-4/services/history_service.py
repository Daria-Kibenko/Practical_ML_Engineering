from __future__ import annotations
from typing import Optional

from enums import TaskStatus, TransactionType
from models.user import User
from models.ml_task import MLTask
from models.transaction import Transaction


class MLRequestHistory:
    """
    Хранит историю всех ML-задач и транзакций конкретного пользователя.
    """

    def __init__(self, user: User) -> None:
        self._user: User = user
        self._tasks: list[MLTask] = []
        self._transactions: list[Transaction] = []

    @property
    def user(self) -> User:
        return self._user

    def add_task(self, task: MLTask) -> None:
        self._tasks.append(task)

    def add_transaction(self, transaction: Transaction) -> None:
        self._transactions.append(transaction)

    def get_tasks(self, status: Optional[TaskStatus] = None) -> list[MLTask]:
        if status is None:
            return list(self._tasks)
        return [t for t in self._tasks if t.status == status]

    def get_transactions(
        self,
        transaction_type: Optional[TransactionType] = None,
    ) -> list[Transaction]:
        if transaction_type is None:
            return list(self._transactions)
        return [t for t in self._transactions if t.transaction_type == transaction_type]

    def total_spent(self) -> float:
        """Суммарно списано кредитов за все предсказания."""
        return sum(
            t.amount
            for t in self._transactions
            if t.transaction_type == TransactionType.DEBIT
        )

    def __repr__(self) -> str:
        return (
            f"MLRequestHistory(user={self._user.username!r}, "
            f"tasks={len(self._tasks)}, transactions={len(self._transactions)})"
        )
