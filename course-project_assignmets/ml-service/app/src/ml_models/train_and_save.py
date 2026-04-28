"""
Скрипт обучения реальных ML-моделей на настоящих датасетах из sklearn.

Запускается один раз при первом старте приложения (или вручную).
Сохраняет обученные модели в /app/src/ml_models/*.joblib.

Датасеты:
  Classifier v1    → Breast Cancer Wisconsin (569 образцов, 30 признаков)
                     Задача: бинарная классификация опухоли (злокачественная/доброкачественная)
  Regressor v1     → Diabetes (442 образца, 10 признаков)
                     Задача: предсказание прогрессии диабета через год
  Anomaly Detector → Breast Cancer (нормальные = benign, аномалии = malignant)
                     Задача: обнаружение аномальных клеточных параметров
"""

import logging
import os

import joblib
import numpy as np
from sklearn.datasets import load_breast_cancer, load_diabetes
from sklearn.ensemble import GradientBoostingClassifier, IsolationForest, RandomForestRegressor
from sklearn.metrics import accuracy_score, mean_absolute_error, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

MODELS_DIR = os.path.dirname(os.path.abspath(__file__))

CLASSIFIER_PATH     = os.path.join(MODELS_DIR, "classifier_v1.joblib")
REGRESSOR_PATH      = os.path.join(MODELS_DIR, "regressor_v1.joblib")
ANOMALY_PATH        = os.path.join(MODELS_DIR, "anomaly_detector.joblib")
METADATA_PATH       = os.path.join(MODELS_DIR, "metadata.joblib")


def train_classifier() -> Pipeline:
    """
    GradientBoostingClassifier на датасете Breast Cancer Wisconsin.
    Признаки: mean radius, mean texture, mean perimeter, mean area, ...
    Классы: 0=malignant (злокачественная), 1=benign (доброкачественная)
    """
    data = load_breast_cancer()
    X, y = data.data, data.target

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("model", GradientBoostingClassifier(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=4,
            random_state=42,
        )),
    ])
    pipe.fit(X_train, y_train)

    y_pred = pipe.predict(X_test)
    y_prob = pipe.predict_proba(X_test)[:, 1]
    acc = accuracy_score(y_test, y_pred)
    auc = roc_auc_score(y_test, y_prob)
    logger.info("Classifier v1 (Breast Cancer): accuracy=%.4f  AUC=%.4f", acc, auc)

    return pipe, {
        "dataset": "Breast Cancer Wisconsin",
        "n_samples": len(X),
        "n_features": X.shape[1],
        "feature_names": list(data.feature_names),
        "classes": {0: "malignant", 1: "benign"},
        "test_accuracy": round(acc, 4),
        "test_auc": round(auc, 4),
        "algorithm": "GradientBoostingClassifier",
        "expected_input": "30 числовых признаков клеток: mean radius, mean texture, mean perimeter, mean area, mean smoothness, ..."
    }


def train_regressor() -> Pipeline:
    """
    RandomForestRegressor на датасете Diabetes.
    Признаки: age, sex, bmi, bp, s1-s6 (стандартизированные)
    Цель: прогрессия диабета через 1 год (25–346)
    """
    data = load_diabetes()
    X, y = data.data, data.target

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("model", RandomForestRegressor(
            n_estimators=200,
            max_depth=8,
            min_samples_leaf=3,
            random_state=42,
        )),
    ])
    pipe.fit(X_train, y_train)

    y_pred = pipe.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    logger.info("Regressor v1 (Diabetes): MAE=%.4f", mae)

    return pipe, {
        "dataset": "Diabetes (sklearn)",
        "n_samples": len(X),
        "n_features": X.shape[1],
        "feature_names": list(data.feature_names),
        "target": "disease progression after 1 year (25-346)",
        "test_mae": round(mae, 4),
        "algorithm": "RandomForestRegressor",
        "expected_input": "10 признаков: age, sex, bmi, bp, s1, s2, s3, s4, s5, s6 (стандартизированные, ~[-0.2, 0.2])"
    }


def train_anomaly_detector() -> tuple:
    """
    IsolationForest обучается на нормальных образцах (benign).
    Аномалии — злокачественные клетки (malignant) из Breast Cancer датасета.
    """
    data = load_breast_cancer()
    X, y = data.data, data.target

    # Обучаем только на нормальных (benign=1)
    X_normal = X[y == 1]

    scaler = StandardScaler()
    X_normal_scaled = scaler.fit_transform(X_normal)

    detector = IsolationForest(
        n_estimators=200,
        contamination=0.05,
        random_state=42,
    )
    detector.fit(X_normal_scaled)

    # Оценка: аномалии должны детектироваться как malignant
    X_test_scaled = scaler.transform(X)
    preds = detector.predict(X_test_scaled)  # -1=anomaly, 1=normal
    detected_malignant = np.sum((preds == -1) & (y == 0))
    total_malignant = np.sum(y == 0)
    recall = detected_malignant / total_malignant
    logger.info("Anomaly Detector (Breast Cancer): malignant recall=%.4f", recall)

    return detector, scaler, {
        "dataset": "Breast Cancer Wisconsin (normal=benign)",
        "n_train_samples": len(X_normal),
        "n_features": X.shape[1],
        "feature_names": list(data.feature_names),
        "malignant_recall": round(recall, 4),
        "algorithm": "IsolationForest",
        "expected_input": "30 признаков клеток (те же что у Classifier v1)"
    }


def train_all(force: bool = False) -> dict:
    """
    Обучить все модели и сохранить на диск.
    Если модели уже существуют и force=False — пропускает обучение.
    """
    all_exist = all(os.path.exists(p) for p in [CLASSIFIER_PATH, REGRESSOR_PATH, ANOMALY_PATH])

    if all_exist and not force:
        logger.info("Модели уже обучены, загружаю из файлов (передайте force=True для переобучения)")
        return joblib.load(METADATA_PATH)

    logger.info("Начинаю обучение реальных ML-моделей...")

    clf, clf_meta = train_classifier()
    joblib.dump(clf, CLASSIFIER_PATH)

    reg, reg_meta = train_regressor()
    joblib.dump(reg, REGRESSOR_PATH)

    det, scaler, det_meta = train_anomaly_detector()
    joblib.dump({"detector": det, "scaler": scaler}, ANOMALY_PATH)

    metadata = {
        "Classifier v1":    clf_meta,
        "Regressor v1":     reg_meta,
        "Anomaly Detector": det_meta,
    }
    joblib.dump(metadata, METADATA_PATH)

    logger.info("Все модели обучены и сохранены в %s", MODELS_DIR)
    return metadata


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    meta = train_all(force=True)
    for name, m in meta.items():
        print(f"\n{name}:")
        for k, v in m.items():
            print(f"  {k}: {v}")
