"""Security regression suite.

Maps 1:1 to docs/ARCHITECTURE_FOR_SECURITY_TESTING.txt and the pre-production
security review. Two kinds of tests:

  * PASSING tests pin behaviour that is already safe (parameterized ORM, JSON
    encoding of reflected input). They fail if a regression reintroduces risk.

  * xfail(strict=True) tests assert the *target* secure behaviour for controls
    that are NOT yet implemented (auth, input validation, secret strength, etc.).
    They xfail today; the day the control lands they XPASS, which under strict
    mode FAILS the suite and forces you to delete the marker. Self-tightening.

Run from backend/:  pytest tests/test_security.py
"""

from __future__ import annotations

from pathlib import Path

import pytest

from market_data.provider import PriceBar, StockInfo
from market_data.repository import StockRepository

_REPO_ROOT = Path(__file__).resolve().parents[2]

INJECTION_PAYLOADS = [
    "AAPL' OR '1'='1",
    "'; DROP TABLE stocks;--",
    "' UNION SELECT password_hash FROM users--",
    "%27%20OR%201=1",
]

# Inputs sendable through the test client's URL parser as a SINGLE path segment.
# Two classes of payload are deliberately excluded from the HTTP-exercised list
# because the client mangles them before they reach the app (defense-in-depth,
# not app behaviour):
#   * control chars (\n, NUL) — httpx rejects them client-side.
#   * anything containing "/" (e.g. "../../etc/passwd", "<script>...</script>")
#     — the client splits/normalizes it into a different path, so it never hits
#     the /stocks/{symbol} route. These are covered at the service layer instead
#     (test_service_rejects_bad_symbol_before_provider_call).
BAD_INPUT_PAYLOADS = [
    "A" * 10_000,             # oversized
    "<script>",               # invalid charset (XSS-ish, single segment)
    "%0A",                    # encoded newline (log injection)
    "💥📈",                    # unicode
]


@pytest.fixture()
def seeded(db_session):
    """One known stock so injection/enumeration tests have a target to leak."""
    repo = StockRepository(db_session)
    repo.upsert_stock(StockInfo(symbol="AAPL", name="Apple Inc.", sector="Tech"))
    db_session.commit()
    return repo


# --------------------------------------------------------------------------- #
# SAFE-001 / W-11 : SQL injection is mitigated by the ORM. Prove it stays so.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("payload", INJECTION_PAYLOADS)
def test_sqli_payload_never_leaks_or_breaks(client, seeded, payload):
    resp = client.get(f"/stocks/{payload}")
    # Must be a clean "not found" or validation error, never a 500 and never the
    # seeded AAPL row returned via a boolean bypass.
    assert resp.status_code in (404, 422)
    # Table still intact / queries still work after the payload.
    assert seeded.get_by_symbol("AAPL") is not None
    assert len(seeded.list_stocks()) == 1


# --------------------------------------------------------------------------- #
# CRITICAL-002 / W-3 : symbol input validation.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("payload", BAD_INPUT_PAYLOADS)
def test_bad_symbol_does_not_500(client, payload):
    """Robustness (passes today): malformed input must not crash the server."""
    resp = client.get(f"/stocks/{payload}")
    assert resp.status_code != 500
    assert client.get("/health").status_code == 200  # process still healthy


@pytest.mark.parametrize("payload", BAD_INPUT_PAYLOADS)
def test_bad_symbol_rejected_with_422(client, payload):
    """Invalid symbols are rejected at validation, not silently 404'd."""
    assert client.get(f"/stocks/{payload}").status_code == 422


# --------------------------------------------------------------------------- #
# MEDIUM-001 / W-4 : reflected input in 404 detail stays JSON-safe.
# --------------------------------------------------------------------------- #
def test_reflected_symbol_is_json_encoded(client, auth_headers):
    """A valid-but-missing symbol is reflected into a 404 body, JSON-encoded so it
    cannot break out of the response context."""
    resp = client.get("/stocks/ZZZZ", headers=auth_headers)
    assert resp.status_code == 404
    assert resp.headers["content-type"].startswith("application/json")
    # Round-trips as JSON => cannot break out of the response context.
    assert isinstance(resp.json()["detail"], str)
    assert "ZZZZ" in resp.json()["detail"]


