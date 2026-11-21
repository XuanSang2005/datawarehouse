-- =============================================================================
-- Weekly series for demand forecasting (E4) — SELECT only, read by ml/forecast/train.py
-- Grain : 1 row = 1 hotel × 1 calendar week (Monday starting the week = gold.dim_date.week_start_date)
-- Range : from the week containing the first night of data to the last complete week of dim_date (2018-12),
--   so calendar features (week of year, holidays) are available for future weeks.
-- Columns:
--   room_nights   : sum of rooms_occupied (non-canceled bookings) over the nights of the week that HAVE data;
--                   NULL if the week is outside the range of fact_daily_occupancy.
--   days_observed : number of nights of the week present in fact_daily_occupancy. < 7 for edge weeks
--                   (2015-06-29 has only 5 nights, 2017-08-28 only 4 nights) → Python excludes them from training
--                   and does not use them as actuals.
--   n_holidays    : number of Portuguese holidays in the week (dim_date.is_holiday).
--   iso_week      : ISO week of the week's Monday (1..53).
-- =============================================================================

WITH weeks AS (
    SELECT
        d.week_start_date,
        min(d.iso_year) FILTER (WHERE d.day_of_week = 1)  AS iso_year,
        min(d.iso_week) FILTER (WHERE d.day_of_week = 1)  AS iso_week,
        count(*) FILTER (WHERE d.is_holiday)              AS n_holidays,
        count(*)                                          AS days_in_calendar
    FROM gold.dim_date AS d
    GROUP BY d.week_start_date
),
occupancy AS (
    SELECT
        o.hotel_key,
        d.week_start_date,
        sum(o.rooms_occupied)  AS room_nights,
        count(*)               AS days_observed
    FROM gold.fact_daily_occupancy AS o
    JOIN gold.dim_date AS d ON d.date_key = o.stay_date_key
    GROUP BY o.hotel_key, d.week_start_date
)
SELECT
    h.hotel_key,
    h.hotel_name,
    h.hotel_type,
    w.week_start_date,
    w.iso_year::INT                         AS iso_year,
    w.iso_week::INT                         AS iso_week,
    w.n_holidays::INT                       AS n_holidays,
    o.room_nights::INT                      AS room_nights,
    COALESCE(o.days_observed, 0)::INT       AS days_observed
FROM gold.dim_hotel AS h
CROSS JOIN weeks AS w
LEFT JOIN occupancy AS o
       ON o.hotel_key = h.hotel_key AND o.week_start_date = w.week_start_date
WHERE w.days_in_calendar = 7
  AND w.week_start_date >= (SELECT min(week_start_date) FROM occupancy)
ORDER BY h.hotel_key, w.week_start_date;
