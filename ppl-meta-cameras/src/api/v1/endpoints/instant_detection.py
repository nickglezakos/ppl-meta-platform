"""
Instant Detection API Endpoints

Provides REST API endpoints for instant temporal face detection.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Optional
import logging
import time

from src.services.instant_detection import InstantDetectionSampler
from src.database import get_db
from src.models.camera import Camera
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter(tags=["instant-detection"])

# Global instant detection manager (singleton)
_instant_detection_manager: Optional[InstantDetectionSampler] = None


def get_instant_detection_manager() -> InstantDetectionSampler:
    """Get or create instant detection manager singleton"""
    global _instant_detection_manager
    
    if _instant_detection_manager is None:
        _instant_detection_manager = InstantDetectionSampler(
            vision_service_url="http://localhost:8003",
            sampling_interval=5,
            temporal_window=1.0
        )
        logger.info("✅ Instant detection manager initialized")
    
    return _instant_detection_manager


@router.get("/status")
async def get_status(
    manager: InstantDetectionSampler = Depends(get_instant_detection_manager)
) -> Dict:
    """
    Get status of instant detection system
    
    Returns:
        Status information including running state, cached results count
    """
    return {
        "success": True,
        "status": manager.get_status()
    }


@router.get("/results/{camera_id}")
async def get_instant_results(
    camera_id: str,
    manager: InstantDetectionSampler = Depends(get_instant_detection_manager)
) -> Dict:
    """
    Get latest instant detection results for a camera.
    
    Results are kept in memory until replaced by next iteration.
    This allows other hooks to access instant results while recording is active.
    
    Args:
        camera_id: Camera device ID
        
    Returns:
        Latest detection results or 404 if no results available
    """
    cached_data = manager.results_cache.get(camera_id)
    
    if cached_data is None:
        raise HTTPException(
            status_code=404,
            detail=f"No instant detection results for camera {camera_id}. Start instant detection first."
        )
    
    # Include metadata about when result was cached
    result = cached_data["result"].copy()
    result["_metadata"] = {
        "cached_at": cached_data["cached_at"],
        "iteration": cached_data["iteration"],
        "age_seconds": time.time() - cached_data["cached_at"]
    }
    
    return result


@router.get("/results")
async def get_all_instant_results(
    manager: InstantDetectionSampler = Depends(get_instant_detection_manager)
) -> Dict:
    """
    Get latest instant detection results for ALL cameras.
    
    Useful for dashboards or monitoring multiple cameras.
    
    Returns:
        Dict mapping camera_id to latest results
    """
    all_results = {}
    
    for camera_id, cached_data in manager.results_cache.items():
        result = cached_data["result"].copy()
        result["_metadata"] = {
            "cached_at": cached_data["cached_at"],
            "iteration": cached_data["iteration"],
            "age_seconds": time.time() - cached_data["cached_at"]
        }
        all_results[camera_id] = result
    
    return {
        "success": True,
        "total_cameras": len(all_results),
        "results": all_results
    }


@router.post("/start/{camera_id}")
async def start_instant_detection(
    camera_id: str,
    db: Session = Depends(get_db),
    manager: InstantDetectionSampler = Depends(get_instant_detection_manager)
) -> Dict:
    """
    Start instant detection for a camera
    
    Args:
        camera_id: Camera device ID
        
    Returns:
        Success status
    """
    # Verify camera exists
    camera = db.query(Camera).filter(Camera.device_id == camera_id).first()
    
    if not camera:
        raise HTTPException(
            status_code=404,
            detail=f"Camera {camera_id} not found"
        )
    
    # Get camera path
    camera_path = camera.connection_string or f"/dev/video{camera.device_index or 0}"
    
    try:
        manager.start_sampling(camera_id, camera_path)
        
        return {
            "success": True,
            "message": f"Instant detection started for camera {camera_id}",
            "camera_id": camera_id,
            "sampling_interval": manager.sampling_interval,
            "temporal_window": manager.temporal_window
        }
        
    except Exception as e:
        logger.error(f"Failed to start instant detection: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start instant detection: {str(e)}"
        )


@router.post("/stop")
async def stop_instant_detection(
    manager: InstantDetectionSampler = Depends(get_instant_detection_manager)
) -> Dict:
    """
    Stop instant detection sampling
    
    Returns:
        Success status
    """
    try:
        manager.stop_sampling()
        
        return {
            "success": True,
            "message": "Instant detection stopped"
        }
        
    except Exception as e:
        logger.error(f"Failed to stop instant detection: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to stop instant detection: {str(e)}"
        )
