"""Schemas shared by several endpoints: the booking filter and the standard KPI set."""

from datetime import date

from pydantic import BaseModel, Field


class BookingFilter(BaseModel):
    """Shared slice & dice filter. The date range applies to the ARRIVAL DATE (arrival_date)."""

    hotel_key: int | None = Field(
        None, description="gold.dim_hotel.hotel_key; empty = both hotels"
    )
    date_from: date | None = Field(None, description="Arrival date from (inclusive)")
    date_to: date | None = Field(None, description="Arrival date to (inclusive)")
    channel_group: str | None = Field(
        None, description="gold.dim_channel.channel_group, e.g. 'OTA'"
    )
    country_code: str | None = Field(None, description="ISO alpha-3 code, e.g. 'PRT'")


class KpiValues(BaseModel):
    """Standard KPI set. Rates/averages are always recomputed from totals (rule 8); None if the
    denominator is 0."""

    bookings: int
    canceled_bookings: int
    cancellation_rate: float | None = Field(description="canceled_bookings / bookings")
    room_nights_sold: int = Field(description="Room-nights of non-canceled bookings")
    realized_revenue: float = Field(description="Realized revenue (EUR), after cancellations")
    lost_revenue: float = Field(description="Revenue lost to cancellations (EUR, upper bound)")
    net_lost_revenue: float = Field(description="lost_revenue minus deposit retained (EUR)")
    adr: float | None = Field(description="realized_revenue / room_nights_sold (EUR)")
    avg_lead_time: float | None = Field(description="Average lead time (days)")
    avg_los: float | None = Field(description="Average length of stay (nights) per booking")
