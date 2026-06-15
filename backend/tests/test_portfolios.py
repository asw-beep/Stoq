"""Portfolio API tests."""

from __future__ import annotations

import pytest
from datetime import date, timedelta

from models.stock import HistoricalPrice, Stock


@pytest.fixture()
def seed_stock_with_price(db_session):
    """Create a stock with one price bar and return (stock, price)."""
    stock = Stock(symbol="TSLA", name="Tesla Inc.", sector="Auto")
    db_session.add(stock)
    db_session.flush()
    today = date.today()
    price = HistoricalPrice(
        stock_id=stock.id,
        date=today,
        open=250.0,
        high=260.0,
        low=245.0,
        close=255.0,
        volume=10_000_000,
    )
    db_session.add(price)
    db_session.commit()
    return stock, price


# ---- create / list / delete portfolios ----

def test_create_portfolio(client, auth_headers):
    resp = client.post("/portfolios", json={"name": "My Portfolio"}, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "My Portfolio"
    assert data["holding_count"] == 0
    assert "id" in data


def test_list_portfolios_empty(client, auth_headers):
    resp = client.get("/portfolios", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_portfolios(client, auth_headers):
    client.post("/portfolios", json={"name": "P1"}, headers=auth_headers)
    client.post("/portfolios", json={"name": "P2"}, headers=auth_headers)
    resp = client.get("/portfolios", headers=auth_headers)
    assert resp.status_code == 200
    names = [p["name"] for p in resp.json()]
    assert "P1" in names and "P2" in names


def test_get_portfolio_detail_empty(client, auth_headers):
    created = client.post("/portfolios", json={"name": "Empty"}, headers=auth_headers).json()
    resp = client.get(f"/portfolios/{created['id']}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["holdings"] == []
    assert data["total_cost"] == 0.0
    assert data["total_value"] is None


def test_get_portfolio_404(client, auth_headers):
    resp = client.get("/portfolios/9999", headers=auth_headers)
    assert resp.status_code == 404


def test_delete_portfolio(client, auth_headers):
    created = client.post("/portfolios", json={"name": "ToDelete"}, headers=auth_headers).json()
    pid = created["id"]
    resp = client.delete(f"/portfolios/{pid}", headers=auth_headers)
    assert resp.status_code == 204
    assert client.get(f"/portfolios/{pid}", headers=auth_headers).status_code == 404


def test_delete_portfolio_404(client, auth_headers):
    resp = client.delete("/portfolios/9999", headers=auth_headers)
    assert resp.status_code == 404


# ---- holdings ----

def test_add_holding(client, auth_headers, seed_stock_with_price):
    created = client.post("/portfolios", json={"name": "P"}, headers=auth_headers).json()
    pid = created["id"]
    resp = client.post(
        f"/portfolios/{pid}/holdings",
        json={"symbol": "TSLA", "shares": 10.0, "purchase_price": 200.0},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["symbol"] == "TSLA"
    assert data["shares"] == 10.0
    assert data["purchase_price"] == 200.0
    assert data["cost_basis"] == 2000.0
    assert data["current_price"] == 255.0
    assert data["market_value"] == 2550.0
    assert data["gain_loss"] == pytest.approx(550.0)


def test_add_holding_unknown_stock(client, auth_headers):
    created = client.post("/portfolios", json={"name": "P"}, headers=auth_headers).json()
    resp = client.post(
        f"/portfolios/{created['id']}/holdings",
        json={"symbol": "ZZZZZ", "shares": 1.0, "purchase_price": 100.0},
        headers=auth_headers,
    )
    assert resp.status_code == 404


def test_add_holding_wrong_portfolio(client, make_user, db_session, seed_stock_with_price):
    from core.security import create_access_token

    other = make_user(email="other@example.com")
    other_token = create_access_token(subject=str(other.id))
    other_headers = {"Authorization": f"Bearer {other_token}"}

    created = client.post(
        "/portfolios", json={"name": "Mine"}, headers=other_headers
    ).json()
    pid = created["id"]

    from core.security import create_access_token as cat
    attacker = make_user(email="attacker@example.com")
    attacker_headers = {"Authorization": f"Bearer {cat(subject=str(attacker.id))}"}

    resp = client.post(
        f"/portfolios/{pid}/holdings",
        json={"symbol": "TSLA", "shares": 1.0, "purchase_price": 100.0},
        headers=attacker_headers,
    )
    assert resp.status_code == 404


def test_portfolio_detail_with_holding(client, auth_headers, seed_stock_with_price):
    created = client.post("/portfolios", json={"name": "P"}, headers=auth_headers).json()
    pid = created["id"]
    client.post(
        f"/portfolios/{pid}/holdings",
        json={"symbol": "TSLA", "shares": 5.0, "purchase_price": 200.0},
        headers=auth_headers,
    )
    resp = client.get(f"/portfolios/{pid}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["holdings"]) == 1
    assert data["total_cost"] == 1000.0
    assert data["total_value"] == 1275.0
    assert data["total_gain_loss"] == pytest.approx(275.0)


def test_remove_holding(client, auth_headers, seed_stock_with_price):
    created = client.post("/portfolios", json={"name": "P"}, headers=auth_headers).json()
    pid = created["id"]
    holding = client.post(
        f"/portfolios/{pid}/holdings",
        json={"symbol": "TSLA", "shares": 1.0, "purchase_price": 100.0},
        headers=auth_headers,
    ).json()
    resp = client.delete(
        f"/portfolios/{pid}/holdings/{holding['id']}", headers=auth_headers
    )
    assert resp.status_code == 204
    detail = client.get(f"/portfolios/{pid}", headers=auth_headers).json()
    assert detail["holdings"] == []


def test_remove_holding_404(client, auth_headers):
    created = client.post("/portfolios", json={"name": "P"}, headers=auth_headers).json()
    resp = client.delete(
        f"/portfolios/{created['id']}/holdings/9999", headers=auth_headers
    )
    assert resp.status_code == 404


def test_portfolios_require_auth(client):
    assert client.get("/portfolios").status_code == 401
    assert client.post("/portfolios", json={"name": "X"}).status_code == 401


def test_portfolio_isolation_between_users(client, make_user):
    from core.security import create_access_token

    u1 = make_user(email="u1@example.com")
    u2 = make_user(email="u2@example.com")
    h1 = {"Authorization": f"Bearer {create_access_token(subject=str(u1.id))}"}
    h2 = {"Authorization": f"Bearer {create_access_token(subject=str(u2.id))}"}

    client.post("/portfolios", json={"name": "U1 portfolio"}, headers=h1)
    resp = client.get("/portfolios", headers=h2)
    assert resp.status_code == 200
    assert resp.json() == []
