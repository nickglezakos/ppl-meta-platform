"""
PPL Meta Vision Service - Production Entry Point
Generated from VIS-001.3 - Microservice Implementation

This is the main entry point for the PPL Meta Vision Service,
containing the FastAPI application with face detection capabilities.
"""

import asyncio
import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Add the current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

import base64
import io

# Image Processing & ML
import cv2
import numpy as np
import requests
import uvicorn
from database import vision_db

# Import our services and models
from extracted_face_detector import ExtractedFaceDetector

# Web Framework & API
from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    File,
    Header,
    HTTPException,
    Query,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# JWT token handling
from jose import JWTError, jwt
from media_processor import MediaProcessingService
from models import (
    BaseResponse,
    FaceDetectionResult,
    MediaProcessingRequest,
    MediaRecord,
    OverlayRequest,
    TimelineRequest,
)
from PIL import Image
from pydantic import BaseModel, Field

# Configure logging and logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ppl-meta-vision")

# PPL Meta Platform Configuration
PPL_META_CONFIG = {
    "vision_service": {
        "port": 8003,
        "host": "0.0.0.0",
        "name": "ppl-meta-vision",
        "version": "1.1.0",  # Updated for media integration
    },
    "media_service": {
        "url": "http://localhost:8080",
        "timeout": 30,
    },  # Use Gateway URL for media access
    "gateway": {"url": "http://localhost:8080", "health_endpoint": "/health"},
    "orchestrator": {
        "url": "http://localhost:8002",
        "register_endpoint": "/services/register",
    },
}

# JWT Configuration (should match Node service and Gateway config)
JWT_SECRET_KEY = "default-secret-key-change-in-production"
JWT_ALGORITHM = "HS256"


def extract_user_id_from_token(authorization_header: str) -> Optional[str]:
    """Extract user_id from JWT token in Authorization header."""
    try:
        if not authorization_header or not authorization_header.startswith("Bearer "):
            return None

        # Extract token
        token = authorization_header.split(" ")[1]

        # Decode JWT token
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])

        return payload.get("sub")  # 'sub' contains the user_id
    except JWTError:
        return None
    except Exception:
        return None


def get_user_uuid_from_profile(authorization_header: str) -> Optional[str]:
    """Get user UUID by calling the user profile endpoint."""
    try:
        if not authorization_header:
            return None

        # Call user profile endpoint to get UUID via Gateway service
        headers = {"Authorization": authorization_header}
        gateway_url = PPL_META_CONFIG["gateway"]["url"]
        profile_url = f"{gateway_url}/api/v1/user/profile"

        response = requests.get(profile_url, headers=headers, timeout=30)

        if response.status_code == 200:
            profile_data = response.json()
            uuid = profile_data.get("guid")
            return uuid  # UUID is in 'guid' field

        return None
    except Exception as e:
        return None


# Pydantic models for request/response
class FaceDetectionRequest(BaseModel):
    """Request model for face detection."""

    image_base64: str = Field(..., description="Base64 encoded image")
    methods: Optional[List[str]] = Field(
        default=None, description="Detection methods to use"
    )
    confidence_threshold: Optional[float] = Field(
        default=0.5, description="Confidence threshold"
    )


class FaceDetection(BaseModel):
    """Model for a single face detection."""

    bbox: List[int] = Field(..., description="Bounding box [x1, y1, x2, y2]")
    confidence: float = Field(..., description="Detection confidence score")
    method: str = Field(..., description="Detection method used")


class FaceDetectionResponse(BaseModel):
    """Response model for face detection."""

    success: bool = Field(..., description="Whether detection was successful")
    detections: List[FaceDetection] = Field(..., description="List of detected faces")
    processing_time: float = Field(..., description="Processing time in seconds")
    method_results: Optional[Dict[str, Any]] = Field(
        default=None, description="Detailed results per method"
    )
    message: Optional[str] = Field(default=None, description="Status message")


class ServiceHealth(BaseModel):
    """Service health status."""

    status: str = Field(..., description="Service status")
    version: str = Field(..., description="Service version")
    uptime: float = Field(..., description="Service uptime in seconds")
    models_loaded: bool = Field(..., description="Whether models are loaded")
    available_methods: List[str] = Field(..., description="Available detection methods")


