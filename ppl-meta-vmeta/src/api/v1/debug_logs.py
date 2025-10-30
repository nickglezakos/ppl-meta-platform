"""Debug endpoint to capture and return logs."""
import logging
import io
from fastapi import APIRouter, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from database.connection import get_db_pool
from services.integrated_caching import IntegratedCachingService
import jwt

router = APIRouter(prefix="/api/v1/debug", tags=["debug"])

# JWT configuration
SECRET_KEY = "your-secret-key-here"
ALGORITHM = "HS256"
security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """Decode JWT token and extract user info."""
    token = credentials.credentials
    payload = jwt.decode(
        token,
        SECRET_KEY,
        algorithms=[ALGORITHM],
        options={"verify_signature": False}
    )
    user_id = payload.get("sub")
    return {"user_id": user_id}


@router.get("/test-with-logs/{session_uuid}")
async def test_with_logs(
    session_uuid: str,
    db_pool=Depends(get_db_pool),
    current_user: dict = Depends(get_current_user),
):
    """Test session retrieval and capture all logs."""
    # Create string buffer to capture logs
    log_capture = io.StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    
    # Add handler to relevant loggers
    loggers_to_capture = [
        logging.getLogger('database.connection'),
        logging.getLogger('services.session_manager'),
        logging.getLogger('services.integrated_caching'),
    ]
    
    for logger in loggers_to_capture:
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    
    try:
        # Test 1: Direct pool query
        async with db_pool.acquire() as conn:
            db_name = await conn.fetchval("SELECT current_database()")
            direct_result = await conn.fetchrow(
                "SELECT session_uuid, user_id FROM tracking_sessions WHERE session_uuid = $1",
                session_uuid
            )
        
        # Test 2: Via IntegratedCachingService
        caching_service = IntegratedCachingService(db_pool)
        status = await caching_service.session_manager.get_session_status(
            session_uuid
        )
        
        # Get captured logs
        log_output = log_capture.getvalue()
        
        return {
            "database": db_name,
            "direct_query_found": direct_result is not None,
            "session_manager_status": status,
            "captured_logs": log_output.split('\n'),
        }
    finally:
        # Remove handlers
        for logger in loggers_to_capture:
            logger.removeHandler(handler)
