from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import BookingFilter, KpiValues

Grain = Literal["year", "quarter", "month", "week"]


class HotelKpi(KpiValues):
    hotel_key: int
    hotel_name: str


class KpiSummary(BaseModel):
    """KPI tổng (theo bộ lọc) và tách theo từng khách sạn để so sánh City vs Resort."""

    filters: BookingFilter
    total: KpiValues
    by_hotel: list[HotelKpi]


class KpiPoint(KpiValues):
    period: str = Field(description="Nhãn kỳ: 2016 | 2016-Q3 | 2016-07 | 2016-W27 (tuần ISO)")
    period_start: date = Field(description="Ngày đầu kỳ, dùng làm trục x")
    hotel_key: int | None = Field(None, description="Chỉ có khi by_hotel=true")
    hotel_name: str | None = None


class KpiTimeseries(BaseModel):
    grain: Grain
    by_hotel: bool
    filters: BookingFilter
    points: list[KpiPoint] = Field(description="Sắp xếp theo period_start, rồi hotel_key")
