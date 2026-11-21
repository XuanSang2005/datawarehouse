"""Write the cancellation model results to gold.ml_booking_risk and gold.ml_model_metrics.

The DDL lives in database/ml/ (rule 1). Only parameterized DELETE/COPY/INSERT statements are here,
all in ONE transaction: an error midway does not lose the old data.
Idempotent: deletes exactly the rows with the same model_version (and, for the metrics table, the
same model_name), then rewrites them.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Sequence
from datetime import datetime

import pandas as pd

from etl.config import DATABASE_DIR
from etl.db import run_sql_file

log = logging.getLogger("ml.cancellation.store")

DDL_FILES = (
    DATABASE_DIR / "ml" / "01_ml_model_metrics.sql",  # shared table, CREATE IF NOT EXISTS only
    DATABASE_DIR / "ml" / "02_ml_booking_risk.sql",
)

RISK_COLUMNS = (
    "booking_id",
    "model_version",
    "cancel_probability",
    "risk_band",
    "is_test_set",
    "scored_at",
)

# (model_name, metric_name, metric_value, dataset)
MetricRow = tuple[str, str, float, str]


def ensure_tables(conn) -> None:
    for path in DDL_FILES:
        run_sql_file(conn, path)


def write_booking_risk(conn, scores: pd.DataFrame, model_version: str, scored_at: datetime) -> int:
    """scores has columns booking_id, cancel_probability, risk_band, is_test_set."""
    with conn.cursor() as cur:
        cur.execute("DELETE FROM gold.ml_booking_risk WHERE model_version = %s", (model_version,))
        log.info("Deleted %s old rows of %s in gold.ml_booking_risk", cur.rowcount, model_version)
        copy_sql = f"COPY gold.ml_booking_risk ({', '.join(RISK_COLUMNS)}) FROM STDIN"
        with cur.copy(copy_sql) as copy:
            for row in scores.itertuples(index=False):
                copy.write_row(
                    (
                        int(row.booking_id),
                        model_version,
                        f"{row.cancel_probability:.4f}",
                        row.risk_band,
                        bool(row.is_test_set),
                        scored_at,
                    )
                )
    return len(scores)


def write_metrics(
    conn,
    rows: Iterable[MetricRow],
    model_names: Sequence[str],
    model_version: str,
    trained_at: datetime,
) -> int:
    """Only touches rows whose model_name is in model_names (table shared with E4)."""
    rows = list(rows)
    unexpected = {r[0] for r in rows} - set(model_names)
    if unexpected:
        raise ValueError(f"model_name not in the list allowed to be written: {sorted(unexpected)}")
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM gold.ml_model_metrics WHERE model_version = %s AND model_name = ANY(%s)",
            (model_version, list(model_names)),
        )
        cur.executemany(
            "INSERT INTO gold.ml_model_metrics"
            " (model_version, model_name, metric_name, metric_value, dataset, trained_at)"
            " VALUES (%s, %s, %s, %s, %s, %s)",
            [
                (model_version, name, metric, round(float(value), 6), dataset, trained_at)
                for name, metric, value, dataset in rows
            ],
        )
    return len(rows)
