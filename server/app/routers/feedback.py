"""
User feedback endpoints for personalization.
Track accept/reject to improve future suggestions.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel

from app.core.security import require_api_key
from app.services.user_profiling import get_profiler

router = APIRouter(prefix="/feedback", tags=["feedback"])
logger = logging.getLogger("feedback")


class CompletionFeedback(BaseModel):
    """Feedback on a completion"""
    request_id: str
    accepted: bool
    completion_text: str = ""
    prefix: str = ""
    accept_time_ms: float = 0.0


@router.post("/completion", dependencies=[Depends(require_api_key)])
def record_completion_feedback(
    feedback: CompletionFeedback,
    x_user_id: Optional[str] = Header(None, description="User identifier")
):
    """
    Record user feedback on a completion (accepted or rejected).
    This helps personalize future suggestions.
    """
    if not x_user_id:
        raise HTTPException(
            status_code=400,
            detail="X-User-ID header required for feedback"
        )
    
    try:
        profiler = get_profiler()
        profile = profiler.update_profile_from_completion(
            user_id=x_user_id,
            prefix=feedback.prefix,
            completion=feedback.completion_text,
            accepted=feedback.accepted,
            accept_time_ms=feedback.accept_time_ms
        )
        
        return {
            "status": "ok",
            "user_id": x_user_id,
            "total_samples": profile.coding_style.total_samples,
            "accept_rate": profile.accept_rate
        }
    except Exception as e:
        logger.error(f"Failed to record feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/profile", dependencies=[Depends(require_api_key)])
def get_user_profile(
    x_user_id: Optional[str] = Header(None, description="User identifier")
):
    """Get user's coding profile and personalization data"""
    if not x_user_id:
        raise HTTPException(
            status_code=400,
            detail="X-User-ID header required"
        )
    
    try:
        profiler = get_profiler()
        profile = profiler.load_profile(x_user_id)
        
        return {
            "user_id": profile.user_id,
            "coding_style": profile.coding_style.model_dump(),
            "accept_rate": profile.accept_rate,
            "avg_accept_time_ms": profile.avg_accept_time_ms,
            "preferred_completion_length": profile.preferred_completion_length,
            "total_samples": profile.coding_style.total_samples,
            "created_at": profile.created_at,
            "updated_at": profile.updated_at
        }
    except Exception as e:
        logger.error(f"Failed to get profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/profile", dependencies=[Depends(require_api_key)])
def delete_user_profile(
    x_user_id: Optional[str] = Header(None, description="User identifier")
):
    """Delete user's profile and all personalization data"""
    if not x_user_id:
        raise HTTPException(
            status_code=400,
            detail="X-User-ID header required"
        )
    
    try:
        profiler = get_profiler()
        profile_path = profiler.get_profile_path(x_user_id)
        
        if profile_path.exists():
            profile_path.unlink()
            return {"status": "deleted", "user_id": x_user_id}
        else:
            return {"status": "not_found", "user_id": x_user_id}
    except Exception as e:
        logger.error(f"Failed to delete profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))
