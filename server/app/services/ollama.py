import uuid

from fastapi import HTTPException

from app.core.config import settings
from app.core.http import SESSION, TIMEOUT
from app.schemas.completion import CompleteRequest


def build_prompt(seq: CompleteRequest) -> str:
    rules = [
        f"Return ONLY the missing {seq.language} code.",
        "Never output backticks or any Markdown.",
        (
            "Do not add explanations, comments, or docstrings "
            "unless strictly required for correctness."
        ),
        "Respect indentation from the last line before the cursor.",
        "Do not repeat any code that already exists in the prefix or suffix.",
    ]
    return (
        f"You are a {seq.language} code completion engine.\n"
        "Follow ALL rules strictly.\n"
        "Rules:\n- " + "\n- ".join(rules) + "\n"
        "Complete at the cursor using the surrounding context.\n"
        "---\n"
        f"<prefix>\n{seq.prefix}\n</prefix>\n"
        f"<suffix>\n{seq.suffix}\n</suffix>\n"
        "<cursor/>\n"
    )


def call_generate(prompt: str, max_tokens: int, temperature: float, stop, stream: bool):
    body = {
        "model": settings.MODEL,
        "prompt": prompt,
        "stream": stream,
        "options": {
            "temperature": float(temperature),
            "num_ctx": getattr(settings, "NUM_CTX", 2048),
            "num_predict": int(max_tokens),
            "repeat_penalty": 1.1,
            "stop": stop,
        },
    }
    url = f"{settings.OLLAMA_URL.rstrip('/')}/api/generate"
    resp = SESSION.post(url, json=body, timeout=TIMEOUT, stream=stream)
    if resp.status_code >= 400:
        try:
            detail = resp.json()
        except Exception:
            detail = resp.text
        raise HTTPException(status_code=502, detail={"ollama_error": detail})
    return resp

# --- Public shim expected by tests ---
def generate_completion(*args, **kwargs) -> str:
    """
    Public entry expected by tests. If you already have an internal function that
    does the actual work (e.g., _generate_completion or complete_once), delegate to it.
    Otherwise this will raise until wired up — tests will monkeypatch it anyway.
    """
    try:
        # Nếu bạn đã có hàm thật, đổi tên ở đây cho đúng:
        return _generate_completion(*args, **kwargs)  # type: ignore[name-defined]
    except NameError:
        raise RuntimeError("generate_completion is not wired to an internal impl yet")


def new_request_id() -> str:
    return str(uuid.uuid4())[:8]
