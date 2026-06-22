"""Market overview, signals, and sentiment endpoint tests (Phase 5.5 / F4)."""

from __future__ import annotations

from datetime import date, timedelta

from models.forecast import Forecast
from models.news import NewsArticle, SentimentScore
from models.stock import HistoricalPrice, Stock


def _seed_stock_with_closes(db_session, symbol, closes):
    """Create a stock with one bar per close, dated consecutively (oldest first)."""
    stock = Stock(symbol=symbol, name=f"{symbol} Inc.", sector="Tech")
    db_session.add(stock)
    db_session.flush()
    start = date.today() - timedelta(days=len(closes))
    for i, c in enumerate(closes):
        db_session.add(
            HistoricalPrice(
                stock_id=stock.id,
                date=start + timedelta(days=i),
                open=c,
                high=c,
                low=c,
                close=c,
                volume=1_000,
            )
        )
    db_session.commit()
    return stock


def test_market_overview_requires_auth(client):
    assert client.get("/market/overview").status_code == 401


def test_market_overview_empty(client, auth_headers):
    resp = client.get("/market/overview", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_market_overview_computes_change(client, auth_headers, db_session):
    _seed_stock_with_closes(db_session, "AAPL", [100.0, 110.0])  # +10 (10%)
    resp = client.get("/market/overview", headers=auth_headers)
    assert resp.status_code == 200
    item = next(i for i in resp.json() if i["symbol"] == "AAPL")
    assert item["latest_close"] == 110.0
    assert item["previous_close"] == 100.0
    assert item["change"] == 10.0
    assert item["change_pct"] == 10.0


def test_market_overview_single_bar_has_no_change(client, auth_headers, db_session):
    _seed_stock_with_closes(db_session, "MSFT", [200.0])
    resp = client.get("/market/overview", headers=auth_headers)
    item = next(i for i in resp.json() if i["symbol"] == "MSFT")
    assert item["latest_close"] == 200.0
    assert item["previous_close"] is None
    assert item["change"] is None
    assert item["change_pct"] is None


# ---- signals (F4 forecast dashboard) ----


def _seed_forecast(db_session, stock_id, *, fdate, tdate, direction, prob, model="xgboost"):
    db_session.add(
        Forecast(
            stock_id=stock_id,
            forecast_date=fdate,
            target_date=tdate,
            model=model,
            direction=direction,
            probability=prob,
        )
    )
    db_session.commit()


def test_market_signals_requires_auth(client):
    assert client.get("/market/signals").status_code == 401


def test_market_signals_empty(client, auth_headers):
    resp = client.get("/market/signals", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_market_signals_returns_latest_nearest_signal(client, auth_headers, db_session):
    stock = _seed_stock_with_closes(db_session, "AAPL", [100.0])
    today = date.today()
    # An older run that should be ignored once a newer forecast_date exists.
    _seed_forecast(
        db_session, stock.id, fdate=today - timedelta(days=3),
        tdate=today + timedelta(days=1), direction=0, prob=0.55,
    )
    # The latest run, two horizons. The nearest target_date is the signal.
    _seed_forecast(
        db_session, stock.id, fdate=today,
        tdate=today + timedelta(days=1), direction=1, prob=0.72,
    )
    _seed_forecast(
        db_session, stock.id, fdate=today,
        tdate=today + timedelta(days=7), direction=0, prob=0.61,
    )

    resp = client.get("/market/signals", headers=auth_headers)
    assert resp.status_code == 200
    rows = resp.json()
    aapl = [r for r in rows if r["symbol"] == "AAPL"]
    assert len(aapl) == 1  # exactly one row per stock
    item = aapl[0]
    assert item["direction"] == 1
    assert item["probability"] == 0.72
    assert item["target_date"] == (today + timedelta(days=1)).isoformat()


def test_market_signals_dedupes_multiple_models(client, auth_headers, db_session):
    # Two directional models, same stock/forecast_date/target_date: the endpoint
    # must return one row per symbol, keeping the most confident signal.
    stock = _seed_stock_with_closes(db_session, "AAPL", [100.0])
    today = date.today()
    tdate = today + timedelta(days=1)
    _seed_forecast(db_session, stock.id, fdate=today, tdate=tdate,
                   direction=0, prob=0.55, model="xgboost")
    _seed_forecast(db_session, stock.id, fdate=today, tdate=tdate,
                   direction=1, prob=0.81, model="lstm")

    rows = client.get("/market/signals", headers=auth_headers).json()
    aapl = [r for r in rows if r["symbol"] == "AAPL"]
    assert len(aapl) == 1
    assert aapl[0]["probability"] == 0.81  # most confident wins
    assert aapl[0]["direction"] == 1


def test_market_signals_omits_stocks_without_direction(client, auth_headers, db_session):
    stock = _seed_stock_with_closes(db_session, "MSFT", [200.0])
    today = date.today()
    # A regression-style forecast (no direction) must not appear as a signal.
    db_session.add(
        Forecast(
            stock_id=stock.id,
            forecast_date=today,
            target_date=today + timedelta(days=1),
            model="prophet",
            direction=None,
            probability=None,
            predicted_price=210.0,
            confidence=0.9,
        )
    )
    db_session.commit()
    resp = client.get("/market/signals", headers=auth_headers)
    assert resp.status_code == 200
    assert all(r["symbol"] != "MSFT" for r in resp.json())


# ---- sentiment (F4 sentiment dashboard) ----


def _seed_news(db_session, stock_id, sentiments):
    """Create one scored article per label in `sentiments` (e.g. ['positive',...])."""
    for i, label in enumerate(sentiments):
        article = NewsArticle(
            stock_id=stock_id,
            title=f"headline {stock_id}-{i}",
            url=f"https://news.test/{stock_id}/{i}",
        )
        db_session.add(article)
        db_session.flush()
        db_session.add(
            SentimentScore(article_id=article.id, sentiment=label, confidence=0.9)
        )
    db_session.commit()


def test_market_sentiment_requires_auth(client):
    assert client.get("/market/sentiment").status_code == 401


def test_market_sentiment_aggregates_counts(client, auth_headers, db_session):
    stock = _seed_stock_with_closes(db_session, "AAPL", [100.0])
    _seed_news(db_session, stock.id, ["positive", "positive", "negative", "neutral"])

    resp = client.get("/market/sentiment", headers=auth_headers)
    assert resp.status_code == 200
    item = next(i for i in resp.json() if i["symbol"] == "AAPL")
    assert item["positive"] == 2
    assert item["negative"] == 1
    assert item["neutral"] == 1
    assert item["total"] == 4


def test_market_sentiment_includes_stocks_without_news(client, auth_headers, db_session):
    _seed_stock_with_closes(db_session, "NEW", [50.0])  # no news ingested
    resp = client.get("/market/sentiment", headers=auth_headers)
    assert resp.status_code == 200
    item = next(i for i in resp.json() if i["symbol"] == "NEW")
    assert item == {
        "symbol": "NEW",
        "name": "NEW Inc.",
        "positive": 0,
        "negative": 0,
        "neutral": 0,
        "total": 0,
    }
