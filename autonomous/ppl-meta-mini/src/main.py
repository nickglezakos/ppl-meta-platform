"""
PPL Meta Mini - Standalone Face Analytics Service
"""

import logging

import uvicorn
from api.analytics import router as analytics_router
from api.camera import camera_router, initialize_camera_services
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

app = FastAPI(
    title="PPL Meta Mini",
    description="Standalone Face Analytics with Video Processing",
    version="1.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(analytics_router, prefix="/api/v1", tags=["analytics"])
app.include_router(camera_router, tags=["camera"])


# Initialize camera services on startup
@app.on_event("startup")
async def startup_event():
    """Initialize services on application startup."""
    try:
        # Initialize camera services
        initialize_camera_services()
        logging.info("✅ PPL Meta Mini started with camera support")
    except Exception as e:
        logging.error(f"❌ Failed to initialize camera services: {e}")
        logging.info("⚠️ PPL Meta Mini started without camera support")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "PPL Meta Mini",
        "version": "1.1.0",
        "description": "Standalone Face Analytics with Video Processing",
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "upload_and_analyze": "/api/v1/upload-and-analyze",
            "camera_detect": "/api/v1/camera/detect-and-connect",
            "camera_record": "/api/v1/camera/record-and-analyze",
            "camera_status": "/api/v1/camera/status",
        },
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "ppl-meta-mini", "version": "1.1.0"}


if __name__ == "__main__":
    # Production configuration
    uvicorn.run("main:app", host="0.0.0.0", port=8004, reload=False)
