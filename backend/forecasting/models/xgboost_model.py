"""XGBoost feature-based forecaster.

Implements the ``Forecaster`` Protocol using the engineered indicators from
``features.py``. Uses a **direct multi-step** strategy: for each horizon ``h`` a
separate regressor is trained to map today's features to the close price ``h``
trading days ahead, then predicts from the latest feature row.

xgboost is imported lazily inside ``predict`` (matching ``ProphetForecaster``) so
the package imports and the stubbed test suite run without the heavy wheel.
"""

from __future__ import annotations

from datetime import timedelta

import pandas as pd

from forecasting.features import build_feature_frame
from forecasting.models.base import Prediction

# Feature columns fed to the model (per docs/ML_Design.md: price, volume, indicators).
_FEATURE_COLS = [
    "close",
    "volume",
    "sma_20",
    "ema_20",
    "rsi_14",
    "macd",
    "macd_signal",
    "macd_hist",
    "volatility_20",
]
# Indicators need ~33 rows to warm up; require comfortably more so each horizon
# still has training rows after the target shift.
_MIN_ROWS = 60


class XGBoostForecaster:
    """Gradient-boosted regression over technical features."""

    name = "xgboost"

    def __init__(
        self,
        n_estimators: int = 200,
        max_depth: int = 4,
        learning_rate: float = 0.05,
    ) -> None:
        self.params = {
            "n_estimators": n_estimators,
            "max_depth": max_depth,
            "learning_rate": learning_rate,
            "objective": "reg:squarederror",
        }

    def predict(self, prices: pd.DataFrame, horizons: list[int]) -> list[Prediction]:
        if "close" not in prices.columns:
            raise ValueError("price frame must contain a 'close' column")
        if len(prices) < _MIN_ROWS:
            raise ValueError(f"need at least {_MIN_ROWS} rows of history, got {len(prices)}")
        if not horizons:
            return []

        from xgboost import XGBRegressor

        feats = build_feature_frame(prices)
        feature_rows = feats[_FEATURE_COLS].dropna()
        if feature_rows.empty:
            raise ValueError("not enough history to compute features")
        latest = feature_rows.iloc[[-1]]  # most recent fully-warmed feature row

        last_date = pd.Timestamp(prices.index[-1]).date()
        results: list[Prediction] = []
        for h in horizons:
            # Target = close price h steps ahead, aligned to feature rows.
            target = feats["close"].shift(-h)
            train = feats[_FEATURE_COLS].join(target.rename("_y")).dropna()
            if train.empty:
                raise ValueError(f"not enough history to train horizon {h}")

            model = XGBRegressor(**self.params)
            model.fit(train[_FEATURE_COLS], train["_y"])
            pred = float(model.predict(latest)[0])
            # XGBoost regression yields a point estimate, no native interval.
            results.append(
                Prediction(
                    target_date=last_date + timedelta(days=h),
                    predicted_price=pred,
                    confidence=None,
                )
            )
        return results
