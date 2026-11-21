-- =============================================================================
-- 01_meta_tables.sql — Pipeline log table.
-- When the pipeline fails: SELECT * FROM meta.etl_run_log ORDER BY log_id DESC LIMIT 20;
-- =============================================================================

CREATE TABLE IF NOT EXISTS meta.etl_run_log (
    log_id        BIGSERIAL PRIMARY KEY,
    run_id        UUID        NOT NULL,              -- 1 pipeline run = 1 run_id
    step          TEXT        NOT NULL,              -- e.g. bronze, silver/01_hotel_bookings.sql
    status        TEXT        NOT NULL CHECK (status IN ('running', 'success', 'warning', 'failed')),
    rows_affected BIGINT,
    message       TEXT,
    started_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at   TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_etl_run_log_run_id ON meta.etl_run_log (run_id);
