"""
Страницы аутентификации.
  GET/POST /login     → форма входа
  GET/POST /register  → форма регистрации
  GET      /logout    → сброс сессии
"""

import sys
from pathlib import Path

# Добавляем корневую папку проекта в путь поиска модулей
sys.path.append(str(Path(__file__).parent.parent))

from flask import Blueprint, render_template, request, redirect, url_for, session
import api_client as api   # ← теперь абсолютный импорт

bp = Blueprint("auth", __name__)

@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        result = api.login(request.form["email"], request.form["password"])
        if result["ok"]:
            session["token"] = result["data"]["access_token"]
            return redirect(url_for("public.index"))
        error = result["data"].get("detail", "Неверный email или пароль")
        return render_template("pages/login.html", error=error)
    return render_template("pages/login.html")


@bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        result = api.register(request.form["email"], request.form["password"])
        if result["ok"]:
            # После регистрации сразу логиним
            login_result = api.login(request.form["email"], request.form["password"])
            if login_result["ok"]:
                session["token"] = login_result["data"]["access_token"]
            return redirect(url_for("public.index"))
        status = result["status"]
        if status == 409:
            error = "Пользователь с таким email уже существует"
        elif status == 422:
            error = "Пароль должен быть не короче 6 символов"
        else:
            error = result["data"].get("detail", "Ошибка регистрации")
        return render_template("pages/register.html", error=error)
    return render_template("pages/register.html")


@bp.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("public.index"))
