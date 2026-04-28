"""
MLEngine — загрузка и вызов реальных ML-моделей.

Три модели, обученные на настоящих датасетах sklearn:

  "Classifier v1"    → GradientBoostingClassifier
                        Датасет: Breast Cancer Wisconsin (569 образцов, 30 признаков)
                        Задача:  бинарная классификация опухоли (malignant / benign)
                        Метрики: accuracy=0.9474, AUC=0.9864

  "Regressor v1"     → RandomForestRegressor
                        Датасет: Diabetes (442 образца, 10 признаков)
                        Задача:  предсказание прогрессии диабета через 1 год (25–346)
                        Метрики: MAE=43.88

  "Anomaly Detector" → IsolationForest
                        Датасет: Breast Cancer (обучен на benign-образцах)
                        Задача:  обнаружение аномальных клеточных параметров
                        Метрики: malignant recall=0.83

Модели обучаются при первом старте (если .joblib-файлы не найдены)
и кешируются в памяти процесса при последующих вызовах.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

import joblib
import numpy as np

logger = logging.getLogger(__name__)

# Пути к файлам моделей
_MODELS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ml_models")
_MODELS_DIR = os.path.normpath(_MODELS_DIR)

CLASSIFIER_PATH = os.path.join(_MODELS_DIR, "classifier_v1.joblib")
REGRESSOR_PATH  = os.path.join(_MODELS_DIR, "regressor_v1.joblib")
ANOMALY_PATH    = os.path.join(_MODELS_DIR, "anomaly_detector.joblib")
METADATA_PATH   = os.path.join(_MODELS_DIR, "metadata.joblib")

# Признаки каждой модели (порядок важен для numpy-массива)
_CLASSIFIER_FEATURES = [
    "mean radius", "mean texture", "mean perimeter", "mean area", "mean smoothness",
    "mean compactness", "mean concavity", "mean concave points", "mean symmetry",
    "mean fractal dimension", "radius error", "texture error", "perimeter error",
    "area error", "smoothness error", "compactness error", "concavity error",
    "concave points error", "symmetry error", "fractal dimension error",
    "worst radius", "worst texture", "worst perimeter", "worst area", "worst smoothness",
    "worst compactness", "worst concavity", "worst concave points", "worst symmetry",
    "worst fractal dimension",
]

_REGRESSOR_FEATURES = ["age", "sex", "bmi", "bp", "s1", "s2", "s3", "s4", "s5", "s6"]

_ANOMALY_FEATURES = _CLASSIFIER_FEATURES  # тот же датасет


# Утилита: выровнять входной словарь под нужный порядок признаков
def _align(input_data: Dict[str, float], feature_names: list) -> np.ndarray:
    """
    Собирает вектор признаков в правильном порядке.
    Отсутствующие признаки заполняются 0.0 (среднее по стандартизированным данным).
    """
    return np.array(
        [float(input_data.get(f, 0.0)) for f in feature_names],
        dtype=np.float64,
    ).reshape(1, -1)


# Реестр моделей (ленивая загрузка + кеш в памяти)
class _ModelRegistry:

    def __init__(self) -> None:
        self._classifier = None
        self._regressor  = None
        self._anomaly_detector = None
        self._anomaly_scaler   = None
        self._metadata: Optional[dict] = None

    def _ensure_trained(self) -> None:
        """Обучить и сохранить модели если файлов ещё нет."""
        if not os.path.exists(CLASSIFIER_PATH):
            logger.info("Файлы моделей не найдены — запускаю обучение...")
            from src.ml_models.train_and_save import train_all
            train_all()

    def _load_classifier(self):
        if self._classifier is None:
            self._ensure_trained()
            self._classifier = joblib.load(CLASSIFIER_PATH)
            logger.info("Classifier v1 загружен из %s", CLASSIFIER_PATH)
        return self._classifier

    def _load_regressor(self):
        if self._regressor is None:
            self._ensure_trained()
            self._regressor = joblib.load(REGRESSOR_PATH)
            logger.info("Regressor v1 загружен из %s", REGRESSOR_PATH)
        return self._regressor

    def _load_anomaly(self):
        if self._anomaly_detector is None:
            self._ensure_trained()
            bundle = joblib.load(ANOMALY_PATH)
            self._anomaly_detector = bundle["detector"]
            self._anomaly_scaler   = bundle["scaler"]
            logger.info("Anomaly Detector загружен из %s", ANOMALY_PATH)
        return self._anomaly_detector, self._anomaly_scaler

    # Предсказания
    def predict_classifier(self, input_data: Dict[str, float]) -> Dict[str, Any]:
        model = self._load_classifier()
        X = _align(input_data, _CLASSIFIER_FEATURES)

        label = int(model.predict(X)[0])
        proba = model.predict_proba(X)[0]
        class_name = "benign" if label == 1 else "malignant"

        return {
            "model": "Classifier v1",
            "algorithm": "GradientBoostingClassifier",
            "dataset": "Breast Cancer Wisconsin",
            "prediction": class_name,
            "label": label,
            "confidence": round(float(proba[label]), 4),
            "probabilities": {
                "malignant": round(float(proba[0]), 4),
                "benign":    round(float(proba[1]), 4),
            },
            "features_received": list(input_data.keys()),
            "features_imputed":  [f for f in _CLASSIFIER_FEATURES if f not in input_data],
        }

    def predict_regressor(self, input_data: Dict[str, float]) -> Dict[str, Any]:
        model = self._load_regressor()
        X = _align(input_data, _REGRESSOR_FEATURES)
        value = float(model.predict(X)[0])

        return {
            "model": "Regressor v1",
            "algorithm": "RandomForestRegressor",
            "dataset": "Diabetes",
            "prediction": round(value, 2),
            "unit": "disease progression score (25–346)",
            "features_received": list(input_data.keys()),
            "features_imputed":  [f for f in _REGRESSOR_FEATURES if f not in input_data],
        }

    def predict_anomaly(self, input_data: Dict[str, float]) -> Dict[str, Any]:
        detector, scaler = self._load_anomaly()
        X = _align(input_data, _ANOMALY_FEATURES)
        X_scaled = scaler.transform(X)

        label = int(detector.predict(X_scaled)[0])   # -1=anomaly, 1=normal
        raw_score = float(detector.score_samples(X_scaled)[0])
        # Нормализуем в [0,1]: 1 = явная аномалия
        anomaly_score = round(max(0.0, min(1.0, (-raw_score - 0.3) / 0.7)), 4)

        return {
            "model": "Anomaly Detector",
            "algorithm": "IsolationForest",
            "dataset": "Breast Cancer Wisconsin (trained on benign)",
            "prediction": "anomaly" if label == -1 else "normal",
            "is_anomaly": label == -1,
            "anomaly_score": anomaly_score,
            "raw_score": round(raw_score, 4),
            "features_received": list(input_data.keys()),
            "features_imputed":  [f for f in _ANOMALY_FEATURES if f not in input_data],
        }


# Синглтон
_registry = _ModelRegistry()


# Публичный интерфейс
def run_prediction(model_name: str, input_data: Dict[str, float]) -> Dict[str, Any]:
    """
    Выполнить предсказание реальной ML-моделью.
    Маршрутизация по имени модели (как в таблице ml_models).
    """
    name_lower = model_name.lower()

    if "classifier" in name_lower:
        return _registry.predict_classifier(input_data)
    elif "regressor" in name_lower or "regression" in name_lower:
        return _registry.predict_regressor(input_data)
    elif "anomaly" in name_lower:
        return _registry.predict_anomaly(input_data)
    else:
        logger.warning("Неизвестная модель '%s', используем Classifier", model_name)
        result = _registry.predict_classifier(input_data)
        result["warning"] = f"Модель '{model_name}' не найдена, использован Classifier v1"
        return result


def get_model_metadata() -> dict:
    """Вернуть метаданные всех обученных моделей (датасет, метрики, признаки)."""
    if os.path.exists(METADATA_PATH):
        return joblib.load(METADATA_PATH)
    return {}
