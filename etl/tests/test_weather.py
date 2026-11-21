"""Tests for the Open-Meteo weather source (no network calls, no DB needed)."""

import csv
import re
from datetime import date

import pytest

from etl.config import DATABASE_DIR
from etl.extract import weather
from etl.extract.weather import (
    CSV_HEADER,
    DAILY_VARIABLES,
    LOCATIONS,
    WeatherDataError,
    WeatherLocation,
    expected_dates,
    rows_from_response,
)

LISBON = WeatherLocation("Lisbon", 38.7223, -9.1393)
START, END = date(2016, 2, 27), date(2016, 3, 2)  # includes the 29 Feb leap day


def fake_payload(days: list[str]) -> dict:
    n = len(days)
    daily = {"time": days}
    for i, var in enumerate(DAILY_VARIABLES):
        daily[var] = [float(i)] * n
    daily["rain_sum"] = [None] * n  # the API may return null
    return {"latitude": 38.71, "longitude": -9.14, "daily": daily}


def test_expected_dates_inclusive_with_leap_day():
    days = expected_dates(START, END)
    assert days == ["2016-02-27", "2016-02-28", "2016-02-29", "2016-03-01", "2016-03-02"]


def test_default_range_covers_booking_period():
    # Arrivals run from 2015-07-01 to 2017-08-31 (+ stay nights spilling into September).
    assert weather.START_DATE <= date(2015, 7, 1)
    assert weather.END_DATE >= date(2017, 9, 30)
    assert len(expected_dates(weather.START_DATE, weather.END_DATE)) == 1096


def test_rows_from_response_one_row_per_day():
    rows = rows_from_response(LISBON, fake_payload(expected_dates(START, END)), START, END)
    assert len(rows) == 5
    assert all(len(r) == len(CSV_HEADER) for r in rows)
    assert [r[3] for r in rows] == expected_dates(START, END)
    assert len({(r[0], r[3]) for r in rows}) == len(rows)  # unique (location, day)
    rain_idx = CSV_HEADER.index("rain_sum")
    assert rows[0][0] == "Lisbon" and rows[0][rain_idx] == ""  # null -> empty string


@pytest.mark.parametrize(
    "days",
    [
        ["2016-02-27", "2016-02-28", "2016-03-01", "2016-03-02"],                # missing 29 Feb
        ["2016-02-27", "2016-02-28", "2016-02-28", "2016-02-29", "2016-03-01"],  # duplicate day
        ["2016-02-28", "2016-02-29", "2016-03-01", "2016-03-02", "2016-03-03"],  # shifted range
    ],
)
def test_rows_from_response_rejects_wrong_days(days):
    with pytest.raises(WeatherDataError, match="Returned dates do not match"):
        rows_from_response(LISBON, fake_payload(days), START, END)


def test_rows_from_response_rejects_missing_variable():
    payload = fake_payload(expected_dates(START, END))
    del payload["daily"]["sunshine_duration"]
    with pytest.raises(WeatherDataError, match="sunshine_duration"):
        rows_from_response(LISBON, payload, START, END)


def test_rows_from_response_rejects_ragged_arrays():
    payload = fake_payload(expected_dates(START, END))
    payload["daily"]["temperature_2m_max"] = [1.0]
    with pytest.raises(WeatherDataError, match="temperature_2m_max"):
        rows_from_response(LISBON, payload, START, END)


def test_extract_writes_csv_with_all_locations(tmp_path, monkeypatch):
    monkeypatch.setattr(weather, "START_DATE", START)
    monkeypatch.setattr(weather, "END_DATE", END)
    monkeypatch.setattr(
        weather, "fetch_location", lambda loc: fake_payload(expected_dates(START, END))
    )
    target = tmp_path / "weather_daily.csv"
    weather.extract(target)

    with target.open(newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert rows[0] == CSV_HEADER
    assert len(rows) - 1 == len(LOCATIONS) * 5
    assert not (tmp_path / "weather_daily.csv.part").exists()


def _ddl_columns(sql_text: str) -> list[str]:
    body = sql_text.split("(", 1)[1]
    cols = re.findall(r"^\s+([a-z0-9_]+)\s+[A-Z]", body, flags=re.MULTILINE)
    return [c for c in cols if not c.startswith("_")]


def test_bronze_ddl_matches_csv_header():
    ddl = (DATABASE_DIR / "bronze" / "04_weather_daily.sql").read_text(encoding="utf-8")
    assert _ddl_columns(ddl) == CSV_HEADER


def test_every_location_is_mapped_to_a_hotel():
    dim_hotel = (DATABASE_DIR / "gold" / "11_dim_hotel.sql").read_text(encoding="utf-8")
    for loc in LOCATIONS:
        assert f"'{loc.name}'" in dim_hotel, f"dim_hotel.weather_location is missing '{loc.name}'"
