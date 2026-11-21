-- =============================================================================
-- gold.kpi_cancellation_profile — Cancellation rate by lead time band × deposit type × channel group (Cancellation Risk page)
-- Source: gold.fact_booking + dim_hotel + dim_booking_profile + dim_channel
-- Grain : 1 row = 1 hotel × 1 lead time band × 1 deposit_type × 1 channel_group
-- Lead time bands: 0–7, 8–30, 31–90, 91–180, 181–365, >365 days (lead_time_band_order for sorting)
-- Non-additive measures (cancellation_rate, adr, avg_los) are recomputed from totals (rule 8).
-- Common columns: bookings, canceled_bookings, cancellation_rate, room_nights_sold, realized_revenue,
--            lost_revenue, net_lost_revenue, adr, avg_lead_time, avg_los
-- =============================================================================

DROP VIEW IF EXISTS gold.kpi_cancellation_profile;

CREATE VIEW gold.kpi_cancellation_profile AS
WITH banded AS (
    SELECT
        f.*,
        CASE
            WHEN f.lead_time <= 7   THEN 1
            WHEN f.lead_time <= 30  THEN 2
            WHEN f.lead_time <= 90  THEN 3
            WHEN f.lead_time <= 180 THEN 4
            WHEN f.lead_time <= 365 THEN 5
            ELSE 6
        END AS lead_time_band_order
    FROM gold.fact_booking AS f
)
SELECT
    h.hotel_key,
    h.hotel_name,
    f.lead_time_band_order,
    (ARRAY['0-7', '8-30', '31-90', '91-180', '181-365', '>365'])[f.lead_time_band_order] AS lead_time_band,
    bp.deposit_type,
    ch.channel_group,
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
FROM banded AS f
JOIN gold.dim_hotel AS h            ON h.hotel_key = f.hotel_key
JOIN gold.dim_booking_profile AS bp ON bp.booking_profile_key = f.booking_profile_key
JOIN gold.dim_channel AS ch         ON ch.channel_key = f.channel_key
GROUP BY h.hotel_key, h.hotel_name, f.lead_time_band_order, bp.deposit_type, ch.channel_group;
