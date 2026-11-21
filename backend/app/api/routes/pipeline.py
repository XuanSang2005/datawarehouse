from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Connection

from app.core.db import get_connection
from app.schemas.pipeline import PipelineRun
from app.services import pipeline_service

router = APIRouter(prefix="/pipeline", tags=["system"])

DbConn = Annotated[Connection, Depends(get_connection)]


@router.get("/runs", response_model=list[PipelineRun])
def list_runs(
    conn: DbConn,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
) -> list[PipelineRun]:
    """Các bước ETL gần nhất (đọc từ meta.etl_run_log)."""
    return pipeline_service.get_recent_runs(conn, limit)
