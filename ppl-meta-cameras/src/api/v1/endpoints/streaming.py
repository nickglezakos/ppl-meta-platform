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
from src.models.camera import Camera, CameraType
from src.security.auth import (
    get_current_user,
    get_current_user_flexible,
    require_start_stream,
    require_view_stream_flexible,
    security,
)
from src.services.camera_detection import camera_service
from src.services.mobile_streaming import mobile_streaming_service
from src.services.session_auth import session_manager
from src.services.session_aware_face_detector import session_aware_face_detector
from src.services.streaming_session_manager import streaming_session_manager

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/{device_id}/start", dependencies=[Depends(require_start_stream)])
async def start_stream(
    device_id: str, current_user: Dict = Depends(get_current_user)
) -> Dict:
    """Start streaming from a specific camera."""

    try:
        # For USB cameras, always force a fresh connection to avoid black screen issues
        # after stopping and restarting streams
        existing_connection = await camera_service.get_camera_stream(device_id)
        if existing_connection:
            # Disconnect first to ensure fresh connection
            await camera_service.disconnect_camera(device_id)

        # Connect to camera with a fresh connection
        connection = await camera_service.connect_camera(device_id)
        if not connection:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to connect to camera {device_id}",
            )

        logger.info(
            "User %s started stream for camera %s (fresh connection)",
            current_user.get("sub"),
            device_id,
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
    """Stream video from camera with integrated session management."""

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

    # Continue with regular camera streaming for non-mobile cameras with session support

    async def generate_frames():
        """Generate video frames for streaming with face detection and session tracking."""

        session_uuid = None

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

            # Create streaming session for USB camera
            session_uuid = await streaming_session_manager.create_streaming_session(
                device_id=device_id,
                camera_device_uuid=camera.device_id,
                session_metadata={
                    "camera_type": "usb",
                    "quality": quality,
                    "stream_type": "http_mjpeg",
                },
            )

            logger.info(
                f"✅ Created USB camera streaming session {session_uuid} for device {device_id}"
            )

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

            frame_count = 0
            while True:
                ret, frame = cap.read()
                if not ret:
                    logger.warning(f"Failed to read frame from camera {device_id}")
                    break

                # Cache the frame for recording use
                camera_service.latest_frames[device_id] = (ret, frame.copy())

                # Perform session-aware face detection on every 5th frame to balance performance
                if frame_count % 5 == 0 and session_uuid:
                    try:
                        detection_result = (
                            await session_aware_face_detector.detect_faces_with_session(
                                frame=frame,
                                session_uuid=session_uuid,
                                device_id=device_id,
                                method="two_stage",
                                confidence_threshold=0.7,
                                frame_metadata={
                                    "frame_count": frame_count,
                                    "frame_size": frame.shape,
                                    "stream_type": "usb_mjpeg",
                                },
                            )
                        )

                        # Update session with detection results
                        await streaming_session_manager.update_session_detection(
                            device_id=device_id,
                            faces_detected=detection_result["faces_detected"],
                            frame_metadata=detection_result["frame_metadata"],
                        )

                        if detection_result["face_count"] > 0:
                            logger.debug(
                                f"🔍 USB Camera {device_id}: detected {detection_result['face_count']} faces in frame {frame_count}"
                            )

                    except Exception as detection_error:
                        logger.error(
                            f"❌ Face detection error for USB camera {device_id}: {detection_error}"
                        )

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

                frame_count += 1

                # Small delay to control frame rate
                await asyncio.sleep(1.0 / fps)

        except Exception as e:
            logger.error(f"Error in video stream for camera {device_id}: {e}")
            return
        finally:
            # Complete session when stream ends
            if session_uuid:
                await streaming_session_manager.complete_streaming_session(
                    device_id=device_id, completion_reason="stream_ended"
                )
                logger.info(f"✅ Completed USB camera streaming session {session_uuid}")

                # Cleanup session-aware detector session
                session_aware_face_detector.cleanup_session(session_uuid)

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
                # Get latest frame data from mobile streaming service
                frame_data = (
                    await mobile_streaming_service.get_latest_mobile_frame_data(
                        device_id
                    )
                )

                if frame_data is None:
                    # No frame available, send a blank frame or wait
                    logger.debug(f"No frame available for mobile camera {device_id}")
                    await asyncio.sleep(0.1)  # Wait 100ms before trying again
                    continue

                frame = frame_data["frame"]
                rotation_angle = frame_data.get("rotation_angle", 0)
                orientation = frame_data.get("orientation", "portraitUp")

                logger.info(
                    f"🔄 [ROTATION_DEBUG] Processing frame - "
                    f"orientation: {orientation}, rotation_angle: {rotation_angle}"
                )
                logger.info(f"🔄 [ROTATION_DEBUG] Original frame shape: {frame.shape}")

                # Apply rotation to frame based on orientation metadata
                if rotation_angle != 0:
                    logger.info(
                        f"🔄 [ROTATION_DEBUG] Applying {rotation_angle}° "
                        f"rotation to frame"
                    )
                    original_shape = frame.shape
                    # Rotate frame based on rotation angle
                    if rotation_angle == 90:
                        frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
                        logger.info(
                            "🔄 [ROTATION_DEBUG] Applied 90° clockwise rotation"
                        )
                    elif rotation_angle == 180:
                        frame = cv2.rotate(frame, cv2.ROTATE_180)
                        logger.info("🔄 [ROTATION_DEBUG] Applied 180° rotation")
                    elif rotation_angle == 270:
                        frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
                        logger.info(
                            "🔄 [ROTATION_DEBUG] Applied 270° (90° counter-clockwise) rotation"
                        )
                    else:
                        logger.warning(
                            f"🔄 [ROTATION_DEBUG] Unknown rotation angle: {rotation_angle}"
                        )

                    logger.info(
                        f"🔄 [ROTATION_DEBUG] Frame shape after rotation: {frame.shape} (was: {original_shape})"
                    )
                    logger.info("🔄 [ROTATION_DEBUG] Frame rotated successfully")
                else:
                    logger.info(
                        "🔄 [ROTATION_DEBUG] No rotation needed " "(rotation_angle = 0)"
                    )

                # Resize frame if needed (after rotation)
                if frame.shape[1] != width or frame.shape[0] != height:
                    frame = cv2.resize(frame, (width, height))

                # Encode frame as JPEG
                _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                frame_bytes = buffer.tobytes()

                # Yield frame in standard multipart format (no need for orientation headers now)
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

                # Cache the frame for recording use
                camera_service.latest_frames[device_id] = (ret, frame.copy())

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

                # Get latest frame data from mobile streaming service
                frame_data = (
                    await mobile_streaming_service.get_latest_mobile_frame_data(
                        device_id
                    )
                )

                if frame_data is None:
                    # No frame available, send a blank frame or wait
                    logger.debug(f"No frame available for mobile camera {device_id}")
                    await asyncio.sleep(0.1)  # Wait 100ms before trying again
                    continue

                frame = frame_data["frame"]
                rotation_angle = frame_data.get("rotation_angle", 0)
                orientation = frame_data.get("orientation", "portraitUp")

                logger.info(
                    f"🔄 [ROTATION_DEBUG_SESSION] Processing frame - "
                    f"orientation: {orientation}, rotation_angle: {rotation_angle}"
                )

                # Apply rotation to frame based on orientation metadata
                if rotation_angle != 0:
                    logger.info(
                        f"🔄 [ROTATION_DEBUG_SESSION] Applying {rotation_angle}° "
                        f"rotation to frame"
                    )
                    # Rotate frame based on rotation angle
                    if rotation_angle == 90:
                        frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
                    elif rotation_angle == 180:
                        frame = cv2.rotate(frame, cv2.ROTATE_180)
                    elif rotation_angle == 270:
                        frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
                    logger.info(
                        "🔄 [ROTATION_DEBUG_SESSION] Frame rotated successfully"
                    )
                else:
                    logger.info(
                        "🔄 [ROTATION_DEBUG_SESSION] No rotation needed "
                        "(rotation_angle = 0)"
                    )

                # Resize frame if needed (after rotation)
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

                # Cache the frame for recording use
                camera_service.latest_frames[device_id] = (ret, frame.copy())

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
        # Clean up any active streaming sessions for this device
        cleaned_sessions = session_manager.cleanup_sessions_for_device(device_id)

        # Actually disconnect the camera to stop the stream
        success = await camera_service.disconnect_camera(device_id)

        if success:
            logger.info(
                "User %s stopped stream for camera %s, cleaned %d sessions",
                current_user.get("sub"),
                device_id,
                cleaned_sessions,
            )
            return {
                "device_id": device_id,
                "status": "stopped",
                "message": f"Stream stopped for camera {device_id}",
                "sessions_cleaned": cleaned_sessions,
            }
        else:
            logger.warning("Camera %s was not connected", device_id)
            return {
                "device_id": device_id,
                "status": "stopped",
                "message": f"Camera {device_id} was already stopped",
                "sessions_cleaned": cleaned_sessions,
            }

    except Exception as e:
        logger.error("Error stopping stream for camera %s: %s", device_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to stop stream",
        ) from e


@router.post("/{device_id}/record/start")
async def start_recording(
    device_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict:
    """Start recording from a specific camera to collection."""

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

        # Check if already recording
        existing_recording = camera_service.get_active_recording(device_id)
        if existing_recording:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Camera {device_id} is already recording",
            )

        # Start recording
        recording_info = await camera_service.start_recording(
            device_id=device_id,
            user_id=current_user.get("sub") or "",
            quality="high",  # TODO: Make configurable
            auth_token=credentials.credentials,
        )

        if not recording_info:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to start recording for camera {device_id}",
            )

        logger.info(
            f"User {current_user.get('sub')} started recording for camera {device_id}"
        )

        return {
            "status": "success",
            "message": f"Recording started for camera {device_id}",
            "device_id": device_id,
            "recording_id": recording_info.get("recording_id"),
            "started_at": recording_info.get("started_at"),
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

        return {
            "status": "success",
            "message": f"Recording stopped for camera {device_id}",
            "device_id": device_id,
            "recording_id": recording_result.get("recording_id"),
            "duration_seconds": recording_result.get("duration_seconds"),
            "file_path": recording_result.get("file_path"),
            "file_size_bytes": recording_result.get("file_size_bytes"),
            "collection_id": recording_result.get("collection_id"),
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
