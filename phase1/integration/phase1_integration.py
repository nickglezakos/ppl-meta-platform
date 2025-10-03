# ================================================================
# Phase 1: Complete Integration - PPL Meta Enhanced Person Detection
# Session-Based Processing with Distance & Embeddings
# ================================================================

"""
Phase 1 Complete Integration

This file provides the complete integration of all Phase 1 components:
- Enhanced Vision Service with distance calculation and embeddings
- Master Lifecycle Workflow Controller with session management
- Database client with pgvector support
- FastAPI endpoints for all Phase 1 features

Usage:
    python phase1_integration.py

Features Delivered:
✅ Session-based processing (no duplicate prevention)
✅ 3D distance calculation using autonomous system methodology
✅ 512-dimensional facial embeddings with DeepFace
✅ Person routes tracking with movement analytics
✅ Vector similarity search with pgvector
✅ Spatial analysis and heatmap generation
✅ Master workflow lifecycle management
✅ Complete REST API for all features
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Any, Dict

import uvicorn
from fastapi import BackgroundTasks, FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Phase 1 imports
from phase1_database_client import Phase1DatabaseClient, create_phase1_database_client
from phase1_enhanced_vision_service import PHASE1_VISION_CONFIG, EnhancedVisionService
from phase1_orchestrator_workflow import (
    MasterLifecycleWorkflowController,
    PersonRoutesRequest,
    WorkflowExecutionRequest,
    create_phase1_router,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ================================================================
# Phase 1 Configuration
# ================================================================

PHASE1_CONFIG = {
    # Database configuration
    "database": {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", 5432)),
        "database": os.getenv("DB_NAME", "ppl_meta"),
        "username": os.getenv("DB_USER", "ppl_user"),
        "password": os.getenv("DB_PASSWORD", "ppl_password"),
    },
    # Enhanced Vision Service configuration
    "vision": {
        "distance_multiplier": 1000000.0,  # Autonomous system methodology
        "embedding_model": "Facenet512",  # 512-dimensional embeddings
        "detector_backend": "opencv",
        "enable_distance_calculation": True,
        "enable_embedding_generation": True,
        "enable_route_tracking": True,
        "confidence_threshold": 0.5,
        "frames_per_second": 3,
    },
    # API configuration
    "api": {
        "host": "0.0.0.0",
        "port": 8010,  # Phase 1 dedicated port
        "title": "PPL Meta Phase 1 - Enhanced Person Detection",
        "version": "1.0.0",
        "description": """
        Phase 1 Enhanced Person Detection System
        
        Features:
        - Session-based processing (unlimited re-executions)
        - 3D distance calculation using autonomous system methodology  
        - 512-dimensional facial embeddings with DeepFace
        - Person routes tracking with movement analytics
        - Vector similarity search with pgvector
        - Spatial analysis and heatmap generation
        - Master workflow lifecycle management
        """,
    },
}

# Global services
db_client: Phase1DatabaseClient = None
vision_service: EnhancedVisionService = None
workflow_controller: MasterLifecycleWorkflowController = None


# ================================================================
# Application Lifecycle Management
# ================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle manager for Phase 1."""

    global db_client, vision_service, workflow_controller

    try:
        logger.info("🚀 Starting Phase 1 Enhanced Person Detection System")

        # Initialize database client
        logger.info("📊 Initializing database client with pgvector support...")
        db_client = await create_phase1_database_client(PHASE1_CONFIG["database"])

        # Verify database schema
        await verify_phase1_database_schema(db_client)

        # Initialize enhanced vision service
        logger.info("👁️ Initializing enhanced vision service...")
        vision_service = EnhancedVisionService(
            database_client=db_client, config=PHASE1_CONFIG["vision"]
        )

        # Initialize master workflow controller
        logger.info("⚙️ Initializing master workflow controller...")
        workflow_controller = MasterLifecycleWorkflowController(
            database_client=db_client,
            vision_service=vision_service,
            config=PHASE1_CONFIG,
        )

        # Get system health metrics
        health_metrics = await db_client.get_system_health_metrics()
        logger.info(f"📈 System health metrics: {health_metrics}")

        logger.info("✅ Phase 1 system initialization completed successfully")

        yield  # Application runs here

    except Exception as e:
        logger.error(f"❌ Failed to initialize Phase 1 system: {e}")
        raise

    finally:
        # Cleanup
        logger.info("🧹 Shutting down Phase 1 system...")
        if db_client:
            await db_client.close()
        logger.info("✅ Phase 1 system shutdown completed")


