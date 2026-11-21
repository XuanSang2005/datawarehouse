"""E4: train + backtest the weekly room-nights forecast → gold.ml_demand_forecast, ml_model_metrics.

Run from the repo root:
    python -m ml.forecast.train            # backtest, forecast the future, write to DB
    python -m ml.forecast.train --dry-run  # print metrics only, no DB writes

Design (details and limitations: ml/README.md):
- Series: room-nights sold (non-canceled bookings) per hotel × week (Monday starting the week),
  complete 7-night weeks only: 2015-07-06 → 2017-08-21 (112 weeks per hotel).
- 3 models: forecast_gbm (main), forecast_seasonal_naive, forecast_moving_avg (baselines).
- Rolling-origin backtest, horizon 1..8 weeks, refit at each origin:
    * calibration window: target weeks 2016-07-04 → 2016-12-26 → error quantiles for the 80%
      interval
    * test window: target weeks 2017-01-02 → last complete week (2017-08-21) → reported MAPE
- Written to the table: h=1 forecasts for the test weeks (with actuals) + 8 future weeks from the
  last origin (actual NULL; week 2017-08-28 only has 4 nights of data so it also counts as future).
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
HORIZON = 8  # number of weeks forecast ahead (backtest and future)
STORE_HORIZON = 1  # horizon of the backtest forecasts written to the table
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
    """Calibration + test backtest, future forecast. Returns (forecasts to write, test, calib)."""
    calib = rolling_origin(forecaster, history, calendar, *CALIB_WINDOW, HORIZON)
    test = rolling_origin(forecaster, history, calendar, TEST_START, last_week, HORIZON)
    # Intervals for test weeks only use calibration errors (no peeking at the test results)
    test = apply_interval(test, residual_quantiles(calib, COVERAGE))
    # Intervals for future weeks use every backtest error known at forecast time
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
    with connect() as conn:  # 1 transaction: an error midway does not lose the old data
        for path in DDL_FILES:
            run_sql_file(conn, path)
        with conn.cursor() as cur:
            # Idempotent: only delete the E4 models' own rows (the metrics table is shared with E3)
            cur.execute(
                "DELETE FROM gold.ml_demand_forecast WHERE model_version = ANY(%s)", (versions,)
            )
            cur.executemany(INSERT_FORECAST, fc_rows)
            cur.execute("DELETE FROM gold.ml_model_metrics WHERE model_name = ANY(%s)", (names,))
            cur.executemany(INSERT_METRIC, metric_rows)
    log.info("Wrote %d rows to ml_demand_forecast, %d rows to ml_model_metrics",
             len(fc_rows), len(metric_rows))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true", help="No DB writes; print metrics only")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    raw = load_series()
    history, calendar, last_week = prepare_series(raw)
    hotels = raw.drop_duplicates("hotel_key").set_index("hotel_key")
    hotel_names = hotels["hotel_name"].to_dict()
    resort_keys = set(hotels.index[hotels["hotel_type"] == "Resort"])
    log.info("Weekly series: %d rows, %s → %s", len(history),
             history["week_start_date"].min().date(), last_week.date())
    if calendar.index.max() < last_week + ONE_WEEK * HORIZON:
        raise ValueError("dim_date is not long enough for the future weeks")

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
        log.info("--dry-run: not writing to DB (%d forecast rows)", len(forecasts))
        return
    write_results(forecasts, metrics)


if __name__ == "__main__":
    main()
