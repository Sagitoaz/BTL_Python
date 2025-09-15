import re
import json
from collections import Counter
import uuid
from fastapi import HTTPException
from app.core.config import settings
from app.core.http import SESSION, TIMEOUT
from app.schemas.completion import CompleteRequest

def build_prompt(seq:CompleteRequest ) -> str:
    

    rules = [
        "Return ONLY the missing Python code.",
        "Never output backticks or any Markdown.",
        "Do not add explanations, comments, or docstrings unless strictly required for correctness.",
        "Respect indentation from the last line before the cursor.",
        "Do not repeat any code that already exists in the prefix or suffix.",
        "Prefer the shortest syntactically valid completion; close any open blocks/brackets.",
        "Stop at a natural boundary (end of statement/block).",
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

# Ollama caller

def call_generate(prompt: str, max_tokens: int, temperature: float, stop, stream: bool):
    body = {
        "model": settings.MODEL,
        "prompt": prompt,
        "stream": stream,
        "options": {
            "temperature": temperature,
            "num_ctx": 2048,
            "num_predict": max_tokens,
            "repeat_penalty": 1.1,
            "stop": stop,
        },
    }
    # Nếu settings.OLLAMA_URL là base (vd http://127.0.0.1:11434) thì
    # cân nhắc đổi thành ... + "/api/generate". Nếu đã là endpoint đầy đủ thì giữ nguyên.
    url = f"{settings.OLLAMA_URL}/api/generate"
    resp = SESSION.post(url, json=body, timeout=TIMEOUT, stream=stream)
    if resp.status_code >= 400:
        try:
            detail = resp.json()
        except Exception:
            detail = resp.text
        raise HTTPException(status_code=502, detail={"ollama_error": detail})
    return resp

def new_request_id() -> str:
    return str(uuid.uuid4())[:8]
