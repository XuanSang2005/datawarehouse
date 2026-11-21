"""Shared route dependencies: DB connection and the booking filter from the query string."""

from datetime import date
from typing import Annotated

from fastapi import Depends, Query
from sqlalchemy import Connection

from app.core.db import get_connection
from app.core.errors import InvalidParameterError
from app.schemas.common import BookingFilter

DbConn = Annotated[Connection, Depends(get_connection)]


def booking_filter(
    hotel_key: Annotated[
        int | None, Query(ge=1, description="Hotel (gold.dim_hotel.hotel_key)")
    ] = None,
    date_from: Annotated[
        date | None, Query(description="Arrival date from (YYYY-MM-DD, inclusive)")
    ] = None,
    date_to: Annotated[
        date | None, Query(description="Arrival date to (YYYY-MM-DD, inclusive)")
    ] = None,
    channel_group: Annotated[
        str | None, Query(max_length=50, description="Channel group, e.g. OTA")
    ] = None,
    country_code: Annotated[
        str | None,
        Query(min_length=2, max_length=10, description="ISO alpha-3 country code, e.g. PRT"),
    ] = None,
) -> BookingFilter:
    if date_from and date_to and date_from > date_to:
        raise InvalidParameterError("date_from must be less than or equal to date_to")
    return BookingFilter(
        hotel_key=hotel_key,
        date_from=date_from,
        date_to=date_to,
        channel_group=channel_group,
        country_code=country_code.upper() if country_code else None,
    )


Filters = Annotated[BookingFilter, Depends(booking_filter)]
