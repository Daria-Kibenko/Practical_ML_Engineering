"""
Эндпоинты для работы с балансом пользователя.
Бизнес-логика делегируется в BalanceService.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.orm import UserORM
from ..schemas.schemas import AdminDepositRequest, BalanceResponse, DepositRequest, DepositResponse
from ..services.auth_service import get_current_admin, get_current_user
from ..services.balance_service import BalanceService

router = APIRouter(prefix="/balance", tags=["Баланс"])


@router.get("/", response_model=BalanceResponse, summary="Получить текущий баланс")
def get_balance(
    db: Session = Depends(get_db),
    current_user: UserORM = Depends(get_current_user),
) -> BalanceResponse:
    svc = BalanceService(db)
    bal = svc.get_balance(current_user.id)
    return BalanceResponse(user_id=current_user.id, amount=bal.amount)


@router.post("/deposit", response_model=DepositResponse, summary="Пополнить баланс")
def deposit(
    body: DepositRequest,
    db: Session = Depends(get_db),
    current_user: UserORM = Depends(get_current_user),
) -> DepositResponse:
    svc = BalanceService(db)
    bal = svc.deposit(user_id=current_user.id, amount=body.amount)
    db.commit()
    return DepositResponse(user_id=current_user.id, amount=bal.amount, deposited=body.amount)


@router.post(
    "/admin/deposit",
    response_model=DepositResponse,
    summary="[Админ] Пополнить баланс пользователя",
)
def admin_deposit(
    body: AdminDepositRequest,
    db: Session = Depends(get_db),
    _admin: UserORM = Depends(get_current_admin),
) -> DepositResponse:
    user = db.get(UserORM, body.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")

    svc = BalanceService(db)
    bal = svc.deposit(user_id=body.user_id, amount=body.amount)
    db.commit()
    return DepositResponse(user_id=body.user_id, amount=bal.amount, deposited=body.amount)
