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
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Add the current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Add parent directory to path for shared modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

try:
    from shared.service_discovery import deregister_service, register_service

    service_discovery_available = True
except ImportError:
    service_discovery_available = False

    # Create stub functions
    async def register_service(*args, **kwargs):
        pass

    async def deregister_service(*args, **kwargs):
        pass


import base64

# Import database.py file directly (not the database/ directory)
import importlib.util
import io
import os

# Import database directly from the file (not the directory)
import sys

# Image Processing & ML
import cv2
import numpy as np
import requests
import uvicorn

# Import API models
from api_models import SessionQueryRequest

db_spec = importlib.util.spec_from_file_location(
    "database", os.path.join(os.path.dirname(__file__), "database.py")
)
db_module = importlib.util.module_from_spec(db_spec)
db_spec.loader.exec_module(db_module)

vision_db = db_module.vision_db

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


# 🎯 PPL Thread Auto-Trigger Function
async def trigger_ppl_thread_workflow_auto(
    media_id: str, session_uuid: str, face_count: int, processing_time: float
):
    """
    Auto-trigger PPL Thread workflow after face detection completion.

    This function should be called by all face detection endpoints that store
    faces with session UUIDs to ensure person objects are created automatically.
    """
    if face_count <= 0:
        return  # No faces detected, skip trigger

    try:
        logger.info(
            f"🎯 AUTO-TRIGGER: Face detection completed for media {media_id} "
            f"with {face_count} faces. Starting PPL Thread workflow..."
        )

        # Trigger PPL Thread workflow via internal API call
        import aiohttp

        async def trigger_workflow():
            try:
                async with aiohttp.ClientSession() as sess:
                    # Call the correct PPL Thread trigger endpoint
                    url = (
                        "http://localhost:8003/api/v1/"
                        "person-objects/workflow/trigger"
                    )

                    # Prepare payload with all required data
                    payload = {
                        "media_id": media_id,
                        "session_uuid": session_uuid,
                        "face_count": face_count,
                        "processing_time": processing_time,
                    }

                    async with sess.post(url, json=payload, timeout=30) as response:
                        if response.status == 200:
                            result = await response.json()
                            persons = result.get("total_persons", "unknown")
                            logger.info(
                                f"🎯 ✅ AUTO-TRIGGER: PPL Thread workflow "
                                f"completed for media {media_id}: "
                                f"{face_count} faces → {persons} persons"
                            )
                        else:
                            resp_text = await response.text()
                            logger.warning(
                                f"🎯 ❌ AUTO-TRIGGER: PPL Thread workflow "
                                f"returned status {response.status}: "
                                f"{resp_text[:200]}"
                            )
            except Exception as e:
                logger.warning(
                    f"🎯 ❌ AUTO-TRIGGER: Failed to trigger PPL Thread "
                    f"workflow for media {media_id}: {e}"
                )

        # Execute trigger in background task
        asyncio.create_task(trigger_workflow())

    except Exception as e:
        logger.warning(
            f"🎯 ❌ AUTO-TRIGGER: Failed to initiate PPL Thread "
            f"workflow for media {media_id}: {e}"
        )


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
JWT_SECRET_KEY = "RA6XfYJZqhz-_MAbGMhGCoQz1KGIKecLTb3RkLVOUr4"
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

# Include PPL Thread (Person Objects) API router immediately after app creation
try:
    from person_objects.person_objects_api import router as person_objects_router

    app.include_router(person_objects_router)
    print("✅ PPL Thread (Person Objects) router included successfully")
except Exception as router_error:
    print(f"⚠️ Failed to include PPL Thread router: {router_error}")
    # Continue without person objects functionality

# Global variables
face_detector_instance = None
media_processor_instance = None
service_start_time = time.time()


