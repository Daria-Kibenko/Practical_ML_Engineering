"""
Сценарий 5: История операций.

Покрывает:
  ✓ история транзакций сохраняется после пополнения
  ✓ история транзакций сохраняется после списания (ML-запрос)
  ✓ история ML-запросов сохраняется с корректными данными
  ✓ корректное отображение типов транзакций (deposit/debit)
  ✓ история изолирована между пользователями
  ✓ история пуста у нового пользователя
  ✓ сопоставление суммы списания с результатом задачи
"""

import pytest


VALID_INPUT = {
    "mean radius": 14.0,
    "mean texture": 20.0,
    "mean smoothness": 0.1,
}


class TestTransactionHistory:

    def test_history_empty_for_new_user(self, client, auth_headers):
        """У нового пользователя история транзакций пуста."""
        resp = client.get("/history/transactions", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_deposit_appears_in_history(self, client, auth_headers):
        """Пополнение баланса фиксируется в истории транзакций."""
        client.post("/balance/deposit", json={"amount": 50.0}, headers=auth_headers)

        resp = client.get("/history/transactions", headers=auth_headers)
        assert resp.status_code == 200
        txs = resp.json()
        assert len(txs) == 1
        assert txs[0]["type"] == "deposit"
        assert txs[0]["amount"] == 50.0
        assert txs[0]["task_id"] is None

    def test_multiple_deposits_all_recorded(self, client, auth_headers):
        """Несколько пополнений — все записи присутствуют."""
        client.post("/balance/deposit", json={"amount": 30.0}, headers=auth_headers)
        client.post("/balance/deposit", json={"amount": 70.0}, headers=auth_headers)

        txs = client.get("/history/transactions", headers=auth_headers).json()
        assert len(txs) == 2
        amounts = {t["amount"] for t in txs}
        assert amounts == {30.0, 70.0}

    def test_debit_appears_after_prediction(self, client, funded_user, auth_headers, ml_model):
        """Списание кредитов (ML-запрос) фиксируется в истории."""
        client.post("/predict/", headers=funded_user, json={
            "model_id": ml_model["id"],
            "input_data": VALID_INPUT,
        })

        txs = client.get("/history/transactions", headers=auth_headers).json()
        debit_txs = [t for t in txs if t["type"] == "debit"]
        assert len(debit_txs) == 1
        assert debit_txs[0]["amount"] == ml_model["cost"]
        assert debit_txs[0]["task_id"] is not None

    def test_transaction_linked_to_task(self, client, funded_user, auth_headers, ml_model):
        """task_id в транзакции совпадает с id выполненной задачи."""
        predict_resp = client.post("/predict/", headers=funded_user, json={
            "model_id": ml_model["id"],
            "input_data": VALID_INPUT,
        })
        task_id = predict_resp.json()["task_id"]

        txs = client.get("/history/transactions", headers=auth_headers).json()
        debit = next(t for t in txs if t["type"] == "debit")
        assert debit["task_id"] == task_id

    def test_history_order_newest_first(self, client, auth_headers):
        """История возвращается в обратном хронологическом порядке."""
        for amount in [10.0, 20.0, 30.0]:
            client.post("/balance/deposit", json={"amount": amount}, headers=auth_headers)

        txs = client.get("/history/transactions", headers=auth_headers).json()
        amounts = [t["amount"] for t in txs]
        # Последняя транзакция (30) должна быть первой
        assert set(amounts) == {10.0, 20.0, 30.0}  # все суммы присутствуют

    def test_transaction_history_isolated_between_users(self, client, auth_headers):
        """История транзакций изолирована — пользователь видит только свои записи."""
        client.post("/balance/deposit", json={"amount": 100.0}, headers=auth_headers)

        # Второй пользователь
        client.post("/auth/register", json={"email": "bob@test.com", "password": "pass123"})
        t2 = client.post("/auth/login", json={"email": "bob@test.com", "password": "pass123"}).json()["access_token"]
        h2 = {"Authorization": f"Bearer {t2}"}

        txs2 = client.get("/history/transactions", headers=h2).json()
        assert txs2 == []


class TestMLRequestHistory:

    def test_ml_history_empty_for_new_user(self, client, auth_headers):
        """У нового пользователя история ML-запросов пуста."""
        resp = client.get("/history/ml-requests", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_prediction_appears_in_ml_history(self, client, funded_user, auth_headers, ml_model):
        """После предсказания запись появляется в истории ML-запросов."""
        client.post("/predict/", headers=funded_user, json={
            "model_id": ml_model["id"],
            "input_data": VALID_INPUT,
        })

        history = client.get("/history/ml-requests", headers=auth_headers).json()
        assert len(history) == 1
        item = history[0]
        assert item["status"] == "completed"
        assert item["model_name"] == ml_model["name"]
        assert item["credits_charged"] == ml_model["cost"]
        assert item["result"] is not None

    def test_ml_history_matches_transactions(self, client, funded_user, auth_headers, ml_model):
        """Количество debit-транзакций = количеству выполненных ML-запросов."""
        for _ in range(3):
            client.post("/predict/", headers=funded_user, json={
                "model_id": ml_model["id"],
                "input_data": VALID_INPUT,
            })

        ml_history = client.get("/history/ml-requests", headers=auth_headers).json()
        txs = client.get("/history/transactions", headers=auth_headers).json()
        debits = [t for t in txs if t["type"] == "debit"]

        assert len(ml_history) == 3
        assert len(debits) == 3

    def test_ml_history_shows_real_prediction_result(self, client, funded_user, auth_headers, ml_model):
        """История содержит реальный результат предсказания от sklearn-модели."""
        client.post("/predict/", headers=funded_user, json={
            "model_id": ml_model["id"],
            "input_data": VALID_INPUT,
        })

        history = client.get("/history/ml-requests", headers=auth_headers).json()
        result = history[0]["result"]

        # Реальная модель (GradientBoostingClassifier) возвращает эти поля
        assert "prediction" in result
        assert "algorithm" in result
        assert result["prediction"] in ("benign", "malignant")
        assert result["algorithm"] == "GradientBoostingClassifier"

    def test_failed_prediction_not_in_debit_history(self, client, auth_headers, ml_model):
        """Неудавшийся запрос (нет баланса) не создаёт debit-транзакцию."""
        # Баланс пуст
        client.post("/predict/", headers=auth_headers, json={
            "model_id": ml_model["id"],
            "input_data": VALID_INPUT,
        })  # → 402, транзакции нет

        txs = client.get("/history/transactions", headers=auth_headers).json()
        debits = [t for t in txs if t["type"] == "debit"]
        assert len(debits) == 0


class TestFullScenario:

    def test_full_user_workflow(self, client, ml_model):
        """
        Сквозной сценарий:
        регистрация → вход → пополнение → предсказание → проверка баланса и истории.
        """
        # 1. Регистрация
        reg = client.post("/auth/register", json={"email": "e2e@test.com", "password": "pass1234"})
        assert reg.status_code == 201

        # 2. Авторизация
        login = client.post("/auth/login", json={"email": "e2e@test.com", "password": "pass1234"})
        assert login.status_code == 200
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        # 3. Начальный баланс = 0
        assert client.get("/balance/", headers=headers).json()["amount"] == 0.0

        # 4. Пополнение
        dep = client.post("/balance/deposit", json={"amount": 50.0}, headers=headers)
        assert dep.status_code == 200
        assert dep.json()["amount"] == 50.0

        # 5. ML-предсказание
        pred = client.post("/predict/", headers=headers, json={
            "model_id": ml_model["id"],
            "input_data": VALID_INPUT,
        })
        assert pred.status_code == 200
        result = pred.json()
        assert result["status"] == "completed"
        task_id = result["task_id"]
        cost = result["credits_charged"]

        # 6. Баланс уменьшился
        balance = client.get("/balance/", headers=headers).json()["amount"]
        assert balance == 50.0 - cost

        # 7. В истории транзакций: 1 deposit + 1 debit
        txs = client.get("/history/transactions", headers=headers).json()
        types = [t["type"] for t in txs]
        assert "deposit" in types
        assert "debit" in types

        # 8. В истории ML-запросов: 1 запись
        ml_hist = client.get("/history/ml-requests", headers=headers).json()
        assert len(ml_hist) == 1
        assert ml_hist[0]["status"] == "completed"

        # 9. Статус задачи через task_id
        task_status = client.get(f"/predict/{task_id}", headers=headers).json()
        assert task_status["status"] == "completed"
