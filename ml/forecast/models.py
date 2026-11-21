"""Weekly room-nights forecasting models: 2 baselines + Gradient Boosting.

Every forecaster has the same interface:
    forecast(history, calendar, horizon) -> DataFrame[hotel_key, h, week_start_date, yhat]
where `history` only contains data up to the origin week — the last week of each hotel —
and the forecast covers weeks origin+1 … origin+horizon. Models that learn are refit at each origin.
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
    """Mean Absolute Percentage Error as a RATIO (0.08 = 8%). Actual must be > 0."""
    a = np.asarray(actual, dtype=float)
    p = np.asarray(predicted, dtype=float)
    if a.shape != p.shape or a.size == 0:
        raise ValueError("actual and predicted must have the same length and not be empty")
    if (a <= 0).any():
        raise ValueError("MAPE is undefined when actual <= 0")
    return float(np.mean(np.abs(a - p) / a))


def seasonal_naive(past: Sequence[float], horizon: int, season: int = SEASON_LAG) -> list[float]:
    """Forecast for week origin+h = the value of the same week last year (`season` weeks back).

    NaN for the h where the history is not long enough yet (no "same week last year").
    """
    if horizon > season:
        raise ValueError("horizon must not exceed the seasonal period")
    n = len(past)
    out = []
    for h in range(1, horizon + 1):
        idx = n - season + h - 1
        out.append(float(past[idx]) if idx >= 0 else float("nan"))
    return out


def moving_average(past: Sequence[float], horizon: int, window: int = 4) -> list[float]:
    """Flat forecast = mean of the last `window` weeks (the same for every h)."""
    if len(past) < window:
        raise ValueError(f"At least {window} weeks of history are needed for the moving average")
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
    """Wraps 1 baseline function (seasonal_naive / moving_average) run separately per hotel."""

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
    """Gradient Boosting pooling both hotels; lag + seasonal + calendar features; recursive.

    Multi-step forecasts are recursive: forecast week origin+1, then feed it in as lag_1 for
    week origin+2, … Lags ≥ 52 weeks are always real values when horizon ≤ 51.
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
        """Fit the model; drop all-NaN columns (e.g. lag_52 with < 1 year of history early on)."""
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
