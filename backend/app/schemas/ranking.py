from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import BookingFilter

RankingSort = Literal[
    "realized_revenue", "adr", "cancellation_rate", "bookings", "room_nights_sold"
]


class RankingItem(BaseModel):
    rank: int
    key: str = Field(description="channel_group or country_code ('UNK' = unknown)")
    label: str
    group: str | None = Field(description="For markets: market_group (Domestic, Core Europe...)")
    bookings: int
    canceled_bookings: int
    cancellation_rate: float | None
    room_nights_sold: int
    realized_revenue: float = Field(description="Realized revenue (after cancellations), EUR")
    revenue_share: float | None = Field(
        description="Share of realized_revenue in the filtered total"
    )
    lost_revenue: float
    adr: float | None = Field(description="realized_revenue / room_nights_sold")


class RankingResponse(BaseModel):
    dimension: Literal["channel", "market"]
    sort_by: RankingSort
    min_bookings: int = Field(
        description="Groups with fewer bookings are not ranked (avoids noisy ADR/rates)"
    )
    filters: BookingFilter
    total_realized_revenue: float
    groups_ranked: int = Field(description="Number of eligible groups before the top-N cut")
    items: list[RankingItem]
