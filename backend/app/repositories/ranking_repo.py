"""Channel / market ranking (G5): totals by group from gold.fact_booking. Ranked in the service."""

from sqlalchemy import Connection, text

from app.repositories.booking_sql import BOOKING_FROM, COUNTRY_CODE_SQL, build_where
from app.schemas.common import BookingFilter

# (key, label, group) — whitelist
DIMENSION_SQL: dict[str, tuple[str, str, str]] = {
    "channel": ("ch.channel_group", "ch.channel_group", "NULL::TEXT"),
    "market": (COUNTRY_CODE_SQL, "co.country_name", "co.market_group"),
}


def fetch_groups(conn: Connection, flt: BookingFilter, dimension: str) -> list[dict]:
    key_sql, label_sql, group_sql = DIMENSION_SQL[dimension]
    where, params = build_where(flt)
    query = text(
        f"""
        SELECT {key_sql} AS key, min({label_sql}) AS label, min({group_sql}) AS grp,
               sum(f.booking_count)::BIGINT    AS bookings,
               sum(f.is_canceled)::BIGINT      AS canceled_bookings,
               sum(f.room_nights_sold)::BIGINT AS room_nights_sold,
               coalesce(sum(f.realized_revenue), 0) AS realized_revenue,
               coalesce(sum(f.lost_revenue), 0)     AS lost_revenue
        {BOOKING_FROM}
        {where}
        GROUP BY 1
        """
    )
    return [dict(r) for r in conn.execute(query, params).mappings()]
