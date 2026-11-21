"""Hàm thuần (không cần DB) để chọn ngưỡng, gán risk band và tính metric phân loại."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)

RISK_BANDS = ("Low", "Medium", "High")
# Ngưỡng High: precision tối thiểu trên tập validation. Booking "High" sẽ bị yêu cầu đặt cọc hoặc
# được tính vào hạn mức overbooking, là hành động TỐN KÉM nếu đoán sai, nên cần >= 4/5 booking
# được gắn High thực sự hủy.
HIGH_TARGET_PRECISION = 0.80


@dataclass(frozen=True)
class RiskThresholds:
    """Low: p < medium; Medium: medium <= p < high; High: p >= high."""

    medium: float
    high: float

    def __post_init__(self) -> None:
        if not 0.0 < self.medium <= self.high < 1.0:
            raise ValueError(f"Ngưỡng không hợp lệ: medium={self.medium}, high={self.high}")


def best_f1_threshold(y_true, proba) -> float:
    """Ngưỡng làm F1 lớn nhất (làm tròn 2 chữ số để dễ đọc, dễ giải thích)."""
    precision, recall, thresholds = precision_recall_curve(y_true, proba)
    # precision/recall dài hơn thresholds 1 phần tử (điểm cuối recall = 0)
    p, r = precision[:-1], recall[:-1]
    f1 = np.divide(2 * p * r, p + r, out=np.zeros_like(p), where=(p + r) > 0)
    return round(float(thresholds[int(np.argmax(f1))]), 2)


def precision_threshold(y_true, proba, target_precision: float = HIGH_TARGET_PRECISION) -> float:
    """Ngưỡng NHỎ NHẤT (recall lớn nhất) mà precision (p >= ngưỡng) vẫn >= target_precision.

    Làm tròn LÊN 2 chữ số. Nếu không ngưỡng nào đạt target thì lấy ngưỡng có precision cao nhất.
    """
    precision, _, thresholds = precision_recall_curve(y_true, proba)
    p = precision[:-1]
    ok = np.flatnonzero(p >= target_precision)
    idx = int(ok[0]) if len(ok) else int(np.argmax(p))
    return float(np.ceil(round(float(thresholds[idx]) * 100, 6)) / 100)


def choose_thresholds(y_true, proba) -> RiskThresholds:
    """Chọn ngưỡng trên tập validation.

    High   = ngưỡng nhỏ nhất đạt precision >= 80% (hành động tốn kém: đòi cọc, overbooking).
    Medium = ngưỡng làm F1 lớn nhất (cân bằng precision/recall; hành động rẻ: gọi xác nhận lại).
    Nếu ngưỡng F1 cao hơn ngưỡng High thì Medium = High (không có band Medium).
    """
    high = precision_threshold(y_true, proba)
    medium = min(max(best_f1_threshold(y_true, proba), 0.01), high)
    high = min(high, 0.99)
    return RiskThresholds(medium=min(medium, high), high=high)


def assign_risk_band(proba, thresholds: RiskThresholds) -> np.ndarray:
    proba = np.asarray(proba, dtype=float)
    return np.where(
        proba >= thresholds.high,
        "High",
        np.where(proba >= thresholds.medium, "Medium", "Low"),
    )


def classification_metrics(y_true, proba, threshold: float) -> dict[str, float]:
    """AUC, PR-AUC, Brier + precision/recall/F1/accuracy và confusion matrix tại ngưỡng."""
    y_true = np.asarray(y_true).astype(int)
    proba = np.asarray(proba, dtype=float)
    y_pred = (proba >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    return {
        "auc": float(roc_auc_score(y_true, proba)),
        "pr_auc": float(average_precision_score(y_true, proba)),
        "brier": float(brier_score_loss(y_true, proba)),
        "threshold": float(threshold),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "tn": float(tn),
        "fp": float(fp),
        "fn": float(fn),
        "tp": float(tp),
        "n_rows": float(len(y_true)),
        "positive_rate": float(y_true.mean()),
    }
