-- =============================================================================
-- silver.pt_holidays — Typed holidays, 1 row per day (names merged when dates collide).
-- Source: bronze.pt_holidays
-- =============================================================================

DROP TABLE IF EXISTS silver.pt_holidays;

CREATE TABLE silver.pt_holidays AS
SELECT
    holiday_date::DATE                                    AS holiday_date,
    string_agg(DISTINCT holiday_name, '; ')               AS holiday_name
FROM bronze.pt_holidays
GROUP BY holiday_date::DATE;

ALTER TABLE silver.pt_holidays ADD PRIMARY KEY (holiday_date);