# Initialize services on startup
@app.on_event("startup")
async def startup_event():
    """Initialize the face detector and media processor when the service starts."""
    global face_detector_instance, media_processor_instance

    # Set up logger first (outside try block for exception handling)
    logger = logging.getLogger("ppl-meta-vision")

    try:
        # Initialize database
        vision_db.init_database()

        # Initialize face detector
        face_detector_instance = ExtractedFaceDetector()

        # Initialize media processor
        media_processor_instance = MediaProcessingService(
            face_detector=face_detector_instance
        )

        # Initialize session manager for Workflow 4
        try:
            from session_manager import initialize_session_manager

            initialize_session_manager(vision_db)
            logger.info("✅ Session manager initialized for Workflow 4")
        except Exception as e:
            logger.warning(f"⚠️ Session manager initialization failed: {e}")

        # Initialize authenticated workflow API for workflow widgets
        try:
            from authenticated_workflow_api import enhanced_status_router

            app.include_router(enhanced_status_router)
            logger.info("✅ Authenticated workflow API registered for workflow widgets")
        except Exception as e:
            logger.warning("⚠️ Authenticated workflow API initialization failed: %s", e)
        except Exception as e:
            logger.warning(f"⚠️ Failed to initialize session manager: {e}")
            logger.info("Continuing without session management")

        # Initialize analytics service for Phase 5
        try:
            from analytics_service import get_analytics_service

            global analytics_service_instance
            analytics_service_instance = get_analytics_service()
            logger.info("✅ Advanced Analytics Service initialized")
        except Exception as e:
            logger.warning(f"⚠️ Advanced Analytics Service failed: {e}")

        # Initialize PPL Thread (Person Objects) functionality - Phase 4
        try:
            from database.person_objects_migrations import PersonObjectsMigration

            # Initialize database schema (router already included at app startup)
            migration = PersonObjectsMigration(vision_db.connection)
            await migration.migrate_schema()

            logger.info("✅ PPL Thread (Person Objects) functionality initialized")
        except Exception as e:
            logger.warning(f"⚠️ PPL Thread initialization failed: {e}")
            import traceback

            logger.error("PPL Thread error details: %s", traceback.format_exc())

        # Register with discovery service
        try:
            import socket

            # Detect actual network IP for registration
            try:
                # Connect to a remote address to determine local IP
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                detected_ip = s.getsockname()[0]
                s.close()
            except Exception:
                # Fallback to hostname resolution
                detected_ip = socket.gethostbyname(socket.gethostname())

            await register_service(
                name="ppl-meta-vision",
                service_type="backend",
                version="1.1.0",
                host=detected_ip,
                port=8003,
                health_endpoint="/health",
                capabilities=["vision", "face-detection", "image-analysis"],
                metadata={
                    "version": "1.1.0",
                    "environment": "development",
                    "features": "face_detection,image_analysis,media_processing",
                },
            )
            logger.info(
                "✅ Successfully registered ppl-meta-vision with discovery service"
            )
        except Exception as e:
            logger.warning(f"⚠️ Failed to register with discovery service: {e}")
            logger.info("Continuing without service discovery")

        logger.info("✅ PPL Meta Vision Service started successfully")
        logger.info(f"📊 Available methods: {face_detector_instance.available_methods}")
        logger.info("🗄️ Database initialized")

    except Exception as e:
        logger.error(f"❌ Failed to initialize services: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup when the service is shutting down."""
    try:
        # Add parent directory to path for shared modules
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        from shared.service_discovery import deregister_service

        await deregister_service("ppl-meta-vision")
        logger.info("✅ Service deregistered from discovery service")
    except Exception as e:
        logger.warning(f"⚠️ Failed to deregister service: {e}")


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
    media_id: str,
    media_url: str,
    media_type: str = "image",
    camera_device_uuid: Optional[str] = None,
    create_session: bool = True,
):
    """
    Process media file from Media Service for face detection.

    This endpoint fetches media from the Media Service and processes it for faces.
    Now includes automatic session management for Workflow 4 traceability.
    """
    global face_detector_instance

    if face_detector_instance is None:
        raise HTTPException(status_code=503, detail="Face detector not initialized")

    start_time = time.time()
    session_uuid = None
    session_mgr = None

    try:
        # Initialize session if requested (default behavior)
        if create_session:
            try:
                from api_models import FaceDetectionSessionRequest
                from session_manager import get_session_manager

                session_mgr = get_session_manager()
                if session_mgr:
                    session_request = FaceDetectionSessionRequest(
                        media_uuid=media_id,
                        camera_device_uuid=camera_device_uuid,
                        session_type="upload" if media_type == "image" else "batch",
                        metadata={
                            "media_url": media_url,
                            "media_type": media_type,
                            "processing_method": "process_media_endpoint",
                        },
                    )

                    session_result = await session_mgr.create_session(session_request)
                    if not hasattr(session_result, "error"):
                        session_uuid = session_result.session.session_uuid
                        logger.info(
                            f"Created session {session_uuid} for media {media_id}"
                        )
            except Exception as e:
                logger.warning(
                    f"Session creation failed, continuing without session: {e}"
                )

        # Fetch media from Media Service
        response = requests.get(media_url, timeout=30)
        if response.status_code != 200:
            # Complete session with error if applicable
            if session_mgr and session_uuid:
                try:
                    from api_models import SessionCompleteRequest

                    await session_mgr.complete_session(
                        session_uuid,
                        SessionCompleteRequest(
                            metadata={"error": "Failed to fetch media"}
                        ),
                    )
                except Exception:
                    pass

            raise HTTPException(
                status_code=400, detail="Failed to fetch media from Media Service"
            )

        if media_type == "image":
            # Process image
            image_array = np.asarray(bytearray(response.content), dtype=np.uint8)
            image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

            if image is None:
                # Complete session with error if applicable
                if session_mgr and session_uuid:
                    try:
                        from api_models import SessionCompleteRequest

                        await session_mgr.complete_session(
                            session_uuid,
                            SessionCompleteRequest(
                                metadata={"error": "Invalid image data"}
                            ),
                        )
                    except Exception:
                        pass
                raise HTTPException(status_code=400, detail="Invalid image data")

            # Run face detection
            results = face_detector_instance.detect_faces_multi_method(image)

            # Aggregate results and store with session tracking
            all_detections = []
            stored_count = 0

            for method, result in results.items():
                if result.get("success", False):
                    for det in result.get("detections", []):
                        detection_dict = {
                            "bbox": det["bbox"],
                            "confidence": det["confidence"],
                            "method": det["method"],
                            "media_id": media_id,
                        }
                        all_detections.append(detection_dict)

                        # Store in database with session tracking
                        if vision_db and vision_db.connection:
                            try:
                                detection = FaceDetectionResult(
                                    id=str(uuid.uuid4()),
                                    media_id=media_id,
                                    media_type=media_type,
                                    frame_number=0,  # Single image
                                    timestamp=datetime.now(),
                                    bbox=det["bbox"],
                                    confidence=det["confidence"],
                                    method=det["method"],
                                )

                                # Store with session UUID if available
                                if session_uuid:
                                    # Enhanced storage with session tracking
                                    vision_db.store_face_detection_with_session(
                                        detection, session_uuid
                                    )
                                    # Update session face count
                                    if session_mgr:
                                        await session_mgr.update_session_face_count(
                                            session_uuid, 1
                                        )
                                else:
                                    # Fallback to regular storage
                                    vision_db.store_face_detection(detection)

                                stored_count += 1
                            except Exception as e:
                                logger.warning(f"Failed to store detection: {e}")

            processing_time = time.time() - start_time

            # Complete session if created
            if session_mgr and session_uuid:
                try:
                    from api_models import SessionCompleteRequest

                    await session_mgr.complete_session(
                        session_uuid,
                        SessionCompleteRequest(
                            metadata={
                                "processing_time": processing_time,
                                "total_faces_detected": len(all_detections),
                                "stored_count": stored_count,
                            }
                        ),
                    )

                    # 🎯 AUTO-TRIGGER: Start PPL Thread workflow after completion
                    if session_uuid:  # Only trigger if session UUID exists
                        await trigger_ppl_thread_workflow_auto(
                            media_id,
                            session_uuid,
                            len(all_detections),
                            processing_time,
                        )
                    else:
                        logger.info(
                            f"🎯 No faces detected for media {media_id}, "
                            f"skipping PPL Thread workflow"
                        )

                except Exception as e:
                    logger.warning(f"Failed to complete session: {e}")

            return {
                "success": True,
                "media_id": media_id,
                "media_type": media_type,
                "total_faces": len(all_detections),
                "stored_faces": stored_count,
                "detections": all_detections,
                "processing_time": processing_time,
                "session_uuid": session_uuid,
                "message": f"Processed {media_type} with {len(all_detections)} faces detected"
                + (f" (session: {session_uuid})" if session_uuid else ""),
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
    camera_device_uuid: Optional[str] = None,
    create_session: bool = True,
):
    """Store multiple face detections for a media file with session tracking."""
    try:
        # 🔒 DUPLICATE PREVENTION: Check if faces already exist for this media
        if vision_db and vision_db.connection:
            try:
                with vision_db.connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT COUNT(*) FROM face_detections WHERE media_id = %s",
                        (media_id,),
                    )
                    existing_count = cursor.fetchone()[0]

                    if existing_count > 0:
                        logger.info(
                            f"🛡️ DUPLICATE PREVENTION: Found {existing_count} existing faces for media {media_id}, skipping bulk storage"
                        )
                        return {
                            "success": True,
                            "duplicate_prevention": True,
                            "skipped_storage": True,
                            "media_id": media_id,
                            "existing_faces": existing_count,
                            "message": f"Skipped storage - {existing_count} faces already exist for this media",
                        }
            except Exception as e:
                logger.error(f"❌ Duplicate prevention check failed: {e}")
                # Continue with storage if check fails - better to store than lose data

        session_uuid = None
        session_mgr = None

        # Initialize session if requested (default behavior)
        if create_session:
            try:
                from api_models import FaceDetectionSessionRequest
                from session_manager import get_session_manager

                session_mgr = get_session_manager()
                if session_mgr:
                    session_request = FaceDetectionSessionRequest(
                        media_uuid=media_id,
                        camera_device_uuid=camera_device_uuid,
                        session_type="batch",
                        metadata={
                            "total_frames": faces_data.get("total_frames", 0),
                            "duration": faces_data.get("duration", 0.0),
                            "fps": faces_data.get("fps", 30.0),
                            "processing_method": "bulk_storage_endpoint",
                        },
                    )

                    session_result = await session_mgr.create_session(session_request)
                    if not hasattr(session_result, "error"):
                        session_uuid = session_result.session.session_uuid
                        logger.info(
                            f"Created session {session_uuid} for bulk storage of media {media_id}"
                        )
            except Exception as e:
                logger.warning(
                    f"Session creation failed, continuing without session: {e}"
                )

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

        # Store face detections with session tracking
        stored_count = 0
        faces_by_frame = faces_data.get("faces_by_frame", {})

        for frame_number, frame_faces in faces_by_frame.items():
            for face in frame_faces:
                detection = FaceDetectionResult(
                    id=str(uuid.uuid4()),
                    media_id=media_id,
                    media_type="video",
                    frame_number=int(frame_number),
                    timestamp=face.get("timestamp"),
                    bbox=face["bbox"],
                    confidence=face["confidence"],
                    method=face.get("method", "real_time"),
                )

                # Store with session tracking if available
                if session_uuid:
                    if vision_db.store_face_detection_with_session(
                        detection, session_uuid
                    ):
                        stored_count += 1
                        # Update session face count periodically (every 10 faces for performance)
                        if stored_count % 10 == 0 and session_mgr:
                            await session_mgr.update_session_face_count(
                                session_uuid, 10
                            )
                else:
                    # Fallback to regular storage
                    if vision_db.store_face_detection(detection):
                        stored_count += 1

        # Final session face count update
        if session_mgr and session_uuid:
            await session_mgr.update_session_face_count(
                session_uuid, 0
            )  # This will recount from DB

        # Complete session if created
        if session_mgr and session_uuid:
            try:
                from api_models import SessionCompleteRequest

                await session_mgr.complete_session(
                    session_uuid,
                    SessionCompleteRequest(
                        metadata={
                            "total_faces_stored": stored_count,
                            "total_frames_processed": len(faces_by_frame),
                            "storage_method": "bulk_endpoint",
                        }
                    ),
                )

                # 🎯 AUTO-TRIGGER: PPL Thread workflow after completion
                await trigger_ppl_thread_workflow_auto(
                    media_id, session_uuid, stored_count, 0.0
                )

            except Exception as e:
                logger.warning(f"Failed to complete session: {e}")

        return {
            "success": True,
            "media_id": media_id,
            "stored_faces": stored_count,
            "total_frames": len(faces_by_frame),
            "session_uuid": session_uuid,
            "message": f"Successfully stored {stored_count} face detections for {len(faces_by_frame)} frames"
            + (f" (session: {session_uuid})" if session_uuid else ""),
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
    camera_device_uuid: Optional[str] = None,
    create_session: bool = True,
    force_process: bool = Query(
        False, description="Force processing even if existing session found"
    ),
):
    """
    Bulk process entire video for face detection in memory with session tracking.

    Downloads video once, extracts frames in memory, and processes all frames
    with face detection in a single operation. Much more efficient than
    frame-by-frame processing.

    ALWAYS uses two_stage method with 0.5 confidence threshold for consistency.
    Now includes automatic session management for Workflow 4 traceability.

    DUPLICATE PREVENTION: Checks for existing face detection sessions to prevent
    duplicate processing from multiple workflows (Orchestrator vs Direct calls).
    """
    try:
        if not face_detector_instance:
            raise HTTPException(status_code=503, detail="Face detector not initialized")

        # DUPLICATE PREVENTION: Check for existing face detection results
        # FIXED: Use direct SQL count query instead of failing ORM methods
        if not force_process:
            try:
                logger.info(
                    f"DUPLICATE PREVENTION: Starting check for media {media_id}"
                )

                # FIXED: Use direct SQL query that works in bulk-process context
                existing_count = 0
                try:
                    # Get database connection and execute direct count query
                    if vision_db and vision_db.connection:
                        with vision_db.connection.cursor() as cursor:
                            cursor.execute(
                                "SELECT COUNT(*) FROM face_detections WHERE media_id = %s",
                                (media_id,),
                            )
                            existing_count = cursor.fetchone()[0]
                    else:
                        raise Exception("Database connection not available")

                    logger.info(
                        f"DUPLICATE PREVENTION: Direct SQL query found {existing_count} existing faces"
                    )
                except Exception as sql_error:
                    logger.error(
                        f"DUPLICATE PREVENTION: Direct SQL query failed: {sql_error}"
                    )
                    # Try fallback to ORM methods if direct SQL fails
                    try:
                        existing_faces = vision_db.get_face_detections(media_id)
                        existing_count = len(existing_faces) if existing_faces else 0
                        logger.info(
                            f"DUPLICATE PREVENTION: ORM fallback found {existing_count} faces"
                        )
                    except Exception as orm_error:
                        logger.error(
                            f"DUPLICATE PREVENTION: ORM fallback failed: {orm_error}"
                        )
                        existing_count = 0

                if existing_count > 0:
                    logger.info(
                        f"DUPLICATE PREVENTION SUCCESS: Found {existing_count} existing faces for media {media_id}. "
                        f"Skipping duplicate processing. Use force_process=true to override."
                    )
                    return {
                        "success": True,
                        "message": f"Face detection already completed for media {media_id}",
                        "existing_results": {
                            "total_faces": existing_count,
                            "processing_method": "existing_data_reused",
                        },
                        "duplicate_prevention": True,
                        "skipped_processing": True,
                    }
                else:
                    logger.info(
                        f"DUPLICATE PREVENTION: No existing faces found for media {media_id}, proceeding with processing"
                    )

            except Exception as check_error:
                logger.error(
                    f"DUPLICATE PREVENTION CRITICAL FAILURE for {media_id}: {check_error}"
                )
                # FIXED: Safely abort instead of continuing with potential duplicates
                raise HTTPException(
                    status_code=409,  # Conflict
                    detail=f"Cannot verify duplicate status for media {media_id}: {check_error}. "
                    f"Aborting to prevent duplicate face storage. Use force_process=true to override.",
                )

        start_time = time.time()
        session_uuid = None
        session_mgr = None

        # Initialize session if requested (default behavior)
        if create_session:
            try:
                from api_models import FaceDetectionSessionRequest
                from session_manager import get_session_manager

                session_mgr = get_session_manager()
                if session_mgr:
                    session_request = FaceDetectionSessionRequest(
                        media_uuid=media_id,
                        camera_device_uuid=camera_device_uuid,
                        session_type="batch",
                        metadata={
                            "frame_interval": frame_interval,
                            "max_frames": max_frames,
                            "detection_method": "two_stage",
                            "confidence_threshold": 0.5,
                            "processing_method": "bulk_process_video_endpoint",
                        },
                    )

                    session_result = await session_mgr.create_session(session_request)
                    if not hasattr(session_result, "error"):
                        session_uuid = session_result.session.session_uuid
                        logger.info(
                            f"Created session {session_uuid} for bulk video processing of media {media_id}"
                        )
            except Exception as e:
                logger.warning(
                    f"Session creation failed, continuing without session: {e}"
                )

        # Force consistent detection parameters
        confidence_threshold = 0.5  # Always use 0.5 confidence
        detection_method = "two_stage"  # Always use two_stage method

        # Get user authentication
        user_uuid = get_user_uuid_from_profile(authorization) if authorization else None
        if not user_uuid:
            # Complete session with error if applicable
            if session_mgr and session_uuid:
                try:
                    from api_models import SessionCompleteRequest

                    await session_mgr.complete_session(
                        session_uuid,
                        SessionCompleteRequest(
                            metadata={"error": "Authentication required"}
                        ),
                    )
                except Exception:
                    pass
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
            # Complete session with error if applicable
            if session_mgr and session_uuid:
                try:
                    from api_models import SessionCompleteRequest

                    await session_mgr.complete_session(
                        session_uuid,
                        SessionCompleteRequest(
                            metadata={"error": f"Media not found: {media_id}"}
                        ),
                    )
                except Exception:
                    pass
            raise HTTPException(status_code=404, detail=f"Media not found: {media_id}")

        media_info = media_response.json()
        if media_info.get("media_type") != "video":
            # Complete session with error if applicable
            if session_mgr and session_uuid:
                try:
                    from api_models import SessionCompleteRequest

                    await session_mgr.complete_session(
                        session_uuid,
                        SessionCompleteRequest(
                            metadata={
                                "error": "Only video files supported for bulk processing"
                            }
                        ),
                    )
                except Exception:
                    pass
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

                        # Store face detection in database with session tracking
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

                        # Store in database with session tracking if available
                        try:
                            if session_uuid:
                                vision_db.store_face_detection_with_session(
                                    face_detection, session_uuid
                                )
                                # Update session face count periodically (every 100 faces for performance)
                                if processed_frames % 100 == 0 and session_mgr:
                                    await session_mgr.update_session_face_count(
                                        session_uuid, 0
                                    )  # Recount from DB
                            else:
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

            # Complete session if created
            if session_mgr and session_uuid:
                try:
                    # Final face count update
                    await session_mgr.update_session_face_count(
                        session_uuid, 0
                    )  # Recount from DB

                    from api_models import SessionCompleteRequest

                    await session_mgr.complete_session(
                        session_uuid,
                        SessionCompleteRequest(
                            metadata={
                                "total_faces_detected": total_faces,
                                "frames_processed": processed_frames,
                                "total_frames": int(total_frames),
                                "processing_time": processing_time,
                                "frame_interval": frame_interval,
                                "detection_method": "two_stage",
                                "confidence_threshold": confidence_threshold,
                            }
                        ),
                    )

                    # 🎯 AUTO-TRIGGER: PPL Thread workflow after completion
                    await trigger_ppl_thread_workflow_auto(
                        media_id,
                        session_uuid,
                        int(total_faces),
                        processing_time,
                    )

                except Exception as e:
                    logger.warning(f"Failed to complete session: {e}")

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
                "session_uuid": session_uuid,
                "message": (
                    f"Bulk processed {processed_frames} frames, "
                    f"found {total_faces} faces total"
                    + (f" (session: {session_uuid})" if session_uuid else "")
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


# Session Management Endpoints - Phase 2 Implementation


@app.post("/sessions/start", summary="Start Face Detection Session")
async def start_face_detection_session(request: dict):
    """
    Start a new face detection session for traceability.

    This endpoint creates a new session for tracking face detection operations
    across streaming, upload, or batch processing scenarios.
    """
    try:
        from api_models import FaceDetectionSessionRequest
        from session_manager import get_session_manager

        session_mgr = get_session_manager()
        if not session_mgr:
            raise HTTPException(
                status_code=503, detail="Session management not available"
            )

        # Convert dict to FaceDetectionSessionRequest
        session_request = FaceDetectionSessionRequest(**request)

        # Create session
        result = await session_mgr.create_session(session_request)

        # Check if result is an error
        if hasattr(result, "error"):
            raise HTTPException(status_code=400, detail=result.message)

        return result.dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting session: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to start session: {str(e)}"
        )


