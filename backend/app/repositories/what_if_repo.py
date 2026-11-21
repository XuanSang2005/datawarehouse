"""Data for the what-if simulation (G4). SELECT on gold only."""

from datetime import date

from sqlalchemy import Connection, text


def fetch_hotel_name(conn: Connection, hotel_key: int) -> str | None:
    return conn.execute(
        text("SELECT hotel_name FROM gold.dim_hotel WHERE hotel_key = :hotel_key"),
        {"hotel_key": hotel_key},
    ).scalar()


def fetch_assumption(conn: Connection, param_name: str) -> float | None:
    value = conn.execute(
        text("SELECT param_value FROM gold.business_assumptions WHERE param_name = :name"),
        {"name": param_name},
    ).scalar()
    return float(value) if value is not None else None


def fetch_nights(conn: Connection, hotel_key: int, date_from: date, date_to: date) -> list[dict]:
    """1 row per night: occupied rooms, canceled rooms, realized revenue of that night."""
    query = text(
        """
        SELECT d.full_date AS stay_date, o.rooms_occupied, o.rooms_canceled, o.realized_revenue
        FROM gold.fact_daily_occupancy AS o
        JOIN gold.dim_date AS d ON d.date_key = o.stay_date_key
        WHERE o.hotel_key = :hotel_key AND d.full_date BETWEEN :date_from AND :date_to
        ORDER BY d.full_date
        """
    )
    params = {"hotel_key": hotel_key, "date_from": date_from, "date_to": date_to}
    return [dict(r) for r in conn.execute(query, params).mappings()]


def fetch_revenue_by_channel(
    conn: Connection, hotel_key: int, date_from: date, date_to: date
) -> dict:
    """Total and OTA realized revenue of bookings arriving in the period (for the OTA share)."""
    query = text(
        """
        SELECT coalesce(sum(f.realized_revenue), 0) AS realized_revenue,
               coalesce(sum(f.realized_revenue) FILTER (WHERE ch.channel_group = 'OTA'), 0)
                   AS ota_revenue
        FROM gold.fact_booking AS f
        JOIN gold.dim_date    AS ad ON ad.date_key = f.arrival_date_key
        JOIN gold.dim_channel AS ch ON ch.channel_key = f.channel_key
        WHERE f.hotel_key = :hotel_key AND ad.full_date BETWEEN :date_from AND :date_to
        """
    )
    params = {"hotel_key": hotel_key, "date_from": date_from, "date_to": date_to}
    return dict(conn.execute(query, params).mappings().one())


def fetch_deposit_aggregates(
    conn: Connection,
    hotel_key: int,
    date_from: date,
    date_to: date,
    threshold: float,
    model_version: str,
) -> dict:
    """Totals for the 'deposit requested' group (probability >= threshold, not yet Non Refund)."""
    query = text(
        """
        WITH b AS (
            SELECT f.is_canceled, f.booked_revenue, f.realized_revenue, r.is_test_set,
                   ch.channel_group = 'OTA' AS is_ota,
                   r.cancel_probability >= :threshold AND bp.deposit_type <> 'Non Refund' AS flagged
            FROM gold.fact_booking AS f
            JOIN gold.dim_date            AS ad ON ad.date_key = f.arrival_date_key
            JOIN gold.dim_channel         AS ch ON ch.channel_key = f.channel_key
            JOIN gold.dim_booking_profile AS bp ON bp.booking_profile_key = f.booking_profile_key
            JOIN gold.ml_booking_risk     AS r  ON r.booking_id = f.booking_id
                                               AND r.model_version = :model_version
            WHERE f.hotel_key = :hotel_key AND ad.full_date BETWEEN :date_from AND :date_to
        )
        SELECT count(*) AS bookings,
               count(*) FILTER (WHERE flagged) AS flagged_bookings,
               count(*) FILTER (WHERE flagged AND is_canceled = 1) AS flagged_canceled,
               coalesce(sum(booked_revenue) FILTER (WHERE flagged AND is_canceled = 1), 0)
                   AS flagged_canceled_booked_revenue,
               coalesce(sum(realized_revenue)
                        FILTER (WHERE flagged AND is_canceled = 0 AND NOT is_ota), 0)
                   AS flagged_kept_direct_revenue,
               coalesce(sum(realized_revenue)
                        FILTER (WHERE flagged AND is_canceled = 0 AND is_ota), 0)
                   AS flagged_kept_ota_revenue,
               count(*) FILTER (WHERE NOT is_test_set) AS in_sample_bookings
        FROM b
        """
    )
    params = {
        "hotel_key": hotel_key,
        "date_from": date_from,
        "date_to": date_to,
        "threshold": threshold,
        "model_version": model_version,
    }
    return dict(conn.execute(query, params).mappings().one())
