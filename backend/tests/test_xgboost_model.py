"""XGBoostForecaster tests.

The model training tests require the ``xgboost`` wheel; they are skipped when it
is not installed (it is lazy-imported in the engine). The factory test runs
unconditionally.
"""

from __future__ import annotations

import math

import pandas as pd
import pytest

from forecasting.models.factory import SUPPORTED_MODELS, build_forecaster


def _price_frame(days: int = 80, start: float = 100.0) -> pd.DataFrame:
    import math as _math
    idx = pd.date_range("2024-01-01", periods=days, freq="D")
    # Sinusoidal pattern so both up and down days exist — prevents single-class
    # label issues in the classifier tests.
    close = [start + 10 * _math.sin(i * 0.3) + i * 0.1 for i in range(days)]
    return pd.DataFrame({"close": close, "volume": [1_000_000 + i for i in range(days)]}, index=idx)


def test_factory_builds_known_models():
    assert build_forecaster("xgboost").name == "xgboost"
    assert set(SUPPORTED_MODELS) == {"xgboost"}


def test_factory_unknown_model_raises():
    with pytest.raises(ValueError):
        build_forecaster("magic-8-ball")


def test_xgboost_rejects_short_history():
    from forecasting.models.xgboost_model import XGBoostForecaster

    with pytest.raises(ValueError):
        XGBoostForecaster().predict(_price_frame(days=10), [1])


def test_xgboost_predicts_each_horizon():
    pytest.importorskip("xgboost")
    from forecasting.models.xgboost_model import XGBoostForecaster

    preds = XGBoostForecaster(n_estimators=20).predict(_price_frame(days=200), [1, 7, 30])

    assert len(preds) == 3
    assert [p.target_date for p in preds] == sorted(p.target_date for p in preds)
    for p in preds:
        assert p.direction in (0, 1)
        assert math.isfinite(p.probability)
        assert 0.0 <= p.probability <= 1.0
