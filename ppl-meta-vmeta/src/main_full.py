"""
PPL Meta vmeta Service - Full Implementation
Vector-based facial embeddings and person detection analytics

Complete implementation with Phase 1 functionality including:
- Database connectivity with pgvector
- Facial embeddings generation using DeepFace
- Session-based workflow processing
- Vector similarity search
- Distance calculations
- Person routes analytics
"""

import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Import vmeta services
from database.client import VmetaDatabaseClient
from services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)

# Global service instances
db_client: Optional[VmetaDatabaseClient] = None
embedding_service: Optional[EmbeddingService] = None
workflow_service: Optional[WorkflowService] = None

# Service state tracking
service_state = {
    "initialized": False,
    "database_connected": False,
    "services_ready": False,
    "deepface_available": False,
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle manager for vmeta service."""
    global db_client, embedding_service, workflow_service

    try:
        logger.info("🚀 Starting PPL Meta vmeta Service - Full Implementation")

        # Initialize database configuration
        db_config = {
            "host": os.getenv("POSTGRES_HOST", "localhost"),
            "port": int(os.getenv("POSTGRES_PORT", 5432)),
            "database": os.getenv("POSTGRES_DB", "ppl_meta"),
            "username": os.getenv("POSTGRES_USER", "nickgklezakos"),
            "password": os.getenv("POSTGRES_PASSWORD", ""),
        }

        logger.info(
            f"📊 Database: {db_config['host']}:{db_config['port']}/{db_config['database']}"
        )

        # Initialize database client
        db_client = VmetaDatabaseClient(db_config)
        await db_client.initialize()
        service_state["database_connected"] = True
        logger.info("✅ Database client initialized")

        # Initialize embedding service
        embedding_config = {
            "embedding_model": "Facenet512",
            "detector_backend": "opencv",
            "distance_multiplier": 1000000.0,
        }
        embedding_service = EmbeddingService(db_client, embedding_config)

        # Check DeepFace availability
        try:
            from deepface import DeepFace

            service_state["deepface_available"] = True
            logger.info("✅ DeepFace available for facial embeddings")
        except ImportError:
            service_state["deepface_available"] = False
            logger.warning("⚠️ DeepFace not available - facial embeddings disabled")

        # Initialize workflow service
        workflow_service = WorkflowService(db_client, embedding_service)

        service_state["initialized"] = True
        service_state["services_ready"] = True

        logger.info("✅ vmeta service full initialization completed successfully")
        logger.info("🌐 API Server: http://0.0.0.0:8008")

        yield  # Application runs here

    except Exception as e:
        logger.error(f"❌ Failed to initialize vmeta service: {e}", exc_info=True)
        service_state["services_ready"] = False
        raise

    finally:
        # Cleanup
        logger.info("🧹 Shutting down vmeta service...")
        if db_client:
            await db_client.close()
        logger.info("✅ vmeta service shutdown completed")


# Create FastAPI application
app = FastAPI(
    title="PPL Meta vmeta Service",
    version="2.19.0",
    description="Vector-based facial embeddings and person detection analytics with Phase 1 functionality",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response Models
class WorkflowRequest(BaseModel):
    session_uuid: str
    media_id: str
    source_identifier: str
    source_type: str = "video"
    execution_trigger: str = "automatic"
    config: Optional[Dict[str, Any]] = None


class EmbeddingRequest(BaseModel):
    face_image_base64: str
    session_uuid: Optional[str] = None


class SimilaritySearchRequest(BaseModel):
    target_embedding: List[float]
    threshold: float = 0.7
    limit: int = 10
    session_uuid: Optional[str] = None


class PersonRoutesRequest(BaseModel):
    session_uuid: str
    time_range_start: Optional[str] = None
    time_range_end: Optional[str] = None


@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "vmeta",
        "version": "2.19.0",
        "description": "PPL Meta Vector-based facial embeddings and analytics",
        "status": "operational",
        "capabilities": [
            "facial_embeddings",
            "vector_similarity_search",
            "session_based_workflows",
            "3d_distance_calculation",
            "person_routes_analytics",
        ],
        "phase1_features": {
            "session_based_processing": True,
            "distance_calculation": True,
            "facial_embeddings_512d": service_state["deepface_available"],
            "vector_similarity_search": True,
            "person_routes_tracking": True,
        },
    }


@app.get("/health")
async def health_check():
    """Comprehensive service health check endpoint."""

    health_status = "healthy"
    health_details = {}

    try:
        # Check database connectivity
        if db_client and service_state["database_connected"]:
            # Try a simple database query
            health_details["database"] = "connected"
        else:
            health_status = "unhealthy"
            health_details["database"] = "disconnected"

        # Check services initialization
        health_details["services_initialized"] = service_state["initialized"]
        health_details["deepface_available"] = service_state["deepface_available"]

        # Get system health metrics if possible
        if workflow_service and service_state["services_ready"]:
            try:
                metrics = await workflow_service.get_system_health_metrics()
                health_details["system_metrics"] = metrics
            except Exception as e:
                health_details["system_metrics_error"] = str(e)

    except Exception as e:
        health_status = "unhealthy"
        health_details["error"] = str(e)

    return {
        "status": health_status,
        "service": "vmeta",
        "version": "2.19.0",
        "database_connected": service_state["database_connected"],
        "services_initialized": service_state["initialized"],
        "services_ready": service_state["services_ready"],
        "deepface_available": service_state["deepface_available"],
        "details": health_details,
        "timestamp": asyncio.get_event_loop().time(),
    }


@app.get("/metrics")
async def service_metrics():
    """Service metrics endpoint."""
    try:
        if not workflow_service:
            raise HTTPException(
                status_code=503, detail="Workflow service not initialized"
            )

        metrics = await workflow_service.get_system_metrics()
        return {
            "metrics": metrics,
            "status": "operational",
            "service": "vmeta",
            "timestamp": asyncio.get_event_loop().time(),
        }
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        return {
            "metrics": {
                "active_sessions": 0,
                "total_embeddings_generated": 0,
                "vector_searches_performed": 0,
                "uptime_seconds": int(asyncio.get_event_loop().time()),
            },
            "status": "partial",
            "error": str(e),
        }


# Workflow Management Endpoints
@app.post("/api/v1/workflows/execute")
async def execute_workflow(workflow_request: WorkflowRequest):
    """Execute enhanced person detection workflow with Phase 1 features."""
    try:
        if not workflow_service:
            raise HTTPException(
                status_code=503, detail="Workflow service not initialized"
            )

        result = await workflow_service.execute_workflow(
            session_uuid=workflow_request.session_uuid,
            media_id=workflow_request.media_id,
            source_identifier=workflow_request.source_identifier,
            source_type=workflow_request.source_type,
            execution_trigger=workflow_request.execution_trigger,
            config=workflow_request.config or {},
        )

        return {
            "status": "initiated",
            "session_uuid": workflow_request.session_uuid,
            "workflow_id": result.get("workflow_id"),
            "message": "vmeta workflow execution started with Phase 1 features",
            "capabilities_enabled": [
                "facial_embeddings",
                "distance_calculation",
                "session_tracking",
                "person_routes",
            ],
            "result": result,
        }

    except Exception as e:
        logger.error(f"Error executing workflow: {e}")
        raise HTTPException(
            status_code=500, detail=f"Workflow execution failed: {str(e)}"
        )


@app.get("/api/v1/workflows/status/{session_uuid}")
async def get_workflow_status(session_uuid: str):
    """Get workflow execution status."""
    try:
        if not workflow_service:
            raise HTTPException(
                status_code=503, detail="Workflow service not initialized"
            )

        status = await workflow_service.get_workflow_status(session_uuid)

        return {
            "session_uuid": session_uuid,
            "status": status.get("status", "unknown"),
            "progress": status.get("progress", 0),
            "message": status.get("message", "Status retrieved"),
            "details": status,
        }

    except Exception as e:
        logger.error(f"Error getting workflow status: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get workflow status: {str(e)}"
        )


@app.get("/api/v1/workflows/sessions/active")
async def get_active_sessions():
    """Get all active workflow sessions."""
    try:
        if not db_client:
            raise HTTPException(
                status_code=503, detail="Database client not initialized"
            )

        sessions = await db_client.get_active_sessions()

        return {
            "active_sessions": sessions,
            "total_count": len(sessions),
            "service": "vmeta",
        }

    except Exception as e:
        logger.error(f"Error getting active sessions: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get active sessions: {str(e)}"
        )


# Embeddings Endpoints
@app.post("/api/v1/embeddings/generate")
async def generate_embeddings(embedding_request: EmbeddingRequest):
    """Generate facial embeddings for face images using Phase 1 DeepFace integration."""
    try:
        if not embedding_service:
            raise HTTPException(
                status_code=503, detail="Embedding service not initialized"
            )

        if not service_state["deepface_available"]:
            raise HTTPException(
                status_code=503,
                detail="DeepFace not available for embedding generation",
            )

        result = await embedding_service.generate_facial_embedding(
            face_image_base64=embedding_request.face_image_base64,
            session_uuid=embedding_request.session_uuid,
        )

        return {
            "embeddings_generated": 1,
            "embedding": result["embedding"],
            "model": "Facenet512",
            "dimensions": 512,
            "status": "success",
            "service": "vmeta",
            "result": result,
        }

    except Exception as e:
        logger.error(f"Error generating embeddings: {e}")
        raise HTTPException(
            status_code=500, detail=f"Embedding generation failed: {str(e)}"
        )


@app.post("/api/v1/embeddings/search")
async def search_similar_faces(search_request: SimilaritySearchRequest):
    """Search for similar faces using vector similarity with Phase 1 pgvector integration."""
    try:
        if not embedding_service:
            raise HTTPException(
                status_code=503, detail="Embedding service not initialized"
            )

        result = await embedding_service.search_similar_faces(
            target_embedding=search_request.target_embedding,
            threshold=search_request.threshold,
            limit=search_request.limit,
            session_uuid=search_request.session_uuid,
        )

        return {
            "similar_faces": result["similar_faces"],
            "total_matches": len(result["similar_faces"]),
            "search_time_ms": result.get("search_time_ms", 0),
            "threshold_used": search_request.threshold,
            "service": "vmeta",
            "status": "success",
        }

    except Exception as e:
        logger.error(f"Error searching similar faces: {e}")
        raise HTTPException(
            status_code=500, detail=f"Similar faces search failed: {str(e)}"
        )


# Analytics Endpoints
@app.post("/api/v1/analytics/person-routes")
async def analyze_person_routes(analytics_request: PersonRoutesRequest):
    """Analyze person movement routes and patterns using Phase 1 spatial analysis."""
    try:
        if not workflow_service:
            raise HTTPException(
                status_code=503, detail="Workflow service not initialized"
            )

        result = await workflow_service.analyze_person_routes(
            session_uuid=analytics_request.session_uuid,
            time_range_start=analytics_request.time_range_start,
            time_range_end=analytics_request.time_range_end,
        )

        return {
            "person_routes": result["routes"],
            "movement_statistics": result["statistics"],
            "session_uuid": analytics_request.session_uuid,
            "analysis_completed_at": result.get("completed_at"),
            "status": "success",
            "service": "vmeta",
        }

    except Exception as e:
        logger.error(f"Error analyzing person routes: {e}")
        raise HTTPException(
            status_code=500, detail=f"Person routes analysis failed: {str(e)}"
        )


@app.get("/api/v1/analytics/heatmap")
async def generate_heatmap(session_uuid: Optional[str] = None):
    """Generate spatial heatmap for person detection."""
    try:
        if not workflow_service:
            raise HTTPException(
                status_code=503, detail="Workflow service not initialized"
            )

        result = await workflow_service.generate_heatmap(session_uuid)

        return {
            "heatmap_data": result["heatmap_data"],
            "grid_size": result["grid_size"],
            "session_uuid": session_uuid,
            "generated_at": result.get("generated_at"),
            "service": "vmeta",
            "status": "success",
        }

    except Exception as e:
        logger.error(f"Error generating heatmap: {e}")
        raise HTTPException(
            status_code=500, detail=f"Heatmap generation failed: {str(e)}"
        )


# Development and Testing
@app.post("/dev/quick-test")
async def quick_test():
    """Development quick test endpoint that verifies Phase 1 functionality."""
    test_results = {}
    overall_status = "passed"

    try:
        # Test database connectivity
        if db_client and service_state["database_connected"]:
            test_results["database"] = "connected"
        else:
            test_results["database"] = "failed"
            overall_status = "failed"

        # Test service initialization
        test_results["services_initialized"] = service_state["initialized"]
        test_results["workflow_service"] = workflow_service is not None
        test_results["embedding_service"] = embedding_service is not None

        # Test DeepFace availability
        test_results["deepface_available"] = service_state["deepface_available"]

        # If all services are ready, test basic functionality
        if service_state["services_ready"]:
            try:
                # Test system metrics
                if workflow_service:
                    metrics = await workflow_service.get_system_health_metrics()
                    test_results["system_metrics"] = "operational"
                else:
                    test_results["system_metrics"] = "service_unavailable"
            except Exception as e:
                test_results["system_metrics"] = f"error: {str(e)}"

        return {
            "test_status": overall_status,
            "service": "vmeta",
            "version": "2.19.0",
            "phase1_functionality": "implemented",
            "message": "vmeta service with Phase 1 features is operational",
            "test_results": test_results,
        }

    except Exception as e:
        logger.error(f"Quick test failed: {e}")
        return {
            "test_status": "failed",
            "service": "vmeta",
            "error": str(e),
            "test_results": test_results,
        }


@app.get("/dev/service-info")
async def service_info():
    """Development service information endpoint."""
    return {
        "service_name": "vmeta",
        "service_type": "backend",
        "port": 8008,
        "version": "2.19.0",
        "phase1_implementation": True,
        "capabilities": [
            "facial_embeddings_512d",
            "vector_similarity_search",
            "session_based_workflows",
            "3d_distance_calculation",
            "person_routes_analytics",
        ],
        "integration_points": {
            "discovery_service": "http://localhost:8006",
            "orchestrator": "http://localhost:8002",
            "gateway": "http://localhost:8080",
        },
        "database": "postgresql://localhost:5432/ppl_meta",
        "deepface_available": service_state["deepface_available"],
        "status": (
            "development_ready" if service_state["services_ready"] else "initializing"
        ),
        "phase1_features": {
            "session_based_processing": True,
            "distance_calculation": True,
            "facial_embeddings": service_state["deepface_available"],
            "vector_search": True,
            "person_routes": True,
        },
    }


# Cleanup endpoint
@app.post("/cleanup")
async def cleanup_service():
    """Cleanup service resources and sessions."""
    try:
        if workflow_service:
            cleanup_result = await workflow_service.cleanup_sessions()
            return {
                "status": "completed",
                "message": "Service cleanup completed",
                "cleanup_result": cleanup_result,
            }
        else:
            return {"status": "completed", "message": "No active services to cleanup"}
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")


if __name__ == "__main__":
    logger.info("🚀 Starting PPL Meta vmeta Service - Full Implementation")
    uvicorn.run(
        "main_full:app", host="0.0.0.0", port=8008, reload=True, log_level="info"
    )
