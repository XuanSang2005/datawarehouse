-- severity: warning
-- Days with weather but missing mean temperature or precipitation (the API returned null).
SELECT location, weather_date, temp_mean_c, precipitation_mm
FROM silver.weather_daily
WHERE temp_mean_c IS NULL OR precipitation_mm IS NULL;