async def verify_phase1_database_schema(db_client: Phase1DatabaseClient):
    """Verify that Phase 1 database schema is properly deployed."""

    logger.info("🔍 Verifying Phase 1 database schema...")

    # Check required tables exist
    required_tables = [
        "persons_lifecycle_master_workflows",
        "person_routes",
        "face_detections",
        "person_objects",
    ]

    try:
        async with db_client.pool.acquire() as conn:
            for table in required_tables:
                exists = await conn.fetchval(
                    "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = $1)",
                    table,
                )
                if not exists:
                    raise Exception(
                        f"Required table '{table}' not found. Please run phase1_database_schema.sql"
                    )
                logger.info(f"✅ Table '{table}' exists")

            # Check pgvector extension
            extension_exists = await conn.fetchval(
                "SELECT EXISTS (SELECT FROM pg_extension WHERE extname = 'vector')"
            )
            if not extension_exists:
                raise Exception(
                    "pgvector extension not installed. Please install pgvector extension."
                )
            logger.info("✅ pgvector extension is installed")

        logger.info("✅ Database schema verification completed successfully")

    except Exception as e:
        logger.error(f"❌ Database schema verification failed: {e}")
        raise


# ================================================================
# FastAPI Application Setup
# ================================================================

app = FastAPI(
    title=PHASE1_CONFIG["api"]["title"],
    version=PHASE1_CONFIG["api"]["version"],
    description=PHASE1_CONFIG["api"]["description"],
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ================================================================
# Phase 1 API Endpoints
# ================================================================


@app.get("/")
async def root():
    """Root endpoint with Phase 1 system information."""
    return {
        "system": "PPL Meta Phase 1 - Enhanced Person Detection",
        "version": PHASE1_CONFIG["api"]["version"],
        "status": "operational",
        "features": [
            "Session-based processing (unlimited re-executions)",
            "3D distance calculation",
            "512-dimensional facial embeddings",
            "Person routes tracking",
            "Vector similarity search",
            "Spatial analysis and heatmaps",
            "Master workflow management",
        ],
        "endpoints": {
            "workflows": "/api/v1/workflows",
            "health": "/health",
            "metrics": "/metrics",
            "docs": "/docs",
            "openapi": "/openapi.json",
        },
    }


@app.get("/health")
async def health_check():
    """Health check endpoint with system metrics."""

    try:
        # Get comprehensive health metrics
        db_health = await db_client.get_system_health_metrics()

        # Check service status
        services_status = {
            "database": "healthy" if db_client and db_client.pool else "unhealthy",
            "vision_service": "healthy" if vision_service else "unhealthy",
            "workflow_controller": "healthy" if workflow_controller else "unhealthy",
        }

        return {
            "status": "healthy",
            "timestamp": asyncio.get_event_loop().time(),
            "services": services_status,
            "database_metrics": db_health,
            "phase": "Phase 1 - Core Infrastructure & Enhanced Features",
        }

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": asyncio.get_event_loop().time(),
        }


@app.get("/metrics")
async def system_metrics():
    """Detailed system metrics for monitoring."""

    try:
        # Database metrics
        db_metrics = await db_client.get_system_health_metrics()

        # Embedding statistics
        embedding_stats = await db_client.get_embedding_statistics()

        # Route analytics
        route_analytics = await db_client.get_route_analytics_summary()

        # Active sessions
        active_sessions = list(workflow_controller.active_sessions.keys())

        return {
            "system_metrics": {
                "active_sessions": len(active_sessions),
                "active_session_ids": active_sessions,
                **db_metrics,
            },
            "embedding_metrics": embedding_stats,
            "route_analytics": route_analytics,
            "phase1_features": {
                "distance_calculation": PHASE1_CONFIG["vision"][
                    "enable_distance_calculation"
                ],
                "embedding_generation": PHASE1_CONFIG["vision"][
                    "enable_embedding_generation"
                ],
                "route_tracking": PHASE1_CONFIG["vision"]["enable_route_tracking"],
            },
        }

    except Exception as e:
        logger.error(f"Failed to get system metrics: {e}")
        return {"error": str(e)}


@app.post("/cleanup")
async def cleanup_old_data(days_old: int = 30):
    """Cleanup old data (admin endpoint)."""

    try:
        deleted_count = await db_client.cleanup_old_sessions(days_old)
        return {
            "status": "completed",
            "records_deleted": deleted_count,
            "days_old": days_old,
        }
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        return {"error": str(e)}


# ================================================================
# Include Phase 1 Workflow Router
# ================================================================

# Add the Phase 1 workflow router
phase1_router = create_phase1_router(workflow_controller)
app.include_router(phase1_router)


# ================================================================
# Development and Testing Endpoints
# ================================================================


