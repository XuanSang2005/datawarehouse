"""Kết nối PostgreSQL và chạy file SQL."""

from __future__ import annotations

import logging
from pathlib import Path

import psycopg

from etl.config import get_db_settings

log = logging.getLogger("etl.db")


class DatabaseConnectionError(RuntimeError):
    pass


def connect(autocommit: bool = False) -> psycopg.Connection:
    settings = get_db_settings()
    try:
        return psycopg.connect(settings.conninfo, autocommit=autocommit)
    except psycopg.OperationalError as exc:
        raise DatabaseConnectionError(
            f"Không kết nối được DB {settings.describe()}. "
            "Kiểm tra: (1) DB đã chạy chưa? `docker compose up -d db` "
            "(2) thông tin trong .env có đúng không? "
            f"Chi tiết: {exc}"
        ) from exc


def run_sql_file(conn: psycopg.Connection, path: Path) -> None:
    """Chạy toàn bộ nội dung 1 file SQL (có thể nhiều câu lệnh)."""
    sql_text = path.read_text(encoding="utf-8")
    with conn.cursor() as cur:
        cur.execute(sql_text)


def list_sql_files(directory: Path) -> list[Path]:
    """Các file .sql trong thư mục, sắp xếp theo tên (vì vậy phải đánh số 01_, 02_...)."""
    return sorted(p for p in directory.glob("*.sql") if p.is_file())
