from __future__ import annotations


class Wallet:
    """
    Кошелек пользователя — отдельная сущность, управляющая балансом.
    """

    def __init__(self, wallet_id: int, balance: float = 0.0) -> None:
        self._wallet_id: int = wallet_id
        self._balance: float = balance

    @property
    def wallet_id(self) -> int:
        return self._wallet_id

    @property
    def balance(self) -> float:
        return self._balance

    def deposit(self, amount: float) -> None:
        """Пополнить кошелек."""
        if amount <= 0:
            raise ValueError("Сумма пополнения должна быть положительной.")
        self._balance += amount

    def debit(self, amount: float) -> None:
        """Списать средства с кошелька."""
        if amount <= 0:
            raise ValueError("Сумма списания должна быть положительной.")
        if self._balance < amount:
            raise ValueError("Недостаточно средств на балансе.")
        self._balance -= amount

    def has_sufficient_balance(self, amount: float) -> bool:
        """Проверить, достаточно ли средств."""
        return self._balance >= amount

    def __repr__(self) -> str:
        return f"Wallet(id={self._wallet_id}, balance={self._balance})"
