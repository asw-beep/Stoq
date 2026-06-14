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
    """One predicted price for a future target date.

    ``confidence`` is an optional model-supplied score in [0, 1] (e.g. derived
    from a prediction interval); ``None`` when the model does not provide one.
    """

    target_date: date
    predicted_price: float
    confidence: float | None = None


@runtime_checkable
class Forecaster(Protocol):
    """Interface every forecasting model must implement."""

    #: Stable identifier persisted on each Forecast row (e.g. "prophet").
    name: str

    def predict(self, prices: pd.DataFrame, horizons: list[int]) -> list[Prediction]:
        """Fit on ``prices`` and predict the close price ``h`` trading days ahead.

        ``prices`` is a date-indexed frame with at least a ``close`` column.
        ``horizons`` are day offsets (e.g. [1, 7, 30]). Returns one Prediction
        per requested horizon.
        """
        ...
