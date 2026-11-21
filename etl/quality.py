"""Data quality checks: runs the files in database/checks/.

Convention for each check file:
  * First line: `-- severity: error` or `-- severity: warning`
  * The SELECT returns the VIOLATING ROWS (0 rows = pass).
  * error with violations -> pipeline stops with exit code 1; warning -> logged only.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import psycopg

_SEVERITY_RE = re.compile(r"--\s*severity:\s*(error|warning)", re.IGNORECASE)


@dataclass
class CheckResult:
    name: str
    severity: str
    violations: int

    @property
    def passed(self) -> bool:
        return self.violations == 0


def parse_severity(sql_text: str) -> str:
    match = _SEVERITY_RE.search(sql_text)
    return match.group(1).lower() if match else "error"


def run_check(conn: psycopg.Connection, path: Path) -> CheckResult:
    sql_text = path.read_text(encoding="utf-8")
    count_sql = f"SELECT count(*) FROM ({sql_text.rstrip().rstrip(';')}) AS violations"
    row = conn.execute(count_sql).fetchone()
    return CheckResult(name=path.stem, severity=parse_severity(sql_text), violations=row[0])