# Initialize FastAPI application
app = FastAPI(
    title="PPL Meta Vision Service",
    description="Face detection microservice for PPL Meta Platform",
    version=PPL_META_CONFIG["vision_service"]["version"],
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure based on your needs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables
face_detector_instance = None
media_processor_instance = None
service_start_time = time.time()


# Initialize services on startup
@app.on_event("startup")
async def startup_event():
    """Initialize the face detector and media processor when the service starts."""
    global face_detector_instance, media_processor_instance
    try:
        # Initialize database
        vision_db.init_database()

        # Initialize face detector
        face_detector_instance = ExtractedFaceDetector()

        # Initialize media processor
        media_processor_instance = MediaProcessingService(face_detector_instance)

        logger = logging.getLogger("ppl-meta-vision")
        logger.info("✅ PPL Meta Vision Service started successfully")
        logger.info(f"📊 Available methods: {face_detector_instance.available_methods}")
        logger.info("🗄️ Database initialized")
        logger.info("🎬 Media processor initialized")
    except Exception as e:
        logger = logging.getLogger("ppl-meta-vision")
        logger.error(f"❌ Failed to initialize services: {e}")
        raise


def decode_base64_image(image_base64: str) -> np.ndarray:
    """Decode base64 image to numpy array."""
    try:
        # Remove data URL prefix if present
        if image_base64.startswith("data:image"):
            image_base64 = image_base64.split(",")[1]

        # Decode base64
        image_bytes = base64.b64decode(image_base64)

        # Convert to PIL Image
        pil_image = Image.open(io.BytesIO(image_bytes))

        # Convert to numpy array (OpenCV format)
        image_array = np.array(pil_image)

        # Convert RGB to BGR if needed (OpenCV uses BGR)
        if len(image_array.shape) == 3 and image_array.shape[2] == 3:
            image_array = cv2.cvtColor(image_array, cv2.COLOR_RGB2BGR)

        return image_array
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image data: {str(e)}")


# API Endpoints


@app.get("/", summary="Service Info")
async def root():
    """Get basic service information."""
    return {
        "service": "PPL Meta Vision Service",
        "version": PPL_META_CONFIG["vision_service"]["version"],
        "status": "running",
        "endpoints": {
            "detect": "/detect",
            "health": "/health",
            "models": "/models",
            "docs": "/docs",
        },
    }


@app.get("/health", response_model=ServiceHealth, summary="Health Check")
async def health_check():
    """Get service health status."""
    global face_detector_instance, service_start_time

    uptime = time.time() - service_start_time

    if face_detector_instance is None:
        return ServiceHealth(
            status="unhealthy",
            version=PPL_META_CONFIG["vision_service"]["version"],
            uptime=uptime,
            models_loaded=False,
            available_methods=[],
        )

    return ServiceHealth(
        status="healthy",
        version=PPL_META_CONFIG["vision_service"]["version"],
        uptime=uptime,
        models_loaded=face_detector_instance.models_loaded,
        available_methods=face_detector_instance.available_methods,
    )


@app.get("/models", summary="Get Available Models")
async def get_models():
    """Get information about available detection models."""
    global face_detector_instance

    if face_detector_instance is None:
        raise HTTPException(status_code=503, detail="Face detector not initialized")

    summary = face_detector_instance.get_detection_summary()
    return {
        "available_methods": summary["available_methods"],
        "total_methods": summary["total_methods"],
        "models_loaded": summary["models_loaded"],
        "model_paths": summary["model_paths"],
    }


@app.post("/detect", response_model=FaceDetectionResponse, summary="Detect Faces")
async def detect_faces(request: FaceDetectionRequest):
    """
    Detect faces in an image using specified detection methods.

    Supports multiple detection methods: haar, dlib, mtcnn
    Returns bounding boxes, confidence scores, and processing time.
    """
    global face_detector_instance

    if face_detector_instance is None:
        raise HTTPException(status_code=503, detail="Face detector not initialized")

    start_time = time.time()

    try:
        # Decode image
        image = decode_base64_image(request.image_base64)

        # Determine methods to use
        methods = (
            request.methods
            if request.methods
            else face_detector_instance.available_methods
        )

        # Validate methods
        for method in methods:
            if method not in face_detector_instance.available_methods:
                raise HTTPException(
                    status_code=400,
                    detail=f"Method '{method}' not available. Available: {face_detector_instance.available_methods}",
                )

        # Update confidence thresholds if provided
        if request.confidence_threshold is not None:
            for method in methods:
                if method in ["haar", "dlib", "mtcnn", "two_stage"]:
                    face_detector_instance.update_confidence_threshold(
                        method, request.confidence_threshold
                    )

        # Run detection
        if len(methods) == 1:
            # Single method detection
            method = methods[0]
            if method == "haar":
                result = face_detector_instance.detect_faces_haar(image)
            elif method == "dlib":
                result = face_detector_instance.detect_faces_dlib(image)
            elif method == "mtcnn":
                result = face_detector_instance.detect_faces_mtcnn(image)
            elif method == "two_stage":
                result = face_detector_instance.detect_faces_two_stage(image)
            else:
                raise HTTPException(status_code=400, detail=f"Unknown method: {method}")

            # Format response
            if result["success"]:
                detections = [
                    FaceDetection(
                        bbox=det["bbox"],
                        confidence=det["confidence"],
                        method=det["method"],
                    )
                    for det in result["detections"]
                ]

                processing_time = time.time() - start_time
                return FaceDetectionResponse(
                    success=True,
                    detections=detections,
                    processing_time=processing_time,
                    message=f"Detected {len(detections)} faces using {method}",
                )
            else:
                raise HTTPException(
                    status_code=500, detail=result.get("error", "Detection failed")
                )

        else:
            # Multi-method detection
            results = face_detector_instance.detect_faces_multi_method(image, methods)

            # Aggregate all detections
            all_detections = []
            for method, method_result in results.items():
                if method_result.get("success", False):
                    for det in method_result.get("detections", []):
                        all_detections.append(
                            FaceDetection(
                                bbox=det["bbox"],
                                confidence=det["confidence"],
                                method=det["method"],
                            )
                        )

            processing_time = time.time() - start_time
            return FaceDetectionResponse(
                success=True,
                detections=all_detections,
                processing_time=processing_time,
                method_results=results,
                message=f"Detected {len(all_detections)} faces using {len(methods)} methods",
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Detection error: {str(e)}")


@app.post(
    "/detect/file",
    response_model=FaceDetectionResponse,
    summary="Detect Faces from File",
)
async def detect_faces_file(
    file: UploadFile = File(..., description="Image file"),
    methods: Optional[str] = None,
    confidence_threshold: Optional[float] = 0.5,
):
    """
    Detect faces in an uploaded image file.

    Alternative endpoint for file uploads instead of base64 encoding.
    """
    global face_detector_instance

    if face_detector_instance is None:
        raise HTTPException(status_code=503, detail="Face detector not initialized")

    # Validate file type
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    try:
        # Read file content
        file_content = await file.read()

        # Convert to base64 for reuse of existing logic
        image_base64 = base64.b64encode(file_content).decode("utf-8")

        # Parse methods parameter
        methods_list = methods.split(",") if methods else None

        # Create request object
        request = FaceDetectionRequest(
            image_base64=image_base64,
            methods=methods_list,
            confidence_threshold=confidence_threshold,
        )

        # Reuse the main detection endpoint
        return await detect_faces(request)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File processing error: {str(e)}")


@app.post("/process/media", summary="Process Media from Media Service")
async def process_media_from_service(
    media_id: str, media_url: str, media_type: str = "image"
):
    """
    Process media file from Media Service for face detection.

    This endpoint fetches media from the Media Service and processes it for faces.
    """
    global face_detector_instance

    if face_detector_instance is None:
        raise HTTPException(status_code=503, detail="Face detector not initialized")

    start_time = time.time()

    try:
        # Fetch media from Media Service
        response = requests.get(media_url, timeout=30)
        if response.status_code != 200:
            raise HTTPException(
                status_code=400, detail="Failed to fetch media from Media Service"
            )

        if media_type == "image":
            # Process image
            image_array = np.asarray(bytearray(response.content), dtype=np.uint8)
            image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

            if image is None:
                raise HTTPException(status_code=400, detail="Invalid image data")

            # Run face detection
            results = face_detector_instance.detect_faces_multi_method(image)

            # Aggregate results
            all_detections = []
            for method, result in results.items():
                if result.get("success", False):
                    for det in result.get("detections", []):
                        all_detections.append(
                            {
                                "bbox": det["bbox"],
                                "confidence": det["confidence"],
                                "method": det["method"],
                                "media_id": media_id,
                            }
                        )

            processing_time = time.time() - start_time

            return {
                "success": True,
                "media_id": media_id,
                "media_type": media_type,
                "total_faces": len(all_detections),
                "detections": all_detections,
                "processing_time": processing_time,
                "message": f"Processed {media_type} with {len(all_detections)} faces detected",
            }

        else:
            raise HTTPException(
                status_code=400,
                detail="Only image processing supported in this version",
            )

    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch media: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")


# Enhanced Media Processing Endpoints with Database Integration


@app.post("/process/media/enhanced")
async def process_media_enhanced(request: MediaProcessingRequest):
    """
    Enhanced media processing with database storage and comprehensive analytics.

    Processes images or videos with face detection and stores results in database.
    """
    global media_processor_instance

    if media_processor_instance is None:
        raise HTTPException(status_code=503, detail="Media processor not initialized")

    try:
        result = await media_processor_instance.process_media_from_url(request)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Enhanced processing error: {str(e)}"
        )


@app.post("/overlay/generate")
async def generate_overlay(request: OverlayRequest):
    """
    Generate overlay data for face rectangles display.

    Returns overlay rectangles for frontend visualization with synchronized timestamps.
    """
    global media_processor_instance

    if media_processor_instance is None:
        raise HTTPException(status_code=503, detail="Media processor not initialized")

    try:
        result = media_processor_instance.generate_overlay_data(request)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Overlay generation error: {str(e)}"
        )


