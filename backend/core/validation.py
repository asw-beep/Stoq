"""Shared input validation.

Centralizes the canonical stock-symbol rule so the API layer (HTTP 422) and the
service layer (pre-fetch guard) enforce exactly the same contract — no drift, one
source of truth. See docs/ARCHITECTURE_FOR_SECURITY_TESTING.txt (W-3, CRITICAL-002).
"""

from __future__ import annotations

import re

# Tickers are short, uppercase, alphanumeric with dots/hyphens (e.g. BRK.B, RDS-A).
SYMBOL_PATTERN = r"^[A-Z0-9.-]{1,20}$"
_SYMBOL_RE = re.compile(SYMBOL_PATTERN)


def normalize_symbol(symbol: str) -> str:
    """Uppercase + validate a stock symbol.

    Returns the normalized (uppercased) symbol, or raises ``ValueError`` if it
    does not match :data:`SYMBOL_PATTERN`. Accepts lowercase input for ergonomics
    while rejecting anything outside the allowed charset/length.
    """
    candidate = symbol.strip().upper()
    if not _SYMBOL_RE.fullmatch(candidate):
        raise ValueError(f"Invalid stock symbol: {symbol!r}")
    return candidate
