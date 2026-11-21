from sqlalchemy import Connection

from app.core.errors import DataNotReadyError
from app.repositories import filters_repo
from app.schemas.filters import CountryOption, DateRange, FilterOptions, HotelOption


def get_filter_options(conn: Connection) -> FilterOptions:
    date_range = filters_repo.fetch_arrival_date_range(conn)
    if date_range is None:
        raise DataNotReadyError(
            "gold.fact_booking chưa có dữ liệu",
            hint="Chạy pipeline: python -m etl.run_pipeline",
        )
    return FilterOptions(
        hotels=[HotelOption(**r) for r in filters_repo.fetch_hotels(conn)],
        channel_groups=filters_repo.fetch_channel_groups(conn),
        market_segments=filters_repo.fetch_market_segments(conn),
        countries=[CountryOption(**r) for r in filters_repo.fetch_countries(conn)],
        arrival_date_range=DateRange(**date_range),
    )
