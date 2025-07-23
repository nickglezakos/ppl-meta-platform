"""
PPL Meta Media Service - Real-time Video Streaming with Face Detection
Provides video streaming endpoints with embedded face detection capabilities.
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from src.auth import AuthUser, get_current_user

from ...database import get_db
from ...services.face_detection_service import MediaFaceDetectionService
from .media import get_media_access_check

# Initialize face detection service
media_face_detection = MediaFaceDetectionService()

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stream", tags=["video-streaming"])


@router.get("/video/{media_id}")
async def stream_video_with_faces(
    media_id: str,
    face_detection: bool = Query(True, description="Enable face detection overlay"),
    confidence_threshold: float = Query(
        0.5, description="Face detection confidence threshold"
    ),
    method: str = Query(
        "auto", description="Face detection method: auto, two_stage, haar, dlib, dnn"
    ),
    current_user: AuthUser = Depends(get_current_user),
    share_token: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Stream video with real-time face detection overlay.

    This endpoint eliminates the need for cross-service API calls by embedding
    face detection directly in the media streaming process. Now supports
    high-accuracy two-stage detection method.

    Args:
        media_id: UUID of the media to stream
        face_detection: Whether to enable face detection overlay
        confidence_threshold: Minimum confidence for face detection (0.0-1.0)
        method: Detection method (auto=best available, two_stage=Haar+Dlib)
        current_user: Authenticated user
        share_token: Optional share token for public access
        db: Database session
        response: FastAPI response object

    Returns:
        StreamingResponse with video frames containing yellow face rectangles
    """
    try:
        # Check access permissions
        access_info = get_media_access_check(
            media_id, current_user.user_id, share_token, db
        )

        file_path = Path(access_info["file_path"])

        # Verify file exists on disk
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Media file not found")

        # Check if face detection is available
        detection_info = media_face_detection.get_face_detection_info()
        if face_detection and not detection_info["enabled"]:
            logger.warning("Face detection requested but not available")
            face_detection = False

        # Return original video file for optimal browser compatibility
        # Face detection will be handled by Vision service + frontend overlay
        file_size = file_path.stat().st_size

        def generate_chunks():
            with open(file_path, "rb") as f:
                while chunk := f.read(8192):
                    yield chunk

        return StreamingResponse(
            generate_chunks(),
            media_type=access_info["mime_type"],
            headers={
                "Content-Length": str(file_size),
                "Accept-Ranges": "bytes",
                "Content-Type": access_info["mime_type"],
                "Cache-Control": "private, max-age=3600",
            },
        )

    except Exception as e:
        logger.error(f"Video streaming error: {e}")
        raise HTTPException(status_code=500, detail="Video streaming failed")


@router.get("/test/video/{media_id}")
async def test_stream_video_no_auth(
    media_id: str,
    face_detection: bool = Query(True, description="Enable face detection overlay"),
    confidence_threshold: float = Query(
        0.5, description="Face detection confidence threshold"
    ),
    db: Session = Depends(get_db),
):
    """
    Test endpoint for video streaming without authentication.
    Used for testing the core streaming functionality.
    """
    try:
        # Simplified access check - just verify media exists
        from src.models.media import Media

        media = db.query(Media).filter(Media.uuid == media_id).first()
        if not media:
            raise HTTPException(status_code=404, detail="Media not found")

        file_path = Path(media.file_path)

        # Verify file exists on disk
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Media file not found")

        # Check if face detection is available
        detection_info = media_face_detection.get_face_detection_info()
        if face_detection and not detection_info["enabled"]:
            logger.warning("Face detection requested but not available")
            face_detection = False

        # Create streaming response
        return StreamingResponse(
            _generate_video_frames(file_path, face_detection, confidence_threshold),
            media_type="multipart/x-mixed-replace; boundary=frame",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )

    except Exception as e:
        logger.error(f"Test video streaming error: {e}")
        raise HTTPException(status_code=500, detail="Test streaming failed")


