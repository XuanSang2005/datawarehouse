"""Chuẩn bị chuỗi tuần và tạo đặc trưng (feature) cho mô hình dự báo nhu cầu.

Quy ước dữ liệu dùng chung trong `ml/forecast/`:
- `history`: DataFrame dài, mỗi dòng = 1 khách sạn × 1 tuần ĐẦY ĐỦ 7 đêm, cột
  `hotel_key`, `week_start_date`, `y` (room-nights bán được). Các tuần liên tục, không hở.
- `calendar`: DataFrame index = `week_start_date` (mọi tuần, kể cả tương lai), cột
  `iso_week`, `n_holidays`.

Mọi hàm ở đây thuần (không đọc DB) để unit test được.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from datetime import timedelta

import numpy as np
import pandas as pd

SEASON_LAG = 52  # "cùng tuần năm trước" = lùi 52 tuần (364 ngày, cùng thứ trong tuần)
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
MIN_PAST_WEEKS = 4  # cần tối thiểu 4 tuần quá khứ để có ma_4


def prepare_series(raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.Timestamp]:
    """Tách dữ liệu đọc từ `database/ml/31_forecast_weekly_series.sql` thành history + calendar.

    - Chỉ giữ tuần đủ 7 đêm (`days_observed = 7`) làm dữ liệu quan sát. Tuần biên thiếu ngày
      (2015-06-29: 5 đêm, 2017-08-28: 4 đêm) bị loại: tổng room-nights của chúng thấp giả tạo.
    - Kiểm tra các tuần đầy đủ liên tục (lag theo vị trí mới đúng nghĩa).
    - Trả về thêm `last_week`: tuần đầy đủ cuối cùng (chung cho mọi khách sạn).
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
        raise ValueError(f"Các khách sạn kết thúc ở tuần khác nhau: {last_weeks.to_dict()}")
    for hotel_key, grp in history.groupby("hotel_key"):
        gaps = grp["week_start_date"].diff().dropna()
        if not (gaps.dt.days == 7).all():
            raise ValueError(f"Chuỗi tuần của hotel_key={hotel_key} bị hở giữa chừng")
    return history.reset_index(drop=True), calendar, last_weeks.iloc[0]


def lag_value(past: Sequence[float], k: int) -> float:
    """Giá trị lùi k tuần so với tuần cần dự báo (past[-1] là tuần ngay trước). NaN nếu thiếu."""
    return float(past[-k]) if len(past) >= k else math.nan


def _mean(values: Sequence[float]) -> float:
    arr = np.asarray(values, dtype=float)
    return float(arr.mean()) if arr.size and not np.isnan(arr).any() else math.nan


def feature_row(past: Sequence[float], is_resort: int, iso_week: int, n_holidays: int) -> dict:
    """Đặc trưng cho 1 tuần mục tiêu, chỉ dùng giá trị TRƯỚC tuần đó (`past`).

    - lag_1, lag_2, ma_4: mức gần đây (khi dự báo nhiều bước, phần đuôi của `past` là dự báo).
    - lag_52, seasonal_3: cùng tuần năm trước và trung bình 3 tuần quanh đó (giảm nhiễu).
    - yoy_level: tỉ lệ ma_4 hiện tại / ma_4 cùng kỳ năm trước (xu hướng tăng/giảm theo năm).
    - seasonal_adj = seasonal_3 × yoy_level: mùa vụ năm trước điều chỉnh theo mức hiện tại.
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
    """Ma trận train gộp mọi khách sạn: mỗi tuần (từ tuần thứ MIN_PAST_WEEKS+1) là 1 dòng."""
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
