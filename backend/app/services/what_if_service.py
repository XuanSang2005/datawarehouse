"""Mô phỏng what-if cho quyết định overbooking và chính sách đặt cọc (G4).

Dataset không có số phòng, chi phí đền bù hay hoa hồng, nên các giá trị này là THAM SỐ người
dùng nhập (quy tắc 10). Các hàm tính toán (`simulate_overbooking`, `simulate_deposit`,
`build_curve`) là hàm thuần, không đọc DB, để unit test với dữ liệu giả và dùng lại công thức
trong báo cáo.

Ký hiệu (cho 1 khách sạn, 1 đêm d trong giai đoạn mô phỏng):
    C      = capacity (số phòng, người dùng nhập)
    p      = overbooking_pct
    occ_d  = số phòng có khách thực tế (gold.fact_daily_occupancy.rooms_occupied)
    can_d  = số phòng của booking đã hủy cho đêm d (rooms_canceled)
    rev_d  = doanh thu thực của đêm d (realized_revenue)

1. Overbooking (`simulate_overbooking`)
    booked_d = occ_d + can_d                      đặt phòng trên sổ cho đêm d
    r_d      = can_d / booked_d                   tỉ lệ hủy đêm d (0 nếu booked_d = 0)
    extra_d  = C × p   nếu booked_d >= C, ngược lại 0
               Giả định: chỉ đêm "kín trên sổ" (booked_d >= C) mới có nhu cầu bị từ chối
               để nhận thêm.
    show_d   = extra_d × (1 − r_d)                 số đặt thêm đến ở thật
    spare_d  = max(C − occ_d, 0)                   phòng trống thực tế
    fill_d   = min(show_d, spare_d)                phòng trống được lấp
    walk_d   = show_d − fill_d                     khách phải chuyển đi (hết phòng)
    adr_d    = rev_d / occ_d  (đêm không có khách: ADR cả giai đoạn)
    Doanh thu cứu được = Σ fill_d × adr_d × (1 − s_OTA × k)
                         (s_OTA = tỉ trọng doanh thu OTA, k = hoa hồng OTA)
    Chi phí đền bù     = Σ walk_d × walk_cost
    Lợi ích ròng       = doanh thu cứu được − chi phí đền bù
    Đêm có nguy cơ hết phòng = số đêm có walk_d > 0
    Dùng r_d thực tế của từng đêm (kỳ vọng theo đêm); không mô hình hóa biến động ngẫu nhiên
    trong đêm, nên rủi ro hết phòng có thể bị đánh giá thấp: nên chọn mức overbooking thấp hơn
    mức tối ưu một chút.

2. Đặt cọc theo rủi ro (`simulate_deposit`), trên booking ĐẾN trong giai đoạn
    flagged    = cancel_probability >= ngưỡng VÀ deposit_type <> 'Non Refund' (đã có cọc thì bỏ qua)
    Tiền cọc giữ lại  = deposit_rate × Σ booked_revenue (flagged VÀ hủy)
    Mất do khách bỏ   = attrition × Σ realized_revenue_sau_hoa_hong (flagged VÀ không hủy)
                        (booking OTA tính sau hoa hồng: × (1 − k))
    Lợi ích ròng      = tiền cọc giữ lại − mất do khách bỏ

3. Tổng lợi ích ròng = (1) + (2). Mức overbooking gợi ý = mức có lợi ích ròng (1) lớn nhất trên lưới
   0%, 1%, ..., max_curve_pct (hòa thì chọn mức thấp hơn, ít rủi ro hơn).

Occupancy = room_nights / (C × số đêm)
RevPAR    = doanh thu phòng (gộp, trước hoa hồng) / (C × số đêm)
"""

from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import Connection

from app.core.errors import InvalidParameterError
from app.repositories import ml_repo, what_if_repo
from app.schemas.what_if import (
    BaselineResult,
    CurvePoint,
    DepositResult,
    OverbookingResult,
    WhatIfAssumptions,
    WhatIfRequest,
    WhatIfResponse,
)
from app.services.kpi_math import ratio, to_float

