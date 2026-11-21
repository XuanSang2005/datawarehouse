"""Phân tích hủy, metric ML, xử lý khi bảng ML chưa có. Không cần DB."""

from datetime import datetime

import pytest

from app.core.errors import DataNotReadyError
from app.repositories import ml_repo
from app.services import cancellation_service, ml_service


def group(key, bookings, canceled, band_order=None, label=None):
    return {
        "key": key,
        "label": label or key,
        "band_order": band_order,
        "bookings": bookings,
        "canceled_bookings": canceled,
        "lost_revenue": canceled * 100,
        "net_lost_revenue": canceled * 80,
    }


def test_breakdown_orders_lead_time_bands_by_band_order():
    rows = [
        group("31-90", 50, 20, band_order=3),
        group("0-7", 10, 1, band_order=1),
        group("8-30", 40, 10, band_order=2),
    ]
    items, total, canceled = cancellation_service.build_breakdown(rows, top_n=None)
    assert [i.key for i in items] == ["0-7", "8-30", "31-90"]
    assert (total, canceled) == (100, 31)
    assert items[0].cancellation_rate == pytest.approx(0.1)
    assert items[2].booking_share == pytest.approx(0.5)


def test_breakdown_top_n_keeps_largest_groups_but_totals_cover_all():
    rows = [group("PRT", 100, 50), group("GBR", 30, 6), group("FRA", 20, 4), group("XYZ", 1, 1)]
    items, total, _ = cancellation_service.build_breakdown(rows, top_n=2)
    assert [i.key for i in items] == ["PRT", "GBR"]
    assert total == 151  # tỉ trọng/tỉ lệ chung tính trên mọi nhóm, không chỉ top N


def test_group_metrics_nests_by_dataset():
    t = datetime(2026, 11, 21)
    rows = [
        {
            "model_name": "cancellation_gbm",
            "model_version": "v1",
            "dataset": "test",
            "metric_name": "auc",
            "metric_value": 0.888,
            "trained_at": t,
        },
        {
            "model_name": "cancellation_gbm",
            "model_version": "v1",
            "dataset": "validation",
            "metric_name": "threshold_high",
            "metric_value": 0.31,
            "trained_at": t,
        },
        {
            "model_name": "cancellation_logreg",
            "model_version": "v1",
            "dataset": "test",
            "metric_name": "auc",
            "metric_value": 0.871,
            "trained_at": t,
        },
    ]
    models = ml_service.group_metrics(rows)
    assert [m.model_name for m in models] == ["cancellation_gbm", "cancellation_logreg"]
    assert models[0].metrics == {"test": {"auc": 0.888}, "validation": {"threshold_high": 0.31}}


def test_missing_ml_table_raises_data_not_ready(monkeypatch):
    monkeypatch.setattr(ml_repo, "table_exists", lambda conn, name: False)
    with pytest.raises(DataNotReadyError) as exc:
        cancellation_service.resolve_risk_version(object(), None)
    assert "ml.cancellation.train" in exc.value.hint


def test_unknown_model_version_lists_available(monkeypatch):
    monkeypatch.setattr(ml_repo, "table_exists", lambda conn, name: True)
    monkeypatch.setattr(
        ml_repo, "fetch_risk_versions", lambda conn: ["cancellation_v2", "cancellation_v1"]
    )
    assert cancellation_service.resolve_risk_version(object(), None) == "cancellation_v2"
    with pytest.raises(DataNotReadyError) as exc:
        cancellation_service.resolve_risk_version(object(), "nope")
    assert "cancellation_v1" in exc.value.hint


def test_model_metrics_endpoint_returns_404_when_ml_not_run(monkeypatch, client, no_db):
    monkeypatch.setattr(ml_repo, "table_exists", lambda conn, name: False)
    resp = client.get("/api/cancellation/model-metrics")
    assert resp.status_code == 404
    body = resp.json()
    assert body["error_type"] == "DataNotReady"
    assert "python -m ml" in body["hint"]


def test_high_risk_validation(client, no_db):
    assert client.get("/api/cancellation/high-risk?risk_band=Extreme").status_code == 422
    assert client.get("/api/cancellation/high-risk?page=0").status_code == 422
    assert client.get("/api/cancellation/high-risk?page_size=201").status_code == 422
    assert client.get("/api/cancellation/high-risk?sort=random").status_code == 422
    assert client.get("/api/cancellation/breakdown?by=weather").status_code == 422
