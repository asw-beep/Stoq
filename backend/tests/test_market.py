"""Market overview endpoint tests (Phase 5.5)."""

from __future__ import annotations

from datetime import date, timedelta

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
