"""
MVR-People API Dependencies

FastAPI dependencies for authentication, database connections, and service injection.

Author: PPL Meta Platform
Date: October 31, 2025
Version: 1.0.0
"""

import logging
import os
from typing import Optional
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import asyncpg

# MVR Components
from database.mvr_repository import MVRRepository
from ml.mvr_processor import MVRProcessor
from services.mvr_service import MVRService
from services.mvr_matcher import MVRMatcher
from background.mvr_background_processor import MVRBackgroundProcessor

# Individual Groups
from services.individual_groups_manager import IndividualGroupsManager

# Cache
from utils.redis_client import VMetaCacheClient

# Authentication
from utils.auth import verify_jwt_token, get_user_from_token

logger = logging.getLogger(__name__)

# HTTP Bearer token scheme
security = HTTPBearer()
INTERNAL_SERVICE_TOKEN = os.getenv(
    "INTERNAL_SERVICE_TOKEN",
    "ppl-meta-internal-service-secret-key-change-in-production",
)


# ============================================================================
# Authentication Dependencies
# ============================================================================

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """
    Verify JWT token and extract user information.
    
    **Authentication Flow:**
    1. Extract Bearer token from Authorization header
    2. Verify JWT signature with Node service
    3. Extract user information from token payload
    4. Return user dict
    
    **Returns:**
        dict: User information (email, user_uuid, etc.)
        
    **Raises:**
        HTTPException: 401 if token invalid or expired
    """
    token = credentials.credentials
    
    try:
        # Verify JWT token
        is_valid = await verify_jwt_token(token)
        
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Extract user from token
        user = await get_user_from_token(token)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        logger.info(f"Authenticated user: {user.get('email')}")
        return user
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    )
) -> Optional[dict]:
    """
    Optional authentication - returns None if no token provided.
    
    **Use Case:** Endpoints that work for both authenticated and anonymous users
    
    **Returns:**
        Optional[dict]: User information or None
    """
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None


