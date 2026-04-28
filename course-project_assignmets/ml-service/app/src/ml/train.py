"""
Скрипт обучения ML-моделей.

Обучает три реальных модели на синтетических данных и сохраняет в models/.
Запускается один раз при старте приложения (если файлы ещё не существуют).

Модели:
  Classifier v1   — LogisticRegression (бинарная классификация)
  Regressor v1    — Ridge (регрессия числового значения)
  Anomaly Detector — IsolationForest (обнаружение аномалий)
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

logger = logging.getLogger(__name__)

MODELS_DIR = Path(__file__).parent / "saved_models"


def _models_exist() -> bool:
    return (
        (MODELS_DIR / "classifier_v1.pkl").exists()
        and (MODELS_DIR / "regressor_v1.pkl").exists()
        and (MODELS_DIR / "anomaly_detector.pkl").exists()
    )


def train_and_save() -> None:
    """Обучить все модели и сохранить .pkl файлы. Идемпотентно."""
    if _models_exist():
        logger.info("ML-модели уже обучены, пропускаем")
        return

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(42)

    # 1. Classifier v1 — LogisticRegression
    #    Данные: 4 числовых признака, бинарный класс (0/1)
    #    Позитивный класс: сумма признаков > 0
    logger.info("Обучаю Classifier v1...")
    n = 1000
    X_clf = rng.standard_normal((n, 4))
    y_clf = (X_clf.sum(axis=1) > 0).astype(int)

    clf_pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("model", LogisticRegression(max_iter=1000, random_state=42)),
    ])
    clf_pipeline.fit(X_clf, y_clf)
    joblib.dump(clf_pipeline, MODELS_DIR / "classifier_v1.pkl")
    logger.info("Classifier v1 сохранён (accuracy ~%.2f)", clf_pipeline.score(X_clf, y_clf))

    # 2. Regressor v1 — Ridge Regression
    #    Данные: 4 числовых признака, таргет = взвешенная сумма + шум
    logger.info("Обучаю Regressor v1...")
    X_reg = rng.standard_normal((n, 4))
    weights = np.array([1.5, -0.5, 2.0, 0.8])
    y_reg = X_reg @ weights + rng.normal(0, 0.5, n)

    reg_pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("model", Ridge(alpha=1.0)),
    ])
    reg_pipeline.fit(X_reg, y_reg)
    joblib.dump(reg_pipeline, MODELS_DIR / "regressor_v1.pkl")
    logger.info("Regressor v1 сохранён (R²=%.2f)", reg_pipeline.score(X_reg, y_reg))

    # 3. Anomaly Detector — IsolationForest
    #    Данные: нормальные наблюдения; аномалии — выбросы за 3σ
    logger.info("Обучаю Anomaly Detector...")
    X_normal = rng.standard_normal((n, 4))  # обучаем только на нормальных

    anomaly_pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("model", IsolationForest(
            n_estimators=100,
            contamination=0.05,  # ожидаем ~5% аномалий
            random_state=42,
        )),
    ])
    anomaly_pipeline.fit(X_normal)
    joblib.dump(anomaly_pipeline, MODELS_DIR / "anomaly_detector.pkl")
    logger.info("Anomaly Detector сохранён")

    logger.info("Все модели успешно обучены и сохранены в %s", MODELS_DIR)
