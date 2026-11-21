-- =============================================================================
-- gold.dim_hotel — Hotel dimension (conformed)
-- Source: DISTINCT silver.hotel_bookings.hotel_name + descriptive attributes from the original paper
--         (City Hotel in Lisbon, Resort Hotel in the Algarve)
--   * weather_location: the hotel's weather location (join key to silver.weather_daily.location,
--     used in gold/32_fact_daily_weather.sql). Coordinates match etl/extract/weather.py.
-- Grain : 1 row = 1 hotel (2 rows)
-- Deliberately NO room-count column: the dataset has no capacity (rule 10 in CLAUDE.md).
-- =============================================================================

DROP TABLE IF EXISTS gold.dim_hotel CASCADE;

CREATE TABLE gold.dim_hotel AS
WITH hotels AS (
    SELECT DISTINCT hotel_name FROM silver.hotel_bookings
)
SELECT
    ROW_NUMBER() OVER (ORDER BY hotel_name)::INT                                   AS hotel_key,
    hotel_name,
    CASE hotel_name WHEN 'City Hotel' THEN 'City' WHEN 'Resort Hotel' THEN 'Resort' ELSE 'Unknown' END
                                                                                   AS hotel_type,
    CASE hotel_name WHEN 'City Hotel' THEN 'Lisbon' WHEN 'Resort Hotel' THEN 'Algarve' ELSE 'Unknown' END
                                                                                   AS city,
    'PRT'::TEXT                                                                    AS country_code,
    CASE hotel_name WHEN 'City Hotel' THEN 38.72230 WHEN 'Resort Hotel' THEN 37.01930 END::NUMERIC(8, 5)
                                                                                   AS latitude,
    CASE hotel_name WHEN 'City Hotel' THEN -9.13930 WHEN 'Resort Hotel' THEN -7.93040 END::NUMERIC(8, 5)
                                                                                   AS longitude,
    CASE hotel_name WHEN 'City Hotel' THEN 'Lisbon' WHEN 'Resort Hotel' THEN 'Faro' END
                                                                                   AS weather_location
FROM hotels;

ALTER TABLE gold.dim_hotel ADD PRIMARY KEY (hotel_key);
ALTER TABLE gold.dim_hotel ADD CONSTRAINT uq_dim_hotel_name UNIQUE (hotel_name);
