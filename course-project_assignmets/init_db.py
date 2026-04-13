from database import engine, SessionLocal
from orm_models import Base, UserORM, MLModelORM
from enums.roles import UserRole


def init_database():
    # создаем таблицы (если не существуют)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Демо-пользователь
        if not db.query(UserORM).filter(UserORM.username == "demo_user").first():
            demo = UserORM(username="demo_user", email="demo@example.com", balance=100, role=UserRole.USER)
            db.add(demo)
        # Демо-администратор
        if not db.query(UserORM).filter(UserORM.username == "admin").first():
            admin = UserORM(username="admin", email="admin@example.com", balance=1000, role=UserRole.ADMIN)
            db.add(admin)

        # Базовые ML-модели
        models = [
            {"name": "Классификация текста", "description": "Определяет тональность", "cost": 5, "type": "classification"},
            {"name": "Генерация изображения", "description": "Текст → картинка", "cost": 20, "type": "generation"},
            {"name": "Предсказание временных рядов", "description": "Forecast", "cost": 10, "type": "regression"},
        ]
        for m in models:
            exists = db.query(MLModelORM).filter(MLModelORM.name == m["name"]).first()
            if not exists:
                db.add(MLModelORM(name=m["name"], description=m["description"], cost_per_request=m["cost"], model_type=m["type"]))
        db.commit()
        print("База данных инициализирована (таблицы + демо-данные)")
    finally:
        db.close()

if __name__ == "__main__":
    init_database()
