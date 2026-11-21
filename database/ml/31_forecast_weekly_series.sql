-- =============================================================================
-- Chuỗi tuần cho dự báo nhu cầu (E4) — chỉ SELECT, đọc bởi ml/forecast/train.py
-- Grain : 1 dòng = 1 khách sạn × 1 tuần lịch (Thứ Hai đầu tuần = gold.dim_date.week_start_date)
-- Phạm vi: từ tuần chứa đêm dữ liệu đầu tiên đến tuần đầy đủ cuối cùng của dim_date (2018-12),
--   để có sẵn đặc trưng lịch (tuần trong năm, ngày lễ) cho các tuần tương lai.
-- Cột:
--   room_nights   : tổng rooms_occupied (booking không hủy) trong các đêm CÓ dữ liệu của tuần;
--                   NULL nếu tuần nằm ngoài phạm vi fact_daily_occupancy.
--   days_observed : số đêm của tuần có trong fact_daily_occupancy. < 7 ở tuần biên
--                   (2015-06-29 chỉ có 5 đêm, 2017-08-28 chỉ có 4 đêm) → Python loại khỏi train
--                   và không dùng làm actual.
--   n_holidays    : số ngày lễ Bồ Đào Nha trong tuần (dim_date.is_holiday).
--   iso_week      : tuần ISO của Thứ Hai đầu tuần (1..53).
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
