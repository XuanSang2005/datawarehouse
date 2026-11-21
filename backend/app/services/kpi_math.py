"""Phép tính KPI non-additive từ các tổng (quy tắc 8). Dùng chung cho mọi service.

Mọi tỉ lệ/trung bình đều = tổng tử / tổng mẫu, KHÔNG lấy trung bình của các tỉ lệ con.
Mẫu số = 0 → None (frontend hiển thị "—").
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
    """Dựng KpiValues từ 1 dòng có các cột của booking_sql.KPI_SUMS."""
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
