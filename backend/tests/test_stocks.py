from market_data.provider import StockInfo
from market_data.repository import StockRepository


def test_list_stocks_empty(client):
    resp = client.get("/stocks")
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_unknown_stock_404(client):
    resp = client.get("/stocks/NOPE")
    assert resp.status_code == 404


def test_upsert_and_list_stock(client, db_session):
    repo = StockRepository(db_session)
    repo.upsert_stock(StockInfo(symbol="AAPL", name="Apple Inc.", sector="Technology"))
    db_session.commit()

    resp = client.get("/stocks")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["symbol"] == "AAPL"
    assert data[0]["sector"] == "Technology"

    detail = client.get("/stocks/aapl")
    assert detail.status_code == 200
    assert detail.json()["price_count"] == 0


def test_upsert_is_idempotent(client, db_session):
    repo = StockRepository(db_session)
    repo.upsert_stock(StockInfo(symbol="MSFT", name="Microsoft", sector="Technology"))
    repo.upsert_stock(StockInfo(symbol="MSFT", name="Microsoft Corp", sector="Technology"))
    db_session.commit()
    assert len(repo.list_stocks()) == 1
    assert repo.get_by_symbol("MSFT").name == "Microsoft Corp"
