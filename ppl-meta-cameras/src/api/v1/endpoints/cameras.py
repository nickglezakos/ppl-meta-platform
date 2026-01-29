"""
Camera management endpoints for PPL Meta Cameras API.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Request,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from pydantic import BaseModel
from sqlalchemy.orm import Session
from src.database import get_db
from src.models.camera import Camera, CameraStatus, CameraType
from src.security.auth import (
    get_current_user,
    require_admin_cameras,
    require_connect_camera,
    require_detect_cameras,
    require_view_cameras,
)
from src.services.camera_service_queue import get_camera_service
from src.services.session_auth import session_manager
from src.services.session_aware_face_detector import session_aware_face_detector
from src.services.session_statistics_broadcaster import statistics_broadcaster
from src.services.streaming_session_manager import streaming_session_manager

logger = logging.getLogger(__name__)
router = APIRouter()


class RTSPCameraCreate(BaseModel):
    """Model for RTSP camera creation/update"""

    name: str
    host: str
    port: int = 554
    path: str = "/stream"
    username: Optional[str] = None
    password: Optional[str] = None


class MobileCameraCreate(BaseModel):
    """Model for mobile camera registration"""

    name: str
    device_id: str
    ip_address: Optional[str] = None  # Will be auto-detected from client IP
    port: int = 8554
    device_model: Optional[str] = None
    device_manufacturer: Optional[str] = None
    app_version: Optional[str] = None
    resolution_width: int = 1920
    resolution_height: int = 1080
    max_fps: int = 30
    supports_audio: bool = False


class MobileCameraUpdate(BaseModel):
    """Model for mobile camera status updates"""

    status: Optional[CameraStatus] = None
    resolution_width: Optional[int] = None
    resolution_height: Optional[int] = None
    current_fps: Optional[int] = None
    battery_level: Optional[int] = None
    ip_address: Optional[str] = None
    port: Optional[int] = None


@router.get("/", dependencies=[Depends(require_view_cameras)])
async def list_cameras(
    db: Session = Depends(get_db), current_user: Dict = Depends(get_current_user)
) -> List[Dict]:
    """List all cameras in the database."""

    try:
        cameras = db.query(Camera).all()
        
        # Get real-time worker status
        queue_service = get_camera_service()

        camera_list = []
        for camera in cameras:
            # For mobile cameras, use database status (they don't have workers)
            # For USB/RTSP cameras, check real-time worker status
            if camera.camera_type == CameraType.MOBILE:
                # Mobile cameras don't use workers - check database status
                realtime_status = camera.status.value
            else:
                # Check if camera has an active worker
                worker = await queue_service.get_camera_stream(camera.device_id)
                realtime_status = worker.status.value if worker else "disconnected"
            
            camera_dict = {
                "id": camera.id,
                "name": camera.name,
                "device_id": camera.device_id,
                "camera_type": camera.camera_type.value,
                "status": realtime_status,  # Use appropriate status based on camera type
                "resolution": f"{camera.resolution_width}x{camera.resolution_height}",
                "max_fps": camera.max_fps,
                "supports_streaming": camera.supports_streaming,
                "supports_recording": camera.supports_recording,
                "connection_string": camera.connection_string,  # Include for mobile cameras
                "last_seen": camera.last_seen.isoformat() if camera.last_seen else None,
                "created_at": (
                    camera.created_at.isoformat() if camera.created_at else None
                ),
            }
            camera_list.append(camera_dict)

        logger.info(f"User {current_user.get('sub')} listed {len(camera_list)} cameras")
        return camera_list

    except Exception as e:
        logger.error(f"Error listing cameras: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve cameras",
        )


@router.get("/{device_id}/realtime-status", dependencies=[Depends(require_view_cameras)])
async def get_camera_realtime_status(
    device_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """
    Get REAL-TIME camera status from memory (NO database query).
    
    Returns instant state including:
    - Connection status
    - Frame availability
    - Frame count and age
    - Error status
    
    This endpoint is FAST and used by streaming to check if frames are available.
    """
    try:
        from src.services.camera_pool_manager import camera_pool_manager
        from src.config import get_config
        
        config = get_config()
        
        if config.USE_CAMERA_POOL_MANAGER:
            # Get state from pool manager (instant, no DB)
            state = camera_pool_manager.get_camera_state(device_id)
            return {
                "device_id": device_id,
                "realtime": True,
                "source": "camera_pool_manager",
                **state
            }
        else:
            # Check queue-based worker status
            queue_service = get_camera_service()
            worker = await queue_service.get_camera_stream(device_id)
            
            is_connected = worker is not None and worker.status.value == "connected"
            has_frames = worker is not None and worker.has_frames()
            
            return {
                "device_id": device_id,
                "realtime": True,
                "source": "queue_worker",
                "status": worker.status.value if worker else "disconnected",
                "has_frames": has_frames,
                "is_reading": is_connected
            }
    
    except Exception as e:
        logger.error(f"Error getting realtime status for {device_id}: {e}")
        return {
            "device_id": device_id,
            "realtime": True,
            "status": "error",
            "error": str(e)
        }


@router.post("/detect", dependencies=[Depends(require_detect_cameras)])
async def detect_cameras(
    save_to_db: bool = True,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user),
) -> Dict:
    """Detect available cameras and optionally save to database."""

    try:
        # ✅ Use queue-based camera service for detection
        queue_service = get_camera_service()
        detected_cameras = await queue_service.detect_available_cameras()

        result = {
            "detected_count": len(detected_cameras),
            "cameras": detected_cameras,
            "saved_to_db": False,
        }

        if save_to_db:
            # Save detected cameras to database
            saved_count = 0
            for cam_info in detected_cameras:
                device_id = cam_info.get('device_id')
                camera_type_str = cam_info.get('camera_type', 'USB')
                camera_type = CameraType[camera_type_str] if camera_type_str in CameraType.__members__ else CameraType.USB
                
                existing = db.query(Camera).filter(Camera.device_id == device_id).first()
                if not existing:
                    new_camera = Camera(
                        device_id=device_id,
                        camera_type=camera_type,
                        name=cam_info.get('name', device_id),
                        location=cam_info.get('location', ''),
                        status=CameraStatus.DISCONNECTED,
                    )
                    db.add(new_camera)
                    saved_count += 1
            
            db.commit()
            result["saved_to_db"] = True
            result["saved_count"] = saved_count

        logger.info(
            f"User {current_user.get('sub')} detected {len(detected_cameras)} cameras"
        )
        return result

    except Exception as e:
        logger.error(f"Error detecting cameras: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to detect cameras",
        )


@router.post("/{device_id}/connect", dependencies=[Depends(require_connect_camera)])
async def connect_camera(
    device_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user),
) -> Dict:
    """Connect to a specific camera."""

    try:
        # Clean up stale recording sessions for this camera before connecting
        from src.services.recording_session_service import RecordingSessionService
        session_service = RecordingSessionService(db)
        cleaned = session_service.cleanup_stale_sessions(max_age_hours=1)
        if cleaned > 0:
            logger.info(f"Cleaned up {cleaned} stale recording sessions before connecting {device_id}")

        # Check if camera exists in database
        camera = db.query(Camera).filter(Camera.device_id == device_id).first()
        if not camera:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Camera {device_id} not found",
            )

        # Handle mobile cameras differently - they don't need backend connection setup
        if camera.camera_type == CameraType.MOBILE:
            # For mobile cameras, "connecting" means marking them as available for streaming
            # The actual streaming connection is handled directly between frontend and mobile app
            camera.status = CameraStatus.CONNECTED
            camera.last_seen = datetime.utcnow()
            
            # ✅ COMMIT STATUS TO DATABASE for mobile cameras so frontend can see the update
            db.commit()
            db.refresh(camera)

            logger.info(
                f"User {current_user.get('sub')} manually connected mobile camera {device_id}"
            )

            return {
                "message": f"Mobile camera {device_id} marked as connected",
                "device_id": device_id,
                "status": "connected",
                "camera_type": "mobile",
                "connection_string": camera.connection_string,
                "last_seen": camera.last_seen.isoformat() if camera.last_seen else None,
            }

        # Connect to USB/other camera types
        # ✅ For RTSP cameras, connection can take 15+ seconds
        # Use background task to avoid gateway timeout
        if camera.camera_type == CameraType.RTSP:
            # Return immediately, connect in background
            async def connect_rtsp():
                # ✅ Use queue-based camera service for RTSP connection
                queue_service = get_camera_service()
                connection_success = await queue_service.connect_camera(device_id)
                if connection_success:
                    # ✅ NO DATABASE UPDATE - state managed in memory
                    camera.status = CameraStatus.CONNECTED
                    logger.info(f"✅ Background connection successful for RTSP camera {device_id}")
                else:
                    logger.error(f"❌ Background connection failed for RTSP camera {device_id}")
            
            background_tasks.add_task(connect_rtsp)
            
            logger.info(f"User {current_user.get('sub')} initiated connection to RTSP camera {device_id} (background)")
            
            return {
                "device_id": device_id,
                "status": "connecting",
                "message": f"RTSP camera {device_id} connection initiated (this may take 10-15 seconds)",
            }
        else:
            # USB cameras connect quickly, can wait
            # ✅ Use queue-based camera service for connection
            queue_service = get_camera_service()
            connection_success = await queue_service.connect_camera(device_id)
            if not connection_success:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to connect to camera {device_id}",
                )

            # ✅ NO DATABASE UPDATE - state managed in memory
            camera.status = CameraStatus.CONNECTED

            logger.info(f"User {current_user.get('sub')} connected to camera {device_id}")

            return {
                "device_id": device_id,
                "status": "connected",
                "message": f"Successfully connected to camera {device_id}",
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error connecting to camera {device_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to connect to camera",
        )


@router.post("/{device_id}/disconnect", dependencies=[Depends(require_connect_camera)])
async def disconnect_camera(
    device_id: str,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user),
) -> Dict:
    """Disconnect from a specific camera."""

    try:
        # Clean up any active streaming sessions for this device
        cleaned_sessions = session_manager.cleanup_sessions_for_device(device_id)

        # Disconnect from camera using queue service (if currently connected)
        queue_service = get_camera_service()
        success = await queue_service.disconnect_camera(device_id)

        # Update camera status in database regardless of current connection state
        # This fixes state inconsistencies where DB shows "connected" but no active connection exists
        camera = db.query(Camera).filter(Camera.device_id == device_id).first()
        if camera:
            if camera.status == CameraStatus.CONNECTED:
                camera.status = CameraStatus.AVAILABLE
                db.commit()
                logger.info(
                    "Updated camera %s status from connected to available (was in inconsistent state: %s)",
                    device_id,
                    "active connection" if success else "no active connection",
                )
            elif not success:
                # Camera was already available, but user tried to disconnect
                logger.warning(
                    "User %s attempted to disconnect camera %s which was already available",
                    current_user.get("sub"),
                    device_id,
                )
        elif not success:
            # Camera not found in database and not connected
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Camera {device_id} not found",
            )

        logger.info(
            "User %s disconnected from camera %s, cleaned %d sessions, connection_was_active=%s",
            current_user.get("sub"),
            device_id,
            cleaned_sessions,
            success,
        )

        return {
            "device_id": device_id,
            "status": "disconnected",
            "message": f"Successfully disconnected from camera {device_id}",
            "sessions_cleaned": cleaned_sessions,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error disconnecting from camera %s: %s", device_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to disconnect from camera",
        ) from e


@router.get("/{device_id}/info", dependencies=[Depends(require_view_cameras)])
async def get_camera_info(
    device_id: str,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user),
) -> Dict:
    """Get detailed information about a specific camera."""

    try:
        # Get camera from database
        camera = db.query(Camera).filter(Camera.device_id == device_id).first()
        if not camera:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Camera {device_id} not found",
            )

        # Get runtime info from service
        # Get runtime information from queue worker
        queue_service = get_camera_service()
        worker = await queue_service.get_camera_stream(device_id)
        runtime_info = {
            'is_connected': worker is not None and worker.status.value == 'connected',
            'frames_read': worker.frames_read if worker else 0,
            'last_frame_time': worker.last_frame_time if worker else None,
        } if worker else {}

        camera_info = {
            "id": camera.id,
            "name": camera.name,
            "device_id": camera.device_id,
            "camera_type": camera.camera_type.value,
            "status": camera.status.value,
            "resolution": {
                "width": camera.resolution_width,
                "height": camera.resolution_height,
            },
            "max_fps": camera.max_fps,
            "connection_string": camera.connection_string,
            "capabilities": {
                "supports_streaming": camera.supports_streaming,
                "supports_recording": camera.supports_recording,
                "supports_audio": camera.supports_audio,
                "supports_ptz": camera.supports_ptz,
            },
            "hardware": {
                "manufacturer": camera.manufacturer,
                "model": camera.model,
                "serial_number": camera.serial_number,
                "firmware_version": camera.firmware_version,
            },
            "timestamps": {
                "last_seen": camera.last_seen.isoformat() if camera.last_seen else None,
                "created_at": (
                    camera.created_at.isoformat() if camera.created_at else None
                ),
                "updated_at": (
                    camera.updated_at.isoformat() if camera.updated_at else None
                ),
            },
            "runtime_info": runtime_info,
        }

        return camera_info

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting camera info for {device_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get camera information",
        )


@router.get("/active", dependencies=[Depends(require_view_cameras)])
async def list_active_connections(
    current_user: Dict = Depends(get_current_user),
) -> Dict:
    """List all active camera connections."""

    try:
        # Get connected workers from queue service
        from src.services.worker_manager import get_worker_manager
        manager = get_worker_manager()
        connected_workers = manager.get_connected_workers()
        
        active_connections = []
        for device_id, worker in connected_workers.items():
            stats = worker.get_stats()
            active_connections.append({
                "device_id": device_id,
                "status": worker.status.value,
                "frames_read": stats["frames_read"],
                "uptime": stats.get("uptime_seconds", 0)
            })

        logger.info(
            f"User {current_user.get('sub')} listed {len(active_connections)} active connections"
        )

        return {
            "active_count": len(active_connections),
            "active_cameras": active_connections,
        }

    except Exception as e:
        logger.error(f"Error listing active connections: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list active connections",
        )


@router.post("/disconnect-all", dependencies=[Depends(require_admin_cameras)])
async def disconnect_all_cameras(
    current_user: Dict = Depends(get_current_user),
) -> Dict:
    """Disconnect all active camera connections (admin only)."""

    try:
        logger.info(f"🔌 User {current_user.get('sub')} requesting disconnect-all")
        
        # Clean up all active streaming sessions
        cleaned_sessions = session_manager.cleanup_all_sessions()
        logger.info(f"Cleaned {cleaned_sessions} streaming sessions")

        # Disconnect all cameras using queue service
        queue_service = get_camera_service()
        from src.services.worker_manager import get_worker_manager
        manager = get_worker_manager()
        workers = manager.get_all_workers()
        
        for device_id in workers.keys():
            await queue_service.disconnect_camera(device_id)

        logger.info(
            "✅ Admin %s disconnected all cameras, cleaned %d sessions",
            current_user.get("sub"),
            cleaned_sessions,
        )

        return {
            "message": "All cameras disconnected successfully",
            "status": "success",
            "sessions_cleaned": cleaned_sessions,
        }

    except Exception as e:
        logger.error("❌ Error in disconnect-all endpoint: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to disconnect all cameras: {str(e)}",
        ) from e


@router.post("/rtsp", dependencies=[Depends(require_admin_cameras)])
async def add_rtsp_camera(
    camera_data: Dict,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user),
) -> Dict:
    """Add a new RTSP camera to the system."""

    try:
        # Validate required fields
        required_fields = ["name", "host", "port", "path"]
        for field in required_fields:
            if field not in camera_data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Missing required field: {field}",
                )

        # Extract camera data
        name = camera_data["name"]
        host = camera_data["host"]
        port = int(camera_data["port"])
        path = camera_data["path"]
        username = camera_data.get("username")
        password = camera_data.get("password")

        # Build RTSP URL
        credentials = ""
        if username:
            if password:
                credentials = f"{username}:{password}@"
            else:
                credentials = f"{username}@"

        rtsp_url = f"rtsp://{credentials}{host}:{port}{path}"
        device_id = f"rtsp_{host}_{port}"

        # Check if camera already exists
        existing_camera = db.query(Camera).filter(Camera.device_id == device_id).first()
        if existing_camera:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"RTSP camera with host {host}:{port} already exists",
            )

        # Create new RTSP camera
        new_camera = Camera(
            name=name,
            device_id=device_id,
            camera_type=CameraType.RTSP,
            status=CameraStatus.AVAILABLE,
            connection_string=rtsp_url,
            port=port,
            username=username,
            password=password,  # TODO: Encrypt in production
            resolution_width=1920,  # Default resolution
            resolution_height=1080,
            max_fps=30,
            supports_streaming=True,
            supports_recording=True,  # Enable RTSP camera recording
            supports_audio=False,
            supports_ptz=False,
        )

        db.add(new_camera)
        db.commit()
        db.refresh(new_camera)

        logger.info(f"User {current_user.get('sub')} added RTSP camera: {name}")

        return {
            "message": "RTSP camera added successfully",
            "camera": {
                "id": new_camera.id,
                "name": new_camera.name,
                "device_id": new_camera.device_id,
                "camera_type": new_camera.camera_type.value,
                "status": new_camera.status.value,
                "rtsp_url": rtsp_url,
            },
        }

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid port number: {camera_data.get('port')}",
        )
    except Exception as e:
        logger.error(f"Error adding RTSP camera: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add RTSP camera",
        )


@router.delete("/rtsp/{device_id}", dependencies=[Depends(require_admin_cameras)])
async def remove_rtsp_camera(
    device_id: str,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user),
) -> Dict:
    """Remove an RTSP camera from the system."""

    try:
        # Find the camera
        camera = (
            db.query(Camera)
            .filter(
                Camera.device_id == device_id, Camera.camera_type == CameraType.RTSP
            )
            .first()
        )

        if not camera:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="RTSP camera not found",
            )

        # Disconnect if connected
        if camera.status == CameraStatus.CONNECTED:
            queue_service = get_camera_service()
            await queue_service.disconnect_camera(device_id)

        # Delete the camera
        db.delete(camera)
        db.commit()

        logger.info(
            f"User {current_user.get('sub')} removed RTSP camera: " f"{camera.name}"
        )

        return {
            "message": "RTSP camera removed successfully",
            "camera_id": device_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing RTSP camera: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove RTSP camera",
        )


@router.put("/rtsp/{device_id}", dependencies=[Depends(require_admin_cameras)])
async def update_rtsp_camera(
    device_id: str,
    camera_update: RTSPCameraCreate,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user),
) -> Dict:
    """Update an existing RTSP camera configuration."""

    try:
        # Find the camera
        camera = (
            db.query(Camera)
            .filter(
                Camera.device_id == device_id, Camera.camera_type == CameraType.RTSP
            )
            .first()
        )

        if not camera:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="RTSP camera not found",
            )

        # Update camera fields
        camera.name = camera_update.name

        # Build new device_id and RTSP URL
        new_device_id = f"rtsp_{camera_update.host}_{camera_update.port}"

        # Build RTSP URL with credentials
        credentials = ""
        if camera_update.username:
            if camera_update.password:
                credentials = f"{camera_update.username}:{camera_update.password}@"
            else:
                credentials = f"{camera_update.username}@"

        rtsp_url = f"rtsp://{credentials}{camera_update.host}:{camera_update.port}{camera_update.path}"

        # Update camera fields
        camera.device_id = new_device_id
        camera.connection_string = rtsp_url
        camera.username = camera_update.username
        camera.password = camera_update.password
        camera.supports_recording = True  # Enable RTSP camera recording
        camera.last_seen = datetime.utcnow()

        # Commit changes
        db.commit()
        db.refresh(camera)

        logger.info(
            f"User {current_user.get('sub')} updated RTSP camera: " f"{camera.name}"
        )

        return {
            "message": "RTSP camera updated successfully",
            "camera": {
                "id": camera.id,
                "name": camera.name,
                "device_id": camera.device_id,
                "camera_type": camera.camera_type.value,
                "status": camera.status.value,
                "rtsp_url": rtsp_url,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating RTSP camera: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update RTSP camera",
        )


# 📱 MOBILE CAMERA ENDPOINTS


@router.post("/mobile", dependencies=[Depends(require_connect_camera)])
async def register_mobile_camera(
    mobile_data: MobileCameraCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user),
) -> Dict:
    """Register a mobile device as a camera in the PPL Meta Platform."""

    try:
        # Auto-detect client IP address from request
        client_ip = request.client.host
        actual_ip = mobile_data.ip_address or client_ip

        logger.info(
            f"Mobile camera registration: client_ip={client_ip}, provided_ip={mobile_data.ip_address}, using_ip={actual_ip}"
        )

        # Check if mobile camera already exists
        existing_camera = (
            db.query(Camera).filter(Camera.device_id == mobile_data.device_id).first()
        )
        if existing_camera:
            # Update existing camera with new IP address and connection string
            logger.info(
                f"User {current_user.get('sub')} updating existing mobile camera: "
                f"{mobile_data.device_id} with new IP {actual_ip}"
            )

            # Update IP address and rebuild connection string
            existing_camera.connection_string = (
                f"mobile://{actual_ip}:{mobile_data.port}"
            )
            existing_camera.port = mobile_data.port
            existing_camera.last_seen = datetime.utcnow()

            # Update other fields that might have changed
            if mobile_data.name != existing_camera.name:
                existing_camera.name = mobile_data.name
            if mobile_data.resolution_width != existing_camera.resolution_width:
                existing_camera.resolution_width = mobile_data.resolution_width
            if mobile_data.resolution_height != existing_camera.resolution_height:
                existing_camera.resolution_height = mobile_data.resolution_height

            db.commit()
            db.refresh(existing_camera)

            return {
                "message": "Mobile camera updated with new IP address",
                "camera": {
                    "id": existing_camera.id,
                    "name": existing_camera.name,
                    "device_id": existing_camera.device_id,
                    "camera_type": existing_camera.camera_type.value,
                    "status": existing_camera.status.value,
                    "connection_string": existing_camera.connection_string,
                    "ip_address": actual_ip,
                    "port": existing_camera.port,
                    "resolution": f"{existing_camera.resolution_width}x{existing_camera.resolution_height}",
                },
            }

        # Build mobile streaming URL/connection string
        connection_string = f"mobile://{actual_ip}:{mobile_data.port}"

        # Create new mobile camera
        new_camera = Camera(
            name=mobile_data.name,
            device_id=mobile_data.device_id,
            camera_type=CameraType.MOBILE,
            status=CameraStatus.AVAILABLE,
            connection_string=connection_string,
            port=mobile_data.port,
            resolution_width=mobile_data.resolution_width,
            resolution_height=mobile_data.resolution_height,
            max_fps=mobile_data.max_fps,
            manufacturer=mobile_data.device_manufacturer,
            model=mobile_data.device_model,
            firmware_version=mobile_data.app_version,
            supports_streaming=True,
            supports_recording=True,  # Enable mobile camera recording
            supports_audio=mobile_data.supports_audio,
            supports_ptz=False,
        )

        db.add(new_camera)
        db.commit()
        db.refresh(new_camera)

        logger.info(
            f"User {current_user.get('sub')} registered mobile camera: "
            f"{mobile_data.name} ({mobile_data.device_id})"
        )

        return {
            "message": "Mobile camera registered successfully",
            "camera": {
                "id": new_camera.id,
                "name": new_camera.name,
                "device_id": new_camera.device_id,
                "camera_type": new_camera.camera_type.value,
                "status": new_camera.status.value,
                "connection_string": connection_string,
                "ip_address": actual_ip,
                "port": mobile_data.port,
                "resolution": f"{mobile_data.resolution_width}x{mobile_data.resolution_height}",
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registering mobile camera: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register mobile camera",
        )


@router.put("/mobile/{device_id}", dependencies=[Depends(require_connect_camera)])
async def update_mobile_camera(
    device_id: str,
    mobile_update: MobileCameraUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user),
) -> Dict:
    """Update mobile camera status and properties."""

    try:
        # Find the mobile camera
        camera = (
            db.query(Camera)
            .filter(
                Camera.device_id == device_id, Camera.camera_type == CameraType.MOBILE
            )
            .first()
        )

        if not camera:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Mobile camera {device_id} not found",
            )

        # Update fields if provided
        updated_fields = []
        if mobile_update.status is not None:
            camera.status = mobile_update.status
            updated_fields.append("status")

        if mobile_update.resolution_width is not None:
            camera.resolution_width = mobile_update.resolution_width
            updated_fields.append("resolution_width")

        if mobile_update.resolution_height is not None:
            camera.resolution_height = mobile_update.resolution_height
            updated_fields.append("resolution_height")

        # Handle IP address update - use auto-detection instead of client-provided IP
        if mobile_update.ip_address is not None:
            # Auto-detect client IP address from request
            client_ip = request.client.host
            actual_ip = mobile_update.ip_address or client_ip
            port = mobile_update.port or camera.port or 8554
            camera.connection_string = f"mobile://{actual_ip}:{port}"
            camera.port = port
            updated_fields.append("ip_address")
            updated_fields.append("connection_string")
            logger.info(
                f"Mobile camera {device_id} IP updated: client_ip={client_ip}, provided_ip={mobile_update.ip_address}, using_ip={actual_ip}"
            )

        # Update last_seen timestamp
        camera.last_seen = datetime.utcnow()
        updated_fields.append("last_seen")

        db.commit()

        logger.info(
            f"User {current_user.get('sub')} updated mobile camera "
            f"{device_id}: {', '.join(updated_fields)}"
        )

        return {
            "message": "Mobile camera updated successfully",
            "device_id": device_id,
            "updated_fields": updated_fields,
            "camera": {
                "id": camera.id,
                "name": camera.name,
                "device_id": camera.device_id,
                "status": camera.status.value,
                "resolution": f"{camera.resolution_width}x{camera.resolution_height}",
                "last_seen": camera.last_seen.isoformat(),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating mobile camera {device_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update mobile camera",
        )


@router.delete("/mobile/{device_id}", dependencies=[Depends(require_admin_cameras)])
async def unregister_mobile_camera(
    device_id: str,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user),
) -> Dict:
    """Unregister a mobile camera from the PPL Meta Platform."""

    try:
        # Find the mobile camera
        camera = (
            db.query(Camera)
            .filter(
                Camera.device_id == device_id, Camera.camera_type == CameraType.MOBILE
            )
            .first()
        )

        if not camera:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Mobile camera {device_id} not found",
            )

        # Clean up any active streaming sessions for this device
        cleaned_sessions = session_manager.cleanup_sessions_for_device(device_id)

        # Disconnect if connected
        if camera.status == CameraStatus.CONNECTED:
            queue_service = get_camera_service()
            await queue_service.disconnect_camera(device_id)

        # Delete the camera
        camera_name = camera.name
        db.delete(camera)
        db.commit()

        logger.info(
            "User %s unregistered mobile camera: %s (%s), cleaned %d sessions",
            current_user.get("sub"),
            camera_name,
            device_id,
            cleaned_sessions,
        )

        return {
            "message": "Mobile camera unregistered successfully",
            "device_id": device_id,
            "camera_name": camera_name,
            "sessions_cleaned": cleaned_sessions,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unregistering mobile camera {device_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unregister mobile camera",
        )


@router.get("/mobile", dependencies=[Depends(require_view_cameras)])
async def list_mobile_cameras(
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user),
) -> List[Dict]:
    """List all registered mobile cameras."""

    try:
        mobile_cameras = (
            db.query(Camera).filter(Camera.camera_type == CameraType.MOBILE).all()
        )

        camera_list = []
        for camera in mobile_cameras:
            camera_dict = {
                "id": camera.id,
                "name": camera.name,
                "device_id": camera.device_id,
                "camera_type": camera.camera_type.value,
                "status": camera.status.value,
                "connection_string": camera.connection_string,  # Add for direct frontend access
                "ip_address": camera.connection_string.split("://")[1].split(":")[0],
                "port": camera.port,
                "resolution": f"{camera.resolution_width}x{camera.resolution_height}",
                "max_fps": camera.max_fps,
                "supports_audio": camera.supports_audio,
                "manufacturer": camera.manufacturer,
                "model": camera.model,
                "app_version": camera.firmware_version,
                "last_seen": camera.last_seen.isoformat() if camera.last_seen else None,
                "created_at": (
                    camera.created_at.isoformat() if camera.created_at else None
                ),
            }
            camera_list.append(camera_dict)

        logger.info(
            f"User {current_user.get('sub')} listed {len(camera_list)} mobile cameras"
        )

        return camera_list

    except Exception as e:
        logger.error(f"Error listing mobile cameras: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list mobile cameras",
        )


@router.post(
    "/mobile/{device_id}/update-ip", dependencies=[Depends(require_connect_camera)]
)
async def update_mobile_camera_ip(
    device_id: str,
    ip_update: Dict[str, Any],
    request: Request,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user),
) -> Dict:
    """Update mobile camera IP address when the device detects network changes."""

    try:
        # Find the mobile camera
        camera = (
            db.query(Camera)
            .filter(
                Camera.device_id == device_id, Camera.camera_type == CameraType.MOBILE
            )
            .first()
        )

        if not camera:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Mobile camera {device_id} not found",
            )

        # Auto-detect client IP address from request
        client_ip = request.client.host
        provided_ip = ip_update.get("ip_address")
        actual_ip = provided_ip or client_ip
        new_port = ip_update.get("port", camera.port or 8554)

        # Update connection string with detected IP
        old_connection = camera.connection_string
        camera.connection_string = f"mobile://{actual_ip}:{new_port}"
        camera.port = new_port
        camera.last_seen = datetime.utcnow()

        db.commit()

        logger.info(
            f"Mobile camera {device_id} IP updated: client_ip={client_ip}, "
            f"provided_ip={provided_ip}, using_ip={actual_ip}, "
            f"old={old_connection} -> new=mobile://{actual_ip}:{new_port}"
        )

        return {
            "message": "Mobile camera IP updated successfully",
            "device_id": device_id,
            "old_connection": old_connection,
            "new_connection": camera.connection_string,
            "ip_address": actual_ip,
            "port": new_port,
            "updated_at": camera.last_seen.isoformat() if camera.last_seen else None,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating mobile camera IP {device_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update mobile camera IP",
        )


@router.post(
    "/mobile/{device_id}/heartbeat", dependencies=[Depends(require_connect_camera)]
)
async def mobile_camera_heartbeat(
    device_id: str,
    heartbeat_data: Optional[Dict] = None,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user),
) -> Dict:
    """Receive heartbeat from mobile camera to update last_seen timestamp."""

    try:
        # Find the mobile camera
        camera = (
            db.query(Camera)
            .filter(
                Camera.device_id == device_id, Camera.camera_type == CameraType.MOBILE
            )
            .first()
        )

        if not camera:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Mobile camera {device_id} not found",
            )

        # Update last_seen timestamp
        camera.last_seen = datetime.utcnow()

        # Update status to CONNECTED if it was AVAILABLE
        if camera.status == CameraStatus.AVAILABLE:
            camera.status = CameraStatus.CONNECTED

        db.commit()

        return {
            "message": "Heartbeat received",
            "device_id": device_id,
            "status": camera.status.value,
            "timestamp": camera.last_seen.isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing heartbeat for mobile camera {device_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process mobile camera heartbeat",
        )


@router.post("/mobile/cleanup-stale", dependencies=[Depends(require_admin_cameras)])
async def cleanup_stale_mobile_cameras(
    current_user: Dict = Depends(get_current_user),
) -> Dict:
    """Manually trigger cleanup of stale mobile camera connections."""

    try:
        from src.services.mobile_cleanup import mobile_cleanup_service

        updated_count = await mobile_cleanup_service.cleanup_stale_mobile_cameras()

        logger.info(
            f"Admin {current_user.get('sub')} triggered mobile camera cleanup, "
            f"updated {updated_count} cameras"
        )

        return {
            "message": "Mobile camera cleanup completed",
            "updated_cameras": updated_count,
            "status": "success",
        }

    except Exception as e:
        logger.error(f"Error during manual mobile camera cleanup: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cleanup stale mobile cameras",
        )


@router.websocket("/mobile/{device_id}/stream")
async def mobile_camera_stream_websocket(websocket: WebSocket, device_id: str):
    """WebSocket endpoint for camera streaming with integrated session management."""
    await websocket.accept()

    session_uuid = None  # Track session for cleanup

    try:
        logger.info(f"WebSocket connection established for camera {device_id}")

        # Send initial connection confirmation
        await websocket.send_text(
            json.dumps(
                {
                    "type": "connection_established",
                    "device_id": device_id,
                    "message": "Connected to PPL Meta camera streaming server",
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )
        )

        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for messages from mobile app
                data = await websocket.receive_text()
                message = json.loads(data)

                logger.info(
                    f"Received message from mobile camera {device_id}: {message.get('type', 'unknown')}"
                )

                # Handle different message types
                if message.get("type") == "ping":
                    await websocket.send_text(
                        json.dumps(
                            {"type": "pong", "timestamp": datetime.utcnow().isoformat()}
                        )
                    )

                elif message.get("type") == "start_stream":
                    # Create a new streaming session when stream starts
                    session_uuid = (
                        await streaming_session_manager.create_streaming_session(
                            device_id=device_id,
                            session_metadata={
                                "connection_type": "websocket",
                                "stream_start_time": datetime.utcnow().isoformat(),
                            },
                        )
                    )

                    response = {
                        "type": "stream_ready",
                        "device_id": device_id,
                        "message": "Camera stream is ready to receive frames",
                        "timestamp": datetime.utcnow().isoformat(),
                    }

                    if session_uuid:
                        response["session_uuid"] = session_uuid
                        logger.info(
                            f"✅ Created streaming session {session_uuid} for device {device_id}"
                        )
                    else:
                        logger.warning(
                            f"⚠️ Failed to create streaming session for device {device_id}"
                        )

                    await websocket.send_text(json.dumps(response))

                elif message.get("type") == "stop_stream":
                    # Stop the mobile camera stream and reject future frames
                    from src.services.mobile_streaming import mobile_streaming_service
                    
                    success = await mobile_streaming_service.stop_mobile_camera_stream(device_id)
                    
                    response = {
                        "type": "stream_stopped",
                        "device_id": device_id,
                        "success": success,
                        "message": "Camera stream stopped" if success else "Failed to stop stream",
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                    
                    logger.info(f"🛑 Stopped mobile camera stream for {device_id}, success={success}")
                    await websocket.send_text(json.dumps(response))

                elif message.get("type") == "frame_data":
                    # Handle incoming frame data with session-aware face detection
                    frame_response = {
                        "type": "frame_received",
                        "timestamp": datetime.utcnow().isoformat(),
                    }

                    try:
                        # Extract frame data from message
                        frame_base64 = message.get("frame_data")
                        if frame_base64 and session_uuid:
                            # Decode frame and perform session-aware face detection
                            import base64

                            import cv2
                            import numpy as np

                            # Decode base64 frame
                            frame_bytes = base64.b64decode(frame_base64)
                            nparr = np.frombuffer(frame_bytes, np.uint8)
                            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                            if frame is not None:
                                # Perform session-aware face detection
                                detection_result = await session_aware_face_detector.detect_faces_with_session(
                                    frame=frame,
                                    session_uuid=session_uuid,
                                    device_id=device_id,
                                    method="two_stage",
                                    confidence_threshold=0.7,
                                    frame_metadata={
                                        "frame_size": frame.shape,
                                        "websocket_message_type": "frame_data",
                                        "encoding": "base64_jpeg",
                                    },
                                )

                                # Update session with detection results
                                await streaming_session_manager.update_session_detection(
                                    device_id=device_id,
                                    faces_detected=detection_result["faces_detected"],
                                    frame_metadata=detection_result["frame_metadata"],
                                )

                                # Include enhanced detection results in response
                                frame_response.update(
                                    {
                                        "faces_detected": detection_result[
                                            "face_count"
                                        ],
                                        "session_uuid": session_uuid,
                                        "detection_results": detection_result[
                                            "faces_detected"
                                        ],
                                        "session_statistics": detection_result[
                                            "session_statistics"
                                        ],
                                        "detection_time_ms": detection_result[
                                            "detection_time_ms"
                                        ],
                                    }
                                )

                                # Broadcast immediate statistics update if there are faces detected
                                if detection_result["face_count"] > 0:
                                    immediate_stats = {
                                        "timestamp": datetime.utcnow().isoformat(),
                                        "type": "immediate_detection",
                                        "device_id": device_id,
                                        "session_uuid": session_uuid,
                                        "faces_detected": detection_result[
                                            "face_count"
                                        ],
                                        "session_statistics": detection_result[
                                            "session_statistics"
                                        ],
                                    }
                                    await statistics_broadcaster.broadcast_immediate(
                                        immediate_stats
                                    )

                                logger.debug(
                                    f"🔍 Detected {detection_result['face_count']} faces in WebSocket frame from {device_id}"
                                )
                            else:
                                logger.warning(
                                    f"⚠️ Failed to decode frame from {device_id}"
                                )

                    except Exception as detection_error:
                        logger.error(
                            f"❌ Face detection error for {device_id}: {detection_error}"
                        )
                        frame_response["detection_error"] = str(detection_error)

                    await websocket.send_text(json.dumps(frame_response))

                else:
                    # Echo back unknown messages
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "echo",
                                "original_message": message,
                                "timestamp": datetime.utcnow().isoformat(),
                            }
                        )
                    )

            except json.JSONDecodeError:
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "error",
                            "message": "Invalid JSON format",
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    )
                )

    except WebSocketDisconnect:
        # Clean up sessions when mobile camera disconnects via WebSocket
        if session_uuid:
            await streaming_session_manager.complete_streaming_session(
                device_id=device_id, completion_reason="websocket_disconnect"
            )
            logger.info(
                f"✅ Completed streaming session {session_uuid} due to WebSocket disconnect"
            )

        cleaned_sessions = session_manager.cleanup_sessions_for_device(device_id)
        logger.info(
            "WebSocket connection closed for camera %s, cleaned %d sessions",
            device_id,
            cleaned_sessions,
        )
    except Exception as e:
        logger.error("WebSocket error for camera %s: %s", device_id, e)

        # Complete streaming session on error
        if session_uuid:
            await streaming_session_manager.complete_streaming_session(
                device_id=device_id, completion_reason="websocket_error"
            )
            logger.info(
                f"✅ Completed streaming session {session_uuid} due to WebSocket error"
            )

        # Clean up sessions on error as well
        cleaned_sessions = session_manager.cleanup_sessions_for_device(device_id)
        logger.info("Cleaned %d sessions due to WebSocket error", cleaned_sessions)
        try:
            await websocket.close()
        except Exception:
            pass


@router.websocket("/statistics/stream")
async def session_statistics_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time session statistics broadcasting."""
    await statistics_broadcaster.handle_statistics_websocket(websocket)


