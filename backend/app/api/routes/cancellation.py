from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import DbConn, Filters
from app.schemas.cancellation import (
    BreakdownDimension,
    CancellationBreakdown,
    HighRiskPage,
    HighRiskSort,
    RiskBand,
)
from app.schemas.ml import ModelMetricsResponse
from app.services import cancellation_service

router = APIRouter(prefix="/cancellation", tags=["cancellation"])


@router.get("/breakdown", response_model=CancellationBreakdown)
def get_breakdown(
    conn: DbConn,
    flt: Filters,
    by: Annotated[BreakdownDimension, Query(description="Chiều phân tích tỉ lệ hủy")] = "lead_time",
    top_n: Annotated[
        int | None, Query(ge=1, le=200, description="Chỉ lấy N nhóm nhiều booking nhất")
    ] = None,
) -> CancellationBreakdown:
    """Tỉ lệ hủy theo lead time / kênh / loại đặt cọc / quốc gia (+ phân khúc, loại khách).

    Tỉ lệ tính lại từ tổng.
    """
    return cancellation_service.get_breakdown(conn, flt, by, top_n)


@router.get("/high-risk", response_model=HighRiskPage)
def get_high_risk(
    conn: DbConn,
    flt: Filters,
    risk_band: Annotated[
        RiskBand | None, Query(description="Lọc theo nhóm rủi ro; bỏ trống = mọi nhóm")
    ] = "High",
    test_set_only: Annotated[
        bool, Query(description="Chỉ booking năm 2017 (điểm ngoài mẫu, model chưa thấy khi train)")
    ] = True,
    sort: Annotated[
        HighRiskSort,
        Query(description="probability: xác suất hủy; expected_loss: xác suất × doanh thu đặt"),
    ] = "probability",
    model_version: Annotated[
        str | None, Query(max_length=100, description="Mặc định: phiên bản mới nhất")
    ] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
) -> HighRiskPage:
    """Danh sách booking rủi ro hủy cao (phân trang).

    Dùng cho bộ phận Reservations gọi xác nhận / yêu cầu cọc.

    404 nếu bảng gold.ml_booking_risk chưa có dữ liệu.
    """
    return cancellation_service.get_high_risk(
        conn,
        flt,
        model_version=model_version,
        risk_band=risk_band,
        test_set_only=test_set_only,
        sort=sort,
        page=page,
        page_size=page_size,
    )


@router.get("/model-metrics", response_model=ModelMetricsResponse)
def get_model_metrics(conn: DbConn) -> ModelMetricsResponse:
    """AUC, precision, recall, F1, confusion matrix, ngưỡng rủi ro của các model dự đoán hủy.

    404 nếu chưa chạy script ML.
    """
    return ModelMetricsResponse(models=cancellation_service.get_model_metrics(conn))
