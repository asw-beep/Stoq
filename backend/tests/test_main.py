"""App-factory hardening: docs disabled in production + global exception
sanitizer (Phase 5, ADR-0010)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import create_app
from core.config import Settings, get_settings

# A strong secret so production Settings pass the W-2 strength check.
_STRONG_SECRET = "x" * 40


def test_docs_enabled_in_development():
    app = create_app(get_settings())
    assert app.docs_url == "/docs"
    assert app.openapi_url == "/openapi.json"


def test_docs_disabled_in_production():
    prod = Settings(environment="production", secret_key=_STRONG_SECRET)
    app = create_app(prod)
    assert app.docs_url is None
    assert app.redoc_url is None
    assert app.openapi_url is None

    # The schema route is genuinely gone, not just hidden.
    client = TestClient(app)
    assert client.get("/openapi.json").status_code == 404
    assert client.get("/docs").status_code == 404


def test_unhandled_exception_is_sanitized():
    """A genuine 500 returns a generic body with no internal details (W-12)."""
    app = create_app(get_settings())

    @app.get("/_boom")
    def boom() -> None:
        raise RuntimeError("secret detail: postgresql://user:pass@host/db")

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/_boom")

    assert resp.status_code == 500
    assert resp.json() == {"detail": "Internal server error"}
    body = resp.text.lower()
    for needle in ("traceback", "runtimeerror", "postgresql", "secret detail", "/app/"):
        assert needle not in body