# CAMERA SETTINGS ENDPOINTS


@router.get("/{device_id}/settings", dependencies=[Depends(require_view_cameras)])
async def get_camera_settings(
    device_id: str,
    user_id: str = None,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user),
) -> Dict:
    """Get camera settings for a specific user and camera."""
    try:
        from src.models.camera_settings import CameraSettings

        # Use current user if user_id not provided
        target_user_id = user_id if user_id else current_user.get("sub")

        # Query settings
        settings = (
            db.query(CameraSettings)
            .filter(
                CameraSettings.camera_device_id == device_id,
                CameraSettings.user_id == target_user_id,
            )
            .first()
        )

        if not settings:
            # Return default settings if none exist
            default_settings = {
                "camera_device_id": device_id,
                "user_id": target_user_id,
                "auto_face_detection": False,
                "detection_methods": ["mtcnn"],
                "processing_options": {},
                "auto_recording": False,
                "recording_duration": 30,
                "notifications_enabled": True,
                "notification_methods": ["email"],
                "store_faces_in_memory": True,
                "persist_after_recording": True,
            }

            # Create and save default settings
            settings = CameraSettings(**default_settings)
            db.add(settings)
            db.commit()
            db.refresh(settings)

        return settings.to_dict()

    except Exception as e:
        logger.error(f"Error getting camera settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get camera settings: {str(e)}",
        )


