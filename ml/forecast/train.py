"""E4: train + backtest dự báo room-nights theo tuần → gold.ml_demand_forecast, ml_model_metrics.

Chạy từ thư mục gốc repo:
    python -m ml.forecast.train            # backtest, dự báo tương lai, ghi DB
    python -m ml.forecast.train --dry-run  # chỉ in metric, không ghi DB

Thiết kế (chi tiết và hạn chế: ml/README.md):
- Chuỗi: room-nights bán được (booking không hủy) theo khách sạn × tuần (Thứ Hai đầu tuần),
  chỉ tuần đủ 7 đêm: 2015-07-06 → 2017-08-21 (112 tuần/khách sạn).
- 3 model: forecast_gbm (chính), forecast_seasonal_naive, forecast_moving_avg (baseline).
- Backtest rolling-origin, horizon 1..8 tuần, học lại ở mỗi origin:
    * cửa sổ calibration: tuần mục tiêu 2016-07-04 → 2016-12-26 → phân vị sai số cho khoảng 80%
    * cửa sổ test: tuần mục tiêu 2017-01-02 → tuần đầy đủ cuối (2017-08-21) → MAPE báo cáo
- Ghi bảng: dự báo h=1 cho các tuần test (có actual) + 8 tuần tương lai từ origin cuối
  (actual NULL; tuần 2017-08-28 chỉ có 4 đêm dữ liệu nên cũng coi là tương lai).
"""

from __future__ import annotations

import argparse
import logging
from datetime import UTC, datetime

import pandas as pd

from etl.config import DATABASE_DIR
from etl.db import connect, run_sql_file
from ml.forecast.backtest import apply_interval, residual_quantiles, rolling_origin, summarize
from ml.forecast.features import ONE_WEEK, prepare_series
from ml.forecast.models import GbmForecaster, PerHotelBaseline, moving_average, seasonal_naive

log = logging.getLogger("ml.forecast")

ML_SQL_DIR = DATABASE_DIR / "ml"
SERIES_SQL = ML_SQL_DIR / "31_forecast_weekly_series.sql"
DDL_FILES = [ML_SQL_DIR / "01_ml_model_metrics.sql", ML_SQL_DIR / "03_ml_demand_forecast.sql"]

VERSION_SUFFIX = "v1"
HORIZON = 8  # số tuần dự báo trước (backtest và tương lai)
STORE_HORIZON = 1  # horizon của dự báo backtest được ghi vào bảng
CALIB_WINDOW = (pd.Timestamp("2016-07-04"), pd.Timestamp("2016-12-26"))
TEST_START = pd.Timestamp("2017-01-02")
COVERAGE = 0.8

INSERT_FORECAST = """
INSERT INTO gold.ml_demand_forecast
    (hotel_key, week_start_date, model_version, predicted_room_nights,
     lower_bound, upper_bound, actual_room_nights, horizon_weeks, created_at)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
"""
INSERT_METRIC = """
INSERT INTO gold.ml_model_metrics
    (model_version, model_name, metric_name, metric_value, dataset, trained_at)
VALUES (%s, %s, %s, %s, %s, %s)
"""


def model_version(model_name: str) -> str:
    return f"{model_name}_{VERSION_SUFFIX}"


def load_series() -> pd.DataFrame:
    with connect() as conn, conn.cursor() as cur:
        cur.execute(SERIES_SQL.read_text(encoding="utf-8"))
        cols = [c.name for c in cur.description]
        return pd.DataFrame(cur.fetchall(), columns=cols)


def evaluate_model(forecaster, history, calendar, last_week):
    """Backtest calibration + test, dự báo tương lai. Trả về (bảng dự báo để ghi, test, calib)."""
    calib = rolling_origin(forecaster, history, calendar, *CALIB_WINDOW, HORIZON)
    test = rolling_origin(forecaster, history, calendar, TEST_START, last_week, HORIZON)
    # Khoảng cho tuần test chỉ dùng sai số của calibration (không nhìn trước kết quả test)
    test = apply_interval(test, residual_quantiles(calib, COVERAGE))
    # Khoảng cho tuần tương lai dùng mọi sai số backtest đã biết tại thời điểm dự báo
    future = forecaster.forecast(history, calendar, HORIZON).assign(actual=float("nan"))
    future = apply_interval(future, residual_quantiles(pd.concat([calib, test]), COVERAGE))
    stored = pd.concat([test[test["h"] == STORE_HORIZON], future], ignore_index=True)
    return stored, test, calib


