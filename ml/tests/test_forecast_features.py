"""Unit test cho chuẩn bị chuỗi tuần và tạo feature của ml/forecast (không cần DB)."""

import math

import pandas as pd
import pytest

from ml.forecast.features import (
    FEATURE_COLUMNS,
    MIN_PAST_WEEKS,
    build_training_matrix,
    feature_row,
    lag_value,
    prepare_series,
)


def raw_frame(days_observed: list[int], hotels=(1, 2)) -> pd.DataFrame:
    weeks = pd.date_range("2015-06-29", periods=len(days_observed), freq="7D")
    rows = []
    for hk in hotels:
        for i, (w, d) in enumerate(zip(weeks, days_observed, strict=True)):
            rows.append({
                "hotel_key": hk, "hotel_name": f"H{hk}", "hotel_type": "City",
                "week_start_date": w.date(), "iso_year": w.isocalendar().year,
                "iso_week": w.isocalendar().week, "n_holidays": int(i == 2),
                "room_nights": 100 + i if d else None, "days_observed": d,
            })
    return pd.DataFrame(rows)


def test_prepare_series_drops_partial_edge_weeks_and_keeps_calendar():
    raw = raw_frame([5, 7, 7, 7, 4, 0, 0])
    history, calendar, last_week = prepare_series(raw)
    # Tuần đầu (5 đêm), tuần cuối (4 đêm) và tuần tương lai (0 đêm) bị loại khỏi history
    assert len(history) == 2 * 3
    assert last_week == pd.Timestamp("2015-07-20")
    assert history["y"].tolist()[:3] == [101.0, 102.0, 103.0]
    # Lịch vẫn giữ mọi tuần (kể cả tương lai) để tạo feature
    assert len(calendar) == 7 and calendar["n_holidays"].sum() == 1


def test_prepare_series_rejects_gap_in_middle():
    with pytest.raises(ValueError, match="hở"):
        prepare_series(raw_frame([7, 7, 3, 7, 7]))


def test_lag_value():
    past = [10, 20, 30]
    assert lag_value(past, 1) == 30
    assert lag_value(past, 3) == 10
    assert math.isnan(lag_value(past, 4))


def test_feature_row_short_history_has_nan_seasonal_features():
    row = feature_row([1.0, 2.0, 3.0, 4.0, 5.0], is_resort=1, iso_week=10, n_holidays=1)
    assert list(row) == FEATURE_COLUMNS
    assert row["lag_1"] == 5.0 and row["lag_2"] == 4.0
    assert row["ma_4"] == pytest.approx(3.5)
    assert math.isnan(row["lag_52"]) and math.isnan(row["seasonal_3"])
    assert math.isnan(row["yoy_level"]) and math.isnan(row["seasonal_adj"])
    assert row["is_resort"] == 1 and row["iso_week"] == 10 and row["n_holidays"] == 1


def test_feature_row_seasonal_features():
    # 60 tuần: giá trị = chỉ số tuần (0..59). Tuần mục tiêu có chỉ số 60.
    past = [float(i) for i in range(60)]
    row = feature_row(past, is_resort=0, iso_week=1, n_holidays=0)
    assert row["lag_52"] == 8.0  # 60 − 52
    assert row["seasonal_3"] == pytest.approx((7 + 8 + 9) / 3)
    assert row["ma_4"] == pytest.approx((56 + 57 + 58 + 59) / 4)
    # ma_4 cùng kỳ năm trước = mean(past[-56:-52]) = mean(4..7)
    assert row["yoy_level"] == pytest.approx(57.5 / 5.5)
    assert row["seasonal_adj"] == pytest.approx(8.0 * 57.5 / 5.5)


def test_build_training_matrix_shape_and_no_lookahead():
    weeks = pd.date_range("2016-01-04", periods=10, freq="7D")
    history = pd.DataFrame({
        "hotel_key": [1] * 10 + [2] * 10,
        "week_start_date": list(weeks) * 2,
        "y": [float(i) for i in range(10)] + [float(100 + i) for i in range(10)],
    })
    calendar = pd.DataFrame({"iso_week": range(1, 11), "n_holidays": 0}, index=weeks)
    x, y = build_training_matrix(history, calendar, resort_keys={2})
    assert x.shape == (2 * (10 - MIN_PAST_WEEKS), len(FEATURE_COLUMNS))
    # lag_1 luôn là giá trị tuần TRƯỚC mục tiêu → không rò rỉ
    assert (x["lag_1"].to_numpy() == y - 1).all()
    assert x["is_resort"].tolist() == [0] * 6 + [1] * 6
