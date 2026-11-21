from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.core.db import get_connection
from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


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
