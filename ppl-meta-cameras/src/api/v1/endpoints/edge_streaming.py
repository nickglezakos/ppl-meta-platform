"""
Edge camera streaming endpoints.
Handles frame ingestion from edge camera devices (RPi5, dedicated edge devices).
"""

import logging
from typing import Dict
from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.camera import Camera, CameraType, CameraStatus
from src.security.auth import get_current_user, require_start_stream
from src.services.edge_camera_ws_manager import get_ws_manager
from src.services.edge_camera_processor import get_edge_processor

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/edge/{device_id}/ws")
async def edge_camera_websocket(
    websocket: WebSocket,
    device_id: str,
):
    """WebSocket endpoint for edge camera control connection."""
    ws_manager = get_ws_manager()
    
    # Get database session for camera registration
    db = next(get_db())
    
    try:
        # Auto-create camera in database when WebSocket connects
        camera = (
            db.query(Camera)
            .filter(
                Camera.device_id == device_id, 
                Camera.camera_type == CameraType.EDGE
            )
            .first()
        )
        
        if not camera:
            logger.info(f"📡 Edge camera {device_id} not in DB, auto-creating on WebSocket connection...")
            camera = Camera(
                device_id=device_id,
                camera_type=CameraType.EDGE,
                name=f"Edge Camera - {device_id}",
                connection_string=f"edge://{device_id}",
                is_active=True,
                status=CameraStatus.CONNECTED  # WebSocket connected = camera available
            )
            db.add(camera)
            db.commit()
            db.refresh(camera)
            logger.info(f"✅ Auto-created edge camera in database: {device_id}")
        else:
            # Update status to connected
            camera.status = CameraStatus.CONNECTED
            db.commit()
            logger.info(f"✅ Edge camera {device_id} WebSocket connected, status updated")
        
        await ws_manager.connect(device_id, websocket)
        
        try:
            while True:
                # Receive messages from edge camera
                data = await websocket.receive_json()
                await ws_manager.handle_message(device_id, data)
                
        except WebSocketDisconnect:
            # Update status to disconnected
            camera.status = CameraStatus.DISCONNECTED
            db.commit()
            
            await ws_manager.disconnect(device_id)
            logger.info(f"Edge camera {device_id} WebSocket disconnected")
        except Exception as e:
            logger.error(f"WebSocket error for {device_id}: {e}")
            
            # Update status to disconnected
            camera.status = CameraStatus.DISCONNECTED
            db.commit()
            
            await ws_manager.disconnect(device_id)
    finally:
        db.close()


@router.post("/edge/{device_id}/frame")
async def receive_edge_camera_frame(
    device_id: str,
    frame: UploadFile = File(...),
    timestamp: float = Form(...),
    frame_number: int = Form(...),
    encoding: str = Form("mjpeg"),
    db: Session = Depends(get_db),
) -> Dict:
    """
    Receive a video frame from an edge camera.
    
    Note: This endpoint does not require user authentication as it's device-to-device
    communication. The edge camera must be connected via WebSocket (which establishes trust).
    """

    try:
        logger.info(f"📹 [EDGE-FRAME] Received frame #{frame_number} from {device_id} at {timestamp}")

        # Check if edge camera exists in database
        camera = (
            db.query(Camera)
            .filter(
                Camera.device_id == device_id, 
                Camera.camera_type == CameraType.EDGE
            )
            .first()
        )

        # Auto-create camera from discovery service if not exists
        if not camera:
            logger.info(f"Edge camera {device_id} not in DB, auto-creating from first frame...")
            
            # Generate unique camera name
            from src.services.name_validation import generate_unique_camera_name
            camera_name = generate_unique_camera_name(db, f"Edge Camera - {device_id}")
            
            camera = Camera(
                device_id=device_id,
                camera_type=CameraType.EDGE,
                name=camera_name,  # Use generated unique name
                connection_string=f"edge://{device_id}",
                is_active=True,
                status=CameraStatus.AVAILABLE,
                supports_recording=True,
                recording_pipeline_enabled=True,
                instant_detection_enabled=True,
                instant_detection_interval_seconds=5,
                segment_duration_seconds=30
            )
            db.add(camera)
            db.commit()
            db.refresh(camera)
            logger.info(f"✅ Auto-created edge camera: {device_id} with name: {camera_name}")
            
            # Create collection for edge camera
            try:
                import httpx
                from src.security.auth import get_node_service_secret
                
                # Get node service token for API calls
                node_secret = get_node_service_secret()
                headers = {
                    'Authorization': f'Bearer {node_secret}',
                    'Content-Type': 'application/json'
                }
                
                # Create collection via media service using camera name
                collection_data = {
                    "name": camera_name,  # Use same name as camera
                    "description": f"Recordings from {camera_name}",
                    "is_public": False,
                    "camera_device_id": device_id
                }
                
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "http://localhost:8000/api/v1/media/collections",
                        json=collection_data,
                        headers=headers,
                        timeout=10.0
                    )
                    
                    if response.status_code == 200:
                        collection = response.json()
                        logger.info(f"✅ Created collection for edge camera {device_id}: {collection.get('uuid')}")
                    else:
                        logger.warning(f"⚠️ Failed to create collection for edge camera {device_id}: {response.status_code}")
            except Exception as e:
                logger.error(f"❌ Error creating collection for edge camera {device_id}: {e}")

        # Read frame bytes from upload
        try:
            frame_bytes = await frame.read()
        except Exception as e:
            logger.error(f"Failed to read frame data: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid frame data"
            )

        # Process frame through existing pipeline (instant detection, recording, vision, etc.)
        edge_processor = get_edge_processor()
        
        # Build camera info for processor
        camera_info = {
            "device_id": device_id,
            "camera_type": "EDGE",
            "resolution_width": camera.resolution_width if camera else 1280,
            "resolution_height": camera.resolution_height if camera else 720,
            "instant_detection_interval_seconds": 5,  # Default instant detection interval
            "detection_config": {
                "interval_seconds": 5
            }
        }
        
        # Process frame - this integrates edge camera with full pipeline
        # - Instant detection (face detection every 5 seconds)
        # - Video recording (if recording session active)
        # - Vision service integration (demographics, tracking)
        # - Triggers (demographic-based actions)
        success = edge_processor.process_frame(
            device_id=device_id,
            frame_bytes=frame_bytes,
            frame_number=frame_number,  # Pass frame_number for de-duplication
            camera_info=camera_info,
            enable_instant_detection=True  # Enable instant detection by default
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to process frame through pipeline"
            )
        
        logger.debug(f"📹 [EDGE] Frame {frame_number} processed through full pipeline")

        return {
            "status": "success",
            "device_id": device_id,
            "frame_number": frame_number,
            "timestamp": timestamp,
            "message": "Frame received and processed through pipeline"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing edge camera frame: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process frame: {str(e)}"
        )


