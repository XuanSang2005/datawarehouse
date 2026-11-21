-- =============================================================================
-- gold.ml_model_metrics — Evaluation metrics of the models in ml/
-- Grain : 1 row = 1 model version × 1 metric (contract: docs/STAR_SCHEMA.md section 7)
-- SHARED table between E3 (cancellation prediction) and E4 (demand forecasting):
--   - Do NOT DROP this table. Each script only deletes/rewrites the rows with its own model_name.
-- Files in database/ml/ are NOT run by etl/run_pipeline.py; the scripts in ml/ call them
--   (etl.db.run_sql_file) before writing results. Hence they must be idempotent.
-- =============================================================================

CREATE TABLE IF NOT EXISTS gold.ml_model_metrics (
    model_version  TEXT        NOT NULL,
    model_name     TEXT        NOT NULL,            -- e.g. cancellation_logreg, cancellation_gbm, forecast_seasonal_naive
    metric_name    TEXT        NOT NULL,            -- auc, precision, recall, f1, mape, ...
    metric_value   NUMERIC(12, 6) NOT NULL,
    dataset        TEXT        NOT NULL DEFAULT 'test',  -- test / backtest / train
    trained_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (model_version, model_name, metric_name, dataset)
);
