-- =============================================================================
-- gold.fact_daily_weather — Thời tiết theo khách sạn × ngày (periodic snapshot)
-- Nguồn : silver.weather_daily (Open-Meteo) nối dim_hotel qua dim_hotel.weather_location
--         (City Hotel -> Lisbon, Resort Hotel -> Faro).
-- Grain : 1 dòng = 1 khách sạn × 1 ngày lịch. PK (hotel_key, date_key)
-- Phạm vi: 2015-01-01 → 2017-12-31 (2 × 1.096 = 2.192 dòng), phủ trọn fact_daily_occupancy.
-- Cách dùng (KHÔNG nhân bản dòng fact, vì PK = đúng khóa nối):
--   * fact_daily_occupancy: JOIN 1:1 theo (hotel_key, stay_date_key = date_key)
--   * fact_booking        : JOIN N:1 theo (hotel_key, arrival_date_key = date_key) -> thời tiết ngày đến
-- Biến đổi chính:
--   * weather_group: gom mã WMO thành 7 nhóm dễ đọc
--   * is_rainy_day = 1 khi lượng mưa >= 1 mm (ngưỡng "ngày mưa" thông dụng), SMALLINT để SUM ra số ngày mưa
-- Lưu ý ML: thời tiết thực tế của ngày đến KHÔNG biết được lúc đặt phòng -> không dùng làm feature
-- dự đoán hủy (xem STAR_SCHEMA.md mục 5.3).
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
