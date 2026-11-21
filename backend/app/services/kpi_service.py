"""Overview KPIs (G1): aggregates by filter, hotel comparison, drill-down time series."""

from sqlalchemy import Connection

from app.repositories import kpi_repo
from app.schemas.common import BookingFilter
from app.schemas.kpi import Grain, HotelKpi, KpiPoint, KpiSummary, KpiTimeseries
from app.services.kpi_math import kpi_from_sums

SUM_COLUMNS = (
    "bookings",
    "canceled_bookings",
    "room_nights_sold",
    "realized_revenue",
    "lost_revenue",
    "net_lost_revenue",
    "sum_lead_time",
    "sum_total_nights",
)


def combine_sums(rows: list[dict]) -> dict:
    """Add up the (additive) TOTALS of several groups into an overall total, then compute rates."""
    return {col: sum((r[col] or 0) for r in rows) for col in SUM_COLUMNS}


def get_summary(conn: Connection, flt: BookingFilter) -> KpiSummary:
    rows = kpi_repo.fetch_summary_by_hotel(conn, flt)
    by_hotel = [
        HotelKpi(
            hotel_key=r["hotel_key"], hotel_name=r["hotel_name"], **kpi_from_sums(r).model_dump()
        )
        for r in rows
    ]
    return KpiSummary(filters=flt, total=kpi_from_sums(combine_sums(rows)), by_hotel=by_hotel)


def get_timeseries(
    conn: Connection, flt: BookingFilter, grain: Grain, by_hotel: bool
) -> KpiTimeseries:
    rows = kpi_repo.fetch_timeseries(conn, flt, grain, by_hotel)
    points = [
        KpiPoint(
            period=r["period"],
            period_start=r["period_start"],
            hotel_key=r.get("hotel_key"),
            hotel_name=r.get("hotel_name"),
            **kpi_from_sums(r).model_dump(),
        )
        for r in rows
    ]
    return KpiTimeseries(grain=grain, by_hotel=by_hotel, filters=flt, points=points)
