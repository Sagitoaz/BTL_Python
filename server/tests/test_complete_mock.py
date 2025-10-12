from fastapi.testclient import TestClient

from app.main import app


def test_complete_mock(monkeypatch):
    # Mock call_generate trong chính router module
    from app.routers import completions
    
    class FakeResponse:
        def json(self):
            return {"response": "def two_sum(nums, target):\n    return []\n"}

    def fake_call_generate(prompt, max_tokens, temperature, stops, stream=False):
        return FakeResponse()

    # Patch cả hai nơi có thể import
    monkeypatch.setattr("app.routers.completions.call_generate", fake_call_generate)
    monkeypatch.setattr("app.services.ollama.call_generate", fake_call_generate)

    client = TestClient(app)
    payload = {"prefix": "def two_sum(", "suffix": ")", "language": "python"}
    r = client.post("/complete", json=payload)
    
    assert r.status_code == 200
    data = r.json()
    assert "completion" in data
    # Postprocessing có thể cắt bỏ phần đầu, chỉ cần check có content
    assert len(data["completion"]) > 0
