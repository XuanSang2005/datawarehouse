-- =============================================================================
-- gold.ml_demand_forecast — Dự báo room-nights theo tuần cho từng khách sạn (E4)
-- Grain : 1 dòng = 1 khách sạn × 1 tuần (Thứ Hai đầu tuần) × 1 phiên bản model
--         (giao kèo cột: docs/STAR_SCHEMA.md mục 7)
-- Ghi bởi: python -m ml.forecast.train (KHÔNG chạy bởi etl/run_pipeline.py)
--   - Gồm giai đoạn backtest 2017 (actual_room_nights có giá trị) và các tuần tương lai
--     sau dữ liệu (actual_room_nights = NULL).
--   - model_version định danh luôn loại model (vd forecast_gbm_v1, forecast_seasonal_naive_v1)
--     để FE so sánh model chính với baseline; khớp cột model_version của gold.ml_model_metrics.
--   - Idempotent: script xóa các dòng có model_version của nó rồi ghi lại.
-- Không khai báo FK tới dim_hotel / dim_date vì gold được dựng lại bằng DROP ... CASCADE.
-- =============================================================================

CREATE TABLE IF NOT EXISTS gold.ml_demand_forecast (
    hotel_key              INT            NOT NULL,   -- → gold.dim_hotel.hotel_key
    week_start_date        DATE           NOT NULL,   -- → gold.dim_date.week_start_date (Thứ Hai)
    model_version          TEXT           NOT NULL,
    predicted_room_nights  NUMERIC(10, 1) NOT NULL,
    lower_bound            NUMERIC(10, 1) NOT NULL,   -- cận dưới khoảng dự báo 80%
    upper_bound            NUMERIC(10, 1) NOT NULL,   -- cận trên khoảng dự báo 80%
    actual_room_nights     INT,                       -- NULL nếu là tuần tương lai / tuần thiếu ngày
    horizon_weeks          SMALLINT       NOT NULL,   -- dự báo trước bao nhiêu tuần (1 = tuần kế tiếp)
    created_at             TIMESTAMPTZ    NOT NULL DEFAULT now(),
    PRIMARY KEY (hotel_key, week_start_date, model_version),
    CHECK (lower_bound <= predicted_room_nights AND predicted_room_nights <= upper_bound)
);
