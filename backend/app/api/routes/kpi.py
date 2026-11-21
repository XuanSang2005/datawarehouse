from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import DbConn, Filters
from app.schemas.kpi import Grain, KpiSummary, KpiTimeseries
from app.services import kpi_service

router = APIRouter(prefix="/kpi", tags=["kpi"])


@router.get("/summary", response_model=KpiSummary)
def get_summary(conn: DbConn, flt: Filters) -> KpiSummary:
    """KPI tổng quan (G1): doanh thu, room-nights, ADR, tỉ lệ hủy, lead time; tách theo khách sạn.

    Lọc theo ngày đến. ADR và tỉ lệ hủy tính lại từ tổng (sum/sum).
    """
    return kpi_service.get_summary(conn, flt)


@router.get("/timeseries", response_model=KpiTimeseries)
def get_timeseries(
    conn: DbConn,
    flt: Filters,
    grain: Annotated[
        Grain, Query(description="Mức drill-down: year → quarter → month → week (ISO)")
    ] = "month",
    by_hotel: Annotated[bool, Query(description="Tách mỗi kỳ theo từng khách sạn")] = False,
) -> KpiTimeseries:
    """Chuỗi KPI theo kỳ (ngày đến) để drill-down Năm → Quý → Tháng → Tuần."""
    return kpi_service.get_timeseries(conn, flt, grain, by_hotel)
