"""
Pydantic-схемы для валидации входных и выходных данных API.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from ..models.domain import TaskStatus, TransactionType, UserRole


# Auth / Users
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    email: str
    role: UserRole
    created_at: datetime

    model_config = {"from_attributes": True}


# Balance — отдельная сущность
class BalanceResponse(BaseModel):
    user_id: int
    amount: float

    model_config = {"from_attributes": True}


class DepositRequest(BaseModel):
    amount: float = Field(gt=0, description="Сумма пополнения (кредитов)")


class DepositResponse(BaseModel):
    user_id: int
    amount: float       # баланс ПОСЛЕ операции
    deposited: float    # сколько добавили


# ML Predictions
class PredictRequest(BaseModel):
    model_id: int
    input_data: Dict[str, Any] = Field(
        description="Входные данные для модели в формате ключ-значение"
    )

    @field_validator("input_data")
    @classmethod
    def input_data_not_empty(cls, v: dict) -> dict:
        if not v:
            raise ValueError("input_data не может быть пустым")
        return v


class ValidationError(BaseModel):
    field: str
    error: str


class PredictResponse(BaseModel):
    task_id: int
    status: TaskStatus
    result: Optional[Dict[str, Any]] = None
    credits_charged: Optional[float] = None
    validation_errors: Optional[List[ValidationError]] = None


class MLModelResponse(BaseModel):
    id: int
    name: str
    description: str
    cost_per_prediction: float

    model_config = {"from_attributes": True}


# History
class MLTaskHistoryItem(BaseModel):
    id: int
    model_name: str
    status: TaskStatus
    credits_charged: Optional[float] = None
    result: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TransactionHistoryItem(BaseModel):
    id: int
    type: TransactionType
    amount: float
    task_id: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# Admin
class AdminDepositRequest(BaseModel):
    user_id: int
    amount: float = Field(gt=0)


class ErrorResponse(BaseModel):
    detail: str
