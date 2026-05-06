"""
Создаёт (если не существуют):
  - демо-пользователя  (user@example.com  / password123) + начальный баланс 100
  - демо-администратора (admin@example.com / admin123)   + начальный баланс 1000
  - 3 базовые ML-модели

Идемпотентна: повторный запуск не ломает данные.
"""

import logging
import time

from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from .models.domain import UserRole
from .models.orm import BalanceORM, Base, MLModelORM, UserORM
from .services.auth_service import hash_password

logger = logging.getLogger(__name__)


DEMO_USERS = [
    {"email": "user@example.com",  "password": "password123", "role": UserRole.USER,  "balance": 100.0},
    {"email": "admin@example.com", "password": "admin123",    "role": UserRole.ADMIN, "balance": 1000.0},
]

DEMO_MODELS = [
    {"name": "Classifier v1",   "description": "Базовая классификационная модель. Принимает числовые признаки, возвращает бинарный класс.", "cost_per_prediction": 1.0},
    {"name": "Regressor v1",    "description": "Модель регрессии для предсказания числовых значений.", "cost_per_prediction": 2.0},
    {"name": "Anomaly Detector","description": "Детектор аномалий в числовых данных.", "cost_per_prediction": 3.0},
]


def _wait_for_db(engine, retries: int = 10, delay: int = 3) -> None:
    """Ждём, пока БД станет доступной (актуально при старте через docker compose)."""
    for attempt in range(1, retries + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("БД доступна (попытка %d)", attempt)
            return
        except OperationalError:
            logger.warning("БД недоступна, жду %ds (попытка %d/%d)...", delay, attempt, retries)
            time.sleep(delay)
    raise RuntimeError(f"БД не стала доступной после {retries} попыток")


def init_db(engine) -> None:
    """Создать таблицы (если не существуют) и заполнить демо-данными."""
    _wait_for_db(engine)

    # Создаём все таблицы описанные в Base.metadata (идемпотентно: CREATE IF NOT EXISTS)
    Base.metadata.create_all(bind=engine)
    logger.info("Таблицы созданы / проверены")

    with Session(engine) as db:
        _seed_users(db)
        _seed_models(db)
        db.commit()

    from .ml_models.train_and_save import train_all
    train_all()  # обучить реальные ML-модели если ещё нет
    logger.info("Инициализация БД завершена")


def _seed_users(db: Session) -> None:
    for data in DEMO_USERS:
        user = db.query(UserORM).filter(UserORM.email == data["email"]).first()
        if not user:
            user = UserORM(
                email=data["email"],
                password_hash=hash_password(data["password"]),
                role=data["role"],
            )
            db.add(user)
            db.flush()  # нужен user.id для BalanceORM

            # Создаём запись баланса отдельно
            db.add(BalanceORM(user_id=user.id, amount=data["balance"]))
            logger.info("Создан пользователь: %s (баланс: %s)", data["email"], data["balance"])
        else:
            # Убеждаемся, что запись баланса существует
            if not db.query(BalanceORM).filter(BalanceORM.user_id == user.id).first():
                db.add(BalanceORM(user_id=user.id, amount=data["balance"]))
                logger.info("Создан баланс для существующего пользователя: %s", data["email"])


def _seed_models(db: Session) -> None:
    for data in DEMO_MODELS:
        if not db.query(MLModelORM).filter(MLModelORM.name == data["name"]).first():
            db.add(MLModelORM(**data))
            logger.info("Создана ML-модель: %s", data["name"])

