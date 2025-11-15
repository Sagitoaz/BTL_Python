"""
Admin endpoints for telemetry management.
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
import os

from app.core.security import require_api_key
from app.middleware.telemetry import get_telemetry_collector
from app.services.user_profiling import get_profiler

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/telemetry/stats", dependencies=[Depends(require_api_key)])
def get_telemetry_stats():
    """Get telemetry statistics"""
    collector = get_telemetry_collector()
    return collector.get_stats()


@router.post("/telemetry/export", dependencies=[Depends(require_api_key)])
def export_telemetry(format: str = "jsonl"):
    """
    Export telemetry data for training.
    
    Args:
        format: Export format ("jsonl" or "csv")
    """
    if format not in ("jsonl", "csv"):
        raise HTTPException(status_code=400, detail="Format must be 'jsonl' or 'csv'")
    
    collector = get_telemetry_collector()
    output_file = f"data/exports/training_data.{format}"
    
    # Create exports directory
    os.makedirs("data/exports", exist_ok=True)
    
    count = collector.export_training_data(output_file, format=format)
    
    return {
        "status": "success",
        "records_exported": count,
        "file": output_file
    }


@router.get("/telemetry/download/{filename}", dependencies=[Depends(require_api_key)])
def download_telemetry_file(filename: str):
    """Download exported telemetry file"""
    file_path = f"data/exports/{filename}"
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        file_path,
        media_type="application/octet-stream",
        filename=filename
    )


@router.get("/profiles/list", dependencies=[Depends(require_api_key)])
def list_user_profiles():
    """List all user profiles"""
    profiler = get_profiler()
    profiles = []
    
    if profiler.data_dir.exists():
        for profile_file in profiler.data_dir.glob("*.json"):
            user_id = profile_file.stem
            profile = profiler.load_profile(user_id)
            profiles.append({
                "user_id": user_id,
                "total_samples": profile.coding_style.total_samples,
                "accept_rate": profile.accept_rate,
                "last_updated": profile.updated_at
            })
    
    return {
        "total_users": len(profiles),
        "profiles": profiles
    }


@router.get("/profiles/{user_id}", dependencies=[Depends(require_api_key)])
def get_user_profile(user_id: str):
    """Get detailed profile for a specific user"""
    profiler = get_profiler()
    profile = profiler.load_profile(user_id)
    
    return profile.model_dump()


@router.get("/profiles/{user_id}/style-hints", dependencies=[Depends(require_api_key)])
def get_user_style_hints(user_id: str):
    """Get style hints that would be sent to LLM for this user"""
    profiler = get_profiler()
    hints = profiler.get_style_hints(user_id)
    
    return {
        "user_id": user_id,
        "style_hints": hints
    }
