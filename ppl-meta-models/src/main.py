"""PPL Meta Models catalog service."""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
import sys
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import router as catalog_router
from catalog import seed_builtins
from config import config
from database import SessionLocal, create_tables, test_connection

src_dir = Path(__file__).resolve().parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))


@asynccontextmanager
async def lifespan(_application: FastAPI):
    create_tables()
    db = SessionLocal()
    try:
        seed_builtins(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title="PPL Meta Models Service",
    description="Detection model catalog, assignments, and later training jobs",
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

app.include_router(catalog_router, prefix="/api/v1/mv-models", tags=["mv-models"])


@app.get("/")
async def root():
    return {
        "service": "ppl-meta-models",
        "version": config.VERSION,
        "endpoints": {
            "health": "/health",
            "catalog": "/api/v1/mv-models",
        },
    }


@app.get("/health")
async def health_check():
    return {
        "service": "ppl-meta-models",
        "status": "healthy" if test_connection() else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
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
