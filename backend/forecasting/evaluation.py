"""Classification metrics for directional forecasting.

Replaces the old RMSE/MAE/MAPE suite — price-error metrics are statistically
misleading for stocks (arXiv 2101.10942) and can't represent the directional
signal investors actually care about.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ClassificationMetrics:
    accuracy: float    # fraction of correct direction calls
    precision: float   # of predicted "up", fraction that were actually up
    recall: float      # of actual "up" days, fraction the model caught
    n_samples: int

    def __str__(self) -> str:
        return (
            f"accuracy={self.accuracy:.3f} precision={self.precision:.3f} "
            f"recall={self.recall:.3f} n={self.n_samples}"
        )


def _validate(y_true: Sequence[int], y_pred: Sequence[int]) -> tuple[np.ndarray, np.ndarray]:
    a = np.asarray(y_true, dtype=int)
    b = np.asarray(y_pred, dtype=int)
    if a.shape != b.shape:
        raise ValueError(f"length mismatch: y_true={a.shape} y_pred={b.shape}")
    if a.size == 0:
        raise ValueError("cannot compute metrics on empty input")
    return a, b


def accuracy(y_true: Sequence[int], y_pred: Sequence[int]) -> float:
    a, b = _validate(y_true, y_pred)
    return float(np.mean(a == b))


def precision_recall(
    y_true: Sequence[int], y_pred: Sequence[int]
) -> tuple[float, float]:
    """Precision and recall for the positive (up) class."""
    a, b = _validate(y_true, y_pred)
    tp = int(np.sum((b == 1) & (a == 1)))
    fp = int(np.sum((b == 1) & (a == 0)))
    fn = int(np.sum((b == 0) & (a == 1)))
    prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    return prec, rec


def evaluate(y_true: Sequence[int], y_pred: Sequence[int]) -> ClassificationMetrics:
    a, b = _validate(y_true, y_pred)
    prec, rec = precision_recall(a, b)
    return ClassificationMetrics(
        accuracy=accuracy(a, b),
        precision=prec,
        recall=rec,
        n_samples=len(a),
    )
