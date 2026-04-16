"""
Роутер /balance — работа с балансом пользователя.

GET  /balance          — текущий баланс
POST /balance/deposit  — пополнение баланса
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from dependencies import CurrentUser, DBSession
from orm_models import TransactionORM
from schemas import BalanceResponse, DepositRequest, ErrorResponse

router = APIRouter(prefix="/balance", tags=["Balance"])


@router.get(
    "",
    response_model=BalanceResponse,
    responses={401: {"model": ErrorResponse}},
    summary="Получить текущий баланс",
)
def get_balance(current_user: CurrentUser) -> BalanceResponse:
    balance = current_user.wallet.balance if current_user.wallet else 0.0
    return BalanceResponse(
        user_id=current_user.user_id,
        balance=balance,
    )


@router.post(
    "/deposit",
    response_model=BalanceResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Некорректная сумма"},
        401: {"model": ErrorResponse},
    },
    summary="Пополнить баланс",
)
def deposit(
    body: DepositRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> BalanceResponse:
    wallet = current_user.wallet
    if wallet is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Кошелёк пользователя не найден",
        )

    # Пополняем баланс
    wallet.balance = round(wallet.balance + body.amount, 2)

    # Записываем транзакцию
    tx = TransactionORM(
        wallet_id=wallet.wallet_id,
        amount=body.amount,
        transaction_type="DEPOSIT",
        ml_task_id=None,
    )
    db.add(tx)
    db.commit()
    db.refresh(wallet)

    return BalanceResponse(
        user_id=current_user.user_id,
        balance=wallet.balance,
        message=f"Баланс пополнен на {body.amount} кредитов",
    )
