FROM python:3.9-slim

WORKDIR /app

RUN pip install flask pika psycopg2-binary

COPY src/ /app/

CMD ["python", "app.py"]