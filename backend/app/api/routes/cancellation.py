from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import DbConn, Filters
from app.schemas.cancellation import (
    BreakdownDimension,
    CancellationBreakdown,
    HighRiskPage,
    HighRiskSort,
    RiskBandFilter,
)
from app.schemas.ml import ModelMetricsResponse
from app.services import cancellation_service

router = APIRouter(prefix="/cancellation", tags=["cancellation"])


@router.get("/breakdown", response_model=CancellationBreakdown)
def get_breakdown(
    conn: DbConn,
    flt: Filters,
    by: Annotated[
        BreakdownDimension, Query(description="Dimension for the cancellation rate")
    ] = "lead_time",
    top_n: Annotated[
        int | None, Query(ge=1, le=200, description="Only the N groups with the most bookings")
    ] = None,
) -> CancellationBreakdown:
    """Cancellation rate by lead time / channel / deposit type / country (+ segment, customer type).

    Rates are recomputed from totals.
    """
    return cancellation_service.get_breakdown(conn, flt, by, top_n)


@router.get("/high-risk", response_model=HighRiskPage)
def get_high_risk(
    conn: DbConn,
    flt: Filters,
    risk_band: Annotated[
        RiskBandFilter, Query(description="Risk band to return; All = every band")
    ] = "High",
    min_probability: Annotated[
        float | None,
        Query(
            ge=0, le=1, description="Only bookings with cancellation probability >= threshold (0–1)"
        ),
    ] = None,
    test_set_only: Annotated[
        bool,
        Query(description="Only 2017 bookings (out-of-sample scores, unseen in model training)"),
    ] = True,
    sort: Annotated[
        HighRiskSort,
        Query(
            description="probability: cancellation probability; "
            "expected_loss: probability × booked revenue"
        ),
    ] = "probability",
    model_version: Annotated[
        str | None, Query(max_length=100, description="Default: latest version")
    ] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
) -> HighRiskPage:
    """List of high cancellation-risk bookings (paginated).

    Used by Reservations to call guests for confirmation / request a deposit.

    404 if gold.ml_booking_risk has no data yet.
    """
    return cancellation_service.get_high_risk(
        conn,
        flt,
        model_version=model_version,
        risk_band=None if risk_band == "All" else risk_band,
        min_probability=min_probability,
        test_set_only=test_set_only,
        sort=sort,
        page=page,
        page_size=page_size,
    )


@router.get("/model-metrics", response_model=ModelMetricsResponse)
def get_model_metrics(conn: DbConn) -> ModelMetricsResponse:
    """AUC, precision, recall, F1, confusion matrix and risk thresholds of the cancellation models.

    404 if the ML script has not been run.
    """
    return ModelMetricsResponse(models=cancellation_service.get_model_metrics(conn))