RISK_TABLE = "gold.ml_booking_risk"
RISK_MODEL_NAME = "cancellation_gbm"
DEFAULT_DEPOSIT_RATE = 0.2
CURVE_STEP = 0.01


@dataclass(frozen=True)
class Night:
    rooms_occupied: float
    rooms_canceled: float
    realized_revenue: float


@dataclass(frozen=True)
class DepositAggregates:
    bookings: int
    flagged_bookings: int
    flagged_canceled: int
    flagged_canceled_booked_revenue: float
    flagged_kept_direct_revenue: float
    flagged_kept_ota_revenue: float
    in_sample_bookings: int


def revenue_factor(ota_revenue_share: float | None, ota_commission: float) -> float:
    """Phần doanh thu khách sạn giữ lại sau hoa hồng: 1 − s_OTA × k."""
    return 1.0 - (ota_revenue_share or 0.0) * ota_commission


def period_adr(nights: Sequence[Night]) -> float:
    return (
        ratio(sum(n.realized_revenue for n in nights), sum(n.rooms_occupied for n in nights)) or 0.0
    )


def simulate_overbooking(
    nights: Sequence[Night],
    capacity: int,
    overbooking_pct: float,
    walk_cost: float,
    net_factor: float,
) -> OverbookingResult:
    """Mục 1 của docstring module."""
    fallback_adr = period_adr(nights)
    extra_total = shows_total = filled_total = walked_total = gross_recovered = 0.0
    nights_extra = nights_at_risk = 0
    for n in nights:
        booked = n.rooms_occupied + n.rooms_canceled
        cancel_rate = n.rooms_canceled / booked if booked > 0 else 0.0
        extra = capacity * overbooking_pct if booked >= capacity else 0.0
        shows = extra * (1.0 - cancel_rate)
        spare = max(capacity - n.rooms_occupied, 0.0)
        filled = min(shows, spare)
        walked = shows - filled
        adr = n.realized_revenue / n.rooms_occupied if n.rooms_occupied > 0 else fallback_adr

        extra_total += extra
        shows_total += shows
        filled_total += filled
        walked_total += walked
        gross_recovered += filled * adr
        nights_extra += extra > 0
        nights_at_risk += walked > 1e-9

    capacity_nights = capacity * len(nights)
    sold = sum(n.rooms_occupied for n in nights)
    revenue = sum(n.realized_revenue for n in nights)
    recovered = gross_recovered * net_factor
    walk_total = walked_total * walk_cost
    return OverbookingResult(
        overbooking_pct=overbooking_pct,
        extra_reservations=extra_total,
        extra_show_ups=shows_total,
        rooms_filled=filled_total,
        rooms_walked=walked_total,
        revenue_recovered=recovered,
        walk_cost_total=walk_total,
        net_benefit=recovered - walk_total,
        nights_with_extra_bookings=nights_extra,
        nights_at_risk=nights_at_risk,
        occupancy_rate_after=ratio(sold + filled_total, capacity_nights),
        revpar_after=ratio(revenue + gross_recovered, capacity_nights),
    )


def build_curve(
    nights: Sequence[Night],
    capacity: int,
    walk_cost: float,
    net_factor: float,
    max_pct: float,
) -> tuple[list[CurvePoint], float]:
    """Mục 3: lợi ích ròng ở từng mức overbooking trên lưới, và mức tốt nhất."""
    steps = round(max_pct / CURVE_STEP)
    curve: list[CurvePoint] = []
    best_pct, best_value = 0.0, float("-inf")
    for i in range(steps + 1):
        pct = round(i * CURVE_STEP, 4)
        result = simulate_overbooking(nights, capacity, pct, walk_cost, net_factor)
        curve.append(
            CurvePoint(
                overbooking_pct=pct,
                revenue_recovered=result.revenue_recovered,
                walk_cost_total=result.walk_cost_total,
                net_benefit=result.net_benefit,
                rooms_walked=result.rooms_walked,
                nights_at_risk=result.nights_at_risk,
            )
        )
        if result.net_benefit > best_value + 1e-6:
            best_pct, best_value = pct, result.net_benefit
    return curve, best_pct


