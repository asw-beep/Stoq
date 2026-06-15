"""Data-access layer for NewsArticle and SentimentScore."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from models.news import NewsArticle, SentimentScore
from news.provider import RawArticle
from news.sentiment import SentimentResult


class NewsRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def upsert_article(self, stock_id: int, raw: RawArticle) -> tuple[NewsArticle, bool]:
        """Insert article if URL is new; return (article, created)."""
        existing = None
        if raw.url:
            existing = self.db.scalar(
                select(NewsArticle).where(NewsArticle.url == raw.url)
            )
        if existing is not None:
            return existing, False

        published = (
            datetime.fromtimestamp(raw.published_at, tz=timezone.utc)
            if raw.published_at
            else None
        )
        article = NewsArticle(
            stock_id=stock_id,
            title=raw.title,
            content=raw.summary,
            source=raw.source,
            url=raw.url,
            published_at=published,
        )
        self.db.add(article)
        self.db.flush()
        return article, True

    def set_sentiment(self, article_id: int, result: SentimentResult) -> SentimentScore:
        """Replace any existing sentiment score for this article."""
        existing = self.db.scalar(
            select(SentimentScore).where(SentimentScore.article_id == article_id)
        )
        if existing is not None:
            existing.sentiment = result.label
            existing.confidence = result.score
            return existing

        score = SentimentScore(
            article_id=article_id,
            sentiment=result.label,
            confidence=result.score,
        )
        self.db.add(score)
        self.db.flush()
        return score

    def list_for_stock(self, stock_id: int, limit: int = 50) -> list[NewsArticle]:
        return list(
            self.db.scalars(
                select(NewsArticle)
                .where(NewsArticle.stock_id == stock_id)
                .options(selectinload(NewsArticle.sentiment))
                .order_by(NewsArticle.published_at.desc())
                .limit(limit)
            )
        )
