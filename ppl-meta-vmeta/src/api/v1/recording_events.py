"""
Recording Event API Endpoints for vmeta Service
Receives recording lifecycle events from Camera Service to control polling.
"""

import logging
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/recording", tags=["recording-events"])

# Global reference to polling manager (set in main.py)
polling_manager = None


class RecordingStartEvent(BaseModel):
    """Recording start event from Camera Service."""
    collection_id: str = Field(..., description="Camera collection ID")
    session_uuid: str = Field(..., description="Recording session UUID")
    device_id: str = Field(..., description="Camera device ID")
    user_id: str = Field(..., description="User ID")
    timestamp: str = Field(..., description="ISO timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class RecordingStopEvent(BaseModel):
    """Recording stop event from Camera Service."""
    collection_id: str = Field(..., description="Camera collection ID")
    session_uuid: str = Field(..., description="Recording session UUID")
    device_id: str = Field(..., description="Camera device ID")
    user_id: str = Field(..., description="User ID")
    timestamp: str = Field(..., description="ISO timestamp")
    video_count: int = Field(default=0, description="Total videos in session")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


@router.post("/started")
async def handle_recording_started(event: RecordingStartEvent) -> Dict[str, Any]:
    """
    Handle recording started event from Camera Service.
    Activates polling for the specific collection.
    """
    logger.info(
        f"📹 Recording started: collection={event.collection_id}, "
        f"session={event.session_uuid}, device={event.device_id}"
    )
    
    if polling_manager is None:
        logger.error("Polling manager not initialized")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Polling manager not available"
        )
    
    try:
        # Start polling for this collection
        await polling_manager.start_recording(
            collection_id=event.collection_id,
            session_uuid=event.session_uuid
        )
        
        logger.info(
            f"✅ Polling activated for collection {event.collection_id}, "
            f"session {event.session_uuid}"
        )
        
        return {
            "status": "success",
            "message": f"Polling activated for collection {event.collection_id}",
            "collection_id": event.collection_id,
            "session_uuid": event.session_uuid,
            "polling_active": True
        }
        
    except Exception as e:
        logger.error(f"Failed to handle recording start event: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start polling: {str(e)}"
        )


@router.post("/stopped")
async def handle_recording_stopped(event: RecordingStopEvent) -> Dict[str, Any]:
    """
    Handle recording stopped event from Camera Service.
    Triggers final batch processing and stops polling for the collection.
    """
    logger.info(
        f"🛑 Recording stopped: collection={event.collection_id}, "
        f"session={event.session_uuid}, device={event.device_id}, videos={event.video_count}"
    )
    
    if polling_manager is None:
        logger.error("Polling manager not initialized")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Polling manager not available"
        )
    
    try:
        # Stop polling and process remaining videos
        result = await polling_manager.stop_recording(
            collection_id=event.collection_id,
            session_uuid=event.session_uuid
        )
        
        logger.info(
            f"✅ Recording stopped for collection {event.collection_id}, "
            f"session {event.session_uuid}. Processed {result.get('videos_processed', 0)} remaining videos"
        )
        
        return {
            "status": "success",
            "message": f"Recording stopped and final batch triggered for {event.collection_id}",
            "collection_id": event.collection_id,
            "session_uuid": event.session_uuid,
            "polling_active": False,
            **result
        }
        
    except Exception as e:
        logger.error(f"Failed to handle recording stop event: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop recording: {str(e)}"
        )


@router.get("/status")
async def get_polling_status() -> Dict[str, Any]:
    """Get current polling status for all active recordings."""
    
    if polling_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Polling manager not available"
        )
    
    try:
        status_data = polling_manager.get_status()
        return {
            "status": "success",
            "polling_manager": status_data
        }
    except Exception as e:
        logger.error(f"Failed to get polling status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get status: {str(e)}"
        )


@router.post("/test-trigger")
async def test_trigger_batch() -> Dict[str, Any]:
    """
    Test endpoint to manually trigger batch processing.
    Useful for debugging and testing.
    """
    if polling_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Polling manager not available"
        )
    
    try:
        result = await polling_manager.manual_trigger()
        return {
            "status": "success",
            "message": "Manual batch trigger executed",
            **result
        }
    except Exception as e:
        logger.error(f"Manual trigger failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Manual trigger failed: {str(e)}"
        )
