"""KPI tổng quan từ gold.fact_booking (thời gian = ngày đến).

Chỉ trả về các TỔNG; tỉ lệ tính ở service.
"""

from sqlalchemy import Connection, text

from app.repositories.booking_sql import BOOKING_FROM, KPI_SUMS, build_where
from app.schemas.common import BookingFilter

# Biểu thức kỳ theo grain (whitelist: không bao giờ nối chuỗi từ input người dùng vào SQL).
PERIOD_SQL: dict[str, tuple[str, str]] = {
    "year": ("ad.year::TEXT", "make_date(ad.year, 1, 1)"),
    "quarter": ("ad.year || '-Q' || ad.quarter", "make_date(ad.year, (ad.quarter - 1) * 3 + 1, 1)"),
    "month": ("ad.year_month", "make_date(ad.year, ad.month, 1)"),
    "week": ("ad.iso_year || '-W' || lpad(ad.iso_week::TEXT, 2, '0')", "ad.week_start_date"),
}


def fetch_summary_by_hotel(conn: Connection, flt: BookingFilter) -> list[dict]:
    where, params = build_where(flt)
    query = text(
        f"""
        SELECT h.hotel_key, h.hotel_name, {KPI_SUMS}
        {BOOKING_FROM}
        {where}
        GROUP BY h.hotel_key, h.hotel_name
        ORDER BY h.hotel_key
        """
    )
    return [dict(r) for r in conn.execute(query, params).mappings()]


def fetch_timeseries(
    conn: Connection, flt: BookingFilter, grain: str, by_hotel: bool
) -> list[dict]:
    label_sql, start_sql = PERIOD_SQL[grain]
    hotel_cols = "h.hotel_key, h.hotel_name," if by_hotel else ""
    hotel_group = ", h.hotel_key, h.hotel_name" if by_hotel else ""
    where, params = build_where(flt)
    query = text(
        f"""
        SELECT {label_sql} AS period, {start_sql} AS period_start, {hotel_cols} {KPI_SUMS}
        {BOOKING_FROM}
        {where}
        GROUP BY 1, 2 {hotel_group}
        ORDER BY 2 {", h.hotel_key" if by_hotel else ""}
        """
    )
    return [dict(r) for r in conn.execute(query, params).mappings()]
