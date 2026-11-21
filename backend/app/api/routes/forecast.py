from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import DbConn
from app.schemas.forecast import ForecastMetricsResponse, ForecastResponse
from app.services import forecast_service

router = APIRouter(prefix="/forecast", tags=["forecast"])


@router.get("", response_model=ForecastResponse)
def get_forecast(
    conn: DbConn,
    hotel_key: Annotated[int | None, Query(ge=1, description="Empty = both hotels")] = None,
    model_version: Annotated[
        str | None, Query(max_length=100, description="Default: latest forecast_gbm main model")
    ] = None,
) -> ForecastResponse:
    """Weekly room-nights: forecast, 80% interval, actuals (2017 backtest + future weeks).

    404 if gold.ml_demand_forecast has no data yet.
    """
    return forecast_service.get_forecast(conn, hotel_key, model_version)


@router.get("/metrics", response_model=ForecastMetricsResponse)
def get_forecast_metrics(conn: DbConn) -> ForecastMetricsResponse:
    """MAPE (overall, by horizon, by hotel) and 80% interval coverage of each model."""
    return forecast_service.get_metrics(conn)
