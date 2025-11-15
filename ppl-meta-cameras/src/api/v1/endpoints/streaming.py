"""
Streaming endpoints for PPL Meta Cameras API.
"""

import asyncio
import base64
import io
import logging
from typing import Dict

import cv2
import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from src.database import get_db
from src.models.camera import Camera
from src.security.auth import (
    get_current_user,
    get_current_user_flexible,
    require_start_stream,
    require_view_stream_flexible,
    security,
)
from src.services.camera_detection import camera_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/{device_id}/start", dependencies=[Depends(require_start_stream)])
async def start_stream(
    device_id: str, current_user: Dict = Depends(get_current_user)
) -> Dict:
    """Start streaming from a specific camera."""

    try:
        # Connect to camera if not already connected
        connection = await camera_service.get_camera_stream(device_id)
        if not connection:
            connection = await camera_service.connect_camera(device_id)
            if not connection:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to connect to camera {device_id}",
                )

        logger.info(
            f"User {current_user.get('sub')} started stream for camera {device_id}"
        )

        return {
            "device_id": device_id,
            "status": "streaming",
            "message": f"Stream started for camera {device_id}",
            "stream_url": f"/api/v1/streaming/{device_id}/video",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting stream for camera {device_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start stream",
        )


@router.get("/{device_id}/video")
async def video_stream(
    device_id: str,
    quality: str = "medium",
    current_user: Dict = Depends(require_view_stream_flexible),
):
    """Stream video from camera."""

    async def generate_frames():
        """Generate video frames for streaming."""

        try:
            cap = await camera_service.get_camera_stream(device_id)
            if not cap:
                logger.error(f"Camera {device_id} not connected for streaming")
                return

            # Set quality parameters
            quality_settings = {
                "low": (320, 240, 15),
                "medium": (640, 480, 30),
                "high": (1280, 720, 30),
                "ultra": (1920, 1080, 30),
            }

            width, height, fps = quality_settings.get(
                quality, quality_settings["medium"]
            )

            # Set camera properties
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            cap.set(cv2.CAP_PROP_FPS, fps)

            while True:
                ret, frame = cap.read()
                if not ret:
                    logger.warning(f"Failed to read frame from camera {device_id}")
                    break

                # Resize frame if needed
                if frame.shape[1] != width or frame.shape[0] != height:
                    frame = cv2.resize(frame, (width, height))

                # Encode frame as JPEG
                _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                frame_bytes = buffer.tobytes()

                # Yield frame in multipart format
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
                )

                # Small delay to control frame rate
                await asyncio.sleep(1.0 / fps)

        except Exception as e:
            logger.error(f"Error in video stream for camera {device_id}: {e}")
            return

    try:
        # Check if camera is connected
        cap = await camera_service.get_camera_stream(device_id)
        if not cap:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Camera {device_id} not connected",
            )

        logger.info(
            f"User {current_user.get('sub')} accessing video stream for camera {device_id}"
        )

        return StreamingResponse(
            generate_frames(), media_type="multipart/x-mixed-replace; boundary=frame"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting up video stream for camera {device_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to setup video stream",
        )


@router.get(
    "/{device_id}/snapshot", dependencies=[Depends(require_view_stream_flexible)]
)
async def capture_snapshot(request: Request, device_id: str) -> Dict:
    """Capture a single snapshot from camera."""

    try:
        # Get current user from request
        current_user = await get_current_user_flexible(request)

        # Capture frame
        result = await camera_service.capture_frame(device_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    f"Camera {device_id} not connected or " "failed to capture frame"
                ),
            )

        ret, frame = result
        if not ret or frame is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to capture frame from camera",
            )

        # Encode frame as base64 JPEG
        _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
        frame_base64 = base64.b64encode(buffer.tobytes()).decode("utf-8")

        logger.info(
            f"User {current_user.get('sub')} captured snapshot "
            f"from camera {device_id}"
        )

        return {
            "device_id": device_id,
            "timestamp": asyncio.get_event_loop().time(),
            "format": "jpeg",
            "size": {"width": frame.shape[1], "height": frame.shape[0]},
            "data": f"data:image/jpeg;base64,{frame_base64}",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error capturing snapshot from camera {device_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to capture snapshot",
        )


@router.post("/{device_id}/stop", dependencies=[Depends(require_start_stream)])
async def stop_stream(
    device_id: str, current_user: Dict = Depends(get_current_user)
) -> Dict:
    """Stop streaming from a specific camera."""

    try:
        # For now, we'll just keep the connection but log the stop request
        # In a full implementation, you might track active streams separately

        logger.info(
            f"User {current_user.get('sub')} stopped stream for camera {device_id}"
        )

        return {
            "device_id": device_id,
            "status": "stopped",
            "message": f"Stream stopped for camera {device_id}",
        }

    except Exception as e:
        logger.error(f"Error stopping stream for camera {device_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to stop stream",
        )


@router.post("/{device_id}/record/start")
async def start_recording(
    device_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict:
    """Start recording from a specific camera with session tracking."""

    try:
        # Verify camera exists and supports recording
        camera = db.query(Camera).filter(Camera.device_id == device_id).first()
        if not camera:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Camera {device_id} not found",
            )

        if not camera.supports_recording:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Camera {device_id} does not support recording",
            )

        # Check if already recording using both old and new systems
        existing_recording = camera_service.get_active_recording(device_id)
        active_session = camera.get_active_recording_session()

        if existing_recording or active_session:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Camera {device_id} is already recording",
            )

        # Create recording session first
        from src.services.recording_session_service import RecordingSessionService

        session_service = RecordingSessionService(db)

        # Get recording configuration (with segment support)
        recording_config = {
            "quality": "high",
            "segment_duration_seconds": 30,  # Default segment duration
            "auto_face_detection_enabled": True,
            "video_codec": "h264",
            "audio_enabled": False,
            "face_detection_method": "enhanced-v2",
            "quality_preset": "balanced",
        }

        # Create recording session
        recording_session = session_service.create_session(
            camera_device_id=device_id,
            user_id=current_user.get("sub") or "",
            recording_config=recording_config,
        )

        # Start recording with session tracking
        recording_info = await camera_service.start_recording_with_session(
            device_id=device_id,
            user_id=current_user.get("sub") or "",
            quality="high",
            auth_token=credentials.credentials,
            session_uuid=recording_session.session_uuid,
            segment_duration=recording_config["segment_duration_seconds"],
        )

        if not recording_info:
            # If recording fails, mark session as failed
            session_service.update_session_status(
                recording_session.session_uuid, "failed"
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to start recording for camera {device_id}",
            )

        logger.info(
            f"User {current_user.get('sub')} started recording session "
            f"{recording_session.session_uuid} for camera {device_id}"
        )

        # Notify VMeta service of recording start for polling activation
        try:
            import httpx
            from datetime import datetime
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(
                    "http://localhost:8008/api/v1/recording/started",
                    json={
                        "collection_id": device_id,
                        "session_uuid": recording_session.session_uuid,
                        "device_id": device_id,
                        "user_id": current_user.get("sub") or "",
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                        "metadata": {}
                    },
                    headers={"Authorization": f"Bearer {credentials.credentials}"}
                )
                logger.info(
                    f"📹 Notified VMeta of recording start: {recording_session.session_uuid}"
                )
        except Exception as e:
            logger.warning(f"Failed to notify VMeta of recording start: {e}")
            # Don't fail the recording if VMeta notification fails

        return {
            "status": "success",
            "message": f"Recording started for camera {device_id}",
            "device_id": device_id,
            "session_uuid": recording_session.session_uuid,
            "recording_id": recording_info.get("recording_id"),
            "started_at": recording_info.get("started_at"),
            "segment_duration": recording_config["segment_duration_seconds"],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error starting recording for camera %s: %s", device_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start recording",
        ) from e


