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
from src.security.auth import (
    get_current_user,
    get_current_user_flexible,
    require_start_stream,
    require_view_stream_flexible,
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
