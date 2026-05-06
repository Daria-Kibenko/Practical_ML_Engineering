"""
Клиент для обращения к FastAPI-бэкенду.
Все HTTP-запросы к API проходят через этот модуль — роутеры не обращаются к API напрямую.
"""

import requests
from flask import session
from config import Config
import os

API_URL = os.getenv("API_URL", "http://app:8000")


def _headers():
    """Заголовок Authorization если пользователь авторизован."""
    token = session.get("token")
    return {"Authorization": f"Bearer {token}"} if token else {}


def _url(path: str) -> str:
    return API_URL.rstrip("/") + path


def login(email, password):
    # Бэкенд ожидает form-data с полями username и password
    response = requests.post(
        f"{API_URL}/auth/login",
        data={"username": email, "password": password}
    )
    if response.status_code == 200:
        return {"ok": True, "data": response.json()}
    else:
        return {"ok": False, "data": response.json(), "status": response.status_code}


def register(email, password):
    # Регистрация ожидает JSON с полями email и password
    response = requests.post(
        f"{API_URL}/auth/register",
        json={"email": email, "password": password}
    )
    if response.status_code == 201:
        return {"ok": True, "data": response.json()}
    else:
        return {"ok": False, "data": response.json(), "status": response.status_code}


def get_me() -> dict:
    r = requests.get(_url("/auth/me"), headers=_headers())
    return {"ok": r.status_code == 200, "data": r.json()}


def get_balance() -> dict:
    r = requests.get(_url("/balance"), headers=_headers())
    return {"ok": r.status_code == 200, "data": r.json()}


def deposit(amount: float) -> dict:
    r = requests.post(_url("/balance/deposit"), json={"amount": amount}, headers=_headers())
    return {"ok": r.status_code == 200, "data": r.json(), "status": r.status_code}


def get_models() -> dict:
    r = requests.get(_url("/predict/models"), headers=_headers())
    return {"ok": r.status_code == 200, "data": r.json()}


def predict(model_id: int, input_data: dict) -> dict:
    r = requests.post(
        _url("/predict/"),
        json={"model_id": model_id, "input_data": input_data},
        headers=_headers(),
    )
    return {"ok": r.status_code == 200, "data": r.json(), "status": r.status_code}


def get_ml_history(limit: int = 20) -> dict:
    r = requests.get(_url(f"/history/ml-requests?limit={limit}"), headers=_headers())
    return {"ok": r.status_code == 200, "data": r.json()}


def get_transactions(limit: int = 20) -> dict:
    r = requests.get(_url(f"/history/transactions?limit={limit}"), headers=_headers())
    return {"ok": r.status_code == 200, "data": r.json()}
