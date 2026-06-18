"""Rate limiting (Phase 5, ADR-0010).

The limiter is disabled suite-wide in conftest; this test re-enables it locally
so it can assert the per-IP login limit actually trips, then restores the
disabled state for the rest of the suite.
"""

from __future__ import annotations

import pytest

from core.rate_limit import limiter


@pytest.fixture()
def rate_limited(client):
    """Enable the limiter (and reset its counters) for one test."""
    limiter.reset()
    limiter.enabled = True
    try:
        yield client
    finally:
        limiter.enabled = False
        limiter.reset()


def test_login_is_rate_limited(rate_limited):
    """The 6th login within the window is rejected with 429 (limit is 5/min)."""
    form = {"username": "nobody@example.com", "password": "wrong-password"}

    statuses = [
        rate_limited.post("/auth/login", data=form).status_code for _ in range(6)
    ]

    # First five are processed (401 — bad creds); the sixth is throttled.
    assert statuses[:5] == [401, 401, 401, 401, 401]
    assert statuses[5] == 429
