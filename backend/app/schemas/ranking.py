from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import BookingFilter

RankingSort = Literal[
    "realized_revenue", "adr", "cancellation_rate", "bookings", "room_nights_sold"
]


class RankingItem(BaseModel):
    rank: int
    key: str = Field(description="channel_group hoặc country_code ('UNK' = không rõ)")
    label: str
    group: str | None = Field(description="Với thị trường: market_group (Domestic, Core Europe...)")
    bookings: int
    canceled_bookings: int
    cancellation_rate: float | None
    room_nights_sold: int
    realized_revenue: float = Field(description="Doanh thu thực (sau hủy), EUR")
    revenue_share: float | None = Field(description="Tỉ trọng realized_revenue trong tổng đã lọc")
    lost_revenue: float
    adr: float | None = Field(description="realized_revenue / room_nights_sold")


class RankingResponse(BaseModel):
    dimension: Literal["channel", "market"]
    sort_by: RankingSort
    min_bookings: int = Field(
        description="Nhóm có ít booking hơn bị loại khỏi xếp hạng (tránh ADR/tỉ lệ nhiễu)"
    )
    filters: BookingFilter
    total_realized_revenue: float
    groups_ranked: int = Field(description="Số nhóm đủ điều kiện trước khi cắt top N")
    items: list[RankingItem]
