-- =============================================================================
-- gold.ml_model_metrics — Metric đánh giá của các mô hình trong ml/
-- Grain : 1 dòng = 1 phiên bản model × 1 metric (giao kèo: docs/STAR_SCHEMA.md mục 7)
-- Bảng DÙNG CHUNG giữa E3 (dự đoán hủy) và E4 (dự báo nhu cầu):
--   - KHÔNG DROP bảng này. Mỗi script chỉ xóa/ghi lại các dòng có model_name của chính nó.
-- File trong database/ml/ KHÔNG chạy bởi etl/run_pipeline.py, mà do script trong ml/ gọi
--   (etl.db.run_sql_file) trước khi ghi kết quả. Vì vậy phải idempotent.
-- =============================================================================

CREATE TABLE IF NOT EXISTS gold.ml_model_metrics (
    model_version  TEXT        NOT NULL,
    model_name     TEXT        NOT NULL,            -- vd: cancellation_logreg, cancellation_gbm, forecast_seasonal_naive
    metric_name    TEXT        NOT NULL,            -- auc, precision, recall, f1, mape, ...
    metric_value   NUMERIC(12, 6) NOT NULL,
    dataset        TEXT        NOT NULL DEFAULT 'test',  -- test / backtest / train
    trained_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (model_version, model_name, metric_name, dataset)
);