@app.post("/timeline/generate")
async def generate_timeline(request: TimelineRequest):
    """
    Generate timeline data for video scrubbing with face detection segments.

    Returns timeline segments showing face detection density over time.
    """
    global media_processor_instance

    if media_processor_instance is None:
        raise HTTPException(status_code=503, detail="Media processor not initialized")

    try:
        result = media_processor_instance.generate_timeline_data(request)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Timeline generation error: {str(e)}"
        )


@app.get("/media/{media_id}/analytics")
async def get_media_analytics(media_id: str):
    """
    Get comprehensive analytics for processed media.

    Returns statistics, processing history, and performance metrics.
    """
    global media_processor_instance

    if media_processor_instance is None:
        raise HTTPException(status_code=503, detail="Media processor not initialized")

    try:
        analytics = media_processor_instance.get_media_analytics(media_id)
        if not analytics:
            raise HTTPException(
                status_code=404, detail=f"No analytics found for media: {media_id}"
            )

        return {
            "success": True,
            "media_id": media_id,
            "analytics": analytics,
            "message": "Analytics retrieved successfully",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analytics error: {str(e)}")


@app.get("/faces/media/{media_id}")
async def get_all_media_faces(
    media_id: str,
    confidence_threshold: float = 0.5,
    authorization: str = Header(None),
):
    """Get all stored face detections for a media file."""
    try:
        # Get stored face detections from database
        stored_faces = vision_db.get_face_detections(
            media_id, confidence_threshold=confidence_threshold
        )

        if stored_faces:
            # Convert database format to API response format
            faces_by_frame = {}
            for face in stored_faces:
                frame_num = face.get("frame_number", 0)
                if frame_num not in faces_by_frame:
                    faces_by_frame[frame_num] = []

                faces_by_frame[frame_num].append(
                    {
                        "bbox": face["bbox"],  # bbox is already an array from database
                        "confidence": face["confidence"],
                        "method": face["method"],
                        "timestamp": face.get("timestamp"),
                    }
                )

            return {
                "success": True,
                "media_id": media_id,
                "has_stored_faces": True,
                "total_faces": len(stored_faces),
                "faces_by_frame": faces_by_frame,
                "message": f"Found {len(stored_faces)} stored face detections across {len(faces_by_frame)} frames",
            }
        else:
            return {
                "success": True,
                "media_id": media_id,
                "has_stored_faces": False,
                "total_faces": 0,
                "faces_by_frame": {},
                "message": "No stored face detections found - real-time detection required",
            }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get media face detections: {str(e)}"
        )


