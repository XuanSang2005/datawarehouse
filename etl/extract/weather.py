"""Source 4: Daily historical weather from the Open-Meteo Historical Weather API (ERA5).

Two locations, one per hotel (column `weather_location` in `gold.dim_hotel`):
  * Lisbon -> City Hotel
  * Faro   -> Resort Hotel (Algarve)
Date range: 2015-01-01 → 2017-12-31 (covers every arrival date/stay night in the booking dataset).
Output: exactly 1 row per location × day.
`rows_from_response` checks this before writing the file.

Free API, no key required (limit ~10,000 requests/day per IP).
Each extract makes only 2 requests.
Docs: https://open-meteo.com/en/docs/historical-weather-api (data CC BY 4.0).
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
TIMEZONE = "Europe/Lisbon"  # Lisbon and Faro share a time zone: the "day" matches the booking dates
START_DATE = date(2015, 1, 1)
END_DATE = date(2017, 12, 31)

# Daily variables fetched from the API (names as returned by the API; also the CSV/bronze columns).
DAILY_VARIABLES = [
    "weather_code",          # WMO weather code (0 = clear sky ... 95+ = thunderstorm)
    "temperature_2m_max",    # °C
    "temperature_2m_min",    # °C
    "temperature_2m_mean",   # °C
    "precipitation_sum",     # mm (rain + snow)
    "rain_sum",              # mm
    "precipitation_hours",   # hours with precipitation
    "wind_speed_10m_max",    # km/h
    "sunshine_duration",     # seconds
]

CSV_HEADER = ["location", "latitude", "longitude", "weather_date", *DAILY_VARIABLES]

MAX_ATTEMPTS = 4
RETRY_STATUS = {429, 500, 502, 503, 504}


@dataclass(frozen=True)
class WeatherLocation:
    name: str
    latitude: float
    longitude: float


# Coordinates match gold.dim_hotel (database/gold/11_dim_hotel.sql).
LOCATIONS = [
    WeatherLocation("Lisbon", 38.72230, -9.13930),
    WeatherLocation("Faro", 37.01930, -7.93040),
]


class WeatherDataError(ValueError):
    """The API data is not exactly 1 row per day, or a variable is missing."""


def expected_dates(start: date, end: date) -> list[str]:
    return [(start + timedelta(days=i)).isoformat() for i in range((end - start).days + 1)]


def _fmt(value: Any) -> str:
    """API NULL -> empty string in the CSV (bronze keeps TEXT, silver turns '' into NULL)."""
    return "" if value is None else str(value)


def rows_from_response(
    location: WeatherLocation, payload: dict[str, Any], start: date, end: date
) -> list[list[str]]:
    """Convert Open-Meteo JSON into CSV rows, ensuring exactly 1 row per day."""
    daily = payload.get("daily")
    if not isinstance(daily, dict) or "time" not in daily:
        raise WeatherDataError(f"[{location.name}] API response has no 'daily.time' block")

    missing_vars = [v for v in DAILY_VARIABLES if v not in daily]
    if missing_vars:
        raise WeatherDataError(f"[{location.name}] API is missing variables: {missing_vars}")

    days = daily["time"]
    wanted = expected_dates(start, end)
    if days != wanted:
        dupes = len(days) - len(set(days))
        missing = sorted(set(wanted) - set(days))[:5]
        extra = sorted(set(days) - set(wanted))[:5]
        raise WeatherDataError(
            f"[{location.name}] Returned dates do not match {start}→{end}: {len(days)} days "
            f"(expected {len(wanted)}), duplicates {dupes}, missing {missing or '-'}, "
            f"extra {extra or '-'}"
        )
    for var in DAILY_VARIABLES:
        if len(daily[var]) != len(days):
            raise WeatherDataError(
                f"[{location.name}] Variable {var} has {len(daily[var])} values, "
                f"expected {len(days)}"
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
        log.warning("[%s] Open-Meteo returned HTTP %s, retrying in %ss (attempt %d/%d)",
                    location.name, resp.status_code, wait, attempt, MAX_ATTEMPTS)
        time.sleep(wait)

    if resp.status_code != 200:
        try:
            reason = resp.json().get("reason", resp.text[:200])
        except ValueError:
            reason = resp.text[:200]
        raise RuntimeError(
            f"Open-Meteo returned HTTP {resp.status_code} for {location.name}: {reason}. "
            "If this is the daily request limit, retry later or see docs/TROUBLESHOOTING.md "
            "section 2."
        )
    return resp.json()


def extract(target: Path) -> None:
    rows: list[list[str]] = []
    for loc in LOCATIONS:
        log.info("Downloading weather for %s (%s, %s) %s→%s", loc.name, loc.latitude, loc.longitude,
                 START_DATE, END_DATE)
        rows.extend(rows_from_response(loc, fetch_location(loc), START_DATE, END_DATE))

    # Write to a temp file then rename: a failure midway leaves no incomplete file in data/raw/.
    tmp = target.with_suffix(target.suffix + ".part")
    with tmp.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(CSV_HEADER)
        writer.writerows(rows)
    tmp.replace(target)
    log.info("Saved %d rows (%d locations × %d days) to %s", len(rows), len(LOCATIONS),
             len(rows) // len(LOCATIONS), target)
