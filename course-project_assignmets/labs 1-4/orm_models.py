"""
SQLAlchemy ORM-модели (объединенная версия).
Сочетает лучшие практики из двух подходов:
- современный стиль SQLAlchemy 2.0 (Mapped, mapped_column)
- отдельная модель Wallet для управления балансом
- все поля из обоих исходных вариантов
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class WalletORM(Base):
    """Кошелёк пользователя для хранения баланса и истории транзакций."""
    __tablename__ = "wallets"

    wallet_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    balance: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Связи
    user: Mapped["UserORM"] = relationship("UserORM", back_populates="wallet", uselist=False)
    transactions: Mapped[List["TransactionORM"]] = relationship(
        "TransactionORM", back_populates="wallet"
    )


class UserORM(Base):
    """Пользователь системы."""
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="USER", nullable=False)  # USER, ADMIN, ...
    wallet_id: Mapped[Optional[int]] = mapped_column(ForeignKey("wallets.wallet_id"), nullable=True)

    # Связи
    wallet: Mapped[Optional["WalletORM"]] = relationship("WalletORM", back_populates="user")
    tasks: Mapped[List["MLTaskORM"]] = relationship("MLTaskORM", back_populates="user")


class MLModelORM(Base):
    """Модель машинного обучения, доступная для выполнения задач."""
    __tablename__ = "ml_models"

    model_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, default="")
    cost_per_prediction: Mapped[float] = mapped_column(Float, default=1.0)   # стоимость одного предсказания
    model_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # "classification", "regression"

    # Связи
    tasks: Mapped[List["MLTaskORM"]] = relationship("MLTaskORM", back_populates="model")


class MLTaskORM(Base):
    """Задача на выполнение предсказания."""
    __tablename__ = "ml_tasks"

    task_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), nullable=False)
    model_id: Mapped[int] = mapped_column(ForeignKey("ml_models.model_id"), nullable=False)
    input_data: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="PENDING")  # PENDING, PROCESSING, COMPLETED, FAILED
    credits_used: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # количество потраченных кредитов
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Связи
    user: Mapped["UserORM"] = relationship("UserORM", back_populates="tasks")
    model: Mapped["MLModelORM"] = relationship("MLModelORM", back_populates="tasks")
    result: Mapped[Optional["PredictionResultORM"]] = relationship(
        "PredictionResultORM", back_populates="task", uselist=False
    )
    transactions: Mapped[List["TransactionORM"]] = relationship(
        "TransactionORM", back_populates="ml_task"
    )


class PredictionResultORM(Base):
    """Результат выполнения задачи предсказания."""
    __tablename__ = "prediction_results"

    result_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("ml_tasks.task_id"), nullable=False, unique=True)
    predicted_label: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)  # для классификации
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)          # уверенность
    raw_output: Mapped[str] = mapped_column(Text, default="{}")                        # JSON-строка с полным выводом
    output_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)            # альтернативное поле для результата
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Связи
    task: Mapped["MLTaskORM"] = relationship("MLTaskORM", back_populates="result")


class TransactionORM(Base):
    """Транзакция по списанию или пополнению средств кошелька."""
    __tablename__ = "transactions"

    transaction_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    wallet_id: Mapped[int] = mapped_column(ForeignKey("wallets.wallet_id"), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)          # положительная или отрицательная сумма
    transaction_type: Mapped[str] = mapped_column(String(30), nullable=False)  # DEPOSIT, WITHDRAW, PREDICTION_COST
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)     # пояснение (например, "пополнение баланса")
    ml_task_id: Mapped[Optional[int]] = mapped_column(ForeignKey("ml_tasks.task_id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Связи
    wallet: Mapped["WalletORM"] = relationship("WalletORM", back_populates="transactions")
    ml_task: Mapped[Optional["MLTaskORM"]] = relationship("MLTaskORM", back_populates="transactions")