@router.put("/{device_id}/settings", dependencies=[Depends(require_connect_camera)])
async def update_camera_settings(
    device_id: str,
    settings_update: Dict,
    user_id: str = None,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user),
) -> Dict:
    """Update camera settings for a specific user and camera."""
    try:
        from src.models.camera_settings import CameraSettings

        # Use current user if user_id not provided
        target_user_id = user_id if user_id else current_user.get("sub")

        # Get existing settings or create new ones
        settings = (
            db.query(CameraSettings)
            .filter(
                CameraSettings.camera_device_id == device_id,
                CameraSettings.user_id == target_user_id,
            )
            .first()
        )

        if not settings:
            # Create new settings if none exist
            settings = CameraSettings(
                camera_device_id=device_id,
                user_id=target_user_id,
            )
            db.add(settings)

        # Update fields that are provided
        for field, value in settings_update.items():
            if hasattr(settings, field):
                setattr(settings, field, value)

        db.commit()
        db.refresh(settings)

        logger.info(
            f"Updated camera settings for device {device_id}, user {target_user_id}"
        )

        return settings.to_dict()

    except Exception as e:
        logger.error(f"Error updating camera settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update camera settings: {str(e)}",
        )


# =============================================================================
# PIPELINE SETTINGS ENDPOINTS - Instant Detection & Recording Decoupling
# =============================================================================