@router.post("/{device_id}/record/stop")
async def stop_recording(
    device_id: str,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict:
    """Stop recording from a specific camera and save to collection."""

    try:
        # Verify camera exists
        camera = db.query(Camera).filter(Camera.device_id == device_id).first()
        if not camera:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Camera {device_id} not found",
            )

        # Stop recording and get recording info
        recording_result = await camera_service.stop_recording(
            device_id=device_id, user_id=current_user.get("sub")
        )

        if not recording_result:
            # Camera might not be recording
            return {
                "status": "success",
                "message": f"Camera {device_id} was not recording",
                "device_id": device_id,
            }

        logger.info(
            f"User {current_user.get('sub')} stopped recording for camera {device_id} - "
            f"Duration: {recording_result.get('duration_seconds')}s, "
            f"File: {recording_result.get('file_path')}"
        )

        # Notify VMeta service of recording stop for final batch processing
        try:
            import httpx
            from datetime import datetime
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(
                    "http://localhost:8008/api/v1/recording/stopped",
                    json={
                        "collection_id": device_id,
                        "session_uuid": recording_result.get("session_uuid", ""),
                        "device_id": device_id,
                        "user_id": current_user.get("sub") or "",
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                        "video_count": recording_result.get("segment_count", 0),
                        "metadata": {
                            "duration_seconds": recording_result.get("duration_seconds"),
                            "file_size_bytes": recording_result.get("file_size_bytes")
                        }
                    }
                )
                logger.info(
                    f"🛑 Notified VMeta of recording stop: {recording_result.get('session_uuid')} "
                    f"({recording_result.get('segment_count', 0)} videos)"
                )
        except Exception as e:
            logger.warning(f"Failed to notify VMeta of recording stop: {e}")
            # Don't fail the stop operation if VMeta notification fails

        return {
            "status": "success",
            "message": f"Recording stopped for camera {device_id}",
            "device_id": device_id,
            "recording_id": recording_result.get("recording_id"),
            "session_uuid": recording_result.get("session_uuid"),
            "duration_seconds": recording_result.get("duration_seconds"),
            "file_path": recording_result.get("file_path"),
            "file_size_bytes": recording_result.get("file_size_bytes"),
            "collection_id": recording_result.get("collection_id"),
            "segment_count": recording_result.get("segment_count"),
            "segment_files": recording_result.get("segment_files"),
            "session_dir": recording_result.get("session_dir"),
            "stopped_at": recording_result.get("stopped_at"),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error stopping recording for camera %s: %s", device_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to stop recording",
        ) from e


