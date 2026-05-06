"""
ML-воркер — Consumer RabbitMQ.

Архитектура: один publisher (FastAPI) → очередь ml_tasks → несколько воркеров (round-robin).

Каждый воркер:
  1. Подключается к RabbitMQ с retry.
  2. Берёт по одному сообщению (prefetch=1 — честный round-robin).
  3. Валидирует входные данные (только числовые признаки).
  4. Выполняет предсказание через РЕАЛЬНУЮ ML-модель (sklearn).
  5. Списывает кредиты через BalanceService (SELECT FOR UPDATE).
  6. Сохраняет результат в PostgreSQL напрямую.
  7. Подтверждает обработку (ack) либо отклоняет без requeue (nack).
"""

from __future__ import annotations

import json
import logging
import os
import socket
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import pika
import pika.exceptions
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Конфигурация
RABBITMQ_HOST  = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_PORT  = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_USER  = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASS  = os.getenv("RABBITMQ_PASSWORD", "guest")
RABBITMQ_QUEUE = os.getenv("RABBITMQ_QUEUE", "ml_tasks")

DB_URL = "postgresql+psycopg2://{user}:{pw}@{host}:{port}/{db}".format(
    user=os.getenv("DB_USER", "postgres"),
    pw=os.getenv("DB_PASSWORD", "postgres"),
    host=os.getenv("DB_HOST", "database"),
    port=os.getenv("DB_PORT", "5432"),
    db=os.getenv("DB_NAME", "ml_service"),
)

WORKER_ID = socket.gethostname()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | worker=" + WORKER_ID + " | %(message)s",
)
logger = logging.getLogger(__name__)

# sys.path: работает и в Docker, и локально в PyCharm
# Docker:  worker.py → /app/worker.py,  src/ → /app/src/
# PyCharm: worker.py → .../worker/worker.py, src/ → .../app/src/
_worker_dir = os.path.dirname(os.path.abspath(__file__))

if os.path.isdir(os.path.join(_worker_dir, "src")):
    _app_root = _worker_dir                                          # Docker
else:
    _app_root = os.path.abspath(os.path.join(_worker_dir, "..", "app"))  # локально

if _app_root not in sys.path:
    sys.path.insert(0, _app_root)

logger.debug("app root: %s", _app_root)

# Импорты из пакета src
from app.src.models.domain import TaskStatus
from app.src.models.orm import MLModelORM, MLTaskORM, PredictionResultORM
from app.src.services.balance_service import BalanceService, InsufficientFundsError
from app.src.services.ml_engine import run_prediction

# БД
engine = create_engine(DB_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)


# Валидация входных данных
def validate_features(
    features: Dict[str, Any],
) -> Tuple[Dict[str, float], List[str]]:
    """Отделяет числовые признаки от невалидных."""
    valid: Dict[str, float] = {}
    errors: List[str] = []
    for key, value in features.items():
        if isinstance(value, (int, float)):
            valid[key] = float(value)
        else:
            errors.append(
                "{}: ожидается число, получено {!r}".format(key, type(value).__name__)
            )
    return valid, errors


# Обработка одного сообщения
def process_message(body: bytes) -> None:
    raw = body.decode("utf-8")
    logger.info("Получено: %s", raw[:200])

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("Некорректный JSON: %s", exc)
        return

    task_id: Optional[int] = data.get("task_id")
    features: Dict[str, Any] = data.get("features", {})
    model_name: str = data.get("model", "Classifier v1")

    if not task_id:
        logger.error("Нет task_id — пропускаем")
        return

    logger.info("Обрабатываю task_id=%s model=%s", task_id, model_name)

    with SessionLocal() as db:
        task = db.get(MLTaskORM, task_id)
        if not task:
            logger.error("Задача %s не найдена в БД", task_id)
            return

        task.status = TaskStatus.PROCESSING
        db.commit()

        try:
            # 1. Валидация
            valid_features, errors = validate_features(features)
            if errors:
                logger.warning("Невалидные поля задачи %s: %s", task_id, errors)

            # 2. Реальное ML-предсказание (sklearn)
            model_orm = db.get(MLModelORM, task.model_id)
            cost = model_orm.cost_per_prediction if model_orm else 1.0

            result = run_prediction(model_name, valid_features)
            result["worker_id"] = WORKER_ID
            result["processed_at"] = datetime.now(timezone.utc).isoformat()
            if errors:
                result["validation_errors"] = errors

            logger.info(
                "task_id=%s prediction=%s algorithm=%s",
                task_id, result.get("prediction"), result.get("algorithm"),
            )

            # 3. Списываем кредиты через BalanceService (SELECT FOR UPDATE)
            try:
                BalanceService(db).debit(
                    user_id=task.user_id,
                    amount=cost,
                    task_id=task.id,
                )
            except InsufficientFundsError as exc:
                logger.warning("Задача %s: %s — результат сохранён без списания", task_id, exc)
                cost = 0.0

            # 4. Сохраняем результат
            db.add(PredictionResultORM(
                task_id=task.id,
                output_data=result,
                credits_charged=cost,
            ))
            task.status = TaskStatus.COMPLETED
            db.commit()

            logger.info("Задача %s завершена | charged=%.2f", task_id, cost)

        except Exception as exc:
            db.rollback()
            task.status = TaskStatus.FAILED
            db.commit()
            logger.error("Ошибка задачи %s: %s", task_id, exc)
            raise


# RabbitMQ Consumer
def callback(ch, method, _properties, body):
    try:
        process_message(body)
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as exc:
        logger.error("Критическая ошибка: %s — nack без requeue", exc)
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def connect_with_retry(max_retries: int = 10, delay: int = 5) -> pika.BlockingConnection:
    params = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        credentials=pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS),
        heartbeat=600,
        blocked_connection_timeout=300,
    )
    for attempt in range(1, max_retries + 1):
        try:
            conn = pika.BlockingConnection(params)
            logger.info("Подключён к RabbitMQ (попытка %d)", attempt)
            return conn
        except pika.exceptions.AMQPConnectionError:
            logger.warning(
                "RabbitMQ недоступен, жду %ds (попытка %d/%d)",
                delay, attempt, max_retries,
            )
            time.sleep(delay)
    raise RuntimeError(
        "Не удалось подключиться к RabbitMQ после {} попыток".format(max_retries)
    )


def start_worker() -> None:
    logger.info("Воркер %s запускается...", WORKER_ID)
    connection = connect_with_retry()
    channel = connection.channel()
    channel.queue_declare(queue=RABBITMQ_QUEUE, durable=True)
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=RABBITMQ_QUEUE, on_message_callback=callback)
    logger.info("Воркер %s ожидает задачи в '%s'", WORKER_ID, RABBITMQ_QUEUE)
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        channel.stop_consuming()
        logger.info("Воркер %s остановлен", WORKER_ID)
    finally:
        connection.close()


if __name__ == "__main__":
    start_worker()
