"""Extract: lấy dữ liệu từ nguồn bên ngoài về thư mục data/raw/.

Mỗi nguồn dữ liệu = 1 module + 1 dòng trong SOURCES.
Thêm nguồn mới: viết module extract, tạo file DDL trong database/bronze/, rồi đăng ký ở đây.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from etl.extract import countries, hotel_bookings, pt_holidays, weather


@dataclass(frozen=True)
class Source:
    name: str
    filename: str                      # tên file trong data/raw/
    bronze_table: str                  # bảng đích ở lớp bronze
    extract: Callable[[Path], None]    # hàm tạo/tải file vào đường dẫn cho trước


SOURCES: list[Source] = [
    Source("hotel_bookings", "hotel_bookings.csv", "bronze.hotel_bookings", hotel_bookings.extract),
    Source("pt_holidays", "pt_holidays.csv", "bronze.pt_holidays", pt_holidays.extract),
    Source("countries", "countries.csv", "bronze.countries", countries.extract),
    Source("weather_daily", "weather_daily.csv", "bronze.weather_daily", weather.extract),
]
