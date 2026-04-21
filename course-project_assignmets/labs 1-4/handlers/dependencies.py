"""
FastAPI-зависимости (Depends).
Содержит: получение сессии БД, декодирование токена, получение текущего пользователя.

Аутентификация - упрощённая (base64-encoded user_id) согласно заданию.
JWT будет добавлен на следующем этапе.
"""
from __future__ import annotations

import base64
import binascii
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from database import SessionLocal
from orm_models import UserORM

bearer_scheme = HTTPBearer(auto_error=False)


# DB session
def get_db() -> Session:  # type: ignore[return]
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


DBSession = Annotated[Session, Depends(get_db)]


# Simple token helpers
# (token = base64(user_id); JWT будет добавлен позже)
def encode_token(user_id: int) -> str:
    """Кодировать идентификатор пользователя в токен."""
    return base64.urlsafe_b64encode(str(user_id).encode()).decode()


def decode_token(token: str) -> int:
    """Декодировать токен → user_id. Выбросить 401 при невалидном токене."""
    try:
        user_id = int(base64.urlsafe_b64decode(token.encode()).decode())
        return user_id
    except (binascii.Error, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невалидный токен авторизации",
            headers={"WWW-Authenticate": "Bearer"},
        )


# Current user dependency
def get_current_user(
    db: DBSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)] = None,
) -> UserORM:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется авторизация",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = decode_token(credentials.credentials)
    user = db.get(UserORM, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден",
        )
    return user


CurrentUser = Annotated[UserORM, Depends(get_current_user)]
