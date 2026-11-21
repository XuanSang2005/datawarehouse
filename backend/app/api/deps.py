"""Dependency dùng chung cho các route: kết nối DB và bộ lọc booking từ query string."""

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
        int | None, Query(ge=1, description="Khách sạn (gold.dim_hotel.hotel_key)")
    ] = None,
    date_from: Annotated[
        date | None, Query(description="Ngày đến từ (YYYY-MM-DD, bao gồm)")
    ] = None,
    date_to: Annotated[date | None, Query(description="Ngày đến đến (YYYY-MM-DD, bao gồm)")] = None,
    channel_group: Annotated[
        str | None, Query(max_length=50, description="Nhóm kênh, vd OTA")
    ] = None,
    country_code: Annotated[
        str | None,
        Query(min_length=2, max_length=10, description="Mã quốc gia ISO alpha-3, vd PRT"),
    ] = None,
) -> BookingFilter:
    if date_from and date_to and date_from > date_to:
        raise InvalidParameterError("date_from phải nhỏ hơn hoặc bằng date_to")
    return BookingFilter(
        hotel_key=hotel_key,
        date_from=date_from,
        date_to=date_to,
        channel_group=channel_group,
        country_code=country_code.upper() if country_code else None,
    )


Filters = Annotated[BookingFilter, Depends(booking_filter)]
