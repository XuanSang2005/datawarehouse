"""Phân tích hủy (G2): tỉ lệ hủy theo chiều, danh sách booking rủi ro cao, metric model."""

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
    """Tính tỉ lệ từ tổng, sắp xếp, cắt top N.

    Trả về (items, tổng booking, tổng hủy); hai tổng tính trên TOÀN BỘ nhóm, không chỉ top N.
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
    """Phiên bản được yêu cầu, hoặc mới nhất. 404 nếu bảng rỗng hay phiên bản không tồn tại."""
    ml_service.require_table(conn, RISK_TABLE)
    versions = ml_repo.fetch_risk_versions(conn)
    if not versions:
        raise ml_service.not_ready(RISK_TABLE)
    if model_version is None:
        return versions[0]
    if model_version not in versions:
        raise DataNotReadyError(
            f"Không có điểm rủi ro cho model_version '{model_version}'",
            hint=f"Các phiên bản hiện có: {', '.join(versions)}",
        )
    return model_version


def get_high_risk(
    conn: Connection,
    flt: BookingFilter,
    *,
    model_version: str | None,
    risk_band: RiskBand | None,
    test_set_only: bool,
    sort: HighRiskSort,
    page: int,
    page_size: int,
) -> HighRiskPage:
    version = resolve_risk_version(conn, model_version)
    total = cancellation_repo.count_high_risk(conn, flt, version, risk_band, test_set_only)
    rows = cancellation_repo.fetch_high_risk(
        conn, flt, version, risk_band, test_set_only, sort, page_size, (page - 1) * page_size
    )
    return HighRiskPage(
        model_version=version,
        filters=flt,
        risk_band=risk_band,
        sort=sort,
        page=page,
        page_size=page_size,
        total=total,
        items=[HighRiskBooking(**r) for r in rows],
    )


def get_model_metrics(conn: Connection) -> list[ModelMetrics]:
    return ml_service.get_model_metrics(conn, "cancellation_", RISK_TABLE)
