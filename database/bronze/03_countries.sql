-- =============================================================================
-- bronze.countries — Bảng mã quốc gia ISO 3166-1 + phân vùng UN M49 (nguyên bản)
-- Nguồn : github.com/lukes/ISO-3166-Countries-with-Regional-Codes (all/all.csv)
-- Grain : 1 dòng = 1 quốc gia / vùng lãnh thổ
-- Tên cột giữ nguyên header CSV (có dấu gạch ngang nên phải đặt trong dấu ngoặc kép).
-- Dùng để làm giàu gold.dim_country (tên nước, châu lục).
-- =============================================================================

DROP TABLE IF EXISTS bronze.countries;

CREATE TABLE bronze.countries (
    "name"                     TEXT,
    "alpha-2"                  TEXT,
    "alpha-3"                  TEXT,
    "country-code"             TEXT,
    "iso_3166-2"               TEXT,
    "region"                   TEXT,
    "sub-region"               TEXT,
    "intermediate-region"      TEXT,
    "region-code"              TEXT,
    "sub-region-code"          TEXT,
    "intermediate-region-code" TEXT,
    _source_row                BIGINT,
    _source_file               TEXT,
    _loaded_at                 TIMESTAMPTZ NOT NULL DEFAULT now()
);
