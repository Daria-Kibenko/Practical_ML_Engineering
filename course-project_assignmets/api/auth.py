"""
Роутер /auth - регистрация и авторизация пользователей.

POST /auth/register - создать нового пользователя
POST /auth/login - получить токен по email + паролю
"""
from __future__ import annotations

import hashlib

from fastapi import APIRouter, HTTPException, status

from dependencies import DBSession, encode_token
from orm_models import UserORM, WalletORM
from schemas import (
    ErrorResponse,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)

router = APIRouter(prefix="/auth", tags=["Auth"])


def _hash_password(password: str) -> str:
    """SHA-256 хэш пароля (в реальном проекте используйте bcrypt)."""
    return hashlib.sha256(password.encode()).hexdigest()


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        409: {"model": ErrorResponse, "description": "Email уже занят"},
    },
    summary="Регистрация нового пользователя",
)
def register(body: RegisterRequest, db: DBSession) -> TokenResponse:
    # Проверка уникальности email
    existing = db.query(UserORM).filter(UserORM.email == body.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Пользователь с email '{body.email}' уже существует",
        )

    # Создаем кошелек
    wallet = WalletORM(balance=0.0)
    db.add(wallet)
    db.flush()  # получаем wallet.wallet_id до commit

    # Создаем пользователя
    user = UserORM(
        username=body.username,
        email=body.email,
        password_hash=_hash_password(body.password),
        role="USER",
        wallet_id=wallet.wallet_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = encode_token(user.user_id)
    return TokenResponse(
        access_token=token,
        user_id=user.user_id,
        username=user.username,
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Неверные учётные данные"},
    },
    summary="Авторизация (получение токена)",
)
def login(body: LoginRequest, db: DBSession) -> TokenResponse:
    user = db.query(UserORM).filter(UserORM.email == body.email).first()
    if user is None or user.password_hash != _hash_password(body.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
        )

    token = encode_token(user.user_id)
    return TokenResponse(
        access_token=token,
        user_id=user.user_id,
        username=user.username,
    )
