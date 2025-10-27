"""
PPL Meta Vision Service - Enhanced Production Entry Point
Generated from VIS-001.3 + VIS-001.4 - Media Processing Integration

This service processes media files from the PPL Meta Media Service,
performs face detection, stores results to database, and provides
overlay data for synchronized media playback.
"""

import base64
import io
import logging
import os
import sys
import tempfile
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add the current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Image Processing & ML
import cv2
import numpy as np
import requests
import uvicorn

# Database and models
from database import VisionDatabase

# Import our extracted face detector
from extracted_face_detector import ExtractedFaceDetector

# Web Framework & API
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from models import FaceDetectionResult, MediaRecord
from PIL import Image
from pydantic import BaseModel, Field

# PPL Meta Platform Configuration
PPL_META_CONFIG = {
    "vision_service": {
        "port": 8003,
        "host": "0.0.0.0",
        "name": "ppl-meta-vision",
        "version": "1.1.0",  # Updated for media integration
    },
    "media_service": {"url": "http://localhost:8000", "timeout": 30},
    "gateway": {"url": "http://localhost:8080", "health_endpoint": "/health"},
    "orchestrator": {
        "url": "http://localhost:8002",
        "register_endpoint": "/services/register",
    },
}


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


# Enhanced models for media processing
class MediaProcessingRequest(BaseModel):
    """Request to process media from Media Service."""

    media_id: str = Field(..., description="Media ID from Media Service")
    media_type: str = Field(..., description="Type: 'image' or 'video'")
    media_url: str = Field(..., description="URL to fetch media from Media Service")
    processing_options: Optional[Dict[str, Any]] = Field(
        default=None, description="Processing options"
    )


class FaceDetectionResult(BaseModel):
    """Individual face detection result with metadata."""

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), description="Unique detection ID"
    )
    media_id: str = Field(..., description="Source media ID")
    frame_number: Optional[int] = Field(
        default=None, description="Frame number for video"
    )
    timestamp: Optional[float] = Field(
        default=None, description="Timestamp in video (seconds)"
    )
    bbox: List[int] = Field(..., description="Bounding box [x1, y1, x2, y2]")
    confidence: float = Field(..., description="Detection confidence")
    method: str = Field(..., description="Detection method used")
    created_at: datetime = Field(default_factory=datetime.now)


class MediaProcessingResponse(BaseModel):
    """Response from media processing."""

    success: bool = Field(..., description="Processing success status")
    media_id: str = Field(..., description="Processed media ID")
    total_faces: int = Field(..., description="Total faces detected")
    total_frames: Optional[int] = Field(
        default=None, description="Total frames processed (video)"
    )
    processing_time: float = Field(..., description="Total processing time")
    detections: List[FaceDetectionResult] = Field(
        ..., description="All face detections"
    )
    message: Optional[str] = Field(default=None)


class MediaOverlayRequest(BaseModel):
    """Request for media overlay data."""

    media_id: str = Field(..., description="Media ID")
    frame_number: Optional[int] = Field(
        default=None, description="Specific frame for video"
    )
    timestamp: Optional[float] = Field(default=None, description="Timestamp for video")
    confidence_threshold: Optional[float] = Field(
        default=0.5, description="Minimum confidence"
    )


class MediaOverlayResponse(BaseModel):
    """Response with overlay data for media player."""

    media_id: str = Field(..., description="Media ID")
    overlays: List[Dict[str, Any]] = Field(
        ..., description="Overlay rectangles with metadata"
    )
    frame_info: Optional[Dict[str, Any]] = Field(
        default=None, description="Frame information"
    )


