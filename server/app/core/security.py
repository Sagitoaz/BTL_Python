from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

security = HTTPBearer(auto_error=False)


def require_api_key(
    credentials: HTTPAuthorizationCredentials = Security(security),  # noqa: B008
):
    if not settings.API_KEY:
        return
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    if credentials.credentials != settings.API_KEY:
        raise HTTPException(status_code=403, detail="Invalid token")
