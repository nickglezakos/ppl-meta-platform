"""
Streaming endpoints for PPL Meta Cameras API.
"""

import asyncio
import base64
import io
import logging
import time
from typing import Dict

import cv2
import numpy as np
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
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
from src.services.camera_service_queue import get_camera_service
from src.services.camera_detection import camera_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/{device_id}/start", dependencies=[Depends(require_start_stream)])
async def start_stream(
    device_id: str, current_user: Dict = Depends(get_current_user)
) -> Dict:
    """Start streaming from a specific camera."""
    logger.info(f"🎬 [START_STREAM] Called for device_id={device_id}, user={current_user.get('sub')}")

    try:
        # ✅ Use queue-based camera service
        queue_service = get_camera_service()
        
        # Check if camera is already connected
        worker = queue_service.get_camera_stream(device_id)
        logger.info(f"🔍 [START_STREAM] Worker found: {worker is not None}")
        
        # ✅ Check if worker exists and is connected
        if not worker:
            logger.info(f"🔌 [START_STREAM] Camera {device_id} not connected, connecting now...")
            connection_success = await queue_service.connect_camera(device_id)
            if not connection_success:
                logger.error(f"❌ [START_STREAM] Failed to connect camera {device_id}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to connect to camera {device_id}",
                )
            logger.info(f"✅ [START_STREAM] Successfully connected camera {device_id}")
        else:
            logger.info(f"✅ [START_STREAM] Camera {device_id} already connected")

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
            
            # Publish streaming started event
            try:
                from src.services.status_notification_service import get_status_service, CameraStatusEvent
                status_service = get_status_service()
                await status_service.publish_status_change(
                    device_id,
                    CameraStatusEvent.STREAMING_STARTED,
                    {
                        "quality": quality,
                        "resolution": f"{width}x{height}",
                        "fps": fps,
                        "user_id": current_user.get('sub')
                    }
                )
            except Exception as e:
                logger.debug(f"Could not publish streaming_started event: {e}")

            consecutive_failures = 0
            max_consecutive_failures = 50  # 5 seconds at 10fps before giving up
            last_frame_time = time.time()
            stream_timeout = 30.0  # 30 seconds without frames = timeout
            
            # Determine camera type
            is_mobile = device_id.startswith('mobile_')
            is_edge = device_id.startswith('edge-camera-')
            
            # 🎯 UNIFIED QUEUE ARCHITECTURE: All cameras use queue workers now
            if is_edge:
                # Edge cameras use EdgeCameraFrameProcessor which manages CameraWorker
                from src.services.edge_camera_processor import get_edge_processor
                edge_processor = get_edge_processor()
                logger.info(f"📹 [GENERATE_FRAMES] Using edge processor worker for {device_id}")
            else:
                # USB/RTSP/Mobile cameras use queue service
                queue_service = get_camera_service()
                logger.info(f"🎥 [GENERATE_FRAMES] Using queue service worker for {device_id} (mobile: {is_mobile})")

            while True:
                try:
                    # Check for stream timeout
                    if time.time() - last_frame_time > stream_timeout:
                        logger.error(f"⏱️ Stream timeout for {device_id} - no frames for {stream_timeout}s")
                        break

                    # Get frame from appropriate source
                    if is_edge:
                        # Get frame from edge camera worker
                        worker = edge_processor.get_worker(device_id)
                        frame = worker.get_latest_frame() if worker else None
                    else:
                        # Get frame from queue worker (USB/RTSP/MOBILE)
                        frame = await queue_service.get_latest_frame(device_id)
                    
                    if frame is None:
                        consecutive_failures += 1
                        if consecutive_failures >= max_consecutive_failures:
                            logger.error(f"❌ Too many frame read failures for {device_id}, stopping stream")
                            break
                        logger.debug(f"No frame available from {device_id} (failure {consecutive_failures}/{max_consecutive_failures})")
                        await asyncio.sleep(0.1)
                        continue

                    # Reset failure counter on success
                    consecutive_failures = 0
                    last_frame_time = time.time()

                    # Mobile camera frames are already rotated by the queue worker
                    # No additional rotation needed

                    # Resize frame if needed (maintain aspect ratio for mobile cameras)
                    if is_mobile:
                        # For mobile cameras, maintain aspect ratio
                        # Calculate scaling to fit within target dimensions
                        frame_height, frame_width = frame.shape[:2]
                        target_aspect = width / height
                        frame_aspect = frame_width / frame_height
                        
                        # Only resize if frame is significantly different from target
                        if abs(frame_width - width) > 10 or abs(frame_height - height) > 10:
                            if frame_aspect > target_aspect:
                                # Frame is wider - fit to width
                                new_width = width
                                new_height = int(width / frame_aspect)
                            else:
                                # Frame is taller - fit to height
                                new_height = height
                                new_width = int(height * frame_aspect)
                            
                            frame = cv2.resize(frame, (new_width, new_height))
                            logger.debug(f"📱 Resized frame from {frame_width}x{frame_height} to {new_width}x{new_height} (maintaining aspect ratio)")
                    else:
                        # For non-mobile cameras, resize normally
                        if frame.shape[1] != width or frame.shape[0] != height:
                            frame = cv2.resize(frame, (width, height))

                    # Convert RGB to BGR for mobile cameras (JPEG is RGB, OpenCV expects BGR)
                    if is_mobile and len(frame.shape) == 3 and frame.shape[2] == 3:
                        # Check if frame is RGB (mobile cameras store as RGB from JPEG)
                        # OpenCV imencode expects BGR
                        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

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
                    
                except GeneratorExit:
                    # Client disconnected - graceful exit
                    logger.info(f"🔌 Client disconnected from stream {device_id}")
                    break
                except Exception as e:
                    consecutive_failures += 1
                    logger.error(f"Error in stream loop for {device_id}: {e}")
                    if consecutive_failures >= max_consecutive_failures:
                        logger.error(f"❌ Too many errors for {device_id}, stopping stream")
                        break
                    await asyncio.sleep(0.1)
                    
            logger.info(f"🛑 Stream ended for {device_id}")
            
            # Publish streaming stopped event
            try:
                from src.services.status_notification_service import get_status_service, CameraStatusEvent
                status_service = get_status_service()
                await status_service.publish_status_change(
                    device_id,
                    CameraStatusEvent.STREAMING_STOPPED,
                    {
                        "user_id": current_user.get('sub')
                    }
                )
            except Exception as e:
                logger.debug(f"Could not publish streaming_stopped event: {e}")

        except Exception as e:
            logger.error(f"Error in video stream for camera {device_id}: {e}")
            return

    logger.info(f"🎥 [VIDEO_STREAM] Request for device_id={device_id}, user={current_user.get('sub')}")
    
    try:
        # Check camera type
        is_mobile = device_id.startswith('mobile_')
        is_edge = device_id.startswith('edge-camera-')
        
        if is_mobile:
            # 🎯 UNIFIED QUEUE ARCHITECTURE: Mobile cameras now use queue workers too
            logger.info(f"📱 [VIDEO_STREAM] Mobile camera detected: {device_id}")
            from src.services.mobile_streaming import mobile_streaming_service
            
            # Check if mobile camera is sending frames to backend
            if not mobile_streaming_service.has_active_mobile_camera(device_id):
                logger.error(f"❌ [VIDEO_STREAM] Mobile camera {device_id} not streaming to backend")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Mobile camera {device_id} not actively streaming frames",
                )
            
            # Ensure queue worker is connected
            queue_service = get_camera_service()
            worker = await queue_service.get_camera_stream(device_id)
            
            if not worker:
                logger.info(f"📱 [VIDEO_STREAM] Connecting queue worker for mobile camera {device_id}")
                success = await queue_service.connect_camera(device_id)
                if not success:
                    logger.error(f"❌ Failed to connect queue worker for mobile camera {device_id}")
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail=f"Failed to connect mobile camera worker",
                    )
                worker = await queue_service.get_camera_stream(device_id)
            
            logger.info(f"✅ [VIDEO_STREAM] Mobile camera {device_id} queue worker ready")
        elif is_edge:
            # Edge cameras use processor architecture (frames pushed from edge device)
            logger.info(f"📹 [VIDEO_STREAM] Edge camera detected: {device_id}")
            from src.services.edge_camera_processor import get_edge_processor
            from src.services.edge_camera_ws_manager import get_ws_manager
            
            # Check if edge camera is connected via WebSocket
            ws_manager = get_ws_manager()
            if not ws_manager.is_connected(device_id):
                logger.error(f"❌ [VIDEO_STREAM] Edge camera {device_id} not connected via WebSocket")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Edge camera {device_id} not connected. Please connect via WebSocket first",
                )
            
            # Check if edge camera has a worker (created when frames start arriving)
            edge_processor = get_edge_processor()
            worker = edge_processor.get_worker(device_id)
            
            if not worker:
                logger.error(f"❌ [VIDEO_STREAM] Edge camera {device_id} worker not created yet (no frames received)")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Edge camera {device_id} not streaming. Please start streaming from edge device first",
                )
            
            logger.info(f"✅ [VIDEO_STREAM] Edge camera {device_id} worker ready")
        else:
            # USB/RTSP cameras use worker queue architecture
            logger.info(f"🎥 [VIDEO_STREAM] USB/RTSP camera detected: {device_id}")
            queue_service = get_camera_service()
            worker = await queue_service.get_camera_stream(device_id)
            logger.info(f"🔍 [VIDEO_STREAM] Worker found: {worker is not None}, Status: {worker.status.value if worker else 'N/A'}")
            
            if not worker or worker.status.value != 'connected':
                logger.error(f"❌ [VIDEO_STREAM] Camera {device_id} worker not connected")
                from src.services.worker_manager import get_worker_manager
                manager = get_worker_manager()
                logger.error(f"❌ [VIDEO_STREAM] Available workers: {list(manager.workers.keys())}")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Camera {device_id} not connected. Please connect via /cameras/{device_id}/connect first",
                )

        logger.info(
            f"✅ [VIDEO_STREAM] User {current_user.get('sub')} accessing video stream for camera {device_id}"
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
    enable_instant_detection: bool = True,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks(),
) -> Dict:
    """Start recording from a specific camera with session tracking.
    
    Args:
        enable_instant_detection: Whether to automatically start instant detection
    """

    try:
        # 🔍 DEBUG: Log current_user to investigate user_id issue
        logger.info(f"🔍 [RECORD-START] current_user: {current_user}")
        logger.info(f"🔍 [RECORD-START] current_user.get('sub'): {current_user.get('sub')}")
        logger.info(f"🔍 [RECORD-START] device_id: {device_id}")
        logger.info(f"🔍 [RECORD-START] enable_instant_detection parameter: {enable_instant_detection}")
        
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

        logger.info(f"🔍 [RECORD-CHECK] existing_recording: {existing_recording}")
        logger.info(f"🔍 [RECORD-CHECK] active_session: {active_session}")

        if existing_recording or active_session:
            logger.warning(f"❌ [RECORD-BLOCKED] Camera {device_id} already recording - existing_recording={existing_recording is not None}, active_session={active_session is not None}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Camera {device_id} is already recording",
            )
        
        # Auto-start streaming for edge cameras (they need active stream to send frames)
        is_edge = device_id.startswith('edge-camera-')
        if is_edge:
            from src.services.edge_camera_ws_manager import get_ws_manager
            ws_manager = get_ws_manager()
            # Send start-stream command (edge camera will handle if already streaming)
            logger.info(f"📹 [EDGE-AUTO-STREAM] Ensuring stream is active for {device_id}")
            try:
                success = await ws_manager.send_command(device_id, "start-stream")
                if success:
                    logger.info(f"✅ [EDGE-AUTO-STREAM] Start-stream command sent to {device_id}")
                else:
                    logger.warning(f"⚠️ [EDGE-AUTO-STREAM] Failed to send start-stream to {device_id} (not connected?)")
            except Exception as e:
                logger.error(f"❌ [EDGE-AUTO-STREAM] Error sending start-stream: {e}")

        # Create recording session first
        from src.services.recording_session_service import RecordingSessionService

        session_service = RecordingSessionService(db)

        # Get recording configuration (with segment support)
        recording_config = {
            "quality": "high",
            "segment_duration_seconds": 30,  # 30-second segments
            "auto_face_detection_enabled": True,
            "video_codec": "h264",
            "audio_enabled": False,
            "face_detection_method": "enhanced-v2",
            "quality_preset": "balanced",
        }

        # Extract user_id from JWT token
        user_id_from_token = current_user.get("sub")
        if not user_id_from_token:
            logger.error(f"🔍 [START-RECORDING] current_user: {current_user}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid authentication token: missing user ID"
            )

        # Create recording session
        recording_session = session_service.create_session(
            camera_device_id=device_id,
            user_id=user_id_from_token,
            recording_config=recording_config,
        )

        # Start recording with session tracking
        logger.info(f"🔍 [RECORD-START] Calling start_recording_with_session with enable_instant_detection={enable_instant_detection}")
        try:
            recording_info = await camera_service.start_recording_with_session(
                device_id=device_id,
                user_id=user_id_from_token,
                quality="high",
                auth_token=credentials.credentials,
                session_uuid=recording_session.session_uuid,
                segment_duration=recording_config["segment_duration_seconds"],
                enable_instant_detection=enable_instant_detection,
            )

            if not recording_info:
                # If recording fails, mark session as failed and clean up
                logger.error(f"❌ [RECORD-START] start_recording_with_session returned None for {device_id}")
                session_service.update_session_status(
                    recording_session.session_uuid, "failed", "Recording service returned no info"
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to start recording for camera {device_id}",
                )
        except Exception as e:
            # If any exception occurs, mark session as failed
            logger.error(f"❌ [RECORD-START] Exception during recording start: {e}", exc_info=True)
            session_service.update_session_status(
                recording_session.session_uuid, "failed", str(e)
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to start recording: {str(e)}",
            )

        logger.info(
            f"User {current_user.get('sub')} started recording session "
            f"{recording_session.session_uuid} for camera {device_id}"
        )

        # ✅ RETURN IMMEDIATELY - Don't wait for VMeta notification
        logger.info(f"📤 [RECORD-START] Preparing response for session {recording_session.session_uuid}")
        response_data = {
            "status": "success",
            "message": f"Recording started for camera {device_id}",
            "device_id": device_id,
            "session_uuid": recording_session.session_uuid,
            "recording_id": recording_info.get("recording_id"),
            "started_at": recording_info.get("started_at"),
            "segment_duration": recording_config["segment_duration_seconds"],
        }
        
        logger.info(f"✅ [RECORD-START] Returning response immediately, VMeta notification scheduled")
        
        # ✅ SCHEDULE VMETA NOTIFICATION AS BACKGROUND TASK
        # This runs AFTER the response is sent to the client
        background_tasks.add_task(
            notify_vmeta_recording_start,
            device_id=device_id,
            session_uuid=recording_session.session_uuid,
            user_id=current_user.get("sub"),
            auth_token=credentials.credentials,
        )
        
        return response_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error starting recording for camera %s: %s", device_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start recording",
        ) from e