async def get_current_user_or_internal_service(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
    x_service_name: Optional[str] = Header(None, alias="X-Service-Name"),
) -> dict:
    """Allow either a normal user JWT or the shared internal service token."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    if token == INTERNAL_SERVICE_TOKEN:
        return {
            "email": f"{x_service_name or 'internal-service'}@internal",
            "user_uuid": None,
            "is_admin": True,
            "service_name": x_service_name or "unknown",
            "auth_type": "internal_service",
            "token": token,
        }

    return await get_current_user(credentials)


# ============================================================================
# Database Dependencies
# ============================================================================

async def get_db_connection() -> asyncpg.Connection:
    """
    Get database connection from pool.
    
    **Lifecycle:**
    - Connection acquired from pool
    - Yielded to endpoint
    - Automatically released back to pool after request
    
    **Returns:**
        asyncpg.Connection: Database connection
    """
    from main import db_client
    
    if not db_client or not db_client.pool:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not initialized"
        )
    
    async with db_client.pool.acquire() as conn:
        yield conn


# ============================================================================
# MVR Component Dependencies
# ============================================================================

async def get_mvr_repository() -> MVRRepository:
    """
    Get MVRRepository instance from global state.
    
    **Singleton Pattern:** Returns shared repository instance initialized in main.py
    
    **Returns:**
        MVRRepository: Repository instance
    """
    import main
    if not main.mvr_repository:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MVR-People services not initialized"
        )
    return main.mvr_repository


async def get_mvr_processor() -> MVRProcessor:
    """
    Get MVRProcessor instance (ML models) from global state.
    
    **Singleton Pattern:** Returns shared processor instance initialized in main.py
    
    **Returns:**
        MVRProcessor: ML processor instance
    """
    import main
    if not main.mvr_service or not main.mvr_service.ml_processor:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MVR ML processor not initialized"
        )
    return main.mvr_service.ml_processor


async def get_mvr_service() -> MVRService:
    """
    Get MVRService instance from global state.
    
    **Dependencies:**
    - MVRRepository
    - MVRProcessor
    - Orchestrator client
    
    **Returns:**
        MVRService: Service instance
    """
    import main
    if not main.mvr_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MVR service not initialized"
        )
    return main.mvr_service


async def get_mvr_matcher() -> MVRMatcher:
    """
    Get MVRMatcher instance from global state.
    
    **Dependencies:**
    - MVRRepository
    - MVRProcessor
    
    **Returns:**
        MVRMatcher: Matcher instance
    """
    import main
    if not main.mvr_matcher:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MVR matcher not initialized"
        )
    return main.mvr_matcher


async def get_mvr_background_processor() -> MVRBackgroundProcessor:
    """
    Get MVRBackgroundProcessor instance from global state.
    
    **Singleton Pattern:** Returns shared background processor instance
    
    **Returns:**
        MVRBackgroundProcessor: Background processor instance
    """
    import main
    if not main.mvr_background_processor:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MVR background processor not initialized"
        )
    return main.mvr_background_processor


async def get_cache_client() -> VMetaCacheClient:
    """
    Get Redis cache client instance from global state.
    
    **Graceful Degradation:** Returns client even if Redis is not connected.
    Endpoints should check client.is_connected() before use.
    
    **Returns:**
        VMetaCacheClient: Cache client instance
    """
    import main
    if not main.vmeta_cache_client:
        logger.warning("Redis cache client not initialized, caching disabled")
        # Return a new instance that will gracefully handle no connection
        return VMetaCacheClient()
    return main.vmeta_cache_client


# ============================================================================
# Permission Dependencies
# ============================================================================

async def require_admin_user(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """
    Require user to have admin permissions.
    
    **Use Case:** Endpoints that modify configuration or sensitive data
    
    **Returns:**
        dict: User information
        
    **Raises:**
        HTTPException: 403 if user is not admin
    """
    is_admin = current_user.get('is_admin', False)
    
    if not is_admin:
        logger.warning(
            f"Non-admin user {current_user.get('email')} "
            f"attempted to access admin endpoint"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin permissions required",
        )
    
    return current_user


# ============================================================================
# Rate Limiting Dependencies
# ============================================================================

class RateLimiter:
    """
    Simple rate limiter for API endpoints.
    
    **Implementation:** In-memory rate limiting (for production, use Redis)
    """
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum requests per window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = {}  # {user_id: [(timestamp, count), ...]}
    
    async def __call__(
        self,
        current_user: dict = Depends(get_current_user)
    ):
        """
        Check rate limit for user.
        
        **Raises:**
            HTTPException: 429 if rate limit exceeded
        """
        user_id = current_user.get('user_uuid')
        
        # TODO: Implement actual rate limiting logic
        # For now, just pass through
        return current_user


# Create rate limiter instances
rate_limit_100_per_minute = RateLimiter(
    max_requests=100,
    window_seconds=60
)
rate_limit_1000_per_hour = RateLimiter(
    max_requests=1000,
    window_seconds=3600
)


# ============================================================================
# Individual Groups Manager
# ============================================================================

async def get_groups_manager() -> IndividualGroupsManager:
    """
    Get IndividualGroupsManager instance.
    
    Returns:
        IndividualGroupsManager: Initialized groups manager
    """
    from main import db_client
    
    if not db_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not available"
        )
    
    return IndividualGroupsManager(db_client)


# ============================================================================
# Export Dependencies
# ============================================================================

__all__ = [
    # Authentication
    "get_current_user",
    "get_optional_user",
    "require_admin_user",
    
    # Database
    "get_db_connection",
    
    # MVR Components
    "get_mvr_repository",
    "get_mvr_processor",
    "get_mvr_service",
    "get_mvr_matcher",
    "get_mvr_background_processor",
    
    # Individual Groups
    "get_groups_manager",
    
    # Rate Limiting
    "RateLimiter",
    "rate_limit_100_per_minute",
    "rate_limit_1000_per_hour",
]
