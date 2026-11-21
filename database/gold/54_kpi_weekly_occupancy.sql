-- =============================================================================
-- gold.kpi_weekly_occupancy — Occupied rooms per hotel × ISO week (Demand Forecast and What-if pages)
-- Source: gold.fact_daily_occupancy + dim_hotel + dim_date (stay night)
-- Grain : 1 row = 1 hotel × 1 ISO week
-- days_in_week < 7 in the first/last week of the data (partial weeks): is_complete_week = false,
-- these should be excluded from the forecast training data.
-- ADR is recomputed from totals (rule 8).
-- =============================================================================

DROP VIEW IF EXISTS gold.kpi_weekly_occupancy;

CREATE VIEW gold.kpi_weekly_occupancy AS
SELECT
    h.hotel_key,
    h.hotel_name,
    d.iso_year,
    d.iso_week,
    d.week_start_date,
    count(*)                                                                AS days_in_week,
    (count(*) = 7)                                                          AS is_complete_week,
    sum(o.rooms_occupied)                                                   AS room_nights_sold,
    sum(o.rooms_canceled)                                                   AS room_nights_canceled,
    sum(o.rooms_booked)                                                     AS room_nights_booked,
    sum(o.guests_in_house)                                                  AS guest_nights,
    sum(o.arrivals)                                                         AS arrivals,
    sum(o.realized_revenue)                                                 AS realized_revenue,
    sum(o.lost_revenue)                                                     AS lost_revenue,
    round(sum(o.realized_revenue) / NULLIF(sum(o.rooms_occupied), 0), 2)    AS adr,
    round(sum(o.rooms_canceled)::NUMERIC / NULLIF(sum(o.rooms_booked), 0), 4) AS night_cancellation_rate
FROM gold.fact_daily_occupancy AS o
JOIN gold.dim_hotel AS h ON h.hotel_key = o.hotel_key
JOIN gold.dim_date AS d  ON d.date_key = o.stay_date_key
GROUP BY h.hotel_key, h.hotel_name, d.iso_year, d.iso_week, d.week_start_date;
