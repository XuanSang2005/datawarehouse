from fastapi import APIRouter

from app.api.deps import DbConn
from app.schemas.filters import FilterOptions
from app.services import filters_service

router = APIRouter(prefix="/filters", tags=["filters"])


@router.get("", response_model=FilterOptions)
def get_filters(conn: DbConn) -> FilterOptions:
    """Danh mục cho bộ lọc: khách sạn, nhóm kênh, phân khúc, quốc gia, khoảng ngày đến."""
    return filters_service.get_filter_options(conn)
