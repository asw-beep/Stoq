from datetime import date, timedelta

from market_data.provider import StockInfo
from market_data.repository import StockRepository
from models.stock import HistoricalPrice, Stock


def test_list_stocks_empty(client, auth_headers):
    resp = client.get("/stocks", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body == {"items": [], "total": 0, "limit": 50, "offset": 0}


def test_get_unknown_stock_404(client, auth_headers):
    resp = client.get("/stocks/NOPE", headers=auth_headers)
    assert resp.status_code == 404


def test_upsert_and_list_stock(client, auth_headers, db_session):
    repo = StockRepository(db_session)
    repo.upsert_stock(StockInfo(symbol="AAPL", name="Apple Inc.", sector="Technology"))
    db_session.commit()

    resp = client.get("/stocks", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    data = body["items"]
    assert len(data) == 1
    assert data[0]["symbol"] == "AAPL"
    assert data[0]["sector"] == "Technology"

    detail = client.get("/stocks/aapl", headers=auth_headers)
    assert detail.status_code == 200
    assert detail.json()["price_count"] == 0


def test_upsert_is_idempotent(client, db_session):
    repo = StockRepository(db_session)
    repo.upsert_stock(StockInfo(symbol="MSFT", name="Microsoft", sector="Technology"))
    repo.upsert_stock(StockInfo(symbol="MSFT", name="Microsoft Corp", sector="Technology"))
    db_session.commit()
    assert len(repo.list_stocks()) == 1
    assert repo.get_by_symbol("MSFT").name == "Microsoft Corp"


def test_list_stocks_pagination(client, auth_headers, db_session):
    repo = StockRepository(db_session)
    for sym in ("AAA", "BBB", "CCC"):
        repo.upsert_stock(StockInfo(symbol=sym, name=sym, sector="Tech"))
    db_session.commit()

    resp = client.get("/stocks?limit=2&offset=0", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 3  # total is the unfiltered count
    assert body["limit"] == 2 and body["offset"] == 0
    assert [s["symbol"] for s in body["items"]] == ["AAA", "BBB"]  # ordered by symbol

    page2 = client.get("/stocks?limit=2&offset=2", headers=auth_headers).json()
    assert [s["symbol"] for s in page2["items"]] == ["CCC"]


def test_list_stocks_rejects_bad_pagination(client, auth_headers):
    assert client.get("/stocks?limit=0", headers=auth_headers).status_code == 422
    assert client.get("/stocks?limit=201", headers=auth_headers).status_code == 422
    assert client.get("/stocks?offset=-1", headers=auth_headers).status_code == 422


# ---- prices ----

def _seed_prices(db_session, symbol="AAPL", offsets=(0, 10, 100)):
    """Create a stock with one bar per day-offset (days before today)."""
    stock = Stock(symbol=symbol, name=f"{symbol} Inc.", sector="Tech")
    db_session.add(stock)
    db_session.flush()
    today = date.today()
    for i, off in enumerate(offsets):
        px = 100.0 + i
        db_session.add(
            HistoricalPrice(
                stock_id=stock.id,
                date=today - timedelta(days=off),
                open=px,
                high=px + 1,
                low=px - 1,
                close=px,
                volume=1_000 + i,
            )
        )
    db_session.commit()
    return stock


def test_get_prices_returns_bars_oldest_first(client, auth_headers, db_session):
    _seed_prices(db_session, offsets=(0, 10, 100))
    resp = client.get("/stocks/AAPL/prices?range=max", headers=auth_headers)
    assert resp.status_code == 200
    bars = resp.json()
    assert len(bars) == 3
    dates = [b["date"] for b in bars]
    assert dates == sorted(dates)  # ascending (chart-friendly)
    assert set(bars[0]) == {"date", "open", "high", "low", "close", "volume"}


def test_get_prices_range_filter(client, auth_headers, db_session):
    _seed_prices(db_session, offsets=(0, 10, 100))
    # 1m window (30d) excludes the 100-day-old bar.
    resp = client.get("/stocks/AAPL/prices?range=1m", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_get_prices_rejects_bad_range(client, auth_headers, db_session):
    _seed_prices(db_session)
    assert client.get("/stocks/AAPL/prices?range=5y", headers=auth_headers).status_code == 422


def test_get_prices_unknown_stock_404(client, auth_headers):
    assert client.get("/stocks/ZZZZ/prices", headers=auth_headers).status_code == 404


def test_get_prices_requires_auth(client):
    assert client.get("/stocks/AAPL/prices").status_code == 401


def test_get_prices_bad_symbol_422(client):
    assert client.get("/stocks/<script>/prices").status_code == 422