# ✅ SEPARATE FUNCTION FOR BACKGROUND VMETA NOTIFICATION
async def notify_vmeta_recording_start(
    device_id: str,
    session_uuid: str,
    user_id: str,
    auth_token: str,
) -> None:
    """Background task to notify VMeta service of recording start."""
    try:
        import httpx
        from datetime import datetime
        
        logger.info(f"📹 [VMETA-NOTIFY] Starting background VMeta notification for {session_uuid}")
        
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.post(
                "http://localhost:8008/api/v1/recording/started",
                json={
                    "collection_id": device_id,
                    "session_uuid": session_uuid,
                    "device_id": device_id,
                    "user_id": user_id or "",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "metadata": {}
                },
                headers={"Authorization": f"Bearer {auth_token}"}
            )
            logger.info(
                f"✅ [VMETA-NOTIFY] VMeta notified successfully: {session_uuid}, "
                f"status: {response.status_code}"
            )
    except Exception as e:
        # Log but don't fail - recording already started successfully
        logger.warning(f"⚠️ [VMETA-NOTIFY] Failed to notify VMeta: {e}")


@router.post("/{device_id}/record/stop")
async def stop_recording(
    device_id: str,
    auto_stop_instant_detection: bool = True,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict:
    """Stop recording from a specific camera and save to collection.
    
    Args:
        auto_stop_instant_detection: Whether to automatically stop instant detection
    """

    try:
        # Log the auto_stop parameter for debugging
        logger.info(f"🛑 Stop recording endpoint called for {device_id}, auto_stop_instant_detection={auto_stop_instant_detection}")
        
        # Clean up any stale recording sessions for this camera
        from src.services.recording_session_service import RecordingSessionService
        session_service = RecordingSessionService(db)
        cleaned = session_service.cleanup_stale_sessions(max_age_hours=1)
        if cleaned > 0:
            logger.info(f"Cleaned up {cleaned} stale recording sessions before stopping {device_id}")
        
        # Verify camera exists
        camera = db.query(Camera).filter(Camera.device_id == device_id).first()
        if not camera:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Camera {device_id} not found",
            )

        # Stop recording and get recording info
        # Extract user_id from JWT token
        user_id_from_token = current_user.get("sub")
        if not user_id_from_token:
            logger.error(f"🔍 [STOP-RECORDING] current_user has no 'sub': {current_user}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid authentication token: missing user ID"
            )
        
        # Start the stop recording process (returns immediately, upload happens in background)
        recording_result = await camera_service.stop_recording(
            device_id=device_id, 
            user_id=user_id_from_token,
            auto_stop_instant_detection=auto_stop_instant_detection
        )

        if not recording_result:
            # Camera might not be recording
            logger.warning(f"⚠️ Stop recording called but camera {device_id} was not recording")
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
