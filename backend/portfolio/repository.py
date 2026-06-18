"""Data-access layer for Portfolio and Holding (Repository Pattern)."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from models.portfolio import Holding, Portfolio
from models.stock import HistoricalPrice, Stock


class PortfolioRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ---- portfolios ----

    def create(self, user_id: int, name: str) -> Portfolio:
        portfolio = Portfolio(user_id=user_id, name=name)
        self.db.add(portfolio)
        self.db.flush()
        return portfolio

    def list_for_user(
        self, user_id: int, limit: int | None = None, offset: int = 0
    ) -> list[Portfolio]:
        stmt = (
            select(Portfolio)
            .where(Portfolio.user_id == user_id)
            .order_by(Portfolio.id)
            .offset(offset)
            .options(selectinload(Portfolio.holdings).selectinload(Holding.stock))
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        return list(self.db.scalars(stmt))

    def count_for_user(self, user_id: int) -> int:
        return (
            self.db.scalar(
                select(func.count())
                .select_from(Portfolio)
                .where(Portfolio.user_id == user_id)
            )
            or 0
        )

    def get(self, portfolio_id: int) -> Portfolio | None:
        return self.db.scalar(
            select(Portfolio)
            .where(Portfolio.id == portfolio_id)
            .options(selectinload(Portfolio.holdings).selectinload(Holding.stock))
        )

    def delete(self, portfolio: Portfolio) -> None:
        self.db.delete(portfolio)
        self.db.flush()

    # ---- holdings ----

    def add_holding(
        self,
        portfolio_id: int,
        stock_id: int,
        shares: float,
        purchase_price: float,
    ) -> Holding:
        holding = Holding(
            portfolio_id=portfolio_id,
            stock_id=stock_id,
            shares=shares,
            purchase_price=purchase_price,
        )
        self.db.add(holding)
        self.db.flush()
        self.db.refresh(holding)
        return holding

    def get_holding(self, holding_id: int) -> Holding | None:
        return self.db.scalar(select(Holding).where(Holding.id == holding_id))

    def delete_holding(self, holding: Holding) -> None:
        self.db.delete(holding)
        self.db.flush()

    # ---- pricing ----

    def latest_close(self, stock_id: int) -> float | None:
        """Most recent closing price for a stock from historical data."""
        row = self.db.scalar(
            select(HistoricalPrice.close)
            .where(HistoricalPrice.stock_id == stock_id)
            .order_by(HistoricalPrice.date.desc())
            .limit(1)
        )
        return float(row) if row is not None else None

    def get_stock_by_symbol(self, symbol: str) -> Stock | None:
        return self.db.scalar(select(Stock).where(Stock.symbol == symbol.upper()))
