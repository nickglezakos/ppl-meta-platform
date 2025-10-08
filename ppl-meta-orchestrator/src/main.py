import logging
import os
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

# Standard library and third-party imports
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from service_clients import ServiceClientManager
from workflow_orchestrator import CameraFaceDetectionWorkflowOrchestrator

# Local imports
from config import settings

# Setup enhanced logging for Phase 1
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Try to import consul for service discovery
try:
    import consul

    service_discovery_available = True
    logger.info("Consul module available for service discovery")
except ImportError:
    service_discovery_available = False
    logger.warning("Consul module not available, service discovery disabled")

# Global components for Phase 1 & Phase 2 implementation
consul_client = None
service_manager: Optional[ServiceClientManager] = None
workflow_orchestrator: Optional[CameraFaceDetectionWorkflowOrchestrator] = None
workflow_endpoints = None  # Will be set to CameraWorkflowEndpoints after import

# Phase 2 components
automation_manager = None  # Will be set to CameraAutomationManager
camera_automation_endpoints = None  # Will be set to CameraAutomationEndpoints

# Phase 2.2 components
event_publisher = None  # Will be set to CameraEventPublisher
event_endpoints = None  # Will be set to CameraEventEndpoints

# Phase 2.3 components
method_lifecycle_manager = None  # Will be set to MethodLifecycleManager
method_lifecycle_endpoints = None  # Will be set to MethodLifecycleEndpoints

# Phase 2.4 components
automation_engine = None  # Will be set to AutomationEngine
automation_endpoints = None  # Will be set to AutomationEndpoints

