"""Kiểm tra chống data leakage của mô hình dự đoán hủy (không cần DB)."""

import re
from datetime import date

import pandas as pd

from ml.cancellation.features import (
    CATEGORICAL_FEATURES,
    FEATURES,
    FEATURES_SQL,
    ID_COLUMN,
    LEAKAGE_COLUMNS,
    NUMERIC_FEATURES,
    SPLIT_DATE_COLUMN,
    TARGET,
    TEST_START,
    build_features,
    in_test_period,
    in_validation_period,
)

# Cột cấm theo comment đầu database/gold/30_fact_booking.sql và quy tắc 7 CLAUDE.md.
MUST_EXCLUDE = {
    "reservation_status",
    "reservation_status_date",
    "status_date_key",
    "room_nights_sold",
    "realized_revenue",
    "lost_revenue",
    "deposit_retained",
    "net_lost_revenue",
    "cancel_lead_days",
    "assigned_room_type",
    "assigned_room_type_key",
    "is_room_changed",
    "booking_changes",
    "days_in_waiting_list",
}


def _sample_raw(n: int = 4) -> pd.DataFrame:
    """Dữ liệu giả có đủ cột của SELECT + thêm toàn bộ cột cấm."""
    data = {
        ID_COLUMN: range(1, n + 1),
        TARGET: [0, 1] * (n // 2),
        SPLIT_DATE_COLUMN: pd.to_datetime(["2016-03-01", "2016-08-15", "2017-01-01", "2017-05-02"]),
        "hotel_name": ["City Hotel", "Resort Hotel"] * (n // 2),
        "arrival_day_of_week": [2, 1, 7, 2],
        "arrival_season": ["Low", "High", "Low", "Shoulder"],
        "arrival_is_holiday": [False, True, True, False],
        "lead_time": [10, 0, 200, 35],
        "weekend_nights": [1, 0, 2, 0],
        "week_nights": [2, 1, 5, 0],
        "total_nights": [3, 1, 7, 0],
        "adults": [2, 1, 0, 2],
        "children": [0, 0, 0, 1],
        "babies": [0, 0, 1, 0],
        "market_segment": ["Online TA", "Direct", None, "Groups"],
        "distribution_channel": ["TA/TO", "Direct", None, "TA/TO"],
        "agent_id": [9.0, None, 240.0, None],
        "company_id": [None, None, 40.0, None],
        "country_code": ["PRT", "GBR", None, "FRA"],
        "market_group": ["Domestic", "Core Europe", "Unknown", "Core Europe"],
        "meal": ["BB", "HB", "SC", "BB"],
        "deposit_type": ["No Deposit", "Non Refund", "Refundable", "No Deposit"],
        "customer_type": ["Transient", "Contract", "Group", "Transient-Party"],
        "is_repeated_guest": [False, True, False, False],
        "party_type": ["Couple", "Solo", "Other", "Family"],
        "previous_cancellations": [0, 1, 0, 0],
        "previous_bookings_not_canceled": [0, 3, 0, 0],
        "reserved_room_type": ["A", "D", "A", "E"],
        "adr": [100.0, 80.0, 0.0, 120.0],
        "total_of_special_requests": [0, 2, 0, 1],
    }
    df = pd.DataFrame(data)
    for col in LEAKAGE_COLUMNS:
        if col not in df.columns:
            df[col] = 1
    return df


def test_no_leakage_column_in_feature_set():
    assert MUST_EXCLUDE <= set(LEAKAGE_COLUMNS), "Thiếu lý do loại bỏ cho cột cấm"
    leaked = set(FEATURES) & set(LEAKAGE_COLUMNS)
    assert not leaked, f"Cột leakage nằm trong feature set: {leaked}"
    assert TARGET not in FEATURES and ID_COLUMN not in FEATURES
    assert SPLIT_DATE_COLUMN not in FEATURES


def test_feature_lists_are_disjoint_and_unique():
    assert not set(CATEGORICAL_FEATURES) & set(NUMERIC_FEATURES)
    assert len(FEATURES) == len(set(FEATURES))


def test_build_features_drops_leakage_columns():
    raw = _sample_raw()
    out = build_features(raw)
    assert list(out.columns) == FEATURES
    assert not set(out.columns) & set(LEAKAGE_COLUMNS)
    assert len(out) == len(raw)


def test_build_features_handles_missing_and_derived_values():
    out = build_features(_sample_raw())
    assert out["agent_id"].tolist() == ["9", "None", "240", "None"]
    assert out["country_code"].iloc[2] == "Unknown"
    assert out["market_segment"].iloc[2] == "Unknown"
    # booking_month = tháng của (arrival_date - lead_time): 2016-03-01 - 10 ngày = tháng 2
    assert out["booking_month"].tolist() == [2.0, 8.0, 6.0, 3.0]
    # adr_per_person: không có người trả tiền (adults + children = 0) thì chia cho 1
    assert out["adr_per_person"].tolist() == [50.0, 80.0, 0.0, 40.0]
    assert out[CATEGORICAL_FEATURES].isna().sum().sum() == 0


def test_features_sql_does_not_select_leakage_columns():
    sql = FEATURES_SQL.read_text(encoding="utf-8")
    code = "\n".join(line.split("--", 1)[0] for line in sql.splitlines())  # bỏ comment
    tokens = set(re.findall(r"[a-z_]+", code.lower()))
    selected_leakage = (set(LEAKAGE_COLUMNS) - {TARGET, ID_COLUMN, SPLIT_DATE_COLUMN}) & tokens
    assert not selected_leakage, f"File SQL nhắc tới cột cấm: {selected_leakage}"


def test_time_split():
    raw = _sample_raw()
    assert TEST_START == date(2017, 1, 1)
    assert in_test_period(raw).tolist() == [False, False, True, True]
    assert in_validation_period(raw).tolist() == [False, True, False, False]
