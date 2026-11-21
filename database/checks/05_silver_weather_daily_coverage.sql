-- severity: error
-- Each location must have EXACTLY 1 row per day with no gaps (the PK blocks duplicates,
-- this check blocks gaps), and both locations that gold.dim_hotel needs (Lisbon, Faro) must exist.
WITH expected_locations AS (
    SELECT unnest(ARRAY['Lisbon', 'Faro']) AS location
),
stats AS (
    SELECT location, min(weather_date) AS first_day, max(weather_date) AS last_day, count(*) AS days
    FROM silver.weather_daily
    GROUP BY location
)
SELECT e.location, s.first_day, s.last_day, s.days,
       (s.last_day - s.first_day + 1) AS expected_days
FROM expected_locations AS e
LEFT JOIN stats AS s ON s.location = e.location
WHERE s.location IS NULL
   OR s.days <> (s.last_day - s.first_day + 1);