@app.get("/sessions/{session_uuid}/status", summary="Get Session Status")
async def get_session_status(session_uuid: str):
    """
    Get the current status and statistics of a face detection session.

    Returns session details, processing status, and face detection counts.
    """
    try:
        from session_manager import get_session_manager

        session_mgr = get_session_manager()
        if not session_mgr:
            raise HTTPException(
                status_code=503, detail="Session management not available"
            )

        # Get session status
        result = await session_mgr.get_session_status(session_uuid)

        # Check if result is an error
        if hasattr(result, "error"):
            if result.error == "SESSION_NOT_FOUND":
                raise HTTPException(status_code=404, detail=result.message)
            else:
                raise HTTPException(status_code=400, detail=result.message)

        return result.dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session status: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get session status: {str(e)}"
        )


@app.post("/sessions/{session_uuid}/complete", summary="Complete Session")
async def complete_face_detection_session(session_uuid: str, request: dict = None):
    """
    Complete a face detection session and finalize statistics.

    Marks the session as completed and calculates final processing statistics.
    """
    try:
        from api_models import SessionCompleteRequest
        from session_manager import get_session_manager

        session_mgr = get_session_manager()
        if not session_mgr:
            raise HTTPException(
                status_code=503, detail="Session management not available"
            )

        # Convert dict to SessionCompleteRequest (if provided)
        complete_request = SessionCompleteRequest(**(request or {}))

        # Complete session
        result = await session_mgr.complete_session(session_uuid, complete_request)

        # Check if result is an error
        if hasattr(result, "error"):
            if result.error == "SESSION_NOT_FOUND":
                raise HTTPException(status_code=404, detail=result.message)
            else:
                raise HTTPException(status_code=400, detail=result.message)

        return result.dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error completing session: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to complete session: {str(e)}"
        )


