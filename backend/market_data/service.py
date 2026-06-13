"""Business logic for ingesting market data (Service layer)."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy.orm import Session

from market_data.provider import MarketDataProvider
from market_data.repository import StockRepository

logger = logging.getLogger(__name__)


@dataclass
class IngestResult:
    symbol: str
    bars_ingested: int
    total_bars: int


class MarketDataService:
    """Orchestrates provider fetch -> repository persistence."""

    def __init__(self, db: Session, provider: MarketDataProvider) -> None:
        self.db = db
        self.provider = provider
        self.repo = StockRepository(db)

    def ingest_symbol(self, symbol: str, years: int) -> IngestResult:
        """Fetch and persist stock info + historical prices for one symbol."""
        symbol = symbol.upper()
        logger.info("Ingesting %s (%dy history)", symbol, years)

        info = self.provider.get_stock_info(symbol)
        stock = self.repo.upsert_stock(info)

        bars = self.provider.get_history(symbol, years)
        sent = self.repo.bulk_upsert_prices(stock.id, bars)
        self.db.commit()

        total = self.repo.price_count(stock.id)
        logger.info("Ingested %s: %d bars sent, %d total in db", symbol, sent, total)
        return IngestResult(symbol=symbol, bars_ingested=sent, total_bars=total)

    def ingest_many(self, symbols: list[str], years: int) -> list[IngestResult]:
        results: list[IngestResult] = []
        for sym in symbols:
            try:
                results.append(self.ingest_symbol(sym, years))
            except Exception:  # noqa: BLE001 - one bad symbol shouldn't abort the batch
                logger.exception("Failed to ingest %s", sym)
        return results
