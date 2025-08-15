"""
Camera management endpoints for PPL Meta Cameras API.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
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
            f"User {current_user.get('sub')} disconnected from camera {device_id}"
        )

        return {
            "device_id": device_id,
            "status": "disconnected",
            "message": f"Successfully disconnected from camera {device_id}",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error disconnecting from camera {device_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to disconnect from camera",
        )


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
        await camera_service.disconnect_all()

        logger.info(f"Admin {current_user.get('sub')} disconnected all cameras")

        return {"message": "All cameras disconnected successfully", "status": "success"}

    except Exception as e:
        logger.error(f"Error disconnecting all cameras: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to disconnect all cameras",
        )


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
