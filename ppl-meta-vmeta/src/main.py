"""
PPL Meta vmeta Service
Vector-based facial embeddings and person detection analytics

Main FastAPI application entry point.
"""

import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent))

from api.v1 import analytics, embeddings, health, workflows
from config.settings import settings
from database.client import VmetaDatabaseClient, create_vmeta_database_client
from services.embedding_service import EmbeddingService
from services.workflow_service import WorkflowService

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global services
db_client: VmetaDatabaseClient = None
embedding_service: EmbeddingService = None
workflow_service: WorkflowService = None

# MVR-People services (lazy loaded)
mvr_repository = None
mvr_service = None
mvr_matcher = None
mvr_background_processor = None
mvr_integration_hook = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle manager for vmeta service."""

    global db_client, embedding_service, workflow_service
    global mvr_repository, mvr_service, mvr_matcher
    global mvr_background_processor, mvr_integration_hook

    try:
        logger.info("🚀 Starting PPL Meta vmeta Service")
        logger.info(f"📊 Database: {settings.DB_HOST}:{settings.DB_PORT}")
        logger.info(f"🌐 API Server: http://{settings.HOST}:{settings.PORT}")

        # Initialize database client
        logger.info("📊 Initializing database client with pgvector support...")
        db_client = await create_vmeta_database_client(settings.get_database_config())

        # Initialize embedding service
        logger.info("🧠 Initializing embedding service...")
        embedding_service = EmbeddingService(
            database_client=db_client,
            config={"embedding_model": settings.EMBEDDING_MODEL}
        )

        # Initialize workflow service
        logger.info("⚙️ Initializing workflow service...")
        workflow_service = WorkflowService(
            database_client=db_client, embedding_service=embedding_service
        )

        # Initialize MVR-People services (lazy initialization)
        try:
            logger.info("🧬 Initializing MVR-People services...")
            from database.mvr_repository import MVRRepository
            from services.mvr_service import MVRService
            from services.mvr_matcher import MVRMatcher
            from ml.mvr_processor import MVRProcessor
            from background.mvr_background_processor import (
                MVRBackgroundProcessor
            )
            from background.mvr_integration_hook import MVRIntegrationHook
            from background import mvr_helper
            import asyncpg

            # Create connection pool for MVR repository
            mvr_pool = await asyncpg.create_pool(
                host=settings.DB_HOST,
                port=settings.DB_PORT,
                user=settings.DB_USER,
                password=settings.DB_PASSWORD,
                database=settings.DB_NAME,
                min_size=2,
                max_size=10
            )

            mvr_repository = MVRRepository(connection_pool=mvr_pool)

            # Initialize ML processor
            ml_processor = MVRProcessor()

            mvr_service = MVRService(
                repository=mvr_repository,
                ml_processor=ml_processor
            )
            mvr_matcher = MVRMatcher(
                repository=mvr_repository,
                ml_processor=ml_processor
            )

            mvr_background_processor = MVRBackgroundProcessor(
                mvr_service=mvr_service,
                mvr_matcher=mvr_matcher,
                max_retries=3,
                retry_delay=5.0
            )

            mvr_integration_hook = MVRIntegrationHook(
                background_processor=mvr_background_processor
            )

            # Register hook globally for easy access
            mvr_helper.set_mvr_integration_hook(mvr_integration_hook)

            # Store pool for cleanup
            app.state.mvr_pool = mvr_pool

            logger.info("✅ MVR-People services initialized successfully")

        except Exception as e:
            logger.warning(f"⚠️ MVR-People services not initialized: {e}")
            logger.warning("⚠️ MVR-People features will not be available")

        # Register with service discovery
        # await register_with_discovery()

        logger.info("✅ vmeta service initialization completed successfully")

        yield  # Application runs here

    except Exception as e:
        logger.error(f"❌ Failed to initialize vmeta service: {e}")
        raise

    finally:
        # Cleanup
        logger.info("🧹 Shutting down vmeta service...")
        if hasattr(app.state, 'mvr_pool') and app.state.mvr_pool:
            await app.state.mvr_pool.close()
        if db_client:
            await db_client.close()
        logger.info("✅ vmeta service shutdown completed")


# Create FastAPI application
app = FastAPI(
    title="PPL Meta vmeta Service",
    version=settings.SERVICE_VERSION,
    description="Vector-based facial embeddings and person detection analytics",
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

# Include API routers
app.include_router(health.router, tags=["health"])
app.include_router(workflows.router, prefix="/api/v1/workflows", tags=["workflows"])
app.include_router(embeddings.router, prefix="/api/v1/embeddings", tags=["embeddings"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["analytics"])

# Add cross-video tracking router with error handling
try:
    from api.v1.cross_video_tracking_simple import router as cross_video_router
    app.include_router(
        cross_video_router,
        prefix="/api/v1/cross-video",
        tags=["cross-video-tracking"]
    )
    logger.info("✅ Cross-video tracking router (simple + Phase 5/6) added successfully")
except ImportError as e:
    logger.warning(f"⚠️ Cross-video tracking router not available: {e}")
except Exception as e:
    logger.error(f"❌ Error adding cross-video tracking router: {e}")

# Add MVR-People API router with error handling
try:
    from api.routes.mvr_people import router as mvr_people_router
    app.include_router(
        mvr_people_router,
        tags=["mvr-people"]
    )
    logger.info("✅ MVR-People API router added successfully (14 endpoints)")
except ImportError as e:
    logger.warning(f"⚠️ MVR-People API router not available: {e}")
except Exception as e:
    logger.error(f"❌ Error adding MVR-People API router: {e}")


@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "vmeta",
        "version": settings.SERVICE_VERSION,
        "description": "PPL Meta Vector-based facial embeddings and analytics",
        "status": "operational",
        "capabilities": settings.get_service_info()["capabilities"],
    }


if __name__ == "__main__":
    logger.info("🚀 Starting PPL Meta vmeta Service")
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
        log_level="info",
    )
