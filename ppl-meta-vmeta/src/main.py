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
import os
from logging.handlers import RotatingFileHandler

# Create logs directory if it doesn't exist
log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "ppl-meta-vmeta.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        RotatingFileHandler(
            log_file, maxBytes=10*1024*1024, backupCount=5
        ),
        logging.StreamHandler()
    ]
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

            # Initialize orchestrator client for fetching person objects
            from utils.orchestrator_client import OrchestratorClient
            orchestrator_client = OrchestratorClient()

            mvr_service = MVRService(
                repository=mvr_repository,
                ml_processor=ml_processor,
                orchestrator_client=orchestrator_client
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

        # Initialize Batch Processing services
        try:
            logger.info("📦 Initializing Batch Processing services...")
            from database.batch_repository import BatchProcessingRepository
            from services.batch_config import BatchConfigService
            from services.batch_monitor import BatchMonitor
            # from services.hybrid_batch_trigger import HybridBatchTrigger  # OLD SYSTEM DISABLED
            from services.pipeline_executor import PipelineExecutor
            from services.batch_timeout_manager import PollingFallbackManager
            from api.v1.batch_processing import set_batch_services
            import asyncpg
            
            # Create connection pool for batch processing
            batch_pool = await asyncpg.create_pool(
                host=settings.DB_HOST,
                port=settings.DB_PORT,
                user=settings.DB_USER,
                password=settings.DB_PASSWORD,
                database=settings.DB_NAME,
                min_size=2,
                max_size=10
            )
            
            # Create batch repository
            batch_repository = BatchProcessingRepository(
                connection_pool=batch_pool
            )
            
            # Create batch config service
            batch_config = BatchConfigService(repository=batch_repository)
            
            # OLD SYSTEM DISABLED: HybridBatchTrigger replaced by PollingFallbackManager
            # The old event-driven batch system (HybridBatchTrigger) created 20-video batches
            # which interfered with the new recording-aware incremental batching (5 videos per batch).
            # PollingFallbackManager directly calls the tracking API and doesn't need BatchMonitor
            # for triggering, so we can safely disable the old system.
            
            # hybrid_trigger = HybridBatchTrigger(
            #     default_timeout_minutes=10,
            #     default_min_partial_batch_size=2,
            #     max_wait_hours=24
            # )
            
            # Create pipeline executor
            pipeline_executor = PipelineExecutor(
                media_service_url="http://localhost:8000",
                orchestrator_url="http://localhost:8002",
                max_workers=3
            )
            
            # Start pipeline executor
            await pipeline_executor.start()
            logger.info("✅ PipelineExecutor started")
            
            # Create batch monitor (simplified - no hybrid trigger)
            # NOTE: PollingFallbackManager receives batch_monitor reference but doesn't use it
            # for triggering batches. It directly calls the tracking session API.
            batch_monitor = BatchMonitor(
                repository=batch_repository,
                config_service=batch_config,
                batch_processor_callback=None
            )
            
            # Wire up hybrid trigger to batch monitor - DISABLED
            # batch_monitor.set_hybrid_trigger(hybrid_trigger)
            
            # Create and start polling fallback manager
            # NOTE: Collection IDs are now dynamically managed via recording events.
            # The polling manager will monitor ALL active recordings from Camera service
            # recording start/stop events, not a single hardcoded collection.
            polling_manager = PollingFallbackManager(
                batch_monitor=batch_monitor,
                poll_interval_seconds=30,  # Check every 30 seconds
                enabled=True,
                media_url="http://localhost:8000",
                vision_url="http://localhost:8003",
                vmeta_url="http://localhost:8008",
                node_url="http://localhost:8001",
                batch_size=5,  # Trigger after 5 videos
                collection_id=None,  # Dynamic - managed by recording events
                pipeline_executor=pipeline_executor  # Pass executor for explicit video_uuids
            )
            
            # Start polling in background
            await polling_manager.start()
            
            # Set global services for batch processing API (no trigger - disabled)
            set_batch_services(
                repository=batch_repository,
                monitor=batch_monitor,
                trigger=None,  # Hybrid trigger disabled
                executor=pipeline_executor
            )
            
            # Set polling manager reference for recording events API
            from api.v1 import recording_events
            recording_events.polling_manager = polling_manager
            
            # Store for cleanup
            app.state.batch_pool = batch_pool
            app.state.polling_manager = polling_manager
            app.state.pipeline_executor = pipeline_executor
            
            logger.info("✅ Batch Processing services initialized")
            logger.info(
                "✅ Polling manager started "
                "(30s interval, batch_size=5, collection=usb_camera_0)"
            )
            
        except Exception as e:
            logger.warning(
                f"⚠️ Batch Processing services not initialized: {e}"
            )
            logger.warning(
                "⚠️ Batch Processing features will not be available"
            )

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
        if hasattr(app.state, 'batch_pool') and app.state.batch_pool:
            await app.state.batch_pool.close()
        if hasattr(app.state, 'pipeline_executor') and app.state.pipeline_executor:
            await app.state.pipeline_executor.stop()
        if hasattr(app.state, 'polling_manager') and app.state.polling_manager:
            await app.state.polling_manager.stop()
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

# Add recording events router
try:
    from api.v1 import recording_events
    app.include_router(
        recording_events.router,
        tags=["recording-events"]
    )
    logger.info("✅ Recording events API registered")
except Exception as e:
    logger.warning(f"⚠️ Recording events API not available: {e}")

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

# Add Batch Processing API router with error handling
try:
    from api.v1.batch_processing import router as batch_processing_router
    app.include_router(
        batch_processing_router,
        prefix="/api/v1/batch-processing",
        tags=["batch-processing"]
    )
    logger.info("✅ Batch Processing API router added successfully")
except ImportError as e:
    logger.warning(f"⚠️ Batch Processing API router not available: {e}")
except Exception as e:
    logger.error(f"❌ Error adding Batch Processing API router: {e}")


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


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("🛑 Shutting down vmeta service...")
    
    # Stop polling manager if it exists
    if hasattr(app.state, 'polling_manager'):
        try:
            await app.state.polling_manager.stop()
            logger.info("✅ Polling manager stopped")
        except Exception as e:
            logger.error(f"❌ Error stopping polling manager: {e}")
    
    # Close batch processing pool if it exists
    if hasattr(app.state, 'batch_pool'):
        try:
            await app.state.batch_pool.close()
            logger.info("✅ Batch processing pool closed")
        except Exception as e:
            logger.error(f"❌ Error closing batch pool: {e}")


if __name__ == "__main__":
    logger.info("🚀 Starting PPL Meta vmeta Service")
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
        log_level="info",
    )
