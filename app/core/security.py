from fastapi.security import HTTPBearer
from fastapi import Security, HTTPException
from app.core.config import settings

security = HTTPBearer(auto_error=False)

def require_api_key(credentials = Security(security)):
    if not settings.API_KEY:
        return
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    if credentials.credentials != settings.API_KEY:
        raise HTTPException(status_code=403, detail="Invalid token")
