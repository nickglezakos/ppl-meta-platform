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
from sqlalchemy.orm import Session
from src.database import get_db
from src.models.camera import Camera, CameraType
from src.security.auth import (
    get_current_user,
    get_current_user_flexible,
    require_start_stream,
    require_view_stream_flexible,
)
from src.services.camera_detection import camera_service
from src.services.mobile_streaming import mobile_streaming_service
from src.services.session_auth import session_manager

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
            "stream_url": f"/cameras/api/v1/streaming/{device_id}/video",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting stream for camera {device_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start stream",
        )


@router.get("/{device_id}/status")
async def get_streaming_status(
    device_id: str,
    current_user: Dict = Depends(require_view_stream_flexible),
) -> Dict:
    """Get streaming status for a specific camera."""

    try:
        # Check if camera is connected and streaming
        cap = await camera_service.get_camera_stream(device_id)
        is_streaming = cap is not None and cap.isOpened()

        # Get camera info from detected cameras
        camera_info = camera_service.detected_cameras.get(device_id)

        status_data = {
            "device_id": device_id,
            "is_streaming": is_streaming,
            "status": "streaming" if is_streaming else "stopped",
        }

        if is_streaming and cap:
            # Get current stream properties
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = int(cap.get(cv2.CAP_PROP_FPS))

            status_data.update(
                {
                    "stream_url": f"/cameras/api/v1/streaming/" f"{device_id}/video",
                    "resolution": f"{width}x{height}",
                    "fps": fps,
                }
            )

        if camera_info:
            status_data.update(
                {
                    "camera_name": camera_info.get("name", device_id),
                    "camera_type": camera_info.get("type", "Unknown"),
                }
            )

        logger.debug(f"Streaming status for {device_id}: {status_data}")
        return status_data

    except Exception as e:
        logger.error(f"Error getting streaming status for {device_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get streaming status for {device_id}",
        )


@router.get("/{device_id}/video")
async def video_stream(
    device_id: str,
    quality: str = "medium",
    current_user: Dict = Depends(require_view_stream_flexible),
    db: Session = Depends(get_db),
):
    """Stream video from camera."""

    # Check if this is a mobile camera
    camera = db.query(Camera).filter(Camera.device_id == device_id).first()
    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera {device_id} not found",
        )

    # Handle mobile cameras differently
    if camera.camera_type == CameraType.MOBILE:
        return await handle_mobile_camera_stream(device_id, quality, current_user)

    # Continue with regular camera streaming for non-mobile cameras


async def handle_mobile_camera_stream(device_id: str, quality: str, current_user: Dict):
    """Handle mobile camera streaming using the mobile streaming service."""

    async def generate_mobile_frames():
        """Generate video frames from mobile camera stream."""

        try:
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

            while True:
                # Get latest frame from mobile streaming service
                frame = await mobile_streaming_service.get_latest_mobile_frame(
                    device_id
                )

                if frame is None:
                    # No frame available, send a blank frame or wait
                    logger.debug(f"No frame available for mobile camera {device_id}")
                    await asyncio.sleep(0.1)  # Wait 100ms before trying again
                    continue

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
            logger.error(f"Error in mobile video stream for camera {device_id}: {e}")
            return

    try:
        logger.info(
            f"User {current_user.get('sub')} accessing mobile video stream for camera {device_id}"
        )

        return StreamingResponse(
            generate_mobile_frames(),
            media_type="multipart/x-mixed-replace; boundary=frame",
        )

    except Exception as e:
        logger.error(
            f"Error setting up mobile video stream for camera {device_id}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to setup mobile video stream",
        )

    async def generate_frames():
        """Generate video frames for streaming."""

        try:
            cap = await camera_service.get_camera_stream(device_id)
            if not cap:
                logger.info(
                    f"Camera {device_id} not connected, attempting to connect..."
                )
                # Try to connect the camera automatically
                connection = await camera_service.connect_camera(device_id)
                if not connection:
                    logger.error(
                        f"Failed to auto-connect camera {device_id} for streaming"
                    )
                    return
                cap = await camera_service.get_camera_stream(device_id)
                if not cap:
                    logger.error(
                        f"Camera {device_id} still not connected after auto-connect"
                    )
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


