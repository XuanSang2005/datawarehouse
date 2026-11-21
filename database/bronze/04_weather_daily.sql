-- =============================================================================
-- bronze.weather_daily — Thời tiết lịch sử theo ngày (Open-Meteo Historical Weather API, nguyên bản)
-- Nguồn : etl/extract/weather.py -> data/raw/weather_daily.csv
-- Grain : 1 dòng = 1 điểm đo (Lisbon, Faro) × 1 ngày, 2015-01-01 → 2017-12-31
-- Mọi cột TEXT, tên cột giữ nguyên tên biến của API. Giá trị thiếu của API là chuỗi rỗng.
-- Dùng để làm giàu gold.fact_daily_weather (thời tiết theo khách sạn × ngày).
-- =============================================================================

DROP TABLE IF EXISTS bronze.weather_daily;

CREATE TABLE bronze.weather_daily (
    location             TEXT,
    latitude             TEXT,
    longitude            TEXT,
    weather_date         TEXT,
    weather_code         TEXT,
    temperature_2m_max   TEXT,
    temperature_2m_min   TEXT,
    temperature_2m_mean  TEXT,
    precipitation_sum    TEXT,
    rain_sum             TEXT,
    precipitation_hours  TEXT,
    wind_speed_10m_max   TEXT,
    sunshine_duration    TEXT,
    _source_row          BIGINT,
    _source_file         TEXT,
    _loaded_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);
