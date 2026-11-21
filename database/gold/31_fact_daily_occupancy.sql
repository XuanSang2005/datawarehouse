-- =============================================================================
-- gold.fact_daily_occupancy — Periodic snapshot: số phòng có khách mỗi đêm ở mỗi khách sạn
-- Nguồn : gold.fact_booking "nở" theo từng đêm lưu trú (generate_series), gom theo khách sạn × đêm.
--         Lưới dày đặc dim_hotel × dim_date: đêm không có khách vẫn có dòng (giá trị 0).
-- Grain : 1 dòng = 1 khách sạn × 1 đêm lưu trú. PK (hotel_key, stay_date_key)
-- Phạm vi: từ ngày đến sớm nhất đến ngày đến muộn nhất trong fact_booking (2015-07-01 → 2017-08-31).
--   Sau đó bị thiếu (không có booking đến từ 09/2017). Các đêm đầu 07/2015 hơi thấp vì thiếu khách
--   đến trước 2015-07-01 mà ở vắt sang.
-- Giả định: 1 booking = 1 phòng.
-- Occupancy / RevPAR tính ở backend từ công suất người dùng nhập (không lưu ở đây).
-- lost_revenue ở đây là thiệt hại GỘP theo đêm (chưa trừ tiền cọc giữ lại).
-- =============================================================================

DROP TABLE IF EXISTS gold.fact_daily_occupancy CASCADE;

CREATE TABLE gold.fact_daily_occupancy AS
WITH bookings AS (
    SELECT f.hotel_key, f.is_canceled, f.guests, f.adr, f.total_nights,
           arr.full_date AS arrival_date, dep.full_date AS departure_date
    FROM gold.fact_booking AS f
    JOIN gold.dim_date AS arr ON arr.date_key = f.arrival_date_key
    JOIN gold.dim_date AS dep ON dep.date_key = f.departure_date_key
),
period AS (
    SELECT min(arrival_date) AS first_night, max(arrival_date) AS last_night FROM bookings
),
nights AS (
    -- Mỗi booking sinh total_nights dòng; booking 0 đêm không sinh dòng nào.
    SELECT b.hotel_key, b.arrival_date + i AS stay_date, b.is_canceled, b.guests, b.adr
    FROM bookings AS b
    CROSS JOIN LATERAL generate_series(0, b.total_nights - 1) AS i
),
night_agg AS (
    SELECT
        hotel_key,
        stay_date,
        count(*) FILTER (WHERE is_canceled = 0)      AS rooms_occupied,
        count(*) FILTER (WHERE is_canceled = 1)      AS rooms_canceled,
        sum(guests) FILTER (WHERE is_canceled = 0)   AS guests_in_house,
        sum(adr) FILTER (WHERE is_canceled = 0)      AS realized_revenue,
        sum(adr) FILTER (WHERE is_canceled = 1)      AS lost_revenue
    FROM nights
    GROUP BY hotel_key, stay_date
),
arrivals AS (
    SELECT hotel_key, arrival_date AS stay_date, count(*) AS arrivals
    FROM bookings WHERE is_canceled = 0
    GROUP BY hotel_key, arrival_date
),
departures AS (
    SELECT hotel_key, departure_date AS stay_date, count(*) AS departures
    FROM bookings WHERE is_canceled = 0
    GROUP BY hotel_key, departure_date
),
grid AS (
    SELECT h.hotel_key, d.date_key, d.full_date
    FROM gold.dim_hotel AS h
    CROSS JOIN gold.dim_date AS d
    CROSS JOIN period
    WHERE d.full_date BETWEEN period.first_night AND period.last_night
)
SELECT
    g.hotel_key,
    g.date_key                                                         AS stay_date_key,
    COALESCE(n.rooms_occupied, 0)::INT                                 AS rooms_occupied,
    COALESCE(n.rooms_canceled, 0)::INT                                 AS rooms_canceled,
    (COALESCE(n.rooms_occupied, 0) + COALESCE(n.rooms_canceled, 0))::INT AS rooms_booked,
    COALESCE(n.guests_in_house, 0)::INT                                AS guests_in_house,
    COALESCE(a.arrivals, 0)::INT                                       AS arrivals,
    COALESCE(dp.departures, 0)::INT                                    AS departures,
    COALESCE(n.realized_revenue, 0)::NUMERIC(12, 2)                    AS realized_revenue,
    COALESCE(n.lost_revenue, 0)::NUMERIC(12, 2)                        AS lost_revenue
FROM grid AS g
LEFT JOIN night_agg  AS n  ON n.hotel_key = g.hotel_key  AND n.stay_date = g.full_date
LEFT JOIN arrivals   AS a  ON a.hotel_key = g.hotel_key  AND a.stay_date = g.full_date
LEFT JOIN departures AS dp ON dp.hotel_key = g.hotel_key AND dp.stay_date = g.full_date;

ALTER TABLE gold.fact_daily_occupancy ADD PRIMARY KEY (hotel_key, stay_date_key);

ALTER TABLE gold.fact_daily_occupancy
    ADD CONSTRAINT fk_fact_occupancy_hotel FOREIGN KEY (hotel_key)     REFERENCES gold.dim_hotel (hotel_key),
    ADD CONSTRAINT fk_fact_occupancy_date  FOREIGN KEY (stay_date_key) REFERENCES gold.dim_date (date_key);
