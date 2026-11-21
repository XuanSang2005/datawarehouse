"""Kiểm tra cấu trúc thư mục/quy ước mà pipeline phụ thuộc vào (không cần DB)."""

import re

from etl.config import DATABASE_DIR
from etl.db import list_sql_files
from etl.extract import SOURCES
from etl.run_pipeline import parse_args, resolve_steps

NUMBERED = re.compile(r"^\d{2}_[a-z0-9_]+\.sql$")


def test_sql_files_are_numbered():
    for layer in ("init", "bronze", "silver", "gold", "checks"):
        for path in list_sql_files(DATABASE_DIR / layer):
            assert NUMBERED.match(path.name), f"{path} phải đặt tên dạng NN_ten_file.sql"


def test_every_source_has_bronze_ddl():
    ddl = " ".join(p.read_text() for p in list_sql_files(DATABASE_DIR / "bronze"))
    for src in SOURCES:
        assert f"CREATE TABLE {src.bronze_table}" in ddl, f"Thiếu DDL cho {src.bronze_table}"


def test_resolve_steps_from():
    assert resolve_steps(parse_args(["--from", "silver"])) == ["silver", "gold", "checks"]


def test_resolve_steps_keeps_canonical_order():
    assert resolve_steps(parse_args(["--steps", "gold", "bronze"])) == ["bronze", "gold"]
