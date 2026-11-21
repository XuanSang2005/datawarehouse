"""Điểm chạy chính của pipeline.

Cách dùng (chạy từ thư mục gốc repo, đã activate venv):
    python -m etl.run_pipeline                       # chạy tất cả các bước
    python -m etl.run_pipeline --steps silver gold   # chỉ chạy một số bước
    python -m etl.run_pipeline --from silver         # chạy từ bước silver trở đi
    python -m etl.run_pipeline --refresh-sources     # tải lại file nguồn dù đã có

Thứ tự các bước:
    init     -> database/init/*.sql      (tạo schema + bảng meta)
    extract  -> etl/extract/             (tải/sinh file vào data/raw/)
    bronze   -> database/bronze/*.sql + etl/load/  (tạo bảng thô và nạp CSV)
    silver   -> database/silver/*.sql    (làm sạch, ép kiểu)
    gold     -> database/gold/*.sql      (star schema, KPI)
    checks   -> database/checks/*.sql    (kiểm tra chất lượng dữ liệu)
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
    """Chạy fn, ghi log vào meta.etl_run_log (nếu có), ném StepFailed khi lỗi."""
    log_id = logger.start(step) if logger else None
    try:
        rows = fn()
    except Exception as exc:
        if logger and log_id is not None:
            logger.finish(log_id, "failed", message=str(exc)[:2000])
        raise StepFailed(f"Bước '{step}' lỗi: {exc}") from exc
    if logger and log_id is not None:
        logger.finish(log_id, "success", rows=rows)
    return rows


def _run_sql_layer(conn: psycopg.Connection, logger: RunLogger | None, layer: str) -> None:
    files = list_sql_files(DATABASE_DIR / layer)
    if not files:
        log.info("[%s] Không có file SQL nào trong database/%s/ -> bỏ qua", layer, layer)
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
    # Bước init không ghi meta log vì bảng log được tạo chính trong bước này.
    for path in list_sql_files(DATABASE_DIR / "init"):
        try:
            with conn.transaction():
                run_sql_file(conn, path)
        except psycopg.Error as exc:
            raise StepFailed(f"Bước 'init/{path.name}' lỗi: {exc}") from exc
        log.info("[init] ✔ %s", path.name)


def step_extract(logger: RunLogger, refresh: bool) -> None:
    DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)
    for src in SOURCES:
        target = DATA_RAW_DIR / src.filename
        if target.exists() and not refresh:
            log.info("[extract] %s đã có sẵn -> bỏ qua (dùng --refresh-sources để tải lại)",
                     src.filename)
            continue
        _tracked(logger, f"extract/{src.name}", lambda s=src, t=target: s.extract(t))
        log.info("[extract] ✔ %s", src.filename)


def step_bronze(conn: psycopg.Connection, logger: RunLogger) -> None:
    _run_sql_layer(conn, logger, "bronze")  # tạo lại bảng bronze (full load)
    for src in SOURCES:
        path = DATA_RAW_DIR / src.filename
        if not path.exists():
            raise StepFailed(
                f"Thiếu file {path}. Chạy bước extract trước: python -m etl.run_pipeline "
                "--steps extract"
            )

        def work(s=src, p=path) -> int:
            with conn.transaction():
                return load_csv(conn, p, s.bronze_table)

        rows = _tracked(logger, f"bronze/load_{src.name}", work)
        log.info("[bronze] ✔ %s -> %s (%s dòng)", src.filename, src.bronze_table, rows)


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
                      message=None if result.passed else f"{result.violations} dòng vi phạm")
        log.info("[checks] %s %-45s %s vi phạm (%s)", icon, result.name, result.violations,
                 result.severity)
    if errors:
        raise StepFailed(f"Kiểm tra chất lượng thất bại: {errors}. Xem database/checks/.")


# ----------------------------------------------------------------------------- main


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Chạy ETL pipeline Tourism DSS")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--steps", nargs="+", choices=STEPS, help="Chỉ chạy các bước này")
    group.add_argument("--from", dest="from_step", choices=STEPS, help="Chạy từ bước này trở đi")
    parser.add_argument("--refresh-sources", action="store_true",
                        help="Tải lại file nguồn dù đã tồn tại trong data/raw/")
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
    log.info("Pipeline bắt đầu | DB: %s | Các bước: %s", get_db_settings().describe(),
             " -> ".join(steps))

    logger: RunLogger | None = None
    try:
        with connect() as conn:
            step_init(conn)  # luôn chạy: idempotent, đảm bảo schema + bảng log tồn tại
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
            log.error("Xem chi tiết: SELECT * FROM meta.etl_run_log WHERE run_id = '%s';",
                      logger.run_id)
        return 1
    finally:
        if logger:
            logger.close()

    log.info("✔ Pipeline hoàn tất (run_id=%s)", logger.run_id if logger else "-")
    return 0


if __name__ == "__main__":
    sys.exit(main())
