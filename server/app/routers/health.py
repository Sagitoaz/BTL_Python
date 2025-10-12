from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.core.http import SESSION

router = APIRouter(prefix="", tags=["health"])


@router.get("/health")
def health():
    ok = True
    models = []
    try:
        r = SESSION.get(f"{settings.OLLAMA_URL.rstrip('/')}/api/tags", timeout=2)
        if r.ok:
            data = r.json()
            models = [m.get("name") for m in data.get("models", [])]
        else:
            ok = False
    except Exception:
        ok, models = False, []
    return {
        "status": "ok" if ok else "degraded",
        "model": settings.MODEL,
        "available_models": models,
    }


@router.get("/models")
def models():
    try:
        r = SESSION.get(f"{settings.OLLAMA_URL.rstrip('/')}/api/tags", timeout=3)
        return r.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Cannot query models: {e}") from e
