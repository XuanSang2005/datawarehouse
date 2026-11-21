import logging

from fastapi import APIRouter
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.core.db import get_engine
from app.schemas.health import HealthResponse

router = APIRouter(tags=["system"])
log = logging.getLogger("app.health")


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Kiểm tra API còn sống và có kết nối được DB không."""
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        db = "up"
    except SQLAlchemyError as exc:
        log.warning("Không kết nối được DB: %s", exc.__class__.__name__)
        db = "down"
    return HealthResponse(
        status="ok" if db == "up" else "degraded",
        database=db,
        version=get_settings().app_version,
    )
