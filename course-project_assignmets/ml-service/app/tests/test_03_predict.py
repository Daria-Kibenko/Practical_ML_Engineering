"""
Сценарии 3 и 4: Списание кредитов и ML-запросы.

Покрывает:
  ✓ успешное списание при выполнении ML-запроса
  ✓ запрет списания при недостаточном балансе (402)
  ✓ отсутствие списания при ошибке запроса
  ✓ успешная отправка данных на предсказание
  ✓ получение результата предсказания (реальная модель)
  ✓ обработка некорректных входных данных (не числа)
  ✓ корректная обработка частично валидных данных
  ✓ проверка статуса задачи через GET /predict/{task_id}
"""

import pytest


VALID_INPUT = {
    "mean radius": 14.0,
    "mean texture": 20.0,
    "mean perimeter": 90.0,
    "mean area": 600.0,
    "mean smoothness": 0.1,
}

INVALID_INPUT = {
    "mean radius": "not-a-number",
    "mean texture": None,
}

MIXED_INPUT = {
    "mean radius": 14.0,        # валидный
    "mean texture": "текст",    # невалидный
    "mean smoothness": 0.1,     # валидный
}


class TestMLPrediction:

    def test_predict_success(self, client, funded_user, ml_model):
        """Успешное предсказание: реальная модель возвращает результат."""
        resp = client.post("/predict/", headers=funded_user, json={
            "model_id": ml_model["id"],
            "input_data": VALID_INPUT,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert data["result"] is not None
        assert data["credits_charged"] == ml_model["cost"]

        # Результат содержит реальные поля от sklearn-модели
        result = data["result"]
        assert "prediction" in result
        assert "algorithm" in result
        assert result["prediction"] in ("benign", "malignant")

    def test_predict_returns_task_id(self, client, funded_user, ml_model):
        """Ответ содержит task_id для последующего опроса."""
        resp = client.post("/predict/", headers=funded_user, json={
            "model_id": ml_model["id"],
            "input_data": VALID_INPUT,
        })
        assert resp.status_code == 200
        assert "task_id" in resp.json()
        assert isinstance(resp.json()["task_id"], int)

    def test_predict_unknown_model(self, client, funded_user):
        """Несуществующая модель → 404."""
        resp = client.post("/predict/", headers=funded_user, json={
            "model_id": 9999,
            "input_data": VALID_INPUT,
        })
        assert resp.status_code == 404

    def test_predict_empty_input(self, client, funded_user, ml_model):
        """Пустые входные данные → 422."""
        resp = client.post("/predict/", headers=funded_user, json={
            "model_id": ml_model["id"],
            "input_data": {},
        })
        assert resp.status_code == 422

    def test_predict_invalid_data_returns_validation_errors(self, client, funded_user, ml_model):
        """Полностью невалидные данные → задача создана, validation_errors в ответе."""
        resp = client.post("/predict/", headers=funded_user, json={
            "model_id": ml_model["id"],
            "input_data": {"feature": "not-a-number"},
        })
        # Задача выполнена (по пустому набору валидных признаков)
        assert resp.status_code == 200
        data = resp.json()
        assert data["validation_errors"] is not None
        assert len(data["validation_errors"]) == 1
        assert data["validation_errors"][0]["field"] == "feature"

    def test_predict_mixed_data_processes_valid_fields(self, client, funded_user, ml_model):
        """Частично валидные данные: предсказание выполняется по валидным полям."""
        resp = client.post("/predict/", headers=funded_user, json={
            "model_id": ml_model["id"],
            "input_data": MIXED_INPUT,
        })
        assert resp.status_code == 200
        data = resp.json()
        # Предсказание выполнено
        assert data["result"] is not None
        assert data["status"] == "completed"
        # Невалидное поле зафиксировано
        assert data["validation_errors"] is not None
        invalid_fields = [e["field"] for e in data["validation_errors"]]
        assert "mean texture" in invalid_fields
        # Валидные поля попали в предсказание
        valid_fields = data["result"].get("features_received", [])
        assert "mean radius" in valid_fields

    def test_list_models(self, client, auth_headers, ml_model):
        """GET /predict/models возвращает список активных моделей."""
        resp = client.get("/predict/models", headers=auth_headers)
        assert resp.status_code == 200
        models = resp.json()
        assert len(models) >= 1
        assert any(m["id"] == ml_model["id"] for m in models)


class TestCreditDeduction:

    def test_credits_deducted_after_predict(self, client, funded_user, ml_model, auth_headers):
        """После успешного предсказания баланс уменьшается на стоимость модели."""
        before = client.get("/balance/", headers=auth_headers).json()["amount"]

        client.post("/predict/", headers=funded_user, json={
            "model_id": ml_model["id"],
            "input_data": VALID_INPUT,
        })

        after = client.get("/balance/", headers=auth_headers).json()["amount"]
        assert after == before - ml_model["cost"]

    def test_insufficient_balance_returns_402(self, client, auth_headers, ml_model):
        """Предсказание при нулевом балансе → 402 Payment Required."""
        # Баланс не пополнялся — он 0.0
        resp = client.post("/predict/", headers=auth_headers, json={
            "model_id": ml_model["id"],
            "input_data": VALID_INPUT,
        })
        assert resp.status_code == 402

    def test_no_deduction_on_insufficient_balance(self, client, auth_headers, ml_model):
        """При отказе (402) баланс не изменяется."""
        # Пополняем меньше стоимости модели
        client.post("/balance/deposit", json={"amount": 1.0}, headers=auth_headers)
        before = client.get("/balance/", headers=auth_headers).json()["amount"]

        client.post("/predict/", headers=auth_headers, json={
            "model_id": ml_model["id"],
            "input_data": VALID_INPUT,
        })

        after = client.get("/balance/", headers=auth_headers).json()["amount"]
        assert after == before  # баланс не изменился

    def test_multiple_predictions_deduct_correctly(self, client, funded_user, ml_model, auth_headers):
        """Несколько предсказаний подряд — каждое списывает корректно."""
        initial = client.get("/balance/", headers=auth_headers).json()["amount"]

        for _ in range(3):
            r = client.post("/predict/", headers=funded_user, json={
                "model_id": ml_model["id"],
                "input_data": VALID_INPUT,
            })
            assert r.status_code == 200

        final = client.get("/balance/", headers=auth_headers).json()["amount"]
        assert final == initial - ml_model["cost"] * 3


class TestTaskStatus:

    def test_get_task_status_after_predict(self, client, funded_user, ml_model):
        """После синхронного предсказания статус задачи — completed."""
        resp = client.post("/predict/", headers=funded_user, json={
            "model_id": ml_model["id"],
            "input_data": VALID_INPUT,
        })
        task_id = resp.json()["task_id"]

        status_resp = client.get(f"/predict/{task_id}", headers=funded_user)
        assert status_resp.status_code == 200
        data = status_resp.json()
        assert data["task_id"] == task_id
        assert data["status"] == "completed"
        assert data["result"] is not None
        assert data["credits_charged"] == ml_model["cost"]

    def test_task_not_found_for_other_user(self, client, funded_user, ml_model):
        """Пользователь не видит чужие задачи → 404."""
        resp = client.post("/predict/", headers=funded_user, json={
            "model_id": ml_model["id"],
            "input_data": VALID_INPUT,
        })
        task_id = resp.json()["task_id"]

        # Регистрируем другого пользователя
        client.post("/auth/register", json={"email": "other@test.com", "password": "pass123"})
        token2 = client.post("/auth/login", json={
            "email": "other@test.com", "password": "pass123"
        }).json()["access_token"]
        headers2 = {"Authorization": f"Bearer {token2}"}

        resp2 = client.get(f"/predict/{task_id}", headers=headers2)
        assert resp2.status_code == 404

    def test_async_predict_returns_pending(self, client, funded_user, ml_model):
        """
        Асинхронный запрос → 202, статус pending.
        conftest заменяет publish_ml_task stub-функцией, поэтому RabbitMQ не нужен.
        """
        resp = client.post("/predict/async", headers=funded_user, json={
            "model_id": ml_model["id"],
            "input_data": VALID_INPUT,
        })
        assert resp.status_code == 202
        data = resp.json()
        assert data["status"] == "pending"
        assert "task_id" in data
        assert "message" in data

        # Задача создана в БД со статусом pending (воркер не запущен)
        task_id = data["task_id"]
        status = client.get(f"/predict/{task_id}", headers=funded_user).json()
        assert status["status"] == "pending"
        assert status["result"] is None
