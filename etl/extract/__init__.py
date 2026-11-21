"""Extract: fetch data from external sources into data/raw/.

Each data source = 1 module + 1 entry in SOURCES.
To add a source: write an extract module, add a DDL file in database/bronze/, then register it here.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from etl.extract import countries, hotel_bookings, pt_holidays, weather


@dataclass(frozen=True)
class Source:
    name: str
    filename: str                      # file name in data/raw/
    bronze_table: str                  # target table in the bronze layer
    extract: Callable[[Path], None]    # function that creates/downloads the file at the given path


SOURCES: list[Source] = [
    Source("hotel_bookings", "hotel_bookings.csv", "bronze.hotel_bookings", hotel_bookings.extract),
    Source("pt_holidays", "pt_holidays.csv", "bronze.pt_holidays", pt_holidays.extract),
    Source("countries", "countries.csv", "bronze.countries", countries.extract),
    Source("weather_daily", "weather_daily.csv", "bronze.weather_daily", weather.extract),
]
