"""Repository: contains ONLY SQL and returns raw data (list[dict]).

Rule: the backend only reads the `gold` (business data) and `meta` (operations) schemas.
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
        # Table does not exist = the pipeline has never run.
        conn.rollback()
        return []
