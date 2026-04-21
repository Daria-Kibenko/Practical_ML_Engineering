"""
Эндпоинты аутентификации: регистрация и вход.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.domain import UserRole
from ..models.orm import UserORM
from ..schemas.schemas import (
    LoginRequest, RegisterRequest, TokenResponse, UserResponse,
)
from ..services.auth_service import (
    create_access_token, get_current_user, hash_password, verify_password,
)

router = APIRouter(prefix="/auth", tags=["Авторизация"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Регистрация нового пользователя",
)
def register(body: RegisterRequest, db: Session = Depends(get_db)) -> UserORM:
    existing = db.query(UserORM).filter(UserORM.email == body.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Пользователь с таким email уже существует",
        )
    user = UserORM(
        email=body.email,
        password_hash=hash_password(body.password),
        role=UserRole.USER,
        balance=0.0,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Авторизация (получение JWT-токена)",
)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.query(UserORM).filter(UserORM.email == body.email).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Аккаунт деактивирован",
        )
    token = create_access_token(user.id)
    return TokenResponse(access_token=token)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Информация о текущем пользователе",
)
def me(current_user: UserORM = Depends(get_current_user)) -> UserORM:
    return current_user
