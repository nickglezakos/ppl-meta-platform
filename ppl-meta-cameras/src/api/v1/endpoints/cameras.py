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
from src.services.camera_detection import camera_service
from src.services.session_auth import session_manager

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

        camera_list = []
        for camera in cameras:
            camera_dict = {
                "id": camera.id,
                "name": camera.name,
                "device_id": camera.device_id,
                "camera_type": camera.camera_type.value,
                "status": camera.status.value,
                "resolution": f"{camera.resolution_width}x{camera.resolution_height}",
                "max_fps": camera.max_fps,
                "supports_streaming": camera.supports_streaming,
                "supports_recording": camera.supports_recording,
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


@router.post("/detect", dependencies=[Depends(require_detect_cameras)])
async def detect_cameras(
    save_to_db: bool = True,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user),
) -> Dict:
    """Detect available cameras and optionally save to database."""

    try:
        detected_cameras = await camera_service.detect_available_cameras()

        result = {
            "detected_count": len(detected_cameras),
            "cameras": detected_cameras,
            "saved_to_db": False,
        }

        if save_to_db:
            saved_count = await camera_service.save_cameras_to_db(db)
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
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user),
) -> Dict:
    """Connect to a specific camera."""

    try:
        # Check if camera exists in database
        camera = db.query(Camera).filter(Camera.device_id == device_id).first()
        if not camera:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Camera {device_id} not found",
            )

        # Mobile cameras should not be connected via backend - they use direct frontend access
        if camera.camera_type == CameraType.MOBILE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Mobile camera {device_id} does not support backend connection. "
                "Mobile cameras are accessed directly by frontend.",
            )

        # Connect to camera
        connection = await camera_service.connect_camera(device_id)
        if not connection:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to connect to camera {device_id}",
            )

        # Update camera status in database
        camera.status = CameraStatus.CONNECTED
        db.commit()

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

        # Disconnect from camera
        success = await camera_service.disconnect_camera(device_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Camera {device_id} was not connected",
            )

        # Update camera status in database
        camera = db.query(Camera).filter(Camera.device_id == device_id).first()
        if camera:
            camera.status = CameraStatus.AVAILABLE
            db.commit()

        logger.info(
            "User %s disconnected from camera %s, cleaned %d sessions",
            current_user.get("sub"),
            device_id,
            cleaned_sessions,
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
        runtime_info = await camera_service.get_camera_info(device_id)

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
        active_connections = await camera_service.list_active_connections()

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
        # Clean up all active streaming sessions
        cleaned_sessions = session_manager.cleanup_all_sessions()

        await camera_service.disconnect_all()

        logger.info(
            "Admin %s disconnected all cameras, cleaned %d sessions",
            current_user.get("sub"),
            cleaned_sessions,
        )

        return {
            "message": "All cameras disconnected successfully",
            "status": "success",
            "sessions_cleaned": cleaned_sessions,
        }

    except Exception as e:
        logger.error("Error disconnecting all cameras: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to disconnect all cameras",
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
            supports_recording=False,
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
            await camera_service.disconnect_camera(device_id)

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
            supports_recording=False,
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
            await camera_service.disconnect_camera(device_id)

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
    """WebSocket endpoint for camera streaming that matches mobile app expectations."""
    await websocket.accept()

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
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "stream_ready",
                                "device_id": device_id,
                                "message": "Camera stream is ready to receive frames",
                                "timestamp": datetime.utcnow().isoformat(),
                            }
                        )
                    )

                elif message.get("type") == "frame_data":
                    # Handle incoming frame data from mobile camera
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "frame_received",
                                "timestamp": datetime.utcnow().isoformat(),
                            }
                        )
                    )

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
        cleaned_sessions = session_manager.cleanup_sessions_for_device(device_id)
        logger.info(
            "WebSocket connection closed for camera %s, cleaned %d sessions",
            device_id,
            cleaned_sessions,
        )
    except Exception as e:
        logger.error("WebSocket error for camera %s: %s", device_id, e)
        # Clean up sessions on error as well
        cleaned_sessions = session_manager.cleanup_sessions_for_device(device_id)
        logger.info("Cleaned %d sessions due to WebSocket error", cleaned_sessions)
        try:
            await websocket.close()
        except Exception:
            pass
