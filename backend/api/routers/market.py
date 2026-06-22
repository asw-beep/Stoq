"""Market overview, signals, and sentiment endpoints (Phase 5.5 / F4)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from api.schemas import MarketOverviewItem, MarketSentimentItem, MarketSignalItem
from auth.dependencies import get_current_user
from db.session import get_db
from market_data.repository import StockRepository
from models.forecast import Forecast
from models.news import NewsArticle, SentimentScore
from models.stock import Stock
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


@router.get("/signals", response_model=list[MarketSignalItem])
def market_signals(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[MarketSignalItem]:
    """Latest 1-day directional forecast signal per tracked stock."""
    # Latest forecast_date per stock that has a direction
    latest_fdate = (
        select(Forecast.stock_id, func.max(Forecast.forecast_date).label("max_fdate"))
        .where(Forecast.direction.isnot(None))
        .group_by(Forecast.stock_id)
        .subquery()
    )
    # Among those rows, take the nearest target_date (horizon-1 signal)
    nearest_tdate = (
        select(
            Forecast.stock_id,
            Forecast.forecast_date,
            func.min(Forecast.target_date).label("min_tdate"),
        )
        .join(
            latest_fdate,
            (Forecast.stock_id == latest_fdate.c.stock_id)
            & (Forecast.forecast_date == latest_fdate.c.max_fdate),
        )
        .group_by(Forecast.stock_id, Forecast.forecast_date)
        .subquery()
    )
    rows = db.execute(
        select(
            Stock.symbol,
            Stock.name,
            Forecast.model,
            Forecast.direction,
            Forecast.probability,
            Forecast.forecast_date,
            Forecast.target_date,
        )
        .join(Forecast, Forecast.stock_id == Stock.id)
        .join(
            nearest_tdate,
            (Forecast.stock_id == nearest_tdate.c.stock_id)
            & (Forecast.forecast_date == nearest_tdate.c.forecast_date)
            & (Forecast.target_date == nearest_tdate.c.min_tdate),
        )
        .order_by(Stock.symbol)
    ).fetchall()

    # The join keys on (stock, forecast_date, target_date) but not model, so two
    # directional models that ran the same day for the same horizon would each
    # produce a row. Collapse to one signal per symbol, keeping the most
    # confident (highest probability) so the dashboard never double-counts.
    best: dict[str, MarketSignalItem] = {}
    for r in rows:
        prob = float(r.probability) if r.probability is not None else None
        existing = best.get(r.symbol)
        if existing is None or (prob or 0.0) > (existing.probability or 0.0):
            best[r.symbol] = MarketSignalItem(
                symbol=r.symbol,
                name=r.name,
                model=r.model,
                direction=r.direction,
                probability=prob,
                forecast_date=r.forecast_date,
                target_date=r.target_date,
            )
    return [best[k] for k in sorted(best)]


@router.get("/sentiment", response_model=list[MarketSentimentItem])
def market_sentiment(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[MarketSentimentItem]:
    """Aggregated FinBERT sentiment counts per tracked stock."""
    rows = db.execute(
        select(
            Stock.symbol,
            Stock.name,
            func.count(SentimentScore.id).label("total"),
            func.sum(
                case((SentimentScore.sentiment == "positive", 1), else_=0)
            ).label("positive"),
            func.sum(
                case((SentimentScore.sentiment == "negative", 1), else_=0)
            ).label("negative"),
            func.sum(
                case((SentimentScore.sentiment == "neutral", 1), else_=0)
            ).label("neutral"),
        )
        .select_from(Stock)
        .join(NewsArticle, NewsArticle.stock_id == Stock.id, isouter=True)
        .join(SentimentScore, SentimentScore.article_id == NewsArticle.id, isouter=True)
        .group_by(Stock.id, Stock.symbol, Stock.name)
        .order_by(Stock.symbol)
    ).fetchall()

    return [
        MarketSentimentItem(
            symbol=r.symbol,
            name=r.name,
            positive=int(r.positive or 0),
            negative=int(r.negative or 0),
            neutral=int(r.neutral or 0),
            total=int(r.total or 0),
        )
        for r in rows
    ]
