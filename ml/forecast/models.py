"""Các mô hình dự báo room-nights theo tuần: 2 baseline + Gradient Boosting.

Mỗi forecaster có cùng giao diện:
    forecast(history, calendar, horizon) -> DataFrame[hotel_key, h, week_start_date, yhat]
trong đó `history` chỉ chứa dữ liệu đến tuần gốc (origin) — tuần cuối của mỗi khách sạn —
và dự báo các tuần origin+1 … origin+horizon. Mô hình cần học thì học lại ở mỗi origin.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

from ml.forecast.features import (
    FEATURE_COLUMNS,
    ONE_WEEK,
    SEASON_LAG,
    build_training_matrix,
    feature_row,
)


def mape(actual: Sequence[float], predicted: Sequence[float]) -> float:
    """Mean Absolute Percentage Error dạng TỈ LỆ (0.08 = 8%). Actual phải > 0."""
    a = np.asarray(actual, dtype=float)
    p = np.asarray(predicted, dtype=float)
    if a.shape != p.shape or a.size == 0:
        raise ValueError("actual và predicted phải cùng độ dài và không rỗng")
    if (a <= 0).any():
        raise ValueError("MAPE không xác định khi actual <= 0")
    return float(np.mean(np.abs(a - p) / a))


def seasonal_naive(past: Sequence[float], horizon: int, season: int = SEASON_LAG) -> list[float]:
    """Dự báo tuần origin+h = giá trị cùng tuần năm trước (lùi `season` tuần).

    NaN cho các h mà lịch sử chưa đủ dài (chưa có "cùng tuần năm trước").
    """
    if horizon > season:
        raise ValueError("horizon không được vượt quá chu kỳ mùa vụ")
    n = len(past)
    out = []
    for h in range(1, horizon + 1):
        idx = n - season + h - 1
        out.append(float(past[idx]) if idx >= 0 else float("nan"))
    return out


def moving_average(past: Sequence[float], horizon: int, window: int = 4) -> list[float]:
    """Dự báo phẳng = trung bình `window` tuần gần nhất (giữ nguyên cho mọi h)."""
    if len(past) < window:
        raise ValueError(f"Cần ít nhất {window} tuần lịch sử cho moving average")
    level = float(np.mean(past[-window:]))
    return [level] * horizon


def _frame(hotel_key: int, origin: pd.Timestamp, yhat: Sequence[float]) -> pd.DataFrame:
    hs = np.arange(1, len(yhat) + 1)
    return pd.DataFrame(
        {
            "hotel_key": hotel_key,
            "h": hs,
            "week_start_date": [origin + ONE_WEEK * int(h) for h in hs],
            "yhat": np.asarray(yhat, dtype=float),
        }
    )


@dataclass
class PerHotelBaseline:
    """Bọc 1 hàm baseline (seasonal_naive / moving_average) chạy riêng từng khách sạn."""

    model_name: str
    func: object  # Callable[[Sequence[float], int], list[float]]

    def forecast(self, history: pd.DataFrame, calendar: pd.DataFrame, horizon: int) -> pd.DataFrame:
        parts = []
        for hotel_key, grp in history.groupby("hotel_key"):
            origin = grp["week_start_date"].max()
            parts.append(_frame(int(hotel_key), origin, self.func(grp["y"].tolist(), horizon)))
        return pd.concat(parts, ignore_index=True)


@dataclass
class GbmForecaster:
    """Gradient Boosting gộp 2 khách sạn, đặc trưng lag + mùa vụ + lịch; dự báo đệ quy.

    Dự báo nhiều bước theo kiểu đệ quy: dự báo tuần origin+1 rồi đưa vào làm lag_1 cho
    tuần origin+2, … Các lag ≥ 52 tuần luôn là số thật khi horizon ≤ 51.
    """

    resort_keys: set[int]
    model_name: str = "forecast_gbm"
    params: dict = field(
        default_factory=lambda: {
            "max_iter": 300,
            "learning_rate": 0.05,
            "max_depth": 3,
            "min_samples_leaf": 8,
            "l2_regularization": 1.0,
            "random_state": 42,
        }
    )

    def fit(
        self, history: pd.DataFrame, calendar: pd.DataFrame
    ) -> tuple[HistGradientBoostingRegressor, list[str]]:
        """Học model; bỏ cột toàn NaN (vd lag_52 khi lịch sử < 1 năm ở các origin sớm)."""
        x, y = build_training_matrix(history, calendar, self.resort_keys)
        columns = [c for c in FEATURE_COLUMNS if x[c].notna().any()]
        model = HistGradientBoostingRegressor(**self.params)
        model.fit(x[columns], y)
        return model, columns

    def forecast(self, history: pd.DataFrame, calendar: pd.DataFrame, horizon: int) -> pd.DataFrame:
        model, columns = self.fit(history, calendar)
        parts = []
        for hotel_key, grp in history.groupby("hotel_key"):
            origin = grp["week_start_date"].max()
            past = grp["y"].tolist()
            preds: list[float] = []
            for h in range(1, horizon + 1):
                cal = calendar.loc[origin + ONE_WEEK * h]
                row = feature_row(
                    past, int(hotel_key in self.resort_keys), cal["iso_week"], cal["n_holidays"]
                )
                yhat = float(model.predict(pd.DataFrame([row], columns=columns))[0])
                yhat = max(yhat, 0.0)
                preds.append(yhat)
                past = [*past, yhat]
            parts.append(_frame(int(hotel_key), origin, preds))
        return pd.concat(parts, ignore_index=True)
