from datetime import datetime

from pydantic import BaseModel


class PipelineRun(BaseModel):
    log_id: int
    run_id: str
    step: str
    status: str
    rows_affected: int | None
    message: str | None
    started_at: datetime
    finished_at: datetime | None
