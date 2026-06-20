"""Forecaster factory: resolve a model implementation by name.

Mirrors ``market_data.provider.get_provider`` — the single place that knows the
concrete model classes, so callers (the API dependency) depend only on the
``Forecaster`` abstraction.
"""

from __future__ import annotations

from forecasting.models.base import Forecaster

SUPPORTED_MODELS = ("xgboost",)


def build_forecaster(name: str = "xgboost") -> Forecaster:
    """Return a Forecaster for ``name``; raises ValueError if unknown."""
    if name == "xgboost":
        from forecasting.models.xgboost_model import XGBoostForecaster

        return XGBoostForecaster()
    raise ValueError(f"Unknown forecasting model: {name!r} (supported: {SUPPORTED_MODELS})")
