import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from database import SessionLocal
from services.balance_service import (
    create_user, deposit, deduct, make_prediction,
    get_transaction_history, get_prediction_history, InsufficientBalanceError
)
from init_db import init_database
from orm_models import MLModelORM
from enums.roles import UserRole


def main():
    init_database()

    db = SessionLocal()
    try:
        # 1. Создание пользователя
        user = create_user(db, "alice", "alice@example.com", initial_balance=0)
        admin = create_user(db, "admin", "admin@example.com", initial_balance=1000, role=UserRole.ADMIN)
        print(f"Создан {user.username}, баланс: {user.balance}")

        # 2. Администратор пополняет баланс пользователя
        deposit(db, user.id, 100.0, description="Пополнение от администратора")
        db.refresh(user)
        print(f"После пополнения: баланс = {user.balance}")

        # 3. Загрузка ML-модели (демо-данные уже есть)
        model = db.query(MLModelORM).filter(MLModelORM.name == "Классификация текста").first()
        if not model:
            print("Модель не найдена, запустите init_db.py")
            return

        # 4. Выполнение предсказания
        task = make_prediction(db, user.id, model.id, '{"text": "Отличный сервис!"}')
        db.refresh(user)
        print(f"Задача выполнена, списано {task.credits_used} кредитов. Баланс: {user.balance}")

        # 5. Проверка недостатка средств
        try:
            deduct(db, user.id, 1000, "Попытка списать много")
        except InsufficientBalanceError as e:
            print(f"Ожидаемая ошибка: {e}")

        # 6. История транзакций
        print("\n=== История транзакций ===")
        for tx in get_transaction_history(db, user.id):
            print(f"{tx.timestamp} | {tx.type.value} | {tx.amount} | {tx.description}")

        # 7. История предсказаний
        print("\n=== История предсказаний ===")
        for t in get_prediction_history(db, user.id):
            print(f"{t.created_at} | модель {t.model_id} | кредитов: {t.credits_used} | статус: {t.status.value}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
