from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import DbConn, Filters
from app.schemas.ranking import RankingResponse, RankingSort
from app.services import ranking_service

router = APIRouter(tags=["ranking"])

SortParam = Annotated[
    RankingSort,
    Query(description="Tiêu chí xếp hạng; cancellation_rate xếp tăng dần, còn lại giảm dần"),
]
TopN = Annotated[int, Query(ge=1, le=200, description="Số nhóm trả về")]


@router.get("/channels/ranking", response_model=RankingResponse)
def rank_channels(
    conn: DbConn,
    flt: Filters,
    sort_by: SortParam = "realized_revenue",
    top_n: TopN = 10,
    min_bookings: Annotated[int, Query(ge=0)] = 0,
) -> RankingResponse:
    """Xếp hạng nhóm kênh bán theo doanh thu thực (sau hủy), ADR, tỉ lệ hủy, số booking."""
    return ranking_service.get_ranking(conn, flt, "channel", sort_by, min_bookings, top_n)


@router.get("/markets/ranking", response_model=RankingResponse)
def rank_markets(
    conn: DbConn,
    flt: Filters,
    sort_by: SortParam = "realized_revenue",
    top_n: TopN = 10,
    min_bookings: Annotated[
        int, Query(ge=0, description="Bỏ quốc gia có ít booking (ADR/tỉ lệ của nhóm nhỏ rất nhiễu)")
    ] = 100,
) -> RankingResponse:
    """Xếp hạng thị trường (quốc gia) theo doanh thu thực (sau hủy), ADR, tỉ lệ hủy, số booking."""
    return ranking_service.get_ranking(conn, flt, "market", sort_by, min_bookings, top_n)
