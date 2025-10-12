from fastapi.testclient import TestClient

from app.main import app


def test_health_ok():
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    # Accept both "ok" and "degraded" status since Ollama may not be running in tests
    assert data.get("status") in {"ok", "healthy", "ready", "degraded"}
