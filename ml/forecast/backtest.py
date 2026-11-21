"""Rolling-origin backtest, forecast intervals from the error distribution, and metric summary."""

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
    """Rolling-origin backtest for the target weeks in [window_start, window_end].

    For each origin week `origin` (from window_start − horizon weeks to window_end − 1 week):
    cut history at origin, (refit and) forecast h = 1..horizon weeks, and keep only the forecasts
    that fall inside the window. Each target week therefore has exactly 1 forecast for each h.
    Returns: hotel_key, origin, h, week_start_date, yhat, actual.
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
        raise ValueError("The model could not forecast some weeks in the backtest window")
    if out["actual"].isna().any():
        raise ValueError("The backtest window contains weeks without an actual")
    return out


def residual_quantiles(backtest: pd.DataFrame, coverage: float = 0.8) -> pd.DataFrame:
    """Quantiles of the relative error r = actual / yhat − 1 for each horizon h.

    The `coverage` interval (80% by default): [yhat·(1+q_low), yhat·(1+q_high)] where
    q_low, q_high are the (1−coverage)/2 and (1+coverage)/2 quantiles. Both hotels are pooled
    for a large enough sample.
    """
    alpha = (1 - coverage) / 2
    rel = backtest.assign(rel=backtest["actual"] / backtest["yhat"].clip(lower=1.0) - 1)
    q = rel.groupby("h")["rel"].quantile([alpha, 1 - alpha]).unstack()
    q.columns = ["q_low", "q_high"]
    # Guarantee lower ≤ yhat ≤ upper even when the errors are entirely on one side
    q["q_low"] = q["q_low"].clip(upper=0.0)
    q["q_high"] = q["q_high"].clip(lower=0.0)
    return q


def apply_interval(forecast: pd.DataFrame, quantiles: pd.DataFrame) -> pd.DataFrame:
    """Attach lower_bound / upper_bound to the forecast by h (h missing from quantiles → error)."""
    missing = set(forecast["h"]) - set(quantiles.index)
    if missing:
        raise ValueError(f"No error quantiles for h = {sorted(missing)}")
    q = quantiles.reindex(forecast["h"]).to_numpy()
    out = forecast.copy()
    out["lower_bound"] = np.maximum(out["yhat"] * (1 + q[:, 0]), 0.0)
    out["upper_bound"] = out["yhat"] * (1 + q[:, 1])
    return out


def summarize(backtest: pd.DataFrame, hotel_names: dict[int, str]) -> dict[str, float]:
    """Backtest metrics of 1 model: overall MAPE, per h, per hotel (h=1), interval coverage."""
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