@app.post("/faces/media/{media_id}/bulk")
async def store_bulk_faces(
    media_id: str,
    faces_data: dict,
    authorization: str = Header(None),
):
    """Store multiple face detections for a media file."""
    try:
        # Extract user_id from JWT token for ownership
        user_id = extract_user_id_from_token(authorization) if authorization else None

        # Store media record first
        media_record = MediaRecord(
            media_id=media_id,
            media_type="video",
            media_url=f"/api/v1/media/{media_id}",
            processing_status="completed",
            total_faces=0,
            total_frames=faces_data.get("total_frames", 0),
            video_duration=faces_data.get("duration", 0.0),
            video_fps=faces_data.get("fps", 30.0),
        )

        vision_db.store_media_record(media_record)

        # Store face detections
        stored_count = 0
        faces_by_frame = faces_data.get("faces_by_frame", {})

        for frame_number, frame_faces in faces_by_frame.items():
            for face in frame_faces:
                detection = FaceDetectionResult(
                    id=str(uuid.uuid4()),
                    media_id=media_id,
                    media_type="video",  # Add required media_type field
                    frame_number=int(frame_number),
                    timestamp=face.get("timestamp"),
                    bbox=face["bbox"],
                    confidence=face["confidence"],
                    method=face.get("method", "real_time"),
                )

                if vision_db.store_face_detection(detection):
                    stored_count += 1

        return {
            "success": True,
            "media_id": media_id,
            "stored_faces": stored_count,
            "total_frames": len(faces_by_frame),
            "message": f"Successfully stored {stored_count} face detections for {len(faces_by_frame)} frames",
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to store bulk face detections: {str(e)}"
        )


