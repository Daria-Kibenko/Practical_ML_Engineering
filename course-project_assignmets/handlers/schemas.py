"""
Pydantic-схемы для валидации запросов и сериализации ответов REST API.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


# Auth
class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, examples=["alice"])
    email: EmailStr = Field(..., examples=["alice@example.com"])
    password: str = Field(..., min_length=6, examples=["secret123"])


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str


# User
class UserResponse(BaseModel):
    user_id: int
    username: str
    email: str
    role: str
    balance: float

    model_config = {"from_attributes": True}


# Balance
class DepositRequest(BaseModel):
    amount: float = Field(..., gt=0, description="Сумма пополнения (> 0)")

    @field_validator("amount")
    @classmethod
    def round_amount(cls, v: float) -> float:
        return round(v, 2)


class BalanceResponse(BaseModel):
    user_id: int
    balance: float
    message: str = "OK"


# ML predict
class PredictRequest(BaseModel):
    input_data: Any = Field(..., description="Входные данные для ML-модели")


class PredictionResponse(BaseModel):
    task_id: int
    status: str
    predicted_label: Optional[str] = None
    confidence: Optional[float] = None
    raw_output: Optional[dict] = None
    credits_charged: float
    created_at: datetime


# History
class TaskHistoryItem(BaseModel):
    task_id: int
    model_name: str
    status: str
    credits_charged: float
    created_at: datetime
    completed_at: Optional[datetime] = None


class TransactionHistoryItem(BaseModel):
    transaction_id: int
    transaction_type: str
    amount: float
    created_at: datetime


class TasksHistoryResponse(BaseModel):
    user_id: int
    total: int
    tasks: list[TaskHistoryItem]


class TransactionsHistoryResponse(BaseModel):
    user_id: int
    total: int
    total_spent: float
    transactions: list[TransactionHistoryItem]


# ML Models list
class MLModelInfo(BaseModel):
    model_id: int
    name: str
    description: str
    cost_per_prediction: float


# Error response (единый формат)
class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    code: int