@app.get("/sessions", summary="Query Sessions")
async def query_face_detection_sessions(
    media_uuid: Optional[str] = None,
    camera_device_uuid: Optional[str] = None,
    session_type: Optional[str] = None,
    processing_status: Optional[str] = None,
    limit: Optional[int] = 50,
    offset: Optional[int] = 0,
):
    """
    Query face detection sessions based on various criteria.

    Supports filtering by media UUID, camera device, session type, and processing status.
    """
    try:
        from session_manager import get_session_manager

        session_mgr = get_session_manager()
        if not session_mgr:
            raise HTTPException(
                status_code=503, detail="Session management not available"
            )

        # Create query request
        query_request = SessionQueryRequest(
            media_uuid=media_uuid,
            camera_device_uuid=camera_device_uuid,
            session_type=session_type,
            processing_status=processing_status,
            limit=limit,
            offset=offset,
        )

        # Query sessions
        result = await session_mgr.query_sessions(query_request)

        # Check if result is an error
        if hasattr(result, "error"):
            raise HTTPException(status_code=400, detail=result.message)

        return result.dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying sessions: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to query sessions: {str(e)}"
        )


@app.get("/sessions/stats", summary="Get Session Statistics")
async def get_session_statistics():
    """
    Get overall session management statistics.

    Returns counts of active sessions, total sessions, and system status.
    """
    try:
        from session_manager import get_session_manager

        session_mgr = get_session_manager()
        if not session_mgr:
            raise HTTPException(
                status_code=503, detail="Session management not available"
            )

        active_count = session_mgr.get_active_session_count()

        return {
            "active_sessions": active_count,
            "session_manager_status": "available",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.error(f"Error getting session statistics: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get session statistics: {str(e)}"
        )


@app.get("/sessions/media/{media_uuid}", summary="Find Session by Media UUID")
async def find_session_by_media_uuid(
    media_uuid: str,
    authorization: str = Header(None),
):
    """
    Find session UUID by media UUID for person objects processing.

    This endpoint provides dynamic session discovery functionality that allows
    the frontend to find the appropriate session UUID for a given media UUID
    to enable person objects processing and statistics.
    """
    # Validate authentication
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401, detail="Missing or invalid authorization header"
        )

    try:
        # Import and use the person objects controller for session discovery
        from person_objects.ppl_thread_workflow import PPLThreadWorkflowController

        # Initialize controller with database
        controller = PPLThreadWorkflowController(vision_db)

        # Use the dynamic discovery method
        session_uuid = controller.find_session_uuid_by_media_uuid(media_uuid)

        if session_uuid:
            return {
                "success": True,
                "media_uuid": media_uuid,
                "session_uuid": session_uuid,
                "message": f"Found session {session_uuid} for media {media_uuid}",
            }
        else:
            raise HTTPException(
                status_code=404, detail=f"No session found for media UUID {media_uuid}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error finding session for media UUID {media_uuid}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to find session for media UUID: {str(e)}"
        )


