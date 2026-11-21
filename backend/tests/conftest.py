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
    """Replace the DB connection with a fake: tests run even without PostgreSQL (e.g. CI).

    FastAPI runs dependencies (opening the connection) BEFORE validating query params,
    so validation tests must override this dependency.
    """

    def fake_connection() -> Iterator[object]:
        yield object()

    app.dependency_overrides[get_connection] = fake_connection
    yield
    app.dependency_overrides.pop(get_connection, None)
