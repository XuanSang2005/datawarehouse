"""Đọc dữ liệu và dựng feature cho mô hình dự đoán hủy.

Nguyên tắc: feature chỉ gồm thông tin BIẾT ĐƯỢC TẠI THỜI ĐIỂM ĐẶT PHÒNG (quy tắc 7 CLAUDE.md).
Câu SELECT nằm ở database/ml/21_cancellation_features.sql (quy tắc 1: SQL chỉ nằm trong database/).
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from etl.config import DATABASE_DIR

FEATURES_SQL: Path = DATABASE_DIR / "ml" / "21_cancellation_features.sql"

ID_COLUMN = "booking_id"
TARGET = "is_canceled"
SPLIT_DATE_COLUMN = "arrival_date"
# Chia theo thời gian (docs/STAR_SCHEMA.md mục 7): train arrival < 2017-01-01, test = năm 2017.
TEST_START = date(2017, 1, 1)
# Tập validation (để chọn ngưỡng risk band) = 6 tháng cuối của tập train.
VALIDATION_START = date(2016, 7, 1)

# Cột KHÔNG được dùng làm feature, kèm lý do. Gồm:
#   (a) cột suy ra từ KẾT QUẢ hủy (comment đầu database/gold/30_fact_booking.sql),
#   (b) cột chỉ biết/được cập nhật SAU thời điểm đặt phòng,
#   (c) nhãn, khóa, cột dùng để chia tập.
LEAKAGE_COLUMNS: dict[str, str] = {
    # (a) Kết quả booking: chứa thẳng đáp án
    "reservation_status": "Trạng thái cuối (Canceled/No-Show/Check-Out): chính là nhãn.",
    "reservation_status_date": "Ngày hủy hoặc ngày trả phòng: chỉ có sau khi biết kết quả.",
    "status_date_key": "Khóa ngày của reservation_status_date.",
    "room_nights_sold": "= 0 khi hủy: suy ra từ is_canceled.",
    "realized_revenue": "= 0 khi hủy: suy ra từ is_canceled.",
    "lost_revenue": "> 0 chỉ khi hủy: suy ra từ is_canceled.",
    "deposit_retained": "> 0 chỉ khi hủy: suy ra từ is_canceled.",
    "net_lost_revenue": "> 0 chỉ khi hủy: suy ra từ is_canceled.",
    "cancel_lead_days": "Chỉ có giá trị khi hủy.",
    # (b) Thông tin phát sinh sau khi đặt
    "assigned_room_type": "Phòng thực nhận, gán lúc check-in; booking hủy thường giữ nguyên"
    " phòng đặt, nên chênh lệch với phòng đặt gần như chỉ xảy ra với khách đã đến.",
    "assigned_room_type_key": "Khóa của assigned_room_type.",
    "is_room_changed": "Suy ra từ assigned_room_type.",
    "booking_changes": "Đếm số lần sửa booking cho tới lúc check-in hoặc hủy: tích lũy sau"
    " thời điểm đặt, booking ở lâu trong hệ thống (thường là không hủy) có nhiều lần sửa hơn.",
    "days_in_waiting_list": "Số ngày chờ xác nhận: chỉ chốt sau ngày nhập booking, và giá trị"
    " lớn đi kèm nhóm booking đoàn được xử lý thủ công; không chắc có tại lúc chấm điểm.",
    "required_car_parking_spaces": "EDA: 7.409 booking có chỗ đỗ xe > 0 thì tỉ lệ hủy đúng 0%."
    " Một nhu cầu đặt trước không thể dự báo hoàn hảo như vậy, nên nhiều khả năng cột được"
    " ghi nhận lúc check-in (chỉ khách đã đến mới có).",
    # (c) Nhãn, khóa, cột chia tập
    "is_canceled": "Nhãn cần dự đoán.",
    "booking_id": "Khóa định danh, không mang thông tin.",
    "arrival_date": "Chỉ dùng để chia train/test theo thời gian (tháng/tuần/thứ vẫn là feature).",
    "arrival_date_year": "Năm đến: mô hình không ngoại suy được sang năm chưa thấy.",
}

# Feature dạng phân loại (chuỗi). NULL được thay bằng 'Unknown' / 'None'.
CATEGORICAL_FEATURES: list[str] = [
    "hotel_name",
    "arrival_season",
    "market_segment",
    "distribution_channel",
    "agent_id",
    "company_id",
    "country_code",
    "market_group",
    "meal",
    "deposit_type",
    "customer_type",
    "party_type",
    "reserved_room_type",
]

# Feature dạng số (gồm cờ 0/1).
# Cố ý KHÔNG dùng tháng/tuần đến (arrival_month, arrival_week): mỗi tháng chỉ có 1-2 năm dữ liệu
# nên mô hình học thuộc mẫu hủy của đúng năm đó (vd khối booking đoàn hủy hàng loạt trong một tuần),
# AUC validation tăng 0,844 → 0,876 khi bỏ. Mùa vụ vẫn có qua arrival_season và booking_month.
NUMERIC_FEATURES: list[str] = [
    "lead_time",
    "arrival_day_of_week",
    "arrival_is_holiday",
    "booking_month",
    "weekend_nights",
    "week_nights",
    "total_nights",
    "adults",
    "children",
    "babies",
    "is_repeated_guest",
    "previous_cancellations",
    "previous_bookings_not_canceled",
    "adr",
    "adr_per_person",
    "total_of_special_requests",
]

FEATURES: list[str] = CATEGORICAL_FEATURES + NUMERIC_FEATURES

# Cột quốc gia: ⚠ cân nhắc (xem ml/README.md). train.py chạy thêm 1 model bỏ nhóm này để so sánh.
COUNTRY_FEATURES: list[str] = ["country_code", "market_group"]


def load_dataset(conn) -> pd.DataFrame:
    """Đọc toàn bộ booking của gold.fact_booking (kèm dimension) bằng câu SELECT FEATURES_SQL."""
    sql = FEATURES_SQL.read_text(encoding="utf-8")
    with conn.cursor() as cur:
        cur.execute(sql)
        columns = [c.name for c in cur.description]
        rows = cur.fetchall()
    df = pd.DataFrame(rows, columns=columns)
    df[SPLIT_DATE_COLUMN] = pd.to_datetime(df[SPLIT_DATE_COLUMN])
    return df


def _as_category_text(series: pd.Series, missing: str) -> pd.Series:
    """Chuẩn hóa cột phân loại về chuỗi; mã số (agent_id, company_id) bỏ phần '.0'."""

    def to_text(value) -> str:
        if value is None or pd.isna(value):
            return missing
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return str(value)

    return series.map(to_text).astype(str)


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Trả về DataFrame CHỈ gồm các cột trong FEATURES (đúng thứ tự). Mọi cột khác bị bỏ."""
    out = pd.DataFrame(index=df.index)
    missing_label = {"agent_id": "None", "company_id": "None"}
    for col in CATEGORICAL_FEATURES:
        if col in df.columns:
            out[col] = _as_category_text(df[col], missing_label.get(col, "Unknown"))

    for col in NUMERIC_FEATURES:
        if col in df.columns:
            out[col] = pd.to_numeric(df[col], errors="coerce").astype(float)

    # Feature suy ra (đều từ thông tin lúc đặt):
    #   booking_month : tháng khách đặt phòng = tháng của (arrival_date - lead_time)
    #   adr_per_person: giá mỗi đêm chia cho số người lớn + trẻ em (em bé không tính)
    booking_date = df[SPLIT_DATE_COLUMN] - pd.to_timedelta(df["lead_time"], unit="D")
    out["booking_month"] = booking_date.dt.month.astype(float)
    payers = (df["adults"] + df["children"]).where(lambda s: s > 0, 1)
    out["adr_per_person"] = (df["adr"].astype(float) / payers).astype(float)

    return out[FEATURES]


def in_test_period(df: pd.DataFrame) -> pd.Series:
    """True nếu booking thuộc tập test (đến từ 2017-01-01)."""
    return df[SPLIT_DATE_COLUMN] >= pd.Timestamp(TEST_START)


def in_validation_period(df: pd.DataFrame) -> pd.Series:
    """True nếu booking thuộc tập validation (6 tháng cuối của tập train)."""
    arrival = df[SPLIT_DATE_COLUMN]
    return (arrival >= pd.Timestamp(VALIDATION_START)) & (arrival < pd.Timestamp(TEST_START))
