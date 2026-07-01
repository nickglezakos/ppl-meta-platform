"""PPL Meta Matrix — Cross-Installation Grouping & Aggregated Reporting Service.

Phase 1-2: Scaffolding, group CRUD, membership management.
Runs alongside ppl-meta-node on the primary installation in a Matrix Network.
"""

import logging
import os
import uuid
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from models.database import init_db
from api.groups import router as groups_router
from api.memberships import router as memberships_router
from api.users import router as users_router
from api.reports import router as reports_router
from api.health import router as health_router
from services.matrix_service import matrix_service

logger = logging.getLogger("ppl-meta-matrix")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

MATRIX_PORT = int(os.environ.get("MATRIX_PORT", "8015"))


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logger.info("Starting PPL Meta Matrix Service...")
    init_db()
    logger.info("Database tables verified")

    # Phase 1: Auto-create single-member Matrix on first boot
    try:
        matrix_service.auto_create_default_group()
    except Exception as exc:
        logger.error("Failed to auto-create default Matrix group: %s", exc)

    logger.info("Matrix Service startup complete")
    yield
    logger.info("Matrix Service shutting down")


app = FastAPI(
    title="PPL Meta Matrix",
    description="Cross-Installation Grouping & Aggregated Reporting",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

app.include_router(health_router)
app.include_router(groups_router, prefix="/api/v1/matrix")
app.include_router(memberships_router, prefix="/api/v1/matrix")
app.include_router(users_router, prefix="/api/v1/matrix")
app.include_router(reports_router, prefix="/api/v1/matrix")


@app.get("/")
async def root():
    return {"service": "ppl-meta-matrix", "version": "0.1.0", "status": "operational"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=MATRIX_PORT, reload=True)