def write_results(forecasts: pd.DataFrame, metrics: pd.DataFrame) -> None:
    trained_at = datetime.now(UTC)
    versions = sorted(forecasts["model_version"].unique())
    names = sorted(metrics["model_name"].unique())
    fc_rows = [
        (
            int(r.hotel_key),
            r.week_start_date.date(),
            r.model_version,
            round(float(r.yhat), 1),
            round(float(r.lower_bound), 1),
            round(float(r.upper_bound), 1),
            None if pd.isna(r.actual) else int(r.actual),
            int(r.h),
            trained_at,
        )
        for r in forecasts.itertuples(index=False)
    ]
    metric_rows = [
        (r.model_version, r.model_name, r.metric_name, round(float(r.metric_value), 6), r.dataset,
         trained_at)
        for r in metrics.itertuples(index=False)
    ]
    with connect() as conn:  # 1 transaction: lỗi giữa chừng thì không mất dữ liệu cũ
        for path in DDL_FILES:
            run_sql_file(conn, path)
        with conn.cursor() as cur:
            # Idempotent: chỉ xóa dòng của chính các model E4 (bảng metrics dùng chung với E3)
            cur.execute(
                "DELETE FROM gold.ml_demand_forecast WHERE model_version = ANY(%s)", (versions,)
            )
            cur.executemany(INSERT_FORECAST, fc_rows)
            cur.execute("DELETE FROM gold.ml_model_metrics WHERE model_name = ANY(%s)", (names,))
            cur.executemany(INSERT_METRIC, metric_rows)
    log.info("Đã ghi %d dòng ml_demand_forecast, %d dòng ml_model_metrics",
             len(fc_rows), len(metric_rows))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true", help="Không ghi DB, chỉ in metric")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    raw = load_series()
    history, calendar, last_week = prepare_series(raw)
    hotels = raw.drop_duplicates("hotel_key").set_index("hotel_key")
    hotel_names = hotels["hotel_name"].to_dict()
    resort_keys = set(hotels.index[hotels["hotel_type"] == "Resort"])
    log.info("Chuỗi tuần: %d dòng, %s → %s", len(history),
             history["week_start_date"].min().date(), last_week.date())
    if calendar.index.max() < last_week + ONE_WEEK * HORIZON:
        raise ValueError("dim_date không đủ dài cho các tuần tương lai")

    forecasters = [
        GbmForecaster(resort_keys=resort_keys),
        PerHotelBaseline("forecast_seasonal_naive", seasonal_naive),
        PerHotelBaseline("forecast_moving_avg", moving_average),
    ]
    stored_parts, metric_rows = [], []
    for fc in forecasters:
        stored, test, calib = evaluate_model(fc, history, calendar, last_week)
        version = model_version(fc.model_name)
        stored_parts.append(stored.assign(model_version=version))
        for dataset, frame in (("backtest", test), ("calibration", calib)):
            for metric_name, value in summarize(frame, hotel_names).items():
                metric_rows.append((version, fc.model_name, metric_name, value, dataset))

    metrics = pd.DataFrame(
        metric_rows, columns=["model_version", "model_name", "metric_name", "metric_value",
                              "dataset"]
    )
    report = metrics[metrics["dataset"] == "backtest"].pivot(
        index="metric_name", columns="model_name", values="metric_value"
    )
    print(report.round(4).to_string())
    forecasts = pd.concat(stored_parts, ignore_index=True)
    if args.dry_run:
        log.info("--dry-run: không ghi DB (%d dòng dự báo)", len(forecasts))
        return
    write_results(forecasts, metrics)


if __name__ == "__main__":
    main()
