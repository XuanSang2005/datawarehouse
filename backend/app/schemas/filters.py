from datetime import date

from pydantic import BaseModel, Field


class HotelOption(BaseModel):
    hotel_key: int
    hotel_name: str
    hotel_type: str
    city: str
    peak_rooms_occupied: int | None = Field(
        description="Highest number of occupied rooms in a single night "
        "(suggested lower bound for capacity in the what-if)"
    )


class CountryOption(BaseModel):
    country_code: str = Field(description="ISO alpha-3; 'UNK' = unknown country")
    country_name: str
    market_group: str
    bookings: int


class DateRange(BaseModel):
    min_date: date
    max_date: date


class FilterOptions(BaseModel):
    """Options for the FilterBar. Only values that actually appear in gold.fact_booking."""

    hotels: list[HotelOption]
    channel_groups: list[str]
    market_segments: list[str]
    countries: list[CountryOption] = Field(description="Sorted by number of bookings, descending")
    arrival_date_range: DateRange
