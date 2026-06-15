"""Finnhub news provider.

Fetches company news for a given stock symbol. The free tier allows 60
requests/min, plenty for on-demand per-symbol fetches.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import finnhub


@dataclass
class RawArticle:
    title: str
    summary: str | None
    source: str | None
    url: str | None
    published_at: int  # Unix timestamp from Finnhub


class FinnhubProvider:
    def __init__(self, api_key: str) -> None:
        self._client = finnhub.Client(api_key=api_key)

    def fetch(self, symbol: str, days: int = 7) -> list[RawArticle]:
        """Return up to ``days`` worth of news articles for a symbol."""
        to_date = date.today()
        from_date = to_date - timedelta(days=days)
        raw = self._client.company_news(
            symbol.upper(),
            _from=from_date.isoformat(),
            to=to_date.isoformat(),
        )
        return [
            RawArticle(
                title=item.get("headline", ""),
                summary=item.get("summary") or None,
                source=item.get("source") or None,
                url=item.get("url") or None,
                published_at=item.get("datetime", 0),
            )
            for item in (raw or [])
            if item.get("headline")
        ]
