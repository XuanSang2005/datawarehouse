"""Service: logic nghiệp vụ, kết hợp/biến đổi dữ liệu từ repository.

Các phép tính cho what-if, khuyến nghị overbooking... sẽ nằm ở tầng này.
"""

from sqlalchemy import Connection

from app.repositories import pipeline_repo
from app.schemas.pipeline import PipelineRun


def get_recent_runs(conn: Connection, limit: int = 50) -> list[PipelineRun]:
    return [PipelineRun(**row) for row in pipeline_repo.fetch_recent_runs(conn, limit)]
