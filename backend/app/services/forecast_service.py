"""Demand forecast (G3): forecast series + prediction interval + actuals; model MAPE vs baseline."""

from sqlalchemy import Connection

from app.core.errors import DataNotReadyError
from app.repositories import forecast_repo
from app.schemas.forecast import (
    ForecastMetricsResponse,
    ForecastPoint,
    ForecastResponse,
    HotelForecast,
    WeeklyActual,
)
from app.services import ml_service

FORECAST_TABLE = "gold.ml_demand_forecast"
MAIN_MODEL_PREFIX = "forecast_gbm"


def pick_default_version(versions: list[dict]) -> str:
    """Latest main model (forecast_gbm_*); otherwise the latest version of any model."""
    main = [v for v in versions if v["model_version"].startswith(MAIN_MODEL_PREFIX)]
    candidates = main or versions
    return max(candidates, key=lambda v: v["created_at"])["model_version"]


def build_series(forecast_rows: list[dict], actual_rows: list[dict]) -> list[HotelForecast]:
    history: dict[int, list[WeeklyActual]] = {}
    for r in actual_rows:
        history.setdefault(r["hotel_key"], []).append(
            WeeklyActual(
                week_start_date=r["week_start_date"], room_nights_sold=int(r["room_nights_sold"])
            )
        )
    series: dict[int, HotelForecast] = {}
    for r in forecast_rows:
        item = series.get(r["hotel_key"])
        if item is None:
            item = HotelForecast(
                hotel_key=r["hotel_key"],
                hotel_name=r["hotel_name"],
                points=[],
                history=history.get(r["hotel_key"], []),
            )
            series[r["hotel_key"]] = item
        item.points.append(
            ForecastPoint(
                week_start_date=r["week_start_date"],
                predicted_room_nights=float(r["predicted_room_nights"]),
                lower_bound=float(r["lower_bound"]),
                upper_bound=float(r["upper_bound"]),
                actual_room_nights=r["actual_room_nights"],
                horizon_weeks=int(r["horizon_weeks"]),
                is_future=r["actual_room_nights"] is None,
            )
        )
    return list(series.values())


def get_forecast(
    conn: Connection, hotel_key: int | None, model_version: str | None
) -> ForecastResponse:
    ml_service.require_table(conn, FORECAST_TABLE)
    versions = forecast_repo.fetch_versions(conn)
    if not versions:
        raise ml_service.not_ready(FORECAST_TABLE)
    names = [v["model_version"] for v in versions]
    version = model_version or pick_default_version(versions)
    if version not in names:
        raise DataNotReadyError(
            f"No forecast for model_version '{version}'",
            hint=f"Available versions: {', '.join(names)}",
        )
    rows = forecast_repo.fetch_forecast(conn, version, hotel_key)
    if not rows:
        raise DataNotReadyError(f"No forecast for hotel_key={hotel_key}")
    actuals = forecast_repo.fetch_weekly_actuals(conn, hotel_key)
    return ForecastResponse(
        model_version=version, available_versions=names, series=build_series(rows, actuals)
    )


def get_metrics(conn: Connection) -> ForecastMetricsResponse:
    models = ml_service.get_model_metrics(conn, "forecast_", FORECAST_TABLE)
    main = [m for m in models if m.model_name.startswith(MAIN_MODEL_PREFIX)]
    return ForecastMetricsResponse(
        main_model_version=max(main, key=lambda m: m.trained_at).model_version if main else None,
        models=models,
    )
