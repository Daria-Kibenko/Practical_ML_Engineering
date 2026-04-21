"""
Эндпоинты для просмотра истории ML-запросов и транзакций.
"""

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..models.orm import MLTaskORM, TransactionORM, UserORM
from ..schemas.schemas import MLTaskHistoryItem, TransactionHistoryItem
from ..services.auth_service import get_current_admin, get_current_user

router = APIRouter(prefix="/history", tags=["История"])


@router.get(
    "/ml-requests",
    response_model=List[MLTaskHistoryItem],
    summary="История ML-запросов текущего пользователя",
)
def ml_requests_history(
    db: Session = Depends(get_db),
    current_user: UserORM = Depends(get_current_user),
    limit: int = 50,
    offset: int = 0,
) -> List[MLTaskHistoryItem]:
    tasks = (
        db.query(MLTaskORM)
        .options(joinedload(MLTaskORM.model), joinedload(MLTaskORM.result))
        .filter(MLTaskORM.user_id == current_user.id)
        .order_by(MLTaskORM.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return [
        MLTaskHistoryItem(
            id=t.id,
            model_name=t.model.name if t.model else "unknown",
            status=t.status,
            credits_charged=t.result.credits_charged if t.result else None,
            result=t.result.output_data if t.result else None,
            created_at=t.created_at,
        )
        for t in tasks
    ]


@router.get(
    "/transactions",
    response_model=List[TransactionHistoryItem],
    summary="История транзакций текущего пользователя",
)
def transactions_history(
    db: Session = Depends(get_db),
    current_user: UserORM = Depends(get_current_user),
    limit: int = 50,
    offset: int = 0,
) -> List[TransactionHistoryItem]:
    txs = (
        db.query(TransactionORM)
        .filter(TransactionORM.user_id == current_user.id)
        .order_by(TransactionORM.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [
        TransactionHistoryItem(
            id=tx.id,
            type=tx.type,
            amount=tx.amount,
            task_id=tx.task_id,
            created_at=tx.created_at,
        )
        for tx in txs
    ]


# Администраторские эндпоинты
@router.get(
    "/admin/transactions",
    response_model=List[TransactionHistoryItem],
    summary="[Админ] Все транзакции системы",
)
def all_transactions(
    db: Session = Depends(get_db),
    _admin: UserORM = Depends(get_current_admin),
    limit: int = 100,
    offset: int = 0,
) -> List[TransactionHistoryItem]:
    txs = (
        db.query(TransactionORM)
        .order_by(TransactionORM.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [
        TransactionHistoryItem(
            id=tx.id,
            type=tx.type,
            amount=tx.amount,
            task_id=tx.task_id,
            created_at=tx.created_at,
        )
        for tx in txs
    ]
