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
from fastapi import BackgroundTasks, Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from media_processor import MediaProcessingService
from models import BaseResponse, MediaProcessingRequest, OverlayRequest, TimelineRequest
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
                "/database/status",
                "/docs",
            ],
        },
    )


if __name__ == "__main__":
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
        log_level="info",
    )
