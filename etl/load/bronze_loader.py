"""Load: load CSV files into bronze tables with COPY (much faster than INSERT).

A bronze table must have exactly the CSV header columns, plus technical columns starting with `_`.
"""

from __future__ import annotations

import csv
from pathlib import Path

import psycopg
from psycopg import sql


class HeaderMismatchError(ValueError):
    pass


def _table_columns(conn: psycopg.Connection, table: str) -> list[str]:
    schema, name = table.split(".")
    rows = conn.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema = %s AND table_name = %s AND column_name NOT LIKE '\\_%%' "
        "ORDER BY ordinal_position",
        (schema, name),
    ).fetchall()
    if not rows:
        raise HeaderMismatchError(
            f"Table {table} does not exist. Check the DDL file in database/bronze/."
        )
    return [r[0] for r in rows]


def check_header(header: list[str], table_cols: list[str], csv_path: Path, table: str) -> None:
    missing = [c for c in table_cols if c not in header]
    extra = [c for c in header if c not in table_cols]
    if missing or extra:
        raise HeaderMismatchError(
            f"Header of {csv_path.name} does not match table {table}. "
            f"Missing in CSV: {missing or '-'}; extra in CSV: {extra or '-'}. "
            "Fix the DDL file in database/bronze/ or check the source file."
        )


def load_csv(conn: psycopg.Connection, csv_path: Path, table: str) -> int:
    """Load the whole CSV into `table`. Returns the number of rows loaded."""
    table_cols = _table_columns(conn, table)
    schema, name = table.split(".")

    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        check_header(header, table_cols, csv_path, table)

        columns = [*header, "_source_row", "_source_file"]
        copy_stmt = sql.SQL("COPY {}.{} ({}) FROM STDIN").format(
            sql.Identifier(schema),
            sql.Identifier(name),
            sql.SQL(", ").join(map(sql.Identifier, columns)),
        )
        n = 0
        with conn.cursor() as cur, cur.copy(copy_stmt) as copy:
            for n, row in enumerate(reader, start=1):
                copy.write_row([*row, n, csv_path.name])
    return n
