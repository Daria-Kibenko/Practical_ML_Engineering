FROM python:3.12-slim

WORKDIR /app

# Зависимости воркера
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Код воркера
COPY worker.py .

# Исходники приложения монтируются через volume (см. docker-compose.yml)
# Это позволяет воркеру использовать общие ORM-модели и доменные классы

ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

CMD ["python", "worker.py"]
