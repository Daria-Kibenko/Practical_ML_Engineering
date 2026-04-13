from sqlalchemy.orm import Session

from enums import UserRole
from orm_models import UserORM, TransactionORM, MLModelORM, MLTaskORM, PredictionResultORM
from enums.transaction_type import TransactionType
from enums.task_status import TaskStatus


class InsufficientBalanceError(Exception):
    pass


def create_user(db: Session, username: str, email: str, initial_balance: int = 0, role=UserRole.USER) -> UserORM:
    user = UserORM(username=username, email=email, balance=initial_balance, role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user(db: Session, user_id: int) -> UserORM | None:
    return db.query(UserORM).filter(UserORM.id == user_id).first()


def deposit(db: Session, user_id: int, amount: int, description: str = "Пополнение") -> TransactionORM:
    if amount <= 0:
        raise ValueError("Сумма должна быть положительной")
    user = get_user(db, user_id)
    if not user:
        raise ValueError("Пользователь не найден")
    user.balance += amount
    tx = TransactionORM(user_id=user_id, amount=amount, type=TransactionType.DEPOSIT, description=description)
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


def deduct(db: Session, user_id: int, amount: int, description: str = "Списание") -> TransactionORM:
    if amount <= 0:
        raise ValueError("Сумма должна быть положительной")
    user = get_user(db, user_id)
    if not user:
        raise ValueError("Пользователь не найден")
    if user.balance < amount:
        raise InsufficientBalanceError(f"Недостаточно кредитов. Нужно {amount}, доступно {user.balance}")
    user.balance -= amount
    tx = TransactionORM(user_id=user_id, amount=-amount, type=TransactionType.DEBIT, description=description)
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


def make_prediction(db: Session, user_id: int, model_id: int, input_data: str) -> MLTaskORM:
    model = db.query(MLModelORM).filter(MLModelORM.id == model_id).first()
    if not model:
        raise ValueError("Модель не найдена")
    # списание кредитов
    deduct(db, user_id, model.cost_per_request, description=f"Предсказание через {model.name}")
    # создание задачи
    task = MLTaskORM(
        user_id=user_id,
        model_id=model_id,
        input_data=input_data,
        credits_used=model.cost_per_request,
        status=TaskStatus.COMPLETED
    )
    db.add(task)
    db.flush()
    result = PredictionResultORM(task_id=task.id, output_data=f"Результат для '{input_data[:50]}...'")
    db.add(result)
    db.commit()
    db.refresh(task)
    return task


def get_transaction_history(db: Session, user_id: int, limit: int = 50):
    return db.query(TransactionORM).filter(TransactionORM.user_id == user_id)\
             .order_by(TransactionORM.timestamp.desc()).limit(limit).all()


def get_prediction_history(db: Session, user_id: int, limit: int = 50):
    # возвращаем задачи с результатами, отсортированные по дате создания
    return db.query(MLTaskORM).filter(MLTaskORM.user_id == user_id)\
             .order_by(MLTaskORM.created_at.desc()).limit(limit).all()
