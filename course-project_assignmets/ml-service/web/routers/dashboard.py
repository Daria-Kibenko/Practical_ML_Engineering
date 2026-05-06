"""
Страницы личного кабинета — требуют авторизации.
  GET /dashboard    → кабинет (баланс + форма предсказания)
  GET /history      → история операций
  POST /deposit     → пополнение баланса
  POST /predict     → отправка ML-запроса
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
import api_client as api

bp = Blueprint("dashboard", __name__)

def _require_auth():
    if not session.get("token"):
        return redirect(url_for("auth.login"))

@bp.get("/dashboard")
def dashboard():
    if redir := _require_auth():
        return redir
    user = api.get_me()
    balance = api.get_balance()
    models = api.get_models()
    return render_template(
        "pages/dashboard.html",
        user=user["data"] if user["ok"] else {},
        balance=balance["data"] if balance["ok"] else {"amount": 0},
        models=models["data"] if models["ok"] else [],
    )

@bp.get("/history")
def history():
    if redir := _require_auth():
        return redir
    ml_history = api.get_ml_history()
    transactions = api.get_transactions()
    return render_template(
        "pages/history.html",
        ml_history=ml_history["data"] if ml_history["ok"] else [],
        transactions=transactions["data"] if transactions["ok"] else [],
    )

@bp.post("/deposit")
def deposit():
    if redir := _require_auth():
        return redir
    try:
        amount = float(request.form["amount"])
    except (ValueError, KeyError):
        flash("Введите корректную сумму", "error")
        return redirect(url_for("dashboard.dashboard"))
    result = api.deposit(amount)
    if result["ok"]:
        new_balance = result["data"]["amount"]
        flash(f"Баланс пополнен. Текущий баланс: {new_balance:.2f} кредитов", "success")
    else:
        detail = result["data"].get("detail", "Ошибка пополнения")
        flash(detail, "error")
    return redirect(url_for("dashboard.dashboard"))

@bp.post("/predict")
def predict():
    if redir := _require_auth():
        return redir
    model_id = int(request.form["model_id"])
    raw = request.form.get("input_data", "")
    input_data = {}
    parse_errors = []
    for line in raw.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        if ":" not in line:
            parse_errors.append(f"Неверный формат строки: «{line}»")
            continue
        key, _, value = line.partition(":")
        try:
            input_data[key.strip()] = float(value.strip())
        except ValueError:
            parse_errors.append(f"«{key.strip()}» — значение должно быть числом")
    if parse_errors:
        flash("Ошибки в данных: " + "; ".join(parse_errors), "error")
        return redirect(url_for("dashboard.dashboard"))
    if not input_data:
        flash("Введите хотя бы один числовой признак", "error")
        return redirect(url_for("dashboard.dashboard"))
    result = api.predict(model_id, input_data)
    if result.get("status") == 402:
        flash("Недостаточно кредитов для выполнения запроса", "error")
        return redirect(url_for("dashboard.dashboard"))
    if not result["ok"]:
        detail = result["data"].get("detail", "Ошибка выполнения запроса")
        flash(detail, "error")
        return redirect(url_for("dashboard.dashboard"))
    return render_template("pages/result.html", result=result["data"])