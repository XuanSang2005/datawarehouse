from datetime import date

from pydantic import BaseModel, Field, model_validator


class WhatIfRequest(BaseModel):
    """Tham số mô phỏng. Dataset không có số phòng và chi phí, nên người dùng nhập (quy tắc 10)."""

    hotel_key: int = Field(ge=1, description="Khách sạn mô phỏng")
    capacity: int = Field(
        ge=1, le=5000, description="Số phòng của khách sạn (gợi ý: >= peak_rooms_occupied)"
    )
    overbooking_pct: float = Field(
        0.0,
        ge=0,
        le=0.5,
        description="Nhận thêm đặt phòng vượt công suất, tỉ lệ của capacity (0.05 = 5%)",
    )
    deposit_risk_threshold: float | None = Field(
        None,
        ge=0,
        le=1,
        description="Yêu cầu cọc khi xác suất hủy >= ngưỡng. Mặc định: ngưỡng High của model",
    )
    deposit_rate: float | None = Field(
        None,
        ge=0,
        le=1,
        description="Tỉ lệ tiền cọc giữ lại khi hủy. Mặc định: gold.business_assumptions",
    )
    deposit_attrition_pct: float = Field(
        0.05, ge=0, le=1, description="Tỉ lệ khách KHÔNG hủy nhưng bỏ đặt vì bị yêu cầu cọc"
    )
    walk_cost: float = Field(
        150.0, ge=0, le=10000, description="Chi phí đền bù mỗi đêm phòng phải chuyển khách đi (EUR)"
    )
    ota_commission: float = Field(
        0.15, ge=0, le=0.5, description="Hoa hồng OTA trên doanh thu qua kênh OTA"
    )
    date_from: date = Field(date(2017, 1, 1), description="Từ ngày (mặc định: đầu tập test 2017)")
    date_to: date = Field(date(2017, 8, 31), description="Đến ngày (bao gồm)")
    max_curve_pct: float = Field(
        0.3, ge=0.01, le=0.5, description="Mức overbooking lớn nhất trong đường cong thử"
    )

    @model_validator(mode="after")
    def check_dates(self) -> "WhatIfRequest":
        if self.date_from > self.date_to:
            raise ValueError("date_from phải nhỏ hơn hoặc bằng date_to")
        return self


class WhatIfAssumptions(BaseModel):
    """Giá trị thực sự đã dùng (sau khi điền mặc định), để hiển thị và đưa vào báo cáo."""

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
    nights: int = Field(description="Số đêm trong giai đoạn có dữ liệu")
    room_nights_sold: int
    room_nights_canceled: int
    realized_revenue: float
    adr: float | None
    night_cancellation_rate: float | None = Field(description="Đêm phòng hủy / đêm phòng đã đặt")
    ota_revenue_share: float | None
    ota_commission_cost: float
    occupancy_rate: float | None = Field(description="room_nights_sold / (capacity × nights)")
    revpar: float | None = Field(description="realized_revenue / (capacity × nights)")
    nights_over_capacity: int = Field(
        description="Số đêm thực tế đã có khách nhiều hơn capacity nhập vào"
    )


class OverbookingResult(BaseModel):
    overbooking_pct: float
    extra_reservations: float = Field(description="Đặt phòng nhận thêm nhờ overbooking (kỳ vọng)")
    extra_show_ups: float = Field(description="Số trong đó đến ở thật (không hủy)")
    rooms_filled: float = Field(description="Đêm phòng trống được lấp")
    rooms_walked: float = Field(description="Đêm phòng phải chuyển khách đi vì hết phòng")
    revenue_recovered: float = Field(
        description="rooms_filled × ADR đêm đó × hệ số sau hoa hồng (EUR)"
    )
    walk_cost_total: float
    net_benefit: float = Field(description="revenue_recovered − walk_cost_total")
    nights_with_extra_bookings: int = Field(
        description="Số đêm nhận thêm đặt phòng (đêm 'kín' trên sổ)"
    )
    nights_at_risk: int = Field(description="Số đêm có nguy cơ hết phòng (rooms_walked > 0)")
    occupancy_rate_after: float | None
    revpar_after: float | None


class DepositResult(BaseModel):
    risk_threshold: float
    deposit_rate: float
    attrition_pct: float
    bookings: int = Field(description="Booking đến trong giai đoạn")
    flagged_bookings: int = Field(
        description="Booking bị yêu cầu cọc (xác suất >= ngưỡng, chưa phải Non Refund)"
    )
    flagged_canceled: int
    flagged_precision: float | None = Field(
        description="Tỉ lệ booking bị yêu cầu cọc mà thực tế hủy"
    )
    deposit_retained: float = Field(
        description="deposit_rate × doanh thu đặt của booking bị yêu cầu cọc rồi hủy"
    )
    attrition_loss: float = Field(
        description="attrition_pct × doanh thu (sau hoa hồng) của booking bị yêu cầu cọc "
        "mà không hủy"
    )
    net_benefit: float
    in_sample_bookings: int = Field(
        description="Booking có điểm in-sample (model đã thấy khi train): kết quả lạc quan"
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
    deposit: DepositResult | None = Field(description="None nếu chưa có gold.ml_booking_risk")
    total_net_benefit: float = Field(description="overbooking.net_benefit + deposit.net_benefit")
    curve: list[CurvePoint] = Field(
        description="Lợi ích ròng của overbooking ở từng mức 0..max_curve_pct (bước 1%)"
    )
    recommended_overbooking_pct: float = Field(
        description="Mức có net_benefit lớn nhất trên đường cong"
    )
    warnings: list[str]
