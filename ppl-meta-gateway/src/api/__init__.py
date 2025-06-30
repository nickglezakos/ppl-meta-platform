"""
API v1 Router - Main API Gateway Router
"""
from fastapi import APIRouter

api_router = APIRouter()

@api_router.get("/status")
async def gateway_status():
    """Gateway status endpoint."""
    return {
        "service": "ppl-meta-gateway",
        "status": "operational",
        "version": "1.0.0"
    }
