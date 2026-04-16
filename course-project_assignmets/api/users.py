"""
Роутер /users - информация о текущем пользователе.

GET /users/me - профиль и баланс текущего пользователя
"""
from __future__ import annotations

from fastapi import APIRouter

from dependencies import CurrentUser
from schemas import ErrorResponse, UserResponse

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/me",
    response_model=UserResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Не авторизован"},
    },
    summary="Профиль текущего пользователя",
)
def get_me(current_user: CurrentUser) -> UserResponse:
    return UserResponse(
        user_id=current_user.user_id,
        username=current_user.username,
        email=current_user.email,
        role=current_user.role,
        balance=current_user.wallet.balance if current_user.wallet else 0.0,
    )
