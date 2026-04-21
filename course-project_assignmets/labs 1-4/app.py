"""
Точка входа FastAPI-приложения для ML-сервиса.

Запуск:
    uvicorn app:app --reload

Swagger UI: http://127.0.0.1:8000/docs
ReDoc:       http://127.0.0.1:8000/redoc
"""
from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from api.auth import router as auth_router
from api.balance import router as balance_router
from api.history import router as history_router
from api.predict import router as predict_router
from api.users import router as users_router

# Приложение
app = FastAPI(
    title="ML Service API",
    description=(
        "REST API для ML-сервиса. "
        "Позволяет регистрировать пользователей, управлять балансом, "
        "запускать ML-предсказания и просматривать историю операций."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS (для будущего Web-фронтенда и Telegram-бота)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Глобальный обработчик ошибок - единый формат {"error": ..., "detail": ...}
@app.exception_handler(ValidationError)
async def validation_exception_handler(_request: Request, exc: ValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"error": "Ошибка валидации", "detail": exc.errors(), "code": 422},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "Внутренняя ошибка сервера", "detail": str(exc), "code": 500},
    )


# Роутеры
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(balance_router)
app.include_router(predict_router)
app.include_router(history_router)


# Health-check
@app.get("/health", tags=["System"], summary="Проверка работоспособности")
def health_check() -> dict:
    return {"status": "ok", "service": "ML Service API"}
