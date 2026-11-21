"""Main entry point of the pipeline.

Usage (from the repo root, with the venv activated):
    python -m etl.run_pipeline                       # run all steps
    python -m etl.run_pipeline --steps silver gold   # run only some steps
    python -m etl.run_pipeline --from silver         # run from the silver step onwards
    python -m etl.run_pipeline --refresh-sources     # re-download source files even if present

Step order:
    init     -> database/init/*.sql      (create schemas + meta tables)
    extract  -> etl/extract/             (download/generate files into data/raw/)
    bronze   -> database/bronze/*.sql + etl/load/  (create raw tables and load CSVs)
    silver   -> database/silver/*.sql    (cleaning, type casting)
    gold     -> database/gold/*.sql      (star schema, KPIs)
    checks   -> database/checks/*.sql    (data quality checks)
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Callable

import psycopg

from etl import quality
from etl.config import DATA_RAW_DIR, DATABASE_DIR, get_db_settings
from etl.db import DatabaseConnectionError, connect, list_sql_files, run_sql_file
from etl.extract import SOURCES
from etl.load.bronze_loader import load_csv
from etl.run_log import RunLogger

STEPS = ["init", "extract", "bronze", "silver", "gold", "checks"]

log = logging.getLogger("etl")


class StepFailed(RuntimeError):
    pass


def _tracked(logger: RunLogger | None, step: str, fn: Callable[[], int | None]) -> int | None:
    """Run fn, log to meta.etl_run_log (if available), raise StepFailed on error."""
    log_id = logger.start(step) if logger else None
    try:
        rows = fn()
    except Exception as exc:
        if logger and log_id is not None:
            logger.finish(log_id, "failed", message=str(exc)[:2000])
        raise StepFailed(f"Step '{step}' failed: {exc}") from exc
    if logger and log_id is not None:
        logger.finish(log_id, "success", rows=rows)
    return rows


def _run_sql_layer(conn: psycopg.Connection, logger: RunLogger | None, layer: str) -> None:
    files = list_sql_files(DATABASE_DIR / layer)
    if not files:
        log.info("[%s] No SQL files in database/%s/ -> skipped", layer, layer)
        return
    for path in files:
        step = f"{layer}/{path.name}"

        def work(p=path) -> None:
            with conn.transaction():
                run_sql_file(conn, p)

        _tracked(logger, step, work)
        log.info("[%s] ✔ %s", layer, path.name)


# ----------------------------------------------------------------------------- steps


def step_init(conn: psycopg.Connection) -> None:
    # The init step does not write the meta log because the log table is created in this step.
    for path in list_sql_files(DATABASE_DIR / "init"):
        try:
            with conn.transaction():
                run_sql_file(conn, path)
        except psycopg.Error as exc:
            raise StepFailed(f"Step 'init/{path.name}' failed: {exc}") from exc
        log.info("[init] ✔ %s", path.name)


def step_extract(logger: RunLogger, refresh: bool) -> None:
    DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)
    for src in SOURCES:
        target = DATA_RAW_DIR / src.filename
        if target.exists() and not refresh:
            log.info("[extract] %s exists -> skipped (use --refresh-sources to re-download)",
                     src.filename)
            continue
        _tracked(logger, f"extract/{src.name}", lambda s=src, t=target: s.extract(t))
        log.info("[extract] ✔ %s", src.filename)


def step_bronze(conn: psycopg.Connection, logger: RunLogger) -> None:
    _run_sql_layer(conn, logger, "bronze")  # recreate the bronze tables (full load)
    for src in SOURCES:
        path = DATA_RAW_DIR / src.filename
        if not path.exists():
            raise StepFailed(
                f"Missing file {path}. Run the extract step first: python -m etl.run_pipeline "
                "--steps extract"
            )

        def work(s=src, p=path) -> int:
            with conn.transaction():
                return load_csv(conn, p, s.bronze_table)

        rows = _tracked(logger, f"bronze/load_{src.name}", work)
        log.info("[bronze] ✔ %s -> %s (%s rows)", src.filename, src.bronze_table, rows)


def step_checks(conn: psycopg.Connection, logger: RunLogger) -> None:
    files = list_sql_files(DATABASE_DIR / "checks")
    errors = []
    for path in files:
        log_id = logger.start(f"checks/{path.name}")
        result = quality.run_check(conn, path)
        if result.passed:
            status, icon = "success", "✔"
        elif result.severity == "warning":
            status, icon = "warning", "⚠"
        else:
            status, icon = "failed", "✘"
            errors.append(result.name)
        logger.finish(log_id, status, rows=result.violations,
                      message=None if result.passed else f"{result.violations} violating rows")
        log.info("[checks] %s %-45s %s violations (%s)", icon, result.name, result.violations,
                 result.severity)
    if errors:
        raise StepFailed(f"Data quality checks failed: {errors}. See database/checks/.")


# ----------------------------------------------------------------------------- main


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Tourism DSS ETL pipeline")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--steps", nargs="+", choices=STEPS, help="Run only these steps")
    group.add_argument("--from", dest="from_step", choices=STEPS, help="Run from this step onwards")
    parser.add_argument("--refresh-sources", action="store_true",
                        help="Re-download source files even if they exist in data/raw/")
    return parser.parse_args(argv)


def resolve_steps(args: argparse.Namespace) -> list[str]:
    if args.steps:
        return [s for s in STEPS if s in args.steps]
    if args.from_step:
        return STEPS[STEPS.index(args.from_step):]
    return list(STEPS)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s",
                        datefmt="%H:%M:%S")
    args = parse_args(argv)
    steps = resolve_steps(args)
    log.info("Pipeline started | DB: %s | Steps: %s", get_db_settings().describe(),
             " -> ".join(steps))

    logger: RunLogger | None = None
    try:
        with connect() as conn:
            step_init(conn)  # always runs: idempotent, ensures schemas + log table exist
            logger = RunLogger()
            if "extract" in steps:
                step_extract(logger, args.refresh_sources)
            if "bronze" in steps:
                step_bronze(conn, logger)
            for layer in ("silver", "gold"):
                if layer in steps:
                    _run_sql_layer(conn, logger, layer)
            if "checks" in steps:
                step_checks(conn, logger)
    except (DatabaseConnectionError, StepFailed) as exc:
        log.error("✘ %s", exc)
        if logger:
            log.error("Details: SELECT * FROM meta.etl_run_log WHERE run_id = '%s';",
                      logger.run_id)
        return 1
    finally:
        if logger:
            logger.close()

    log.info("✔ Pipeline finished (run_id=%s)", logger.run_id if logger else "-")
    return 0


if __name__ == "__main__":
    sys.exit(main())
