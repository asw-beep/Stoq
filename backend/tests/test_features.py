"""Technical-indicator unit tests (no models, no DB)."""

from __future__ import annotations

import pandas as pd
import pytest

from forecasting import features


def _series(values: list[float]) -> pd.Series:
    idx = pd.date_range("2024-01-01", periods=len(values), freq="D")
    return pd.Series(values, index=idx, dtype=float)


def test_sma_matches_manual_mean():
    s = _series([1, 2, 3, 4, 5])
    out = features.sma(s, window=3)
    assert out.iloc[:2].isna().all()  # warm-up
    assert out.iloc[2] == pytest.approx(2.0)  # (1+2+3)/3
    assert out.iloc[4] == pytest.approx(4.0)  # (3+4+5)/3


def test_ema_first_value_equals_first_price():
    s = _series([10, 20, 30])
    out = features.ema(s, span=2)
    assert out.iloc[0] == pytest.approx(10.0)  # adjust=False seeds on first point
    assert out.iloc[-1] > out.iloc[0]


def test_rsi_all_gains_is_100():
    s = _series(list(range(1, 30)))  # strictly increasing -> no losses
    out = features.rsi(s, window=14)
    assert out.dropna().iloc[-1] == pytest.approx(100.0)


def test_rsi_bounded_0_100():
    s = _series([5, 3, 8, 2, 9, 1, 10, 4, 7, 6, 11, 2, 13, 3, 14, 5, 15])
    out = features.rsi(s, window=5).dropna()
    assert ((out >= 0) & (out <= 100)).all()


def test_macd_hist_is_line_minus_signal():
    s = _series([float(i) + (i % 3) for i in range(60)])
    out = features.macd(s)
    assert set(out.columns) == {"macd", "macd_signal", "macd_hist"}
    last = out.dropna().iloc[-1]
    assert last["macd_hist"] == pytest.approx(last["macd"] - last["macd_signal"])


def test_build_feature_frame_adds_all_indicators():
    s = _series([100 + i * 0.5 for i in range(60)])
    frame = pd.DataFrame({"close": s, "volume": 1000})
    out = features.build_feature_frame(frame)
    for col in ("sma_20", "ema_20", "rsi_14", "macd", "macd_signal", "macd_hist", "volatility_20"):
        assert col in out.columns


def test_build_feature_frame_requires_close():
    with pytest.raises(ValueError):
        features.build_feature_frame(pd.DataFrame({"volume": [1, 2, 3]}))
