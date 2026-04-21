# ML Service — Личный кабинет пользователя

Бэкенд сервиса машинного обучения с личным кабинетом: регистрация, кредитный баланс, отправка данных на предсказание, история операций. Реализован как учебный проект, покрывающий весь стек: объектная модель → база данных → REST API → асинхронные воркеры → инфраструктура.

---

## Содержание

1. [Архитектура](#архитектура)
2. [Структура проекта](#структура-проекта)
3. [Быстрый старт](#быстрый-старт)
4. [Переменные окружения](#переменные-окружения)
5. [Сервисы Docker Compose](#сервисы-docker-compose)
6. [Объектная модель (ООП)](#объектная-модель-ооп)
7. [Схема базы данных (ORM)](#схема-базы-данных-orm)
8. [REST API — полный справочник](#rest-api--полный-справочник)
9. [Баланс и транзакции](#баланс-и-транзакции)
10. [Асинхронная обработка (RabbitMQ)](#асинхронная-обработка-rabbitmq)
11. [Аутентификация](#аутентификация)
12. [Демо-данные](#демо-данные)
13. [Разработка и отладка](#разработка-и-отладка)
14. [Примеры запросов](#примеры-запросов)

---

## Архитектура

```
Клиент (браузер / curl / Telegram bot)
        │
        ▼
  ┌─────────────┐
  │  Nginx      │  :80 / :443  — reverse proxy, единая точка входа
  │  web-proxy  │
  └──────┬──────┘
         │ проксирует все запросы
         ▼
  ┌─────────────┐
  │  FastAPI    │  :8000 (не открыт наружу)
  │  app        │  — REST API, бизнес-логика, publisher
  └──────┬──────┘
         │                          │
         │ SQLAlchemy ORM           │ pika (AMQP)
         ▼                          ▼
  ┌─────────────┐          ┌─────────────────┐
  │ PostgreSQL  │          │    RabbitMQ     │  :5672 (AMQP)
  │  database   │          │                 │  :15672 (UI)
  └─────────────┘          └────────┬────────┘
                                    │ round-robin
                              ┌─────┴─────┐
                              ▼           ▼
                           worker-1    worker-2   (масштабируется)
                              │           │
                              └─────┬─────┘
                                    │ SQLAlchemy (прямо в БД)
                                    ▼
                             PostgreSQL (результаты)
```

**Ключевые решения:**
- `app` не пробрасывает порты наружу — весь HTTP трафик идёт через Nginx.
- Воркеры разделяют код ORM-моделей с `app` через bind-mount тома (`./app/src`).
- Баланс — отдельная таблица и сервис, не поле пользователя.
- При списании кредитов используется `SELECT ... FOR UPDATE` для исключения гонки.
- `lifespan` FastAPI гарантирует создание таблиц и демо-данных при каждом старте.

---

## Структура проекта

```
ml-service/
│
├── app/                          # FastAPI-приложение
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── .env                      # переменные окружения (см. раздел ниже)
│   └── src/
│       ├── main.py               # точка входа, lifespan, подключение роутеров
│       ├── config.py             # Settings через pydantic-settings
│       ├── database.py           # engine, SessionLocal, get_db()
│       ├── init_data.py          # создание таблиц + демо-данные при старте
│       │
│       ├── models/
│       │   ├── domain.py         # чистая объектная модель (ООП, без ORM)
│       │   └── orm.py            # SQLAlchemy-модели (таблицы БД)
│       │
│       ├── schemas/
│       │   └── schemas.py        # Pydantic-схемы запросов и ответов
│       │
│       ├── services/
│       │   ├── auth_service.py   # JWT, хэширование паролей, FastAPI depends
│       │   ├── balance_service.py# BalanceService: deposit, debit, get
│       │   └── rabbitmq_publisher.py  # публикация задач в очередь
│       │
│       └── routers/
│           ├── auth.py           # /auth — регистрация, вход, профиль
│           ├── balance.py        # /balance — баланс и пополнение
│           ├── predict.py        # /predict — предсказания (sync + async)
│           └── history.py        # /history — история запросов и транзакций
│
├── worker/                       # ML-воркер (consumer RabbitMQ)
│   ├── Dockerfile
│   ├── requirements.txt
│   └── worker.py                 # подключение, валидация, предсказание, запись в БД
│
├── web-proxy/                    # Nginx reverse proxy
│   ├── Dockerfile
│   └── nginx.conf
│
├── docker-compose.yml            # описание всех 5 сервисов
└── README.md
```

---

## Быстрый старт

### Требования

- Docker Engine 24+
- Docker Compose v2 (`docker compose`, не `docker-compose`)

### Запуск

```
# 1. Клонировать / распаковать проект
cd ml-service

# 2. Запустить все сервисы (2 воркера по умолчанию)
docker compose up --build

# 3. Проверить, что всё поднялось
curl http://localhost/health
# → {"status":"ok","service":"ML Service API"}
```

После старта автоматически:
- создаются все таблицы в PostgreSQL,
- добавляются демо-пользователи и ML-модели.

### Полезные адреса

| Адрес | Описание |
|---|---|
| `http://localhost/docs` | Swagger UI — интерактивная документация API |
| `http://localhost/redoc` | ReDoc — альтернативная документация |
| `http://localhost/health` | Healthcheck |
| `http://localhost:15672` | RabbitMQ Management UI (guest / guest) |

### Остановка

```bash
# Остановить, сохранив данные в volumes
docker compose down

# Остановить и удалить все данные (БД, очереди)
docker compose down -v
```

### Масштабирование воркеров

```bash
# Запустить с 4 воркерами вместо 2
docker compose up --build --scale worker=4
```

---

## Переменные окружения

Файл `app/.env` читается сервисом `app` через `env_file`. Все параметры имеют безопасные дефолты для локального запуска.

```dotenv
# База данных
DB_HOST=database          # имя сервиса в docker-compose
DB_PORT=5432
DB_NAME=ml_service
DB_USER=postgres
DB_PASSWORD=postgres

# JWT-аутентификация 
SECRET_KEY=change_me_in_production_use_random_256bit_string
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440   # 24 часа

# RabbitMQ
RABBITMQ_HOST=rabbitmq
RABBITMQ_PORT=5672
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest
RABBITMQ_QUEUE=ml_tasks

# Приложение
DEBUG=false
APP_TITLE=ML Service API
```

> В продакшне обязательно замените `SECRET_KEY`, `DB_PASSWORD`, `RABBITMQ_DEFAULT_PASS` на случайные значения и не коммитьте `.env` в git.

Воркер читает свои переменные окружения из секции `environment` в `docker-compose.yml` — отдельного `.env` у него нет.

---

## Сервисы Docker Compose

### 1. `app` — FastAPI-приложение

- Собирается из `./app/Dockerfile` на базе `python:3.12-slim`.
- Исходный код монтируется через bind-mount (`./app/src:/app/src`) — изменения сразу видны без пересборки образа.
- Порт 8000 открыт только внутри Docker-сети (`expose`), снаружи недоступен.
- Запускается только после успешного healthcheck БД и RabbitMQ (`depends_on: condition: service_healthy`).
- `restart: unless-stopped` — перезапускается при любом сбое, кроме штатной остановки.

### 2. `web-proxy` — Nginx

- Собирается из `./web-proxy/Dockerfile` на базе `nginx:1.27-alpine`.
- Пробрасывает порты `:80` и `:443` хоста.
- Все HTTP-запросы проксирует на `app:8000`.
- Конфигурация `nginx.conf` копируется в образ при сборке.
- Зависит от `app` через `depends_on`.

### 3. `rabbitmq` — брокер сообщений

- Образ `rabbitmq:3.13-management-alpine` (включает Management UI).
- Порт `5672` — AMQP-протокол для воркеров и `app`.
- Порт `15672` — веб-интерфейс управления.
- Данные очередей хранятся в named volume `rabbitmq_data` — переживают рестарт контейнера.
- `restart: on-failure` — перезапускается только при сбое, не при `docker stop`.
- Healthcheck: `rabbitmq-diagnostics ping` каждые 10 секунд.

### 4. `database` — PostgreSQL

- Образ `postgres:16-alpine`.
- Данные хранятся в named volume `postgres_data` (не bind mount) — не зависят от файловой системы хоста и сохраняются при удалении контейнера.
- Healthcheck: `pg_isready` каждые 10 секунд.
- `restart: unless-stopped`.

### 5. `worker` — ML-воркер

- Собирается из `./worker/Dockerfile`.
- Монтирует `./app/src` — использует общие ORM-модели и доменные классы из `app`.
- По умолчанию запускается 2 экземпляра (`deploy.replicas: 2`).
- `restart: on-failure` — при сбое перезапускается, при штатной остановке нет.
- Задачи распределяются между воркерами по принципу round-robin через `prefetch_count=1`.

---

## Объектная модель (ООП)

Файл: `app/src/models/domain.py`

Чистые Python-классы без зависимости от ORM или фреймворков. Применены все три принципа ООП.

### Инкапсуляция

Все поля приватные (префикс `_`), доступ только через `@property`. Сеттер `balance` защищает инвариант — баланс не может стать отрицательным:

```
@balance.setter
def balance(self, value: float) -> None:
    if value < 0:
        raise ValueError("Баланс не может быть отрицательным")
    self._balance = value
```

### Наследование

Абстрактный класс `Transaction` определяет контракт. Конкретные подклассы реализуют его:

```
Transaction (ABC)
├── DepositTransaction   # пополнение
└── DebitTransaction     # списание (проверяет достаточность средств)
```

### Полиморфизм

Метод `apply(user)` вызывается единообразно, но поведение зависит от типа транзакции:

```
# Одинаковый вызов — разное поведение
deposit_tx.apply(user)   # прибавляет к балансу
debit_tx.apply(user)     # вычитает, выбрасывает ValueError при нехватке
```

### Перечисления

| Enum | Значения |
|---|---|
| `UserRole` | `user`, `admin` |
| `TaskStatus` | `pending`, `processing`, `completed`, `failed` |
| `TransactionType` | `deposit`, `debit` |

### Классы

| Класс | Назначение | Ключевые методы |
|---|---|---|
| `User` | Пользователь | `deposit()`, `debit()`, `is_admin()` |
| `MLModel` | ML-модель | `predict(input_data)` |
| `MLTask` | Задача на предсказание | `start_processing()`, `complete()`, `fail()` |
| `PredictionResult` | Результат | хранит `output_data`, `credits_charged` |
| `Transaction` (ABC) | Базовая транзакция | абстрактные `apply()`, `get_type()` |
| `DepositTransaction` | Пополнение | `apply()` — прибавляет |
| `DebitTransaction` | Списание | `apply()` — вычитает с проверкой |

---

## Схема базы данных (ORM)

Файл: `app/src/models/orm.py`

SQLAlchemy 2.0 с `Mapped`-аннотациями.

### Таблицы и связи

```
users ──────────────────────────────────────────┐
  id (PK)                                        │ 1:1
  email (unique, indexed)                        │
  password_hash                                  ▼
  role (enum: user|admin)              balances
  is_active                              id (PK)
  created_at                             user_id (FK → users.id, unique)
       │                                 amount
       │ 1:N                             updated_at
       ▼
  ml_tasks ──────────────────┐
    id (PK)                  │ N:1
    user_id (FK, indexed)    │
    model_id (FK)            │       ml_models
    input_data (JSON)        └────►    id (PK)
    status (enum)                      name (unique)
    created_at                         description
       │                               cost_per_prediction
       │ 1:1                           is_active
       ▼
  prediction_results         transactions
    id (PK)                    id (PK)
    task_id (FK, unique)       user_id (FK, indexed)
    output_data (JSON)         task_id (FK, nullable)
    credits_charged            type (enum: deposit|debit)
    created_at                 amount
                               created_at
```

### Описание таблиц

**`users`** — учётные данные и роль. Не содержит баланс — он вынесен в `balances`.

**`balances`** — баланс пользователя (один к одному с `users`). Отдельная таблица позволяет блокировать строку при списании (`SELECT FOR UPDATE`) без блокировки всей записи пользователя.

**`ml_models`** — справочник доступных ML-моделей с ценой предсказания.

**`ml_tasks`** — каждый запрос на предсказание. Хранит входные данные и статус. Статус обновляется как FastAPI-приложением (синхронный режим), так и воркером (асинхронный).

**`prediction_results`** — результат выполнения задачи: выходные данные в JSON и списанное количество кредитов. Связь 1:1 с задачей.

**`transactions`** — полная история операций с балансом: пополнения и списания. Списание может быть привязано к конкретной задаче (`task_id`).

---

## REST API — полный справочник

Базовый URL: `http://localhost`  
Swagger UI: `http://localhost/docs`

Все защищённые эндпоинты требуют заголовок:
```
Authorization: Bearer <access_token>
```

---

### `/auth` — Аутентификация

#### `POST /auth/register` — регистрация

Запрос:
```json
{
  "email": "user@example.com",
  "password": "secret123"
}
```

Ответ `201 Created`:
```json
{
  "id": 3,
  "email": "user@example.com",
  "role": "user",
  "created_at": "2026-01-15T10:00:00"
}
```

Ошибки: `409` — email уже занят, `422` — пароль короче 6 символов.

---

#### `POST /auth/login` — вход

Запрос:
```json
{
  "email": "user@example.com",
  "password": "secret123"
}
```

Ответ `200 OK`:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

Токен действует 24 часа (настраивается через `ACCESS_TOKEN_EXPIRE_MINUTES`).

Ошибки: `401` — неверные данные, `403` — аккаунт деактивирован.

---

#### `GET /auth/me` — профиль текущего пользователя

Ответ `200 OK`:
```json
{
  "id": 1,
  "email": "user@example.com",
  "role": "user",
  "created_at": "2026-01-15T10:00:00"
}
```

---

### `/balance` — Баланс

#### `GET /balance/` — текущий баланс

Ответ `200 OK`:
```json
{
  "user_id": 1,
  "amount": 95.0
}
```

---

#### `POST /balance/deposit` — пополнить баланс

Запрос:
```json
{
  "amount": 50.0
}
```

Ответ `200 OK`:
```json
{
  "user_id": 1,
  "amount": 145.0,
  "deposited": 50.0
}
```

Ошибки: `422` — сумма должна быть положительной.

---

#### `POST /balance/admin/deposit` — пополнить баланс любому пользователю

Только для администраторов.

Запрос:
```json
{
  "user_id": 3,
  "amount": 100.0
}
```

Ответ `200 OK`:
```json
{
  "user_id": 3,
  "amount": 100.0,
  "deposited": 100.0
}
```

Ошибки: `403` — не администратор, `404` — пользователь не найден.

---

### `/predict` — ML-предсказания

#### `GET /predict/models` — список доступных моделей

Ответ `200 OK`:
```json
[
  {
    "id": 1,
    "name": "Classifier v1",
    "description": "Базовая классификационная модель...",
    "cost_per_prediction": 1.0
  },
  {
    "id": 2,
    "name": "Regressor v1",
    "description": "Модель регрессии...",
    "cost_per_prediction": 2.0
  },
  {
    "id": 3,
    "name": "Anomaly Detector",
    "description": "Детектор аномалий...",
    "cost_per_prediction": 3.0
  }
]
```

---

#### `POST /predict/` — синхронное предсказание 

Предсказание выполняется немедленно. Кредиты списываются в той же транзакции БД.

Запрос:
```json
{
  "model_id": 1,
  "input_data": {
    "feature1": 2.5,
    "feature2": -1.0,
    "feature3": 0.8
  }
}
```

Ответ `200 OK` (успех):
```json
{
  "task_id": 42,
  "status": "completed",
  "result": {
    "model": "Classifier v1",
    "prediction": "positive",
    "confidence": 0.57,
    "features_used": ["feature1", "feature2", "feature3"]
  },
  "credits_charged": 1.0,
  "validation_errors": null
}
```

Ответ при частично невалидных данных — предсказание выполняется по валидным полям, ошибочные возвращаются в `validation_errors`:
```json
{
  "task_id": 43,
  "status": "completed",
  "result": {
    "model": "Classifier v1",
    "prediction": "positive",
    "confidence": 0.55,
    "features_used": ["feature1"],
    "validation_errors": [{"field": "name", "error": "..."}]
  },
  "credits_charged": 1.0,
  "validation_errors": [
    {
      "field": "name",
      "error": "Ожидается числовое значение, получено: str"
    }
  ]
}
```

Ошибки: `402` — недостаточно кредитов, `404` — модель не найдена.

---

#### `POST /predict/async` — асинхронное предсказание через RabbitMQ

Задача помещается в очередь и обрабатывается воркером в фоне. Кредиты списываются воркером после завершения.

Запрос — такой же, как у синхронного.

Ответ `202 Accepted`:
```json
{
  "task_id": 44,
  "status": "pending",
  "message": "Задача поставлена в очередь. Используйте GET /predict/{task_id} для проверки статуса."
}
```

Ошибки: `402` — недостаточно кредитов, `503` — RabbitMQ недоступен.

---

#### `GET /predict/{task_id}` — статус и результат задачи

Используется для опроса состояния асинхронной задачи.

Ответ (задача в очереди):
```json
{
  "task_id": 44,
  "status": "pending",
  "model_name": "Classifier v1",
  "result": null,
  "credits_charged": null
}
```

Ответ (задача выполнена):
```json
{
  "task_id": 44,
  "status": "completed",
  "model_name": "Classifier v1",
  "result": {
    "model": "Classifier v1",
    "prediction": "negative",
    "confidence": 0.52,
    "features_used": ["x1", "x2"],
    "worker_id": "worker-abc123",
    "processed_at": "2026-01-15T10:05:00+00:00"
  },
  "credits_charged": 1.0
}
```

Ошибки: `404` — задача не найдена или принадлежит другому пользователю.

---

### `/history` — История

#### `GET /history/ml-requests` — история ML-запросов

Параметры: `?limit=50&offset=0`

Ответ `200 OK`:
```json
[
  {
    "id": 42,
    "model_name": "Classifier v1",
    "status": "completed",
    "credits_charged": 1.0,
    "result": { "prediction": "positive", "confidence": 0.57 },
    "created_at": "2026-01-15T10:00:00"
  }
]
```

---

#### `GET /history/transactions` — история транзакций

Параметры: `?limit=50&offset=0`

Ответ `200 OK`:
```json
[
  {
    "id": 10,
    "type": "debit",
    "amount": 1.0,
    "task_id": 42,
    "created_at": "2026-01-15T10:00:00"
  },
  {
    "id": 9,
    "type": "deposit",
    "amount": 50.0,
    "task_id": null,
    "created_at": "2026-01-15T09:50:00"
  }
]
```

---

#### `GET /history/admin/transactions` — все транзакции системы

Только для администраторов. Параметры: `?limit=100&offset=0`

Формат ответа — такой же как у `/history/transactions`.

---

### Коды ответов

| Код | Ситуация |
|---|---|
| `200` | Успех |
| `201` | Ресурс создан (регистрация) |
| `202` | Принято в обработку (async predict) |
| `401` | Нет или неверный токен |
| `402` | Недостаточно кредитов |
| `403` | Нет прав (не администратор) |
| `404` | Ресурс не найден |
| `409` | Конфликт (email уже занят) |
| `422` | Ошибка валидации входных данных |
| `503` | Брокер сообщений недоступен |

---

## Баланс и транзакции

Баланс хранится в отдельной таблице `balances` (не в `users`) и управляется исключительно через `BalanceService`.

### Почему отдельная таблица?

- **Изоляция блокировок.** При списании кредитов применяется `SELECT ... FOR UPDATE` — блокируется только строка баланса, а не вся запись пользователя. Это предотвращает гонку при одновременных запросах.
- **Ясность ответственности.** Класс `User` отвечает за идентификацию и авторизацию. `Balance` — за финансовое состояние.
- **Масштабируемость.** При необходимости таблицу балансов можно перенести в отдельную БД или добавить версионирование строк без изменения схемы пользователей.

### BalanceService

Единственный способ работы с балансом в коде — через методы сервиса:

```
svc = BalanceService(db)

# Получить баланс (создаёт нулевой, если не существует)
balance = svc.get_balance(user_id=1)

# Пополнить — записывает транзакцию типа DEPOSIT
balance = svc.deposit(user_id=1, amount=50.0)

# Списать — SELECT FOR UPDATE + проверка + транзакция DEBIT
# Выбрасывает InsufficientFundsError если средств недостаточно
balance = svc.debit(user_id=1, amount=2.0, task_id=42)
```

Каждый вызов `deposit` и `debit` автоматически создаёт запись в таблице `transactions` — история операций ведётся без дополнительных действий.

---

## Асинхронная обработка (RabbitMQ)

### Схема взаимодействия

```
POST /predict/async
      │
      ▼
  FastAPI (publisher)
      │
      │  JSON: { task_id, features, model, timestamp }
      ▼
  Очередь "ml_tasks" (durable, persistent)
      │
      │  round-robin distribution (prefetch_count=1)
      ├──────────────────────┐
      ▼                      ▼
  worker-1              worker-2
  1. Получить сообщение
  2. Обновить статус → PROCESSING
  3. Валидировать features
  4. Выполнить предсказание (MLModel.predict)
  5. BalanceService.debit (SELECT FOR UPDATE)
  6. Сохранить PredictionResult
  7. Обновить статус → COMPLETED
  8. basic_ack ✓
```

### Гарантии доставки

- Очередь объявлена с `durable=True` — переживает рестарт RabbitMQ.
- Сообщения публикуются с `delivery_mode=Persistent` — не теряются при перезагрузке брокера.
- `prefetch_count=1` — воркер берёт следующее сообщение только после завершения предыдущего.
- При ошибке обработки воркер отправляет `basic_nack(requeue=False)` — сообщение не возвращается в очередь (предотвращает бесконечный цикл).

### Идентификация воркера

В результате предсказания всегда есть поля:
```json
{
  "worker_id": "abc123f4d5e6",
  "processed_at": "2026-01-15T10:05:00+00:00"
}
```
`worker_id` — это hostname контейнера. По нему можно определить, какой экземпляр воркера обработал задачу.

### Retry при старте

Воркер пытается подключиться к RabbitMQ 10 раз с интервалом 5 секунд. Это нужно, потому что RabbitMQ может стартовать медленнее Docker healthcheck предполагает.

---

## Аутентификация

Используется JWT (JSON Web Token) через библиотеку `python-jose`.

### Процесс

```
POST /auth/login  →  { access_token: "eyJ..." }
         │
         │  токен вставляется в заголовок
         ▼
GET /balance/  →  Authorization: Bearer eyJ...
         │
         ▼
  auth_service.get_current_user()
    │  1. OAuth2PasswordBearer извлекает токен
    │  2. jwt.decode проверяет подпись и срок действия
    │  3. из payload["sub"] берётся user_id
    │  4. загружается UserORM из БД
    └► возвращается пользователь как зависимость FastAPI
```

### Структура токена

```
{
  "sub": "1",          // user_id в виде строки
  "exp": 1736000000    // Unix timestamp истечения
}
```

### Защита эндпоинтов

```
# Обычный пользователь
@router.get("/balance/")
def get_balance(current_user: UserORM = Depends(get_current_user)):
    ...

# Только администратор
@router.post("/balance/admin/deposit")
def admin_deposit(_admin: UserORM = Depends(get_current_admin)):
    ...
```

`get_current_admin` вызывает `get_current_user` и дополнительно проверяет `role == UserRole.ADMIN`.

---

## Демо-данные

При каждом старте приложения `init_data.py` проверяет и при необходимости создаёт:

### Пользователи

| Email | Пароль | Роль | Начальный баланс |
|---|---|---|---|
| `user@example.com` | `password123` | `user` | 100 кредитов |
| `admin@example.com` | `admin123` | `admin` | 1000 кредитов |

### ML-модели

| Название | Описание | Стоимость |
|---|---|---|
| Classifier v1 | Бинарная классификация | 1 кредит |
| Regressor v1 | Числовое предсказание | 2 кредита |
| Anomaly Detector | Обнаружение аномалий | 3 кредита |

Инициализация идемпотентна — повторный запуск не дублирует данные и не перезаписывает существующие.

---

## Разработка и отладка

### Локальный запуск без Docker (только app)

```bash
cd app

# Установить зависимости
pip install -r requirements.txt

# Запустить (нужна внешняя БД и RabbitMQ, или поменять .env)
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### Просмотр логов

```bash
# Все сервисы
docker compose logs -f

# Только воркеры
docker compose logs -f worker

# Только приложение
docker compose logs -f app
```

### Включить SQL-логи

Поставьте `DEBUG=true` в `app/.env` — SQLAlchemy будет выводить все SQL-запросы.

### Подключение к БД напрямую

```bash
docker compose exec database psql -U postgres -d ml_service

-- Посмотреть баланс всех пользователей
SELECT u.email, b.amount FROM users u JOIN balances b ON b.user_id = u.id;

-- История транзакций
SELECT u.email, t.type, t.amount, t.created_at
FROM transactions t JOIN users u ON u.id = t.user_id
ORDER BY t.created_at DESC LIMIT 20;

-- Статистика задач
SELECT status, count(*) FROM ml_tasks GROUP BY status;
```

### Сброс данных

```bash
# Полный сброс (удалить все данные и пересоздать)
docker compose down -v && docker compose up --build
```

---

## Примеры запросов

Ниже — полный сценарий работы с API через `curl`.

```bash
BASE="http://localhost"

# 1. Регистрация
curl -s -X POST $BASE/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "alice@test.com", "password": "alicepass"}' | python3 -m json.tool

# 2. Вход и сохранение токена
TOKEN=$(curl -s -X POST $BASE/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "alice@test.com", "password": "alicepass"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

echo "Token: ${TOKEN:0:30}..."

# 3. Профиль 
curl -s $BASE/auth/me -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# 4. Пополнение баланса 
curl -s -X POST $BASE/balance/deposit \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"amount": 25}' | python3 -m json.tool

# 5. Проверка баланса
curl -s $BASE/balance/ -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# 6. Список моделей
curl -s $BASE/predict/models -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# 7. Синхронное предсказание
curl -s -X POST $BASE/predict/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"model_id": 1, "input_data": {"age": 35, "income": 75000, "score": 0.8}}' \
  | python3 -m json.tool

# 8. Предсказание с невалидными данными (частичная обработка)
curl -s -X POST $BASE/predict/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"model_id": 1, "input_data": {"age": 35, "name": "Alice", "score": 0.9}}' \
  | python3 -m json.tool
# name — строка, вернётся в validation_errors; age и score будут обработаны

# 9. Асинхронное предсказание
TASK_ID=$(curl -s -X POST $BASE/predict/async \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"model_id": 2, "input_data": {"x1": 1.5, "x2": 3.0}}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['task_id'])")

echo "Async task_id: $TASK_ID"

# 10. Опрос статуса задачи
sleep 2
curl -s $BASE/predict/$TASK_ID -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# 11. История ML-запросов
curl -s "$BASE/history/ml-requests?limit=5" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# 12. История транзакций
curl -s $BASE/history/transactions \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# 13. Демо-аккаунт администратора
ADMIN_TOKEN=$(curl -s -X POST $BASE/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "admin123"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Пополнить баланс Алисе от имени администратора
ALICE_ID=$(curl -s $BASE/auth/me -H "Authorization: Bearer $TOKEN" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

curl -s -X POST $BASE/balance/admin/deposit \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"user_id\": $ALICE_ID, \"amount\": 100}" | python3 -m json.tool

# Все транзакции системы (только для админа)
curl -s "$BASE/history/admin/transactions?limit=10" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | python3 -m json.tool
```
