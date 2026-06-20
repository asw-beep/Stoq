"""Market overview endpoint (Phase 5.5).

Aggregates the latest close and day-over-day change for every tracked stock so
the dashboard home page has a single read to populate.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.schemas import MarketOverviewItem
from auth.dependencies import get_current_user
from db.session import get_db
from market_data.repository import StockRepository
from models.user import User

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/overview", response_model=list[MarketOverviewItem])
def market_overview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[MarketOverviewItem]:
    """Latest close + day-over-day change for every tracked stock."""
    repo = StockRepository(db)
    items: list[MarketOverviewItem] = []
    for stock in repo.list_stocks():
        closes = repo.latest_two_closes(stock.id)
        latest = closes[0] if closes else None
        previous = closes[1] if len(closes) > 1 else None
        change = (latest - previous) if (latest is not None and previous is not None) else None
        change_pct = (change / previous * 100.0) if (change is not None and previous) else None
        items.append(
            MarketOverviewItem(
                symbol=stock.symbol,
                name=stock.name,
                sector=stock.sector,
                latest_close=latest,
                previous_close=previous,
                change=change,
                change_pct=change_pct,
            )
        )
    return items
