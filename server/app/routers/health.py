from fastapi import APIRouter, HTTPException
from app.core.http import SESSION
from app.core.config import settings

router = APIRouter(prefix="", tags=["health"])

@router.get("/health")
def health():
    try:
        r = SESSION.get(f"{settings.OLLAMA_URL}/api/tags", timeout=10)
        ok = r.status_code == 200
        models = [m.get("name") for m in (r.json().get("models", []) if ok else [])]
    
    except Exception:
        ok, models = False, []
    return {"status": "ok" if ok else "degraded", "model": settings.MODEL, "available_models": models}

@router.get("/models")
def models():
    try:
        
        
        r = SESSION.get(f"{settings.OLLAMA_URL}/api/tags", timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Cannot query models: {e}")
