import logging

import uvicorn
from api.admin import router as admin_router
from api.admin_ui import router as admin_ui_router
from api.health import router as health_router
from api.installations import router as authority_router
from core.storage import initialize_database, seed_demo_installation
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

app = FastAPI(
    title="PPL Meta Authority",
    description="Minimal authority service for ownership, installation registration, and licence lifecycle.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(authority_router)
app.include_router(admin_router)
app.include_router(admin_ui_router)


@app.on_event("startup")
async def startup_event() -> None:
    initialize_database()
    seed_demo_installation()
    logging.info("PPL Meta Authority database initialized")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)