-- =============================================================================
-- gold.ml_booking_risk: Xác suất hủy của từng booking (Epic E3)
-- Grain : 1 dòng = 1 booking × 1 phiên bản model (giao kèo: docs/STAR_SCHEMA.md mục 7)
-- Ghi bởi: python -m ml.cancellation.train (chạy file này qua etl.db.run_sql_file trước khi ghi).
--   Script xóa các dòng cùng model_version rồi ghi lại → chạy lại không nhân đôi dòng.
-- File trong database/ml/ KHÔNG chạy bởi etl/run_pipeline.py, nên phải idempotent và KHÔNG DROP.
-- booking_id tham chiếu gold.fact_booking(booking_id) nhưng KHÔNG khai báo FK:
--   gold/30_fact_booking.sql dùng DROP ... CASCADE, FK sẽ bị xóa theo mỗi lần chạy pipeline.
--   Ghép với fact bằng JOIN ... USING (booking_id).
-- =============================================================================

CREATE TABLE IF NOT EXISTS gold.ml_booking_risk (
    booking_id          BIGINT       NOT NULL,           -- = gold.fact_booking.booking_id
    model_version       TEXT         NOT NULL,           -- vd: cancellation_v1
    cancel_probability  NUMERIC(5, 4) NOT NULL
        CHECK (cancel_probability BETWEEN 0 AND 1),
    risk_band           TEXT         NOT NULL
        CHECK (risk_band IN ('Low', 'Medium', 'High')),  -- ngưỡng: gold.ml_model_metrics (threshold_*)
    is_test_set         BOOLEAN      NOT NULL,           -- TRUE: arrival_date >= 2017-01-01 (model chưa thấy)
    scored_at           TIMESTAMPTZ  NOT NULL DEFAULT now(),
    PRIMARY KEY (booking_id, model_version)
);

CREATE INDEX IF NOT EXISTS ix_ml_booking_risk_version_band
    ON gold.ml_booking_risk (model_version, risk_band);