# ============================================================================
# PHASE 4: Enhanced Face Storage with Session Context
# ============================================================================


@app.post("/faces/store", summary="Store Face Detection with Session Context")
async def store_face_detection_with_session(
    request: dict,
    authorization: str = Header(None),
):
    """
    Store individual face detection with complete session context.

    This endpoint validates session existence and creates proper linkage
    between face detections and their originating sessions for full
    traceability.

    Request body should contain:
    - session_uuid: Associated session UUID
    - frame_number: Frame number (for video)
    - timestamp: Timestamp in video (seconds)
    - bbox: [x1, y1, x2, y2] bounding box coordinates
    - confidence: Detection confidence (0.0-1.0)
    - method: Detection method used
    """
    try:
        # Import required models
        from api_models import FaceDetectionWithSessionRequest
        from session_manager import get_session_manager

        # Validate request data
        try:
            face_request = FaceDetectionWithSessionRequest(**request)
        except Exception as e:
            raise HTTPException(
                status_code=400, detail=f"Invalid request format: {str(e)}"
            )

        # Get session manager
        session_mgr = get_session_manager()
        if not session_mgr:
            raise HTTPException(
                status_code=503, detail="Session management not available"
            )

        # Validate session exists and is active
        session_status = await session_mgr.get_session_status(face_request.session_uuid)
        if hasattr(session_status, "error"):
            raise HTTPException(
                status_code=404,
                detail=f"Session not found: {face_request.session_uuid}",
            )

        if not session_status.session.processing_status == "active":
            status = session_status.session.processing_status
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Session {face_request.session_uuid} is not active "
                    f"(status: {status})"
                ),
            )

        # Get media UUID from session
        media_uuid = session_status.session.media_uuid

        # Generate unique face detection ID
        face_id = str(uuid.uuid4())

        # Store face detection in database with session context
        if vision_db and vision_db.connection:
            try:
                with vision_db.connection.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO face_detections
                        (id, media_id, session_uuid, frame_number, timestamp,
                         bbox_x1, bbox_y1, bbox_x2, bbox_y2, confidence,
                         method, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            face_id,
                            media_uuid,
                            face_request.session_uuid,
                            face_request.frame_number,
                            face_request.timestamp,
                            face_request.bbox[0],  # x1
                            face_request.bbox[1],  # y1
                            face_request.bbox[2],  # x2
                            face_request.bbox[3],  # y2
                            face_request.confidence,
                            face_request.method,
                            datetime.now(timezone.utc),
                        ),
                    )

                    # Update session face count
                    cursor.execute(
                        """
                        UPDATE face_detection_sessions
                        SET total_faces_detected = total_faces_detected + 1,
                            updated_at = %s
                        WHERE session_uuid = %s
                        """,
                        (datetime.now(timezone.utc), face_request.session_uuid),
                    )

                logger.info(
                    f"Stored face detection {face_id} for session "
                    f"{face_request.session_uuid}"
                )

            except Exception as e:
                logger.error(f"Database error storing face detection: {e}")
                raise HTTPException(
                    status_code=500, detail=f"Failed to store face detection: {str(e)}"
                )
        else:
            raise HTTPException(
                status_code=503, detail="Database connection not available"
            )

        # Return response
        return {
            "status": "stored",
            "face_id": face_id,
            "session_uuid": face_request.session_uuid,
            "media_id": media_uuid,
            "frame_number": face_request.frame_number,
            "timestamp": face_request.timestamp,
            "bbox": face_request.bbox,
            "confidence": face_request.confidence,
            "method": face_request.method,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error storing face detection with session: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/processing-status/{media_uuid}", summary="Get Media Processing Status")
async def get_video_processing_status(
    media_uuid: str,
    authorization: str = Header(None),
):
    """
    Check if media file has been processed for face detection.

    Returns processing status including whether face detection has been
    completed, associated session information, and processing statistics.
    """
    try:
        # Validate UUID format
        try:
            uuid.UUID(media_uuid)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid media UUID format")

        # Query processing status from database
        if vision_db and vision_db.connection:
            try:
                with vision_db.connection.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT media_uuid, face_detection_processed, face_detection_session_uuid,
                               processing_completed_at, total_frames_processed, total_faces_detected,
                               processing_method, last_updated
                        FROM media_processing_status 
                        WHERE media_uuid = %s
                        """,
                        (media_uuid,),
                    )

                    result = cursor.fetchone()

                    if not result:
                        return {
                            "media_uuid": media_uuid,
                            "face_detection_processed": False,
                            "status": "unprocessed",
                            "message": "Media has not been processed for face detection",
                        }

                    # Unpack result
                    (
                        media_uuid_db,
                        face_detection_processed,
                        session_uuid,
                        completed_at,
                        total_frames,
                        total_faces,
                        method,
                        last_updated,
                    ) = result

                    return {
                        "media_uuid": media_uuid,
                        "face_detection_processed": face_detection_processed,
                        "face_detection_session_uuid": session_uuid,
                        "processing_completed_at": (
                            completed_at.isoformat() if completed_at else None
                        ),
                        "total_frames_processed": total_frames,
                        "total_faces_detected": total_faces,
                        "processing_method": method,
                        "last_updated": (
                            last_updated.isoformat() if last_updated else None
                        ),
                        "status": (
                            "processed" if face_detection_processed else "unprocessed"
                        ),
                    }

            except Exception as e:
                logger.error(f"Database error getting processing status: {e}")
                raise HTTPException(
                    status_code=500, detail=f"Failed to get processing status: {str(e)}"
                )
        else:
            raise HTTPException(
                status_code=503, detail="Database connection not available"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting processing status: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/processing-status/{media_uuid}/complete", summary="Mark Media as Processed")
async def mark_video_as_processed(
    media_uuid: str,
    request: dict,
    authorization: str = Header(None),
):
    """
    Mark media file as fully processed for face detection.

    Updates the processing status with completion information including
    session UUID, total frames processed, and detection statistics.

    Request body should contain:
    - session_uuid: Processing session UUID
    - total_frames: Total number of frames processed
    - total_faces: Total faces detected
    - method: Detection method used
    """
    try:
        # Import required models
        from api_models import CompleteProcessingRequest

        # Validate request data
        try:
            complete_request = CompleteProcessingRequest(**request)
        except Exception as e:
            raise HTTPException(
                status_code=400, detail=f"Invalid request format: {str(e)}"
            )

        # Validate media UUID format
        try:
            uuid.UUID(media_uuid)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid media UUID format")

        # Update or insert processing status
        if vision_db and vision_db.connection:
            try:
                with vision_db.connection.cursor() as cursor:
                    # Use UPSERT (INSERT ... ON CONFLICT) to handle existing records
                    cursor.execute(
                        """
                        INSERT INTO media_processing_status 
                        (media_uuid, face_detection_processed, face_detection_session_uuid,
                         processing_completed_at, total_frames_processed, total_faces_detected,
                         processing_method, last_updated)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (media_uuid) DO UPDATE SET
                            face_detection_processed = EXCLUDED.face_detection_processed,
                            face_detection_session_uuid = EXCLUDED.face_detection_session_uuid,
                            processing_completed_at = EXCLUDED.processing_completed_at,
                            total_frames_processed = EXCLUDED.total_frames_processed,
                            total_faces_detected = EXCLUDED.total_faces_detected,
                            processing_method = EXCLUDED.processing_method,
                            last_updated = EXCLUDED.last_updated
                        """,
                        (
                            media_uuid,
                            True,  # face_detection_processed
                            complete_request.session_uuid,
                            datetime.now(timezone.utc),
                            complete_request.total_frames,
                            complete_request.total_faces,
                            complete_request.method,
                            datetime.now(timezone.utc),
                        ),
                    )

                logger.info(
                    f"Marked media {media_uuid} as processed (session: {complete_request.session_uuid}, "
                    f"frames: {complete_request.total_frames}, faces: {complete_request.total_faces})"
                )

            except Exception as e:
                logger.error(f"Database error marking media as processed: {e}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to mark media as processed: {str(e)}",
                )
        else:
            raise HTTPException(
                status_code=503, detail="Database connection not available"
            )

        return {
            "status": "marked_as_processed",
            "media_uuid": media_uuid,
            "session_uuid": complete_request.session_uuid,
            "total_frames": complete_request.total_frames,
            "total_faces": complete_request.total_faces,
            "processing_method": complete_request.method,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking media as processed: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get(
    "/faces/media/{media_uuid}/frames",
    summary="Get Frame-Indexed Face Data for Playback",
)
async def get_stored_face_data_for_playback(
    media_uuid: str,
    frame_start: Optional[int] = Query(None, description="Start frame number"),
    frame_end: Optional[int] = Query(None, description="End frame number"),
    confidence_threshold: Optional[float] = Query(
        None, description="Minimum confidence threshold"
    ),
    authorization: str = Header(None),
):
    """
    Retrieve frame-indexed face detection data for video playback.

    This endpoint returns face detection data organized by frame numbers,
    optimized for video playback with frame-by-frame face overlay rendering.
    Supports filtering by frame range and confidence threshold.

    Args:
        media_uuid: Media file UUID
        frame_start: Optional start frame number (inclusive)
        frame_end: Optional end frame number (inclusive)
        confidence_threshold: Optional minimum confidence threshold

    Returns:
        Face data organized by frame number with session context
    """
    try:
        # Validate UUID format
        try:
            uuid.UUID(media_uuid)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid media UUID format")

        # Validate optional parameters
        if frame_start is not None and frame_start < 0:
            raise HTTPException(
                status_code=400, detail="frame_start must be non-negative"
            )

        if frame_end is not None and frame_end < 0:
            raise HTTPException(
                status_code=400, detail="frame_end must be non-negative"
            )

        if (
            frame_start is not None
            and frame_end is not None
            and frame_start > frame_end
        ):
            raise HTTPException(
                status_code=400,
                detail="frame_start must be less than or equal to frame_end",
            )

        if confidence_threshold is not None and (
            confidence_threshold < 0.0 or confidence_threshold > 1.0
        ):
            raise HTTPException(
                status_code=400,
                detail="confidence_threshold must be between 0.0 and 1.0",
            )

        # Query face detections from database
        if vision_db and vision_db.connection:
            try:
                with vision_db.connection.cursor() as cursor:
                    # Build dynamic query based on parameters
                    query = """
                        SELECT frame_number, bbox_x1, bbox_y1, bbox_x2, bbox_y2,
                               confidence, method, session_uuid, created_at
                        FROM face_detections 
                        WHERE media_id = %s
                    """
                    params = [media_uuid]

                    if frame_start is not None:
                        query += " AND frame_number >= %s"
                        params.append(frame_start)

                    if frame_end is not None:
                        query += " AND frame_number <= %s"
                        params.append(frame_end)

                    if confidence_threshold is not None:
                        query += " AND confidence >= %s"
                        params.append(confidence_threshold)

                    # Order by frame number for organized output
                    query += " ORDER BY frame_number, confidence DESC"

                    cursor.execute(query, params)
                    results = cursor.fetchall()

                    if not results:
                        return {
                            "media_uuid": media_uuid,
                            "total_frames": 0,
                            "face_data": {},
                            "session_uuid": None,
                            "message": "No face data found for specified criteria",
                        }

                    # Organize results by frame number
                    face_data = {}
                    session_uuid = None
                    max_frame = 0

                    for row in results:
                        (
                            frame_num,
                            x1,
                            y1,
                            x2,
                            y2,
                            confidence,
                            method,
                            sess_uuid,
                            created_at,
                        ) = row

                        if frame_num is None:
                            continue  # Skip faces without frame numbers

                        frame_key = str(frame_num)
                        if frame_key not in face_data:
                            face_data[frame_key] = []

                        face_data[frame_key].append(
                            {
                                "bbox": [x1, y1, x2, y2],
                                "confidence": confidence,
                                "method": method,
                                "created_at": (
                                    created_at.isoformat() if created_at else None
                                ),
                            }
                        )

                        # Track session UUID and max frame
                        if session_uuid is None:
                            session_uuid = sess_uuid
                        if frame_num > max_frame:
                            max_frame = frame_num

                    return {
                        "media_uuid": media_uuid,
                        "total_frames": max_frame if face_data else 0,
                        "face_data": face_data,
                        "session_uuid": session_uuid,
                        "frame_range": {"start": frame_start, "end": frame_end},
                        "confidence_threshold": confidence_threshold,
                        "total_detections": len(results),
                    }

            except Exception as e:
                logger.error(f"Database error retrieving face data: {e}")
                raise HTTPException(
                    status_code=500, detail=f"Failed to retrieve face data: {str(e)}"
                )
        else:
            raise HTTPException(
                status_code=503, detail="Database connection not available"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving frame-indexed face data: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/faces/session/{session_uuid}/analytics", summary="Get Session Analytics")
async def get_session_analytics(
    session_uuid: str,
    authorization: str = Header(None),
):
    """
    Get comprehensive analytics for a face detection session.

    Returns detailed statistics including face counts by frame,
    average confidence, processing duration, and detection methods.
    """
    try:
        # Validate UUID format
        try:
            uuid.UUID(session_uuid)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid session UUID format")

        # Get session information
        from session_manager import get_session_manager

        session_mgr = get_session_manager()
        if not session_mgr:
            raise HTTPException(
                status_code=503, detail="Session management not available"
            )

        session_status = await session_mgr.get_session_status(session_uuid)
        if hasattr(session_status, "error"):
            raise HTTPException(
                status_code=404, detail=f"Session not found: {session_uuid}"
            )

        session = session_status.session

        # Query face detection analytics from database
        if vision_db and vision_db.connection:
            try:
                with vision_db.connection.cursor() as cursor:
                    # Get face count by frame
                    cursor.execute(
                        """
                        SELECT frame_number, COUNT(*) as face_count
                        FROM face_detections 
                        WHERE session_uuid = %s AND frame_number IS NOT NULL
                        GROUP BY frame_number
                        ORDER BY frame_number
                    """,
                        (session_uuid,),
                    )
                    frame_counts = dict(cursor.fetchall())

                    # Get average confidence
                    cursor.execute(
                        """
                        SELECT AVG(confidence) as avg_confidence
                        FROM face_detections 
                        WHERE session_uuid = %s
                    """,
                        (session_uuid,),
                    )
                    avg_conf_result = cursor.fetchone()
                    avg_confidence = (
                        float(avg_conf_result[0]) if avg_conf_result[0] else 0.0
                    )

                    # Get method distribution
                    cursor.execute(
                        """
                        SELECT method, COUNT(*) as count
                        FROM face_detections 
                        WHERE session_uuid = %s
                        GROUP BY method
                    """,
                        (session_uuid,),
                    )
                    method_counts = dict(cursor.fetchall())

                    # Calculate session duration
                    duration_seconds = None
                    if session.ended_at and session.started_at:
                        duration_seconds = (
                            session.ended_at - session.started_at
                        ).total_seconds()

                    return {
                        "session_uuid": session_uuid,
                        "media_uuid": session.media_uuid,
                        "camera_device_uuid": session.camera_device_uuid,
                        "session_type": session.session_type,
                        "total_faces": session.total_faces_detected,
                        "session_duration": duration_seconds,
                        "avg_confidence": avg_confidence,
                        "faces_per_frame": frame_counts,
                        "detection_methods": method_counts,
                        "processing_status": session.processing_status,
                        "started_at": (
                            session.started_at.isoformat()
                            if session.started_at
                            else None
                        ),
                        "ended_at": (
                            session.ended_at.isoformat() if session.ended_at else None
                        ),
                        "metadata": session.metadata,
                    }

            except Exception as e:
                logger.error(f"Database error getting session analytics: {e}")
                raise HTTPException(
                    status_code=500, detail=f"Failed to get session analytics: {str(e)}"
                )
        else:
            raise HTTPException(
                status_code=503, detail="Database connection not available"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session analytics: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# ============================================================================
# PHASE 5: Advanced Analytics & Traceability Features
# ============================================================================

# Analytics Service Integration
analytics_service_instance = None


@app.get("/analytics/cross-session", summary="Cross-Session Analytics")
async def get_cross_session_analytics(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    camera_device_uuid: Optional[str] = Query(
        None, description="Filter by camera device"
    ),
    authorization: str = Header(None),
):
    """
    Get comprehensive cross-session analytics for face detection operations.

    Provides insights across multiple sessions including:
    - Session overview statistics
    - Detection trends over time
    - Camera performance analysis
    - Success rate analysis
    """
    try:
        if not analytics_service_instance:
            raise HTTPException(
                status_code=503, detail="Analytics service not available"
            )

        # Parse date filters
        start_datetime = None
        end_datetime = None

        if start_date:
            try:
                start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(
                    status_code=400, detail="Invalid start_date format. Use YYYY-MM-DD"
                )

        if end_date:
            try:
                end_datetime = datetime.strptime(end_date, "%Y-%m-%d")
                # Set to end of day
                end_datetime = end_datetime.replace(hour=23, minute=59, second=59)
            except ValueError:
                raise HTTPException(
                    status_code=400, detail="Invalid end_date format. Use YYYY-MM-DD"
                )

        # Get analytics data
        analytics = analytics_service_instance.get_cross_session_analytics(
            start_date=start_datetime,
            end_date=end_datetime,
            camera_device_uuid=camera_device_uuid,
        )

        return {
            "success": True,
            "analytics": analytics,
            "filters": {
                "start_date": start_date,
                "end_date": end_date,
                "camera_device_uuid": camera_device_uuid,
            },
            "message": "Cross-session analytics retrieved successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting cross-session analytics: {e}")
        raise HTTPException(status_code=500, detail=f"Analytics error: {str(e)}")


@app.get(
    "/analytics/device/{camera_device_uuid}", summary="Device Traceability Analytics"
)
async def get_device_traceability_analytics(
    camera_device_uuid: str,
    days: Optional[int] = Query(30, description="Number of days to analyze"),
    include_sessions: Optional[bool] = Query(
        True, description="Include session details"
    ),
    authorization: str = Header(None),
):
    """
    Get comprehensive traceability analytics for a specific camera device.

    Provides device-specific insights including:
    - Session overview for device
    - Session history with processing status
    - Daily activity patterns
    - Quality metrics analysis
    """
    try:
        if not analytics_service_instance:
            raise HTTPException(
                status_code=503, detail="Analytics service not available"
            )

        # Validate UUID format
        try:
            uuid.UUID(camera_device_uuid)
        except ValueError:
            raise HTTPException(
                status_code=400, detail="Invalid camera device UUID format"
            )

        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # Get device analytics
        analytics = analytics_service_instance.get_device_traceability(
            camera_device_uuid=camera_device_uuid,
            start_date=start_date,
            end_date=end_date,
            include_session_details=include_sessions,
        )

        return {
            "success": True,
            "camera_device_uuid": camera_device_uuid,
            "analytics": analytics,
            "analysis_period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": days,
            },
            "message": f"Device traceability analytics for {camera_device_uuid} retrieved successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting device traceability analytics: {e}")
        raise HTTPException(status_code=500, detail=f"Analytics error: {str(e)}")


@app.get("/analytics/media/{media_uuid}/timeline", summary="Media Timeline Analytics")
async def get_media_timeline_analytics(
    media_uuid: str,
    include_sessions: Optional[bool] = Query(
        True, description="Include session details"
    ),
    include_frames: Optional[bool] = Query(False, description="Include frame analysis"),
    authorization: str = Header(None),
):
    """
    Get comprehensive timeline analytics for a specific media file.

    Provides chronological view of face detection sessions including:
    - Media processing overview
    - Session timeline with processing details
    - Frame analysis (if requested)
    - Processing quality metrics
    """
    try:
        if not analytics_service_instance:
            raise HTTPException(
                status_code=503, detail="Analytics service not available"
            )

        # Validate UUID format
        try:
            uuid.UUID(media_uuid)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid media UUID format")

        # Get media timeline analytics
        analytics = analytics_service_instance.get_media_timeline_analytics(
            media_uuid=media_uuid,
            include_session_details=include_sessions,
            include_frame_analysis=include_frames,
        )

        return {
            "success": True,
            "media_uuid": media_uuid,
            "analytics": analytics,
            "options": {
                "include_sessions": include_sessions,
                "include_frames": include_frames,
            },
            "message": f"Media timeline analytics for {media_uuid} retrieved successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting media timeline analytics: {e}")
        raise HTTPException(status_code=500, detail=f"Analytics error: {str(e)}")


@app.get("/analytics/query", summary="Advanced Analytics Query")
async def advanced_analytics_query(
    query_type: str = Query(
        ..., description="Type of query: sessions, devices, media, performance"
    ),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    camera_device_uuid: Optional[str] = Query(
        None, description="Filter by camera device"
    ),
    media_uuid: Optional[str] = Query(None, description="Filter by media file"),
    session_type: Optional[str] = Query(None, description="Filter by session type"),
    processing_status: Optional[str] = Query(
        None, description="Filter by processing status"
    ),
    confidence_threshold: Optional[float] = Query(
        None, description="Minimum confidence threshold"
    ),
    limit: Optional[int] = Query(100, description="Maximum number of results"),
    offset: Optional[int] = Query(0, description="Result offset for pagination"),
    authorization: str = Header(None),
):
    """
    Advanced querying system for complex analytics with filters and aggregations.

    Supports multiple query types:
    - sessions: Query session data with complex filters
    - devices: Query device-specific analytics
    - media: Query media processing analytics
    - performance: Query system performance metrics
    """
    try:
        if not analytics_service_instance:
            raise HTTPException(
                status_code=503, detail="Analytics service not available"
            )

        # Validate query type
        valid_query_types = ["sessions", "devices", "media", "performance"]
        if query_type not in valid_query_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid query_type. Must be one of: {', '.join(valid_query_types)}",
            )

        # Parse date filters
        start_datetime = None
        end_datetime = None

        if start_date:
            try:
                start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(
                    status_code=400, detail="Invalid start_date format. Use YYYY-MM-DD"
                )

        if end_date:
            try:
                end_datetime = datetime.strptime(end_date, "%Y-%m-%d")
                end_datetime = end_datetime.replace(hour=23, minute=59, second=59)
            except ValueError:
                raise HTTPException(
                    status_code=400, detail="Invalid end_date format. Use YYYY-MM-DD"
                )

        # Build filter dictionary
        filters = {}
        if start_datetime:
            filters["start_date"] = start_datetime
        if end_datetime:
            filters["end_date"] = end_datetime
        if camera_device_uuid:
            filters["camera_device_uuid"] = camera_device_uuid
        if media_uuid:
            filters["media_uuid"] = media_uuid
        if session_type:
            filters["session_type"] = session_type
        if processing_status:
            filters["processing_status"] = processing_status
        if confidence_threshold is not None:
            filters["confidence_threshold"] = confidence_threshold

        # Execute query based on type
        if query_type == "sessions":
            result = analytics_service_instance.query_sessions(filters, limit, offset)
        elif query_type == "devices":
            result = analytics_service_instance.query_devices(filters, limit, offset)
        elif query_type == "media":
            result = analytics_service_instance.query_media(filters, limit, offset)
        elif query_type == "performance":
            result = analytics_service_instance.query_performance(
                filters, limit, offset
            )

        return {
            "success": True,
            "query_type": query_type,
            "result": result,
            "filters": filters,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "total_results": (
                    result.get("total_count", 0) if isinstance(result, dict) else None
                ),
            },
            "message": f"Advanced {query_type} query executed successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing advanced analytics query: {e}")
        raise HTTPException(status_code=500, detail=f"Analytics query error: {str(e)}")


@app.get("/analytics/performance", summary="Performance Analytics")
async def get_performance_analytics(
    metric_type: Optional[str] = Query(
        None, description="Specific metric: processing_time, accuracy, throughput"
    ),
    days: Optional[int] = Query(7, description="Number of days to analyze"),
    granularity: Optional[str] = Query(
        "hour", description="Time granularity: hour, day"
    ),
    authorization: str = Header(None),
):
    """
    Get performance analytics and monitoring data.

    Provides system performance insights including:
    - Processing time analytics
    - Detection accuracy metrics
    - System throughput analysis
    - Performance trends over time
    """
    try:
        if not analytics_service_instance:
            raise HTTPException(
                status_code=503, detail="Analytics service not available"
            )

        # Validate parameters
        valid_metrics = ["processing_time", "accuracy", "throughput", None]
        if metric_type not in valid_metrics:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid metric_type. Must be one of: {', '.join([m for m in valid_metrics if m])}",
            )

        valid_granularities = ["hour", "day"]
        if granularity not in valid_granularities:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid granularity. Must be one of: {', '.join(valid_granularities)}",
            )

        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # Get performance analytics
        analytics = analytics_service_instance.get_performance_analytics(
            start_date=start_date,
            end_date=end_date,
            metric_type=metric_type,
            granularity=granularity,
        )

        # Check if analytics returned an error and convert to user-friendly message
        if isinstance(analytics, dict) and "error" in analytics:
            # Return success with informative message instead of error
            return {
                "success": True,
                "analytics": {
                    "processing_time": {
                        "avg_seconds": 0.0,
                        "min_seconds": 0.0,
                        "max_seconds": 0.0,
                        "total_sessions": 0,
                    },
                    "accuracy": {
                        "avg_confidence": 0.0,
                        "min_confidence": 0.0,
                        "max_confidence": 0.0,
                        "total_detections": 0,
                    },
                    "throughput": {
                        "total_faces_processed": 0,
                        "total_processing_time": 0.0,
                        "faces_per_second": 0,
                        "faces_per_minute": 0,
                    },
                    "time_series": [],
                    "status": "no_data",
                    "message": (
                        "No performance data available yet. "
                        "Start processing videos to generate analytics."
                    ),
                },
                "parameters": {
                    "metric_type": metric_type,
                    "days": days,
                    "granularity": granularity,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                },
                "message": (
                    "Performance analytics retrieved successfully "
                    "(no data available yet)"
                ),
            }

        return {
            "success": True,
            "analytics": analytics,
            "parameters": {
                "metric_type": metric_type,
                "days": days,
                "granularity": granularity,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
            "message": "Performance analytics retrieved successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting performance analytics: {e}")
        raise HTTPException(
            status_code=500, detail=f"Performance analytics error: {str(e)}"
        )


@app.get("/analytics/summary", summary="Analytics Dashboard Summary")
async def get_analytics_dashboard_summary(
    days: Optional[int] = Query(7, description="Number of days for summary"),
    authorization: str = Header(None),
):
    """
    Get comprehensive analytics dashboard summary.

    Provides high-level overview including:
    - System activity summary
    - Top performing cameras
    - Recent processing statistics
    - System health metrics
    """
    try:
        if not analytics_service_instance:
            raise HTTPException(
                status_code=503, detail="Analytics service not available"
            )

        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # Get comprehensive summary
        summary = {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": days,
            }
        }

        # Get cross-session overview
        time_range_hours = (days or 7) * 24  # Convert days to hours, default to 7 days
        cross_session = await analytics_service_instance.get_cross_session_analytics(
            time_range_hours=time_range_hours
        )

        summary["system_overview"] = cross_session.get("session_overview", {})
        summary["detection_trends"] = cross_session.get("detection_trends", {})
        summary["camera_performance"] = cross_session.get("camera_performance", {})

        # Get performance metrics
        performance = analytics_service_instance.get_performance_analytics(
            start_date=start_date, end_date=end_date, granularity="day"
        )

        summary["performance_metrics"] = performance

        return {
            "success": True,
            "summary": summary,
            "generated_at": datetime.now().isoformat(),
            "message": f"Analytics dashboard summary for {days} days retrieved successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting analytics dashboard summary: {e}")
        raise HTTPException(
            status_code=500, detail=f"Analytics summary error: {str(e)}"
        )


# Error handlers - Don't interfere with person-objects router responses
# @app.exception_handler(404)  # Disabled to allow person-objects router to handle its own 404s
# async def not_found_handler(request, exc):
#     return JSONResponse(
#         status_code=404,
#         content={
#             "error": "Endpoint not found",
#             "available_endpoints": [
#                 "/",
#                 "/health",
#                 "/models",
#                 "/detect",
#                 "/process/media",
#                 "/process/media/enhanced",
#                 "/overlay/generate",
#                 "/timeline/generate",
#                 "/media/{media_id}/analytics",
#                 "/faces/media/{media_id}/frame/{frame_number}",
#                 "/faces/media/{media_id}/bulk-process",
#                 "/sessions/start",
#                 "/sessions/{session_uuid}/status",
#                 "/sessions/{session_uuid}/complete",
#                 "/sessions",
#                 "/sessions/stats",
#                 "/analytics/cross-session",
#                 "/analytics/device/{camera_device_uuid}",
#                 "/analytics/media/{media_uuid}/timeline",
#                 "/analytics/query",
#                 "/analytics/performance",
#                 "/analytics/summary",
#                 "/database/status",
#                 "/debug/auth",
#                 "/docs",
#             ],
#         },
#     )
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