@router.get("/{device_id}/pipeline-settings", dependencies=[Depends(require_view_cameras)])
async def get_pipeline_settings(
    device_id: str,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user),
) -> Dict:
    """
    Get current pipeline settings for a specific camera.
    
    Returns the instant detection and recording pipeline configuration
    for the specified camera.
    
    Args:
        device_id: Camera device ID
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Pipeline settings including instant detection and recording configuration
    """
    try:
        camera = db.query(Camera).filter(Camera.device_id == device_id).first()
        if not camera:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Camera {device_id} not found",
            )
        
        return {
            "device_id": camera.device_id,
            "camera_name": camera.name,
            "instant_detection_enabled": camera.instant_detection_enabled,
            "recording_pipeline_enabled": camera.recording_pipeline_enabled,
            "instant_detection_interval_seconds": camera.instant_detection_interval_seconds,
            "segment_duration_seconds": camera.segment_duration_seconds,
            "created_at": camera.created_at.isoformat() if camera.created_at else None,
            "updated_at": camera.updated_at.isoformat() if camera.updated_at else None,
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting pipeline settings for {device_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get pipeline settings: {str(e)}",
        )


@router.patch("/{device_id}/pipeline-settings", dependencies=[Depends(require_connect_camera)])
async def update_pipeline_settings(
    device_id: str,
    instant_detection_enabled: bool,
    recording_pipeline_enabled: bool,
    instant_detection_interval_seconds: int = 5,
    segment_duration_seconds: int = 30,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user),
) -> Dict:
    """
    Update pipeline settings for a specific camera.
    
    Allows independent control of instant detection and recording pipelines.
    At least one pipeline must be enabled.
    
    Args:
        device_id: Camera device ID
        instant_detection_enabled: Enable instant detection pipeline
        recording_pipeline_enabled: Enable recording and continuous detection pipeline
        instant_detection_interval_seconds: Interval for instant detection (1-60 seconds)
        segment_duration_seconds: Segment duration for recording (5-300 seconds)
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Updated pipeline settings
    """
    try:
        # Validate: At least one pipeline must be enabled
        if not instant_detection_enabled and not recording_pipeline_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one pipeline must be enabled (instant detection or recording)",
            )
        
        # Validate interval ranges
        if instant_detection_interval_seconds < 1 or instant_detection_interval_seconds > 60:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Instant detection interval must be between 1 and 60 seconds",
            )
        
        if segment_duration_seconds < 5 or segment_duration_seconds > 300:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Segment duration must be between 5 and 300 seconds",
            )
        
        # Get camera from database
        camera = db.query(Camera).filter(Camera.device_id == device_id).first()
        if not camera:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Camera {device_id} not found",
            )
        
        # Update settings
        camera.instant_detection_enabled = instant_detection_enabled
        camera.recording_pipeline_enabled = recording_pipeline_enabled
        camera.instant_detection_interval_seconds = instant_detection_interval_seconds
        camera.segment_duration_seconds = segment_duration_seconds
        
        db.commit()
        db.refresh(camera)
        
        logger.info(
            f"📹 Updated pipeline settings for {device_id}: "
            f"instant_detection={instant_detection_enabled}, "
            f"recording_pipeline={recording_pipeline_enabled}"
        )
        
        return {
            "device_id": camera.device_id,
            "camera_name": camera.name,
            "instant_detection_enabled": camera.instant_detection_enabled,
            "recording_pipeline_enabled": camera.recording_pipeline_enabled,
            "instant_detection_interval_seconds": camera.instant_detection_interval_seconds,
            "segment_duration_seconds": camera.segment_duration_seconds,
            "updated_at": camera.updated_at.isoformat() if camera.updated_at else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update pipeline settings for {device_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update pipeline settings: {str(e)}",
        )


@router.get("/{device_id}/workflow-settings", dependencies=[Depends(require_connect_camera)])
async def get_workflow_settings(
    device_id: str,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user),
) -> Dict:
    """
    Get workflow settings (face detection & performance) for a specific camera.
    
    Args:
        device_id: Camera device ID
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Current workflow settings
    """
    try:
        camera = db.query(Camera).filter(Camera.device_id == device_id).first()
        if not camera:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Camera {device_id} not found",
            )
        
        return {
            "device_id": camera.device_id,
            "camera_name": camera.name,
            "auto_face_detection": camera.auto_face_detection if hasattr(camera, 'auto_face_detection') else False,
            "detection_methods": camera.detection_methods if hasattr(camera, 'detection_methods') else ["opencv", "dlib"],
            "processing_options": camera.processing_options if hasattr(camera, 'processing_options') else {},
            "confidence_threshold": camera.confidence_threshold if hasattr(camera, 'confidence_threshold') else 0.7,
            "enable_performance_optimization": camera.enable_performance_optimization if hasattr(camera, 'enable_performance_optimization') else True,
            "show_performance_indicators": camera.show_performance_indicators if hasattr(camera, 'show_performance_indicators') else True,
            "default_playback_mode": camera.default_playback_mode if hasattr(camera, 'default_playback_mode') else "auto",
            "mvr_quality_threshold": camera.mvr_quality_threshold if hasattr(camera, 'mvr_quality_threshold') else 0.20,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workflow settings for {device_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get workflow settings: {str(e)}",
        )


@router.patch("/{device_id}/workflow-settings", dependencies=[Depends(require_connect_camera)])
async def update_workflow_settings(
    device_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user),
) -> Dict:
    """
    Update workflow settings (face detection & performance) for a specific camera.
    
    Args:
        device_id: Camera device ID
        request: HTTP request with JSON body
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Updated workflow settings
    """
    try:
        # Parse JSON body
        body = await request.json()
        auto_face_detection = body.get('auto_face_detection')
        detection_methods = body.get('detection_methods')
        processing_options = body.get('processing_options')
        confidence_threshold = body.get('confidence_threshold')
        enable_performance_optimization = body.get('enable_performance_optimization')
        show_performance_indicators = body.get('show_performance_indicators')
        default_playback_mode = body.get('default_playback_mode')
        mvr_quality_threshold = body.get('mvr_quality_threshold')
        
        # Validate confidence threshold
        if confidence_threshold is not None and (confidence_threshold < 0.0 or confidence_threshold > 1.0):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Confidence threshold must be between 0.0 and 1.0",
            )
        
        # Validate mvr_quality_threshold
        if mvr_quality_threshold is not None and (mvr_quality_threshold < 0.0 or mvr_quality_threshold > 1.0):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="MVR quality threshold must be between 0.0 and 1.0",
            )
        
        # Validate detection methods
        valid_methods = ["opencv", "dlib", "mtcnn", "yolo"]
        if detection_methods is not None:
            for method in detection_methods:
                if method not in valid_methods:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid detection method: {method}. Valid methods: {valid_methods}",
                    )
        
        # Get camera from database
        camera = db.query(Camera).filter(Camera.device_id == device_id).first()
        if not camera:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Camera {device_id} not found",
            )
        
        # Update settings (only if provided)
        if auto_face_detection is not None:
            camera.auto_face_detection = auto_face_detection
        if detection_methods is not None:
            camera.detection_methods = detection_methods
        if processing_options is not None:
            camera.processing_options = processing_options
        if confidence_threshold is not None:
            camera.confidence_threshold = confidence_threshold
        if enable_performance_optimization is not None:
            camera.enable_performance_optimization = enable_performance_optimization
        if show_performance_indicators is not None:
            camera.show_performance_indicators = show_performance_indicators
        if default_playback_mode is not None:
            camera.default_playback_mode = default_playback_mode
        if mvr_quality_threshold is not None:
            camera.mvr_quality_threshold = mvr_quality_threshold
        
        db.commit()
        db.refresh(camera)
        
        logger.info(
            f"📹 Updated workflow settings for {device_id}: "
            f"auto_face_detection={camera.auto_face_detection}, "
            f"detection_methods={camera.detection_methods}"
        )
        
        return {
            "device_id": camera.device_id,
            "camera_name": camera.name,
            "auto_face_detection": camera.auto_face_detection,
            "detection_methods": camera.detection_methods,
            "processing_options": camera.processing_options,
            "confidence_threshold": camera.confidence_threshold,
            "enable_performance_optimization": camera.enable_performance_optimization,
            "show_performance_indicators": camera.show_performance_indicators,
            "default_playback_mode": camera.default_playback_mode,
            "mvr_quality_threshold": camera.mvr_quality_threshold,
            "updated_at": camera.updated_at.isoformat() if camera.updated_at else None,
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating pipeline settings for {device_id}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update pipeline settings: {str(e)}",
        )


