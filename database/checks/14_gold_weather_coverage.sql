-- severity: error
-- Mọi đêm trong fact_daily_occupancy và mọi ngày đến trong fact_booking phải có thời tiết
-- của đúng khách sạn đó (thiếu = nguồn thời tiết không phủ đủ khoảng ngày của dữ liệu booking).
SELECT 'fact_daily_occupancy' AS fact_table, o.hotel_key, o.stay_date_key AS date_key
FROM gold.fact_daily_occupancy AS o
LEFT JOIN gold.fact_daily_weather AS w
       ON w.hotel_key = o.hotel_key AND w.date_key = o.stay_date_key
WHERE w.hotel_key IS NULL
UNION ALL
SELECT DISTINCT 'fact_booking', f.hotel_key, f.arrival_date_key
FROM gold.fact_booking AS f
LEFT JOIN gold.fact_daily_weather AS w
       ON w.hotel_key = f.hotel_key AND w.date_key = f.arrival_date_key
WHERE w.hotel_key IS NULL;
