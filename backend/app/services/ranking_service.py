"""Xếp hạng kênh bán và thị trường (G5) theo doanh thu thực (sau hủy), ADR, tỉ lệ hủy.

- Tỉ lệ và ADR tính từ tổng của từng nhóm (quy tắc 8).
- `revenue_share` tính trên tổng doanh thu của MỌI nhóm (kể cả nhóm bị loại vì ít booking).
- `cancellation_rate`: xếp TĂNG dần (hủy ít = tốt hơn); các tiêu chí khác xếp GIẢM dần.
- Nhóm có ít hơn `min_bookings` booking bị loại, để ADR/tỉ lệ của nhóm nhỏ không làm nhiễu
  bảng xếp hạng.
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
    """Trả về (top N item đã xếp hạng, tổng doanh thu mọi nhóm, số nhóm đủ điều kiện)."""
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
        missing = value is None  # nhóm không tính được chỉ số luôn xếp cuối
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
