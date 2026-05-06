"""
Общие фикстуры для всех тестов.

Ключевые решения:
  - SQLite in-memory вместо PostgreSQL (тесты не требуют Docker)
  - Подменяем src.database.engine и SessionLocal до создания TestClient
  - Патчим init_db чтобы создавал таблицы в тестовой БД, а не ждал PostgreSQL
  - RabbitMQ-паблишер заменяется stub-функцией
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from unittest.mock import patch

# Тестовый движок БД (SQLite in-memory, отдельный файл на каждый тест)
TEST_DB_URL = "sqlite:///./test_tmp.db"

test_engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_init_db(_engine):
    """
    Упрощённая init_db для тестов:
    создаёт таблицы в SQLite без ожидания PostgreSQL и без ML-обучения.
    """
    from app.src.models.orm import Base
    Base.metadata.create_all(bind=test_engine)


# Фикстуры
@pytest.fixture(autouse=True)
def clean_db():
    """Пересоздаёт схему БД перед каждым тестом."""
    from app.src.models.orm import Base
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client():
    """
    TestClient с:
      - SQLite вместо PostgreSQL
      - заглушкой init_db (без ожидания PostgreSQL)
      - заглушкой RabbitMQ-паблишера
    """
    import app.src.database as db_module
    from app.src.main import app
    from app.src.database import get_db
    import app.src.services.rabbitmq_publisher as rmq

    # Подменяем движок и сессию в модуле database
    original_engine = db_module.engine
    original_session = db_module.SessionLocal
    db_module.engine = test_engine
    db_module.SessionLocal = TestSessionLocal

    # Подменяем зависимость FastAPI
    app.dependency_overrides[get_db] = override_get_db

    # Заглушка RabbitMQ
    published = []
    original_publish = rmq.publish_ml_task
    rmq.publish_ml_task = lambda task_id, model_name, features: published.append(task_id)

    # Критично: роутер импортирует функцию напрямую через "from ... import",
    # поэтому патчим имя прямо в пространстве имён роутера
    import app.src.routers.predict as predict_router
    predict_router.publish_ml_task = lambda task_id, model_name, features: published.append(task_id)

    # Патчим init_db чтобы не ждал PostgreSQL
    with patch("src.main.init_db", side_effect=test_init_db):
        with TestClient(app, raise_server_exceptions=True) as c:
            c.published = published
            yield c

    # Восстанавливаем оригиналы
    db_module.engine = original_engine
    db_module.SessionLocal = original_session
    rmq.publish_ml_task = original_publish
    predict_router.publish_ml_task = original_publish
    app.dependency_overrides.clear()


# Вспомогательные фикстуры
@pytest.fixture
def registered_user(client):
    resp = client.post("/auth/register", json={
        "email": "test@example.com",
        "password": "testpass123",
    })
    assert resp.status_code == 201
    return {"email": "test@example.com", "password": "testpass123", "id": resp.json()["id"]}


@pytest.fixture
def auth_headers(client, registered_user):
    resp = client.post("/auth/login", json={
        "email": registered_user["email"],
        "password": registered_user["password"],
    })
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture
def funded_user(client, auth_headers):
    """Пользователь с балансом 100 кредитов."""
    resp = client.post("/balance/deposit", json={"amount": 100.0}, headers=auth_headers)
    assert resp.status_code == 200
    return auth_headers


@pytest.fixture
def ml_model(client):
    """ML-модель стоимостью 5 кредитов, созданная напрямую в тестовой БД."""
    db = TestSessionLocal()
    try:
        from app.src.models.orm import MLModelORM
        model = MLModelORM(
            name="Classifier v1",
            description="Test classifier",
            cost_per_prediction=5.0,
            is_active=True,
        )
        db.add(model)
        db.commit()
        db.refresh(model)
        return {"id": model.id, "name": model.name, "cost": model.cost_per_prediction}
    finally:
        db.close()
