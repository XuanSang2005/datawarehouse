"""Backtest rolling-origin, khoảng dự báo từ phân phối sai số và tổng hợp metric."""

from __future__ import annotations

import numpy as np
import pandas as pd

from ml.forecast.features import ONE_WEEK
from ml.forecast.models import mape


def rolling_origin(
    forecaster,
    history: pd.DataFrame,
    calendar: pd.DataFrame,
    window_start: pd.Timestamp,
    window_end: pd.Timestamp,
    horizon: int,
) -> pd.DataFrame:
    """Backtest rolling-origin cho các tuần mục tiêu trong [window_start, window_end].

    Với mỗi tuần gốc `origin` (từ window_start − horizon tuần đến window_end − 1 tuần):
    cắt history đến origin, (học lại và) dự báo h = 1..horizon tuần, chỉ giữ các dự báo rơi vào
    cửa sổ. Mỗi tuần mục tiêu vì vậy có đúng 1 dự báo cho mỗi h.
    Trả về: hotel_key, origin, h, week_start_date, yhat, actual.
    """
    actual = history.set_index(["hotel_key", "week_start_date"])["y"]
    origins = pd.date_range(window_start - ONE_WEEK * horizon, window_end - ONE_WEEK, freq="7D")
    parts = []
    for origin in origins:
        past = history[history["week_start_date"] <= origin]
        fc = forecaster.forecast(past, calendar, horizon)
        fc = fc[(fc["week_start_date"] >= window_start) & (fc["week_start_date"] <= window_end)]
        fc = fc.assign(origin=origin)
        parts.append(fc)
    out = pd.concat(parts, ignore_index=True)
    keys = pd.MultiIndex.from_frame(out[["hotel_key", "week_start_date"]])
    out["actual"] = actual.reindex(keys).to_numpy()
    if out["yhat"].isna().any():
        raise ValueError("Model không dự báo được một số tuần trong cửa sổ backtest")
    if out["actual"].isna().any():
        raise ValueError("Cửa sổ backtest chứa tuần không có actual")
    return out


def residual_quantiles(backtest: pd.DataFrame, coverage: float = 0.8) -> pd.DataFrame:
    """Phân vị của sai số tương đối r = actual / yhat − 1 theo từng horizon h.

    Khoảng dự báo `coverage` (mặc định 80%): [yhat·(1+q_low), yhat·(1+q_high)] với
    q_low, q_high là phân vị (1−coverage)/2 và (1+coverage)/2. Gộp 2 khách sạn để đủ mẫu.
    """
    alpha = (1 - coverage) / 2
    rel = backtest.assign(rel=backtest["actual"] / backtest["yhat"].clip(lower=1.0) - 1)
    q = rel.groupby("h")["rel"].quantile([alpha, 1 - alpha]).unstack()
    q.columns = ["q_low", "q_high"]
    # Bảo đảm lower ≤ yhat ≤ upper ngay cả khi sai số lệch hẳn một phía
    q["q_low"] = q["q_low"].clip(upper=0.0)
    q["q_high"] = q["q_high"].clip(lower=0.0)
    return q


def apply_interval(forecast: pd.DataFrame, quantiles: pd.DataFrame) -> pd.DataFrame:
    """Gắn lower_bound / upper_bound vào bảng dự báo theo h (h ngoài bảng phân vị → lỗi)."""
    missing = set(forecast["h"]) - set(quantiles.index)
    if missing:
        raise ValueError(f"Không có phân vị sai số cho h = {sorted(missing)}")
    q = quantiles.reindex(forecast["h"]).to_numpy()
    out = forecast.copy()
    out["lower_bound"] = np.maximum(out["yhat"] * (1 + q[:, 0]), 0.0)
    out["upper_bound"] = out["yhat"] * (1 + q[:, 1])
    return out


def summarize(backtest: pd.DataFrame, hotel_names: dict[int, str]) -> dict[str, float]:
    """Metric backtest của 1 model: MAPE chung, theo h, theo khách sạn (h=1), độ phủ khoảng."""
    metrics = {"mape": mape(backtest["actual"], backtest["yhat"])}
    for h, grp in backtest.groupby("h"):
        metrics[f"mape_h{h}"] = mape(grp["actual"], grp["yhat"])
    h1 = backtest[backtest["h"] == 1]
    for hotel_key, grp in h1.groupby("hotel_key"):
        slug = hotel_names[int(hotel_key)].lower().replace(" ", "_")
        metrics[f"mape_h1_{slug}"] = mape(grp["actual"], grp["yhat"])
    for hotel_key, grp in backtest.groupby("hotel_key"):
        slug = hotel_names[int(hotel_key)].lower().replace(" ", "_")
        metrics[f"mape_{slug}"] = mape(grp["actual"], grp["yhat"])
    if {"lower_bound", "upper_bound"} <= set(backtest.columns):
        inside = backtest["actual"].between(backtest["lower_bound"], backtest["upper_bound"])
        metrics["interval_coverage_80"] = float(inside.mean())
    return metrics
