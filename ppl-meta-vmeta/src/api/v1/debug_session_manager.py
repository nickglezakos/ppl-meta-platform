"""Debug endpoint to test SessionManager the same way as cross-video endpoint."""
import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from database.connection import get_db_pool
from services.integrated_caching import IntegratedCachingService
import jwt

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/debug", tags=["debug"])

# JWT configuration
SECRET_KEY = "your-secret-key-here"
ALGORITHM = "HS256"
security = HTTPBearer()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Decode JWT token and extract user info."""
    try:
        token = credentials.credentials
        payload = jwt.decode(
            token, 
            SECRET_KEY, 
            algorithms=[ALGORITHM], 
            options={"verify_signature": False}
        )
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=401, 
                detail="Invalid authentication token"
            )
        return {"user_id": user_id}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


@router.get("/test-session-manager/{session_uuid}")
async def test_session_manager(
    session_uuid: str,
    db_pool=Depends(get_db_pool),
    current_user: dict = Depends(get_current_user),
):
    """
    Test session retrieval using EXACT same pattern as cross-video endpoint.
    
    This creates IntegratedCachingService and calls session_manager.get_session_status
    exactly like the real endpoint does.
    """
    logger.info(f"🧪 test_session_manager: session_uuid={session_uuid}")
    logger.info(f"🧪 Authenticated user: {current_user}")
    logger.info(f"🧪 db_pool type: {type(db_pool)}")
    
    try:
        # EXACT same pattern as cross-video endpoint
        caching_service = IntegratedCachingService(db_pool)
        logger.info("🧪 Created IntegratedCachingService")
        
        # Call get_session_status just like the real endpoint
        status = await caching_service.session_manager.get_session_status(
            session_uuid
        )
        logger.info(f"🧪 get_session_status returned: {status}")
        
        return {
            "test": "Using IntegratedCachingService + SessionManager",
            "session_uuid": session_uuid,
            "user_id": current_user.get("user_id"),
            "status_result": status,
        }
    except Exception as e:
        logger.error(f"❌ test_session_manager error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