# =============================================================================
# RECORDING ENDPOINTS - Phase 2: Backend Recording Implementation
# =============================================================================


@router.post("/{device_id}/recording/start", dependencies=[Depends(require_connect_camera)])
async def start_recording(
    device_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
) -> Dict:
    """
    Start recording from camera worker buffer.
    
    Flow:
    1. Get worker for device_id
    2. Create recording session
    3. Start background task to read from worker.get_latest_frame()
    4. Write frames to video file
    5. Return session_id
    """
    try:
        # Get camera service and worker
        camera_service = get_camera_service()
        from src.services.worker_manager import get_worker_manager
        manager = get_worker_manager()
        
        worker = manager.get_worker(device_id)
        if not worker:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Camera worker not found for {device_id}"
            )
        
        # Check worker status
        from src.services.camera_worker import CameraStatus
        if worker.status != CameraStatus.CONNECTED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Camera not connected (status: {worker.status.value})"
            )
        
        # Get recording service
        from src.services.recording_service import get_recording_service
        recording_service = get_recording_service()
        
        # Check if already recording
        active_session = await recording_service.get_active_session(device_id)
        if active_session:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Camera {device_id} is already recording (session: {active_session['id']})"
            )
        
        # Create recording session
        user_id = current_user.get('sub', 'unknown')
        session_id = await recording_service.create_session(
            device_id=device_id,
            user_id=user_id
        )
        
        # Small delay to ensure WebSocket listeners are ready
        await asyncio.sleep(0.1)
        
        # Publish recording_started event immediately (before background task)
        try:
            from src.services.status_notification_service import get_status_service, CameraStatusEvent
            status_service = get_status_service()
            await status_service.publish_status_change(
                device_id, 
                CameraStatusEvent.RECORDING_STARTED,
                {
                    "session_id": session_id,
                    "resolution": f"{worker.camera_info.get('resolution_width', 1280)}x{worker.camera_info.get('resolution_height', 720)}",
                    "fps": worker.camera_info.get('max_fps', 30)
                }
            )
        except Exception as e:
            logger.warning(f"Could not publish recording_started event: {e}")
        
        # Start recording task (reads from worker buffer)
        background_tasks.add_task(
            recording_service.record_from_worker,
            worker=worker,
            session_id=session_id
        )
        
        logger.info(f"🎥 User {user_id} started recording on {device_id} (session: {session_id})")
        
        return {
            "status": "success",
            "session_id": session_id,
            "device_id": device_id,
            "message": "Recording started",
            "started_at": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error starting recording for {device_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start recording: {str(e)}"
        )


@router.post("/{device_id}/recording/stop", dependencies=[Depends(require_connect_camera)])
async def stop_recording(
    device_id: str,
    current_user: Dict = Depends(get_current_user)
) -> Dict:
    """
    Stop active recording session.
    
    Returns recording details including duration, frame count, and file path.
    """
    try:
        # Get recording service
        from src.services.recording_service import get_recording_service
        recording_service = get_recording_service()
        
        # Get active session
        active_session = await recording_service.get_active_session(device_id)
        if not active_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No active recording found for camera {device_id}"
            )
        
        session_id = active_session['id']
        
        # Stop recording
        session_info = await recording_service.stop_session(session_id)
        
        # Calculate duration
        if 'stopped_at' in session_info and 'started_at' in session_info:
            duration = (session_info['stopped_at'] - session_info['started_at']).total_seconds()
        else:
            duration = session_info.get('duration', 0)
        
        user_id = current_user.get('sub', 'unknown')
        logger.info(f"🛑 User {user_id} stopped recording on {device_id} (session: {session_id}, duration: {duration:.1f}s)")
        
        return {
            "status": "success",
            "session_id": session_id,
            "device_id": device_id,
            "duration": duration,
            "frame_count": session_info.get('frame_count', 0),
            "file_path": session_info.get('file_path'),
            "message": "Recording stopped successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error stopping recording for {device_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop recording: {str(e)}"
        )


