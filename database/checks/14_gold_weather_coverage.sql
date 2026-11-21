-- severity: error
-- Every night in fact_daily_occupancy and every arrival date in fact_booking must have weather
-- for that same hotel (missing = the weather source does not cover the booking data's date range).
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
