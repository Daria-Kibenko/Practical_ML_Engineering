# ML Service — Объектная модель

Практическое задание №1: проектирование объектной модели личного кабинета пользователя ML-сервиса.

## Описание

Объектная модель описывает ядро системы, которая позволяет:

- регистрировать пользователей и управлять их балансом в условных кредитах;
- выполнять запросы к ML-моделям с автоматическим списанием кредитов;
- валидировать входные данные перед отправкой на предсказание;
- вести историю задач и транзакций каждого пользователя;
- администраторам — пополнять баланс пользователей и просматривать все транзакции.

Модель является основой для дальнейшей реализации: backend, REST API, Telegram-бота, ML-воркеров и Web-интерфейса.

---

## Структура проекта

```
ml_service/
│
├── main.py                      # Точка входа, smoke-test
│
├── enums/                       # Перечисления (константы домена)
│   ├── __init__.py
│   ├── roles.py                 # UserRole: USER, ADMIN
│   ├── task_status.py           # TaskStatus: PENDING, RUNNING, COMPLETED, FAILED, VALIDATION_ERROR
│   └── transaction_type.py      # TransactionType: DEPOSIT, DEBIT, ADMIN_DEPOSIT
│
├── models/                      # Доменные сущности
│   ├── __init__.py
│   ├── user.py                  # User + AdminUser
│   ├── ml_model.py              # MLModel (ABC) + ClassificationModel, RegressionModel
│   ├── ml_task.py               # MLTask — логика запуска предсказания
│   ├── prediction_result.py     # PredictionResult — результат предсказания
│   └── transaction.py           # Transaction (ABC) + DepositTransaction, DebitTransaction, AdminDepositTransaction
│
└── services/                    # Сервисный слой
    ├── __init__.py
    └── history_service.py       # MLRequestHistory — история задач и транзакций
```

---

## Сущности и их ответственность

### `User` / `AdminUser` — `models/user.py`

| Поле / Метод | Тип | Доступ | Описание |
|---|---|---|---|
| `_user_id` | `int` | private | Идентификатор пользователя |
| `_username` | `str` | private | Имя пользователя |
| `_email` | `str` | private | Email |
| `_password_hash` | `str` | private | Хэш пароля |
| `_role` | `UserRole` | private | Роль: USER или ADMIN |
| `_balance` | `float` | private | Баланс в кредитах |
| `deposit(amount)` | `float → None` | public | Пополнить баланс |
| `debit(amount)` | `float → None` | public | Списать кредиты |
| `has_sufficient_balance(amount)` | `float → bool` | public | Проверить достаточность средств |
| `is_admin()` | `→ bool` | public | Проверить роль администратора |

`AdminUser` наследует `User` и добавляет метод `top_up_user(target_user, amount)` для пополнения баланса других пользователей.

---

### `MLModel` (ABC) / `ClassificationModel` / `RegressionModel` — `models/ml_model.py`

| Поле / Метод | Тип | Доступ | Описание |
|---|---|---|---|
| `_model_id` | `int` | private | Идентификатор модели |
| `_name` | `str` | private | Название модели |
| `_description` | `str` | private | Описание модели |
| `_cost_per_prediction` | `float` | private | Стоимость одного предсказания |
| `predict(input_data)` | `Any → PredictionResult` | public abstract | Выполнить предсказание |
| `validate(input_data)` | `Any → (bool, list[str])` | public abstract | Валидировать входные данные |

Абстрактный базовый класс задаёт контракт. Конкретные модели реализуют `predict()` и `validate()` — **полиморфизм**.

---

### `MLTask` — `models/ml_task.py`

| Поле / Метод | Тип | Доступ | Описание |
|---|---|---|---|
| `_task_id` | `int` | private | Идентификатор задачи |
| `_input_data` | `Any` | private | Входные данные |
| `_user` | `User` | private | Ссылка на пользователя |
| `_model` | `MLModel` | private | Ссылка на ML-модель |
| `_status` | `TaskStatus` | private | Текущий статус задачи |
| `_result` | `PredictionResult?` | private | Результат предсказания |
| `_validation_errors` | `list[str]` | private | Ошибки валидации |
| `_created_at` | `datetime` | private | Время создания |
| `_completed_at` | `datetime?` | private | Время завершения |
| `run()` | `→ PredictionResult?` | public | Запустить выполнение задачи |

Метод `run()` реализует полный цикл: валидация → проверка баланса → предсказание → списание кредитов.

---

### `PredictionResult` — `models/prediction_result.py`

| Поле | Тип | Доступ | Описание |
|---|---|---|---|
| `_predicted_label` | `str?` | private | Предсказанный класс/метка |
| `_confidence` | `float?` | private | Уверенность модели |
| `_raw_output` | `dict` | private | Сырой вывод модели |
| `_created_at` | `datetime` | private | Время создания результата |

---

### `Transaction` (ABC) / `DepositTransaction` / `DebitTransaction` / `AdminDepositTransaction` — `models/transaction.py`

| Поле / Метод | Тип | Доступ | Описание |
|---|---|---|---|
| `_transaction_id` | `int` | private | Идентификатор транзакции |
| `_amount` | `float` | private | Сумма |
| `_user` | `User` | private | Связанный пользователь |
| `_ml_task` | `MLTask?` | private | Связанная ML-задача (если применимо) |
| `_created_at` | `datetime` | private | Дата и время транзакции |
| `_transaction_type` | `TransactionType` | private | Тип транзакции |
| `apply()` | `→ None` | public abstract | Применить транзакцию к балансу |

Три конкретных типа транзакций реализуют `apply()` по-разному — **полиморфизм**.

---

### `MLRequestHistory` — `services/history_service.py`

| Поле / Метод | Тип | Доступ | Описание |
|---|---|---|---|
| `_user` | `User` | private | Владелец истории |
| `_tasks` | `list[MLTask]` | private | Список задач |
| `_transactions` | `list[Transaction]` | private | Список транзакций |
| `add_task(task)` | `MLTask → None` | public | Добавить задачу |
| `add_transaction(tx)` | `Transaction → None` | public | Добавить транзакцию |
| `get_tasks(status?)` | `→ list[MLTask]` | public | Получить задачи (с фильтром по статусу) |
| `get_transactions(type?)` | `→ list[Transaction]` | public | Получить транзакции (с фильтром по типу) |
| `total_spent()` | `→ float` | public | Суммарно потрачено кредитов |

---

## Принципы ООП

**Инкапсуляция** — все поля классов объявлены приватными (`_field`). Доступ осуществляется только через `@property` и публичные методы. Например, баланс пользователя нельзя изменить напрямую — только через `deposit()` и `debit()`, которые содержат валидацию.

**Наследование** — `AdminUser` расширяет `User`, добавляя права администратора. `ClassificationModel` и `RegressionModel` наследуют абстрактный `MLModel`. `DepositTransaction`, `DebitTransaction`, `AdminDepositTransaction` наследуют абстрактный `Transaction`.

**Полиморфизм** — `MLModel.predict()` и `MLModel.validate()` объявлены абстрактными. `MLTask.run()` вызывает их не зная конкретного типа модели. Аналогично `Transaction.apply()` — поведение зависит от конкретного подкласса транзакции.
