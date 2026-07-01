"""Health check endpoint for Matrix Service."""
from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health():
    return {"status": "healthy", "service": "ppl-meta-matrix", "version": "0.1.0"}