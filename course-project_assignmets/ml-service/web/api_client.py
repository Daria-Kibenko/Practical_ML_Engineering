"""
Клиент для обращения к FastAPI-бэкенду.
Все HTTP-запросы к API проходят через этот модуль — роутеры не обращаются к API напрямую.
"""

import requests
from flask import session
from config import Config


def _headers():
    """Заголовок Authorization если пользователь авторизован."""
    token = session.get("token")
    return {"Authorization": f"Bearer {token}"} if token else {}


def _url(path: str) -> str:
    return Config.API_BASE_URL.rstrip("/") + path


def register(email: str, password: str) -> dict:
    r = requests.post(_url("/auth/register"), json={"email": email, "password": password})
    return {"ok": r.status_code == 201, "data": r.json(), "status": r.status_code}


def login(email: str, password: str) -> dict:
    r = requests.post(_url("/auth/login"), json={"email": email, "password": password})
    return {"ok": r.status_code == 200, "data": r.json(), "status": r.status_code}


def get_me() -> dict:
    r = requests.get(_url("/auth/me"), headers=_headers())
    return {"ok": r.status_code == 200, "data": r.json()}


def get_balance() -> dict:
    r = requests.get(_url("/balance/"), headers=_headers())
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
