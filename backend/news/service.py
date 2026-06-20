"""News ingestion and retrieval service."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from core.validation import normalize_symbol
from market_data.repository import StockRepository
from models.news import NewsArticle
from news.provider import FinnhubProvider
from news.repository import NewsRepository
from news.sentiment import score_batch

logger = logging.getLogger(__name__)


class UnknownStockError(Exception):
    """Symbol has not been ingested into the system."""


class NewsProviderNotConfiguredError(Exception):
    """FINNHUB_API_KEY is missing or empty."""


@dataclass
class IngestResult:
    symbol: str
    fetched: int
    inserted: int
    scored: int
    articles: list[NewsArticle] = field(default_factory=list)


class NewsService:
    def __init__(self, db: Session, provider: FinnhubProvider | None = None) -> None:
        self.db = db
        self.provider = provider
        self.repo = NewsRepository(db)
        self.stocks = StockRepository(db)

    def ingest(self, symbol: str, days: int = 7) -> IngestResult:
        """Fetch news from Finnhub, score with FinBERT, persist new articles."""
        if self.provider is None:
            raise NewsProviderNotConfiguredError(
                "FINNHUB_API_KEY is not set; add it to your .env file"
            )
        symbol = normalize_symbol(symbol)
        stock = self.stocks.get_by_symbol(symbol)
        if stock is None:
            raise UnknownStockError(f"Stock {symbol!r} has not been ingested")

        raw_articles = self.provider.fetch(symbol, days=days)
        logger.info("Finnhub returned %d articles for %s", len(raw_articles), symbol)

        # Finnhub's free-tier company_news endpoint returns loosely tagged
        # articles that often mention unrelated companies. Keep only articles
        # where the symbol or a meaningful word of the company name appears in
        # the headline or summary.
        _NOISE = {"inc", "inc.", "corp", "corp.", "ltd", "ltd.", "plc",
                  "llc", "co.", "the", "and", "group", "holdings", "company"}
        name_tokens = {
            t.lower() for t in stock.name.split()
            if len(t) > 2 and t.lower() not in _NOISE
        }
        name_tokens.add(symbol.lower())

        def _relevant(article: object) -> bool:
            haystack = (article.title or "").lower()
            return any(tok in haystack for tok in name_tokens)

        raw_articles = [a for a in raw_articles if _relevant(a)]
        logger.info("%d articles remain after relevance filter", len(raw_articles))

        new_articles: list[NewsArticle] = []
        new_texts: list[str] = []

        for raw in raw_articles:
            article, created = self.repo.upsert_article(stock.id, raw)
            if created:
                new_articles.append(article)
                # Use headline + summary for richer sentiment signal.
                text = raw.title
                if raw.summary:
                    text = f"{raw.title}. {raw.summary}"
                new_texts.append(text)

        # Batch-score all new articles in one FinBERT forward pass.
        if new_texts:
            scores = score_batch(new_texts)
            for article, result in zip(new_articles, scores, strict=True):
                self.repo.set_sentiment(article.id, result)

        self.db.commit()

        # Return the full stored list (new + previously stored).
        stored = self.repo.list_for_stock(stock.id)
        return IngestResult(
            symbol=symbol,
            fetched=len(raw_articles),
            inserted=len(new_articles),
            scored=len(new_texts),
            articles=stored,
        )

    def latest(self, symbol: str, limit: int = 50) -> list[NewsArticle]:
        """Return stored articles for a symbol, newest first."""
        symbol = normalize_symbol(symbol)
        stock = self.stocks.get_by_symbol(symbol)
        if stock is None:
            raise UnknownStockError(f"Stock {symbol!r} has not been ingested")
        return self.repo.list_for_stock(stock.id, limit=limit)
