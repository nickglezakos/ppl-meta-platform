"""
Core business logic service.
"""
from sqlalchemy.orm import Session
from src.database import get_db
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class CoreService:
    """Core business logic service."""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def get_service_info(self) -> Dict[str, Any]:
        """Get service information."""
        return {
            "service": "ppl-meta-media",
            "version": "1.0.0",
            "description": "Headless FastAPI microservice",
            "status": "operational"
        }
