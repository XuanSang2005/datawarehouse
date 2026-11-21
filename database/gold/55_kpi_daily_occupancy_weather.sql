-- =============================================================================
-- gold.kpi_daily_occupancy_weather — Occupied rooms + calendar (holidays, weekends) + weather per hotel × night
-- Source: gold.fact_daily_occupancy 1:1 JOIN gold.fact_daily_weather (drill-across via hotel_key + date)
--         + dim_hotel + dim_date
-- Grain : 1 row = 1 hotel × 1 stay night (same row count as fact_daily_occupancy: 1,586)
-- Used for: analysing the effect of weather / holidays on demand, features for demand forecasting.
-- ADR is recomputed from totals (rule 8).
-- =============================================================================

DROP VIEW IF EXISTS gold.kpi_daily_occupancy_weather;

CREATE VIEW gold.kpi_daily_occupancy_weather AS
SELECT
    o.hotel_key,
    h.hotel_name,
    o.stay_date_key,
    d.full_date                                                          AS stay_date,
    d.day_of_week,
    d.is_weekend,
    d.is_holiday,
    d.holiday_name,
    d.season,
    o.rooms_occupied,
    o.rooms_canceled,
    o.rooms_booked,
    o.guests_in_house,
    o.arrivals,
    o.departures,
    o.realized_revenue,
    o.lost_revenue,
    round(o.realized_revenue / NULLIF(o.rooms_occupied, 0), 2)           AS adr,
    w.weather_group,
    w.temp_max_c,
    w.temp_mean_c,
    w.precipitation_mm,
    w.sunshine_hours,
    w.wind_speed_max_kmh,
    w.is_rainy_day
FROM gold.fact_daily_occupancy AS o
JOIN gold.dim_hotel AS h ON h.hotel_key = o.hotel_key
JOIN gold.dim_date  AS d ON d.date_key = o.stay_date_key
LEFT JOIN gold.fact_daily_weather AS w
       ON w.hotel_key = o.hotel_key AND w.date_key = o.stay_date_key;