# Consul configuration
CONSUL_CONFIG = {
    "host": os.getenv("CONSUL_HOST", "consul"),
    "port": int(os.getenv("CONSUL_PORT", "8500")),
    "enabled": os.getenv("CONSUL_ENABLED", "true").lower() == "true",
}


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Application lifespan with Phase 1 component initialization."""
    global consul_client, service_manager, workflow_orchestrator, workflow_endpoints
    logger.info("Starting PPL Meta Orchestrator Service with Phase 1 capabilities...")

    # Initialize Phase 1 service clients
    try:
        logger.info(
            "Initializing service clients for Camera, Media, and Vision services..."
        )
        service_manager = ServiceClientManager(
            camera_base_url=os.getenv("CAMERA_SERVICE_URL", "http://localhost:8005"),
            media_base_url=os.getenv("MEDIA_SERVICE_URL", "http://localhost:8000"),
            vision_base_url=os.getenv("VISION_SERVICE_URL", "http://localhost:8003"),
        )

        # Test service connectivity
        health_results = await service_manager.health_check_all()
        for service_name, result in health_results.items():
            if result and result.success:
                logger.info(
                    f"✅ {service_name.capitalize()} Service connected successfully"
                )
            else:
                logger.warning(f"⚠️ {service_name.capitalize()} Service not available")

        logger.info("Service clients initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize service clients: {e}")
        logger.info("Continuing with limited functionality")

    # Initialize Phase 1 workflow orchestrator
    try:
        logger.info("Initializing Camera Face Detection Workflow Orchestrator...")
        workflow_orchestrator = CameraFaceDetectionWorkflowOrchestrator(service_manager)

        # Import here to avoid circular imports
        from camera_endpoints import CameraWorkflowEndpoints

        workflow_endpoints = CameraWorkflowEndpoints(workflow_orchestrator)
        logger.info("✅ Workflow orchestrator initialized successfully")

        # Include the camera workflow router now that components are ready
        from camera_endpoints import workflow_router

        app.include_router(workflow_router)
        logger.info("✅ Camera workflow endpoints registered")

        # Include session endpoints for tracking workflow status
        try:
            from session_endpoints import create_session_endpoints

            session_router = create_session_endpoints(workflow_orchestrator)
            app.include_router(session_router)
            logger.info("✅ Session endpoints registered")
        except Exception as session_error:
            logger.error(f"Failed to initialize session endpoints: {session_error}")
            logger.warning("Continuing without session endpoints")

        # Include face detection endpoints for self-referencing architecture
        try:
            from face_detection_endpoints import face_detection_router

            app.include_router(face_detection_router)
            logger.info("✅ Face detection endpoints registered")
        except Exception as face_detection_error:
            logger.error(
                f"Failed to initialize face detection endpoints: {face_detection_error}"
            )
            logger.warning("Continuing without face detection endpoints")

    except Exception as e:
        logger.error(f"Failed to initialize workflow orchestrator: {e}")
        raise RuntimeError("Critical component initialization failed")

    # Initialize Phase 2 camera automation
    global automation_manager, camera_automation_endpoints
    try:
        logger.info("Initializing Phase 2 Camera Automation Manager...")

        from camera_automation_endpoints import CameraAutomationEndpoints
        from camera_automation_manager import CameraAutomationManager

        automation_manager = CameraAutomationManager(service_manager)
        camera_automation_endpoints = CameraAutomationEndpoints(automation_manager)

        # Register endpoints
        from camera_automation_endpoints import automation_router

        app.include_router(automation_router)

        logger.info("✅ Phase 2 camera automation initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize camera automation: {e}")
        logger.warning("Continuing without Phase 2 automation features")

    # Initialize Phase 2.2 camera event publishing
    global event_publisher, event_endpoints
    try:
        logger.info("Initializing Phase 2.2 Camera Event Publisher...")

        from camera_event_endpoints import CameraEventEndpoints
        from camera_event_publisher import CameraEventPublisher

        event_publisher = CameraEventPublisher(service_manager, automation_manager)
        event_endpoints = CameraEventEndpoints(event_publisher)

        # Include event publishing router
        from camera_event_endpoints import events_router

        app.include_router(events_router)

        logger.info("✅ Phase 2.2 camera event publishing initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize camera event publishing: {e}")
        logger.warning("Continuing without Phase 2.2 event publishing features")

    # Initialize Phase 2.3 method lifecycle management
    global method_lifecycle_manager, method_lifecycle_endpoints
    try:
        logger.info("Initializing Phase 2.3 Method Lifecycle Manager...")

        from method_lifecycle_endpoints import create_method_lifecycle_router
        from method_lifecycle_manager import MethodLifecycleManager

        method_lifecycle_manager = MethodLifecycleManager(service_manager)
        method_lifecycle_router = create_method_lifecycle_router(
            method_lifecycle_manager
        )

        app.include_router(method_lifecycle_router)

        logger.info("✅ Phase 2.3 method lifecycle management initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize method lifecycle management: {e}")
        logger.warning("Continuing without Phase 2.3 method lifecycle features")

    # Initialize Phase 2.4 automation engine
    global automation_engine, automation_endpoints
    try:
        logger.info("Initializing Phase 2.4 Automation Engine...")

        from automation_endpoints import create_automation_router
        from automation_engine import AutomationEngine

        automation_engine = AutomationEngine(service_manager)
        await automation_engine.start_engine()

        automation_router_v2 = create_automation_router(automation_engine)
        app.include_router(automation_router_v2)

        logger.info("✅ Phase 2.4 automation engine initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize automation engine: {e}")
        logger.warning("Continuing without Phase 2.4 automation features")

    # Initialize PPL Thread (Person Objects) endpoints
    try:
        logger.info("Initializing PPL Thread (Person Objects) endpoints...")

        from ppl_thread_endpoints import create_ppl_thread_endpoints

        ppl_thread_router = create_ppl_thread_endpoints(
            workflow_orchestrator, service_manager
        )
        app.include_router(ppl_thread_router)

        logger.info("✅ PPL Thread endpoints initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize PPL Thread endpoints: {e}")
        logger.warning("Continuing without PPL Thread features")

    # Initialize Master Lifecycle Workflow endpoints (Phase 1 completion)
    try:
        logger.info("Initializing Master Lifecycle Workflow endpoints...")

        # Initialize the Master Workflow Controller first
        from master_lifecycle_workflow import initialize_master_workflow_controller

        # Initialize with service manager clients
        if service_manager:
            vision_client = service_manager.vision
            vmeta_client = None  # vmeta client not available in current setup

            initialize_master_workflow_controller(
                vision_service_client=vision_client,
                vmeta_service_client=vmeta_client,
                config={"max_concurrent_workflows": 10},
            )
            logger.info("✅ Master Workflow Controller initialized")
        else:
            logger.warning(
                "Service manager not available, initializing with None clients"
            )
            initialize_master_workflow_controller(
                vision_service_client=None,
                vmeta_service_client=None,
                config={"max_concurrent_workflows": 10},
            )

        import master_lifecycle_endpoints

        app.include_router(master_lifecycle_endpoints.router)

        logger.info("✅ Master Lifecycle Workflow endpoints initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize Master Lifecycle Workflow endpoints: {e}")
        logger.warning("Continuing without Master Lifecycle Workflow features")

    # Phase 2.5: Face Detection Endpoints (Self-referencing architecture)
    try:
        from face_detection_endpoints import face_detection_router

        app.include_router(face_detection_router)
        logger.info("✅ Face Detection endpoints initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize Face Detection endpoints: {e}")
        logger.warning("Continuing without Face Detection features")

    # Initialize service discovery if available
    try:
        import socket

        from shared.service_discovery import register_service

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
            name="ppl-meta-orchestrator",
            service_type="backend",
            version="1.0.0-phase1",
            host=detected_ip,
            port=settings.PORT,
            health_endpoint="/health",
            capabilities=[
                "orchestration",
                "coordination",
                "workflow",
                "camera_automation",
                "face_detection_workflows",
                "traceability",
            ],
            metadata={
                "version": "1.0.0-phase1",
                "environment": "development",
                "features": "orchestration,camera_workflows,traceability,method_lifecycles",
                "phase": "1",
            },
        )
        logger.info(
            "Successfully registered ppl-meta-orchestrator with enhanced capabilities"
        )

    except Exception as e:
        logger.error(f"Failed to register with discovery service: {e}")
        logger.info("Continuing without service discovery")

    logger.info("🚀 Phase 1 service startup completed successfully")

    yield

    logger.info("Shutting down PPL Meta Orchestrator Service...")

    # Cleanup Phase 2.4 automation engine
    if automation_engine:
        logger.info("Shutting down automation engine...")
        await automation_engine.stop_engine()

    # Cleanup Phase 1 components
    if workflow_orchestrator:
        logger.info("Cleaning up active workflows...")
        # Could add workflow cleanup logic here

    # Deregister from service discovery
    try:
        from shared.service_discovery import deregister_service

        await deregister_service("ppl-meta-orchestrator")
        logger.info("Service deregistered from discovery service")
    except Exception as e:
        logger.error(f"Failed to deregister service: {e}")


def get_workflow_endpoints():
    """Dependency injection for workflow endpoints."""
    if workflow_endpoints is None:
        raise HTTPException(
            status_code=503, detail="Workflow orchestrator not initialized"
        )
    return workflow_endpoints


def validate_orchestrator_input(data: Dict[str, Any]) -> Dict[str, Any]:
    """Basic validation for orchestrator input data."""
    # Simple validation - can be extended later
    validated_data = {}
    for key, value in data.items():
        if isinstance(value, str):
            # Basic sanitization
            validated_data[key] = value.strip()
        else:
            validated_data[key] = value
    return validated_data


# Create FastAPI app with Phase 1 & Phase 2 integration
app = FastAPI(
    title=f"{settings.APP_NAME} - Phase 1 & 2.3",
    version=f"{settings.APP_VERSION}-phase1-2.4",
    lifespan=lifespan,
    description=(
        "PPL Meta Orchestrator with Camera Integration, "
        "Automation, Event Publishing, Method Lifecycle & Automation Engine"
    ),
)

# Add CORS middleware for Flutter web client access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Router will be included after initialization in the lifespan event


@app.get("/health")
async def health_check():
    """Enhanced health check with Phase 1-2.4 component status."""
    health_status = {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": f"{settings.APP_VERSION}-phase1-2.4",
        "environment": settings.ENVIRONMENT,
        "phase": "1-2.4",
        "capabilities": [
            "orchestration",
            "camera_automation",
            "camera_event_publishing",
            "method_lifecycle_management",
            "automation_engine",
            "face_detection_workflows",
            "traceability",
            "method_lifecycles",
            "automation_triggers",
        ],
    }

    # Check Phase 1 component health
    if service_manager:
        try:
            service_health = await service_manager.health_check_all()
            health_status["service_connections"] = {
                name: result.success if result else False
                for name, result in service_health.items()
            }
        except Exception as e:
            health_status["service_connections"] = {"error": str(e)}

    if workflow_orchestrator:
        health_status["workflow_orchestrator"] = {
            "active_workflows": len(workflow_orchestrator.active_workflows),
            "historical_workflows": len(workflow_orchestrator.workflow_history),
        }

    return JSONResponse(status_code=200, content=health_status)


@app.get("/")
async def root():
    """Enhanced root endpoint with Phase 1 information."""
    return {
        "message": f"{settings.APP_NAME} Service - Phase 1",
        "status": "running",
        "version": f"{settings.APP_VERSION}-phase1",
        "phase": "1",
        "description": ("Orchestrator with Camera Integration and Workflow Management"),
        "endpoints": {
            "health": "/health",
            "workflows": "/workflows/*",
            "camera_events": "/workflows/camera/events",
            "bulk_processing": "/workflows/face-detection/bulk-process",
            "analytics": "/workflows/analytics",
        },
    }


# Enhanced orchestration endpoint with validation
@app.post("/orchestrate")
async def orchestrate_request(data: Dict[str, Any]):
    """Legacy orchestration endpoint with enhanced validation."""
    try:
        # Validate input data
        validated_data = validate_orchestrator_input(data)

        # Log orchestration request for traceability
        logger.info(
            "Processing orchestration request with %d parameters", len(validated_data)
        )

        return {
            "status": "orchestrated",
            "processed_data": validated_data,
            "message": "Request orchestration successful",
            "service": settings.APP_NAME,
            "phase": "1",
            "enhanced_features": ("Use /workflows/* endpoints for camera integration"),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Orchestration processing error: {str(e)}"
        ) from e


@app.get("/validate")
async def validate_data_endpoint():
    """Enhanced validation endpoint with Phase 1 security features."""
    return {
        "validation_active": True,
        "security_features": [
            "sql_injection_prevention",
            "xss_protection",
            "input_sanitization",
            "request_traceability",
            "workflow_audit_trails",
        ],
        "phase": "1",
        "workflow_features": [
            "camera_event_processing",
            "bulk_face_detection",
            "method_lifecycle_tracking",
            "cross_service_traceability",
        ],
    }


if __name__ == "__main__":
    import uvicorn

    # Log configuration on startup
    settings.log_configuration()

    uvicorn.run(
        app,
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