async def handle_mobile_camera_stream_session(
    device_id: str, session_id: str, quality: str
):
    """Handle mobile camera streaming using session-based authentication."""

    async def generate_mobile_frames():
        """Generate video frames from mobile camera stream with session validation."""

        try:
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

            logger.info(
                f"Session {session_id[:16]}... accessing mobile video stream "
                f"for camera {device_id} with quality {quality}"
            )

            while True:
                # Validate session is still active
                if not session_manager.validate_session(session_id, device_id):
                    logger.warning(
                        f"Session {session_id[:16]}... expired during mobile streaming"
                    )
                    break

                # Get latest frame from mobile streaming service
                frame = await mobile_streaming_service.get_latest_mobile_frame(
                    device_id
                )

                if frame is None:
                    # No frame available, send a blank frame or wait
                    logger.debug(f"No frame available for mobile camera {device_id}")
                    await asyncio.sleep(0.1)  # Wait 100ms before trying again
                    continue

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
            logger.error(
                f"Error in mobile video stream session for camera {device_id}: {e}"
            )
            return

    try:
        return StreamingResponse(
            generate_mobile_frames(),
            media_type="multipart/x-mixed-replace; boundary=frame",
        )

    except Exception as e:
        logger.error(
            f"Error setting up mobile video stream session for camera {device_id}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to setup mobile video stream session",
        )


@router.get("/{device_id}/video-session/{session_id}")
async def video_stream_session(
    device_id: str,
    session_id: str,
    quality: str = "medium",
    db: Session = Depends(get_db),
):
    """Stream video from camera using session-based authentication."""  # Validate session
    session = session_manager.validate_session(session_id, device_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired streaming session",
        )

    # Check if this is a mobile camera
    camera = db.query(Camera).filter(Camera.device_id == device_id).first()
    if camera and camera.camera_type == CameraType.MOBILE:
        return await handle_mobile_camera_stream_session(device_id, session_id, quality)

    # Continue with regular camera streaming for non-mobile cameras

    async def generate_frames():
        """Generate video frames for streaming."""
        try:
            cap = await camera_service.get_camera_stream(device_id)
            if not cap:
                logger.info(
                    "Camera %s not connected, attempting to connect...", device_id
                )
                # Try to connect the camera automatically
                connection = await camera_service.connect_camera(device_id)
                if not connection:
                    logger.error(
                        "Failed to auto-connect camera %s for streaming", device_id
                    )
                    return
                cap = await camera_service.get_camera_stream(device_id)
                if not cap:
                    logger.error(
                        "Camera %s still not connected after auto-connect", device_id
                    )
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

            logger.info(
                "Session %s accessing video stream for camera %s with quality %s",
                session_id[:16] + "...",
                device_id,
                quality,
            )

            while True:
                # Validate session is still active (check every few frames)
                if not session_manager.validate_session(session_id, device_id):
                    logger.warning(
                        "Session %s expired during streaming", session_id[:16] + "..."
                    )
                    break

                ret, frame = cap.read()
                if not ret:
                    logger.warning("Failed to read frame from camera %s", device_id)
                    await asyncio.sleep(0.1)
                    continue

                # Encode frame as JPEG
                _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                frame_bytes = buffer.tobytes()

                # Yield frame in multipart format
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
                )

                # Control frame rate
                await asyncio.sleep(1.0 / fps)

        except Exception as e:
            logger.error(
                "Error in session video stream for camera %s: %s", device_id, str(e)
            )
            yield (
                b"--frame\r\n"
                b"Content-Type: text/plain\r\n\r\n"
                b"Stream error occurred\r\n"
            )

    try:
        return StreamingResponse(
            generate_frames(), media_type="multipart/x-mixed-replace; boundary=frame"
        )
    except Exception as e:
        logger.error(
            "Error setting up session video stream for camera %s: %s", device_id, str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error setting up session video stream for camera {device_id}: {e}",
        )


