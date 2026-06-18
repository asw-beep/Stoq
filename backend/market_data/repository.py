"""Data-access layer for stocks and historical prices (Repository Pattern)."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from market_data.provider import PriceBar, StockInfo
from models.stock import HistoricalPrice, Stock


class StockRepository:
    """Encapsulates all DB access for Stock / HistoricalPrice."""

    def __init__(self, db: Session) -> None:
        self.db = db

    # ---- stocks ----
    def list_stocks(self, limit: int | None = None, offset: int = 0) -> list[Stock]:
        stmt = select(Stock).order_by(Stock.symbol).offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)
        return list(self.db.scalars(stmt))

    def count_stocks(self) -> int:
        return self.db.scalar(select(func.count()).select_from(Stock)) or 0

    def get_by_symbol(self, symbol: str) -> Stock | None:
        return self.db.scalar(select(Stock).where(Stock.symbol == symbol.upper()))

    def upsert_stock(self, info: StockInfo) -> Stock:
        stock = self.get_by_symbol(info.symbol)
        if stock is None:
            stock = Stock(symbol=info.symbol, name=info.name, sector=info.sector)
            self.db.add(stock)
            self.db.flush()
        else:
            stock.name = info.name or stock.name
            stock.sector = info.sector or stock.sector
        return stock

    # ---- prices ----
    def bulk_upsert_prices(self, stock_id: int, bars: list[PriceBar]) -> int:
        """Insert price bars, ignoring duplicates on (stock_id, date). Returns rows sent."""
        if not bars:
            return 0
        rows = [
            {
                "stock_id": stock_id,
                "date": b.date,
                "open": b.open,
                "high": b.high,
                "low": b.low,
                "close": b.close,
                "volume": b.volume,
            }
            for b in bars
        ]
        stmt = pg_insert(HistoricalPrice).values(rows)
        stmt = stmt.on_conflict_do_nothing(constraint="uq_price_stock_date")
        self.db.execute(stmt)
        return len(rows)

    def price_count(self, stock_id: int) -> int:
        return self.db.scalar(
            select(func.count())
            .select_from(HistoricalPrice)
            .where(HistoricalPrice.stock_id == stock_id)
        ) or 0
