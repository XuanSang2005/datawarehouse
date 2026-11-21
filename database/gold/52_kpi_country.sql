-- =============================================================================
-- gold.kpi_country — KPIs per hotel × country × arrival year (Sales & Marketing, goal G5)
-- Source: gold.fact_booking + dim_hotel + dim_country + dim_date (arrival date role)
-- Grain : 1 row = 1 hotel × 1 country × 1 arrival year
-- Non-additive measures (cancellation_rate, adr, avg_los) are recomputed from totals (rule 8).
-- Common columns: bookings, canceled_bookings, cancellation_rate, room_nights_sold, realized_revenue,
--            lost_revenue, net_lost_revenue, adr, avg_lead_time, avg_los
-- =============================================================================

DROP VIEW IF EXISTS gold.kpi_country;

CREATE VIEW gold.kpi_country AS
SELECT
    h.hotel_key,
    h.hotel_name,
    c.country_key,
    c.country_code,
    c.country_name,
    c.region,
    c.market_group,
    arr.year,
    sum(f.booking_count)                                                    AS bookings,
    sum(f.is_canceled)                                                      AS canceled_bookings,
    round(sum(f.is_canceled)::NUMERIC / NULLIF(sum(f.booking_count), 0), 4) AS cancellation_rate,
    sum(f.room_nights_sold)                                                 AS room_nights_sold,
    sum(f.realized_revenue)                                                 AS realized_revenue,
    sum(f.lost_revenue)                                                     AS lost_revenue,
    sum(f.net_lost_revenue)                                                 AS net_lost_revenue,
    round(sum(f.realized_revenue) / NULLIF(sum(f.room_nights_sold), 0), 2)  AS adr,
    round(avg(f.lead_time), 1)                                              AS avg_lead_time,
    round(sum(f.room_nights_sold)::NUMERIC
          / NULLIF(sum(f.booking_count) - sum(f.is_canceled), 0), 2)        AS avg_los
FROM gold.fact_booking AS f
JOIN gold.dim_hotel AS h    ON h.hotel_key = f.hotel_key
JOIN gold.dim_country AS c  ON c.country_key = f.country_key
JOIN gold.dim_date AS arr   ON arr.date_key = f.arrival_date_key
GROUP BY h.hotel_key, h.hotel_name, c.country_key, c.country_code, c.country_name, c.region,
         c.market_group, arr.year;