# Initialize FastAPI application
app = FastAPI(
    title="PPL Meta Vision Service",
    description="Face detection microservice for PPL Meta Platform with media processing integration",
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
vision_database = None
service_start_time = time.time()

# Simulated database storage (in production, use PostgreSQL/MongoDB)
face_detections_db = []
media_processing_jobs = {}


# Helper functions
def store_face_detection(detection: FaceDetectionResult):
    """Store face detection to database."""
    face_detections_db.append(detection.dict())
    return True


def get_faces_by_media_id(
    media_id: str, frame_number: Optional[int] = None
) -> List[Dict]:
    """Retrieve face detections for a media file."""
    global vision_database
    
    # Use real database if available
    if vision_database and vision_database.connection:
        return vision_database.get_face_detections(media_id, frame_number)
    
    # Fallback to in-memory database (for development/testing)
    results = [d for d in face_detections_db if d["media_id"] == media_id]

    if frame_number is not None:
        results = [d for d in results if d.get("frame_number") == frame_number]

    return results


def process_image_frames(
    image_data: np.ndarray, media_id: str, face_detector
) -> List[FaceDetectionResult]:
    """Process a single image for face detection."""
    detections = []

    # Use multi-method detection
    results = face_detector.detect_faces_multi_method(image_data)

    for method, result in results.items():
        if result.get("success", False):
            for detection in result.get("detections", []):
                face_result = FaceDetectionResult(
                    media_id=media_id,
                    bbox=detection["bbox"],
                    confidence=detection["confidence"],
                    method=detection["method"],
                )
                detections.append(face_result)
                store_face_detection(face_result)

    return detections


def process_video_frames(
    video_path: str, media_id: str, face_detector
) -> List[FaceDetectionResult]:
    """Process video frames for face detection."""
    detections = []

    try:
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        frame_number = 0

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            # Calculate timestamp
            timestamp = frame_number / fps if fps > 0 else 0

            # Process every 10th frame to reduce processing time
            if frame_number % 10 == 0:
                results = face_detector.detect_faces_multi_method(frame)

                for method, result in results.items():
                    if result.get("success", False):
                        for detection in result.get("detections", []):
                            face_result = FaceDetectionResult(
                                media_id=media_id,
                                frame_number=frame_number,
                                timestamp=timestamp,
                                bbox=detection["bbox"],
                                confidence=detection["confidence"],
                                method=detection["method"],
                            )
                            detections.append(face_result)
                            store_face_detection(face_result)

            frame_number += 1

        cap.release()

    except Exception as e:
        logging.error(f"Error processing video: {e}")

    return detections


# Initialize face detector on startup
@app.on_event("startup")
async def startup_event():
    """Initialize face detector and database on startup."""
    global face_detector_instance, vision_database
    try:
        face_detector_instance = ExtractedFaceDetector()
        vision_database = VisionDatabase()
        print("🎯 Face detector initialized successfully")
        print(f"📊 Available methods: {face_detector_instance.available_methods}")
        print("🗄️ Vision database initialized")
    except Exception as e:
        print(f"❌ Failed to initialize service: {e}")
        face_detector_instance = None
        vision_database = None


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
            "process_media": "/process/media",
            "media_faces": "/faces/media/{media_id}",
            "overlay": "/faces/overlay",
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


# Enhanced Media Processing Endpoints


@app.post(
    "/process/media",
    response_model=MediaProcessingResponse,
    summary="Process Media File",
)
async def process_media(request: MediaProcessingRequest):
    """Process media file from Media Service for face detection."""
    global face_detector_instance

    if face_detector_instance is None:
        raise HTTPException(status_code=503, detail="Face detector not initialized")

    start_time = time.time()

    try:
        # Fetch media from Media Service
        media_response = requests.get(
            request.media_url, timeout=PPL_META_CONFIG["media_service"]["timeout"]
        )
        if media_response.status_code != 200:
            raise HTTPException(
                status_code=400, detail="Failed to fetch media from Media Service"
            )

        # Process based on media type
        if request.media_type == "image":
            # Decode image
            image_array = np.asarray(bytearray(media_response.content), dtype=np.uint8)
            image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

            detections = process_image_frames(
                image, request.media_id, face_detector_instance
            )
            total_frames = 1

        elif request.media_type == "video":
            # Save video temporarily and process
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_file:
                temp_file.write(media_response.content)
                temp_video_path = temp_file.name

            try:
                detections = process_video_frames(
                    temp_video_path, request.media_id, face_detector_instance
                )

                # Get frame count
                cap = cv2.VideoCapture(temp_video_path)
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                cap.release()
            finally:
                # Clean up temp file
                if os.path.exists(temp_video_path):
                    os.remove(temp_video_path)

        else:
            raise HTTPException(status_code=400, detail="Unsupported media type")

        processing_time = time.time() - start_time

        return MediaProcessingResponse(
            success=True,
            media_id=request.media_id,
            total_faces=len(detections),
            total_frames=total_frames,
            processing_time=processing_time,
            detections=detections,
            message=f"Processed {request.media_type} with {len(detections)} faces detected",
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")


@app.get("/faces/media/{media_id}", summary="Get Faces for Media")
async def get_media_faces(media_id: str, confidence_threshold: Optional[float] = 0.5):
    """Get all face detections for a specific media file."""
    print(f"🔍 [VISION ENDPOINT] Received request for media_id: {media_id}")
    
    faces = get_faces_by_media_id(media_id)
    
    print(f"🔍 [VISION ENDPOINT] Query returned {len(faces)} faces")
    if faces:
        print(f"🔍 [VISION ENDPOINT] First face media_id: {faces[0].get('media_id')}")

    # Filter by confidence if specified
    if confidence_threshold:
        faces = [f for f in faces if f["confidence"] >= confidence_threshold]
    
    print(f"🔍 [VISION ENDPOINT] After confidence filter: {len(faces)} faces")
    print(f"🔍 [VISION ENDPOINT] Returning response with media_id: {media_id}")

    return {"media_id": media_id, "total_faces": len(faces), "faces": faces}


@app.get(
    "/faces/media/{media_id}/frame/{frame_number}",
    summary="Get Faces for Specific Frame",
)
async def get_frame_faces(media_id: str, frame_number: int):
    """Get face detections for a specific video frame."""
    faces = get_faces_by_media_id(media_id, frame_number)

    return {"media_id": media_id, "frame_number": frame_number, "faces": faces}


@app.post(
    "/faces/overlay",
    response_model=MediaOverlayResponse,
    summary="Generate Media Overlay",
)
async def generate_media_overlay(request: MediaOverlayRequest):
    """Generate overlay data for media player display."""
    faces = get_faces_by_media_id(request.media_id, request.frame_number)

    # Filter by confidence
    if request.confidence_threshold:
        faces = [f for f in faces if f["confidence"] >= request.confidence_threshold]

    # Format overlays for frontend
    overlays = []
    for face in faces:
        overlay = {
            "id": face["id"],
            "bbox": face["bbox"],
            "confidence": face["confidence"],
            "method": face["method"],
            "style": {
                "border": "2px solid #00ff00",
                "background": "rgba(0, 255, 0, 0.1)",
            },
        }

        if face.get("timestamp") is not None:
            overlay["timestamp"] = face["timestamp"]

        overlays.append(overlay)

    return MediaOverlayResponse(
        media_id=request.media_id,
        overlays=overlays,
        frame_info={"total_overlays": len(overlays)},
    )


@app.get("/faces/timeline/{media_id}", summary="Get Face Detection Timeline")
async def get_face_timeline(media_id: str):
    """Get face detection timeline for video playback."""
    faces = get_faces_by_media_id(media_id)

    # Group by timestamp/frame
    timeline = {}
    for face in faces:
        timestamp = face.get("timestamp", 0)
        frame = face.get("frame_number", 0)

        key = f"{timestamp:.2f}" if timestamp else f"frame_{frame}"

        if key not in timeline:
            timeline[key] = []

        timeline[key].append(
            {
                "bbox": face["bbox"],
                "confidence": face["confidence"],
                "method": face["method"],
            }
        )

    return {
        "media_id": media_id,
        "timeline": timeline,
        "total_timestamps": len(timeline),
    }


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


# Media Service Integration Endpoints


class BulkFaceDetectionResult(BaseModel):
    """Model for bulk face detection results from Media Service."""

    media_id: str = Field(..., description="Media item identifier")
    frame_number: Optional[int] = Field(default=None, description="Video frame number")
    timestamp: Optional[float] = Field(
        default=None, description="Video timestamp in seconds"
    )
    detections: List[FaceDetection] = Field(..., description="List of detected faces")
    processing_metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Processing metadata"
    )


class BulkFaceDetectionRequest(BaseModel):
    """Request model for storing bulk face detection results."""

    workflow_id: str = Field(..., description="Workflow identifier")
    results: List[BulkFaceDetectionResult] = Field(
        ..., description="Bulk detection results"
    )
    source_service: str = Field(
        default="ppl-meta-media", description="Source service name"
    )


@app.post(
    "/faces/bulk-store",
    summary="Store Bulk Face Detection Results",
    description="Receive and store bulk face detection results from workflows",
)
async def store_bulk_face_detection_results(request: BulkFaceDetectionRequest):
    """
    Store bulk face detection results from Media Service workflows.

    This endpoint allows Media Service to send processed face detection results
    to Vision Service for storage and analytics processing.
    """
    global vision_database

    try:
        stored_count = 0
        failed_count = 0

        print(f"Receiving bulk results from workflow {request.workflow_id}")
        print(f"Processing {len(request.results)} media items with faces")

        for result in request.results:
            try:
                # Store each detection for this media item
                for detection in result.detections:
                    # Create FaceDetectionResult for database storage
                    face_result = FaceDetectionResult(
                        media_id=result.media_id,
                        frame_number=result.frame_number,
                        timestamp=result.timestamp,
                        bbox=[
                            detection.bbox[0],
                            detection.bbox[1],
                            detection.bbox[2],
                            detection.bbox[3],
                        ],
                        confidence=detection.confidence,
                        method=detection.method,
                    )

                    # Store in database
                    if vision_database and vision_database.store_face_detection(
                        face_result
                    ):
                        stored_count += 1
                    else:
                        failed_count += 1
                        print(f"Failed to store face for {result.media_id}")

                print(
                    f"Processed {len(result.detections)} faces "
                    f"for {result.media_id}"
                )

            except Exception as e:
                failed_count += len(result.detections)
                print(f"Failed to process results for {result.media_id}: {e}")
                continue

        # Update analytics after bulk storage
        total_processed = stored_count + failed_count
        success_rate = (
            (stored_count / total_processed * 100) if total_processed > 0 else 0
        )

        response = {
            "success": True,
            "workflow_id": request.workflow_id,
            "source_service": request.source_service,
            "summary": {
                "media_items_processed": len(request.results),
                "faces_stored": stored_count,
                "faces_failed": failed_count,
                "success_rate_percent": round(success_rate, 2),
            },
            "message": (
                f"Stored {stored_count} faces from " f"{len(request.results)} items"
            ),
        }

        print(
            f"Bulk storage complete: {stored_count} stored, " f"{failed_count} failed"
        )
        return response

    except Exception as e:
        print(f"Failed to store bulk face detection results: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to store bulk results: {str(e)}"
        )


@app.get(
    "/analytics/workflow/{workflow_id}",
    summary="Get Workflow Analytics",
    description="Get analytics data for faces stored from a specific workflow",
)
async def get_workflow_analytics(workflow_id: str):
    """
    Get analytics data for faces stored from a Media Service workflow.

    Provides insights into face detection results processed by this Vision Service
    from a specific Media Service workflow.
    """
    global vision_database

    try:
        if not vision_database:
            raise HTTPException(status_code=503, detail="Database not available")

        # This would require adding workflow tracking to the database
        # For now, return basic structure
        analytics = {
            "workflow_id": workflow_id,
            "status": "Data processing complete",
            "face_analytics": {
                "total_faces_stored": "Available via existing endpoints",
                "confidence_distribution": "Available via existing endpoints",
                "method_performance": "Available via existing endpoints",
            },
            "cross_video_analytics": {
                "potential_matches": "Enhanced analytics coming soon",
                "face_clustering": "Enhanced analytics coming soon",
            },
            "message": "Use existing /faces/media/{media_id} endpoints for detailed data",
        }

        return analytics

    except Exception as e:
        print(f"Failed to get workflow analytics: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get workflow analytics: {str(e)}"
        )


# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return {
        "error": "Endpoint not found",
        "available_endpoints": [
            "/",
            "/health",
            "/models",
            "/detect",
            "/process/media",
            "/faces/bulk-store",
            "/analytics/workflow/{workflow_id}",
            "/docs",
        ],
    }


if __name__ == "__main__":
    print(
        f"🚀 Starting PPL Meta Vision Service v{PPL_META_CONFIG['vision_service']['version']} on port {PPL_META_CONFIG['vision_service']['port']}"
    )
    print(
        f"📊 Documentation available at: http://localhost:{PPL_META_CONFIG['vision_service']['port']}/docs"
    )
    print(f"🎥 Media processing integration enabled")

    uvicorn.run(
        app,
        host=PPL_META_CONFIG["vision_service"]["host"],
        port=PPL_META_CONFIG["vision_service"]["port"],
        reload=False,
        log_level="info",
    )
