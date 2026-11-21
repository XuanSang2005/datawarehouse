-- =============================================================================
-- gold.dim_date — Dimension ngày (role-playing, conformed)
-- Nguồn : generate_series 2013-01-01 → 2018-12-31 + silver.pt_holidays
-- Grain : 1 dòng = 1 ngày lịch (2.191 dòng)
-- Biến đổi chính:
--   * date_key = YYYYMMDD
--   * Tuần ISO tự tính từ ngày. KHÔNG dùng arrival_date_week_number của nguồn (sai lệch, xem STAR_SCHEMA.md)
--   * season: High = T7–8, Shoulder = T4–6 và T9–10, Low = T11–3 (theo ADR đo được của Resort)
-- Vai trong fact_booking: booking_date_key, arrival_date_key, departure_date_key, status_date_key.
-- =============================================================================

DROP TABLE IF EXISTS gold.dim_date CASCADE;

CREATE TABLE gold.dim_date AS
WITH days AS (
    SELECT d::DATE AS full_date
    FROM generate_series('2013-01-01'::DATE, '2018-12-31'::DATE, INTERVAL '1 day') AS g(d)
)
SELECT
    to_char(full_date, 'YYYYMMDD')::INT                       AS date_key,
    full_date,
    EXTRACT(DAY FROM full_date)::SMALLINT                     AS day_of_month,
    EXTRACT(ISODOW FROM full_date)::SMALLINT                  AS day_of_week,     -- 1 = Thứ Hai … 7 = Chủ Nhật
    to_char(full_date, 'FMDay')                               AS day_name,
    EXTRACT(ISODOW FROM full_date) IN (6, 7)                  AS is_weekend,
    EXTRACT(WEEK FROM full_date)::SMALLINT                    AS iso_week,
    EXTRACT(ISOYEAR FROM full_date)::SMALLINT                 AS iso_year,
    date_trunc('week', full_date)::DATE                       AS week_start_date, -- Thứ Hai đầu tuần
    EXTRACT(MONTH FROM full_date)::SMALLINT                   AS month,
    to_char(full_date, 'FMMonth')                             AS month_name,
    EXTRACT(QUARTER FROM full_date)::SMALLINT                 AS quarter,
    EXTRACT(YEAR FROM full_date)::SMALLINT                    AS year,
    to_char(full_date, 'YYYY-MM')                             AS year_month,
    CASE
        WHEN EXTRACT(MONTH FROM full_date) IN (7, 8)            THEN 'High'
        WHEN EXTRACT(MONTH FROM full_date) IN (4, 5, 6, 9, 10)  THEN 'Shoulder'
        ELSE 'Low'
    END                                                       AS season,
    (h.holiday_date IS NOT NULL)                              AS is_holiday,
    h.holiday_name
FROM days
LEFT JOIN silver.pt_holidays AS h ON h.holiday_date = days.full_date;

ALTER TABLE gold.dim_date ADD PRIMARY KEY (date_key);
ALTER TABLE gold.dim_date ADD CONSTRAINT uq_dim_date_full_date UNIQUE (full_date);
