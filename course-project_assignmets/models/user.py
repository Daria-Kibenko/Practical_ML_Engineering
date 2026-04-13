from __future__ import annotations
from enums import UserRole
from models.wallet import Wallet


class User:
    """
    Пользователь ML-сервиса.
    Отвечает только за аутентификацию и роль.
    Баланс вынесен в отдельную сущность Wallet.
    """

    def __init__(
        self,
        user_id: int,
        username: str,
        email: str,
        password_hash: str,
        wallet: Wallet,
        role: UserRole = UserRole.USER,
    ) -> None:
        self._user_id: int = user_id
        self._username: str = username
        self._email: str = email
        self._password_hash: str = password_hash
        self._role: UserRole = role
        self._wallet: Wallet = wallet

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
    def wallet(self) -> Wallet:
        """Доступ к кошельку пользователя."""
        return self._wallet

    def is_admin(self) -> bool:
        return self._role == UserRole.ADMIN

    def __repr__(self) -> str:
        return (
            f"User(id={self._user_id}, username={self._username!r}, "
            f"role={self._role.value}, wallet={self._wallet!r})"
        )


class AdminUser(User):
    """
    Администратор — расширяет базового пользователя.
    Может пополнять баланс других пользователей через их кошельки.
    """

    def __init__(
        self,
        user_id: int,
        username: str,
        email: str,
        password_hash: str,
        wallet: Wallet,
    ) -> None:
        super().__init__(
            user_id=user_id,
            username=username,
            email=email,
            password_hash=password_hash,
            wallet=wallet,
            role=UserRole.ADMIN,
        )

    def top_up_user(self, target_user: User, amount: float) -> "AdminDepositTransaction":
        """
        Пополнить баланс указанного пользователя.
        Работает через кошелек пользователя.
        """
        from models.transaction import AdminDepositTransaction
        target_user.wallet.deposit(amount)
        return AdminDepositTransaction(
            amount=amount,
            user=target_user,
            performed_by=self,
        )
