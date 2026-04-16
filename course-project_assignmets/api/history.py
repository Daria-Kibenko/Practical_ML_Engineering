"""
Роутер /history - история ML-запросов и транзакций.

GET /history/tasks - список ML-задач пользователя
GET /history/transactions - история транзакций пользователя
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query

from dependencies import CurrentUser, DBSession
from orm_models import MLTaskORM, TransactionORM
from schemas import (
    ErrorResponse,
    TaskHistoryItem,
    TasksHistoryResponse,
    TransactionHistoryItem,
    TransactionsHistoryResponse,
)

router = APIRouter(prefix="/history", tags=["History"])


@router.get(
    "/tasks",
    response_model=TasksHistoryResponse,
    responses={401: {"model": ErrorResponse}},
    summary="История ML-запросов",
)
def get_tasks_history(
    current_user: CurrentUser,
    db: DBSession,
    status: Optional[str] = Query(default=None, description="Фильтр по статусу задачи"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> TasksHistoryResponse:
    query = (
        db.query(MLTaskORM)
        .filter(MLTaskORM.user_id == current_user.user_id)
    )
    if status:
        query = query.filter(MLTaskORM.status == status.upper())

    total = query.count()
    tasks = query.order_by(MLTaskORM.created_at.desc()).offset(offset).limit(limit).all()

    items = [
        TaskHistoryItem(
            task_id=t.task_id,
            model_name=t.model.name if t.model else "unknown",
            status=t.status,
            credits_charged=t.model.cost_per_prediction if t.model else 0.0,
            created_at=t.created_at,
            completed_at=t.completed_at,
        )
        for t in tasks
    ]

    return TasksHistoryResponse(
        user_id=current_user.user_id,
        total=total,
        tasks=items,
    )


@router.get(
    "/transactions",
    response_model=TransactionsHistoryResponse,
    responses={401: {"model": ErrorResponse}},
    summary="История транзакций",
)
def get_transactions_history(
    current_user: CurrentUser,
    db: DBSession,
    tx_type: Optional[str] = Query(default=None, alias="type", description="Фильтр по типу"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> TransactionsHistoryResponse:
    wallet = current_user.wallet
    if wallet is None:
        return TransactionsHistoryResponse(
            user_id=current_user.user_id,
            total=0,
            total_spent=0.0,
            transactions=[],
        )

    query = db.query(TransactionORM).filter(
        TransactionORM.wallet_id == wallet.wallet_id
    )
    if tx_type:
        query = query.filter(TransactionORM.transaction_type == tx_type.upper())

    total = query.count()
    txs = query.order_by(TransactionORM.created_at.desc()).offset(offset).limit(limit).all()

    # Суммарно потрачено - только DEBIT-транзакции
    all_debit = (
        db.query(TransactionORM)
        .filter(
            TransactionORM.wallet_id == wallet.wallet_id,
            TransactionORM.transaction_type == "DEBIT",
        )
        .all()
    )
    total_spent = round(sum(t.amount for t in all_debit), 2)

    items = [
        TransactionHistoryItem(
            transaction_id=t.transaction_id,
            transaction_type=t.transaction_type,
            amount=t.amount,
            created_at=t.created_at,
        )
        for t in txs
    ]

    return TransactionsHistoryResponse(
        user_id=current_user.user_id,
        total=total,
        total_spent=total_spent,
        transactions=items,
    )