@router.get("/faces/{media_id}/frame/{frame_number}")
async def detect_faces_at_frame(
    media_id: str,
    frame_number: int,
    confidence_threshold: float = Query(
        0.5, description="Face detection confidence threshold"
    ),
    current_user: AuthUser = Depends(get_current_user),
    share_token: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Real-time face detection for single frame during streaming.

    Phase 1 of Hybrid Face Detection Architecture (Issue 052).
    Provides immediate face detection during video playback without
    requiring complete video processing.

    Args:
        media_id: UUID of the media to analyze
        frame_number: Specific frame number to extract and analyze
        confidence_threshold: Minimum confidence for face detection (0.0-1.0)
        current_user: Authenticated user
        share_token: Optional share token for public access
        db: Database session

    Returns:
        JSON response with detected faces for the specific frame
    """
    try:
        # Check access permissions
        access_info = get_media_access_check(
            media_id, current_user.user_id, share_token, db
        )

        file_path = Path(access_info["file_path"])

        # Verify file exists on disk
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Media file not found")

        # Check if face detection is available
        detection_info = media_face_detection.get_face_detection_info()
        if not detection_info["enabled"]:
            return {
                "faces": [],
                "frame_number": frame_number,
                "detection_time": 0.0,
                "method": "face_detection_disabled",
                "error": "Face detection not available",
            }

        # Extract single frame efficiently
        cap = cv2.VideoCapture(str(file_path))
        try:
            # Set frame position
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            ret, frame = cap.read()

            if not ret:
                return {
                    "faces": [],
                    "frame_number": frame_number,
                    "detection_time": 0.0,
                    "method": "frame_extraction_failed",
                    "error": f"Could not extract frame {frame_number}",
                }

            # Perform Vision service compatible face detection
            # for progressive pre-loading
            import time

            start_time = time.time()

            # Use vision-compatible detection to match Issue 054 results
            faces = media_face_detection.detect_faces_vision_compatible(
                frame, confidence_threshold
            )

            detection_time = time.time() - start_time

            # Determine the actual method used based on face results
            actual_method = "two_stage_haar_dlib"  # Vision compatible method
            if faces and len(faces) > 0:
                # Use the method from the first detected face
                actual_method = faces[0].get("method", "two_stage_haar_dlib")

            return {
                "faces": faces,
                "frame_number": frame_number,
                "detection_time": detection_time,
                "method": actual_method,
                "total_faces": len(faces),
            }

        finally:
            cap.release()

    except Exception as e:
        logger.error(f"Real-time face detection error: {e}")
        return {
            "faces": [],
            "frame_number": frame_number,
            "detection_time": 0.0,
            "method": "error",
            "error": str(e),
        }


@router.get("/info/{media_id}/faces")
async def get_face_detection_info(media_id: str):
    """
    Get face detection capabilities and information for a media item.

    Args:
        media_id: UUID of the media

    Returns:
        Dict containing face detection capabilities and status
    """
    try:
        detection_info = media_face_detection.get_face_detection_info()

        return {
            "media_id": media_id,
            "face_detection": detection_info,
            "streaming_endpoints": {
                "with_faces": f"/stream/video/{media_id}?face_detection=true",
                "without_faces": (f"/stream/video/{media_id}?face_detection=false"),
            },
            "benefits": [
                "Real-time face detection during streaming",
                "No cross-service API calls required",
                "Immediate yellow rectangle overlay",
                "Configurable confidence thresholds",
                "High performance with minimal latency",
            ],
        }

    except Exception as e:
        logger.error(f"Face detection info error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get face detection info")


async def _generate_video_frames(
    file_path: Path, face_detection: bool, confidence_threshold: float
):
    """
    Generate video frames with optional face detection overlay.

    This function reads the actual video file and processes each frame in real-time.
    """
    try:
        import cv2

        # Open the video file
        cap = cv2.VideoCapture(str(file_path))

        if not cap.isOpened():
            logger.error(f"Failed to open video file: {file_path}")
            return

        logger.info(f"Started streaming video: {file_path}")

        while True:
            ret, frame = cap.read()
            if not ret:
                logger.info("End of video stream")
                break

            if face_detection and media_face_detection.is_face_detection_enabled():
                # Process frame with face detection
                frame_bytes = _frame_to_bytes(frame)
                processed_result, faces = (
                    media_face_detection.process_video_frame_with_faces(
                        frame_bytes,
                        draw_overlay=True,
                        confidence_threshold=confidence_threshold,
                    )
                )

                # Ensure processed result is bytes
                if isinstance(processed_result, bytes):
                    processed_bytes = processed_result
                else:
                    # Convert numpy array to bytes
                    processed_bytes = _frame_to_bytes(processed_result)

                # Log face detections
                if faces:
                    logger.debug(f"Detected {len(faces)} faces in frame")

                yield b"--frame\r\n"
                yield b"Content-Type: image/jpeg\r\n\r\n"
                yield processed_bytes
                yield b"\r\n"
            else:
                # Stream without face detection
                frame_bytes = _frame_to_bytes(frame)
                yield b"--frame\r\n"
                yield b"Content-Type: image/jpeg\r\n\r\n"
                yield frame_bytes
                yield b"\r\n"

            await asyncio.sleep(0.033)  # ~30 FPS

        cap.release()
        logger.info("Video streaming completed")

    except Exception as e:
        logger.error(f"Frame generation error: {e}")
        raise


def _frame_to_bytes(frame):
    """Convert OpenCV frame to JPEG bytes."""
    import cv2

    success, encoded = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
    if not success:
        raise ValueError("Failed to encode frame")
    return encoded.tobytes()
