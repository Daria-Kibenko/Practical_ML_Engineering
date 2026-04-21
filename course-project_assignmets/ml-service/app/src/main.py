"""
Задание №4 — REST API на FastAPI.

Запуск: uvicorn src.main:app --reload
Swagger UI: http://localhost/docs
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import engine
from .init_data import init_db
from .routers import auth, balance, history, predict

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


# Lifespan (заменяет устаревший @app.on_event)
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Код до yield выполняется при старте приложения.
    Код после yield — при остановке (graceful shutdown).
    """
    logger.info("Запуск приложения...")
    # Создаём таблицы (если не существуют) и заполняем демо-данными.
    # init_db внутри ждёт доступности БД перед созданием таблиц.
    init_db(engine)
    logger.info("Приложение готово к работе")

    yield  # ← приложение работает

    logger.info("Остановка приложения")
    engine.dispose()


# Создание приложения
app = FastAPI(
    title=settings.app_title,
    description=(
        "Личный кабинет пользователя ML-сервиса. "
        "Регистрация, управление балансом, выполнение предсказаний, история запросов."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Роутеры
app.include_router(auth.router)
app.include_router(balance.router)
app.include_router(predict.router)
app.include_router(history.router)


@app.get("/health", tags=["Служебные"], summary="Проверка работоспособности")
def health() -> dict:
    return {"status": "ok", "service": settings.app_title}
