"""
Camera API endpoints for PPL Meta Mini - Upgrade 2 Implementation
Provides USB camera detection, connection, and recording endpoints.
Enhanced with graceful cancellation support.
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, UploadFile, Request
from pydantic import BaseModel, Field

from services.enhanced_camera_manager import EnhancedCameraManager
from services.temp_storage import TempStorageManager
from api.analytics import analyze_video_from_path


# Global instances (will be initialized in main.py)
camera_manager: Optional[EnhancedCameraManager] = None
temp_storage: Optional[TempStorageManager] = None

# Initialize logger
logger = logging.getLogger(__name__)

# Create router
camera_router = APIRouter(prefix="/api/v1/camera", tags=["camera"])


# Request/Response Models
class RecordingRequest(BaseModel):
    """Request model for recording and analysis."""
    duration: float = Field(default=1.5, ge=0.1, le=30.0, 
                           description="Recording duration in seconds")
    quality: str = Field(default="medium", 
                        pattern="^(high|medium|low)$",
                        description="Recording quality level")
    auto_delete: bool = Field(default=True, 
                             description="Auto-delete temporary files after analysis")


class CameraDetectionResponse(BaseModel):
    """Response model for camera detection."""
    status: str
    camera_detected: bool
    camera_info: Dict[str, Any] = {}
    connection_status: str
    error_message: Optional[str] = None


class RecordingResponse(BaseModel):
    """Response model for recording and analysis."""
    recording_status: str
    video_info: Dict[str, Any] = {}
    analysis_results: Dict[str, Any] = {}
    temp_file_deleted: bool = False
    processing_time_ms: int = 0
    error_message: Optional[str] = None


def initialize_camera_services():
    """Initialize camera services. Called from main.py"""
    global camera_manager, temp_storage
    
    try:
        camera_manager = EnhancedCameraManager()
        temp_storage = TempStorageManager()
        logger.info("✅ Camera services initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize camera services: {e}")
        raise


@camera_router.post("/detect-and-connect", response_model=CameraDetectionResponse)
async def detect_and_connect_camera(request: Request):
    """
    Detect and connect to the first available USB camera with graceful cancellation support.
    
    Args:
        request: FastAPI Request object for cancellation detection
    
    Returns:
        CameraDetectionResponse: Camera detection and connection status
    """
    if camera_manager is None:
        raise HTTPException(
            status_code=500, 
            detail="Camera manager not initialized"
        )
    
    logger.info("🔍 Starting camera detection and connection...")
    
    try:
        # Check if client has disconnected before starting
        if await request.is_disconnected():
            logger.info("⚠️ Client disconnected before camera detection started")
            return CameraDetectionResponse(
                status="cancelled",
                camera_detected=False,
                connection_status="cancelled",
                error_message="Request was cancelled by client"
            )
        
        # Create a task for camera detection that can be cancelled
        detection_task = asyncio.create_task(camera_manager.detect_cameras())
        
        # Monitor for client disconnection during detection
        while not detection_task.done():
            if await request.is_disconnected():
                logger.info("⚠️ Client disconnected during camera detection, cancelling...")
                detection_task.cancel()
                try:
                    await detection_task
                except asyncio.CancelledError:
                    logger.info("✅ Camera detection task successfully cancelled")
                return CameraDetectionResponse(
                    status="cancelled",
                    camera_detected=False,
                    connection_status="cancelled",
                    error_message="Request was cancelled by client during detection"
                )
            
            # Small delay to check disconnection status
            await asyncio.sleep(0.1)
        
        # Get detection results
        cameras = await detection_task
        
        if not cameras:
            return CameraDetectionResponse(
                status="success",
                camera_detected=False,
                connection_status="no_camera",
                error_message="No USB cameras detected"
            )
        
        # Check disconnection before attempting connection
        if await request.is_disconnected():
            logger.info("⚠️ Client disconnected before camera connection")
            return CameraDetectionResponse(
                status="cancelled",
                camera_detected=True,
                connection_status="cancelled",
                error_message="Request was cancelled before connection attempt"
            )
        
        # Connect to the first available camera
        first_camera = cameras[0]
        camera_index = first_camera["index"]
        
        # Create cancellable connection task
        connection_task = asyncio.create_task(camera_manager.connect_camera(camera_index))
        
        # Monitor for disconnection during connection
        while not connection_task.done():
            if await request.is_disconnected():
                logger.info("⚠️ Client disconnected during camera connection, cancelling...")
                connection_task.cancel()
                try:
                    await connection_task
                except asyncio.CancelledError:
                    logger.info("✅ Camera connection task successfully cancelled")
                return CameraDetectionResponse(
                    status="cancelled",
                    camera_detected=True,
                    camera_info=first_camera,
                    connection_status="cancelled",
                    error_message="Request was cancelled during connection"
                )
            
            await asyncio.sleep(0.1)
        
        connection_success = await connection_task
        
        if connection_success:
            camera_info = await camera_manager.get_camera_info()
            
            return CameraDetectionResponse(
                status="success",
                camera_detected=True,
                camera_info=camera_info,
                connection_status="connected"
            )
        else:
            return CameraDetectionResponse(
                status="error",
                camera_detected=True,
                camera_info=first_camera,
                connection_status="failed",
                error_message="Failed to connect to detected camera"
            )
    
    except asyncio.CancelledError:
        logger.info("✅ Camera detection/connection was gracefully cancelled")
        return CameraDetectionResponse(
            status="cancelled",
            camera_detected=False,
            connection_status="cancelled",
            error_message="Operation was cancelled"
        )
    
    except Exception as e:
        logger.error(f"❌ Camera detection/connection error: {e}")
        return CameraDetectionResponse(
            status="error",
            camera_detected=False,
            connection_status="error",
            error_message=str(e)
        )


@camera_router.post("/record-and-analyze", response_model=RecordingResponse)
async def record_and_analyze_video(
    fastapi_request: Request,
    request: RecordingRequest
):
    """
    Record video from connected USB camera and analyze for faces and age estimation.
    Enhanced with graceful cancellation support.
    
    Args:
        fastapi_request: FastAPI Request object for cancellation detection
        request: Recording parameters (duration, quality, auto_delete)
        
    Returns:
        RecordingResponse: Recording and analysis results
    """
    if camera_manager is None or temp_storage is None:
        raise HTTPException(
            status_code=500,
            detail="Camera services not initialized"
        )
    
    start_time = time.time()
    temp_file_path = None
    
    logger.info(f"🎥 Starting recording and analysis (duration: {request.duration}s, quality: {request.quality})")
    
    try:
        # Check if camera is connected
        if not camera_manager.is_camera_connected():
            raise HTTPException(
                status_code=400,
                detail="No camera connected. Call /detect-and-connect first."
            )
        
        # Check storage space (estimate ~10MB per second of recording)
        estimated_size_mb = max(10, int(request.duration * 10))
        if not temp_storage.ensure_storage_space(estimated_size_mb):
            raise HTTPException(
                status_code=507,
                detail=f"Insufficient storage space. Need ~{estimated_size_mb}MB"
            )
        
        # Generate temporary file path
        temp_file_path = temp_storage.generate_temp_filename(
            extension=".mp4",
            prefix="camera_recording_"
        )
        
        # Record video
        logger.info(f"📹 Recording to: {temp_file_path}")
        recorded_path = await camera_manager.record_video(
            duration=request.duration,
            output_path=temp_file_path,
            quality=request.quality
        )
        
        # Get video file information
        import os
        video_info = {
            "duration": request.duration,
            "file_path": recorded_path,
            "file_size": os.path.getsize(recorded_path) if os.path.exists(recorded_path) else 0,
            "quality": request.quality,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Check for cancellation before analysis
        if await fastapi_request.is_disconnected():
            logger.info("⚠️ Client disconnected before video analysis")
            # Cleanup temporary file
            if temp_file_path:
                temp_storage.cleanup_temp_file(temp_file_path)
            return RecordingResponse(
                recording_status="cancelled",
                error_message="Request was cancelled before video analysis",
                processing_time_ms=int((time.time() - start_time) * 1000)
            )
        
        # Analyze the recorded video using existing pipeline with cancellation support
        logger.info("🔍 Starting video analysis...")
        analysis_results = await analyze_video_from_path(recorded_path, request=fastapi_request)
        
        # Calculate processing time
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        # Clean up temporary file if requested
        temp_file_deleted = False
        if request.auto_delete and temp_file_path:
            temp_file_deleted = temp_storage.cleanup_temp_file(temp_file_path)
            if temp_file_deleted:
                video_info["file_path"] = "[deleted]"
        
        logger.info(f"✅ Recording and analysis completed in {processing_time_ms}ms")
        
        return RecordingResponse(
            recording_status="completed",
            video_info=video_info,
            analysis_results=analysis_results,
            temp_file_deleted=temp_file_deleted,
            processing_time_ms=processing_time_ms
        )
    
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"❌ Recording and analysis failed: {e}")
        
        # Cleanup on error if file was created
        if temp_file_path and temp_storage:
            temp_storage.cleanup_temp_file(temp_file_path)
        
        return RecordingResponse(
            recording_status="failed",
            error_message=str(e),
            processing_time_ms=int((time.time() - start_time) * 1000)
        )


@camera_router.get("/status")
async def get_camera_status():
    """
    Get current camera connection status and information.
    
    Returns:
        Dict: Camera status information
    """
    if camera_manager is None:
        return {
            "status": "error",
            "message": "Camera manager not initialized"
        }
    
    try:
        camera_info = await camera_manager.get_camera_info()
        
        # Add storage information
        storage_info = {}
        if temp_storage:
            storage_info = temp_storage.get_temp_directory_info()
        
        return {
            "status": "success",
            "camera": camera_info,
            "storage": storage_info,
            "services_initialized": True
        }
    
    except Exception as e:
        logger.error(f"❌ Error getting camera status: {e}")
        return {
            "status": "error",
            "message": str(e),
            "services_initialized": camera_manager is not None
        }


@camera_router.post("/disconnect")
async def disconnect_camera():
    """
    Disconnect the currently connected camera.
    
    Returns:
        Dict: Disconnection status
    """
    if camera_manager is None:
        raise HTTPException(
            status_code=500,
            detail="Camera manager not initialized"
        )
    
    try:
        success = await camera_manager.disconnect_camera()
        
        if success:
            return {
                "status": "success",
                "message": "Camera disconnected successfully"
            }
        else:
            return {
                "status": "error",
                "message": "Failed to disconnect camera"
            }
    
    except Exception as e:
        logger.error(f"❌ Error disconnecting camera: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


@camera_router.post("/cleanup")
async def cleanup_temporary_storage():
    """
    Clean up all temporary storage files and directories.
    
    Returns:
        Dict: Cleanup statistics
    """
    if temp_storage is None:
        raise HTTPException(
            status_code=500,
            detail="Temp storage manager not initialized"
        )
    
    try:
        cleanup_stats = temp_storage.cleanup_all()
        
        return {
            "status": "success",
            "cleanup_stats": cleanup_stats,
            "message": f"Cleaned up {cleanup_stats['total_items_cleaned']} items"
        }
    
    except Exception as e:
        logger.error(f"❌ Error during cleanup: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


@camera_router.get("/storage-info")
async def get_storage_info():
    """
    Get detailed temporary storage information.
    
    Returns:
        Dict: Storage information including size and file counts
    """
    if temp_storage is None:
        raise HTTPException(
            status_code=500,
            detail="Temp storage manager not initialized"
        )
    
    try:
        storage_info = temp_storage.get_temp_directory_info()
        
        return {
            "status": "success",
            "storage_info": storage_info
        }
    
    except Exception as e:
        logger.error(f"❌ Error getting storage info: {e}")
        return {
            "status": "error",
            "message": str(e)
        }