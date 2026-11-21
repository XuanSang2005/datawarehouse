-- =============================================================================
-- gold.ml_demand_forecast — Weekly room-nights forecast for each hotel (E4)
-- Grain : 1 row = 1 hotel × 1 week (Monday starting the week) × 1 model version
--         (column contract: docs/STAR_SCHEMA.md section 7)
-- Written by: python -m ml.forecast.train (NOT run by etl/run_pipeline.py)
--   - Contains the 2017 backtest period (actual_room_nights populated) and the future weeks
--     after the data ends (actual_room_nights = NULL).
--   - model_version also identifies the model type (e.g. forecast_gbm_v1, forecast_seasonal_naive_v1)
--     so the FE can compare the main model with the baseline; matches gold.ml_model_metrics.model_version.
--   - Idempotent: the script deletes the rows with its model_version and rewrites them.
-- No FK to dim_hotel / dim_date is declared because gold is rebuilt with DROP ... CASCADE.
-- =============================================================================

CREATE TABLE IF NOT EXISTS gold.ml_demand_forecast (
    hotel_key              INT            NOT NULL,   -- → gold.dim_hotel.hotel_key
    week_start_date        DATE           NOT NULL,   -- → gold.dim_date.week_start_date (Monday)
    model_version          TEXT           NOT NULL,
    predicted_room_nights  NUMERIC(10, 1) NOT NULL,
    lower_bound            NUMERIC(10, 1) NOT NULL,   -- lower bound of the 80% interval
    upper_bound            NUMERIC(10, 1) NOT NULL,   -- upper bound of the 80% interval
    actual_room_nights     INT,                       -- NULL for future weeks / partial weeks
    horizon_weeks          SMALLINT       NOT NULL,   -- how many weeks ahead (1 = next week)
    created_at             TIMESTAMPTZ    NOT NULL DEFAULT now(),
    PRIMARY KEY (hotel_key, week_start_date, model_version),
    CHECK (lower_bound <= predicted_room_nights AND predicted_room_nights <= upper_bound)
);
