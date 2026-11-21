from fastapi import APIRouter

from app.api.deps import DbConn
from app.schemas.filters import FilterOptions
from app.services import filters_service

router = APIRouter(prefix="/filters", tags=["filters"])


@router.get("", response_model=FilterOptions)
def get_filters(conn: DbConn) -> FilterOptions:
    """Filter options: hotels, channel groups, segments, countries, arrival date range."""
    return filters_service.get_filter_options(conn)
