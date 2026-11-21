"""Service: business logic, combining/transforming data from the repository.

Calculations for the what-if, overbooking recommendations... live in this layer.
"""

from sqlalchemy import Connection

from app.repositories import pipeline_repo
from app.schemas.pipeline import PipelineRun


def get_recent_runs(conn: Connection, limit: int = 50) -> list[PipelineRun]:
    return [PipelineRun(**row) for row in pipeline_repo.fetch_recent_runs(conn, limit)]