@router.get("/{device_id}/record/status")
async def get_recording_status(
    device_id: str,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict:
    """Get recording status for a specific camera."""

    try:
        # Verify camera exists
        camera = db.query(Camera).filter(Camera.device_id == device_id).first()
        if not camera:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Camera {device_id} not found",
            )

        # Get recording status
        recording_status = camera_service.get_recording_status(device_id)

        return {
            "device_id": device_id,
            "is_recording": recording_status.get("is_recording", False),
            "recording_id": recording_status.get("recording_id"),
            "started_at": recording_status.get("started_at"),
            "duration_seconds": recording_status.get("duration_seconds", 0),
            "file_size_bytes": recording_status.get("file_size_bytes", 0),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting recording status for camera %s: %s", device_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get recording status",
        ) from e


@router.get("/{device_id}/record/debug")
async def debug_recording_state(
    device_id: str,
    current_user: Dict = Depends(get_current_user),
) -> Dict:
    """Debug endpoint to inspect recording state inconsistencies."""
    try:
        debug_info = camera_service.get_debug_recording_state(device_id)
        return debug_info
    except Exception as e:
        logger.error(
            "Error getting debug recording state for camera %s: %s", device_id, e
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get debug recording state",
        ) from e


@router.post("/{device_id}/record/clear-state")
async def clear_recording_state(
    device_id: str,
    current_user: Dict = Depends(get_current_user),
) -> Dict:
    """Debug endpoint to clear stale recording state."""
    try:
        result = camera_service.clear_stale_recording_state(device_id)
        return result
    except Exception as e:
        logger.error("Error clearing recording state for camera %s: %s", device_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear recording state",
        ) from e
