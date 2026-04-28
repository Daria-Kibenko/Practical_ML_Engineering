"""
Запуск: uvicorn src.main:app --reload
Web UI:   http://localhost/
Swagger:  http://localhost/docs
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .database import engine
from .init_data import init_db
from .routers import auth, balance, history, predict

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

_STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Запуск приложения...")
    init_db(engine)
    logger.info("Приложение готово к работе")
    yield
    logger.info("Остановка приложения")
    engine.dispose()


app = FastAPI(
    title=settings.app_title,
    description="ML Service — личный кабинет пользователя.",
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

# API-роутеры (подключаются первыми, чтобы /docs не перехватывал /)
app.include_router(auth.router)
app.include_router(balance.router)
app.include_router(predict.router)
app.include_router(history.router)


@app.get("/health", tags=["Служебные"], summary="Healthcheck")
def health() -> dict:
    return {"status": "ok", "service": settings.app_title}


# Раздача Web-интерфейса
# Все неизвестные маршруты отдают index.html (SPA-режим)
if _STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

    @app.get("/", include_in_schema=False)
    def frontend_root() -> FileResponse:
        return FileResponse(str(_STATIC_DIR / "index.html"))
