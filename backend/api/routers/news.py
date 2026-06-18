"""News endpoints (nested under /stocks/{symbol})."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from api.routers.stocks import valid_symbol
from api.schemas import NewsArticleOut, NewsIngestOut
from auth.dependencies import get_current_user
from core.config import get_settings
from core.rate_limit import limiter
from db.session import get_db
from models.user import User
from news.provider import FinnhubProvider
from news.service import NewsProviderNotConfiguredError, NewsService, UnknownStockError

router = APIRouter(prefix="/stocks/{symbol}/news", tags=["news"])


def get_provider() -> FinnhubProvider | None:
    """Return a Finnhub client if the API key is configured, else None."""
    key = get_settings().finnhub_api_key
    return FinnhubProvider(key) if key else None


@router.post("", response_model=NewsIngestOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def ingest_news(
    request: Request,
    days: int = Query(default=7, ge=1, le=90),
    symbol: str = Depends(valid_symbol),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    provider: FinnhubProvider | None = Depends(get_provider),
) -> NewsIngestOut:
    """Fetch news from Finnhub, score with FinBERT, persist new articles."""
    service = NewsService(db, provider)
    try:
        result = service.ingest(symbol, days=days)
    except NewsProviderNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from None
    except UnknownStockError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from None

    return NewsIngestOut(
        symbol=result.symbol,
        fetched=result.fetched,
        inserted=result.inserted,
        scored=result.scored,
        articles=[NewsArticleOut.model_validate(a) for a in result.articles],
    )


@router.get("", response_model=list[NewsArticleOut])
def get_news(
    limit: int = Query(default=50, ge=1, le=200),
    symbol: str = Depends(valid_symbol),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[NewsArticleOut]:
    """Return stored news articles for a stock, newest first."""
    service = NewsService(db)
    try:
        articles = service.latest(symbol, limit=limit)
    except UnknownStockError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from None
    return [NewsArticleOut.model_validate(a) for a in articles]