# Note: Edge cameras register with discovery service (port 8006), not directly here.
# The cameras service discovers edge cameras by querying the discovery service.
# This follows the same pattern as mobile cameras and digital signage devices.


@router.post("/edge/{device_id}/connect")
async def connect_edge_camera(
    device_id: str,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict:
    """Connect to an edge camera (mark as ready for streaming)."""
    
    try:
        ws_manager = get_ws_manager()
        
        # Check if edge camera is connected via WebSocket
        if not ws_manager.is_connected(device_id):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Edge camera {device_id} not connected to platform"
            )
        
        camera = (
            db.query(Camera)
            .filter(
                Camera.device_id == device_id,
                Camera.camera_type == CameraType.EDGE
            )
            .first()
        )
        
        if not camera:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Edge camera {device_id} not found"
            )
        
        # Send connect command via WebSocket
        command_sent = await ws_manager.send_command(device_id, "connect")
        
        if not command_sent:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send connect command to edge camera"
            )
        
        # Mark camera as connected
        camera.status = "connected"
        from datetime import datetime
        camera.last_seen = datetime.utcnow()
        db.commit()
        db.refresh(camera)
        
        logger.info(f"✅ Connected edge camera: {device_id}")
        
        return {
            "status": "connected",
            "device_id": device_id,
            "camera_type": "edge",
            "message": "Edge camera connected successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to connect edge camera: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to connect: {str(e)}"
        )


@router.post("/edge/{device_id}/disconnect")
async def disconnect_edge_camera(
    device_id: str,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict:
    """Disconnect an edge camera."""
    
    try:
        ws_manager = get_ws_manager()
        edge_processor = get_edge_processor()
        
        camera = (
            db.query(Camera)
            .filter(
                Camera.device_id == device_id,
                Camera.camera_type == CameraType.EDGE
            )
            .first()
        )
        
        if not camera:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Edge camera {device_id} not found"
            )
        
        # Send disconnect command via WebSocket if connected
        if ws_manager.is_connected(device_id):
            await ws_manager.send_command(device_id, "disconnect")
        
        # Stop camera worker (stops instant detection, recording, etc.)
        edge_processor.stop_worker(device_id)
        
        # Mark camera as disconnected
        camera.status = "available"
        db.commit()
        
        logger.info(f"Disconnected edge camera: {device_id}")
        
        return {
            "status": "disconnected",
            "device_id": device_id,
            "message": "Edge camera disconnected"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to disconnect edge camera: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to disconnect: {str(e)}"
        )


@router.get("/edge/{device_id}/status")
async def get_edge_camera_status(
    device_id: str,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict:
    """Get status of an edge camera."""
    
    camera = (
        db.query(Camera)
        .filter(Camera.device_id == device_id, Camera.camera_type == CameraType.EDGE)
        .first()
    )
    
    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Edge camera {device_id} not found"
        )
    
    return {
        "device_id": device_id,
        "camera_id": camera.id,
        "name": camera.name,
        "location": camera.location,
        "is_active": camera.is_active,
        "status": "online" if camera.is_active else "offline"
    }


@router.put("/edge/{device_id}/rename")
async def rename_edge_camera(
    device_id: str,
    new_name: str,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict:
    """Rename an edge camera."""
    
    try:
        camera = (
            db.query(Camera)
            .filter(
                Camera.device_id == device_id,
                Camera.camera_type == CameraType.EDGE
            )
            .first()
        )
        
        if not camera:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Edge camera {device_id} not found"
            )
        
        old_name = camera.name
        camera.name = new_name
        db.commit()
        
        logger.info(f"✏️ Renamed edge camera {device_id}: '{old_name}' → '{new_name}'")
        
        return {
            "status": "success",
            "device_id": device_id,
            "old_name": old_name,
            "new_name": new_name,
            "message": "Camera renamed successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to rename edge camera: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to rename camera: {str(e)}"
        )
