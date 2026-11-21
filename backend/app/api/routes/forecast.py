from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import DbConn
from app.schemas.forecast import ForecastMetricsResponse, ForecastResponse
from app.services import forecast_service

router = APIRouter(prefix="/forecast", tags=["forecast"])


@router.get("", response_model=ForecastResponse)
def get_forecast(
    conn: DbConn,
    hotel_key: Annotated[int | None, Query(ge=1, description="Bỏ trống = cả 2 khách sạn")] = None,
    model_version: Annotated[
        str | None, Query(max_length=100, description="Mặc định: model chính forecast_gbm mới nhất")
    ] = None,
) -> ForecastResponse:
    """Room-nights theo tuần: dự báo, khoảng tin cậy 80%, thực tế (backtest 2017 + tuần tương lai).

    404 nếu bảng gold.ml_demand_forecast chưa có dữ liệu.
    """
    return forecast_service.get_forecast(conn, hotel_key, model_version)


@router.get("/metrics", response_model=ForecastMetricsResponse)
def get_forecast_metrics(conn: DbConn) -> ForecastMetricsResponse:
    """MAPE (chung, theo horizon, theo khách sạn) và độ phủ khoảng 80% của từng model."""
    return forecast_service.get_metrics(conn)
