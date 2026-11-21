-- =============================================================================
-- gold.ml_booking_risk: Cancellation probability of each booking (Epic E3)
-- Grain : 1 row = 1 booking × 1 model version (contract: docs/STAR_SCHEMA.md section 7)
-- Written by: python -m ml.cancellation.train (runs this file via etl.db.run_sql_file before writing).
--   The script deletes the rows with the same model_version and rewrites them → re-runs do not duplicate rows.
-- Files in database/ml/ are NOT run by etl/run_pipeline.py, so they must be idempotent and must NOT DROP.
-- booking_id references gold.fact_booking(booking_id) but NO FK is declared:
--   gold/30_fact_booking.sql uses DROP ... CASCADE, so the FK would be dropped on every pipeline run.
--   Join with the fact via JOIN ... USING (booking_id).
-- =============================================================================

CREATE TABLE IF NOT EXISTS gold.ml_booking_risk (
    booking_id          BIGINT       NOT NULL,           -- = gold.fact_booking.booking_id
    model_version       TEXT         NOT NULL,           -- e.g. cancellation_v1
    cancel_probability  NUMERIC(5, 4) NOT NULL
        CHECK (cancel_probability BETWEEN 0 AND 1),
    risk_band           TEXT         NOT NULL
        CHECK (risk_band IN ('Low', 'Medium', 'High')),  -- thresholds: gold.ml_model_metrics (threshold_*)
    is_test_set         BOOLEAN      NOT NULL,           -- TRUE: arrival_date >= 2017-01-01 (unseen by the model)
    scored_at           TIMESTAMPTZ  NOT NULL DEFAULT now(),
    PRIMARY KEY (booking_id, model_version)
);

CREATE INDEX IF NOT EXISTS ix_ml_booking_risk_version_band
    ON gold.ml_booking_risk (model_version, risk_band);
