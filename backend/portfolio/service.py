"""Portfolio business logic (Service layer).

Enforces ownership: every mutating operation verifies the portfolio belongs to
the requesting user before proceeding.
"""

from __future__ import annotations

import math
from collections import defaultdict
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
class PortfolioAnalytics:
    return_pct: float | None
    annualized_return: float | None
    annualized_volatility: float | None
    sharpe_ratio: float | None
    max_drawdown: float | None


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

    def get_analytics(self, user_id: int, portfolio_id: int) -> PortfolioAnalytics:
        """Compute return %, annualized volatility, Sharpe ratio, and max drawdown.

        Modeling assumptions (intentional simplifications):
        - **Current allocation, not realized P&L.** The daily value series applies
          *today's* share counts across the whole window — it measures the risk
          profile of the current allocation, not what was actually held over time
          (purchase/sale dates are ignored). ``return_pct`` is the only
          cost-basis-aware figure.
        - **Daily returns over a 365-day window** (``prices_for_stocks``); only
          dates where *every* holding has a price contribute, and ≥ 20 such dates
          are required before time-series metrics are reported.
        - **Risk-free rate = 0%** for the Sharpe ratio (annualized via ×252 /
          ×√252). Surfaced as a sub-label in the UI so the assumption is explicit.
        """
        portfolio = self._owned_or_raise(user_id, portfolio_id)
        holdings = portfolio.holdings

        if not holdings:
            return PortfolioAnalytics(None, None, None, None, None)

        # Single price query feeds both the return series and current valuation —
        # the latest close per holding is the last (newest) bar in its series.
        stock_ids = [h.stock_id for h in holdings]
        prices_map = self.repo.prices_for_stocks(stock_ids, days=365)

        total_cost = 0.0
        value_parts: list[float] = []
        for h in holdings:
            total_cost += float(h.shares) * float(h.purchase_price)
            bars = prices_map.get(h.stock_id)
            if bars:
                value_parts.append(float(h.shares) * float(bars[-1].close))
        total_value = sum(value_parts) if value_parts else None
        return_pct = (
            round((total_value - total_cost) / total_cost * 100, 2)
            if (total_value is not None and total_cost > 0)
            else None
        )

        # Build portfolio daily value series (dates where ALL holdings have prices)
        date_values: dict = defaultdict(float)
        date_counts: dict = defaultdict(int)
        for h in holdings:
            for p in prices_map.get(h.stock_id, []):
                date_values[p.date] += float(h.shares) * float(p.close)
                date_counts[p.date] += 1

        n_holdings = len(holdings)
        complete_dates = sorted(d for d, c in date_counts.items() if c == n_holdings)

        if len(complete_dates) < 20:
            return PortfolioAnalytics(
                return_pct=return_pct,
                annualized_return=None,
                annualized_volatility=None,
                sharpe_ratio=None,
                max_drawdown=None,
            )

        values = [date_values[d] for d in complete_dates]
        daily_returns = [
            (values[i] - values[i - 1]) / values[i - 1] for i in range(1, len(values))
        ]

        n = len(daily_returns)
        mean_r = sum(daily_returns) / n
        variance = sum((r - mean_r) ** 2 for r in daily_returns) / n
        std_dev = math.sqrt(variance) if variance > 0 else 0.0

        ann_return = round(mean_r * 252 * 100, 2)
        ann_vol = round(std_dev * math.sqrt(252) * 100, 2)
        sharpe = round(ann_return / ann_vol, 2) if ann_vol > 0 else None

        # Max drawdown (peak-to-trough as %)
        peak = values[0]
        max_dd = 0.0
        for v in values:
            if v > peak:
                peak = v
            dd = (peak - v) / peak if peak > 0 else 0.0
            if dd > max_dd:
                max_dd = dd

        return PortfolioAnalytics(
            return_pct=return_pct,
            annualized_return=ann_return,
            annualized_volatility=ann_vol,
            sharpe_ratio=sharpe,
            max_drawdown=round(max_dd * 100, 2),
        )

    # ---- internal ----

    def _owned_or_raise(self, user_id: int, portfolio_id: int) -> Portfolio:
        portfolio = self.repo.get(portfolio_id)
        if portfolio is None or portfolio.user_id != user_id:
            raise PortfolioNotFoundError(f"Portfolio {portfolio_id} not found")
        return portfolio
