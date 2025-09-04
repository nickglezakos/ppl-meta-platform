"""
Mobile camera specific streaming endpoints for PPL Meta Cameras API.
Extends the base streaming functionality with mobile-specific features.
"""

import logging
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from src.database import get_db
from src.models.camera import Camera, CameraType
from src.security.auth import get_current_user, require_start_stream
from src.services.camera_detection import camera_service
from src.services.mobile_streaming import mobile_streaming_service

logger = logging.getLogger(__name__)
router = APIRouter()


class MobileStreamConfig(BaseModel):
    """Configuration for mobile camera streaming."""

    protocol: str = "rtmp"  # rtmp or webrtc
    quality: str = "medium"  # low, medium, high, ultra
    auto_start: bool = True


class MobileStreamResponse(BaseModel):
    """Response for mobile camera streaming operations."""

    device_id: str
    status: str
    message: str
    stream_endpoint: str
    rtmp_url: str
    streaming_session_id: str


@router.post("/mobile/{device_id}/setup", dependencies=[Depends(require_start_stream)])
async def setup_mobile_camera_streaming(
    device_id: str,
    config: MobileStreamConfig,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MobileStreamResponse:
    """Setup streaming infrastructure for a mobile camera."""

    try:
        # Verify mobile camera exists and is registered
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

        # Parse mobile camera connection details
        connection_string = camera.connection_string  # mobile://ip:port
        if not connection_string or not connection_string.startswith("mobile://"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid mobile camera connection string",
            )

        try:
            _, address_part = connection_string.split("mobile://", 1)
            ip_address, port_str = address_part.split(":")
            port = int(port_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to parse mobile camera connection details",
            )

        # Create stream configuration
        stream_config = {
            "ip_address": ip_address,
            "port": port,
            "protocol": config.protocol,
            "width": camera.resolution_width or 640,
            "height": camera.resolution_height or 480,
            "fps": camera.max_fps or 30,
        }

        # Setup mobile streaming infrastructure
        success = await mobile_streaming_service.setup_mobile_camera_stream(
            device_id, stream_config
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to setup mobile camera streaming infrastructure",
            )

        # Generate streaming session for mobile app
        from src.services.session_auth import session_manager

        session_id = session_manager.create_session(
            user_id=current_user.get("sub"),
            device_id=device_id,
            expires_minutes=60,  # 1 hour session
        )

        # Build response with streaming details
        rtmp_endpoint = f"rtmp://{ip_address}:{port}/live/{device_id}"
        stream_endpoint = f"/cameras/api/v1/streaming/{device_id}/video"

        logger.info(
            f"User {current_user.get('sub')} setup mobile camera streaming for {device_id}"
        )

        return MobileStreamResponse(
            device_id=device_id,
            status="ready",
            message="Mobile camera streaming infrastructure setup complete",
            stream_endpoint=stream_endpoint,
            rtmp_url=rtmp_endpoint,
            streaming_session_id=session_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting up mobile camera streaming for {device_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to setup mobile camera streaming",
        )


@router.get("/mobile/{device_id}/status")
async def get_mobile_streaming_status(
    device_id: str,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict:
    """Get mobile camera streaming status."""

    try:
        # Verify mobile camera exists
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

        # Get mobile streaming status
        stream_status = await mobile_streaming_service.get_mobile_stream_status(
            device_id
        )

        # Get general camera stream status
        camera_connection = await camera_service.get_camera_stream(device_id)
        is_connected = camera_connection is not None

        response = {
            "device_id": device_id,
            "camera_name": camera.name,
            "is_connected": is_connected,
            "mobile_stream_status": stream_status,
            "supports_streaming": camera.supports_streaming,
            "camera_type": camera.camera_type.value,
        }

        if stream_status:
            response.update(
                {
                    "is_streaming": stream_status.get("status") == "active",
                    "protocol": stream_status.get("protocol"),
                    "stream_url": f"/cameras/api/v1/streaming/{device_id}/video",
                }
            )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error getting mobile camera streaming status for {device_id}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get mobile camera streaming status",
        )


@router.post("/mobile/{device_id}/stop")
async def stop_mobile_streaming(
    device_id: str,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict:
    """Stop mobile camera streaming."""

    try:
        # Verify mobile camera exists
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

        # Stop mobile streaming service
        success = await mobile_streaming_service.stop_mobile_camera_stream(device_id)

        # Disconnect camera from general streaming service
        await camera_service.disconnect_camera(device_id)

        logger.info(
            f"User {current_user.get('sub')} stopped mobile camera streaming for {device_id}"
        )

        return {
            "device_id": device_id,
            "status": "stopped" if success else "error",
            "message": (
                "Mobile camera streaming stopped"
                if success
                else "Failed to stop mobile camera streaming"
            ),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error stopping mobile camera streaming for {device_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to stop mobile camera streaming",
        )
