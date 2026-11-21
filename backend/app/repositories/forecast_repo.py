"""Demand forecast (G3): gold.ml_demand_forecast + weekly actuals (gold.kpi_weekly_occupancy)."""

from sqlalchemy import Connection, text


def fetch_versions(conn: Connection) -> list[dict]:
    query = text(
        """
        SELECT model_version, max(created_at) AS created_at
        FROM gold.ml_demand_forecast
        GROUP BY model_version
        ORDER BY model_version
        """
    )
    return [dict(r) for r in conn.execute(query).mappings()]


def fetch_forecast(conn: Connection, model_version: str, hotel_key: int | None) -> list[dict]:
    query = text(
        """
        SELECT fc.hotel_key, h.hotel_name, fc.week_start_date, fc.predicted_room_nights,
               fc.lower_bound, fc.upper_bound, fc.actual_room_nights, fc.horizon_weeks
        FROM gold.ml_demand_forecast AS fc
        JOIN gold.dim_hotel AS h ON h.hotel_key = fc.hotel_key
        WHERE fc.model_version = :model_version
          AND (CAST(:hotel_key AS INT) IS NULL OR fc.hotel_key = :hotel_key)
        ORDER BY fc.hotel_key, fc.week_start_date
        """
    )
    return [
        dict(r)
        for r in conn.execute(
            query, {"model_version": model_version, "hotel_key": hotel_key}
        ).mappings()
    ]


def fetch_weekly_actuals(conn: Connection, hotel_key: int | None) -> list[dict]:
    query = text(
        """
        SELECT hotel_key, week_start_date, room_nights_sold
        FROM gold.kpi_weekly_occupancy
        WHERE is_complete_week
          AND (CAST(:hotel_key AS INT) IS NULL OR hotel_key = :hotel_key)
        ORDER BY hotel_key, week_start_date
        """
    )
    return [dict(r) for r in conn.execute(query, {"hotel_key": hotel_key}).mappings()]
