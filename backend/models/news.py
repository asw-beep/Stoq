"""News article and sentiment score models."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base, TimestampMixin


class NewsArticle(Base, TimestampMixin):
    __tablename__ = "news_articles"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    content: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str | None] = mapped_column(String(120))
    url: Mapped[str | None] = mapped_column(String(1024))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    sentiment: Mapped[SentimentScore | None] = relationship(
        back_populates="article", cascade="all, delete-orphan", uselist=False
    )


class SentimentScore(Base, TimestampMixin):
    __tablename__ = "sentiment_scores"

    id: Mapped[int] = mapped_column(primary_key=True)
    article_id: Mapped[int] = mapped_column(
        ForeignKey("news_articles.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # Label produced by FinBERT: positive | negative | neutral.
    sentiment: Mapped[str] = mapped_column(String(20), nullable=False)
    confidence: Mapped[float] = mapped_column(Numeric(6, 4), nullable=False)

    article: Mapped[NewsArticle] = relationship(back_populates="sentiment")
