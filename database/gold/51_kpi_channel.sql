-- =============================================================================
-- gold.kpi_channel — KPIs per hotel × channel group × arrival month (Sales & Marketing, goal G5)
-- Source: gold.fact_booking + dim_hotel + dim_channel + dim_date (arrival date role)
-- Grain : 1 row = 1 hotel × 1 channel_group × 1 arrival month
-- Non-additive measures (cancellation_rate, adr, avg_los) are recomputed from totals (rule 8).
-- Common columns: bookings, canceled_bookings, cancellation_rate, room_nights_sold, realized_revenue,
--            lost_revenue, net_lost_revenue, adr, avg_lead_time, avg_los
-- =============================================================================

DROP VIEW IF EXISTS gold.kpi_channel;

CREATE VIEW gold.kpi_channel AS
SELECT
    h.hotel_key,
    h.hotel_name,
    ch.channel_group,
    arr.year,
    arr.month,
    arr.year_month,
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
JOIN gold.dim_channel AS ch ON ch.channel_key = f.channel_key
JOIN gold.dim_date AS arr   ON arr.date_key = f.arrival_date_key
GROUP BY h.hotel_key, h.hotel_name, ch.channel_group, arr.year, arr.month, arr.year_month;
