"""News ingestion and sentiment API tests.

transformers/torch are not installed in the local dev venv (they live in the
Docker image), so every test that would trigger FinBERT patches
``news.sentiment.score_batch`` before it can be called.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from models.news import NewsArticle, SentimentScore
from models.stock import Stock
from news.provider import RawArticle
from news.repository import NewsRepository
from news.sentiment import SentimentResult
from news.service import (
    NewsProviderNotConfiguredError,
    NewsService,
    UnknownStockError,
)

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def _raw(title="AAPL rallies", url="https://news.example.com/1", ts=None) -> RawArticle:
    return RawArticle(
        title=title,
        summary="Apple shares rose sharply.",
        source="Reuters",
        url=url,
        published_at=ts or int(datetime(2026, 1, 1, tzinfo=UTC).timestamp()),
    )


def _positive() -> SentimentResult:
    return SentimentResult(label="positive", score=0.92)


@pytest.fixture()
def stock(db_session) -> Stock:
    s = Stock(symbol="AAPL", name="Apple Inc.", sector="Technology")
    db_session.add(s)
    db_session.commit()
    return s


@pytest.fixture()
def news_repo(db_session) -> NewsRepository:
    return NewsRepository(db_session)


# ---------------------------------------------------------------------------
# NewsRepository
# ---------------------------------------------------------------------------

class TestNewsRepository:
    def test_upsert_inserts_new_article(self, db_session, stock, news_repo):
        article, created = news_repo.upsert_article(stock.id, _raw())
        db_session.commit()
        assert created is True
        assert article.id is not None
        assert article.title == "AAPL rallies"
        assert article.stock_id == stock.id

    def test_upsert_deduplicates_by_url(self, db_session, stock, news_repo):
        raw = _raw()
        first, c1 = news_repo.upsert_article(stock.id, raw)
        db_session.commit()
        second, c2 = news_repo.upsert_article(stock.id, raw)
        db_session.commit()
        assert c1 is True
        assert c2 is False
        assert first.id == second.id
        assert db_session.query(NewsArticle).count() == 1

    def test_upsert_null_url_always_inserts(self, db_session, stock, news_repo):
        # Articles without a URL skip deduplication — each call inserts a new row.
        raw = _raw(url=None)
        _, c1 = news_repo.upsert_article(stock.id, raw)
        db_session.commit()
        _, c2 = news_repo.upsert_article(stock.id, raw)
        db_session.commit()
        assert c1 is True
        assert c2 is True
        assert db_session.query(NewsArticle).count() == 2

    def test_set_sentiment_creates_score(self, db_session, stock, news_repo):
        article, _ = news_repo.upsert_article(stock.id, _raw())
        db_session.commit()
        score = news_repo.set_sentiment(article.id, _positive())
        db_session.commit()
        assert score.sentiment == "positive"
        assert float(score.confidence) == pytest.approx(0.92)

    def test_set_sentiment_updates_existing(self, db_session, stock, news_repo):
        article, _ = news_repo.upsert_article(stock.id, _raw())
        db_session.commit()
        news_repo.set_sentiment(article.id, _positive())
        db_session.commit()
        news_repo.set_sentiment(article.id, SentimentResult(label="negative", score=0.80))
        db_session.commit()
        assert db_session.query(SentimentScore).count() == 1
        assert db_session.query(SentimentScore).first().sentiment == "negative"

    def test_list_for_stock_newest_first(self, db_session, stock, news_repo):
        base_ts = int(datetime(2026, 1, 1, tzinfo=UTC).timestamp())
        for i in range(3):
            news_repo.upsert_article(
                stock.id,
                _raw(title=f"Article {i}", url=f"https://example.com/{i}", ts=base_ts + i),
            )
        db_session.commit()
        articles = news_repo.list_for_stock(stock.id)
        titles = [a.title for a in articles]
        assert titles == ["Article 2", "Article 1", "Article 0"]

    def test_list_for_stock_empty(self, db_session, stock, news_repo):
        assert news_repo.list_for_stock(stock.id) == []

    def test_list_for_stock_respects_limit(self, db_session, stock, news_repo):
        for i in range(5):
            news_repo.upsert_article(
                stock.id, _raw(title=f"T{i}", url=f"https://example.com/{i}")
            )
        db_session.commit()
        assert len(news_repo.list_for_stock(stock.id, limit=3)) == 3


# ---------------------------------------------------------------------------
# NewsService
# ---------------------------------------------------------------------------

class TestNewsService:
    def _make_provider(self, articles: list[RawArticle]) -> MagicMock:
        provider = MagicMock()
        provider.fetch.return_value = articles
        return provider

    def test_ingest_inserts_and_scores(self, db_session, stock):
        provider = self._make_provider([_raw()])
        with patch("news.service.score_batch", return_value=[_positive()]):
            result = NewsService(db_session, provider).ingest("AAPL")

        assert result.fetched == 1
        assert result.inserted == 1
        assert result.scored == 1
        assert len(result.articles) == 1
        assert result.articles[0].sentiment is not None
        assert result.articles[0].sentiment.sentiment == "positive"

    def test_ingest_deduplicates_on_second_call(self, db_session, stock):
        raw = _raw()
        provider = self._make_provider([raw])
        with patch("news.service.score_batch", return_value=[_positive()]):
            NewsService(db_session, provider).ingest("AAPL")
        with patch("news.service.score_batch", return_value=[]) as mock_score:
            result = NewsService(db_session, provider).ingest("AAPL")
            mock_score.assert_not_called()

        assert result.inserted == 0
        assert result.scored == 0
        assert result.fetched == 1

    def test_ingest_unknown_stock_raises(self, db_session):
        provider = self._make_provider([])
        with pytest.raises(UnknownStockError):
            NewsService(db_session, provider).ingest("ZZZZ")

    def test_ingest_without_provider_raises(self, db_session, stock):
        with pytest.raises(NewsProviderNotConfiguredError):
            NewsService(db_session, provider=None).ingest("AAPL")

    def test_ingest_empty_feed(self, db_session, stock):
        provider = self._make_provider([])
        with patch("news.service.score_batch", return_value=[]):
            result = NewsService(db_session, provider).ingest("AAPL")
        assert result.fetched == 0
        assert result.inserted == 0

    def test_latest_returns_stored(self, db_session, stock):
        # Seed one article directly via repository.
        repo = NewsRepository(db_session)
        article, _ = repo.upsert_article(stock.id, _raw())
        repo.set_sentiment(article.id, _positive())
        db_session.commit()

        articles = NewsService(db_session).latest("AAPL")
        assert len(articles) == 1
        assert articles[0].sentiment.sentiment == "positive"

    def test_latest_unknown_stock_raises(self, db_session):
        with pytest.raises(UnknownStockError):
            NewsService(db_session).latest("ZZZZ")


# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------

class TestNewsAPI:
    def _seed_article(self, db_session, stock, sentiment="positive"):
        repo = NewsRepository(db_session)
        article, _ = repo.upsert_article(stock.id, _raw())
        repo.set_sentiment(article.id, SentimentResult(label=sentiment, score=0.88))
        db_session.commit()
        return article

    def test_get_news_empty(self, client, auth_headers, stock):
        resp = client.get("/stocks/AAPL/news", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_news_returns_articles_with_sentiment(
        self, client, auth_headers, db_session, stock
    ):
        self._seed_article(db_session, stock, sentiment="negative")
        resp = client.get("/stocks/AAPL/news", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["title"] == "AAPL rallies"
        assert data[0]["sentiment"]["sentiment"] == "negative"
        assert data[0]["sentiment"]["confidence"] == pytest.approx(0.88)

    def test_get_news_unknown_stock_404(self, client, auth_headers):
        resp = client.get("/stocks/ZZZZ/news", headers=auth_headers)
        assert resp.status_code == 404

    def test_get_news_requires_auth(self, client, stock):
        assert client.get("/stocks/AAPL/news").status_code == 401

    def test_post_news_ingest(self, client, auth_headers, db_session, stock):
        mock_provider = MagicMock()
        mock_provider.fetch.return_value = [_raw()]

        from api.main import app
        from api.routers import news as news_router
        app.dependency_overrides[news_router.get_provider] = lambda: mock_provider

        try:
            with patch("news.service.score_batch", return_value=[_positive()]):
                resp = client.post("/stocks/AAPL/news", headers=auth_headers)
        finally:
            app.dependency_overrides.pop(news_router.get_provider, None)

        assert resp.status_code == 201
        data = resp.json()
        assert data["symbol"] == "AAPL"
        assert data["fetched"] == 1
        assert data["inserted"] == 1
        assert data["scored"] == 1
        assert len(data["articles"]) == 1
        assert data["articles"][0]["sentiment"]["sentiment"] == "positive"

    def test_post_news_no_api_key_503(self, client, auth_headers, stock):
        from api.main import app
        from api.routers import news as news_router
        app.dependency_overrides[news_router.get_provider] = lambda: None

        try:
            resp = client.post("/stocks/AAPL/news", headers=auth_headers)
        finally:
            app.dependency_overrides.pop(news_router.get_provider, None)

        assert resp.status_code == 503

    def test_post_news_unknown_stock_404(self, client, auth_headers):
        from api.main import app
        from api.routers import news as news_router
        mock_provider = MagicMock()
        mock_provider.fetch.return_value = []
        app.dependency_overrides[news_router.get_provider] = lambda: mock_provider

        try:
            resp = client.post("/stocks/ZZZZ/news", headers=auth_headers)
        finally:
            app.dependency_overrides.pop(news_router.get_provider, None)

        assert resp.status_code == 404

    def test_post_news_requires_auth(self, client, stock):
        assert client.post("/stocks/AAPL/news").status_code == 401

    def test_get_news_limit_param(self, client, auth_headers, db_session, stock):
        repo = NewsRepository(db_session)
        for i in range(5):
            repo.upsert_article(stock.id, _raw(title=f"T{i}", url=f"https://example.com/{i}"))
        db_session.commit()
        resp = client.get("/stocks/AAPL/news?limit=3", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 3

    def test_post_news_days_param(self, client, auth_headers, db_session, stock):
        mock_provider = MagicMock()
        mock_provider.fetch.return_value = []

        from api.main import app
        from api.routers import news as news_router
        app.dependency_overrides[news_router.get_provider] = lambda: mock_provider

        try:
            with patch("news.service.score_batch", return_value=[]):
                resp = client.post("/stocks/AAPL/news?days=30", headers=auth_headers)
        finally:
            app.dependency_overrides.pop(news_router.get_provider, None)

        assert resp.status_code == 201
        mock_provider.fetch.assert_called_once_with("AAPL", days=30)