@app.post("/dev/quick-test")
async def development_quick_test(background_tasks: BackgroundTasks):
    """Quick test endpoint for development (Phase 1 workflow execution)."""

    try:
        # Create test workflow execution
        test_request = WorkflowExecutionRequest(
            source_identifier="test-camera-lobby",
            source_type="camera_recording",
            source_id="test-media-123",
            execution_trigger="development_test",
            workflow_types=["face_detection", "person_routes"],
            configuration={
                "confidence_threshold": 0.5,
                "frames_per_second": 2,
                "enable_distance_calculation": True,
                "enable_embedding_generation": True,
                "enable_route_tracking": True,
            },
        )

        # Execute workflow
        result = await workflow_controller.start_workflow_execution(
            test_request, background_tasks
        )

        return {
            "test_status": "initiated",
            "session_uuid": result.session_uuid,
            "message": "Development test workflow started",
            "check_status_url": f"/api/v1/workflows/status/{result.session_uuid}",
        }

    except Exception as e:
        logger.error(f"Development test failed: {e}")
        return {"test_status": "failed", "error": str(e)}


@app.get("/dev/example-routes")
async def get_example_routes():
    """Get example person routes for development/testing."""

    try:
        routes_request = PersonRoutesRequest(
            time_range_hours=24, confidence_threshold=0.3, include_spatial_analysis=True
        )

        routes_analytics = await workflow_controller.get_person_routes_analytics(
            routes_request
        )

        return {"example_data": True, "routes_analytics": routes_analytics}

    except Exception as e:
        logger.error(f"Failed to get example routes: {e}")
        return {"error": str(e)}


# ================================================================
# Main Application Entry Point
# ================================================================


def run_phase1_application():
    """Run the Phase 1 application."""

    logger.info("🚀 Starting PPL Meta Phase 1 Enhanced Person Detection System")
    logger.info(
        f"📊 Database: {PHASE1_CONFIG['database']['host']}:{PHASE1_CONFIG['database']['port']}"
    )
    logger.info(
        f"🌐 API Server: http://{PHASE1_CONFIG['api']['host']}:{PHASE1_CONFIG['api']['port']}"
    )
    logger.info("📖 API Documentation: http://localhost:8010/docs")

    uvicorn.run(
        "phase1_integration:app",
        host=PHASE1_CONFIG["api"]["host"],
        port=PHASE1_CONFIG["api"]["port"],
        reload=True,
        log_level="info",
    )


if __name__ == "__main__":
    run_phase1_application()


# ================================================================
# Phase 1 Development Guide
# ================================================================

"""
PHASE 1 DEVELOPMENT DEPLOYMENT GUIDE
====================================

1. Database Setup:
   - Deploy phase1_database_schema.sql to PostgreSQL
   - Ensure pgvector extension is installed
   - Verify all tables and indexes are created

2. Dependencies Installation:
   pip install fastapi uvicorn asyncpg deepface opencv-python numpy pillow

3. Environment Configuration:
   export DB_HOST=localhost
   export DB_PORT=5432
   export DB_NAME=ppl_meta
   export DB_USER=ppl_user
   export DB_PASSWORD=ppl_password

4. Start Phase 1 System:
   python phase1_integration.py

5. API Testing:
   - Health Check: GET http://localhost:8010/health
   - System Metrics: GET http://localhost:8010/metrics
   - API Documentation: http://localhost:8010/docs
   - Quick Test: POST http://localhost:8010/dev/quick-test

6. Workflow Execution:
   POST http://localhost:8010/api/v1/workflows/execute
   {
     "source_identifier": "camera-lobby-main",
     "source_type": "camera_recording",
     "source_id": "media-12345",
     "execution_trigger": "automatic",
     "workflow_types": ["face_detection", "person_routes"],
     "configuration": {
       "confidence_threshold": 0.5,
       "frames_per_second": 3,
       "enable_distance_calculation": true,
       "enable_embedding_generation": true,
       "enable_route_tracking": true
     }
   }

7. Person Routes Analytics:
   POST http://localhost:8010/api/v1/workflows/analytics/person-routes
   {
     "time_range_hours": 24,
     "confidence_threshold": 0.5,
     "include_spatial_analysis": true
   }

8. Vector Search (Similar Faces):
   POST http://localhost:8010/api/v1/workflows/search/similar-faces
   {
     "embedding_vector": [0.1, 0.2, 0.3, ...], // 512 dimensions
     "similarity_threshold": 0.8,
     "limit": 10
   }

PHASE 1 KEY FEATURES DELIVERED:
✅ Session-based processing (no duplicate prevention)
✅ 3D distance calculation using autonomous system methodology
✅ 512-dimensional facial embeddings with DeepFace
✅ Person routes tracking with movement analytics
✅ Vector similarity search with pgvector
✅ Spatial analysis and heatmap generation
✅ Master workflow lifecycle management
✅ Complete REST API for all features
✅ Background task processing
✅ Comprehensive health monitoring
✅ Development and testing endpoints

NEXT PHASE: Vision Service Integration & Testing (Phase 2)
"""