@router.post("/{device_id}/snapshot")
async def capture_custom_snapshot(
    request: Request, device_id: str, settings: Dict = None
) -> Dict:
    """Capture snapshot with custom resolution and quality settings."""

    try:
        # Get current user from request
        current_user = await get_current_user_flexible(request)

        # Parse request body for settings
        if settings is None:
            try:
                body = await request.body()
                if body:
                    import json

                    settings = json.loads(body.decode())
                else:
                    settings = {}
            except Exception:
                settings = {}

        # Default settings
        default_settings = {
            "resolution": "max",
            "quality": 95,
            "format": "JPEG",
            "save_to_file": True,
            "filename": None,
        }

        # Merge with provided settings
        final_settings = {**default_settings, **settings}

        # Validate settings
        from src.models.snapshot_settings import SnapshotSettings

        try:
            validated_settings = SnapshotSettings(**final_settings)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid snapshot settings: {e}",
            )

        # Capture high-resolution frame
        result = await camera_service.capture_high_res_snapshot(
            device_id, validated_settings.dict()
        )

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Camera {device_id} not connected or failed to capture",
            )

        ret, frame, metadata = result
        if not ret or frame is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to capture high-resolution frame",
            )

        # Encode frame with custom quality and format
        if validated_settings.format.upper() == "JPEG":
            encode_params = [cv2.IMWRITE_JPEG_QUALITY, validated_settings.quality]
            extension = ".jpg"
            mime_type = "image/jpeg"
        elif validated_settings.format.upper() == "PNG":
            # PNG compression level (0-9, where 9 is max compression)
            png_compression = max(0, min(9, (100 - validated_settings.quality) // 10))
            encode_params = [cv2.IMWRITE_PNG_COMPRESSION, png_compression]
            extension = ".png"
            mime_type = "image/png"
        else:  # BMP
            encode_params = []
            extension = ".bmp"
            mime_type = "image/bmp"

        _, buffer = cv2.imencode(extension, frame, encode_params)
        frame_base64 = base64.b64encode(buffer.tobytes()).decode("utf-8")

        # Generate filename
        import time

        if validated_settings.filename:
            filename = validated_settings.filename
            if not filename.endswith(extension):
                filename += extension
        else:
            timestamp = int(time.time())
            filename = f"snapshot_{device_id}_{timestamp}{extension}"

        # Save to file if requested
        file_path = None
        if validated_settings.save_to_file:
            import os

            snapshots_dir = "snapshots"
            os.makedirs(snapshots_dir, exist_ok=True)
            file_path = os.path.join(snapshots_dir, filename)

            with open(file_path, "wb") as f:
                f.write(buffer.tobytes())

        # Get actual resolution from frame
        actual_height, actual_width = frame.shape[:2]

        logger.info(
            f"User {current_user.get('sub')} captured enhanced snapshot "
            f"from camera {device_id} at {actual_width}x{actual_height}"
        )

        return {
            "status": "success",
            "message": "Enhanced snapshot captured successfully",
            "device_id": device_id,
            "snapshot_data": {
                "filename": filename,
                "file_size_bytes": len(buffer.tobytes()),
                "resolution": {"width": actual_width, "height": actual_height},
                "format": validated_settings.format.upper(),
                "quality": validated_settings.quality,
                "captured_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "settings": validated_settings.dict(),
                "metadata": metadata,
            },
            "base64_image": f"data:{mime_type};base64,{frame_base64}",
            "download_url": (
                f"/api/v1/streaming/{device_id}/snapshot/{filename}"
                if file_path
                else None
            ),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error capturing enhanced snapshot from camera {device_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to capture enhanced snapshot",
        )


@router.get("/{device_id}/capabilities")
async def get_camera_capabilities(request: Request, device_id: str) -> Dict:
    """Get camera capabilities including supported resolutions."""

    try:
        # Get current user from request
        current_user = await get_current_user_flexible(request)

        # Get camera capabilities
        capabilities = await camera_service.get_camera_capabilities(device_id)

        if not capabilities:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Camera {device_id} not found or capabilities unavailable",
            )

        logger.info(
            f"User {current_user.get('sub')} requested capabilities "
            f"for camera {device_id}"
        )

        return {
            "status": "success",
            "device_id": device_id,
            "capabilities": capabilities,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting capabilities for camera {device_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get camera capabilities",
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
        # Actually disconnect the camera to stop the stream
        success = await camera_service.disconnect_camera(device_id)

        if success:
            logger.info(
                f"User {current_user.get('sub')} stopped stream for "
                f"camera {device_id}"
            )
            return {
                "device_id": device_id,
                "status": "stopped",
                "message": f"Stream stopped for camera {device_id}",
            }
        else:
            logger.warning(f"Camera {device_id} was not connected")
            return {
                "device_id": device_id,
                "status": "stopped",
                "message": f"Camera {device_id} was already stopped",
            }

    except Exception as e:
        logger.error(f"Error stopping stream for camera {device_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to stop stream",
        )
