"""
Задание №3 — ORM-модели (SQLAlchemy).

Таблицы:
  - users              — учётные данные и роль
  - balances           — баланс пользователя (отдельная сущность)
  - ml_models          — доступные ML-модели
  - ml_tasks           — задачи на предсказание
  - prediction_results — результаты предсказаний
  - transactions       — история операций с балансом
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean, DateTime, Enum, Float, ForeignKey,
    Integer, JSON, String, func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from .domain import TaskStatus, TransactionType, UserRole


class Base(DeclarativeBase):
    pass


# Пользователи (только идентификация и роль — без баланса)
class UserORM(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False, default=UserRole.USER)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Связи
    balance: Mapped[Optional["BalanceORM"]] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    tasks: Mapped[List["MLTaskORM"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    transactions: Mapped[List["TransactionORM"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"


# Баланс — отдельная сущность (1-к-1 с пользователем)
class BalanceORM(Base):
    """
    Хранит текущий баланс пользователя.
    Вынесен в отдельную таблицу, чтобы:
      - изменения баланса не «загрязняли» основную запись пользователя;
      - можно было добавить блокировку строки (SELECT ... FOR UPDATE) при списании;
      - история баланса могла развиваться независимо.
    """
    __tablename__ = "balances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Связи
    user: Mapped["UserORM"] = relationship(back_populates="balance")

    def __repr__(self) -> str:
        return f"<Balance user_id={self.user_id} amount={self.amount}>"


# ML-модели
class MLModelORM(Base):
    __tablename__ = "ml_models"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
    cost_per_prediction: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    tasks: Mapped[List["MLTaskORM"]] = relationship(back_populates="model")

    def __repr__(self) -> str:
        return f"<MLModel id={self.id} name={self.name} cost={self.cost_per_prediction}>"


# ML-задачи
class MLTaskORM(Base):
    __tablename__ = "ml_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    model_id: Mapped[int] = mapped_column(Integer, ForeignKey("ml_models.id"), nullable=False)
    input_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus), nullable=False, default=TaskStatus.PENDING)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Связи
    user: Mapped["UserORM"] = relationship(back_populates="tasks")
    model: Mapped["MLModelORM"] = relationship(back_populates="tasks")
    result: Mapped[Optional["PredictionResultORM"]] = relationship(
        back_populates="task", uselist=False, cascade="all, delete-orphan"
    )
    transaction: Mapped[Optional["TransactionORM"]] = relationship(
        back_populates="task", uselist=False
    )

    def __repr__(self) -> str:
        return f"<MLTask id={self.id} user_id={self.user_id} status={self.status}>"


# Результаты предсказаний
class PredictionResultORM(Base):
    __tablename__ = "prediction_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ml_tasks.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    output_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    credits_charged: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    task: Mapped["MLTaskORM"] = relationship(back_populates="result")

    def __repr__(self) -> str:
        return f"<PredictionResult id={self.id} task_id={self.task_id}>"


# Транзакции
class TransactionORM(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    task_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("ml_tasks.id"), nullable=True)
    type: Mapped[TransactionType] = mapped_column(Enum(TransactionType), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Связи
    user: Mapped["UserORM"] = relationship(back_populates="transactions")
    task: Mapped[Optional["MLTaskORM"]] = relationship(back_populates="transaction")

    def __repr__(self) -> str:
        return f"<Transaction id={self.id} type={self.type} amount={self.amount}>"
