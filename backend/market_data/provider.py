"""Market data provider abstraction.

A thin interface over the external data source so the rest of the system depends
on an abstraction, not on yfinance directly (Dependency Inversion). Swapping to
AlphaVantage/Tiingo later means adding a new implementation here only.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol


@dataclass(frozen=True)
class PriceBar:
    """One daily OHLCV bar."""

    date: date
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass(frozen=True)
class StockInfo:
    symbol: str
    name: str | None
    sector: str | None


class MarketDataProvider(Protocol):
    """Interface every market-data source must implement."""

    def get_stock_info(self, symbol: str) -> StockInfo: ...

    def get_history(self, symbol: str, years: int) -> list[PriceBar]: ...


class YFinanceProvider:
    """yfinance-backed implementation of MarketDataProvider."""

    def get_stock_info(self, symbol: str) -> StockInfo:
        import yfinance as yf

        ticker = yf.Ticker(symbol)
        info = ticker.info or {}
        return StockInfo(
            symbol=symbol.upper(),
            name=info.get("longName") or info.get("shortName"),
            sector=info.get("sector"),
        )

    def get_history(self, symbol: str, years: int) -> list[PriceBar]:
        import yfinance as yf

        ticker = yf.Ticker(symbol)
        df = ticker.history(period=f"{years}y", interval="1d", auto_adjust=False)
        bars: list[PriceBar] = []
        for ts, row in df.iterrows():
            bars.append(
                PriceBar(
                    date=ts.date(),
                    open=float(row["Open"]),
                    high=float(row["High"]),
                    low=float(row["Low"]),
                    close=float(row["Close"]),
                    volume=int(row["Volume"]),
                )
            )
        return bars


def get_provider(name: str = "yfinance") -> MarketDataProvider:
    """Factory: resolve a provider implementation by name."""
    if name == "yfinance":
        return YFinanceProvider()
    raise ValueError(f"Unknown market data provider: {name!r}")
