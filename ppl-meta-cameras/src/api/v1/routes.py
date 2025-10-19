"""
API v1 routes for PPL Meta Cameras microservice.
"""

from fastapi import APIRouter
from src.api.v1.endpoints.auth import router as auth_router
from src.api.v1.endpoints.cameras import router as cameras_router
from src.api.v1.endpoints.mobile_streaming import router as mobile_streaming_router
from src.api.v1.endpoints.recording_sessions import router as recording_sessions_router
from src.api.v1.endpoints.streaming import router as streaming_router

# Create main v1 router
v1_router = APIRouter()

# Include endpoint routers
v1_router.include_router(cameras_router, prefix="/cameras", tags=["Cameras"])
v1_router.include_router(streaming_router, prefix="/streaming", tags=["Streaming"])
v1_router.include_router(
    mobile_streaming_router, prefix="/streaming", tags=["Mobile Streaming"]
)
v1_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
v1_router.include_router(recording_sessions_router, tags=["Recording Sessions"])
