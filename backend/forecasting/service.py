"""Forecasting business logic (Service layer).

Orchestrates: validate symbol -> load history -> fit model -> predict -> persist.
Synchronous by design for Phase 2 (ADR-0009): training runs on the request path;
background execution is a deliberate future deferral. Depends on the
``Forecaster`` abstraction, so the model is injected (Dependency Inversion).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from core.validation import normalize_symbol
from forecasting.models.base import Forecaster
from forecasting.repository import ForecastRepository
from market_data.repository import StockRepository
from models.forecast import Forecast

logger = logging.getLogger(__name__)

# Default prediction horizons in days (per docs/ML_Design.md: 1 / 7 / 30 day).
DEFAULT_HORIZONS = [1, 7, 30]


class UnknownStockError(Exception):
    """Raised when a (valid) symbol has no ingested stock/history to forecast."""


@dataclass
class ForecastResult:
    symbol: str
    model: str
    forecast_date: date
    forecasts: list[Forecast]


class ForecastingService:
    """Generates and persists forecasts for a single stock."""

    def __init__(self, db: Session, forecaster: Forecaster | None = None) -> None:
        # forecaster is required by generate() but not by latest() (reads only),
        # so it is optional to let read paths skip model construction.
        self.db = db
        self.forecaster = forecaster
        self.repo = ForecastRepository(db)
        self.stocks = StockRepository(db)

    def generate(self, symbol: str, horizons: list[int] | None = None) -> ForecastResult:
        """Fit the injected model on a stock's history and persist its predictions.

        The symbol is validated *before* any work (Phase 1.5 contract). Raises
        ``UnknownStockError`` if the stock or its price history is missing.
        """
        if self.forecaster is None:
            raise ValueError("a forecaster is required to generate forecasts")
        symbol = normalize_symbol(symbol)
        horizons = horizons or DEFAULT_HORIZONS

        stock = self.stocks.get_by_symbol(symbol)
        if stock is None:
            raise UnknownStockError(f"Stock {symbol!r} has not been ingested")

        prices = self.repo.load_price_frame(stock.id)
        if prices.empty:
            raise UnknownStockError(f"Stock {symbol!r} has no price history to forecast")

        logger.info(
            "Forecasting %s with %s over horizons %s (%d rows)",
            symbol,
            self.forecaster.name,
            horizons,
            len(prices),
        )
        predictions = self.forecaster.predict(prices, horizons)

        run_date = date.today()
        created = self.repo.replace_forecasts(
            stock.id, self.forecaster.name, run_date, predictions
        )
        self.db.commit()
        return ForecastResult(
            symbol=symbol, model=self.forecaster.name, forecast_date=run_date, forecasts=created
        )

    def latest(self, symbol: str, model: str | None = None) -> list[Forecast]:
        """Read the most recent stored forecasts for a stock."""
        symbol = normalize_symbol(symbol)
        stock = self.stocks.get_by_symbol(symbol)
        if stock is None:
            raise UnknownStockError(f"Stock {symbol!r} has not been ingested")
        return self.repo.latest_for_stock(stock.id, model)
