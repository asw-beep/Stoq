"""ForecastingService tests using a stub Forecaster (no heavy training)."""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import pytest

from forecasting.models.base import Prediction
from forecasting.repository import ForecastRepository
from forecasting.service import ForecastingService, UnknownStockError


class StubForecaster:
    """Deterministic Forecaster: predicts a flat price per horizon."""

    name = "stub"

    def __init__(self) -> None:
        self.seen_rows = 0

    def predict(self, prices: pd.DataFrame, horizons: list[int]) -> list[Prediction]:
        self.seen_rows = len(prices)
        last = pd.Timestamp(prices.index[-1]).date()
        return [
            Prediction(target_date=last + timedelta(days=h), predicted_price=42.0, confidence=0.9)
            for h in horizons
        ]


def test_generate_persists_predictions(db_session, seed_stock):
    seed_stock("AAPL", days=40)
    forecaster = StubForecaster()
    service = ForecastingService(db_session, forecaster)

    result = service.generate("aapl", horizons=[1, 7, 30])

    assert result.symbol == "AAPL"
    assert result.model == "stub"
    assert result.forecast_date == date.today()
    assert len(result.forecasts) == 3
    assert forecaster.seen_rows == 40
    assert {f.target_date for f in result.forecasts}  # distinct target dates
    assert all(float(f.predicted_price) == 42.0 for f in result.forecasts)


def test_generate_unknown_symbol_raises(db_session):
    service = ForecastingService(db_session, StubForecaster())
    with pytest.raises(UnknownStockError):
        service.generate("MSFT")


def test_generate_rerun_replaces_same_day(db_session, seed_stock):
    seed_stock("AAPL", days=40)
    service = ForecastingService(db_session, StubForecaster())

    service.generate("AAPL", horizons=[1, 7])
    service.generate("AAPL", horizons=[1, 7, 30])  # same day, more horizons

    rows = service.latest("AAPL")
    assert len(rows) == 3  # replaced, not appended (no duplicate-day rows)


def test_latest_returns_most_recent_run(db_session, seed_stock):
    stock = seed_stock("AAPL", days=40)
    repo = ForecastRepository(db_session)
    # Older run (yesterday) and newer run (today).
    repo.replace_forecasts(
        stock.id, "stub", date.today() - timedelta(days=1),
        [Prediction(date.today(), 1.0, None)],
    )
    repo.replace_forecasts(
        stock.id, "stub", date.today(),
        [Prediction(date.today() + timedelta(days=1), 2.0, None)],
    )
    db_session.commit()

    rows = ForecastingService(db_session, StubForecaster()).latest("AAPL")
    assert len(rows) == 1
    assert float(rows[0].predicted_price) == 2.0
