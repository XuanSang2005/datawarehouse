-- =============================================================================
-- silver.countries — Mã quốc gia đã đổi tên cột về snake_case, chuẩn hóa rỗng thành NULL.
-- Nguồn : bronze.countries
-- Grain : 1 dòng = 1 quốc gia (khóa: country_code = ISO alpha-3)
-- Biến đổi chính:
--   * '' -> NULL
--   * Bổ sung vùng cho 2 mã mà UN M49 để trống nhưng có trong dữ liệu booking:
--     TWN (Đài Loan) -> Asia / Eastern Asia; ATA (Nam Cực) -> Antarctica
-- =============================================================================

DROP TABLE IF EXISTS silver.countries;

CREATE TABLE silver.countries AS
SELECT
    "alpha-3"                                                AS country_code,
    "alpha-2"                                                AS country_code_alpha2,
    "name"                                                   AS country_name,
    CASE "alpha-3"
        WHEN 'TWN' THEN 'Asia'
        WHEN 'ATA' THEN 'Antarctica'
        ELSE NULLIF("region", '')
    END                                                      AS region,
    CASE "alpha-3"
        WHEN 'TWN' THEN 'Eastern Asia'
        WHEN 'ATA' THEN 'Antarctica'
        ELSE NULLIF("sub-region", '')
    END                                                      AS sub_region
FROM bronze.countries;

ALTER TABLE silver.countries ADD PRIMARY KEY (country_code);
