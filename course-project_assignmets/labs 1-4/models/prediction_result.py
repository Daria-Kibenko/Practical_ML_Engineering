from __future__ import annotations
from datetime import datetime
from typing import Optional


class PredictionResult:
    """Результат выполнения предсказания ML-модели."""

    def __init__(
        self,
        predicted_label: Optional[str],
        confidence: Optional[float],
        raw_output: dict,
    ) -> None:
        self._predicted_label: Optional[str] = predicted_label
        self._confidence: Optional[float] = confidence
        self._raw_output: dict = raw_output
        self._created_at: datetime = datetime.now()

    @property
    def predicted_label(self) -> Optional[str]:
        return self._predicted_label

    @property
    def confidence(self) -> Optional[float]:
        return self._confidence

    @property
    def raw_output(self) -> dict:
        return self._raw_output

    @property
    def created_at(self) -> datetime:
        return self._created_at

    def __repr__(self) -> str:
        return (
            f"PredictionResult(label={self._predicted_label!r}, "
            f"confidence={self._confidence})"
        )
