"""PostgreSQL connection and SQL file execution."""

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
            f"Could not connect to DB {settings.describe()}. "
            "Check: (1) is the DB running? `docker compose up -d db` "
            "(2) are the settings in .env correct? "
            f"Details: {exc}"
        ) from exc


def run_sql_file(conn: psycopg.Connection, path: Path) -> None:
    """Run the whole content of one SQL file (may contain multiple statements)."""
    sql_text = path.read_text(encoding="utf-8")
    with conn.cursor() as cur:
        cur.execute(sql_text)


def list_sql_files(directory: Path) -> list[Path]:
    """The .sql files in a directory, sorted by name (hence the 01_, 02_... numbering)."""
    return sorted(p for p in directory.glob("*.sql") if p.is_file())
