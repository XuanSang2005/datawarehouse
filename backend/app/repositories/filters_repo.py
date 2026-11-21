"""Danh mục giá trị cho bộ lọc (chỉ đọc gold)."""

from sqlalchemy import Connection, text

from app.repositories.booking_sql import COUNTRY_CODE_SQL


def fetch_hotels(conn: Connection) -> list[dict]:
    query = text(
        """
        SELECT h.hotel_key, h.hotel_name, h.hotel_type, h.city,
               max(o.rooms_occupied) AS peak_rooms_occupied
        FROM gold.dim_hotel AS h
        LEFT JOIN gold.fact_daily_occupancy AS o ON o.hotel_key = h.hotel_key
        GROUP BY h.hotel_key, h.hotel_name, h.hotel_type, h.city
        ORDER BY h.hotel_key
        """
    )
    return [dict(r) for r in conn.execute(query).mappings()]


def fetch_channel_groups(conn: Connection) -> list[str]:
    query = text(
        """
        SELECT ch.channel_group
        FROM gold.fact_booking AS f
        JOIN gold.dim_channel AS ch ON ch.channel_key = f.channel_key
        GROUP BY ch.channel_group
        ORDER BY count(*) DESC
        """
    )
    return list(conn.execute(query).scalars())


def fetch_market_segments(conn: Connection) -> list[str]:
    query = text(
        """
        SELECT ch.market_segment
        FROM gold.fact_booking AS f
        JOIN gold.dim_channel AS ch ON ch.channel_key = f.channel_key
        GROUP BY ch.market_segment
        ORDER BY count(*) DESC
        """
    )
    return list(conn.execute(query).scalars())


def fetch_countries(conn: Connection) -> list[dict]:
    query = text(
        f"""
        SELECT {COUNTRY_CODE_SQL} AS country_code, co.country_name, co.market_group,
               count(*) AS bookings
        FROM gold.fact_booking AS f
        JOIN gold.dim_country AS co ON co.country_key = f.country_key
        GROUP BY 1, co.country_name, co.market_group
        ORDER BY bookings DESC, 1
        """
    )
    return [dict(r) for r in conn.execute(query).mappings()]


def fetch_arrival_date_range(conn: Connection) -> dict | None:
    query = text(
        """
        SELECT min(ad.full_date) AS min_date, max(ad.full_date) AS max_date
        FROM gold.fact_booking AS f
        JOIN gold.dim_date AS ad ON ad.date_key = f.arrival_date_key
        """
    )
    row = conn.execute(query).mappings().first()
    return dict(row) if row and row["min_date"] else None