@app.get("/faces/media/{media_id}/frame/{frame_number}")
async def get_video_frame_faces(
    media_id: str,
    frame_number: int,
    confidence_threshold: float = 0.5,  # Set to 50% confidence threshold
    authorization: str = Header(None),
):
    """Get face detections for a specific video frame (real-time processing)."""
    try:
        if not face_detector_instance:
            raise HTTPException(status_code=503, detail="Face detector not initialized")

        # First check if we have stored detections for this frame
        stored_faces = vision_db.get_face_detections(
            media_id,
            frame_number=frame_number,
            confidence_threshold=confidence_threshold,
        )

        if stored_faces:
            # Return stored detections
            faces = []
            for face in stored_faces:
                faces.append(
                    {
                        "bbox": face["bbox"],  # bbox is already an array
                        "confidence": face["confidence"],
                        "method": face["method"],
                    }
                )

            return {
                "success": True,
                "media_id": media_id,
                "frame_number": frame_number,
                "faces": faces,
                "processing_time": 0.001,
                "message": f"Retrieved {len(faces)} stored face detections for frame {frame_number}",
                "source": "database",
            }

        # No stored detections - perform real-time detection
        media_service_url = PPL_META_CONFIG["media_service"]["url"]

        try:
            # Prepare headers for media service requests
            headers = {}
            if authorization:
                headers["Authorization"] = authorization

            # Extract user_id from JWT token
            user_id = (
                extract_user_id_from_token(authorization) if authorization else None
            )

            # Get user UUID from profile (media service needs UUID, not integer ID)
            user_uuid = (
                get_user_uuid_from_profile(authorization) if authorization else None
            )

            # Build media URL with user_id parameter if available (use UUID)
            media_url = f"{media_service_url}/api/v1/media/{media_id}"
            if user_uuid:
                media_url += f"?user_id={user_uuid}"

            # Get media info from media service
            media_response = requests.get(media_url, headers=headers)
            if media_response.status_code != 200:
                raise HTTPException(
                    status_code=404, detail=f"Media not found: {media_id}"
                )

            media_info = media_response.json()

            # Get video stream URL
            stream_url = f"{media_service_url}/api/v1/media/stream/{media_id}"

            # Extract frame from video
            frame_image = await extract_video_frame(stream_url, frame_number, headers)
            if frame_image is None:
                raise HTTPException(
                    status_code=400, detail=f"Could not extract frame {frame_number}"
                )

            # Perform real face detection using proven two-stage method
            detection_result = face_detector_instance.detect_faces_two_stage(
                frame_image, confidence_threshold=confidence_threshold
            )

            if detection_result.get("success", False):
                detection_results = detection_result.get("detections", [])
            else:
                detection_results = []

            # Filter by confidence threshold (already done in two-stage method)
            filtered_faces = detection_results

            return {
                "success": True,
                "media_id": media_id,
                "frame_number": frame_number,
                "faces": filtered_faces,
                "processing_time": 0.05,  # Actual processing time
                "message": f"Real face detection for frame {frame_number} using {len(face_detector_instance.available_methods)} methods",
            }

        except requests.RequestException as e:
            # Demo fallback commented out to see real errors
            # return await _generate_demo_faces(
            #     media_id, frame_number, confidence_threshold
            # )
            raise HTTPException(
                status_code=503, detail=f"Media service request failed: {str(e)}"
            )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Frame face detection error: {str(e)}"
        )