def simulate_deposit(
    agg: DepositAggregates,
    risk_threshold: float,
    deposit_rate: float,
    attrition_pct: float,
    ota_commission: float,
) -> DepositResult:
    """Mục 2 của docstring module."""
    retained = deposit_rate * agg.flagged_canceled_booked_revenue
    kept_net = agg.flagged_kept_direct_revenue + agg.flagged_kept_ota_revenue * (
        1.0 - ota_commission
    )
    attrition_loss = attrition_pct * kept_net
    return DepositResult(
        risk_threshold=risk_threshold,
        deposit_rate=deposit_rate,
        attrition_pct=attrition_pct,
        bookings=agg.bookings,
        flagged_bookings=agg.flagged_bookings,
        flagged_canceled=agg.flagged_canceled,
        flagged_precision=ratio(agg.flagged_canceled, agg.flagged_bookings),
        deposit_retained=retained,
        attrition_loss=attrition_loss,
        net_benefit=retained - attrition_loss,
        in_sample_bookings=agg.in_sample_bookings,
    )


def build_baseline(
    nights: Sequence[Night],
    capacity: int,
    ota_revenue: float,
    booking_revenue: float,
    ota_commission: float,
) -> BaselineResult:
    sold = sum(n.rooms_occupied for n in nights)
    canceled = sum(n.rooms_canceled for n in nights)
    revenue = sum(n.realized_revenue for n in nights)
    capacity_nights = capacity * len(nights)
    return BaselineResult(
        nights=len(nights),
        room_nights_sold=int(sold),
        room_nights_canceled=int(canceled),
        realized_revenue=revenue,
        adr=ratio(revenue, sold),
        night_cancellation_rate=ratio(canceled, sold + canceled),
        ota_revenue_share=ratio(ota_revenue, booking_revenue),
        ota_commission_cost=ota_revenue * ota_commission,
        occupancy_rate=ratio(sold, capacity_nights),
        revpar=ratio(revenue, capacity_nights),
        nights_over_capacity=sum(n.rooms_occupied > capacity for n in nights),
    )


def _resolve_deposit(
    conn: Connection, req: WhatIfRequest, warnings: list[str]
) -> tuple[DepositAggregates | None, float | None, str | None]:
    """Đọc dữ liệu cọc nếu đã có kết quả model hủy; nếu chưa thì bỏ qua phần cọc kèm cảnh báo."""
    if not ml_repo.table_exists(conn, RISK_TABLE):
        warnings.append(
            "Chưa có gold.ml_booking_risk: bỏ qua mô phỏng đặt cọc "
            "(chạy python -m ml.cancellation.train)."
        )
        return None, None, None
    versions = ml_repo.fetch_risk_versions(conn)
    if not versions:
        warnings.append("gold.ml_booking_risk đang rỗng: bỏ qua mô phỏng đặt cọc.")
        return None, None, None
    version = versions[0]
    threshold = req.deposit_risk_threshold
    if threshold is None:
        threshold = ml_repo.fetch_metric_value(
            conn, RISK_MODEL_NAME, "threshold_high", "validation"
        )
    if threshold is None:
        threshold = 0.5
        warnings.append("Không tìm thấy ngưỡng High của model; dùng ngưỡng cọc mặc định 0.5.")
    row = what_if_repo.fetch_deposit_aggregates(
        conn, req.hotel_key, req.date_from, req.date_to, threshold, version
    )
    agg = DepositAggregates(
        bookings=int(row["bookings"]),
        flagged_bookings=int(row["flagged_bookings"]),
        flagged_canceled=int(row["flagged_canceled"]),
        flagged_canceled_booked_revenue=to_float(row["flagged_canceled_booked_revenue"]),
        flagged_kept_direct_revenue=to_float(row["flagged_kept_direct_revenue"]),
        flagged_kept_ota_revenue=to_float(row["flagged_kept_ota_revenue"]),
        in_sample_bookings=int(row["in_sample_bookings"]),
    )
    if agg.in_sample_bookings:
        warnings.append(
            f"{agg.in_sample_bookings} booking trong giai đoạn có điểm rủi ro in-sample "
            "(đến trước 2017, model đã thấy khi train): lợi ích đặt cọc bị đánh giá lạc quan. "
            "Nên mô phỏng trên năm 2017."
        )
    return agg, threshold, version


