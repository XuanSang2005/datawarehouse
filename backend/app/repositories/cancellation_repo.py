"""Phân tích hủy (G2): tổng theo chiều (fact_booking), booking rủi ro (gold.ml_booking_risk)."""

from sqlalchemy import Connection, text

from app.repositories.booking_sql import (
    BOOKING_FROM,
    COUNTRY_CODE_SQL,
    LEAD_TIME_BAND_LABEL,
    LEAD_TIME_BAND_ORDER,
    build_where,
)
from app.schemas.common import BookingFilter

# (biểu thức key, biểu thức label, biểu thức thứ tự hoặc None = sắp theo số booking). Whitelist.
DIMENSION_SQL: dict[str, tuple[str, str, str | None]] = {
    "lead_time": (LEAD_TIME_BAND_LABEL, LEAD_TIME_BAND_LABEL, LEAD_TIME_BAND_ORDER),
    "channel": ("ch.channel_group", "ch.channel_group", None),
    "deposit_type": ("bp.deposit_type", "bp.deposit_type", None),
    "country": (COUNTRY_CODE_SQL, "co.country_name", None),
    "market_segment": ("ch.market_segment", "ch.market_segment", None),
    "customer_type": ("bp.customer_type", "bp.customer_type", None),
}

SORTS = {
    "probability": "r.cancel_probability DESC, f.booking_id",
    "expected_loss": "r.cancel_probability * f.booked_revenue DESC, f.booking_id",
}


def fetch_breakdown(conn: Connection, flt: BookingFilter, by: str) -> list[dict]:
    key_sql, label_sql, order_sql = DIMENSION_SQL[by]
    order_expr = f"min({order_sql})" if order_sql else "NULL::INT"
    where, params = build_where(flt)
    query = text(
        f"""
        SELECT {key_sql} AS key, min({label_sql}) AS label, {order_expr} AS band_order,
               sum(f.booking_count)::BIGINT AS bookings,
               sum(f.is_canceled)::BIGINT   AS canceled_bookings,
               coalesce(sum(f.lost_revenue), 0)     AS lost_revenue,
               coalesce(sum(f.net_lost_revenue), 0) AS net_lost_revenue
        {BOOKING_FROM}
        {where}
        GROUP BY 1
        """
    )
    return [dict(r) for r in conn.execute(query, params).mappings()]


def _risk_where(
    flt: BookingFilter, model_version: str, risk_band: str | None, test_set_only: bool
) -> tuple[str, dict]:
    extra = ["r.model_version = :model_version"]
    if risk_band is not None:
        extra.append("r.risk_band = :risk_band")
    if test_set_only:
        extra.append("r.is_test_set")
    where, params = build_where(flt, extra)
    params["model_version"] = model_version
    if risk_band is not None:
        params["risk_band"] = risk_band
    return where, params


RISK_FROM = f"""
    {BOOKING_FROM}
    JOIN gold.dim_date        AS bd ON bd.date_key = f.booking_date_key
    JOIN gold.ml_booking_risk AS r  ON r.booking_id = f.booking_id
"""


def count_high_risk(
    conn: Connection,
    flt: BookingFilter,
    model_version: str,
    risk_band: str | None,
    test_set_only: bool,
) -> int:
    where, params = _risk_where(flt, model_version, risk_band, test_set_only)
    return int(conn.execute(text(f"SELECT count(*) {RISK_FROM} {where}"), params).scalar() or 0)


def fetch_high_risk(
    conn: Connection,
    flt: BookingFilter,
    model_version: str,
    risk_band: str | None,
    test_set_only: bool,
    sort: str,
    limit: int,
    offset: int,
) -> list[dict]:
    where, params = _risk_where(flt, model_version, risk_band, test_set_only)
    query = text(
        f"""
        SELECT f.booking_id, h.hotel_key, h.hotel_name,
               ad.full_date AS arrival_date, bd.full_date AS booking_date,
               f.lead_time, f.total_nights, f.guests, f.adr, f.booked_revenue,
               ch.channel_group, ch.market_segment, {COUNTRY_CODE_SQL} AS country_code,
               bp.deposit_type, bp.customer_type,
               f.total_of_special_requests, f.previous_cancellations,
               r.cancel_probability, r.risk_band,
               r.cancel_probability * f.booked_revenue AS expected_loss,
               r.is_test_set, f.is_canceled = 1 AS is_canceled
        {RISK_FROM}
        {where}
        ORDER BY {SORTS[sort]}
        LIMIT :limit OFFSET :offset
        """
    )
    return [
        dict(r)
        for r in conn.execute(query, {**params, "limit": limit, "offset": offset}).mappings()
    ]
