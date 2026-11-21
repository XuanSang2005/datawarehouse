-- =============================================================================
-- bronze.pt_holidays — Ngày lễ quốc gia Bồ Đào Nha (sinh từ thư viện Python `holidays`)
-- Grain : 1 dòng = 1 ngày lễ
-- Dùng để làm giàu Dim_Date (is_holiday) ở lớp Gold.
-- =============================================================================

DROP TABLE IF EXISTS bronze.pt_holidays;

CREATE TABLE bronze.pt_holidays (
    holiday_date TEXT,
    holiday_name TEXT,
    _source_row  BIGINT,
    _source_file TEXT,
    _loaded_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
