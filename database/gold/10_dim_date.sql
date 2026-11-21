-- =============================================================================
-- gold.dim_date — Date dimension (role-playing, conformed)
-- Source: generate_series 2013-01-01 → 2018-12-31 + silver.pt_holidays
-- Grain : 1 row = 1 calendar day (2,191 rows)
-- Main transformations:
--   * date_key = YYYYMMDD
--   * ISO week computed from the date. Do NOT use the source's arrival_date_week_number (inconsistent, see STAR_SCHEMA.md)
--   * season: High = Jul–Aug, Shoulder = Apr–Jun and Sep–Oct, Low = Nov–Mar (based on the Resort's observed ADR)
-- Roles in fact_booking: booking_date_key, arrival_date_key, departure_date_key, status_date_key.
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
    EXTRACT(ISODOW FROM full_date)::SMALLINT                  AS day_of_week,     -- 1 = Monday … 7 = Sunday
    to_char(full_date, 'FMDay')                               AS day_name,
    EXTRACT(ISODOW FROM full_date) IN (6, 7)                  AS is_weekend,
    EXTRACT(WEEK FROM full_date)::SMALLINT                    AS iso_week,
    EXTRACT(ISOYEAR FROM full_date)::SMALLINT                 AS iso_year,
    date_trunc('week', full_date)::DATE                       AS week_start_date, -- Monday starting the week
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
