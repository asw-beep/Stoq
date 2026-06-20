"""Forecast endpoint tests: auth, validation, and happy path with a stub model."""

from __future__ import annotations

from datetime import timedelta

import pandas as pd
import pytest  # noqa: F401 — used for pytest.approx

from api.main import app
from api.routers.forecasts import get_forecaster
from forecasting.models.base import Prediction


class StubForecaster:
    name = "stub"

    def predict(self, prices: pd.DataFrame, horizons: list[int]) -> list[Prediction]:
        last = pd.Timestamp(prices.index[-1]).date()
        return [
            Prediction(target_date=last + timedelta(days=h), direction=1, probability=0.68)
            for h in horizons
        ]


@pytest.fixture()
def stub_forecaster():
    app.dependency_overrides[get_forecaster] = lambda: StubForecaster()
    yield
    app.dependency_overrides.pop(get_forecaster, None)


def test_create_forecast_requires_auth(client):
    resp = client.post("/stocks/AAPL/forecasts", json={"horizons": [1]})
    assert resp.status_code == 401


def test_create_forecast_bad_symbol_422_even_unauthenticated(client):
    # valid_symbol runs before auth -> malformed symbol 422s without a token.
    resp = client.post("/stocks/@bad!/forecasts", json={"horizons": [1]})
    assert resp.status_code == 422


def test_create_forecast_unknown_stock_404(client, auth_headers, stub_forecaster):
    resp = client.post("/stocks/AAPL/forecasts", json={"horizons": [1]}, headers=auth_headers)
    assert resp.status_code == 404


def test_create_and_read_forecasts(client, auth_headers, stub_forecaster, seed_stock):
    seed_stock("AAPL", days=40)

    created = client.post(
        "/stocks/AAPL/forecasts", json={"horizons": [1, 7, 30]}, headers=auth_headers
    )
    assert created.status_code == 201
    body = created.json()
    assert len(body) == 3
    assert body[0]["model"] == "stub"
    assert body[0]["direction"] == 1
    assert body[0]["probability"] == pytest.approx(0.68)

    got = client.get("/stocks/AAPL/forecasts", headers=auth_headers)
    assert got.status_code == 200
    assert len(got.json()) == 3


def test_create_forecast_empty_horizons_422(client, auth_headers, stub_forecaster, seed_stock):
    seed_stock("AAPL", days=40)
    resp = client.post(
        "/stocks/AAPL/forecasts", json={"horizons": [0, -5]}, headers=auth_headers
    )
    assert resp.status_code == 422


def test_create_forecast_unknown_model_422(client, auth_headers, seed_stock):
    # No stub override here: the real get_forecaster validates the model name.
    seed_stock("AAPL", days=40)
    resp = client.post(
        "/stocks/AAPL/forecasts?model=bogus", json={"horizons": [1]}, headers=auth_headers
    )
    assert resp.status_code == 422


def test_get_forecasts_empty_when_none(client, auth_headers, stub_forecaster, seed_stock):
    seed_stock("AAPL", days=40)
    resp = client.get("/stocks/AAPL/forecasts", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []
