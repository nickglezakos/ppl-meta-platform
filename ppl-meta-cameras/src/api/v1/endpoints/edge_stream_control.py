"""
Edge camera start/stop streaming endpoints.
"""
import logging
from typing import Dict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.camera import Camera, CameraType
from src.security.auth import get_current_user
from src.services.edge_camera_ws_manager import get_ws_manager

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/edge/{device_id}/start-stream")
async def start_edge_camera_stream(
    device_id: str,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict:
    """Start streaming from an edge camera."""
    
    try:
        ws_manager = get_ws_manager()
        
        # Check if edge camera is connected via WebSocket
        if not ws_manager.is_connected(device_id):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Edge camera {device_id} not connected to platform"
            )
        
        # Send start-stream command via WebSocket
        command_sent = await ws_manager.send_command(device_id, "start-stream")
        
        if not command_sent:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send start-stream command to edge camera"
            )
        
        logger.info(f"✅ Start-stream command sent to edge camera: {device_id}")
        
        return {
            "status": "streaming",
            "device_id": device_id,
            "message": "Streaming started successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start edge camera stream: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start stream: {str(e)}"
        )


@router.post("/edge/{device_id}/stop-stream")
async def stop_edge_camera_stream(
    device_id: str,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict:
    """Stop streaming from an edge camera."""
    
    try:
        ws_manager = get_ws_manager()
        
        # Check if edge camera is connected via WebSocket
        if not ws_manager.is_connected(device_id):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Edge camera {device_id} not connected to platform"
            )
        
        # Send stop-stream command via WebSocket
        command_sent = await ws_manager.send_command(device_id, "stop-stream")
        
        if not command_sent:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send stop-stream command to edge camera"
            )
        
        logger.info(f"⏹️ Stop-stream command sent to edge camera: {device_id}")
        
        return {
            "status": "stopped",
            "device_id": device_id,
            "message": "Streaming stopped successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to stop edge camera stream: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop stream: {str(e)}"
        )
