"""
PPL Meta vmeta Service Configuration
Vector-based facial embeddings and person detection analytics
"""

import os
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class VmetaSettings:
    """vmeta service configuration settings."""
    
    # Service identification
    SERVICE_NAME = "vmeta"
    SERVICE_VERSION = "1.0.0"
    SERVICE_TYPE = "backend"
    
    # Server configuration
    HOST = os.getenv("VMETA_HOST", "0.0.0.0")
    PORT = int(os.getenv("VMETA_PORT", "8008"))  # New dedicated port
    
    # Database configuration
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", "5432"))
    DB_NAME = os.getenv("DB_NAME", "ppl_meta")
    DB_USER = os.getenv("DB_USER", "ppl_user")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "ppl_password")
    
    # Vector processing configuration
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "Facenet512")
    DISTANCE_MULTIPLIER = float(os.getenv("DISTANCE_MULTIPLIER", "1000000.0"))
    SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.8"))

    # MVR-people merge default similarity threshold.
    # Single source of truth consumed by every MVR auto-merge code path
    # (search/by-videos, persisted-merge-session, hierarchical merge,
    #  background processor, individual_groups_manager, cross_video_tracking, ...).
    # Lowered from 0.70 -> 0.60 (see docs/proposals/people-counters.md §5.11).
    MVR_MERGE_SIMILARITY_THRESHOLD = float(
        os.getenv("MVR_MERGE_SIMILARITY_THRESHOLD", "0.60")
    )

    @classmethod
    def get_mvr_similarity_threshold(cls) -> float:
        """Return the configured default similarity threshold for MVR auto-merge.

        Endpoint Body defaults and background workers should consult this rather
        than hard-coding a literal so the value can be tuned in one place.
        """
        return cls.MVR_MERGE_SIMILARITY_THRESHOLD
    
    # Service discovery configuration
    DISCOVERY_SERVICE_URL = os.getenv("DISCOVERY_SERVICE_URL", "http://localhost:8006")
    
    # Authentication configuration (must match node service)
    SECRET_KEY = os.getenv("SECRET_KEY", "default-secret-key-change-in-production")
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))
    
    # Performance configuration  
    MAX_BATCH_SIZE = int(os.getenv("MAX_BATCH_SIZE", "32"))
    VECTOR_CACHE_SIZE = int(os.getenv("VECTOR_CACHE_SIZE", "1000"))
    
    @classmethod
    def get_database_config(cls) -> Dict[str, Any]:
        """Get database configuration dictionary."""
        return {
            "host": cls.DB_HOST,
            "port": cls.DB_PORT,
            "database": cls.DB_NAME,
            "username": cls.DB_USER,
            "password": cls.DB_PASSWORD,
        }
    
    @classmethod
    def get_service_info(cls) -> Dict[str, Any]:
        """Get service registration information."""
        return {
            "name": cls.SERVICE_NAME,
            "service_type": cls.SERVICE_TYPE,
            "version": cls.SERVICE_VERSION,
            "host": "localhost",  # Will be updated for container deployment
            "port": cls.PORT,
            "health_endpoint": "/health",
            "capabilities": [
                "facial_embeddings",
                "vector_similarity_search",
                "session_based_workflows", 
                "3d_distance_calculation",
                "person_routes_analytics"
            ]
        }

# Global settings instance
settings = VmetaSettings()
