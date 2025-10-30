"""Debug endpoint to test fetchrow directly."""
import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from database.connection import get_db_pool
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
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_signature": False})
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication token")
        return {"user_id": user_id}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


@router.get("/test-fetchrow/{session_uuid}")
async def test_fetchrow(
    session_uuid: str,
    pool=Depends(get_db_pool),
    current_user: dict = Depends(get_current_user),
):
    """Test fetchrow directly with detailed logging."""
    logger.info(f"🧪 test_fetchrow: session_uuid={session_uuid}")
    logger.info(f"🧪 Authenticated user: {current_user}")
    
    try:
        # Test 1: Check database connection
        async with pool.acquire() as conn:
            db_name = await conn.fetchval("SELECT current_database()")
            logger.info(f"🧪 Connected to database: {db_name}")
            
            # Test 2: Try fetchrow
            query = "SELECT * FROM tracking_sessions WHERE session_uuid = $1"
            logger.info(f"🧪 Executing: {query}")
            logger.info(f"🧪 With param: {session_uuid} (type={type(session_uuid)})")
            
            row = await conn.fetchrow(query, session_uuid)
            logger.info(f"🧪 Result: {row is not None}")
            
            if row:
                return {
                    "found": True,
                    "session_uuid": row.get("session_uuid"),
                    "user_id": row.get("user_id"),
                    "status": row.get("status"),
                    "created_at": str(row.get("created_at")),
                    "all_keys": list(row.keys()),
                }
            else:
                # Test 3: Try COUNT to see if session exists at all
                count = await conn.fetchval(
                    "SELECT COUNT(*) FROM tracking_sessions WHERE session_uuid = $1",
                    session_uuid
                )
                logger.info(f"🧪 COUNT query result: {count}")
                
                # Test 4: List all sessions in table
                all_sessions = await conn.fetch(
                    "SELECT session_uuid, user_id FROM tracking_sessions LIMIT 10"
                )
                logger.info(f"🧪 Total sessions in table (limit 10): {len(all_sessions)}")
                
                return {
                    "found": False,
                    "count_result": count,
                    "sample_sessions": [
                        {
                            "uuid": str(s["session_uuid"]),
                            "user_id": s["user_id"]
                        }
                        for s in all_sessions
                    ],
                }
    except Exception as e:
        logger.error(f"❌ test_fetchrow error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
