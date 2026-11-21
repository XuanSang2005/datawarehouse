"""Unit test cho baseline, MAPE, khoảng dự báo và backtest của ml/forecast (không cần DB)."""

import math
from datetime import timedelta

import numpy as np
import pandas as pd
import pytest

from ml.forecast.backtest import apply_interval, residual_quantiles, rolling_origin, summarize
from ml.forecast.models import (
    GbmForecaster,
    PerHotelBaseline,
    mape,
    moving_average,
    seasonal_naive,
)


def make_series(n_weeks: int = 70, hotels=(1, 2)) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Chuỗi tổng hợp có mùa vụ 52 tuần + lịch dư 20 tuần cho dự báo tương lai."""
    weeks = pd.date_range("2015-07-06", periods=n_weeks + 20, freq="7D")
    calendar = pd.DataFrame(
        {"iso_week": weeks.isocalendar().week.astype(int).to_numpy(), "n_holidays": 0},
        index=weeks,
    )
    rows = []
    for hk in hotels:
        for i, w in enumerate(weeks[:n_weeks]):
            rows.append({"hotel_key": hk, "week_start_date": w,
                         "y": 1000 + 200 * math.sin(2 * math.pi * i / 52) + 50 * hk})
    return pd.DataFrame(rows), calendar


def test_mape_basic():
    assert mape([100, 200], [110, 180]) == pytest.approx((0.1 + 0.1) / 2)
    assert mape([50], [50]) == 0.0


def test_mape_rejects_zero_actual_and_bad_shapes():
    with pytest.raises(ValueError):
        mape([0, 10], [1, 10])
    with pytest.raises(ValueError):
        mape([1, 2], [1])
    with pytest.raises(ValueError):
        mape([], [])


def test_seasonal_naive_uses_same_week_last_year():
    past = list(range(100))  # tuần cuối = 99 → tuần +1 ứng với chỉ số 100 − 52 = 48
    assert seasonal_naive(past, 3) == [48.0, 49.0, 50.0]


def test_seasonal_naive_nan_when_history_short():
    past = list(range(50))  # h=1 cần chỉ số −2 → NaN; h=3 cần chỉ số 0
    out = seasonal_naive(past, 3)
    assert math.isnan(out[0]) and math.isnan(out[1]) and out[2] == 0.0


def test_seasonal_naive_rejects_horizon_above_season():
    with pytest.raises(ValueError):
        seasonal_naive(list(range(200)), 53)


def test_moving_average_flat_forecast():
    assert moving_average([1, 2, 3, 4, 5, 6], 3, window=4) == [4.5, 4.5, 4.5]
    with pytest.raises(ValueError):
        moving_average([1, 2], 1, window=4)


def test_per_hotel_baseline_dates_and_horizon():
    history, calendar = make_series(60)
    fc = PerHotelBaseline("ma", moving_average).forecast(history, calendar, 3)
    assert len(fc) == 6
    last = history["week_start_date"].max()
    assert fc["week_start_date"].min() == last + timedelta(days=7)
    assert fc["week_start_date"].max() == last + timedelta(days=21)
    assert sorted(fc["h"].unique()) == [1, 2, 3]


def test_residual_quantiles_and_interval_contain_forecast():
    bt = pd.DataFrame({"h": [1] * 10, "yhat": [100.0] * 10,
                       "actual": np.linspace(80, 120, 10)})
    q = residual_quantiles(bt, coverage=0.8)
    assert q.loc[1, "q_low"] < 0 < q.loc[1, "q_high"]
    fc = pd.DataFrame({"h": [1], "yhat": [200.0]})
    out = apply_interval(fc, q)
    assert out["lower_bound"].iloc[0] <= 200.0 <= out["upper_bound"].iloc[0]
    with pytest.raises(ValueError):
        apply_interval(pd.DataFrame({"h": [2], "yhat": [1.0]}), q)


def test_residual_quantiles_one_sided_errors_still_bracket_forecast():
    bt = pd.DataFrame({"h": [1] * 5, "yhat": [100.0] * 5, "actual": [110.0] * 5})
    q = residual_quantiles(bt)
    assert q.loc[1, "q_low"] == 0.0 and q.loc[1, "q_high"] > 0


def test_rolling_origin_one_forecast_per_week_and_horizon():
    history, calendar = make_series(70)
    start = history["week_start_date"].iloc[60]
    end = history["week_start_date"].iloc[65]
    bt = rolling_origin(PerHotelBaseline("sn", seasonal_naive), history, calendar, start, end, 4)
    # 6 tuần mục tiêu × 4 horizon × 2 khách sạn
    assert len(bt) == 6 * 4 * 2
    assert not bt.duplicated(["hotel_key", "week_start_date", "h"]).any()
    # Không nhìn trước: tuần gốc luôn trước tuần mục tiêu đúng h tuần
    assert ((bt["week_start_date"] - bt["origin"]).dt.days == bt["h"] * 7).all()
    # Chuỗi tuần hoàn đúng 52 tuần → seasonal naive gần như hoàn hảo
    assert mape(bt["actual"], bt["yhat"]) < 1e-9
    metrics = summarize(bt, {1: "City Hotel", 2: "Resort Hotel"})
    assert {"mape", "mape_h1", "mape_h4", "mape_city_hotel", "mape_h1_resort_hotel"} <= set(metrics)


def test_gbm_forecaster_runs_and_is_reasonable():
    history, calendar = make_series(70)
    gbm = GbmForecaster(resort_keys={2}, params={"max_iter": 50, "random_state": 0})
    fc = gbm.forecast(history, calendar, 4)
    assert len(fc) == 8 and (fc["yhat"] > 0).all()
    assert fc["yhat"].between(500, 1600).all()
