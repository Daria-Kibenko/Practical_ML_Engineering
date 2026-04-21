"""
BalanceService — единственная точка управления балансом пользователя.

Пользователь (UserORM) НЕ управляет балансом напрямую.
Все операции: пополнение, списание, получение — только через этот сервис.

Использует SELECT ... FOR UPDATE для защиты от гонки при одновременных списаниях.
"""

from typing import Optional
from sqlalchemy.orm import Session

from ..models.orm import BalanceORM, TransactionORM
from ..models.domain import TransactionType


class InsufficientFundsError(Exception):
    """Недостаточно кредитов на балансе."""


class BalanceService:

    def __init__(self, db: Session):
        self._db = db

    # Получение баланса
    def get_balance(self, user_id: int) -> BalanceORM:
        """Вернуть запись баланса. Создаёт нулевой баланс если ещё нет."""
        balance = (
            self._db.query(BalanceORM)
            .filter(BalanceORM.user_id == user_id)
            .first()
        )
        if balance is None:
            balance = BalanceORM(user_id=user_id, amount=0.0)
            self._db.add(balance)
            self._db.flush()
        return balance

    def get_amount(self, user_id: int) -> float:
        return self.get_balance(user_id).amount

    # Пополнение
    def deposit(self, user_id: int, amount: float, task_id: Optional[int] = None) -> BalanceORM:
        """Пополнить баланс. Фиксирует транзакцию."""
        if amount <= 0:
            raise ValueError("Сумма пополнения должна быть положительной")

        balance = self.get_balance(user_id)
        balance.amount += amount

        self._db.add(TransactionORM(
            user_id=user_id,
            task_id=task_id,
            type=TransactionType.DEPOSIT,
            amount=amount,
        ))
        return balance

    # Списание
    def debit(self, user_id: int, amount: float, task_id: Optional[int] = None) -> BalanceORM:
        """
        Списать кредиты с баланса.
        Использует SELECT FOR UPDATE — блокирует строку на время транзакции,
        чтобы два одновременных запроса не ушли в минус.
        """
        if amount <= 0:
            raise ValueError("Сумма списания должна быть положительной")

        # Блокируем строку баланса на время операции
        balance = (
            self._db.query(BalanceORM)
            .filter(BalanceORM.user_id == user_id)
            .with_for_update()
            .first()
        )
        if balance is None:
            raise InsufficientFundsError("Баланс пользователя не найден")

        if balance.amount < amount:
            raise InsufficientFundsError(
                f"Недостаточно кредитов. Требуется: {amount}, доступно: {balance.amount}"
            )

        balance.amount -= amount

        self._db.add(TransactionORM(
            user_id=user_id,
            task_id=task_id,
            type=TransactionType.DEBIT,
            amount=amount,
        ))
        return balance
