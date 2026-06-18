"""Portfolio business logic (Service layer).

Enforces ownership: every mutating operation verifies the portfolio belongs to
the requesting user before proceeding.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from core.validation import normalize_symbol
from models.portfolio import Holding, Portfolio
from portfolio.repository import PortfolioRepository


class PortfolioNotFoundError(Exception):
    """Portfolio does not exist or does not belong to this user."""


class HoldingNotFoundError(Exception):
    """Holding does not exist on this portfolio."""


class UnknownStockError(Exception):
    """Symbol has not been ingested into the system."""


@dataclass
class HoldingValuation:
    holding: Holding
    current_price: float | None
    market_value: float | None
    cost_basis: float
    gain_loss: float | None


@dataclass
class PortfolioValuation:
    portfolio: Portfolio
    holdings: list[HoldingValuation] = field(default_factory=list)
    total_cost: float = 0.0
    total_value: float | None = None
    total_gain_loss: float | None = None


class PortfolioService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = PortfolioRepository(db)

    # ---- portfolios ----

    def create(self, user_id: int, name: str) -> Portfolio:
        portfolio = self.repo.create(user_id, name.strip())
        self.db.commit()
        self.db.refresh(portfolio)
        return portfolio

    def list_for_user(
        self, user_id: int, limit: int | None = None, offset: int = 0
    ) -> list[Portfolio]:
        return self.repo.list_for_user(user_id, limit=limit, offset=offset)

    def count_for_user(self, user_id: int) -> int:
        return self.repo.count_for_user(user_id)

    def get_valued(self, user_id: int, portfolio_id: int) -> PortfolioValuation:
        """Return portfolio with per-holding and aggregate valuations."""
        portfolio = self._owned_or_raise(user_id, portfolio_id)
        valuations: list[HoldingValuation] = []
        total_cost = 0.0
        total_value_parts: list[float] = []

        for h in portfolio.holdings:
            cost = float(h.shares) * float(h.purchase_price)
            current = self.repo.latest_close(h.stock_id)
            if current is not None:
                mv = float(h.shares) * current
                gl = mv - cost
                total_value_parts.append(mv)
            else:
                mv = None
                gl = None
            total_cost += cost
            valuations.append(
                HoldingValuation(
                    holding=h,
                    current_price=current,
                    market_value=mv,
                    cost_basis=cost,
                    gain_loss=gl,
                )
            )

        total_value = sum(total_value_parts) if total_value_parts else None
        total_gain_loss = (total_value - total_cost) if total_value is not None else None

        return PortfolioValuation(
            portfolio=portfolio,
            holdings=valuations,
            total_cost=total_cost,
            total_value=total_value,
            total_gain_loss=total_gain_loss,
        )

    def delete(self, user_id: int, portfolio_id: int) -> None:
        portfolio = self._owned_or_raise(user_id, portfolio_id)
        self.repo.delete(portfolio)
        self.db.commit()

    # ---- holdings ----

    def add_holding(
        self,
        user_id: int,
        portfolio_id: int,
        symbol: str,
        shares: float,
        purchase_price: float,
    ) -> Holding:
        portfolio = self._owned_or_raise(user_id, portfolio_id)
        symbol = normalize_symbol(symbol)
        stock = self.repo.get_stock_by_symbol(symbol)
        if stock is None:
            raise UnknownStockError(f"Stock {symbol!r} has not been ingested")
        holding = self.repo.add_holding(portfolio.id, stock.id, shares, purchase_price)
        self.db.commit()
        self.db.refresh(holding)
        return holding

    def remove_holding(self, user_id: int, portfolio_id: int, holding_id: int) -> None:
        portfolio = self._owned_or_raise(user_id, portfolio_id)
        holding = self.repo.get_holding(holding_id)
        if holding is None or holding.portfolio_id != portfolio.id:
            raise HoldingNotFoundError(f"Holding {holding_id} not found on this portfolio")
        self.repo.delete_holding(holding)
        self.db.commit()

    # ---- internal ----

    def _owned_or_raise(self, user_id: int, portfolio_id: int) -> Portfolio:
        portfolio = self.repo.get(portfolio_id)
        if portfolio is None or portfolio.user_id != user_id:
            raise PortfolioNotFoundError(f"Portfolio {portfolio_id} not found")
        return portfolio
