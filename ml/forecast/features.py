"""Prepare the weekly series and build features for the demand forecasting model.

Data conventions shared across `ml/forecast/`:
- `history`: long DataFrame, each row = 1 hotel × 1 COMPLETE 7-night week, columns
  `hotel_key`, `week_start_date`, `y` (room-nights sold). Weeks are contiguous, without gaps.
- `calendar`: DataFrame indexed by `week_start_date` (every week, including future ones), columns
  `iso_week`, `n_holidays`.

All functions here are pure (no DB reads) so they can be unit tested.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from datetime import timedelta

import numpy as np
import pandas as pd

SEASON_LAG = 52  # "same week last year" = 52 weeks back (364 days, same weekday)
ONE_WEEK = timedelta(days=7)

FEATURE_COLUMNS = [
    "is_resort",
    "iso_week",
    "n_holidays",
    "lag_1",
    "lag_2",
    "ma_4",
    "lag_52",
    "seasonal_3",
    "yoy_level",
    "seasonal_adj",
]
MIN_PAST_WEEKS = 4  # at least 4 past weeks are needed for ma_4


def prepare_series(raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.Timestamp]:
    """Split the data read by `database/ml/31_forecast_weekly_series.sql` into history + calendar.

    - Only weeks with all 7 nights (`days_observed = 7`) are kept as observations. Partial edge
      weeks (2015-06-29: 5 nights, 2017-08-28: 4 nights) are dropped: their room-night totals are
      artificially low.
    - Check that the complete weeks are contiguous (only then are positional lags meaningful).
    - Also return `last_week`: the last complete week (shared by all hotels).
    """
    df = raw.copy()
    df["week_start_date"] = pd.to_datetime(df["week_start_date"])

    calendar = (
        df.drop_duplicates("week_start_date")
        .set_index("week_start_date")[["iso_week", "n_holidays"]]
        .sort_index()
    )

    observed = df[df["days_observed"] == 7].copy()
    observed["y"] = observed["room_nights"].astype(float)
    history = observed[["hotel_key", "week_start_date", "y"]].sort_values(
        ["hotel_key", "week_start_date"]
    )

    last_weeks = history.groupby("hotel_key")["week_start_date"].max()
    if last_weeks.nunique() != 1:
        raise ValueError(f"Hotels end at different weeks: {last_weeks.to_dict()}")
    for hotel_key, grp in history.groupby("hotel_key"):
        gaps = grp["week_start_date"].diff().dropna()
        if not (gaps.dt.days == 7).all():
            raise ValueError(f"The weekly series of hotel_key={hotel_key} has a gap")
    return history.reset_index(drop=True), calendar, last_weeks.iloc[0]


def lag_value(past: Sequence[float], k: int) -> float:
    """Value k weeks before the target week (past[-1] is the week just before). NaN if missing."""
    return float(past[-k]) if len(past) >= k else math.nan


def _mean(values: Sequence[float]) -> float:
    arr = np.asarray(values, dtype=float)
    return float(arr.mean()) if arr.size and not np.isnan(arr).any() else math.nan


def feature_row(past: Sequence[float], is_resort: int, iso_week: int, n_holidays: int) -> dict:
    """Features for 1 target week, using only values BEFORE that week (`past`).

    - lag_1, lag_2, ma_4: recent level (in multi-step forecasts, the tail of `past` is forecasts).
    - lag_52, seasonal_3: same week last year and the mean of the 3 weeks around it (less noise).
    - yoy_level: current ma_4 / ma_4 of the same period last year (year-over-year trend).
    - seasonal_adj = seasonal_3 × yoy_level: last year's seasonality adjusted to the current level.
    """
    ma_4 = _mean(past[-4:]) if len(past) >= 4 else math.nan
    seasonal_3 = (
        _mean([lag_value(past, 53), lag_value(past, 52), lag_value(past, 51)])
        if len(past) >= 53
        else math.nan
    )
    last_year_ma_4 = _mean(past[-56:-52]) if len(past) >= 56 else math.nan
    yoy_level = ma_4 / last_year_ma_4 if last_year_ma_4 > 0 else math.nan
    return {
        "is_resort": int(is_resort),
        "iso_week": int(iso_week),
        "n_holidays": int(n_holidays),
        "lag_1": lag_value(past, 1),
        "lag_2": lag_value(past, 2),
        "ma_4": ma_4,
        "lag_52": lag_value(past, SEASON_LAG),
        "seasonal_3": seasonal_3,
        "yoy_level": yoy_level,
        "seasonal_adj": seasonal_3 * yoy_level,
    }


def build_training_matrix(
    history: pd.DataFrame, calendar: pd.DataFrame, resort_keys: set[int]
) -> tuple[pd.DataFrame, np.ndarray]:
    """Training matrix pooling all hotels: each week (from week MIN_PAST_WEEKS+1) is 1 row."""
    rows: list[dict] = []
    targets: list[float] = []
    for hotel_key, grp in history.groupby("hotel_key"):
        values = grp["y"].tolist()
        weeks = grp["week_start_date"].tolist()
        for i in range(MIN_PAST_WEEKS, len(values)):
            cal = calendar.loc[weeks[i]]
            rows.append(
                feature_row(
                    values[:i], int(hotel_key in resort_keys), cal["iso_week"], cal["n_holidays"]
                )
            )
            targets.append(values[i])
    return pd.DataFrame(rows, columns=FEATURE_COLUMNS), np.asarray(targets, dtype=float)
