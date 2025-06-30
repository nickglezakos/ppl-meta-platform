"""
Health check schemas.
"""
from pydantic import BaseModel
from typing import Optional

class HealthResponse(BaseModel):
    """Basic health response model."""
    status: str
    timestamp: float
    service: str
    message: Optional[str] = None

class DetailedHealthResponse(BaseModel):
    """Detailed health response with system metrics."""
    status: str
    timestamp: float
    service: str
    database: str
    system: dict
    message: Optional[str] = None
