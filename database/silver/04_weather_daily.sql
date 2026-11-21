-- =============================================================================
-- silver.weather_daily — Typed daily weather.
-- Source: bronze.weather_daily
-- Grain : 1 row = 1 location × 1 day. PK (location, weather_date): if the source has duplicate days,
--         the pipeline stops right at this file (no silent merging).
-- Main transformations:
--   * '' -> NULL, cast to numeric / date
--   * sunshine_duration (seconds) -> sunshine_hours (hours)
-- No row filtering (silver rule).
-- =============================================================================

DROP TABLE IF EXISTS silver.weather_daily;

CREATE TABLE silver.weather_daily AS
SELECT
    location,
    weather_date::DATE                                             AS weather_date,
    NULLIF(latitude, '')::NUMERIC(8, 5)                            AS latitude,
    NULLIF(longitude, '')::NUMERIC(8, 5)                           AS longitude,
    NULLIF(weather_code, '')::NUMERIC::SMALLINT                    AS weather_code,
    NULLIF(temperature_2m_max, '')::NUMERIC(4, 1)                  AS temp_max_c,
    NULLIF(temperature_2m_min, '')::NUMERIC(4, 1)                  AS temp_min_c,
    NULLIF(temperature_2m_mean, '')::NUMERIC(4, 1)                 AS temp_mean_c,
    NULLIF(precipitation_sum, '')::NUMERIC(6, 1)                   AS precipitation_mm,
    NULLIF(rain_sum, '')::NUMERIC(6, 1)                            AS rain_mm,
    NULLIF(precipitation_hours, '')::NUMERIC(4, 1)                 AS precipitation_hours,
    NULLIF(wind_speed_10m_max, '')::NUMERIC(5, 1)                  AS wind_speed_max_kmh,
    (NULLIF(sunshine_duration, '')::NUMERIC / 3600)::NUMERIC(5, 2) AS sunshine_hours
FROM bronze.weather_daily;

ALTER TABLE silver.weather_daily ADD PRIMARY KEY (location, weather_date);
