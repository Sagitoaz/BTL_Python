import json
import uuid
from fastapi import HTTPException
from app.core.config import settings
from app.core.http import SESSION, TIMEOUT

def build_prompt(prefix: str, suffix: str, language: str) -> str:
    return (
        f"You are a code completion engine. Continue the {language} code.\n"
        "Only output the next few lines of code (no explanations).\n"
        "Make it fit before the trailing context.\n"
        "----\n"
        f"PREFIX:\n{prefix}\n"
        f"SUFFIX:\n{suffix}\n"
        "COMPLETION:\n"
    )

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
