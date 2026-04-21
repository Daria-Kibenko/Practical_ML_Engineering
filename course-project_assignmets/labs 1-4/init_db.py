"""
Идемпотентная инициализация БД (объединенная версия).
Создает таблицы, добавляет demo-пользователя, admin и базовые ML-модели.
"""
from __future__ import annotations

import hashlib

from database import SessionLocal, engine
from orm_models import Base, MLModelORM, UserORM, WalletORM


def _hash(password: str) -> str:
    """Хэширование пароля SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()


def init_db() -> None:
    """Инициализация базы данных: создание таблиц и заполнение начальными данными."""
    # Создаем все таблицы
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # Базовые ML-модели
        if db.query(MLModelORM).count() == 0:
            db.add_all([
                MLModelORM(
                    name="ClassificationModel v1",
                    description="Классификация по числовым признакам",
                    cost_per_prediction=1.5,
                    model_type="classification",
                ),
                MLModelORM(
                    name="RegressionModel v1",
                    description="Регрессия для предсказания числового значения",
                    cost_per_prediction=2.0,
                    model_type="regression",
                ),
                MLModelORM(
                    name="Классификация текста",
                    description="Определяет тональность текста",
                    cost_per_prediction=5.0,
                    model_type="classification",
                ),
                MLModelORM(
                    name="Генерация изображения",
                    description="Текст → картинка",
                    cost_per_prediction=20.0,
                    model_type="generation",
                ),
                MLModelORM(
                    name="Предсказание временных рядов",
                    description="Forecast временных рядов",
                    cost_per_prediction=10.0,
                    model_type="regression",
                ),
            ])
            db.flush()

        # Demo-пользователь
        if not db.query(UserORM).filter(UserORM.email == "demo@example.com").first():
            wallet = WalletORM(balance=100.0)
            db.add(wallet)
            db.flush()
            db.add(UserORM(
                username="demo",
                email="demo@example.com",
                password_hash=_hash("demo1234"),
                role="USER",
                wallet_id=wallet.wallet_id,
            ))

        # Администратор
        if not db.query(UserORM).filter(UserORM.email == "admin@example.com").first():
            wallet = WalletORM(balance=9999.0)
            db.add(wallet)
            db.flush()
            db.add(UserORM(
                username="admin",
                email="admin@example.com",
                password_hash=_hash("admin1234"),
                role="ADMIN",
                wallet_id=wallet.wallet_id,
            ))

        if not db.query(UserORM).filter(UserORM.username == "demo_user").first():
            wallet = WalletORM(balance=50.0)
            db.add(wallet)
            db.flush()
            db.add(UserORM(
                username="demo_user",
                email="demo_user@example.com",
                password_hash=_hash("demo123"),
                role="USER",
                wallet_id=wallet.wallet_id,
            ))

        db.commit()
        print("База данных инициализирована (таблицы + демо-данные).")
        print("Доступные учётные записи:")
        print("demo@example.com / demo1234")
        print("admin@example.com / admin1234")
        print("demo_user@example.com / demo123")

    finally:
        db.close()


if __name__ == "__main__":
    init_db()
