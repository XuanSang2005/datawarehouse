"""Schema dùng chung cho nhiều endpoint: bộ lọc booking và bộ KPI chuẩn."""

from datetime import date

from pydantic import BaseModel, Field


class BookingFilter(BaseModel):
    """Bộ lọc slice & dice dùng chung. Khoảng ngày lọc theo NGÀY ĐẾN (arrival_date) của booking."""

    hotel_key: int | None = Field(
        None, description="gold.dim_hotel.hotel_key; bỏ trống = cả 2 khách sạn"
    )
    date_from: date | None = Field(None, description="Ngày đến từ (bao gồm)")
    date_to: date | None = Field(None, description="Ngày đến đến (bao gồm)")
    channel_group: str | None = Field(None, description="gold.dim_channel.channel_group, vd 'OTA'")
    country_code: str | None = Field(None, description="Mã ISO alpha-3, vd 'PRT'")


class KpiValues(BaseModel):
    """Bộ KPI chuẩn. Tỉ lệ/trung bình luôn tính lại từ tổng (quy tắc 8), None nếu mẫu số = 0."""

    bookings: int
    canceled_bookings: int
    cancellation_rate: float | None = Field(description="canceled_bookings / bookings")
    room_nights_sold: int = Field(description="Đêm phòng của booking không hủy")
    realized_revenue: float = Field(description="Doanh thu thực thu (EUR), sau hủy")
    lost_revenue: float = Field(description="Doanh thu mất do hủy (EUR, cận trên)")
    net_lost_revenue: float = Field(description="lost_revenue trừ tiền cọc giữ lại (EUR)")
    adr: float | None = Field(description="realized_revenue / room_nights_sold (EUR)")
    avg_lead_time: float | None = Field(description="Số ngày đặt trước trung bình")
    avg_los: float | None = Field(description="Số đêm lưu trú trung bình mỗi booking")
