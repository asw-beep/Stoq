"""Classification evaluation metric unit tests."""

from __future__ import annotations

import pytest

from forecasting import evaluation


def test_perfect_accuracy():
    y = [1, 0, 1, 0, 1]
    m = evaluation.evaluate(y, y)
    assert m.accuracy == pytest.approx(1.0)
    assert m.precision == pytest.approx(1.0)
    assert m.recall == pytest.approx(1.0)
    assert m.n_samples == 5


def test_known_values():
    # y_true=[1,0,1,1] y_pred=[1,1,1,0]
    # correct at idx 0,2 → accuracy=0.5
    # TP=2 (idx 0,2), FP=1 (idx 1), FN=1 (idx 3)
    # precision=2/3, recall=2/3
    y_true = [1, 0, 1, 1]
    y_pred = [1, 1, 1, 0]
    m = evaluation.evaluate(y_true, y_pred)
    assert m.accuracy == pytest.approx(0.5)
    assert m.precision == pytest.approx(2 / 3)
    assert m.recall == pytest.approx(2 / 3)


def test_all_wrong():
    y_true = [1, 1, 0, 0]
    y_pred = [0, 0, 1, 1]
    m = evaluation.evaluate(y_true, y_pred)
    assert m.accuracy == pytest.approx(0.0)


def test_length_mismatch_raises():
    with pytest.raises(ValueError):
        evaluation.accuracy([1, 0], [1])


def test_empty_raises():
    with pytest.raises(ValueError):
        evaluation.evaluate([], [])


def test_no_positive_predictions():
    # All predictions are 0 → precision undefined → 0.0
    y_true = [1, 1, 0]
    y_pred = [0, 0, 0]
    m = evaluation.evaluate(y_true, y_pred)
    assert m.precision == pytest.approx(0.0)
    assert m.recall == pytest.approx(0.0)
