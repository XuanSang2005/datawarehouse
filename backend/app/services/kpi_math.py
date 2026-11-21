"""Non-additive KPI calculations from totals (rule 8). Shared by all services.

Every rate/average = sum of numerators / sum of denominators, NEVER an average of sub-rates.
Denominator = 0 → None (the frontend shows "—").
"""

from collections.abc import Mapping
from decimal import Decimal

from app.schemas.common import KpiValues


def ratio(
    numerator: float | Decimal | int | None, denominator: float | Decimal | int | None
) -> float | None:
    if numerator is None or not denominator:
        return None
    return float(numerator) / float(denominator)


def to_float(value: float | Decimal | int | None) -> float:
    return float(value) if value is not None else 0.0


def kpi_from_sums(row: Mapping) -> KpiValues:
    """Build KpiValues from a row with the columns of booking_sql.KPI_SUMS."""
    bookings = int(row["bookings"] or 0)
    room_nights = int(row["room_nights_sold"] or 0)
    realized = to_float(row["realized_revenue"])
    return KpiValues(
        bookings=bookings,
        canceled_bookings=int(row["canceled_bookings"] or 0),
        cancellation_rate=ratio(row["canceled_bookings"], bookings),
        room_nights_sold=room_nights,
        realized_revenue=realized,
        lost_revenue=to_float(row["lost_revenue"]),
        net_lost_revenue=to_float(row["net_lost_revenue"]),
        adr=ratio(realized, room_nights),
        avg_lead_time=ratio(row["sum_lead_time"], bookings),
        avg_los=ratio(row["sum_total_nights"], bookings),
    )
