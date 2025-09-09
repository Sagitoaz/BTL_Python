from fastapi import Header, HTTPException
from typing import Optional
from app.core.config import settings

def require_api_key(authorization: Optional[str] = Header(default=None)):
    if not settings.API_KEY:
        return
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    token = authorization.split(" ", 1)[1].strip()
    if token != settings.API_KEY:
        raise HTTPException(status_code=403, detail="Invalid token")
