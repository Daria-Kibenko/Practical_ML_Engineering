"""
Настройка подключения к БД через SQLAlchemy.
DATABASE_URL берётся из переменной окружения DATABASE_URL (файл .env).
Если переменная не задана, используется SQLite база данных по умолчанию.
"""
from __future__ import annotations

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

load_dotenv()

DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./ml_service.db")

# Дополнительные параметры для SQLite (поддержка многопоточности)
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """Генератор сессий для использования в зависимостях FastAPI."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
