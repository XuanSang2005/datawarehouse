"""Demand forecast and channel/market ranking. No DB needed."""

from datetime import date, datetime

import pytest

from app.core.errors import DataNotReadyError
from app.repositories import forecast_repo, ml_repo
from app.services import forecast_service, ranking_service


def test_pick_default_version_prefers_main_model():
    versions = [
        {"model_version": "forecast_seasonal_naive_v1", "created_at": datetime(2026, 11, 22)},
        {"model_version": "forecast_gbm_v1", "created_at": datetime(2026, 11, 20)},
        {"model_version": "forecast_gbm_v2", "created_at": datetime(2026, 11, 21)},
    ]
    assert forecast_service.pick_default_version(versions) == "forecast_gbm_v2"
    assert forecast_service.pick_default_version(versions[:1]) == "forecast_seasonal_naive_v1"


def test_build_series_marks_future_weeks_and_attaches_history():
    fc = [
        {
            "hotel_key": 1,
            "hotel_name": "City Hotel",
            "week_start_date": date(2017, 8, 21),
            "predicted_room_nights": 1500,
            "lower_bound": 1400,
            "upper_bound": 1700,
            "actual_room_nights": 1520,
            "horizon_weeks": 1,
        },
        {
            "hotel_key": 1,
            "hotel_name": "City Hotel",
            "week_start_date": date(2017, 8, 28),
            "predicted_room_nights": 1480,
            "lower_bound": 1350,
            "upper_bound": 1750,
            "actual_room_nights": None,
            "horizon_weeks": 1,
        },
    ]
    actual = [{"hotel_key": 1, "week_start_date": date(2017, 8, 21), "room_nights_sold": 1520}]
    [series] = forecast_service.build_series(fc, actual)
    assert [p.is_future for p in series.points] == [False, True]
    assert series.history[0].room_nights_sold == 1520


def test_forecast_unknown_version(monkeypatch):
    monkeypatch.setattr(ml_repo, "table_exists", lambda conn, name: True)
    monkeypatch.setattr(
        forecast_repo,
        "fetch_versions",
        lambda conn: [{"model_version": "forecast_gbm_v1", "created_at": datetime(2026, 1, 1)}],
    )
    with pytest.raises(DataNotReadyError):
        forecast_service.get_forecast(object(), None, "forecast_x")


def test_forecast_endpoint_404_when_table_missing(monkeypatch, client, no_db):
    monkeypatch.setattr(ml_repo, "table_exists", lambda conn, name: False)
    resp = client.get("/api/forecast?hotel_key=1")
    assert resp.status_code == 404
    assert "ml.forecast.train" in resp.json()["hint"]


def grp(key, bookings, canceled, nights, revenue):
    return {
        "key": key,
        "label": key,
        "grp": None,
        "bookings": bookings,
        "canceled_bookings": canceled,
        "room_nights_sold": nights,
        "realized_revenue": revenue,
        "lost_revenue": 0,
    }


ROWS = [
    grp("OTA", 1000, 400, 2000, 200_000),  # ADR 100, 40% canceled
    grp("Direct", 300, 30, 600, 75_000),  # ADR 125, 10% canceled
    grp("Groups", 200, 120, 300, 22_500),  # ADR 75,  60% canceled
    grp("Tiny", 5, 0, 5, 2_500),  # ADR 500, too few bookings
]


def test_rank_by_revenue_descending_with_share_over_all_groups():
    items, total, ranked = ranking_service.rank_groups(
        ROWS, "realized_revenue", min_bookings=0, top_n=10
    )
    assert [i.key for i in items] == ["OTA", "Direct", "Groups", "Tiny"]
    assert [i.rank for i in items] == [1, 2, 3, 4]
    assert total == 300_000
    assert items[0].revenue_share == pytest.approx(200_000 / 300_000)


def test_rank_min_bookings_excludes_noisy_groups_from_adr_ranking():
    items, total, ranked = ranking_service.rank_groups(ROWS, "adr", min_bookings=50, top_n=10)
    assert [i.key for i in items] == ["Direct", "OTA", "Groups"]
    assert ranked == 3
    assert total == 300_000  # the total still includes dropped groups


def test_rank_cancellation_rate_ascending_and_top_n():
    items, _, ranked = ranking_service.rank_groups(
        ROWS, "cancellation_rate", min_bookings=50, top_n=2
    )
    assert [i.key for i in items] == ["Direct", "OTA"]
    assert ranked == 3


def test_ranking_validation(client, no_db):
    assert client.get("/api/channels/ranking?sort_by=profit").status_code == 422
    assert client.get("/api/markets/ranking?top_n=0").status_code == 422
