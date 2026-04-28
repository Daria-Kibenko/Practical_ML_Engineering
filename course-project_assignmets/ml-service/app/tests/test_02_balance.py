"""
Сценарий 2: Работа с балансом.

Покрывает:
  ✓ получение начального (нулевого) баланса
  ✓ пополнение баланса
  ✓ корректное обновление суммы после пополнения
  ✓ накопительное пополнение (несколько операций)
  ✓ валидация суммы пополнения
  ✓ баланс изолирован между разными пользователями
"""

import pytest


class TestGetBalance:

    def test_initial_balance_is_zero(self, client, auth_headers):
        """После регистрации баланс равен 0."""
        resp = client.get("/balance/", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["amount"] == 0.0
        assert "user_id" in data

    def test_balance_requires_auth(self, client):
        """Баланс недоступен без авторизации."""
        resp = client.get("/balance/")
        assert resp.status_code == 401


class TestDeposit:

    def test_deposit_success(self, client, auth_headers):
        """Пополнение на корректную сумму → баланс обновлён."""
        resp = client.post("/balance/deposit", json={"amount": 50.0}, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["amount"] == 50.0
        assert data["deposited"] == 50.0

    def test_balance_reflects_deposit(self, client, auth_headers):
        """После пополнения GET /balance возвращает обновлённую сумму."""
        client.post("/balance/deposit", json={"amount": 75.0}, headers=auth_headers)
        resp = client.get("/balance/", headers=auth_headers)
        assert resp.json()["amount"] == 75.0

    def test_multiple_deposits_accumulate(self, client, auth_headers):
        """Несколько пополнений суммируются корректно."""
        client.post("/balance/deposit", json={"amount": 30.0}, headers=auth_headers)
        client.post("/balance/deposit", json={"amount": 20.0}, headers=auth_headers)
        client.post("/balance/deposit", json={"amount": 50.0}, headers=auth_headers)
        resp = client.get("/balance/", headers=auth_headers)
        assert resp.json()["amount"] == 100.0

    def test_deposit_zero_rejected(self, client, auth_headers):
        """Пополнение на 0 → 422 Validation Error."""
        resp = client.post("/balance/deposit", json={"amount": 0}, headers=auth_headers)
        assert resp.status_code == 422

    def test_deposit_negative_rejected(self, client, auth_headers):
        """Отрицательная сумма → 422 Validation Error."""
        resp = client.post("/balance/deposit", json={"amount": -10.0}, headers=auth_headers)
        assert resp.status_code == 422

    def test_deposit_requires_auth(self, client):
        """Пополнение без авторизации → 401."""
        resp = client.post("/balance/deposit", json={"amount": 50.0})
        assert resp.status_code == 401


class TestBalanceIsolation:

    def test_balances_are_isolated_between_users(self, client, auth_headers):
        """Баланс одного пользователя не влияет на баланс другого."""
        # Пополняем первого пользователя
        client.post("/balance/deposit", json={"amount": 100.0}, headers=auth_headers)

        # Регистрируем второго пользователя
        client.post("/auth/register", json={"email": "bob@test.com", "password": "password123"})
        token2 = client.post("/auth/login", json={
            "email": "bob@test.com", "password": "password123"
        }).json()["access_token"]
        headers2 = {"Authorization": f"Bearer {token2}"}

        # У второго пользователя баланс 0
        resp = client.get("/balance/", headers=headers2)
        assert resp.json()["amount"] == 0.0
