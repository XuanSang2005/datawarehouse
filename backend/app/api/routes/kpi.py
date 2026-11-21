from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import DbConn, Filters
from app.schemas.kpi import Grain, KpiSummary, KpiTimeseries
from app.services import kpi_service

router = APIRouter(prefix="/kpi", tags=["kpi"])


@router.get("/summary", response_model=KpiSummary)
def get_summary(conn: DbConn, flt: Filters) -> KpiSummary:
    """Overview KPIs (G1): revenue, room-nights, ADR, cancellation rate, lead time; split by hotel.

    Filtered by arrival date. ADR and cancellation rate are recomputed from totals (sum/sum).
    """
    return kpi_service.get_summary(conn, flt)


@router.get("/timeseries", response_model=KpiTimeseries)
def get_timeseries(
    conn: DbConn,
    flt: Filters,
    grain: Annotated[
        Grain, Query(description="Drill-down level: year → quarter → month → week (ISO)")
    ] = "month",
    by_hotel: Annotated[bool, Query(description="Split each period by hotel")] = False,
) -> KpiTimeseries:
    """KPI series by period (arrival date) for drill-down Year → Quarter → Month → Week."""
    return kpi_service.get_timeseries(conn, flt, grain, by_hotel)
