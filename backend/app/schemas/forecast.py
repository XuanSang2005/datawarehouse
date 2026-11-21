from datetime import date

from pydantic import BaseModel, Field

from app.schemas.ml import ModelMetrics


class ForecastPoint(BaseModel):
    week_start_date: date = Field(
        description="Thứ Hai đầu tuần (khớp gold.dim_date.week_start_date)"
    )
    predicted_room_nights: float
    lower_bound: float = Field(description="Cận dưới khoảng dự báo 80%")
    upper_bound: float = Field(description="Cận trên khoảng dự báo 80%")
    actual_room_nights: int | None = Field(description="NULL với tuần tương lai")
    horizon_weeks: int = Field(description="Dự báo trước bao nhiêu tuần (1 = tuần kế tiếp)")
    is_future: bool


class WeeklyActual(BaseModel):
    week_start_date: date
    room_nights_sold: int


class HotelForecast(BaseModel):
    hotel_key: int
    hotel_name: str
    points: list[ForecastPoint] = Field(description="Giai đoạn backtest 2017 + các tuần tương lai")
    history: list[WeeklyActual] = Field(
        description="Room-nights thực tế mọi tuần đủ 7 ngày, để vẽ nền lịch sử"
    )


class ForecastResponse(BaseModel):
    model_version: str
    available_versions: list[str]
    series: list[HotelForecast]


class ForecastMetricsResponse(BaseModel):
    main_model_version: str | None = Field(description="Phiên bản model chính (forecast_gbm_*)")
    models: list[ModelMetrics]
