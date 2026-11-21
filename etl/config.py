"""Shared ETL configuration: directory paths + DB connection settings.

All values are read from the `.env` file at the repo root (see `.env.example`).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_RAW_DIR = REPO_ROOT / "data" / "raw"
DATABASE_DIR = REPO_ROOT / "database"

load_dotenv(REPO_ROOT / ".env")


@dataclass(frozen=True)
class DbSettings:
    user: str
    password: str
    dbname: str
    host: str
    port: int

    @property
    def conninfo(self) -> str:
        return (
            f"host={self.host} port={self.port} dbname={self.dbname} "
            f"user={self.user} password={self.password} connect_timeout=5"
        )

    def describe(self) -> str:
        """Describe the connection WITHOUT the password (for logging)."""
        return f"{self.user}@{self.host}:{self.port}/{self.dbname}"


def get_db_settings() -> DbSettings:
    return DbSettings(
        user=os.getenv("POSTGRES_USER", "dwh"),
        password=os.getenv("POSTGRES_PASSWORD", "dwh_password"),
        dbname=os.getenv("POSTGRES_DB", "tourism_dw"),
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
    )
