"""
vmeta Service Health API
Provides health check and service status endpoints.
"""

import time
from typing import Any, Dict
from datetime import datetime

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Enhanced service health check endpoint with MVR-People system status.

    Returns:
        Dict containing service health status including MVR-People components
    """
    start_time = time.time()
    
    # Base health response
    response = {
        "status": "healthy",
        "service": "vmeta",
        "version": "1.0.0",
        "description": "Vector-based facial embeddings and analytics",
        "timestamp": datetime.utcnow().isoformat(),
    }
    
    # Try to get MVR-People system status
    try:
        import main
        
        mvr_status = {
            "mvr_people_available": False,
            "database": {"connected": False},
            "ml_models": {"total_loaded": 0},
            "statistics": {}
        }
        
        # Check if MVR services are initialized
        if hasattr(main, 'mvr_repository') and main.mvr_repository is not None:
            mvr_status["mvr_people_available"] = True
            
            # Database health
            try:
                total_mvr = await main.mvr_repository.pool.fetchval(
                    "SELECT COUNT(*) FROM mvr_people"
                )
                active_mvr = await main.mvr_repository.pool.fetchval(
                    "SELECT COUNT(*) FROM mvr_people WHERE is_orphaned = FALSE"
                )
                orphaned_mvr = await main.mvr_repository.pool.fetchval(
                    "SELECT COUNT(*) FROM mvr_people WHERE is_orphaned = TRUE"
                )
                individuals_with_mvr = await main.mvr_repository.pool.fetchval(
                    "SELECT COUNT(*) FROM individual_mvr_mapping"
                )
                
                pool_size = main.mvr_repository.pool.get_size()
                idle = main.mvr_repository.pool.get_idle_size()
                
                mvr_status["database"] = {
                    "connected": True,
                    "pool_size": pool_size,
                    "idle_connections": idle,
                }
                
                mvr_status["statistics"] = {
                    "total_mvr_people": total_mvr or 0,
                    "active_mvr_people": active_mvr or 0,
                    "orphaned_mvr_people": orphaned_mvr or 0,
                    "individuals_with_mvr": individuals_with_mvr or 0,
                }
                
            except Exception as db_error:
                mvr_status["database"]["error"] = str(db_error)
            
            # ML Models health
            try:
                if hasattr(main, 'mvr_service') and main.mvr_service is not None:
                    ml_processor = main.mvr_service.ml_processor
                    models_loaded = 0
                    
                    if hasattr(ml_processor, 'face_model') and ml_processor.face_model is not None:
                        models_loaded += 1
                    if hasattr(ml_processor, 'age_model') and ml_processor.age_model is not None:
                        models_loaded += 1
                    if hasattr(ml_processor, 'gender_model') and ml_processor.gender_model is not None:
                        models_loaded += 1
                    
                    mvr_status["ml_models"] = {
                        "total_loaded": models_loaded,
                        "total_expected": 3
                    }
            except Exception as ml_error:
                mvr_status["ml_models"]["error"] = str(ml_error)
        
        response["mvr_people"] = mvr_status
        
    except Exception as e:
        response["mvr_people"] = {
            "mvr_people_available": False,
            "error": f"MVR-People system not initialized: {str(e)}"
        }
    
    # Add response time
    response["response_time_ms"] = round((time.time() - start_time) * 1000, 2)
    
    return response


@router.get("/metrics")
async def service_metrics() -> Dict[str, Any]:
    """
    Service metrics endpoint.

    Returns:
        Dict containing service performance metrics
    """
    return {
        "metrics": {
            "active_sessions": 0,
            "total_embeddings_generated": 0,
            "vector_searches_performed": 0,
            "uptime_seconds": 0,
        },
        "status": "operational",
    }
