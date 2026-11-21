"""Repository: CHỈ chứa câu SQL và trả về dữ liệu thô (list[dict]).

Quy tắc: backend chỉ đọc schema `gold` (dữ liệu nghiệp vụ) và `meta` (vận hành).
"""

from sqlalchemy import Connection, text
from sqlalchemy.exc import ProgrammingError


def fetch_recent_runs(conn: Connection, limit: int) -> list[dict]:
    query = text(
        """
        SELECT log_id, run_id::text AS run_id, step, status, rows_affected, message,
               started_at, finished_at
        FROM meta.etl_run_log
        ORDER BY log_id DESC
        LIMIT :limit
        """
    )
    try:
        return [dict(r) for r in conn.execute(query, {"limit": limit}).mappings()]
    except ProgrammingError:
        # Bảng chưa tồn tại = pipeline chưa chạy lần nào.
        conn.rollback()
        return []
