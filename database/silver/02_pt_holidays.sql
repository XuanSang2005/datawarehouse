-- =============================================================================
-- silver.pt_holidays — Ngày lễ đã ép kiểu, 1 dòng / 1 ngày (gộp tên nếu trùng ngày).
-- Nguồn : bronze.pt_holidays
-- =============================================================================

DROP TABLE IF EXISTS silver.pt_holidays;

CREATE TABLE silver.pt_holidays AS
SELECT
    holiday_date::DATE                                    AS holiday_date,
    string_agg(DISTINCT holiday_name, '; ')               AS holiday_name
FROM bronze.pt_holidays
GROUP BY holiday_date::DATE;

ALTER TABLE silver.pt_holidays ADD PRIMARY KEY (holiday_date);
