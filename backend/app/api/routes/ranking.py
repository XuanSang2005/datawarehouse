from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import DbConn, Filters
from app.schemas.ranking import RankingResponse, RankingSort
from app.services import ranking_service

router = APIRouter(tags=["ranking"])

SortParam = Annotated[
    RankingSort,
    Query(description="Ranking metric; cancellation_rate sorts ascending, the others descending"),
]
TopN = Annotated[int, Query(ge=1, le=200, description="Number of groups returned")]


@router.get("/channels/ranking", response_model=RankingResponse)
def rank_channels(
    conn: DbConn,
    flt: Filters,
    sort_by: SortParam = "realized_revenue",
    top_n: TopN = 10,
    min_bookings: Annotated[int, Query(ge=0)] = 0,
) -> RankingResponse:
    """Rank channel groups by realized revenue (after cancellations), ADR, cancel rate, bookings."""
    return ranking_service.get_ranking(conn, flt, "channel", sort_by, min_bookings, top_n)


@router.get("/markets/ranking", response_model=RankingResponse)
def rank_markets(
    conn: DbConn,
    flt: Filters,
    sort_by: SortParam = "realized_revenue",
    top_n: TopN = 10,
    min_bookings: Annotated[
        int,
        Query(ge=0, description="Skip countries with few bookings (noisy ADR/rates)"),
    ] = 100,
) -> RankingResponse:
    """Rank markets (countries) by realized revenue (after cancellations), ADR, cancel rate."""
    return ranking_service.get_ranking(conn, flt, "market", sort_by, min_bookings, top_n)
