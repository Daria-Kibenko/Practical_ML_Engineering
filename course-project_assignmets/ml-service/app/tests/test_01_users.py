"""
Сценарий 1: Работа с пользователями.

Покрывает:
  ✓ создание нового пользователя
  ✓ авторизация пользователя (получение JWT)
  ✓ повторная авторизация
  ✓ обработка ошибок при неверных данных
  ✓ защита эндпоинтов от неавторизованного доступа
"""

import pytest


class TestUserRegistration:

    def test_register_success(self, client):
        """Новый пользователь создаётся с корректными данными."""
        resp = client.post("/auth/register", json={
            "email": "alice@test.com",
            "password": "password123",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "alice@test.com"
        assert data["role"] == "user"
        assert "id" in data
        # Пароль никогда не возвращается в ответе
        assert "password" not in data
        assert "password_hash" not in data

    def test_register_duplicate_email(self, client):
        """Повторная регистрация с тем же email → 409 Conflict."""
        payload = {"email": "alice@test.com", "password": "pass123"}
        client.post("/auth/register", json=payload)
        resp = client.post("/auth/register", json=payload)
        assert resp.status_code == 409

    def test_register_short_password(self, client):
        """Пароль короче 6 символов → 422 Validation Error."""
        resp = client.post("/auth/register", json={
            "email": "bob@test.com",
            "password": "123",
        })
        assert resp.status_code == 422

    def test_register_invalid_email(self, client):
        """Некорректный email → 422 Validation Error."""
        resp = client.post("/auth/register", json={
            "email": "not-an-email",
            "password": "password123",
        })
        assert resp.status_code == 422


class TestUserLogin:

    def test_login_success(self, client, registered_user):
        """Авторизация с правильными данными → JWT-токен."""
        resp = client.post("/auth/login", json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert len(data["access_token"]) > 20  # токен не пустой

    def test_login_wrong_password(self, client, registered_user):
        """Неверный пароль → 401 Unauthorized."""
        resp = client.post("/auth/login", json={
            "email": registered_user["email"],
            "password": "WRONG_PASSWORD",
        })
        assert resp.status_code == 401

    def test_login_unknown_email(self, client):
        """Несуществующий email → 401 Unauthorized."""
        resp = client.post("/auth/login", json={
            "email": "nobody@test.com",
            "password": "password123",
        })
        assert resp.status_code == 401

    def test_login_repeated(self, client, registered_user):
        """Повторная авторизация возвращает новый валидный токен."""
        def login():
            return client.post("/auth/login", json={
                "email": registered_user["email"],
                "password": registered_user["password"],
            })

        r1 = login()
        r2 = login()
        assert r1.status_code == 200
        assert r2.status_code == 200
        # Токены могут совпасть (тот же payload + время), главное — оба валидны
        assert r1.json()["access_token"] is not None
        assert r2.json()["access_token"] is not None


class TestUserProfile:

    def test_me_authenticated(self, client, registered_user, auth_headers):
        """Авторизованный пользователь получает свой профиль."""
        resp = client.get("/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == registered_user["email"]
        assert data["role"] == "user"
        assert "password_hash" not in data

    def test_me_unauthenticated(self, client):
        """Запрос без токена → 401 Unauthorized."""
        resp = client.get("/auth/me")
        assert resp.status_code == 401

    def test_me_invalid_token(self, client):
        """Запрос с невалидным токеном → 401 Unauthorized."""
        resp = client.get("/auth/me", headers={"Authorization": "Bearer invalid.token.here"})
        assert resp.status_code == 401
