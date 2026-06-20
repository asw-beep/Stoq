"""XGBoost directional classifier.

Predicts whether the close price will be higher or lower h days from now
(direction: 1 = up, 0 = down). Uses a direct multi-horizon strategy: one
classifier per horizon, each trained independently.

Walk-forward validation (TimeSeriesSplit) is run before the final model to
give an honest estimate of directional accuracy — never shuffled, never leaking
future data into training windows.
"""

from __future__ import annotations

import logging
from datetime import timedelta

import numpy as np
import pandas as pd

from forecasting.evaluation import evaluate
from forecasting.features import build_feature_frame
from forecasting.models.base import Prediction

logger = logging.getLogger(__name__)

_FEATURE_COLS = [
    "close",
    "volume",
    "return_1d",
    "return_5d",
    "return_10d",
    "sma_20",
    "ema_20",
    "rsi_14",
    "macd",
    "macd_signal",
    "macd_hist",
    "volatility_20",
    "volume_zscore",
    "close_to_sma20",
]

# Need enough history to warm up all indicators (≥33 rows) plus room for
# walk-forward splits and the longest horizon shift.
_MIN_ROWS = 120


class XGBoostForecaster:
    """Gradient-boosted directional classifier."""

    name = "xgboost"

    def __init__(
        self,
        n_estimators: int = 200,
        max_depth: int = 4,
        learning_rate: float = 0.05,
        n_cv_splits: int = 5,
    ) -> None:
        self._params = {
            "n_estimators": n_estimators,
            "max_depth": max_depth,
            "learning_rate": learning_rate,
            "objective": "binary:logistic",
            "eval_metric": "logloss",
            "use_label_encoder": False,
        }
        self._n_cv_splits = n_cv_splits

    def predict(self, prices: pd.DataFrame, horizons: list[int]) -> list[Prediction]:
        if "close" not in prices.columns:
            raise ValueError("price frame must contain a 'close' column")
        if len(prices) < _MIN_ROWS:
            raise ValueError(
                f"need at least {_MIN_ROWS} rows of history, got {len(prices)}"
            )
        if not horizons:
            return []

        from sklearn.model_selection import TimeSeriesSplit
        from xgboost import XGBClassifier

        feats = build_feature_frame(prices)
        available = feats[_FEATURE_COLS].dropna()  # "close" already in _FEATURE_COLS
        if available.empty:
            raise ValueError("not enough history to compute features")

        latest_features = available[_FEATURE_COLS].iloc[[-1]]
        last_date = pd.Timestamp(prices.index[-1]).date()

        results: list[Prediction] = []
        for h in horizons:
            # Binary target: 1 if price is higher h days later, else 0
            target = (available["close"].shift(-h) > available["close"]).astype(int)
            dataset = pd.concat(
                [available[_FEATURE_COLS], target.rename("_y")], axis=1
            ).dropna()
            if len(dataset) < _MIN_ROWS // 2:
                raise ValueError(f"not enough history to train horizon {h}")

            X = dataset[_FEATURE_COLS].to_numpy()
            y = dataset["_y"].to_numpy()

            # Walk-forward validation — strict chronological order, no shuffle
            tscv = TimeSeriesSplit(n_splits=self._n_cv_splits)
            fold_preds, fold_true = [], []
            for train_idx, val_idx in tscv.split(X):
                m = XGBClassifier(**self._params)
                m.fit(X[train_idx], y[train_idx], verbose=False)
                fold_preds.extend(m.predict(X[val_idx]).tolist())
                fold_true.extend(y[val_idx].tolist())

            metrics = evaluate(fold_true, fold_preds)
            logger.info(
                "XGBoost horizon=%dd walk-forward: %s", h, metrics
            )

            # Final model trained on the full dataset
            final = XGBClassifier(**self._params)
            final.fit(X, y, verbose=False)
            proba = final.predict_proba(latest_features.to_numpy())[0]  # [p_down, p_up]
            direction = int(np.argmax(proba))
            probability = float(proba[direction])

            results.append(
                Prediction(
                    target_date=last_date + timedelta(days=h),
                    direction=direction,
                    probability=round(probability, 4),
                )
            )

        return results
