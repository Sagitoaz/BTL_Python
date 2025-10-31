from fastapi import APIRouter, HTTPException
import requests

from app.core.config import settings

router = APIRouter(prefix="", tags=["health"])


@router.get("/health")
def health():
    """
    Health check - verifies Groq API connectivity.
    """
    ok = True
    models = []
    
    if settings.GROQ_API_KEY:
        try:
            # Test Groq API connection
            resp = requests.get(
                "https://api.groq.com/openai/v1/models",
                headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
                timeout=5
            )
            if resp.ok:
                data = resp.json()
                models = [m.get("id") for m in data.get("data", [])]
            else:
                ok = False
        except Exception:
            ok = False
    else:
        ok = False
    
    return {
        "status": "ok" if ok else "degraded",
        "model": settings.GROQ_MODEL,
        "available_models": models,
    }


@router.get("/models")
def models():
    """
    List available Groq models.
    """
    if not settings.GROQ_API_KEY:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY not configured")
    
    try:
        resp = requests.get(
            "https://api.groq.com/openai/v1/models",
            headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
            timeout=5
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Cannot query Groq models: {e}") from e
