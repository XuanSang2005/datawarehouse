"""Kiểm tra chọn ngưỡng, gán risk band và metric (không cần DB)."""

import numpy as np
import pytest

from ml.cancellation.evaluation import (
    RiskThresholds,
    assign_risk_band,
    best_f1_threshold,
    choose_thresholds,
    classification_metrics,
    precision_threshold,
)


def test_assign_risk_band_boundaries():
    t = RiskThresholds(medium=0.3, high=0.6)
    bands = assign_risk_band([0.0, 0.29, 0.3, 0.59, 0.6, 1.0], t)
    assert bands.tolist() == ["Low", "Low", "Medium", "Medium", "High", "High"]


def test_invalid_thresholds_rejected():
    with pytest.raises(ValueError):
        RiskThresholds(medium=0.7, high=0.5)
    with pytest.raises(ValueError):
        RiskThresholds(medium=0.0, high=0.5)


def test_best_f1_threshold_separable():
    y = np.array([0, 0, 0, 1, 1, 1])
    p = np.array([0.1, 0.2, 0.3, 0.7, 0.8, 0.9])
    assert best_f1_threshold(y, p) == 0.7


def test_precision_threshold_reaches_target():
    rng = np.random.default_rng(0)
    y = rng.integers(0, 2, 1000)
    p = np.clip(y * 0.4 + rng.random(1000) * 0.6, 0, 1)
    t = precision_threshold(y, p, 0.8)
    assert y[p >= t].mean() >= 0.8
    # là ngưỡng NHỎ NHẤT đạt mục tiêu: hạ thêm 0,02 thì precision không còn vượt hẳn mục tiêu
    assert y[p >= t - 0.02].mean() < 0.81


def test_choose_thresholds_ordered():
    rng = np.random.default_rng(1)
    y = rng.integers(0, 2, 2000)
    p = np.clip(y * 0.3 + rng.random(2000) * 0.7, 0, 0.99)
    t = choose_thresholds(y, p)
    assert 0 < t.medium <= t.high < 1


def test_classification_metrics_confusion_matrix():
    y = [0, 0, 1, 1]
    p = [0.1, 0.6, 0.4, 0.9]
    m = classification_metrics(y, p, threshold=0.5)
    assert (m["tn"], m["fp"], m["fn"], m["tp"]) == (1, 1, 1, 1)
    assert m["precision"] == m["recall"] == m["f1"] == 0.5
    assert m["auc"] == 0.75
