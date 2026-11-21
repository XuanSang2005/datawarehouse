-- =============================================================================
-- gold.kpi_weekly_occupancy — Phòng có khách theo khách sạn × tuần ISO (trang Dự báo nhu cầu, What-if)
-- Nguồn : gold.fact_daily_occupancy + dim_hotel + dim_date (đêm lưu trú)
-- Grain : 1 dòng = 1 khách sạn × 1 tuần ISO
-- days_in_week < 7 ở tuần đầu/cuối dữ liệu (tuần không đủ ngày): is_complete_week = false,
-- nên loại khỏi dữ liệu train dự báo.
-- ADR tính lại từ tổng (quy tắc 8).
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
