"""Load data and build features for the cancellation prediction model.

Principle: features only contain information KNOWN AT BOOKING TIME (rule 7 of CLAUDE.md).
The SELECT lives in database/ml/21_cancellation_features.sql (rule 1: SQL only lives in database/).
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
# Time-based split (docs/STAR_SCHEMA.md section 7): train arrival < 2017-01-01, test = year 2017.
TEST_START = date(2017, 1, 1)
# Validation set (used to pick the risk band thresholds) = last 6 months of the train set.
VALIDATION_START = date(2016, 7, 1)

# Columns that must NOT be used as features, with the reason. They are:
#   (a) columns derived from the cancellation OUTCOME (header of database/gold/30_fact_booking.sql),
#   (b) columns only known/updated AFTER booking time,
#   (c) the label, keys, and the split column.
LEAKAGE_COLUMNS: dict[str, str] = {
    # (a) Booking outcome: contains the answer directly
    "reservation_status": "Final status (Canceled/No-Show/Check-Out): it is the label itself.",
    "reservation_status_date": "Cancellation or check-out date: only exists after the outcome.",
    "status_date_key": "Date key of reservation_status_date.",
    "room_nights_sold": "= 0 when canceled: derived from is_canceled.",
    "realized_revenue": "= 0 when canceled: derived from is_canceled.",
    "lost_revenue": "> 0 only when canceled: derived from is_canceled.",
    "deposit_retained": "> 0 only when canceled: derived from is_canceled.",
    "net_lost_revenue": "> 0 only when canceled: derived from is_canceled.",
    "cancel_lead_days": "Only has a value when canceled.",
    # (b) Information that arises after booking
    "assigned_room_type": "Room actually given, assigned at check-in; canceled bookings usually"
    " keep the reserved room, so a difference from it almost only occurs for guests who arrived.",
    "assigned_room_type_key": "Key of assigned_room_type.",
    "is_room_changed": "Derived from assigned_room_type.",
    "booking_changes": "Counts booking modifications up to check-in or cancellation: accumulates"
    " after booking; bookings that stay longer in the system (usually not canceled) change more.",
    "days_in_waiting_list": "Days waiting for confirmation: only settled after the booking entry"
    " date; large values go with manually handled group bookings; not reliable at scoring time.",
    "required_car_parking_spaces": "EDA: the 7,409 bookings with parking spaces > 0 have exactly 0%"
    " cancellation rate. A pre-booked need cannot be that perfectly predictive, so the column is"
    " most likely recorded at check-in (only guests who arrived have it).",
    # (c) Label, keys, split column
    "is_canceled": "The label to predict.",
    "booking_id": "Identifier, carries no information.",
    "arrival_date": "Only for the time-based train/test split (month/week/weekday stay features).",
    "arrival_date_year": "Arrival year: the model cannot extrapolate to unseen years.",
}

# Categorical (string) features. NULL is replaced by 'Unknown' / 'None'.
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

# Numeric features (including 0/1 flags).
# Arrival month/week (arrival_month, arrival_week) are deliberately NOT used: each month only has
# 1-2 years of data, so the model memorizes that year's cancellation pattern (e.g. a block of group
# bookings canceled in one week); validation AUC rose 0.844 → 0.876 when they were dropped.
# Seasonality is still captured by arrival_season and booking_month.
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

# Country columns: ⚠ debatable (see ml/README.md). train.py also runs a model without them.
COUNTRY_FEATURES: list[str] = ["country_code", "market_group"]


def load_dataset(conn) -> pd.DataFrame:
    """Load every booking of gold.fact_booking (with dimensions) using the FEATURES_SQL SELECT."""
    sql = FEATURES_SQL.read_text(encoding="utf-8")
    with conn.cursor() as cur:
        cur.execute(sql)
        columns = [c.name for c in cur.description]
        rows = cur.fetchall()
    df = pd.DataFrame(rows, columns=columns)
    df[SPLIT_DATE_COLUMN] = pd.to_datetime(df[SPLIT_DATE_COLUMN])
    return df


def _as_category_text(series: pd.Series, missing: str) -> pd.Series:
    """Normalize a categorical column to text; numeric codes (agent_id, company_id) lose '.0'."""

    def to_text(value) -> str:
        if value is None or pd.isna(value):
            return missing
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return str(value)

    return series.map(to_text).astype(str)


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Return a DataFrame with ONLY the FEATURES columns (in order); all others are dropped."""
    out = pd.DataFrame(index=df.index)
    missing_label = {"agent_id": "None", "company_id": "None"}
    for col in CATEGORICAL_FEATURES:
        if col in df.columns:
            out[col] = _as_category_text(df[col], missing_label.get(col, "Unknown"))

    for col in NUMERIC_FEATURES:
        if col in df.columns:
            out[col] = pd.to_numeric(df[col], errors="coerce").astype(float)

    # Derived features (all from booking-time information):
    #   booking_month : month the guest booked = month of (arrival_date - lead_time)
    #   adr_per_person: nightly rate divided by adults + children (babies not counted)
    booking_date = df[SPLIT_DATE_COLUMN] - pd.to_timedelta(df["lead_time"], unit="D")
    out["booking_month"] = booking_date.dt.month.astype(float)
    payers = (df["adults"] + df["children"]).where(lambda s: s > 0, 1)
    out["adr_per_person"] = (df["adr"].astype(float) / payers).astype(float)

    return out[FEATURES]


def in_test_period(df: pd.DataFrame) -> pd.Series:
    """True if the booking belongs to the test set (arrivals from 2017-01-01)."""
    return df[SPLIT_DATE_COLUMN] >= pd.Timestamp(TEST_START)


def in_validation_period(df: pd.DataFrame) -> pd.Series:
    """True if the booking belongs to the validation set (last 6 months of the train set)."""
    arrival = df[SPLIT_DATE_COLUMN]
    return (arrival >= pd.Timestamp(VALIDATION_START)) & (arrival < pd.Timestamp(TEST_START))
