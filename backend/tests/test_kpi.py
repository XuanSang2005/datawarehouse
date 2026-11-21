"""KPI: phép tính từ tổng (quy tắc 8), bộ lọc SQL, validate tham số. Không cần DB."""

from datetime import date

import pytest

from app.repositories.booking_sql import build_where
from app.repositories.kpi_repo import PERIOD_SQL
from app.schemas.common import BookingFilter
from app.services import kpi_service
from app.services.kpi_math import kpi_from_sums, ratio


def sums(**overrides):
    row = {
        "bookings": 10,
        "canceled_bookings": 4,
        "room_nights_sold": 20,
        "realized_revenue": 2000,
        "lost_revenue": 500,
        "net_lost_revenue": 400,
        "sum_lead_time": 300,
        "sum_total_nights": 30,
    }
    row.update(overrides)
    return row


def test_kpi_from_sums_computes_ratios_from_totals():
    kpi = kpi_from_sums(sums())
    assert kpi.cancellation_rate == pytest.approx(0.4)
    assert kpi.adr == pytest.approx(100.0)
    assert kpi.avg_lead_time == pytest.approx(30.0)
    assert kpi.avg_los == pytest.approx(3.0)


def test_kpi_from_sums_handles_empty_group():
    kpi = kpi_from_sums(
        sums(bookings=0, canceled_bookings=0, room_nights_sold=0, realized_revenue=None)
    )
    assert kpi.cancellation_rate is None
    assert kpi.adr is None
    assert kpi.realized_revenue == 0.0


def test_total_is_sum_over_sum_not_average_of_averages():
    # Nhóm A: ADR 100 trên 10 đêm; nhóm B: ADR 200 trên 90 đêm.
    a = sums(room_nights_sold=10, realized_revenue=1000, bookings=1, canceled_bookings=1)
    b = sums(room_nights_sold=90, realized_revenue=18000, bookings=9, canceled_bookings=0)
    total = kpi_from_sums(kpi_service.combine_sums([a, b]))
    assert total.adr == pytest.approx(190.0)  # trung bình của trung bình sẽ ra 150
    assert total.cancellation_rate == pytest.approx(0.1)  # 1/10, không phải (1 + 0)/2


def test_ratio_zero_denominator():
    assert ratio(5, 0) is None
    assert ratio(None, 3) is None


def test_build_where_uses_bind_parameters_only():
    flt = BookingFilter(
        hotel_key=1,
        date_from=date(2017, 1, 1),
        date_to=date(2017, 3, 31),
        channel_group="OTA'; DROP TABLE x; --",
        country_code="PRT",
    )
    where, params = build_where(flt)
    assert where.startswith("WHERE ")
    assert "DROP" not in where  # giá trị không bao giờ nằm trong chuỗi SQL
    assert params == {
        "hotel_key": 1,
        "date_from": date(2017, 1, 1),
        "date_to": date(2017, 3, 31),
        "channel_group": "OTA'; DROP TABLE x; --",
        "country_code": "PRT",
    }


def test_build_where_empty_filter():
    assert build_where(BookingFilter()) == ("", {})


def test_every_grain_has_sql():
    assert set(PERIOD_SQL) == {"year", "quarter", "month", "week"}


def test_kpi_validation(client, no_db):
    assert client.get("/api/kpi/timeseries?grain=day").status_code == 422
    assert client.get("/api/kpi/summary?hotel_key=0").status_code == 422
    resp = client.get("/api/kpi/summary?date_from=2017-02-01&date_to=2017-01-01")
    assert resp.status_code == 422
    assert resp.json()["error_type"] == "InvalidParameter"


def test_country_code_is_uppercased(monkeypatch, client, no_db):
    seen = {}

    def fake_summary(conn, flt):
        seen["flt"] = flt
        raise RuntimeError("stop")

    monkeypatch.setattr(kpi_service, "get_summary", fake_summary)
    with pytest.raises(RuntimeError):
        client.get("/api/kpi/summary?country_code=prt")
    assert seen["flt"].country_code == "PRT"