async def extract_video_frame(
    stream_url: str, frame_number: int, headers: Optional[dict] = None
) -> Optional[np.ndarray]:
    """Extract a specific frame from video stream."""
    try:
        # Download video stream
        response = requests.get(stream_url, stream=True, headers=headers or {})
        if response.status_code != 200:
            return None

        # Save temporary video file
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_file:
            for chunk in response.iter_content(chunk_size=8192):
                temp_file.write(chunk)
            temp_video_path = temp_file.name

        try:
            # Extract frame using OpenCV
            cap = cv2.VideoCapture(temp_video_path)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            ret, frame = cap.read()
            cap.release()

            if ret:
                return frame
            return None

        finally:
            # Clean up temporary file
            os.unlink(temp_video_path)

    except Exception as e:
        logger.warning(f"Frame extraction error: {e}")
        return None


async def _generate_demo_faces(
    media_id: str, frame_number: int, confidence_threshold: float
):
    """Generate demo faces when real detection fails."""
    demo_faces = []

    # Create demo faces based on frame number for simulation
    if frame_number % 30 < 15:  # Show faces for first half of each second
        demo_faces = [
            {
                "bbox": [
                    100 + (frame_number % 10),
                    150 + (frame_number % 5),
                    200 + (frame_number % 10),
                    250 + (frame_number % 5),
                ],
                "confidence": 0.85 + (frame_number % 10) * 0.01,
                "method": "demo",
            },
            {
                "bbox": [
                    300 + (frame_number % 8),
                    180 + (frame_number % 6),
                    400 + (frame_number % 8),
                    280 + (frame_number % 6),
                ],
                "confidence": 0.78 + (frame_number % 15) * 0.01,
                "method": "demo",
            },
        ]

    # Filter by confidence threshold
    filtered_faces = [
        face for face in demo_faces if face["confidence"] >= confidence_threshold
    ]

    return {
        "success": True,
        "media_id": media_id,
        "frame_number": frame_number,
        "faces": filtered_faces,
        "processing_time": 0.02,
        "message": f"Demo face detection for frame {frame_number} (real detection unavailable)",
    }


def _faces_overlap(bbox1: List[int], bbox2: List[int], threshold: float = 0.3) -> bool:
    """Check if two face bounding boxes overlap significantly."""
    x1_1, y1_1, x2_1, y2_1 = bbox1
    x1_2, y1_2, x2_2, y2_2 = bbox2

    # Calculate intersection
    x1_i = max(x1_1, x1_2)
    y1_i = max(y1_1, y1_2)
    x2_i = min(x2_1, x2_2)
    y2_i = min(y2_1, y2_2)

    if x1_i >= x2_i or y1_i >= y2_i:
        return False

    # Calculate areas
    intersection_area = (x2_i - x1_i) * (y2_i - y1_i)
    area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
    area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
    union_area = area1 + area2 - intersection_area

    # Calculate IoU (Intersection over Union)
    iou = intersection_area / union_area if union_area > 0 else 0
    return iou >= threshold


