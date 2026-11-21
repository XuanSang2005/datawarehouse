from datetime import date

from pydantic import BaseModel, Field, model_validator


class WhatIfRequest(BaseModel):
    """Simulation parameters. The dataset has no room count or costs, so the user enters them
    (rule 10).
    """

    hotel_key: int = Field(ge=1, description="Hotel to simulate")
    capacity: int = Field(
        ge=1, le=5000, description="Hotel room count (suggested: >= peak_rooms_occupied)"
    )
    overbooking_pct: float = Field(
        0.0,
        ge=0,
        le=0.5,
        description="Extra reservations accepted above capacity, as a share of it (0.05 = 5%)",
    )
    deposit_risk_threshold: float | None = Field(
        None,
        ge=0,
        le=1,
        description="Require a deposit when cancellation probability >= threshold. "
        "Default: the model's High threshold",
    )
    deposit_rate: float | None = Field(
        None,
        ge=0,
        le=1,
        description="Share of booked revenue retained on cancellation. "
        "Default: gold.business_assumptions",
    )
    deposit_attrition_pct: float = Field(
        0.05,
        ge=0,
        le=1,
        description="Share of guests who would NOT cancel but drop the booking when asked "
        "for a deposit",
    )
    walk_cost: float = Field(
        150.0, ge=0, le=10000, description="Walk cost per room-night walked (EUR)"
    )
    ota_commission: float = Field(
        0.15, ge=0, le=0.5, description="OTA commission on revenue through the OTA channel"
    )
    date_from: date = Field(
        date(2017, 1, 1), description="From date (default: start of the 2017 test set)"
    )
    date_to: date = Field(date(2017, 8, 31), description="To date (inclusive)")
    max_curve_pct: float = Field(
        0.3, ge=0.01, le=0.5, description="Largest overbooking level on the tested curve"
    )

    @model_validator(mode="after")
    def check_dates(self) -> "WhatIfRequest":
        if self.date_from > self.date_to:
            raise ValueError("date_from must be less than or equal to date_to")
        return self


class WhatIfAssumptions(BaseModel):
    """Values actually used (after defaults are filled in), for display and the report."""

    hotel_key: int
    hotel_name: str
    capacity: int
    overbooking_pct: float
    deposit_risk_threshold: float | None
    deposit_rate: float
    deposit_attrition_pct: float
    walk_cost: float
    ota_commission: float
    date_from: date
    date_to: date
    risk_model_version: str | None


class BaselineResult(BaseModel):
    nights: int = Field(description="Number of nights with data in the period")
    room_nights_sold: int
    room_nights_canceled: int
    realized_revenue: float
    adr: float | None
    night_cancellation_rate: float | None = Field(
        description="Canceled room-nights / booked room-nights"
    )
    ota_revenue_share: float | None
    ota_commission_cost: float
    occupancy_rate: float | None = Field(description="room_nights_sold / (capacity × nights)")
    revpar: float | None = Field(description="realized_revenue / (capacity × nights)")
    nights_over_capacity: int = Field(
        description="Number of nights with more occupied rooms than the entered capacity"
    )


class OverbookingResult(BaseModel):
    overbooking_pct: float
    extra_reservations: float = Field(
        description="Extra reservations accepted thanks to overbooking (expected)"
    )
    extra_show_ups: float = Field(description="Of which actually show up (not canceled)")
    rooms_filled: float = Field(description="Empty room-nights filled")
    rooms_walked: float = Field(description="Room-nights walked because the hotel is full")
    revenue_recovered: float = Field(
        description="rooms_filled × that night's ADR × net-of-commission factor (EUR)"
    )
    walk_cost_total: float
    net_benefit: float = Field(description="revenue_recovered − walk_cost_total")
    nights_with_extra_bookings: int = Field(
        description="Number of nights taking extra reservations ('full' nights on the books)"
    )
    nights_at_risk: int = Field(
        description="Number of nights at risk of overselling (rooms_walked > 0)"
    )
    occupancy_rate_after: float | None
    revpar_after: float | None


class DepositResult(BaseModel):
    risk_threshold: float
    deposit_rate: float
    attrition_pct: float
    bookings: int = Field(description="Bookings arriving in the period")
    flagged_bookings: int = Field(
        description="Bookings asked for a deposit (probability >= threshold, not yet Non Refund)"
    )
    flagged_canceled: int
    flagged_precision: float | None = Field(
        description="Share of deposit-flagged bookings that actually canceled"
    )
    deposit_retained: float = Field(
        description="deposit_rate × booked revenue of flagged bookings that canceled"
    )
    attrition_loss: float = Field(
        description="attrition_pct × revenue (net of commission) of flagged bookings "
        "that did not cancel"
    )
    net_benefit: float
    in_sample_bookings: int = Field(
        description="Bookings with in-sample scores (seen by the model in training): optimistic"
    )


class CurvePoint(BaseModel):
    overbooking_pct: float
    revenue_recovered: float
    walk_cost_total: float
    net_benefit: float
    rooms_walked: float
    nights_at_risk: int


class WhatIfResponse(BaseModel):
    assumptions: WhatIfAssumptions
    baseline: BaselineResult
    overbooking: OverbookingResult
    deposit: DepositResult | None = Field(
        description="None if gold.ml_booking_risk is not available"
    )
    total_net_benefit: float = Field(description="overbooking.net_benefit + deposit.net_benefit")
    curve: list[CurvePoint] = Field(
        description="Overbooking net benefit at each level 0..max_curve_pct (1% steps)"
    )
    recommended_overbooking_pct: float = Field(
        description="Level with the highest net_benefit on the curve"
    )
    warnings: list[str]
