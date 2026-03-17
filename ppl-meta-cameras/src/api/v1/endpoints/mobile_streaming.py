"""
Mobile camera specific streaming endpoints for PPL Meta Cameras API.
Extends the base streaming functionality with mobile-specific features.
"""

import base64
import io
import logging
from typing import Dict

import cv2
import numpy as np
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from PIL import Image
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
            permissions=["cameras:stream:view", "cameras:stream:start"],
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


class MobileFrameData(BaseModel):
    """Model for mobile camera frame data."""

    device_id: str
    frame_data: str  # Base64 encoded image data
    timestamp: float
    width: int
    height: int
    format: str = "jpeg"
    # Orientation metadata
    orientation: str = "portraitUp"  # portraitUp, landscapeLeft, etc.
    rotation_angle: int = 0  # 0, 90, 180, 270 degrees
    # Frame rate metadata (CRITICAL for accurate video recording)
    fps: int = 30  # Frames per second the mobile app is sending at (default 30)


@router.post("/mobile/{device_id}/frame")
async def receive_mobile_camera_frame(
    device_id: str,
    frame_data: MobileFrameData,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict:
    """Receive a video frame from a mobile camera."""

    try:
        logger.debug(f"📱 [FRAME_DEBUG] Received frame from mobile camera {device_id}")
        logger.debug(
            f"📱 [FRAME_DEBUG] Frame metadata - orientation: {frame_data.orientation}, rotation_angle: {frame_data.rotation_angle}"
        )
        logger.debug(
            f"📱 [FRAME_DEBUG] Raw frame data received - timestamp: {frame_data.timestamp}"
        )

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

        # Decode base64 frame data
        try:
            frame_bytes = base64.b64decode(frame_data.frame_data)

            # Convert to numpy array for processing
            # Store as RGB (JPEG format), convert to BGR later when needed
            image = Image.open(io.BytesIO(frame_bytes))
            frame = np.array(image)

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid frame data: {e}",
            )

        # Store the frame in the mobile streaming service with orientation and FPS
        success = await mobile_streaming_service.receive_mobile_frame(
            device_id,
            frame,
            frame_data.timestamp,
            frame_data.orientation,
            frame_data.rotation_angle,
            frame_data.fps,  # Pass the actual FPS from mobile device
        )

        if success:
            return {
                "device_id": device_id,
                "status": "received",
                "message": "Frame received successfully",
                "timestamp": frame_data.timestamp,
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to process mobile camera frame",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error receiving mobile camera frame for {device_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to receive mobile camera frame",
        )


@router.get("/mobile/{device_id}/current-frame")
async def get_mobile_current_frame(
    device_id: str,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict:
    """Get the current frame from a mobile camera with orientation metadata."""

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

        # Get latest frame data from mobile streaming service
        frame_data = await mobile_streaming_service.get_latest_mobile_frame_data(
            device_id
        )

        if frame_data is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No frame available",
            )

        frame = frame_data["frame"]
        orientation = frame_data.get("orientation", "portraitUp")
        rotation_angle = frame_data.get("rotation_angle", 0)
        timestamp = frame_data.get("timestamp", 0)

        # Apply rotation to frame for proper display
        if rotation_angle != 0:
            if rotation_angle == 90:
                frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
            elif rotation_angle == 180:
                frame = cv2.rotate(frame, cv2.ROTATE_180)
            elif rotation_angle == 270:
                frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
            logger.debug(f"📱 Rotated frame by {rotation_angle}° for {device_id}")

        # Encode frame as base64 JPEG
        _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        frame_base64 = base64.b64encode(buffer.tobytes()).decode("utf-8")

        return {
            "device_id": device_id,
            "frame_data": frame_base64,
            "orientation": orientation,
            "rotation_angle": rotation_angle,
            "timestamp": timestamp,
            "width": frame.shape[1],
            "height": frame.shape[0],
            "format": "jpeg",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting mobile camera frame for {device_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get mobile camera frame",
        )


@router.post("/mobile/{device_id}/streaming-session")
async def create_mobile_streaming_session(
    device_id: str,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict:
    """Create a streaming session for a mobile camera (browser-compatible)."""

    try:
        # Verify this is a mobile camera
        camera = db.query(Camera).filter(Camera.device_id == device_id).first()
        if not camera:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Camera {device_id} not found",
            )

        if camera.camera_type != CameraType.MOBILE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Camera {device_id} is not a mobile camera",
            )

        # Create streaming session for browser access
        from src.services.session_auth import session_manager

        session_id = session_manager.create_session(
            user_id=current_user.get("sub"),
            device_id=device_id,
            permissions=["cameras:stream:view"],
        )

        logger.info(
            f"User {current_user.get('sub')} created mobile streaming session for {device_id}"
        )

        return {
            "session_id": session_id,
            "device_id": device_id,
            "stream_url": f"/cameras/api/v1/streaming/{device_id}/video-session/{session_id}",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating mobile streaming session for {device_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create mobile streaming session",
        )