def run_what_if(conn: Connection, req: WhatIfRequest) -> WhatIfResponse:
    hotel_name = what_if_repo.fetch_hotel_name(conn, req.hotel_key)
    if hotel_name is None:
        raise InvalidParameterError(f"Không có khách sạn hotel_key={req.hotel_key}")
    nights = [
        Night(
            rooms_occupied=float(r["rooms_occupied"]),
            rooms_canceled=float(r["rooms_canceled"]),
            realized_revenue=to_float(r["realized_revenue"]),
        )
        for r in what_if_repo.fetch_nights(conn, req.hotel_key, req.date_from, req.date_to)
    ]
    if not nights:
        raise InvalidParameterError(
            "Không có dữ liệu đêm nào trong giai đoạn đã chọn (dữ liệu: 2015-07-01 → 2017-08-31)"
        )

    warnings: list[str] = []
    rev = what_if_repo.fetch_revenue_by_channel(conn, req.hotel_key, req.date_from, req.date_to)
    baseline = build_baseline(
        nights,
        req.capacity,
        to_float(rev["ota_revenue"]),
        to_float(rev["realized_revenue"]),
        req.ota_commission,
    )
    if baseline.nights_over_capacity:
        peak = int(max(n.rooms_occupied for n in nights))
        warnings.append(
            f"capacity = {req.capacity} nhỏ hơn số phòng có khách thực tế ở "
            f"{baseline.nights_over_capacity} đêm "
            f"(cao nhất {peak}). Nên nhập capacity >= {peak}."
        )

    net_factor = revenue_factor(baseline.ota_revenue_share, req.ota_commission)
    overbooking = simulate_overbooking(
        nights, req.capacity, req.overbooking_pct, req.walk_cost, net_factor
    )
    curve, best_pct = build_curve(
        nights, req.capacity, req.walk_cost, net_factor, req.max_curve_pct
    )

    deposit_rate = req.deposit_rate
    if deposit_rate is None:
        deposit_rate = (
            what_if_repo.fetch_assumption(conn, "non_refund_deposit_rate") or DEFAULT_DEPOSIT_RATE
        )
    agg, threshold, version = _resolve_deposit(conn, req, warnings)
    deposit = (
        simulate_deposit(
            agg, threshold, deposit_rate, req.deposit_attrition_pct, req.ota_commission
        )
        if agg is not None and threshold is not None
        else None
    )

    return WhatIfResponse(
        assumptions=WhatIfAssumptions(
            hotel_key=req.hotel_key,
            hotel_name=hotel_name,
            capacity=req.capacity,
            overbooking_pct=req.overbooking_pct,
            deposit_risk_threshold=threshold,
            deposit_rate=deposit_rate,
            deposit_attrition_pct=req.deposit_attrition_pct,
            walk_cost=req.walk_cost,
            ota_commission=req.ota_commission,
            date_from=req.date_from,
            date_to=req.date_to,
            risk_model_version=version,
        ),
        baseline=baseline,
        overbooking=overbooking,
        deposit=deposit,
        total_net_benefit=overbooking.net_benefit + (deposit.net_benefit if deposit else 0.0),
        curve=curve,
        recommended_overbooking_pct=best_pct,
        warnings=warnings,
    )
