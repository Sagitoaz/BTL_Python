from fastapi.testclient import TestClient

from app.main import app


def test_complete_ollama_down(monkeypatch):
    from app.services import ollama as ollama_service

    def boom(*a, **k):
        raise RuntimeError("ollama timeout")

    monkeypatch.setattr(ollama_service, "call_generate", boom)

    client = TestClient(app)
    r = client.post("/complete", json={"prefix": "", "suffix": "", "language": "python"})
    assert r.status_code in (500, 502)
