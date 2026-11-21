"""Load: nạp file CSV vào bảng bronze bằng lệnh COPY (nhanh hơn INSERT nhiều lần).

Bảng bronze phải có đúng các cột như header CSV, cộng thêm các cột kỹ thuật bắt đầu bằng `_`.
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
            f"Bảng {table} không tồn tại. Kiểm tra file DDL trong database/bronze/."
        )
    return [r[0] for r in rows]


def check_header(header: list[str], table_cols: list[str], csv_path: Path, table: str) -> None:
    missing = [c for c in table_cols if c not in header]
    extra = [c for c in header if c not in table_cols]
    if missing or extra:
        raise HeaderMismatchError(
            f"Header của {csv_path.name} không khớp bảng {table}. "
            f"Thiếu trong CSV: {missing or '-'}; thừa trong CSV: {extra or '-'}. "
            "Sửa file DDL trong database/bronze/ hoặc kiểm tra lại file nguồn."
        )


def load_csv(conn: psycopg.Connection, csv_path: Path, table: str) -> int:
    """Nạp toàn bộ CSV vào `table`. Trả về số dòng đã nạp."""
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
