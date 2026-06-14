"""Forecast evaluation metrics (per docs/ML_Design.md): RMSE, MAE, MAPE.

Pure functions over array-likes of equal length. Kept dependency-light (numpy
only) and model-agnostic so any forecaster can be backtested the same way.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Metrics:
    rmse: float
    mae: float
    mape: float


def _as_pair(y_true: Sequence[float], y_pred: Sequence[float]) -> tuple[np.ndarray, np.ndarray]:
    a = np.asarray(y_true, dtype=float)
    b = np.asarray(y_pred, dtype=float)
    if a.shape != b.shape:
        raise ValueError(f"length mismatch: y_true={a.shape} y_pred={b.shape}")
    if a.size == 0:
        raise ValueError("cannot compute metrics on empty input")
    return a, b


def rmse(y_true: Sequence[float], y_pred: Sequence[float]) -> float:
    a, b = _as_pair(y_true, y_pred)
    return float(np.sqrt(np.mean((a - b) ** 2)))


def mae(y_true: Sequence[float], y_pred: Sequence[float]) -> float:
    a, b = _as_pair(y_true, y_pred)
    return float(np.mean(np.abs(a - b)))


def mape(y_true: Sequence[float], y_pred: Sequence[float]) -> float:
    """Mean absolute percentage error (%). Ignores points where y_true == 0."""
    a, b = _as_pair(y_true, y_pred)
    mask = a != 0
    if not mask.any():
        raise ValueError("MAPE undefined: all true values are zero")
    return float(np.mean(np.abs((a[mask] - b[mask]) / a[mask])) * 100.0)


def evaluate(y_true: Sequence[float], y_pred: Sequence[float]) -> Metrics:
    """Compute all three metrics at once."""
    return Metrics(rmse=rmse(y_true, y_pred), mae=mae(y_true, y_pred), mape=mape(y_true, y_pred))
