-- =============================================================================
-- 01_meta_tables.sql — Bảng log của pipeline.
-- Khi pipeline lỗi: SELECT * FROM meta.etl_run_log ORDER BY log_id DESC LIMIT 20;
-- =============================================================================

CREATE TABLE IF NOT EXISTS meta.etl_run_log (
    log_id        BIGSERIAL PRIMARY KEY,
    run_id        UUID        NOT NULL,              -- 1 lần chạy pipeline = 1 run_id
    step          TEXT        NOT NULL,              -- vd: bronze, silver/01_hotel_bookings.sql
    status        TEXT        NOT NULL CHECK (status IN ('running', 'success', 'warning', 'failed')),
    rows_affected BIGINT,
    message       TEXT,
    started_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at   TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_etl_run_log_run_id ON meta.etl_run_log (run_id);
