"""Technical indicators (Feature Engineering).

Pure functions over a daily-OHLCV ``pandas.DataFrame`` indexed by date with at
least a ``close`` column (``volume`` for completeness). No DB or model coupling,
so they are trivially unit-testable and reusable by any model.

Indicators implemented (per docs/ML_Design.md): SMA, EMA, RSI, MACD, volatility.
"""

from __future__ import annotations

import pandas as pd


def sma(close: pd.Series, window: int = 20) -> pd.Series:
    """Simple moving average over ``window`` periods."""
    return close.rolling(window=window, min_periods=window).mean()


def ema(close: pd.Series, span: int = 20) -> pd.Series:
    """Exponential moving average with the given ``span``."""
    return close.ewm(span=span, adjust=False).mean()


def rsi(close: pd.Series, window: int = 14) -> pd.Series:
    """Relative Strength Index (Wilder's smoothing), bounded 0..100.

    A flat series yields RSI 100 by convention (no losses); the first ``window``
    values are NaN while the average warms up.
    """
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()
    rs = avg_gain / avg_loss
    out = 100.0 - (100.0 / (1.0 + rs))
    # avg_loss == 0 -> rs is inf/NaN -> RSI is 100 (only gains in the window).
    out = out.where(avg_loss != 0, 100.0)
    return out


def macd(
    close: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> pd.DataFrame:
    """MACD line, signal line, and histogram as a 3-column frame."""
    macd_line = ema(close, span=fast) - ema(close, span=slow)
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return pd.DataFrame(
        {
            "macd": macd_line,
            "macd_signal": signal_line,
            "macd_hist": macd_line - signal_line,
        }
    )


def volatility(close: pd.Series, window: int = 20) -> pd.Series:
    """Rolling volatility = stddev of daily log returns over ``window``."""
    import numpy as np

    log_ret = np.log(close / close.shift(1))
    return log_ret.rolling(window=window, min_periods=window).std()


def build_feature_frame(prices: pd.DataFrame) -> pd.DataFrame:
    """Assemble all indicators onto the price frame.

    Expects columns ``close`` and ``volume`` indexed by date. Returns a new frame
    with indicator columns added; rows whose indicators are still warming up are
    left as NaN (callers decide whether to drop them).
    """
    if "close" not in prices.columns:
        raise ValueError("price frame must contain a 'close' column")

    out = prices.copy()
    close = out["close"]
    out["sma_20"] = sma(close, 20)
    out["ema_20"] = ema(close, 20)
    out["rsi_14"] = rsi(close, 14)
    out = out.join(macd(close))
    out["volatility_20"] = volatility(close, 20)
    return out
