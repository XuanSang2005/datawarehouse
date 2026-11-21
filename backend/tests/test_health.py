def test_health_returns_status_even_without_db(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] in {"ok", "degraded"}
    assert body["database"] in {"up", "down"}


def test_pipeline_runs_validates_limit(client, no_db):
    assert client.get("/api/pipeline/runs?limit=0").status_code == 422
    assert client.get("/api/pipeline/runs?limit=501").status_code == 422
