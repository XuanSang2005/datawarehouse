"""What-if simulation for overbooking and deposit policy decisions (G4).

The dataset has no room count, walk cost or commission, so these values are user-entered
PARAMETERS (rule 10). The calculation functions (`simulate_overbooking`, `simulate_deposit`,
`build_curve`) are pure functions that do not read the DB, so they can be unit tested with fake
data and their formulas reused in the report.

Notation (for 1 hotel, 1 night d in the simulation period):
    C      = capacity (number of rooms, user-entered)
    p      = overbooking_pct
    occ_d  = actual occupied rooms (gold.fact_daily_occupancy.rooms_occupied)
    can_d  = rooms of canceled bookings for night d (rooms_canceled)
    rev_d  = realized revenue of night d (realized_revenue)

1. Overbooking (`simulate_overbooking`)
    booked_d = occ_d + can_d                      reservations on the books for night d
    r_d      = can_d / booked_d                   cancellation rate of night d (0 if booked_d = 0)
    extra_d  = C × p   if booked_d >= C, otherwise 0
               Assumption: only nights "full on the books" (booked_d >= C) have turned-away
               demand that could be accepted.
    show_d   = extra_d × (1 − r_d)                 extra reservations that actually show up
    spare_d  = max(C − occ_d, 0)                   actual empty rooms
    fill_d   = min(show_d, spare_d)                empty rooms filled
    walk_d   = show_d − fill_d                     guests walked (hotel full)
    adr_d    = rev_d / occ_d  (nights with no guests: ADR of the whole period)
    Revenue recovered = Σ fill_d × adr_d × (1 − s_OTA × k)
                        (s_OTA = OTA revenue share, k = OTA commission)
    Walk cost         = Σ walk_d × walk_cost
    Net benefit       = revenue recovered − walk cost
    Nights at risk of overselling = number of nights with walk_d > 0
    Uses the actual r_d of each night (expected value per night); random variation within a
    night is not modelled, so the overselling risk may be underestimated: choose an overbooking
    level slightly below the optimum.

2. Risk-based deposit (`simulate_deposit`), on bookings ARRIVING in the period
    flagged    = cancel_probability >= threshold AND deposit_type <> 'Non Refund' (skip if
                 a deposit is already taken)
    Deposit retained = deposit_rate × Σ booked_revenue (flagged AND canceled)
    Attrition loss   = attrition × Σ realized_revenue_net_of_commission (flagged AND not canceled)
                       (OTA bookings are counted net of commission: × (1 − k))
    Net benefit      = deposit retained − attrition loss

3. Total net benefit = (1) + (2). Recommended overbooking level = the level with the highest
   net benefit (1) on the grid 0%, 1%, ..., max_curve_pct (ties go to the lower, less risky level).

Occupancy = room_nights / (C × number of nights)
RevPAR    = room revenue (gross, before commission) / (C × number of nights)
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
    """Share of revenue the hotel keeps after commission: 1 − s_OTA × k."""
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
    """Section 1 of the module docstring."""
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
    """Section 3: net benefit at each overbooking level on the grid, and the best level."""
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
    """Section 2 of the module docstring."""
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
    """Read deposit data if cancellation model results exist; otherwise skip it with a warning."""
    if not ml_repo.table_exists(conn, RISK_TABLE):
        warnings.append(
            "gold.ml_booking_risk is not available: deposit simulation skipped "
            "(run python -m ml.cancellation.train)."
        )
        return None, None, None
    versions = ml_repo.fetch_risk_versions(conn)
    if not versions:
        warnings.append("gold.ml_booking_risk is empty: deposit simulation skipped.")
        return None, None, None
    version = versions[0]
    threshold = req.deposit_risk_threshold
    if threshold is None:
        threshold = ml_repo.fetch_metric_value(
            conn, RISK_MODEL_NAME, "threshold_high", "validation"
        )
    if threshold is None:
        threshold = 0.5
        warnings.append("Model High threshold not found; using the default deposit threshold 0.5.")
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
            f"{agg.in_sample_bookings} bookings in the period have in-sample risk scores "
            "(arrival before 2017, seen by the model in training): the deposit benefit is "
            "optimistic. Simulate on 2017 instead."
        )
    return agg, threshold, version


def run_what_if(conn: Connection, req: WhatIfRequest) -> WhatIfResponse:
    hotel_name = what_if_repo.fetch_hotel_name(conn, req.hotel_key)
    if hotel_name is None:
        raise InvalidParameterError(f"No hotel with hotel_key={req.hotel_key}")
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
            "No nights with data in the selected period (data: 2015-07-01 → 2017-08-31)"
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
            f"capacity = {req.capacity} is below the actual occupied rooms on "
            f"{baseline.nights_over_capacity} nights "
            f"(peak {peak}). Enter capacity >= {peak}."
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
