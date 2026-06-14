"""Evaluation-metric unit tests."""

from __future__ import annotations

import pytest

from forecasting import evaluation


def test_perfect_prediction_is_zero_error():
    y = [10.0, 20.0, 30.0]
    m = evaluation.evaluate(y, y)
    assert m.rmse == pytest.approx(0.0)
    assert m.mae == pytest.approx(0.0)
    assert m.mape == pytest.approx(0.0)


def test_known_values():
    y_true = [100.0, 200.0]
    y_pred = [110.0, 180.0]  # errors: +10, -20
    assert evaluation.mae(y_true, y_pred) == pytest.approx(15.0)
    assert evaluation.rmse(y_true, y_pred) == pytest.approx((250.0) ** 0.5)
    # |10/100| + |20/200| = 0.10 + 0.10 -> mean 0.10 -> 10%
    assert evaluation.mape(y_true, y_pred) == pytest.approx(10.0)


def test_length_mismatch_raises():
    with pytest.raises(ValueError):
        evaluation.rmse([1.0, 2.0], [1.0])


def test_empty_raises():
    with pytest.raises(ValueError):
        evaluation.mae([], [])


def test_mape_skips_zero_true_values():
    # Only the non-zero true value contributes: |(5-4)/5| = 0.2 -> 20%
    assert evaluation.mape([0.0, 5.0], [1.0, 4.0]) == pytest.approx(20.0)


def test_mape_all_zero_true_raises():
    with pytest.raises(ValueError):
        evaluation.mape([0.0, 0.0], [1.0, 2.0])
