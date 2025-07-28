"""
PPL Meta Mini - Standalone Face Analyt        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "face_grouping": "/api/v1/group-faces",
            "coordinate_analysis": "/api/v1/analyze-coordinates",
            "face_detection_info": "/api/v1/face-detection/info",
            "video_analysis": "/api/v1/analyze-video",
            "video_streaming": "/api/v1/stream-faces",
            "complete_analysis": "/api/v1/complete-video-analysis",
            "demo_data": "/api/v1/demo-data"
        }ervice
"""

import logging

import uvicorn
from api.analytics import router as analytics_router
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
            "face_grouping": "/api/v1/group-faces",
            "coordinate_analysis": "/api/v1/analyze-coordinates",
            "face_detection_info": "/api/v1/face-detection/info",
            "video_analysis": "/api/v1/analyze-video",
            "video_streaming": "/api/v1/stream-faces",
            "demo_data": "/api/v1/demo-data",
        },
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "ppl-meta-mini", "version": "1.1.0"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8004, reload=True)
