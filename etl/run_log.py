"""Log each pipeline step to the meta.etl_run_log table.

Uses a separate autocommit connection so the log is kept even if the main step is rolled back.
"""

from __future__ import annotations

import uuid

from etl.db import connect


class RunLogger:
    def __init__(self) -> None:
        self.run_id = uuid.uuid4()
        self._conn = connect(autocommit=True)

    def start(self, step: str) -> int:
        row = self._conn.execute(
            "INSERT INTO meta.etl_run_log (run_id, step, status) "
            "VALUES (%s, %s, 'running') RETURNING log_id",
            (self.run_id, step),
        ).fetchone()
        assert row is not None
        return row[0]

    def finish(
        self, log_id: int, status: str, rows: int | None = None, message: str | None = None
    ) -> None:
        self._conn.execute(
            "UPDATE meta.etl_run_log "
            "SET status = %s, rows_affected = %s, message = %s, finished_at = now() "
            "WHERE log_id = %s",
            (status, rows, message, log_id),
        )

    def close(self) -> None:
        self._conn.close()
