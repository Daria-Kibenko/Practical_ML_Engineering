from __future__ import annotations
from enums import UserRole


class User:
    """
    Пользователь ML-сервиса.
    Инкапсулирует данные авторизации и баланс.
    """
    def __init__(
        self,
        user_id: int,
        username: str,
        email: str,
        password_hash: str,
        role: UserRole = UserRole.USER,
        balance: float = 0.0,
    ) -> None:
        self._user_id: int = user_id
        self._username: str = username
        self._email: str = email
        self._password_hash: str = password_hash
        self._role: UserRole = role
        self._balance: float = balance

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def username(self) -> str:
        return self._username

    @property
    def email(self) -> str:
        return self._email

    @property
    def role(self) -> UserRole:
        return self._role

    @property
    def balance(self) -> float:
        return self._balance

    def is_admin(self) -> bool:
        return self._role == UserRole.ADMIN

    def deposit(self, amount: float) -> None:
        """Пополнить баланс пользователя."""
        if amount <= 0:
            raise ValueError("Сумма пополнения должна быть положительной.")
        self._balance += amount

    def debit(self, amount: float) -> None:
        """Списать средства с баланса."""
        if amount <= 0:
            raise ValueError("Сумма списания должна быть положительной.")
        if self._balance < amount:
            raise ValueError("Недостаточно средств на балансе.")
        self._balance -= amount

    def has_sufficient_balance(self, amount: float) -> bool:
        """Проверить, достаточно ли средств."""
        return self._balance >= amount

    def __repr__(self) -> str:
        return (
            f"User(id={self._user_id}, username={self._username!r}, "
            f"role={self._role.value}, balance={self._balance})"
        )


class AdminUser(User):
    """
    Администратор — расширяет базового пользователя (наследование).
    Может пополнять баланс других пользователей и просматривать все транзакции.
    """

    def __init__(
        self,
        user_id: int,
        username: str,
        email: str,
        password_hash: str,
    ) -> None:
        super().__init__(
            user_id=user_id,
            username=username,
            email=email,
            password_hash=password_hash,
            role=UserRole.ADMIN,
        )

    def top_up_user(self, target_user: User, amount: float) -> "AdminDepositTransaction":
        """Пополнить баланс указанного пользователя."""
        from models.transaction import AdminDepositTransaction
        target_user.deposit(amount)
        return AdminDepositTransaction(
            amount=amount,
            user=target_user,
            performed_by=self,
        )
