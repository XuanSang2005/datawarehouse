from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import BookingFilter

BreakdownDimension = Literal[
    "lead_time", "channel", "deposit_type", "country", "market_segment", "customer_type"
]
RiskBand = Literal["Low", "Medium", "High"]
RiskBandFilter = Literal["Low", "Medium", "High", "All"]
HighRiskSort = Literal["probability", "expected_loss"]


class BreakdownItem(BaseModel):
    key: str = Field(description="Giá trị nhóm (vd '0-7', 'OTA', 'Non Refund', 'PRT')")
    label: str = Field(description="Nhãn hiển thị (vd tên quốc gia)")
    sort_order: int = Field(
        description="Thứ tự hiển thị gợi ý (lead time theo khoảng; còn lại theo số booking)"
    )
    bookings: int
    canceled_bookings: int
    cancellation_rate: float | None
    booking_share: float | None = Field(description="Tỉ trọng booking của nhóm trong tổng đã lọc")
    lost_revenue: float
    net_lost_revenue: float


class CancellationBreakdown(BaseModel):
    by: BreakdownDimension
    filters: BookingFilter
    overall_cancellation_rate: float | None
    total_bookings: int
    items: list[BreakdownItem]


class HighRiskBooking(BaseModel):
    booking_id: int
    hotel_key: int
    hotel_name: str
    arrival_date: date
    booking_date: date
    lead_time: int
    total_nights: int
    guests: int
    adr: float
    booked_revenue: float
    channel_group: str
    market_segment: str
    country_code: str
    deposit_type: str
    customer_type: str
    total_of_special_requests: int
    previous_cancellations: int
    cancel_probability: float
    risk_band: RiskBand
    expected_loss: float = Field(description="cancel_probability × booked_revenue (EUR)")
    is_test_set: bool = Field(description="TRUE = điểm ngoài mẫu (booking đến năm 2017)")
    is_canceled: bool = Field(
        description="Kết quả THỰC TẾ (dữ liệu lịch sử, lúc ra quyết định chưa biết)"
    )


class HighRiskPage(BaseModel):
    model_version: str
    filters: BookingFilter
    risk_band: RiskBand | None
    min_probability: float | None
    sort: HighRiskSort
    page: int
    page_size: int
    total: int = Field(description="Số booking khớp điều kiện (mọi trang)")
    booked_revenue_total: float = Field(description="Σ booked_revenue của mọi booking khớp (EUR)")
    expected_loss_total: float = Field(
        description="Σ cancel_probability × booked_revenue của mọi booking khớp (EUR)"
    )
    items: list[HighRiskBooking]
