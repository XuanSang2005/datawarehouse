-- =============================================================================
-- silver.weather_daily — Thời tiết theo ngày đã ép kiểu.
-- Nguồn : bronze.weather_daily
-- Grain : 1 dòng = 1 điểm đo × 1 ngày. PK (location, weather_date): nếu nguồn có ngày trùng,
--         pipeline dừng ngay ở file này (không lặng lẽ gộp).
-- Biến đổi chính:
--   * '' -> NULL, ép kiểu số / ngày
--   * sunshine_duration (giây) -> sunshine_hours (giờ)
-- Không lọc dòng (quy tắc silver).
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
