"""Debug endpoints for troubleshooting."""
from fastapi import APIRouter, Depends
import asyncpg
from database.connection import get_database_manager, get_db_pool

router = APIRouter()


@router.get("/test-database-name")
async def test_database_name(db_pool=Depends(get_db_pool)):
    """Test which database the pool is connected to."""
    import logging
    from database.connection import DBProxy
    
    logger = logging.getLogger(__name__)
    
    try:
        db_proxy = DBProxy(db_pool)
        
        # Query the current database name
        result = await db_proxy.fetchrow("SELECT current_database()")
        db_name = result['current_database'] if result else 'unknown'
        
        # Also get some session counts
        session_count = await db_proxy.fetchval(
            "SELECT COUNT(*) FROM tracking_sessions"
        )
        
        user_7_count = await db_proxy.fetchval(
            "SELECT COUNT(*) FROM tracking_sessions WHERE user_id = '7'"
        )
        
        return {
            "database_name": db_name,
            "total_sessions": session_count,
            "user_7_sessions": user_7_count,
            "pool": str(db_pool),
            "pool_id": id(db_pool)
        }
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        return {
            "error": str(e),
            "traceback": traceback.format_exc()
        }


@router.get("/test-session-insert")
async def test_session_insert(db_pool=Depends(get_db_pool)):
    """Test direct session insertion to database."""
    import logging
    from uuid import uuid4
    from datetime import datetime
    from models.cross_video_tracking import TrackingSession, SessionStatus, CrossVideoTrackingConfig
    from services.integrated_caching import IntegratedCachingService
    from services.cache_manager import CacheManager
    from database.connection import DBProxy
    
    logger = logging.getLogger(__name__)
    logger.info(f"🧪 test_session_insert: db_pool={db_pool}, type={type(db_pool)}")
    
    try:
        # Create a simple test session
        test_session = TrackingSession(
            session_uuid=uuid4(),
            user_id="test_insert_user",
            collections=["test_collection"],
            start_time=datetime(2025, 10, 19, 13, 0, 0),
            end_time=datetime(2025, 10, 19, 14, 0, 0),
            status=SessionStatus.INITIALIZED,
            config_hash="test_hash_123",
            algorithm_config=CrossVideoTrackingConfig(),
            total_videos=0,
            cache_hits=0
        )
        
        logger.info(f"🧪 Created test session: {test_session.session_uuid}")
        
        # Create DBProxy and SessionManager
        db_proxy = DBProxy(db_pool)
        cache_manager = CacheManager(db_proxy)
        
        # Import SessionManager  
        from services.session_manager import SessionManager
        session_manager = SessionManager(db_proxy, cache_manager)
        
        logger.info(f"🧪 Calling _store_session...")
        
        # Try to store it
        await session_manager._store_session(test_session)
        
        logger.info(f"🧪 _store_session completed!")
        
        return {
            "success": True,
            "session_uuid": str(test_session.session_uuid),
            "message": "Session stored successfully"
        }
        
    except Exception as e:
        logger.error(f"🧪 Test failed: {e}")
        import traceback
        tb = traceback.format_exc()
        logger.error(f"🧪 Traceback:\n{tb}")
        return {
            "success": False,
            "error": str(e),
            "traceback": tb
        }


@router.get("/db-pool-status")
async def get_db_pool_status():
    """Get the current database pool status for debugging."""
    manager = get_database_manager()
    return {
        "manager_id": id(manager),
        "pool": str(manager.pool),
        "pool_id": id(manager.pool) if manager.pool else None,
        "pool_size": manager.pool.get_size() if manager.pool else None,
        "pool_free": manager.pool.get_idle_size() if manager.pool else None,
    }


@router.get("/test-get-db-pool")
async def test_get_db_pool_dependency(pool: asyncpg.Pool = Depends(get_db_pool)):
    """Test get_db_pool dependency injection."""
    return {
        "pool_received": str(pool),
        "pool_id": id(pool),
        "pool_size": pool.get_size() if pool else None,
        "pool_free": pool.get_idle_size() if pool else None,
    }


@router.get("/active-sessions")
async def get_active_sessions():
    """Get active tracking sessions for debugging."""
    from services.integrated_caching import IntegratedCachingService
    from database.connection import get_database_manager
    
    try:
        manager = get_database_manager()
        caching_service = IntegratedCachingService(manager.pool)
        active = caching_service.session_manager.active_sessions
        
        return {
            "active_count": len(active),
            "sessions": {
                uuid: {
                    "status": str(info['session'].status),
                    "started_at": str(info['started_at']),
                    "task": str(info.get('task')),
                    "task_done": (
                        info.get('task').done() 
                        if info.get('task') else None
                    )
                }
                for uuid, info in active.items()
            }
        }
    except Exception as exc:
        return {"error": str(exc)}


@router.get("/test-background-param/{session_uuid}")
async def test_background_execution(
    session_uuid: str,
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    """Test background execution directly."""
    from services.integrated_caching import IntegratedCachingService
    
    try:
        caching_service = IntegratedCachingService(pool)
        
        # Directly call execute_tracking_session with background=True
        result = await caching_service.session_manager.execute_tracking_session(
            session_uuid=session_uuid,
            background=True
        )
        
        # Check active_sessions
        active = caching_service.session_manager.active_sessions
        
        return {
            "result": result,
            "active_count": len(active),
            "session_in_active": session_uuid in active
        }
    except Exception as exc:
        return {"error": str(exc), "type": type(exc).__name__}