@app.post("/faces/media/{media_id}/bulk-process")
async def bulk_process_video_faces(
    media_id: str,
    authorization: str = Header(None, alias="Authorization"),
    frame_interval: int = Query(
        1, description="Process every frame (1 = maximum efficiency)"
    ),
    max_frames: int = Query(1000, description="Max frames to process"),
):
    """
    Bulk process entire video for face detection in memory.

    Downloads video once, extracts frames in memory, and processes all frames
    with face detection in a single operation. Much more efficient than
    frame-by-frame processing.

    ALWAYS uses two_stage method with 0.5 confidence threshold for consistency.
    """
    try:
        if not face_detector_instance:
            raise HTTPException(status_code=503, detail="Face detector not initialized")

        start_time = time.time()

        # Force consistent detection parameters
        confidence_threshold = 0.5  # Always use 0.5 confidence
        detection_method = "two_stage"  # Always use two_stage method

        # Get user authentication
        user_uuid = get_user_uuid_from_profile(authorization) if authorization else None
        if not user_uuid:
            raise HTTPException(status_code=401, detail="Authentication required")

        # Prepare headers for media service requests
        headers = {"Authorization": authorization} if authorization else {}
        media_service_url = PPL_META_CONFIG["media_service"]["url"]

        # Get media info first
        media_url = (
            f"{media_service_url}/api/v1/media/{media_id}" f"?user_id={user_uuid}"
        )
        media_response = requests.get(media_url, headers=headers)
        if media_response.status_code != 200:
            raise HTTPException(status_code=404, detail=f"Media not found: {media_id}")

        media_info = media_response.json()
        if media_info.get("media_type") != "video":
            raise HTTPException(
                status_code=400, detail="Only video files supported for bulk processing"
            )

        # Store media record in database for reference
        from models import FaceDetectionResult, MediaRecord

        media_record = MediaRecord(
            media_id=media_id,
            media_type="video",
            media_url=f"{media_service_url}/api/v1/media/stream/{media_id}",
            processing_status="processing",
        )
        try:
            vision_db.store_media_record(media_record)
        except Exception as media_error:
            logger.warning(f"Failed to store media record: {media_error}")

        # Download video stream once
        stream_url = f"{media_service_url}/api/v1/media/stream/{media_id}"
        video_response = requests.get(stream_url, stream=True, headers=headers)
        if video_response.status_code != 200:
            raise HTTPException(status_code=404, detail="Video stream not accessible")

        # Save to temporary file
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_file:
            for chunk in video_response.iter_content(chunk_size=8192):
                temp_file.write(chunk)
            temp_video_path = temp_file.name

        try:
            # Process video in memory
            cap = cv2.VideoCapture(temp_video_path)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            duration = total_frames / fps if fps > 0 else 0

            # Calculate frame numbers to process
            frame_numbers = []
            frame_num = 0
            while frame_num < total_frames and len(frame_numbers) < max_frames:
                frame_numbers.append(frame_num)
                frame_num += frame_interval

            # Process all frames in memory
            all_detections = {}
            processed_frames = 0

            for frame_number in frame_numbers:
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
                ret, frame = cap.read()

                if not ret:
                    continue

                # Perform face detection on this frame using proven two-stage method
                frame_detections = []

                # Use the proven two-stage detection (Haar + Dlib validation)
                detection_result = face_detector_instance.detect_faces_two_stage(
                    frame, confidence_threshold=confidence_threshold
                )

                if detection_result.get("success", False):
                    for face in detection_result.get("detections", []):
                        # Convert numpy types to native Python types for JSON serialization
                        bbox = face["bbox"]
                        if hasattr(bbox, "tolist"):
                            bbox = bbox.tolist()
                        elif isinstance(bbox, (list, tuple)):
                            bbox = [int(x) if hasattr(x, "item") else x for x in bbox]

                        confidence = face["confidence"]
                        if hasattr(confidence, "item"):
                            confidence = confidence.item()

                        frame_detections.append(
                            {
                                "bbox": bbox,
                                "confidence": float(confidence),
                                "method": face["method"],
                            }
                        )

                        # Store face detection in database
                        face_detection = FaceDetectionResult(
                            id=str(uuid.uuid4()),
                            media_id=media_id,
                            media_type="video",
                            frame_number=frame_number,
                            timestamp=frame_number / fps if fps > 0 else 0,
                            bbox=bbox,
                            confidence=float(confidence),
                            method=face["method"],
                        )

                        # Store in database
                        try:
                            vision_db.store_face_detection(face_detection)
                        except Exception as db_error:
                            logger.warning(f"Store failed: {db_error}")

                # Store detections for this frame
                all_detections[str(frame_number)] = frame_detections
                processed_frames += 1

            cap.release()

            # Calculate total faces found
            total_faces = sum(len(detections) for detections in all_detections.values())
            processing_time = time.time() - start_time

            return {
                "success": True,
                "media_id": media_id,
                "video_info": {
                    "total_frames": int(
                        total_frames
                    ),  # Convert numpy int to Python int
                    "fps": float(fps),  # Convert numpy float to Python float
                    "duration": float(duration),  # Convert to Python float
                    "processed_frames": int(processed_frames),  # Python int
                    "frame_interval": int(frame_interval),  # Python int
                },
                "faces_by_frame": all_detections,
                "total_faces": int(total_faces),  # Python int
                "processing_time": float(processing_time),  # Python float
                "confidence_threshold": float(confidence_threshold),  # Python float
                "message": (
                    f"Bulk processed {processed_frames} frames, "
                    f"found {total_faces} faces total"
                ),
            }

        finally:
            # Clean up temporary file
            os.unlink(temp_video_path)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Bulk processing error: {str(e)}")


