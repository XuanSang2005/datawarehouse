"""Cancellation analysis (G2): cancellation rate by dimension, high-risk bookings, model metrics."""

from sqlalchemy import Connection

from app.core.errors import DataNotReadyError
from app.repositories import cancellation_repo, ml_repo
from app.schemas.cancellation import (
    BreakdownDimension,
    BreakdownItem,
    CancellationBreakdown,
    HighRiskBooking,
    HighRiskPage,
    HighRiskSort,
    RiskBand,
)
from app.schemas.common import BookingFilter
from app.schemas.ml import ModelMetrics
from app.services import ml_service
from app.services.kpi_math import ratio, to_float

RISK_TABLE = "gold.ml_booking_risk"


def build_breakdown(rows: list[dict], top_n: int | None) -> tuple[list[BreakdownItem], int, int]:
    """Compute rates from totals, sort, cut to top N.

    Returns (items, total bookings, total canceled); both totals cover ALL groups, not just top N.
    """
    total_bookings = sum(int(r["bookings"]) for r in rows)
    total_canceled = sum(int(r["canceled_bookings"]) for r in rows)
    ordered = sorted(
        rows,
        key=lambda r: (
            r["band_order"] if r["band_order"] is not None else 0,
            -int(r["bookings"]),
            str(r["key"]),
        ),
    )
    if top_n is not None:
        ordered = ordered[:top_n]
    items = [
        BreakdownItem(
            key=str(r["key"]),
            label=str(r["label"]),
            sort_order=i + 1,
            bookings=int(r["bookings"]),
            canceled_bookings=int(r["canceled_bookings"]),
            cancellation_rate=ratio(r["canceled_bookings"], r["bookings"]),
            booking_share=ratio(r["bookings"], total_bookings),
            lost_revenue=to_float(r["lost_revenue"]),
            net_lost_revenue=to_float(r["net_lost_revenue"]),
        )
        for i, r in enumerate(ordered)
    ]
    return items, total_bookings, total_canceled


def get_breakdown(
    conn: Connection, flt: BookingFilter, by: BreakdownDimension, top_n: int | None
) -> CancellationBreakdown:
    rows = cancellation_repo.fetch_breakdown(conn, flt, by)
    items, total_bookings, total_canceled = build_breakdown(rows, top_n)
    return CancellationBreakdown(
        by=by,
        filters=flt,
        overall_cancellation_rate=ratio(total_canceled, total_bookings),
        total_bookings=total_bookings,
        items=items,
    )


def resolve_risk_version(conn: Connection, model_version: str | None) -> str:
    """The requested version, or the latest. 404 if the table is empty or the version is unknown."""
    ml_service.require_table(conn, RISK_TABLE)
    versions = ml_repo.fetch_risk_versions(conn)
    if not versions:
        raise ml_service.not_ready(RISK_TABLE)
    if model_version is None:
        return versions[0]
    if model_version not in versions:
        raise DataNotReadyError(
            f"No risk scores for model_version '{model_version}'",
            hint=f"Available versions: {', '.join(versions)}",
        )
    return model_version


def get_high_risk(
    conn: Connection,
    flt: BookingFilter,
    *,
    model_version: str | None,
    risk_band: RiskBand | None,
    min_probability: float | None,
    test_set_only: bool,
    sort: HighRiskSort,
    page: int,
    page_size: int,
) -> HighRiskPage:
    version = resolve_risk_version(conn, model_version)
    sel = cancellation_repo.RiskSelection(
        model_version=version,
        risk_band=risk_band,
        min_probability=min_probability,
        test_set_only=test_set_only,
    )
    summary = cancellation_repo.summarize_high_risk(conn, flt, sel)
    rows = cancellation_repo.fetch_high_risk(
        conn, flt, sel, sort, page_size, (page - 1) * page_size
    )
    return HighRiskPage(
        model_version=version,
        filters=flt,
        risk_band=risk_band,
        min_probability=min_probability,
        sort=sort,
        page=page,
        page_size=page_size,
        total=int(summary["total"]),
        booked_revenue_total=to_float(summary["booked_revenue_total"]),
        expected_loss_total=to_float(summary["expected_loss_total"]),
        items=[HighRiskBooking(**r) for r in rows],
    )


def get_model_metrics(conn: Connection) -> list[ModelMetrics]:
    return ml_service.get_model_metrics(conn, "cancellation_", RISK_TABLE)
