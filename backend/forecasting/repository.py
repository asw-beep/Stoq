"""Data-access layer for forecasts (Repository Pattern).

Mirrors ``StockRepository``. Persistence uses a dialect-agnostic
delete-then-insert so the same code runs on Postgres (production) and SQLite
(tests) — the ``uq_forecast_stock_model_dates`` constraint still guards
integrity, and re-running a model for a given day cleanly replaces its rows.
"""

from __future__ import annotations

from datetime import date as date_type

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from forecasting.models.base import Prediction
from models.forecast import Forecast
from models.stock import HistoricalPrice


class ForecastRepository:
    """Encapsulates DB access for Forecast rows and the price history they read."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def load_price_frame(self, stock_id: int) -> pd.DataFrame:
        """Return a date-indexed OHLCV frame for a stock, oldest first.

        Empty frame (with the expected columns) when the stock has no history.
        """
        rows = self.db.scalars(
            select(HistoricalPrice)
            .where(HistoricalPrice.stock_id == stock_id)
            .order_by(HistoricalPrice.date)
        ).all()
        frame = pd.DataFrame(
            [
                {
                    "date": r.date,
                    "open": float(r.open),
                    "high": float(r.high),
                    "low": float(r.low),
                    "close": float(r.close),
                    "volume": int(r.volume),
                }
                for r in rows
            ],
            columns=["date", "open", "high", "low", "close", "volume"],
        )
        return frame.set_index("date")

    def replace_forecasts(
        self,
        stock_id: int,
        model: str,
        forecast_date: date_type,
        predictions: list[Prediction],
    ) -> list[Forecast]:
        """Replace this model's predictions for the given run date and persist."""
        self.db.query(Forecast).filter(
            Forecast.stock_id == stock_id,
            Forecast.model == model,
            Forecast.forecast_date == forecast_date,
        ).delete(synchronize_session=False)

        created = [
            Forecast(
                stock_id=stock_id,
                forecast_date=forecast_date,
                target_date=p.target_date,
                model=model,
                predicted_price=p.predicted_price,
                confidence=p.confidence,
            )
            for p in predictions
        ]
        self.db.add_all(created)
        self.db.flush()
        return created

    def latest_for_stock(self, stock_id: int, model: str | None = None) -> list[Forecast]:
        """Forecasts from the most recent run date for a stock (optionally one model)."""
        latest_q = select(Forecast.forecast_date).where(Forecast.stock_id == stock_id)
        if model is not None:
            latest_q = latest_q.where(Forecast.model == model)
        latest_date = self.db.scalar(latest_q.order_by(Forecast.forecast_date.desc()).limit(1))
        if latest_date is None:
            return []

        q = select(Forecast).where(
            Forecast.stock_id == stock_id, Forecast.forecast_date == latest_date
        )
        if model is not None:
            q = q.where(Forecast.model == model)
        return list(self.db.scalars(q.order_by(Forecast.target_date)))
