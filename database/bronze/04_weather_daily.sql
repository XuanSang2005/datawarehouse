-- =============================================================================
-- bronze.weather_daily — Daily historical weather (Open-Meteo Historical Weather API, as-is)
-- Source: etl/extract/weather.py -> data/raw/weather_daily.csv
-- Grain : 1 row = 1 location (Lisbon, Faro) × 1 day, 2015-01-01 → 2017-12-31
-- Every column is TEXT; column names keep the API variable names. Missing API values are empty strings.
-- Used to enrich gold.fact_daily_weather (weather per hotel × day).
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
