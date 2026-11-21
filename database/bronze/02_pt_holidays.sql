-- =============================================================================
-- bronze.pt_holidays — Portuguese national holidays (generated with the Python `holidays` library)
-- Grain : 1 row = 1 holiday
-- Used to enrich Dim_Date (is_holiday) in the Gold layer.
-- =============================================================================

DROP TABLE IF EXISTS bronze.pt_holidays;

CREATE TABLE bronze.pt_holidays (
    holiday_date TEXT,
    holiday_name TEXT,
    _source_row  BIGINT,
    _source_file TEXT,
    _loaded_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
