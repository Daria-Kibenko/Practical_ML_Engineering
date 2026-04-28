"""
Сервис публикации ML-задач в очередь RabbitMQ.

Паттерн: один publisher → одна очередь → несколько consumers (round-robin).
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict

import pika
import pika.exceptions

from ..config import settings

logger = logging.getLogger(__name__)

QUEUE_NAME = settings.rabbitmq_queue


def _get_connection() -> pika.BlockingConnection:
    """Создать подключение к RabbitMQ."""
    params = pika.ConnectionParameters(
        host=settings.rabbitmq_host,
        port=settings.rabbitmq_port,
        credentials=pika.PlainCredentials(
            settings.rabbitmq_user,
            settings.rabbitmq_password,
        ),
        heartbeat=600,
        blocked_connection_timeout=300,
    )
    return pika.BlockingConnection(params)


def publish_ml_task(
    task_id: int,
    model_name: str,
    features: Dict[str, Any],
) -> None:
    """
    Опубликовать ML-задачу в очередь.

    Формат сообщения (JSON):
    {
        "task_id": 42,
        "features": {"x1": 1.2, "x2": 5.7},
        "model": "Classifier v1",
        "timestamp": "2026-01-01T12:00:00"
    }
    """
    message = {
        "task_id": task_id,
        "features": features,
        "model": model_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    try:
        connection = _get_connection()
        channel = connection.channel()

        # Объявляем очередь
        channel.queue_declare(queue=QUEUE_NAME, durable=True)

        channel.basic_publish(
            exchange="",                    # direct exchange
            routing_key=QUEUE_NAME,
            body=json.dumps(message),
            properties=pika.BasicProperties(
                delivery_mode=pika.DeliveryMode.Persistent,   # сообщение переживёт рестарт
                content_type="application/json",
            ),
        )
        connection.close()
        logger.info("Задача %s опубликована в очередь '%s'", task_id, QUEUE_NAME)

    except pika.exceptions.AMQPConnectionError as exc:
        logger.error("Ошибка подключения к RabbitMQ: %s", exc)
        raise RuntimeError("Брокер сообщений недоступен") from exc
