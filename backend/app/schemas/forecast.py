from datetime import date

from pydantic import BaseModel, Field

from app.schemas.ml import ModelMetrics


class ForecastPoint(BaseModel):
    week_start_date: date = Field(
        description="Monday starting the week (matches gold.dim_date.week_start_date)"
    )
    predicted_room_nights: float
    lower_bound: float = Field(description="Lower bound of the 80% forecast interval")
    upper_bound: float = Field(description="Upper bound of the 80% forecast interval")
    actual_room_nights: int | None = Field(description="NULL for future weeks")
    horizon_weeks: int = Field(description="Forecast horizon in weeks (1 = next week)")
    is_future: bool


class WeeklyActual(BaseModel):
    week_start_date: date
    room_nights_sold: int


class HotelForecast(BaseModel):
    hotel_key: int
    hotel_name: str
    points: list[ForecastPoint] = Field(description="2017 backtest period + future weeks")
    history: list[WeeklyActual] = Field(
        description="Actual room-nights of every full 7-day week, for the history background"
    )


class ForecastResponse(BaseModel):
    model_version: str
    available_versions: list[str]
    series: list[HotelForecast]


class ForecastMetricsResponse(BaseModel):
    main_model_version: str | None = Field(description="Main model version (forecast_gbm_*)")
    models: list[ModelMetrics]
