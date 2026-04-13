from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Text
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime
from enums.roles import UserRole
from enums.transaction_type import TransactionType
from enums.task_status import TaskStatus

Base = declarative_base()


class UserORM(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.USER)
    balance = Column(Integer, default=0)

    transactions = relationship("TransactionORM", back_populates="user", cascade="all, delete-orphan")
    tasks = relationship("MLTaskORM", back_populates="user", cascade="all, delete-orphan")


class MLModelORM(Base):
    __tablename__ = "ml_models"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    cost_per_request = Column(Integer, nullable=False)
    model_type = Column(String(50))   # "classification" / "regression"

    tasks = relationship("MLTaskORM", back_populates="model")


class MLTaskORM(Base):
    __tablename__ = "ml_tasks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    model_id = Column(Integer, ForeignKey("ml_models.id"), nullable=False)
    input_data = Column(Text)
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING)
    credits_used = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    user = relationship("UserORM", back_populates="tasks")
    model = relationship("MLModelORM", back_populates="tasks")
    result = relationship("PredictionResultORM", back_populates="task", uselist=False)


class PredictionResultORM(Base):
    __tablename__ = "prediction_results"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("ml_tasks.id"), unique=True, nullable=False)
    output_data = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    task = relationship("MLTaskORM", back_populates="result")


class TransactionORM(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Integer, nullable=False)   # положительный для пополнения, отрицательный для списания
    type = Column(Enum(TransactionType), nullable=False)
    description = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)

    user = relationship("UserORM", back_populates="transactions")
