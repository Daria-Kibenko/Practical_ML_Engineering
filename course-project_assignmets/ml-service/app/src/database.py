"""
Подключение к базе данных через SQLAlchemy.
Конфигурация берётся из переменных окружения.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from .config import settings


engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,       # проверять соединение перед использованием
    pool_size=10,
    max_overflow=20,
    echo=settings.debug,      # SQL-логи в режиме отладки
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency — предоставляет сессию БД на время запроса."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
