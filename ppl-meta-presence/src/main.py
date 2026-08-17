"""PPL Meta Presence Service - backend skeleton."""

from contextlib import asynccontextmanager
from datetime import datetime
import os
import sys
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.presence_routes import build_internal_router, build_presence_router
from config import config
from database import test_connection
from services.presence_service import PresenceService

workspace_root = Path(__file__).resolve().parents[2]
if str(workspace_root) not in sys.path:
    sys.path.insert(0, str(workspace_root))

presence_service = PresenceService()


@asynccontextmanager
async def lifespan(_application: FastAPI):
    await presence_service.startup()
    yield
    await presence_service.shutdown()


app = FastAPI(
    title="PPL Meta Presence Service",
    description="Presence identity, QR, session, and analytics orchestration service",
    version=config.VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(build_presence_router(presence_service), prefix="/api/v1/presence", tags=["presence"])
app.include_router(build_internal_router(presence_service), prefix="/api/v1/presence", tags=["presence-internal"])


@app.get("/")
async def root():
    return {
        "service": "ppl-meta-presence",
        "description": "Presence identity, QR, session, and analytics orchestration service",
        "version": config.VERSION,
        "endpoints": {
            "health": "/health",
            "presence": "/api/v1/presence/*",
        },
    }


@app.get("/health")
async def health_check():
    return {
        "service": "ppl-meta-presence",
        "status": "healthy" if test_connection() else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "version": config.VERSION,
        "database": "connected" if test_connection() else "unavailable",
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=config.HOST,
        port=config.PORT,
        reload=True,
        log_level="info",
    )
