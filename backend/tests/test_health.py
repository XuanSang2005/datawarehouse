from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.core.db import get_connection
from app.main import app

client = TestClient(app)


@pytest.fixture
def no_db() -> Iterator[None]:
    """Thay kết nối DB bằng đối tượng giả: test chạy được cả khi không có PostgreSQL (vd: CI).

    FastAPI chạy dependency (mở kết nối) TRƯỚC khi validate query param,
    nên test validation phải override dependency này.
    """

    def fake_connection() -> Iterator[object]:
        yield object()

    app.dependency_overrides[get_connection] = fake_connection
    yield
    app.dependency_overrides.pop(get_connection, None)


def test_health_returns_status_even_without_db():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] in {"ok", "degraded"}
    assert body["database"] in {"up", "down"}


def test_pipeline_runs_validates_limit(no_db):
    assert client.get("/api/pipeline/runs?limit=0").status_code == 422
    assert client.get("/api/pipeline/runs?limit=501").status_code == 422
