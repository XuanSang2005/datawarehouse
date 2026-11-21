-- =============================================================================
-- gold.fact_daily_weather — Weather per hotel × day (periodic snapshot)
-- Source: silver.weather_daily (Open-Meteo) joined to dim_hotel via dim_hotel.weather_location
--         (City Hotel -> Lisbon, Resort Hotel -> Faro).
-- Grain : 1 row = 1 hotel × 1 calendar day. PK (hotel_key, date_key)
-- Range : 2015-01-01 → 2017-12-31 (2 × 1,096 = 2,192 rows), fully covering fact_daily_occupancy.
-- Usage (does NOT duplicate fact rows, because the PK is exactly the join key):
--   * fact_daily_occupancy: 1:1 JOIN on (hotel_key, stay_date_key = date_key)
--   * fact_booking        : N:1 JOIN on (hotel_key, arrival_date_key = date_key) -> weather on the arrival day
-- Main transformations:
--   * weather_group: groups WMO codes into 7 readable groups
--   * is_rainy_day = 1 when precipitation >= 1 mm (the usual "rainy day" threshold), SMALLINT so SUM gives rainy-day counts
-- ML note: the actual weather on the arrival day is NOT known at booking time -> do not use it as a feature
-- for cancellation prediction (see STAR_SCHEMA.md section 5.3).
-- =============================================================================

DROP TABLE IF EXISTS gold.fact_daily_weather CASCADE;

CREATE TABLE gold.fact_daily_weather AS
SELECT
    h.hotel_key,
    d.date_key,
    w.weather_code,
    CASE
        WHEN w.weather_code IN (0, 1)                                          THEN 'Clear'
        WHEN w.weather_code IN (2, 3)                                          THEN 'Cloudy'
        WHEN w.weather_code IN (45, 48)                                        THEN 'Fog'
        WHEN w.weather_code BETWEEN 51 AND 57                                  THEN 'Drizzle'
        WHEN w.weather_code BETWEEN 61 AND 67 OR w.weather_code BETWEEN 80 AND 82 THEN 'Rain'
        WHEN w.weather_code BETWEEN 71 AND 77 OR w.weather_code IN (85, 86)    THEN 'Snow'
        WHEN w.weather_code BETWEEN 95 AND 99                                  THEN 'Thunderstorm'
        ELSE 'Unknown'
    END                                                         AS weather_group,
    w.temp_max_c,
    w.temp_min_c,
    w.temp_mean_c,
    w.precipitation_mm,
    w.rain_mm,
    w.precipitation_hours,
    w.wind_speed_max_kmh,
    w.sunshine_hours,
    (COALESCE(w.precipitation_mm, 0) >= 1.0)::INT::SMALLINT     AS is_rainy_day
FROM silver.weather_daily AS w
JOIN gold.dim_hotel AS h ON h.weather_location = w.location
JOIN gold.dim_date  AS d ON d.full_date = w.weather_date;

ALTER TABLE gold.fact_daily_weather ADD PRIMARY KEY (hotel_key, date_key);

ALTER TABLE gold.fact_daily_weather
    ADD CONSTRAINT fk_fact_weather_hotel FOREIGN KEY (hotel_key) REFERENCES gold.dim_hotel (hotel_key),
    ADD CONSTRAINT fk_fact_weather_date  FOREIGN KEY (date_key)  REFERENCES gold.dim_date (date_key);
