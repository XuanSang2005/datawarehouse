-- severity: warning
-- Ngày có thời tiết nhưng thiếu nhiệt độ trung bình hoặc lượng mưa (API trả null).
SELECT location, weather_date, temp_mean_c, precipitation_mm
FROM silver.weather_daily
WHERE temp_mean_c IS NULL OR precipitation_mm IS NULL;
