# ML Service — Документация

Веб-сервис машинного обучения с личным кабинетом пользователя. Включает REST API на FastAPI, Flask веб-интерфейс, асинхронных воркеров через RabbitMQ и три реальных ML-модели на scikit-learn.

---

## Содержание

1. [Архитектура системы](#архитектура-системы)
2. [Структура проекта](#структура-проекта)
3. [Быстрый старт](#быстрый-старт)
4. [Переменные окружения](#переменные-окружения)
5. [ML-модели](#ml-модели)
6. [REST API](#rest-api)
7. [Веб-интерфейс](#веб-интерфейс)
8. [Тесты](#тесты)
9. [RabbitMQ и воркеры](#rabbitmq-и-воркеры)
10. [База данных](#база-данных)
11. [Примеры использования](#примеры-использования)

---

## Архитектура системы

```
Браузер / curl
      │
      ▼
 ┌─────────────┐   :80/:443
 │    Nginx    │◄──────────── единая точка входа
 └──────┬──────┘
        │
   ┌────┴────┐
   ▼         ▼
┌──────┐  ┌──────────┐
│ Web  │  │ FastAPI  │  :8000 (внутри Docker)
│Flask │  │   app    │
└──────┘  └─────┬────┘
                │
        ┌───────┴────────┐
        ▼                ▼
  ┌──────────┐    ┌────────────┐
  │PostgreSQL│    │  RabbitMQ  │
  └──────────┘    └─────┬──────┘
                        │ round-robin
                  ┌─────┴─────┐
                  ▼           ▼
             worker-1     worker-2
```

**Принципы:**
- `app` не открывает порты наружу — весь трафик через Nginx
- Баланс — отдельная таблица и сервис (`BalanceService`), не поле пользователя
- При списании используется `SELECT ... FOR UPDATE` для защиты от гонки
- ML-модели обучаются один раз при старте, хранятся в `.joblib` файлах
- Воркеры разделяют ORM-код с `app` через bind-mount тома

---

## Структура проекта

```
ml-service/
│
├── app/                          # FastAPI-бэкенд
│   ├── src/
│   │   ├── main.py               # точка входа, lifespan
│   │   ├── config.py             # настройки из env
│   │   ├── database.py           # SQLAlchemy engine
│   │   ├── init_data.py          # создание таблиц + демо-данные
│   │   │
│   │   ├── models/
│   │   │   ├── domain.py         # чистая ООП-модель (без ORM)
│   │   │   └── orm.py            # SQLAlchemy таблицы
│   │   │
│   │   ├── schemas/
│   │   │   └── schemas.py        # Pydantic запросы/ответы
│   │   │
│   │   ├── services/
│   │   │   ├── auth_service.py   # JWT, bcrypt
│   │   │   ├── balance_service.py# BalanceService (SELECT FOR UPDATE)
│   │   │   ├── ml_engine.py      # загрузка и вызов моделей
│   │   │   └── rabbitmq_publisher.py
│   │   │
│   │   ├── routers/
│   │   │   ├── auth.py           # /auth/*
│   │   │   ├── balance.py        # /balance/*
│   │   │   ├── predict.py        # /predict/*
│   │   │   └── history.py        # /history/*
│   │   │
│   │   └── ml_models/
│   │       └── train_and_save.py # обучение на реальных датасетах
│   │
│   └── tests/
│       ├── conftest.py           # SQLite + stub RabbitMQ
│       ├── test_01_users.py
│       ├── test_02_balance.py
│       ├── test_03_predict.py
│       └── test_04_history.py
│
├── web/                          # Flask веб-интерфейс
│   ├── main.py                   # create_app(), Jinja2-фильтры
│   ├── config.py                 # Config из env
│   ├── api_client.py             # все HTTP-вызовы к FastAPI
│   ├── routers/
│   │   ├── public.py             # GET / и /about
│   │   ├── auth.py               # /login, /register, /logout
│   │   └── dashboard.py          # /dashboard, /history, /deposit, /predict
│   ├── templates/
│   │   ├── base.html             # layout (navbar + flash + footer)
│   │   ├── index.html            # роутинг через JS (гость → about, user → dashboard)
│   │   ├── components/
│   │   │   ├── navbar.html       # .guest-only / .auth-only
│   │   │   ├── flash_messages.html
│   │   │   ├── balance_card.html # карточка баланса + быстрые суммы
│   │   │   ├── predict_form.html # форма ML-запроса + шаблоны
│   │   │   └── history_table.html
│   │   └── pages/
│   │       ├── about.html        # лендинг с описанием моделей
│   │       ├── login.html
│   │       ├── register.html
│   │       ├── dashboard.html    # кабинет: баланс + последние операции
│   │       ├── result.html       # результат предсказания + вероятности
│   │       └── history.html      # история с раскрытыми результатами
│   └── static/
│       ├── css/style.css
│       └── js/app.js
│
├── worker/
│   └── worker.py                 # RabbitMQ consumer + ML-предсказание
│
├── web-proxy/
│   └── nginx.conf
│
└── docker-compose.yml
```

---

## Быстрый старт

### Требования

- Docker Engine 24+
- Docker Compose v2

### Запуск

```bash
cd ml-service
docker compose up --build
```

При первом запуске автоматически:
1. Создаются все таблицы в PostgreSQL
2. Добавляются демо-пользователи и ML-модели
3. Обучаются и сохраняются три реальных sklearn-модели

### Адреса

| Адрес                        | Описание |
|------------------------------|---|
| `http://localhost:8888`      | Веб-интерфейс (Flask) |
| `http://localhost:8888/docs` | Swagger UI FastAPI |
| `http://localhost:15672`     | RabbitMQ Management (guest/guest) |

### Демо-пользователи

| Email | Пароль | Роль | Баланс |
|---|---|---|---|
| `user@example.com` | `password123` | user | 100 кредитов |
| `admin@example.com` | `admin123` | admin | 1000 кредитов |

### Остановка

```bash
docker compose down          # сохранить данные
docker compose down -v       # удалить все данные
```

### Масштабирование воркеров

```bash
docker compose up --scale worker=4
```

---

## Переменные окружения

### `app/.env`

```dotenv
DB_HOST=database
DB_PORT=5432
DB_NAME=ml_service
DB_USER=postgres
DB_PASSWORD=postgres

SECRET_KEY=change_me_in_production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

RABBITMQ_HOST=rabbitmq
RABBITMQ_PORT=5672
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest
RABBITMQ_QUEUE=ml_tasks

DEBUG=false
```

### `web/.env`

```dotenv
FLASK_SECRET_KEY=change_me_in_production
FLASK_DEBUG=false
API_BASE_URL=http://app:8888
```

---

## ML-модели

Три реальных модели на данных из `sklearn.datasets`. Обучаются при первом старте, сохраняются в `app/src/ml_models/*.joblib`.

### Classifier v1 — бинарная классификация

- **Датасет:** Breast Cancer Wisconsin (569 образцов, 30 признаков)
- **Алгоритм:** GradientBoostingClassifier
- **Метрики:** accuracy = 0.947, AUC = 0.986
- **Задача:** определить тип опухоли (benign / malignant)

**Пример запроса:**
```json
{
  "mean radius": 14.5,
  "mean texture": 20.1,
  "mean perimeter": 92.0,
  "mean area": 654.0,
  "mean smoothness": 0.098
}
```

**Пример ответа:**
```json
{
  "prediction": "benign",
  "confidence": 0.9821,
  "probabilities": { "malignant": 0.0179, "benign": 0.9821 },
  "algorithm": "GradientBoostingClassifier",
  "dataset": "Breast Cancer Wisconsin"
}
```

### Regressor v1 — регрессия

- **Датасет:** Diabetes (442 образца, 10 признаков)
- **Алгоритм:** RandomForestRegressor
- **Метрики:** MAE = 43.88
- **Задача:** предсказать прогрессию диабета через 1 год (25–346)

**Пример запроса:**
```json
{
  "age": 0.038,
  "sex": 0.050,
  "bmi": 0.062,
  "bp": 0.022,
  "s1": -0.044
}
```

**Пример ответа:**
```json
{
  "prediction": 152.4,
  "unit": "disease progression score (25–346)",
  "algorithm": "RandomForestRegressor"
}
```

### Anomaly Detector — детектор аномалий

- **Датасет:** Breast Cancer (обучен на benign-образцах)
- **Алгоритм:** IsolationForest
- **Метрики:** malignant recall = 0.83
- **Задача:** обнаружить аномальные клеточные параметры

**Пример ответа:**
```json
{
  "prediction": "anomaly",
  "is_anomaly": true,
  "anomaly_score": 0.74,
  "algorithm": "IsolationForest"
}
```

---

## REST API

Базовый URL: `http://localhost:8000`  
Swagger UI: `http://localhost:8000/docs`

Защищённые эндпоинты требуют заголовок:
```
Authorization: Bearer <access_token>
```

### Авторизация `/auth`

| Метод | URL | Описание | Auth |
|---|---|---|---|
| POST | `/auth/register` | Регистрация | — |
| POST | `/auth/login` | Вход, возвращает JWT | — |
| GET | `/auth/me` | Профиль текущего пользователя | ✓ |

### Баланс `/balance`

| Метод | URL | Описание | Auth |
|---|---|---|---|
| GET | `/balance/` | Текущий баланс | ✓ |
| POST | `/balance/deposit` | Пополнить баланс | ✓ |
| POST | `/balance/admin/deposit` | Пополнить баланс другому (только admin) | ✓ admin |

### ML-предсказания `/predict`

| Метод | URL | Описание | Auth |
|---|---|---|---|
| GET | `/predict/models` | Список доступных моделей | ✓ |
| GET | `/predict/models/info` | Метрики и датасеты моделей | — |
| POST | `/predict/` | Синхронное предсказание | ✓ |
| POST | `/predict/async` | Асинхронное (через RabbitMQ) | ✓ |
| GET | `/predict/{task_id}` | Статус и результат задачи | ✓ |

### История `/history`

| Метод | URL | Описание | Auth |
|---|---|---|---|
| GET | `/history/ml-requests` | История ML-запросов | ✓ |
| GET | `/history/transactions` | История транзакций | ✓ |
| GET | `/history/admin/transactions` | Все транзакции (только admin) | ✓ admin |

### Коды ответов

| Код | Ситуация |
|---|---|
| 200 | Успех |
| 201 | Ресурс создан |
| 202 | Принято (async predict) |
| 401 | Не авторизован |
| 402 | Недостаточно кредитов |
| 403 | Нет прав доступа |
| 404 | Не найдено |
| 409 | Email уже существует |
| 422 | Ошибка валидации |
| 503 | RabbitMQ недоступен |

---

## Веб-интерфейс

Flask-приложение работает поверх REST API. Не дублирует бизнес-логику — только отображение и маршрутизация.

### Страницы

| URL | Страница | Доступ |
|---|---|---|
| `/` | Роутинг: гость → `/about`, авторизован → `/dashboard` | Все |
| `/about` | Лендинг с описанием сервиса и моделей | Все |
| `/login` | Форма входа | Гость |
| `/register` | Форма регистрации | Гость |
| `/dashboard` | Личный кабинет: баланс, форма запроса, последние операции | Авторизован |
| `/history` | История ML-запросов и транзакций | Авторизован |
| `/logout` | Сброс сессии | Авторизован |

### Страница результата предсказания

После выполнения ML-запроса показывает:
- **Классификатор:** предсказанный класс + горизонтальные бары вероятностей
- **Регрессор:** числовое значение с единицей измерения
- **Детектор аномалий:** статус (normal/anomaly) + шкала anomaly score
- Таблицу отправленных данных
- Какие признаки использовала модель, а какие были заполнены нулём
- Предупреждения если часть данных не прошла валидацию
- Обновлённый баланс после списания

### История операций

Страница `/history` содержит две вкладки:

**ML-запросы** — для каждого завершённого запроса показывает:
- Название модели и статус
- Результат предсказания (класс, вероятности или anomaly score) прямо в списке
- Алгоритм и датасет
- Количество списанных кредитов и дату

**Транзакции** — хронологический список всех операций с балансом:
- Пополнения: зелёный значок ↑, сумма, дата
- Списания: красный значок ↓, сумма, номер связанной задачи, дата

### Как работает авторизация в браузере

Сессия хранится в серверной куке Flask (httpOnly).  
JS сохраняет флаг `ml_token` в `localStorage` — это сигнал для переключения видимости навбара.

При заходе на `/`:
```
localStorage["ml_token"] существует?
├── Да → window.location.replace("/dashboard")
└── Нет → window.location.replace("/about")
```

Элементы с классом `.guest-only` скрываются для авторизованных.  
Элементы с классом `.auth-only` скрываются для гостей.

---

## Тесты

Тесты используют SQLite in-memory и не требуют запущенного Docker.

### Запуск

```bash
cd app
pip install pytest httpx
pytest tests/ -v
```

### Покрытие (47 тестов)

| Файл | Тестов | Сценарии |
|---|---|---|
| `test_01_users.py` | 13 | регистрация, дубль email, слабый пароль, вход, неверный пароль, токен, профиль |
| `test_02_balance.py` | 10 | нулевой баланс, пополнение, накопление, нулевые суммы, изоляция между пользователями |
| `test_03_predict.py` | 14 | предсказание, task_id, 404 модели, валидация, частичные данные, 402, нет списания при отказе, async |
| `test_04_history.py` | 10 | история транзакций, порядок, связь с задачей, история ML, реальные поля sklearn, E2E-сценарий |

---

## RabbitMQ и воркеры

### Архитектура

```
POST /predict/async
      │
      ▼ JSON: { task_id, features, model, timestamp }
 Очередь "ml_tasks" (durable, persistent)
      │
      │ prefetch_count=1 (честный round-robin)
      ├─────────────┐
      ▼             ▼
  worker-1      worker-2
    1. Получить сообщение
    2. Статус → PROCESSING
    3. Валидация признаков
    4. ml_engine.run_prediction()
    5. BalanceService.debit() — SELECT FOR UPDATE
    6. Сохранить PredictionResultORM
    7. Статус → COMPLETED
    8. basic_ack ✓
```

### Гарантии доставки

- Очередь с `durable=True` — переживает рестарт RabbitMQ
- Сообщения с `delivery_mode=Persistent` — не теряются при перезагрузке
- `basic_nack(requeue=False)` при ошибке — не зависает в очереди бесконечно
- Воркер reconnect с retry (10 попыток × 5 секунд)

### Проверка статуса асинхронной задачи

```bash
# 1. Отправить задачу
curl -X POST http://localhost:8000/predict/async \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"model_id": 1, "input_data": {"mean radius": 14.5}}'
# → {"task_id": 42, "status": "pending"}

# 2. Опросить статус
curl http://localhost:8000/predict/42 \
  -H "Authorization: Bearer $TOKEN"
# → {"status": "completed", "result": {...}}
```

---

## База данных

### Схема

```
users                    balances
  id (PK)          1:1     id (PK)
  email (unique) ◄──────── user_id (FK, unique)
  password_hash            amount
  role                     updated_at
  is_active
  created_at
      │ 1:N
      ▼
  ml_tasks ──── N:1 ──► ml_models
    id (PK)                id (PK)
    user_id (FK)           name (unique)
    model_id (FK)          description
    input_data (JSON)      cost_per_prediction
    status                 is_active
    created_at
        │ 1:1
        ▼
  prediction_results       transactions
    id (PK)                  id (PK)
    task_id (FK, unique)     user_id (FK)
    output_data (JSON)       task_id (FK, nullable)
    credits_charged          type (deposit|debit)
    created_at               amount
                             created_at
```

### Подключение напрямую

```bash
docker compose exec database psql -U postgres -d ml_service

-- Баланс всех пользователей
SELECT u.email, b.amount FROM users u JOIN balances b ON b.user_id = u.id;

-- История транзакций с деталями
SELECT u.email, t.type, t.amount, t.created_at
FROM transactions t JOIN users u ON u.id = t.user_id
ORDER BY t.created_at DESC LIMIT 20;

-- Статистика задач
SELECT status, count(*) FROM ml_tasks GROUP BY status;
```

---

## Примеры использования

### Полный сценарий через curl

```bash
BASE="http://localhost:8000"

# 1. Регистрация
curl -s -X POST $BASE/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "alice@test.com", "password": "secret123"}' | python3 -m json.tool

# 2. Вход
TOKEN=$(curl -s -X POST $BASE/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "alice@test.com", "password": "secret123"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# 3. Пополнение баланса
curl -s -X POST $BASE/balance/deposit \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"amount": 50}' | python3 -m json.tool

# 4. Список моделей
curl -s $BASE/predict/models -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# 5. Синхронное предсказание (Classifier v1)
curl -s -X POST $BASE/predict/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model_id": 1,
    "input_data": {
      "mean radius": 17.99,
      "mean texture": 10.38,
      "mean perimeter": 122.8,
      "mean area": 1001.0,
      "mean smoothness": 0.1184
    }
  }' | python3 -m json.tool

# 6. Асинхронное предсказание
TASK=$(curl -s -X POST $BASE/predict/async \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"model_id": 2, "input_data": {"bmi": 0.062, "bp": 0.022}}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['task_id'])")

sleep 3
curl -s $BASE/predict/$TASK -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# 7. История транзакций
curl -s $BASE/history/transactions -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# 8. История ML-запросов
curl -s $BASE/history/ml-requests -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```
