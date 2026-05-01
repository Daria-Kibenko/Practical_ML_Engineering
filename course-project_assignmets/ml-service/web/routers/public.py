"""
Публичные страницы — доступны без авторизации.
  GET /          → главная (guest или user — решает JS)
  GET /about     → описание сервиса
"""

from flask import Blueprint, render_template

bp = Blueprint("public", __name__)


@bp.get("/")
def index():
    """
    Отдаём пустой index.html с навигацией.
    JS проверяет localStorage на наличие токена и решает:
      - токен есть  → загружает pages/dashboard.html
      - токена нет  → загружает pages/landing.html
    """
    return render_template("index.html")


@bp.get("/about")
def about():
    return render_template("pages/about.html")
