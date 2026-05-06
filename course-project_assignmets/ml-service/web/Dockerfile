# web/Dockerfile
FROM python:3.9-slim

WORKDIR /app

# Копируем зависимости (если requirements.txt лежит в web/)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем всё содержимое web/ в /app
COPY . .

# Открываем порт Flask
EXPOSE 5000

# Переменная окружения для Flask (если нужно)
ENV FLASK_APP=main.py

# Запускаем (точка входа – main.py)
CMD ["python", "main.py"]