@router.get("/{device_id}/recording/status", dependencies=[Depends(require_view_cameras)])
async def get_recording_status(
    device_id: str,
    current_user: Dict = Depends(get_current_user)
) -> Dict:
    """
    Get current recording status for a camera.
    
    Returns whether recording is active, session info, duration, and frame count.
    """
    try:
        # Get recording service
        from src.services.recording_service import get_recording_service
        recording_service = get_recording_service()
        
        # Get active session
        active_session = await recording_service.get_active_session(device_id)
        
        if active_session:
            # Calculate current duration
            duration = (datetime.utcnow() - active_session['started_at']).total_seconds()
            
            return {
                "is_recording": True,
                "session_id": active_session['id'],
                "device_id": device_id,
                "started_at": active_session['started_at'].isoformat(),
                "duration": duration,
                "frame_count": active_session.get('frame_count', 0),
                "status": active_session.get('status', 'recording')
            }
        else:
            return {
                "is_recording": False,
                "device_id": device_id,
                "session_id": None,
                "duration": 0,
                "frame_count": 0,
                "message": "No active recording"
            }
        
    except Exception as e:
        logger.error(f"❌ Error getting recording status for {device_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get recording status: {str(e)}"
        )


@router.get("/recordings/active", dependencies=[Depends(require_view_cameras)])
async def list_active_recordings(
    current_user: Dict = Depends(get_current_user)
) -> Dict:
    """
    List all currently active recording sessions across all cameras.
    
    Returns list of active sessions with device info, duration, and frame counts.
    """
    try:
        # Get recording service
        from src.services.recording_service import get_recording_service
        recording_service = get_recording_service()
        
        # Get all active sessions
        active_sessions = recording_service.get_active_sessions()
        
        # Format sessions with current duration
        sessions_list = []
        for session in active_sessions:
            duration = (datetime.utcnow() - session['started_at']).total_seconds()
            sessions_list.append({
                "session_id": session['id'],
                "device_id": session['device_id'],
                "user_id": session['user_id'],
                "started_at": session['started_at'].isoformat(),
                "duration": duration,
                "frame_count": session.get('frame_count', 0),
                "status": session.get('status', 'recording')
            })
        
        return {
            "active_count": len(sessions_list),
            "sessions": sessions_list
        }
        
    except Exception as e:
        logger.error(f"❌ Error listing active recordings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list active recordings: {str(e)}"
        )