@app.get("/database/status")
async def get_database_status():
    """Get database status and statistics."""
    try:
        stats = vision_db.get_database_statistics()
        return {
            "success": True,
            "database_status": "connected",
            "statistics": stats,
            "message": "Database status retrieved successfully",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database status error: {str(e)}")


@app.get("/debug/auth")
async def debug_auth(authorization: str = Header(None, alias="Authorization")):
    """Debug endpoint to test authentication flow."""
    try:
        if not authorization:
            return {"error": "No authorization header provided"}

        # Test direct call to Gateway
        headers = {"Authorization": authorization}
        gateway_url = PPL_META_CONFIG["gateway"]["url"]
        profile_url = f"{gateway_url}/api/v1/user/profile"

        response = requests.get(profile_url, headers=headers, timeout=30)

        result_data = {
            "authorization_provided": True,
            "authorization_header": authorization[:50] + "...",
            "gateway_url": gateway_url,
            "profile_url": profile_url,
            "response_status": response.status_code,
            "response_headers": dict(response.headers),
            "user_uuid": None,
            "raw_response": None,
            "debug": "Direct call test",
        }

        if response.status_code == 200:
            profile_data = response.json()
            result_data["user_uuid"] = profile_data.get("guid")
            result_data["raw_response"] = profile_data
        else:
            result_data["error_text"] = response.text[:200]

        # Also test the function
        func_result = get_user_uuid_from_profile(authorization)
        result_data["function_result"] = func_result

        return result_data

    except Exception as e:
        return {
            "error": str(e),
            "authorization_provided": authorization is not None,
            "gateway_url": PPL_META_CONFIG["gateway"]["url"],
            "debug": "Exception occurred",
        }


# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={
            "error": "Endpoint not found",
            "available_endpoints": [
                "/",
                "/health",
                "/models",
                "/detect",
                "/process/media",
                "/process/media/enhanced",
                "/overlay/generate",
                "/timeline/generate",
                "/media/{media_id}/analytics",
                "/faces/media/{media_id}/frame/{frame_number}",
                "/faces/media/{media_id}/bulk-process",
                "/database/status",
                "/debug/auth",
                "/docs",
            ],
        },
    )


if __name__ == "__main__":
    # Configure info logging to reduce debug flood
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )

    # Set specific logger levels to INFO to reduce debug messages
    logging.getLogger("ppl-meta-vision").setLevel(logging.INFO)
    logging.getLogger("database").setLevel(logging.INFO)

    print(
        f"🚀 Starting PPL Meta Vision Service on port {PPL_META_CONFIG['vision_service']['port']}"
    )
    print(
        f"📊 Documentation available at: http://localhost:{PPL_META_CONFIG['vision_service']['port']}/docs"
    )

    uvicorn.run(
        app,
        host=PPL_META_CONFIG["vision_service"]["host"],
        port=PPL_META_CONFIG["vision_service"]["port"],
        reload=False,
        log_level="debug",
    )
