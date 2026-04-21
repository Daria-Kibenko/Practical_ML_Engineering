"""
Роутер /predict - отправка данных на ML-предсказание.

GET  /predict/models - список доступных ML-моделей
POST /predict/{model_id} - запустить предсказание
GET  /predict/tasks/{task_id} - статус конкретной задачи
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status

from dependencies import CurrentUser, DBSession
from orm_models import MLModelORM, MLTaskORM, PredictionResultORM, TransactionORM
from schemas import (
    ErrorResponse,
    MLModelInfo,
    PredictRequest,
    PredictionResponse,
)

router = APIRouter(prefix="/predict", tags=["Predict"])


# Helpers
def _run_mock_prediction(model: MLModelORM, input_data: object) -> dict:
    """
    Имитация предсказания.
    """
    if model.name.lower().startswith("classif"):
        return {
            "predicted_label": "class_A",
            "confidence": 0.87,
            "raw_output": {"class_A": 0.87, "class_B": 0.13},
        }
    # RegressionModel
    return {
        "predicted_label": None,
        "confidence": None,
        "raw_output": {"value": 42.0},
    }


# Endpoints
@router.get(
    "/models",
    response_model=list[MLModelInfo],
    summary="Список доступных ML-моделей",
)
def list_models(db: DBSession) -> list[MLModelInfo]:
    models = db.query(MLModelORM).all()
    return [
        MLModelInfo(
            model_id=m.model_id,
            name=m.name,
            description=m.description,
            cost_per_prediction=m.cost_per_prediction,
        )
        for m in models
    ]


@router.post(
    "/{model_id}",
    response_model=PredictionResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "Ошибка валидации входных данных"},
        402: {"model": ErrorResponse, "description": "Недостаточно кредитов"},
        404: {"model": ErrorResponse, "description": "Модель не найдена"},
        401: {"model": ErrorResponse},
    },
    summary="Запустить ML-предсказание",
)
def make_prediction(
    model_id: int,
    body: PredictRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> PredictionResponse:
    # 1. Найти модель
    model = db.get(MLModelORM, model_id)
    if model is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ML-модель с id={model_id} не найдена",
        )

    # 2. Проверить баланс
    wallet = current_user.wallet
    if wallet is None or wallet.balance < model.cost_per_prediction:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=(
                f"Недостаточно кредитов. "
                f"Требуется: {model.cost_per_prediction}, "
                f"доступно: {wallet.balance if wallet else 0}"
            ),
        )

    # 3. Базовая валидация входных данных (расширяется под конкретную модель)
    if body.input_data is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Поле input_data не может быть пустым",
        )

    now = datetime.now(timezone.utc)

    # 4. Создать задачу со статусом RUNNING
    task = MLTaskORM(
        user_id=current_user.user_id,
        model_id=model_id,
        input_data=str(body.input_data),
        status="RUNNING",
        created_at=now,
    )
    db.add(task)
    db.flush()

    try:
        # 5. Выполнить предсказание
        pred_data = _run_mock_prediction(model, body.input_data)

        # 6. Сохранить результат
        result = PredictionResultORM(
            task_id=task.task_id,
            predicted_label=pred_data.get("predicted_label"),
            confidence=pred_data.get("confidence"),
            raw_output=str(pred_data["raw_output"]),
            created_at=now,
        )
        db.add(result)

        # 7. Списать кредиты
        wallet.balance = round(wallet.balance - model.cost_per_prediction, 2)
        tx = TransactionORM(
            wallet_id=wallet.wallet_id,
            amount=model.cost_per_prediction,
            transaction_type="DEBIT",
            ml_task_id=task.task_id,
        )
        db.add(tx)

        # 8. Обновить статус задачи
        task.status = "COMPLETED"
        task.completed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(task)

        return PredictionResponse(
            task_id=task.task_id,
            status=task.status,
            predicted_label=pred_data.get("predicted_label"),
            confidence=pred_data.get("confidence"),
            raw_output=pred_data["raw_output"],
            credits_charged=model.cost_per_prediction,
            created_at=task.created_at,
        )

    except Exception as exc:
        task.status = "FAILED"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка выполнения предсказания: {exc}",
        ) from exc


@router.get(
    "/tasks/{task_id}",
    response_model=PredictionResponse,
    responses={
        404: {"model": ErrorResponse},
        403: {"model": ErrorResponse, "description": "Задача принадлежит другому пользователю"},
        401: {"model": ErrorResponse},
    },
    summary="Статус конкретной задачи",
)
def get_task(
    task_id: int,
    current_user: CurrentUser,
    db: DBSession,
) -> PredictionResponse:
    task = db.get(MLTaskORM, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Задача не найдена")
    if task.user_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет доступа к задаче")

    result = task.result  # relationship
    cost = task.model.cost_per_prediction if task.model else 0.0

    return PredictionResponse(
        task_id=task.task_id,
        status=task.status,
        predicted_label=result.predicted_label if result else None,
        confidence=result.confidence if result else None,
        raw_output={"value": result.raw_output} if result else None,
        credits_charged=cost,
        created_at=task.created_at,
    )
