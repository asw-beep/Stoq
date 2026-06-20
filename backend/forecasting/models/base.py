"""Forecaster abstraction.

Every model implements ``Forecaster`` so the service depends on the abstraction,
not a concrete library (Dependency Inversion) — mirroring ``MarketDataProvider``.
Adding XGBoost later means a new implementation here only, no service change.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol, runtime_checkable

import pandas as pd


@dataclass(frozen=True)
class Prediction:
    """Directional forecast for a future target date.

    ``direction`` is 1 (price expected to rise) or 0 (expected to fall).
    ``probability`` is the model's confidence in that direction, in [0, 1].
    """

    target_date: date
    direction: int      # 1 = up, 0 = down
    probability: float  # confidence in the predicted direction


@runtime_checkable
class Forecaster(Protocol):
    """Interface every forecasting model must implement."""

    #: Stable identifier persisted on each Forecast row (e.g. "xgboost").
    name: str

    def predict(self, prices: pd.DataFrame, horizons: list[int]) -> list[Prediction]:
        """Fit on ``prices`` and predict direction ``h`` trading days ahead.

        ``prices`` is a date-indexed frame with at least a ``close`` column.
        ``horizons`` are day offsets (e.g. [1, 7, 30]). Returns one Prediction
        per requested horizon.
        """
        ...
