"""Unit test cho công thức what-if (services/what_if_service.py) với dữ liệu giả. Không cần DB."""

import pytest

from app.services.what_if_service import (
    DepositAggregates,
    Night,
    build_baseline,
    build_curve,
    revenue_factor,
    simulate_deposit,
    simulate_overbooking,
)

# Khách sạn 100 phòng, ADR 100 €
FULL_ON_BOOKS = Night(
    rooms_occupied=80, rooms_canceled=40, realized_revenue=8000
)  # 120 đặt, hủy 1/3
QUIET = Night(
    rooms_occupied=50, rooms_canceled=10, realized_revenue=5000
)  # 60 đặt < 100: không nhận thêm
SOLD_OUT = Night(
    rooms_occupied=100, rooms_canceled=25, realized_revenue=10000
)  # không còn phòng trống


def test_no_overbooking_means_no_change():
    r = simulate_overbooking(
        [FULL_ON_BOOKS, QUIET], capacity=100, overbooking_pct=0.0, walk_cost=150, net_factor=1.0
    )
    assert r.extra_reservations == 0
    assert r.net_benefit == 0
    assert r.nights_at_risk == 0


def test_overbooking_fills_empty_rooms_on_full_nights_only():
    # Đêm kín trên sổ: nhận thêm 10, đến ở 10 × (1 − 40/120) = 6.67, còn 20 phòng trống → lấp hết.
    r = simulate_overbooking(
        [FULL_ON_BOOKS, QUIET], capacity=100, overbooking_pct=0.10, walk_cost=150, net_factor=1.0
    )
    assert r.extra_reservations == pytest.approx(10)
    assert r.extra_show_ups == pytest.approx(10 * (1 - 40 / 120))
    assert r.rooms_filled == pytest.approx(r.extra_show_ups)
    assert r.rooms_walked == pytest.approx(0)
    assert r.revenue_recovered == pytest.approx(r.rooms_filled * 100)
    assert r.nights_with_extra_bookings == 1


def test_overbooking_walks_guests_when_no_room_left():
    # Đêm đã kín phòng thật: mọi khách đặt thêm đến ở đều phải chuyển đi.
    r = simulate_overbooking(
        [SOLD_OUT], capacity=100, overbooking_pct=0.10, walk_cost=150, net_factor=1.0
    )
    shows = 10 * (1 - 25 / 125)
    assert r.rooms_filled == pytest.approx(0)
    assert r.rooms_walked == pytest.approx(shows)
    assert r.walk_cost_total == pytest.approx(shows * 150)
    assert r.net_benefit == pytest.approx(-shows * 150)
    assert r.nights_at_risk == 1


def test_commission_reduces_recovered_revenue():
    factor = revenue_factor(ota_revenue_share=0.5, ota_commission=0.2)
    assert factor == pytest.approx(0.9)
    r = simulate_overbooking(
        [FULL_ON_BOOKS], capacity=100, overbooking_pct=0.10, walk_cost=0, net_factor=factor
    )
    assert r.revenue_recovered == pytest.approx(r.rooms_filled * 100 * 0.9)


def test_curve_starts_at_zero_and_recommends_interior_optimum():
    nights = [FULL_ON_BOOKS] * 5 + [SOLD_OUT] * 2
    curve, best = build_curve(nights, capacity=100, walk_cost=150, net_factor=1.0, max_pct=0.5)
    assert curve[0].overbooking_pct == 0 and curve[0].net_benefit == 0
    assert len(curve) == 51
    best_point = max(curve, key=lambda p: p.net_benefit)
    assert best == best_point.overbooking_pct
    assert 0 < best < 0.5  # lợi ích tăng rồi giảm khi phải đền bù nhiều


def test_curve_recommends_zero_when_overbooking_never_pays():
    curve, best = build_curve([SOLD_OUT], capacity=100, walk_cost=150, net_factor=1.0, max_pct=0.2)
    assert best == 0.0


def test_baseline_occupancy_and_revpar_use_capacity():
    b = build_baseline(
        [FULL_ON_BOOKS, QUIET],
        capacity=100,
        ota_revenue=3000,
        booking_revenue=12000,
        ota_commission=0.2,
    )
    assert b.occupancy_rate == pytest.approx(130 / 200)
    assert b.revpar == pytest.approx(13000 / 200)
    assert b.adr == pytest.approx(100)
    assert b.ota_revenue_share == pytest.approx(0.25)
    assert b.ota_commission_cost == pytest.approx(600)
    assert b.nights_over_capacity == 0
    assert build_baseline([SOLD_OUT], 90, 0, 1, 0).nights_over_capacity == 1


def test_deposit_policy_retains_deposit_minus_attrition():
    agg = DepositAggregates(
        bookings=100,
        flagged_bookings=20,
        flagged_canceled=15,
        flagged_canceled_booked_revenue=10_000,
        flagged_kept_direct_revenue=2_000,
        flagged_kept_ota_revenue=1_000,
        in_sample_bookings=0,
    )
    d = simulate_deposit(
        agg, risk_threshold=0.3, deposit_rate=0.2, attrition_pct=0.1, ota_commission=0.15
    )
    assert d.deposit_retained == pytest.approx(2_000)
    assert d.attrition_loss == pytest.approx(0.1 * (2_000 + 1_000 * 0.85))
    assert d.net_benefit == pytest.approx(d.deposit_retained - d.attrition_loss)
    assert d.flagged_precision == pytest.approx(0.75)


def test_what_if_request_validation(client, no_db):
    ok = {"hotel_key": 1, "capacity": 200}
    assert client.post("/api/what-if", json={**ok, "capacity": 0}).status_code == 422
    assert client.post("/api/what-if", json={**ok, "overbooking_pct": 0.9}).status_code == 422
    assert client.post("/api/what-if", json={**ok, "ota_commission": -0.1}).status_code == 422
    bad_dates = {**ok, "date_from": "2017-05-01", "date_to": "2017-01-01"}
    assert client.post("/api/what-if", json=bad_dates).status_code == 422
    assert client.post("/api/what-if", json={"capacity": 200}).status_code == 422
