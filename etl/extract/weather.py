"""Nguồn 4: Thời tiết lịch sử theo ngày từ Open-Meteo Historical Weather API (ERA5).

Hai điểm đo, mỗi điểm ứng với một khách sạn (cột `weather_location` trong `gold.dim_hotel`):
  * Lisbon -> City Hotel
  * Faro   -> Resort Hotel (Algarve)
Khoảng ngày: 2015-01-01 → 2017-12-31 (phủ toàn bộ ngày đến/đêm lưu trú trong dataset booking).
Đầu ra: đúng 1 dòng / 1 điểm đo × 1 ngày.
Hàm `rows_from_response` kiểm tra điều này trước khi ghi file.

API miễn phí, không cần key (giới hạn ~10.000 request/ngày theo IP).
Mỗi lần extract chỉ gọi 2 request.
Tài liệu: https://open-meteo.com/en/docs/historical-weather-api (dữ liệu CC BY 4.0).
"""

from __future__ import annotations

import csv
import logging
import time
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import requests

log = logging.getLogger("etl.extract.weather")

API_URL = "https://archive-api.open-meteo.com/v1/archive"
TIMEZONE = "Europe/Lisbon"  # Lisbon và Faro cùng múi giờ: "ngày" khớp với ngày của booking
START_DATE = date(2015, 1, 1)
END_DATE = date(2017, 12, 31)

# Biến daily lấy từ API (tên giữ nguyên như API trả về, cũng là tên cột CSV/bronze).
DAILY_VARIABLES = [
    "weather_code",          # mã thời tiết WMO (0 = trời quang ... 95+ = dông)
    "temperature_2m_max",    # °C
    "temperature_2m_min",    # °C
    "temperature_2m_mean",   # °C
    "precipitation_sum",     # mm (mưa + tuyết)
    "rain_sum",              # mm
    "precipitation_hours",   # giờ có mưa
    "wind_speed_10m_max",    # km/h
    "sunshine_duration",     # giây
]

CSV_HEADER = ["location", "latitude", "longitude", "weather_date", *DAILY_VARIABLES]

MAX_ATTEMPTS = 4
RETRY_STATUS = {429, 500, 502, 503, 504}


@dataclass(frozen=True)
class WeatherLocation:
    name: str
    latitude: float
    longitude: float


# Tọa độ trùng với gold.dim_hotel (database/gold/11_dim_hotel.sql).
LOCATIONS = [
    WeatherLocation("Lisbon", 38.72230, -9.13930),
    WeatherLocation("Faro", 37.01930, -7.93040),
]


class WeatherDataError(ValueError):
    """Dữ liệu API trả về không đúng 1 dòng / 1 ngày, hoặc thiếu biến."""


def expected_dates(start: date, end: date) -> list[str]:
    return [(start + timedelta(days=i)).isoformat() for i in range((end - start).days + 1)]


def _fmt(value: Any) -> str:
    """NULL của API -> chuỗi rỗng trong CSV (bronze giữ TEXT, silver đổi '' thành NULL)."""
    return "" if value is None else str(value)


def rows_from_response(
    location: WeatherLocation, payload: dict[str, Any], start: date, end: date
) -> list[list[str]]:
    """Chuyển JSON của Open-Meteo thành các dòng CSV, đảm bảo đúng 1 dòng cho mỗi ngày."""
    daily = payload.get("daily")
    if not isinstance(daily, dict) or "time" not in daily:
        raise WeatherDataError(f"[{location.name}] Phản hồi API không có khối 'daily.time'")

    missing_vars = [v for v in DAILY_VARIABLES if v not in daily]
    if missing_vars:
        raise WeatherDataError(f"[{location.name}] API thiếu biến: {missing_vars}")

    days = daily["time"]
    wanted = expected_dates(start, end)
    if days != wanted:
        dupes = len(days) - len(set(days))
        missing = sorted(set(wanted) - set(days))[:5]
        extra = sorted(set(days) - set(wanted))[:5]
        raise WeatherDataError(
            f"[{location.name}] Ngày trả về không khớp {start}→{end}: {len(days)} ngày "
            f"(cần {len(wanted)}), trùng {dupes}, thiếu {missing or '-'}, thừa {extra or '-'}"
        )
    for var in DAILY_VARIABLES:
        if len(daily[var]) != len(days):
            raise WeatherDataError(
                f"[{location.name}] Biến {var} có {len(daily[var])} giá trị, cần {len(days)}"
            )

    lat = _fmt(payload.get("latitude", location.latitude))
    lon = _fmt(payload.get("longitude", location.longitude))
    return [
        [location.name, lat, lon, day, *(_fmt(daily[var][i]) for var in DAILY_VARIABLES)]
        for i, day in enumerate(days)
    ]


def fetch_location(
    location: WeatherLocation, start: date = START_DATE, end: date = END_DATE
) -> dict[str, Any]:
    params = {
        "latitude": location.latitude,
        "longitude": location.longitude,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "daily": ",".join(DAILY_VARIABLES),
        "timezone": TIMEZONE,
    }
    for attempt in range(1, MAX_ATTEMPTS + 1):
        resp = requests.get(API_URL, params=params, timeout=60)
        if resp.status_code not in RETRY_STATUS or attempt == MAX_ATTEMPTS:
            break
        wait = 2**attempt
        log.warning("[%s] Open-Meteo trả HTTP %s, thử lại sau %ss (lần %d/%d)",
                    location.name, resp.status_code, wait, attempt, MAX_ATTEMPTS)
        time.sleep(wait)

    if resp.status_code != 200:
        try:
            reason = resp.json().get("reason", resp.text[:200])
        except ValueError:
            reason = resp.text[:200]
        raise RuntimeError(
            f"Open-Meteo trả HTTP {resp.status_code} cho {location.name}: {reason}. "
            "Nếu là giới hạn request/ngày, thử lại sau hoặc xem docs/TROUBLESHOOTING.md mục 2."
        )
    return resp.json()


def extract(target: Path) -> None:
    rows: list[list[str]] = []
    for loc in LOCATIONS:
        log.info("Đang tải thời tiết %s (%s, %s) %s→%s", loc.name, loc.latitude, loc.longitude,
                 START_DATE, END_DATE)
        rows.extend(rows_from_response(loc, fetch_location(loc), START_DATE, END_DATE))

    # Ghi ra file tạm rồi đổi tên: lỗi giữa chừng không để lại file thiếu dữ liệu trong data/raw/.
    tmp = target.with_suffix(target.suffix + ".part")
    with tmp.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(CSV_HEADER)
        writer.writerows(rows)
    tmp.replace(target)
    log.info("Đã lưu %d dòng (%d điểm đo × %d ngày) vào %s", len(rows), len(LOCATIONS),
             len(rows) // len(LOCATIONS), target)
