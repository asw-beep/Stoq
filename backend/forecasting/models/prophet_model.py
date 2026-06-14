"""Prophet trend forecaster.

Wraps Facebook Prophet behind the ``Forecaster`` Protocol. Prophet is imported
lazily inside ``predict`` (matching ``YFinanceProvider``'s lazy ``import yfinance``)
so the package imports — and the stubbed test suite runs — without the heavy
prophet/cmdstan wheels installed.
"""

from __future__ import annotations

from datetime import timedelta

import pandas as pd

from forecasting.models.base import Prediction

# Minimum history Prophet needs to fit a meaningful trend + seasonality.
_MIN_ROWS = 30


class ProphetForecaster:
    """Trend forecasting with Prophet; confidence derived from the yhat interval."""

    name = "prophet"

    def __init__(self, interval_width: float = 0.80) -> None:
        # Width of the uncertainty interval Prophet returns (yhat_lower/upper).
        self.interval_width = interval_width

    def predict(self, prices: pd.DataFrame, horizons: list[int]) -> list[Prediction]:
        if "close" not in prices.columns:
            raise ValueError("price frame must contain a 'close' column")
        if len(prices) < _MIN_ROWS:
            raise ValueError(f"need at least {_MIN_ROWS} rows of history, got {len(prices)}")
        if not horizons:
            return []

        from prophet import Prophet

        # Prophet expects columns ds (datetime) and y (value).
        df = pd.DataFrame(
            {"ds": pd.to_datetime(prices.index), "y": prices["close"].to_numpy(dtype=float)}
        )

        model = Prophet(interval_width=self.interval_width, daily_seasonality=False)
        model.fit(df)

        max_h = max(horizons)
        future = model.make_future_dataframe(periods=max_h, freq="D")
        forecast = model.predict(future).set_index("ds")

        last_date = df["ds"].iloc[-1]
        results: list[Prediction] = []
        for h in horizons:
            target_ts = last_date + timedelta(days=h)
            row = forecast.loc[target_ts]
            yhat = float(row["yhat"])
            results.append(
                Prediction(
                    target_date=target_ts.date(),
                    predicted_price=yhat,
                    confidence=_interval_to_confidence(
                        yhat, float(row["yhat_lower"]), float(row["yhat_upper"])
                    ),
                )
            )
        return results


def _interval_to_confidence(yhat: float, lower: float, upper: float) -> float | None:
    """Map a prediction interval to a 0..1 confidence: tighter interval -> higher.

    Uses relative interval width: confidence = 1 - (width / |yhat|), clamped to
    [0, 1]. Returns None when yhat is ~0 (ratio undefined).
    """
    if abs(yhat) < 1e-9:
        return None
    rel_width = (upper - lower) / abs(yhat)
    return max(0.0, min(1.0, 1.0 - rel_width))
