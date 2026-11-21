from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import BookingFilter, KpiValues

Grain = Literal["year", "quarter", "month", "week"]


class HotelKpi(KpiValues):
    hotel_key: int
    hotel_name: str


class KpiSummary(BaseModel):
    """Overall KPIs (for the filter) and split by hotel to compare City vs Resort."""

    filters: BookingFilter
    total: KpiValues
    by_hotel: list[HotelKpi]


class KpiPoint(KpiValues):
    period: str = Field(description="Period label: 2016 | 2016-Q3 | 2016-07 | 2016-W27 (ISO week)")
    period_start: date = Field(description="First day of the period, used as the x axis")
    hotel_key: int | None = Field(None, description="Only present when by_hotel=true")
    hotel_name: str | None = None


class KpiTimeseries(BaseModel):
    grain: Grain
    by_hotel: bool
    filters: BookingFilter
    points: list[KpiPoint] = Field(description="Sorted by period_start, then hotel_key")