def test_invalid_symbol_error_is_json_encoded(client):
    """An invalid symbol is rejected with a JSON 422 — the rejected input never
    reaches an HTML/unescaped context."""
    resp = client.get("/stocks/<script>")
    assert resp.status_code == 422
    assert resp.headers["content-type"].startswith("application/json")
    resp.json()  # must be valid JSON


# --------------------------------------------------------------------------- #
# CRITICAL-003 / W-1 : authentication required on data endpoints.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("path", ["/stocks", "/stocks/AAPL"])
def test_endpoints_require_auth(client, path):
    assert client.get(path).status_code == 401


# --------------------------------------------------------------------------- #
# CRITICAL-001 / W-2 : weak default secret must be rejected in production.
# --------------------------------------------------------------------------- #
def test_weak_secret_rejected_in_production(monkeypatch):
    from core.config import Settings

    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("SECRET_KEY", "change-me")
    with pytest.raises(ValueError):
        Settings()


# --------------------------------------------------------------------------- #
# CRITICAL-005 / W-10 : a real password-hashing service must exist.
# --------------------------------------------------------------------------- #
def test_password_service_hashes_and_verifies():
    from core import security

    hashed = security.hash_password("hunter2")
    assert hashed != "hunter2" and hashed.startswith("$")  # bcrypt/argon2 prefix
    assert security.verify_password("hunter2", hashed)
    assert not security.verify_password("wrong", hashed)


# --------------------------------------------------------------------------- #
# HIGH-002 / W-5 : /health must not disclose environment.
# --------------------------------------------------------------------------- #
def test_health_does_not_disclose_environment(client):
    body = client.get("/health").json()
    assert "environment" not in body


def test_health_never_leaks_secrets(client):
    """Passes today: no secret/DSN material in the health body regardless."""
    raw = client.get("/health").text.lower()
    for needle in ("change-me", "stockpass", "password", "postgresql+psycopg"):
        assert needle not in raw


# --------------------------------------------------------------------------- #
# HIGH-003 / W-6 : security headers present.
# --------------------------------------------------------------------------- #
def test_security_headers_present(client):
    h = client.get("/health").headers
    assert h.get("x-content-type-options") == "nosniff"
    assert "x-frame-options" in h
    assert "referrer-policy" in h


# --------------------------------------------------------------------------- #
# MEDIUM-003 / W-12 : errors do not leak internals.
# --------------------------------------------------------------------------- #
def test_error_body_has_no_internal_traces(client, auth_headers):
    body = client.get("/stocks/NOPE", headers=auth_headers).text.lower()
    for needle in ("traceback", "sqlalchemy", "psycopg", "site-packages", "/app/"):
        assert needle not in body


# --------------------------------------------------------------------------- #
# MEDIUM-004 / W-13 : settings cache is clearable (env changes take effect).
# --------------------------------------------------------------------------- #
def test_settings_cache_can_be_cleared(monkeypatch):
    from core.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    assert get_settings().log_level == "WARNING"
    get_settings.cache_clear()  # don't poison other tests


# --------------------------------------------------------------------------- #
# FUTURE-001 / W-3,IN-2 : symbols validated BEFORE the outbound provider call.
# --------------------------------------------------------------------------- #
class _RecordingProvider:
    """Fake provider — records calls, never touches the network."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def get_stock_info(self, symbol: str) -> StockInfo:
        self.calls.append(symbol)
        return StockInfo(symbol=symbol.upper(), name=None, sector=None)

    def get_history(self, symbol: str, years: int) -> list[PriceBar]:
        return []


def test_service_rejects_bad_symbol_before_provider_call(db_session):
    from market_data.service import MarketDataService

    provider = _RecordingProvider()
    service = MarketDataService(db_session, provider)
    with pytest.raises(ValueError):
        service.ingest_symbol("../../etc/passwd", years=1)
    assert provider.calls == []  # never reached the external provider


# --------------------------------------------------------------------------- #
# HIGH-005 / HIGH-006 : container & compose hardening (static file checks).
# --------------------------------------------------------------------------- #
def test_dockerfile_runs_as_non_root():
    text = (_REPO_ROOT / "backend" / "Dockerfile").read_text(encoding="utf-8")
    assert "USER " in text


def test_compose_does_not_expose_postgres_to_host():
    text = (_REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert '"5432:5432"' not in text and "5432:5432" not in text
