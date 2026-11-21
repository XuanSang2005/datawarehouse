"""Kết nối database (SQLAlchemy engine dùng chung cho cả app)."""

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Connection, Engine, create_engine

from app.core.config import get_settings


@lru_cache
def get_engine() -> Engine:
    return create_engine(
        get_settings().database_url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 3},
    )


def get_connection() -> Iterator[Connection]:
    """FastAPI dependency: mỗi request mượn 1 connection từ pool."""
    with get_engine().connect() as conn:
        yield conn
