"""Rank sales channels and markets (G5) by realized revenue (after cancellations), ADR,
cancellation rate.

- Rates and ADR are computed from each group's totals (rule 8).
- `revenue_share` is relative to the revenue of ALL groups (including those dropped for having
  few bookings).
- `cancellation_rate`: sorted ASCENDING (fewer cancellations = better); other metrics DESCENDING.
- Groups with fewer than `min_bookings` bookings are dropped, so that the ADR/rates of small
  groups do not add noise to the ranking.
"""

from typing import Literal

from sqlalchemy import Connection

from app.repositories import ranking_repo
from app.schemas.common import BookingFilter
from app.schemas.ranking import RankingItem, RankingResponse, RankingSort
from app.services.kpi_math import ratio, to_float

ASCENDING_SORTS = {"cancellation_rate"}


def rank_groups(
    rows: list[dict], sort_by: RankingSort, min_bookings: int, top_n: int
) -> tuple[list[RankingItem], float, int]:
    """Return (top N ranked items, total revenue of all groups, number of eligible groups)."""
    total_revenue = sum(to_float(r["realized_revenue"]) for r in rows)
    items = [
        RankingItem(
            rank=0,
            key=str(r["key"]),
            label=str(r["label"]),
            group=r["grp"],
            bookings=int(r["bookings"]),
            canceled_bookings=int(r["canceled_bookings"]),
            cancellation_rate=ratio(r["canceled_bookings"], r["bookings"]),
            room_nights_sold=int(r["room_nights_sold"]),
            realized_revenue=to_float(r["realized_revenue"]),
            revenue_share=ratio(r["realized_revenue"], total_revenue),
            lost_revenue=to_float(r["lost_revenue"]),
            adr=ratio(r["realized_revenue"], r["room_nights_sold"]),
        )
        for r in rows
        if int(r["bookings"]) >= min_bookings
    ]
    ascending = sort_by in ASCENDING_SORTS

    def sort_key(item: RankingItem) -> tuple:
        value = getattr(item, sort_by)
        missing = value is None  # groups whose metric cannot be computed always rank last
        number = 0.0 if missing else float(value)
        return (missing, number if ascending else -number, -item.realized_revenue, item.key)

    items.sort(key=sort_key)
    for i, item in enumerate(items, start=1):
        item.rank = i
    return items[:top_n], total_revenue, len(items)


def get_ranking(
    conn: Connection,
    flt: BookingFilter,
    dimension: Literal["channel", "market"],
    sort_by: RankingSort,
    min_bookings: int,
    top_n: int,
) -> RankingResponse:
    rows = ranking_repo.fetch_groups(conn, flt, dimension)
    items, total_revenue, ranked = rank_groups(rows, sort_by, min_bookings, top_n)
    return RankingResponse(
        dimension=dimension,
        sort_by=sort_by,
        min_bookings=min_bookings,
        filters=flt,
        total_realized_revenue=total_revenue,
        groups_ranked=ranked,
        items=items,
    )
