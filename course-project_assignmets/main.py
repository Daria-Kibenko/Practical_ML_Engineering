import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from models import (
    User, AdminUser,
    ClassificationModel,
    MLTask,
    DebitTransaction,
)
from enums import TaskStatus
from services import MLRequestHistory


def main() -> None:
    # Создание пользователей
    user = User(
        user_id=1,
        username="alice",
        email="alice@example.com",
        password_hash="hashed_password",
    )
    admin = AdminUser(
        user_id=2,
        username="admin",
        email="admin@example.com",
        password_hash="hashed_admin_password",
    )

    print("=== Начальное состояние ===")
    print(user)

    # Администратор пополняет баланс
    admin.top_up_user(user, 100.0)
    print(f"\n=== После пополнения администратором (+100) ===")
    print(user)

    # Создание ML-модель
    model = ClassificationModel(
        model_id=1,
        name="SentimentClassifier",
        description="Классификация тональности текста",
        cost_per_prediction=10.0,
    )
    print(f"\n===ML-модель ===")
    print(model)

    # История запросов пользователя
    history = MLRequestHistory(user)

    # Создание и запуск задачи
    task = MLTask(
        task_id=101,
        input_data={"text": "Отличный сервис!"},
        user=user,
        model=model,
    )
    result = task.run()
    history.add_task(task)

    debit_tx = DebitTransaction(
        transaction_id=1,
        amount=model.cost_per_prediction,
        user=user,
        ml_task=task,
    )
    history.add_transaction(debit_tx)

    print(f"\n=== Выполнение задачи ===")
    print(task)
    print(f"Результат: {result}")
    print(f"Баланс после запроса: {user.balance}")

    # Нулевой баланс
    user2 = User(
        user_id=3, username="bob",
        email="bob@example.com",
        password_hash="hashed_bob",
        balance=0.0,
    )
    task2 = MLTask(task_id=102, input_data={"text": "test"}, user=user2, model=model)
    try:
        task2.run()
    except ValueError as e:
        print(f"\n=== Проверка баланса ===")
        print(f"Ожидаемая ошибка: {e}")

    # Невалидные данные
    bad_task = MLTask(task_id=103, input_data=None, user=user, model=model)
    bad_task.run()
    print(f"\n=== Валидация входных данных ===")
    print(f"Статус: {bad_task.status}")
    print(f"Ошибки: {bad_task.validation_errors}")

    # История
    print(f"\n=== История пользователя ===")
    print(history)
    print(f"Завершённых задач: {len(history.get_tasks(TaskStatus.COMPLETED))}")
    print(f"Потрачено кредитов: {history.total_spent()}")


if __name__ == "__main__":
    main()
