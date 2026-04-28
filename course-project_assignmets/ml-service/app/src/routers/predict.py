"""
Эндпоинты для выполнения ML-предсказаний.

  POST /predict/        — синхронное предсказание
  POST /predict/async   — асинхронное (задача → RabbitMQ → воркер)
  GET  /predict/{id}    — статус / результат задачи
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.domain import TaskStatus
from ..models.orm import MLModelORM, MLTaskORM, PredictionResultORM, UserORM
from ..schemas.schemas import MLModelResponse, PredictRequest, PredictResponse, ValidationError
from ..services.auth_service import get_current_user
from ..services.balance_service import BalanceService, InsufficientFundsError
from ..services.ml_engine import run_prediction
from ..services.rabbitmq_publisher import publish_ml_task

router = APIRouter(prefix="/predict", tags=["ML-предсказания"])


class AsyncPredictResponse(BaseModel):
    task_id: int
    status: str
    message: str


class TaskStatusResponse(BaseModel):
    task_id: int
    status: TaskStatus
    model_name: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    credits_charged: Optional[float] = None


def _validate_input(input_data: Dict[str, Any]) -> List[ValidationError]:
    return [
        ValidationError(field=k, error=f"Ожидается число, получено: {type(v).__name__}")
        for k, v in input_data.items()
        if not isinstance(v, (int, float))
    ]


@router.get("/models", response_model=List[MLModelResponse], summary="Список доступных ML-моделей")
def list_models(db: Session = Depends(get_db)) -> List[MLModelORM]:
    return db.query(MLModelORM).filter(MLModelORM.is_active == True).all()  # noqa: E712


@router.post("/", response_model=PredictResponse, summary="Синхронное предсказание")
def predict(
    body: PredictRequest,
    db: Session = Depends(get_db),
    current_user: UserORM = Depends(get_current_user),
) -> PredictResponse:
    model_orm = db.get(MLModelORM, body.model_id)
    if not model_orm or not model_orm.is_active:
        raise HTTPException(status_code=404, detail="ML-модель не найдена или недоступна")

    validation_errors = _validate_input(body.input_data)
    valid_data = {k: v for k, v in body.input_data.items() if not any(e.field == k for e in validation_errors)}

    # Создаём задачу
    task = MLTaskORM(
        user_id=current_user.id,
        model_id=model_orm.id,
        input_data=body.input_data,
        status=TaskStatus.PROCESSING,
    )
    db.add(task)
    db.flush()  # получаем task.id до commit

    # Выполняем предсказание
    output = run_prediction(model_orm.name, valid_data)
    if validation_errors:
        output["validation_errors"] = [e.model_dump() for e in validation_errors]

    # Списываем кредиты через BalanceService
    try:
        BalanceService(db).debit(
            user_id=current_user.id,
            amount=model_orm.cost_per_prediction,
            task_id=task.id,
        )
    except InsufficientFundsError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=str(exc))

    db.add(PredictionResultORM(
        task_id=task.id,
        output_data=output,
        credits_charged=model_orm.cost_per_prediction,
    ))
    task.status = TaskStatus.COMPLETED
    db.commit()

    return PredictResponse(
        task_id=task.id, status=TaskStatus.COMPLETED,
        result=output, credits_charged=model_orm.cost_per_prediction,
        validation_errors=validation_errors if validation_errors else None,
    )


@router.post("/async", response_model=AsyncPredictResponse, status_code=202, summary="Асинхронное предсказание через RabbitMQ")
def predict_async(
    body: PredictRequest,
    db: Session = Depends(get_db),
    current_user: UserORM = Depends(get_current_user),
) -> AsyncPredictResponse:
    model_orm = db.get(MLModelORM, body.model_id)
    if not model_orm or not model_orm.is_active:
        raise HTTPException(status_code=404, detail="ML-модель не найдена или недоступна")

    # Проверяем баланс (без списания — воркер спишет после обработки)
    amount = BalanceService(db).get_amount(current_user.id)
    if amount < model_orm.cost_per_prediction:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Недостаточно кредитов. Требуется: {model_orm.cost_per_prediction}, доступно: {amount}",
        )

    task = MLTaskORM(
        user_id=current_user.id, model_id=model_orm.id,
        input_data=body.input_data, status=TaskStatus.PENDING,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    try:
        publish_ml_task(task_id=task.id, model_name=model_orm.name, features=body.input_data)
    except RuntimeError as exc:
        task.status = TaskStatus.FAILED
        db.commit()
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return AsyncPredictResponse(
        task_id=task.id, status=TaskStatus.PENDING,
        message="Задача поставлена в очередь. Используйте GET /predict/{task_id} для проверки статуса.",
    )


@router.get("/{task_id}", response_model=TaskStatusResponse, summary="Статус и результат задачи")
def get_task_status(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: UserORM = Depends(get_current_user),
) -> TaskStatusResponse:
    from sqlalchemy.orm import joinedload
    task = (
        db.query(MLTaskORM)
        .options(joinedload(MLTaskORM.model), joinedload(MLTaskORM.result))
        .filter(MLTaskORM.id == task_id, MLTaskORM.user_id == current_user.id)
        .first()
    )
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    return TaskStatusResponse(
        task_id=task.id, status=task.status,
        model_name=task.model.name if task.model else None,
        result=task.result.output_data if task.result else None,
        credits_charged=task.result.credits_charged if task.result else None,
    )


@router.get(
    "/models/info",
    summary="Метрики и датасеты реальных ML-моделей",
    tags=["ML-предсказания"],
)
def models_info() -> dict:
    """
    Возвращает информацию об обученных моделях:
    датасет, количество образцов, признаки, метрики качества.
    """
    from ..services.ml_engine import get_model_metadata
    return get_model_metadata()
