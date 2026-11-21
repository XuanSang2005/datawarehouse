from datetime import date

from pydantic import BaseModel, Field


class HotelOption(BaseModel):
    hotel_key: int
    hotel_name: str
    hotel_type: str
    city: str
    peak_rooms_occupied: int | None = Field(
        description="Số phòng có khách cao nhất trong 1 đêm "
        "(gợi ý cận dưới cho công suất khi chạy what-if)"
    )


class CountryOption(BaseModel):
    country_code: str = Field(description="ISO alpha-3; 'UNK' = không rõ quốc gia")
    country_name: str
    market_group: str
    bookings: int


class DateRange(BaseModel):
    min_date: date
    max_date: date


class FilterOptions(BaseModel):
    """Danh mục cho FilterBar. Chỉ gồm giá trị thực sự xuất hiện trong gold.fact_booking."""

    hotels: list[HotelOption]
    channel_groups: list[str]
    market_segments: list[str]
    countries: list[CountryOption] = Field(description="Sắp xếp theo số booking giảm dần")
    arrival_date_range: DateRange
