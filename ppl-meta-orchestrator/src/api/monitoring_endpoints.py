"""
Workflow summary API endpoints for unified monitoring dashboard.
Provides lightweight, cached metrics for performance optimization.
"""

import aiohttp
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from database import get_db
from fastapi import APIRouter, Depends
from services.cache_service import cache_service
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

# Import workflow models from workflow_models.py
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import workflow_models

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/monitoring", tags=["monitoring"])


@router.get("/summary")
async def get_workflow_summary(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Lightweight summary endpoint for monitoring dashboard.
    Returns aggregated metrics with 60-second cache.
    
    Performance: ~50ms vs 2-3s for individual queries.
    
    Returns:
        dict: Summary metrics for low-level and high-level workflows
    """
    cache_key = "workflow_summary"
    
    # Check cache first
    cached_data = cache_service.get(cache_key)
    if cached_data:
        logger.debug("Returning cached workflow summary")
        cached_data["from_cache"] = True
        return cached_data
    
    logger.info("Generating fresh workflow summary (cache miss)")
    
    try:
        # Low-level workflow metrics (face detection/method lifecycles)
        active_sessions_count = db.query(func.count(workflow_models.WorkflowExecution.id))\
            .filter(workflow_models.WorkflowExecution.status.in_(['queued', 'processing']))\
            .scalar() or 0
        
        completed_workflows_count = db.query(func.count(workflow_models.WorkflowExecution.id))\
            .filter(workflow_models.WorkflowExecution.status == 'completed')\
            .scalar() or 0
        
        failed_workflows_count = db.query(func.count(workflow_models.WorkflowExecution.id))\
            .filter(workflow_models.WorkflowExecution.status == 'failed')\
            .scalar() or 0
        
        # Method lifecycle metrics (last 24h)
        yesterday = datetime.utcnow() - timedelta(days=1)
        
        completed_methods_24h = db.query(func.count(workflow_models.MethodLifecycle.id))\
            .filter(
                and_(
                    workflow_models.MethodLifecycle.status == 'completed',
                    workflow_models.MethodLifecycle.completed_at >= yesterday
                )
            ).scalar() or 0
        
        failed_methods_24h = db.query(func.count(workflow_models.MethodLifecycle.id))\
            .filter(
                and_(
                    workflow_models.MethodLifecycle.status == 'failed',
                    workflow_models.MethodLifecycle.completed_at >= yesterday
                )
            ).scalar() or 0
        
        # Average processing time (last 24h)
        avg_processing_time_result = db.query(
            func.avg(
                func.extract('epoch', workflow_models.MethodLifecycle.completed_at - workflow_models.MethodLifecycle.started_at)
            )
        ).filter(
            and_(
                workflow_models.MethodLifecycle.status == 'completed',
                workflow_models.MethodLifecycle.completed_at >= yesterday,
                workflow_models.MethodLifecycle.started_at.isnot(None)
            )
        ).scalar()
        
        avg_processing_time_seconds = float(avg_processing_time_result or 0)
        
        # System health calculation
        health_status = _calculate_system_health(db)

        # MVR metrics from vmeta service
        vmeta_stats = await _fetch_vmeta_mvr_stats(datetime.utcnow())
        high_level = _build_mvr_summary(vmeta_stats)
        
        # Build summary response
        summary = {
            "timestamp": datetime.utcnow().isoformat(),
            "cache_ttl": 60,
            "from_cache": False,
            "low_level_workflows": {
                "active_sessions": active_sessions_count,
                "completed_workflows": completed_workflows_count,
                "failed_workflows": failed_workflows_count,
                "completed_methods_24h": completed_methods_24h,
                "failed_methods_24h": failed_methods_24h,
                "avg_processing_time_seconds": round(avg_processing_time_seconds, 2),
                "success_rate_24h": _calculate_success_rate(
                    completed_methods_24h, failed_methods_24h
                )
            },
            "high_level_workflows": high_level,
            "system_health": health_status
        }
        
        # Cache for 60 seconds
        cache_service.set(cache_key, summary, ttl=60)
        logger.info(f"Workflow summary generated and cached (active: {active_sessions_count}, completed 24h: {completed_methods_24h})")
        
        return summary
        
    except Exception as e:
        logger.error(f"Error generating workflow summary: {e}", exc_info=True)
        # Return minimal error response
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
            "low_level_workflows": {
                "active_sessions": 0,
                "completed_workflows": 0,
                "failed_workflows": 0
            },
            "high_level_workflows": {},
            "system_health": {
                "status": "error",
                "color": "red",
                "message": "Failed to calculate system health"
            }
        }


def _calculate_system_health(db: Session) -> Dict[str, Any]:
    """Calculate overall system health status."""
    try:
        # Check for stuck workflows (processing > 2 hours)
        two_hours_ago = datetime.utcnow() - timedelta(hours=2)
        stuck_workflows = db.query(func.count(workflow_models.WorkflowExecution.id))\
            .filter(
                and_(
                    workflow_models.WorkflowExecution.status.in_(['queued', 'processing']),
                    workflow_models.WorkflowExecution.created_at < two_hours_ago
                )
            ).scalar() or 0
        
        # Check recent failures (last hour)
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        recent_failures = db.query(func.count(workflow_models.WorkflowExecution.id))\
            .filter(
                and_(
                    workflow_models.WorkflowExecution.status == 'failed',
                    workflow_models.WorkflowExecution.completed_at >= one_hour_ago
                )
            ).scalar() or 0
        
        # Determine health status
        if stuck_workflows > 5 or recent_failures > 10:
            status = "unhealthy"
            color = "red"
            message = f"Critical: {stuck_workflows} stuck workflows, {recent_failures} recent failures"
        elif stuck_workflows > 0 or recent_failures > 3:
            status = "degraded"
            color = "orange"
            message = f"Warning: {stuck_workflows} stuck workflows, {recent_failures} recent failures"
        else:
            status = "healthy"
            color = "green"
            message = "All systems operational"
        
        return {
            "status": status,
            "color": color,
            "message": message,
            "stuck_workflows": stuck_workflows,
            "recent_failures": recent_failures,
            "checked_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error calculating system health: {e}")
        return {
            "status": "error",
            "color": "red",
            "message": f"Health check error: {str(e)}",
            "stuck_workflows": 0,
            "recent_failures": 0
        }


def _calculate_success_rate(completed: int, failed: int) -> float:
    """Calculate success rate percentage."""
    total = completed + failed
    if total == 0:
        return 100.0  # No failures = 100% success
    return round((completed / total) * 100, 2)


VMETA_BASE_URL = os.getenv("VMETA_SERVICE_URL", "http://localhost:8008")


async def _fetch_vmeta_mvr_stats(now: datetime, days: int = 7) -> Dict[str, Any]:
    """
    Fetch daily MVR activity from the vmeta service.
    Returns the full stats dict; falls back to empty data on failure.
    """
    empty = {
        "total_active_mvr_people": 0,
        "mvr_created_per_day": [],
        "merges_per_day": [],
        "mappings_per_day": [],
    }
    try:
        timeout = aiohttp.ClientTimeout(total=5)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(
                f"{VMETA_BASE_URL}/api/v1/mvr-people/stats/daily",
                params={"days": days},
            ) as resp:
                if resp.status != 200:
                    logger.warning(f"vmeta stats returned {resp.status}, using fallback")
                    return empty
                return await resp.json()
    except Exception as e:
        logger.warning(f"Failed to fetch vmeta MVR stats: {e}")
        return empty


def _build_mvr_match_trend(vmeta_stats: Dict[str, Any], now: datetime, days: int = 7) -> list:
    """Build the MVR match trend chart data from vmeta stats."""
    created_map = {r["date"]: r["count"] for r in vmeta_stats.get("mvr_created_per_day", [])}
    merges_map = {r["date"]: r["count"] for r in vmeta_stats.get("merges_per_day", [])}
    mappings_map = {r["date"]: r["count"] for r in vmeta_stats.get("mappings_per_day", [])}

    result = []
    for i in range(days - 1, -1, -1):
        day_str = (now - timedelta(days=i)).strftime('%Y-%m-%d')
        result.append({
            "date": day_str,
            "matches": merges_map.get(day_str, 0) + mappings_map.get(day_str, 0),
            "mvr_created": created_map.get(day_str, 0),
            "merges": merges_map.get(day_str, 0),
            "mappings": mappings_map.get(day_str, 0),
        })
    return result


def _build_mvr_summary(vmeta_stats: Dict[str, Any]) -> Dict[str, Any]:
    """Build the high-level workflows summary from vmeta stats."""
    total_active = vmeta_stats.get("total_active_mvr_people", 0)
    today_str = datetime.utcnow().strftime('%Y-%m-%d')

    created_map = {r["date"]: r["count"] for r in vmeta_stats.get("mvr_created_per_day", [])}
    merges_map = {r["date"]: r["count"] for r in vmeta_stats.get("merges_per_day", [])}
    mappings_map = {r["date"]: r["count"] for r in vmeta_stats.get("mappings_per_day", [])}

    # Sum all activity across the fetched window
    total_merges = sum(r["count"] for r in vmeta_stats.get("merges_per_day", []))
    total_mappings = sum(r["count"] for r in vmeta_stats.get("mappings_per_day", []))
    matches_today = merges_map.get(today_str, 0) + mappings_map.get(today_str, 0)
    created_today = created_map.get(today_str, 0)

    return {
        "active_mvr_sessions": 0,  # no active session concept yet
        "total_individuals": total_active,
        "person_objects_today": created_today,
        "cross_video_matches_today": matches_today,
        "total_merges": total_merges,
        "total_mappings": total_mappings,
    }


@router.get("/charts")
async def get_monitoring_charts(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Time-series chart data for the monitoring dashboard.
    Returns hourly/daily buckets for graphs with 60-second cache.
    """
    cache_key = "monitoring_charts"
    cached = cache_service.get(cache_key)
    if cached:
        cached["from_cache"] = True
        return cached

    logger.info("Generating monitoring chart data (cache miss)")

    try:
        now = datetime.utcnow()
        yesterday = now - timedelta(days=1)
        seven_days_ago = now - timedelta(days=7)

        # --- Detection throughput (hourly, last 24h) ---
        throughput_rows = (
            db.query(
                func.date_trunc('hour', workflow_models.MethodLifecycle.completed_at).label('hour'),
                func.count(workflow_models.MethodLifecycle.id).label('count'),
            )
            .filter(
                workflow_models.MethodLifecycle.status == 'completed',
                workflow_models.MethodLifecycle.completed_at >= yesterday,
            )
            .group_by('hour')
            .order_by('hour')
            .all()
        )
        detection_throughput = [
            {"timestamp": row.hour.isoformat() if row.hour else None, "value": row.count}
            for row in throughput_rows
        ]

        # --- Success rate trend (daily, last 7 days) ---
        daily_outcomes = (
            db.query(
                func.date_trunc('day', workflow_models.MethodLifecycle.completed_at).label('day'),
                workflow_models.MethodLifecycle.status,
                func.count(workflow_models.MethodLifecycle.id).label('count'),
            )
            .filter(
                workflow_models.MethodLifecycle.status.in_(['completed', 'failed']),
                workflow_models.MethodLifecycle.completed_at >= seven_days_ago,
            )
            .group_by('day', workflow_models.MethodLifecycle.status)
            .order_by('day')
            .all()
        )
        # Aggregate into {day: {completed, failed, rate}}
        day_map: Dict[str, Dict[str, int]] = {}
        for row in daily_outcomes:
            key = row.day.strftime('%Y-%m-%d') if row.day else 'unknown'
            if key not in day_map:
                day_map[key] = {"completed": 0, "failed": 0}
            day_map[key][row.status] = row.count

        success_rate_trend = []
        for day_str in sorted(day_map.keys()):
            c = day_map[day_str]["completed"]
            f = day_map[day_str]["failed"]
            total = c + f
            rate = round((c / total) * 100, 1) if total > 0 else 100.0
            success_rate_trend.append({"date": day_str, "rate": rate, "completed": c, "failed": f})

        # --- Active sessions over time (hourly, last 24h) ---
        # Approximate by counting workflows created per hour that were active
        active_rows = (
            db.query(
                func.date_trunc('hour', workflow_models.WorkflowExecution.created_at).label('hour'),
                func.count(workflow_models.WorkflowExecution.id).label('count'),
            )
            .filter(
                workflow_models.WorkflowExecution.created_at >= yesterday,
            )
            .group_by('hour')
            .order_by('hour')
            .all()
        )
        active_sessions_trend = [
            {"timestamp": row.hour.isoformat() if row.hour else None, "value": row.count}
            for row in active_rows
        ]

        # --- Processing time distribution (buckets) ---
        processing_times_raw = (
            db.query(
                func.extract(
                    'epoch',
                    workflow_models.MethodLifecycle.completed_at - workflow_models.MethodLifecycle.started_at,
                ).label('seconds')
            )
            .filter(
                workflow_models.MethodLifecycle.status == 'completed',
                workflow_models.MethodLifecycle.completed_at >= yesterday,
                workflow_models.MethodLifecycle.started_at.isnot(None),
            )
            .all()
        )
        # Bucket into: <1s, 1-5s, 5-15s, 15-30s, 30-60s, >60s
        buckets = {"<1s": 0, "1-5s": 0, "5-15s": 0, "15-30s": 0, "30-60s": 0, ">60s": 0}
        for row in processing_times_raw:
            s = float(row.seconds) if row.seconds else 0
            if s < 1:
                buckets["<1s"] += 1
            elif s < 5:
                buckets["1-5s"] += 1
            elif s < 15:
                buckets["5-15s"] += 1
            elif s < 30:
                buckets["15-30s"] += 1
            elif s < 60:
                buckets["30-60s"] += 1
            else:
                buckets[">60s"] += 1
        processing_time_distribution = [
            {"bucket": k, "count": v} for k, v in buckets.items()
        ]

        # --- MVR matches (daily, last 7 days) — from vmeta service ---
        vmeta_stats = await _fetch_vmeta_mvr_stats(now)
        mvr_match_trend = _build_mvr_match_trend(vmeta_stats, now)

        result = {
            "timestamp": now.isoformat(),
            "from_cache": False,
            "cache_ttl": 60,
            "detection_throughput": detection_throughput,
            "success_rate_trend": success_rate_trend,
            "active_sessions_trend": active_sessions_trend,
            "processing_time_distribution": processing_time_distribution,
            "mvr_match_trend": mvr_match_trend,
        }

        cache_service.set(cache_key, result, ttl=60)
        return result

    except Exception as e:
        logger.error(f"Error generating chart data: {e}", exc_info=True)
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
            "detection_throughput": [],
            "success_rate_trend": [],
            "active_sessions_trend": [],
            "processing_time_distribution": [],
            "mvr_match_trend": [],
        }


@router.get("/workflows/low-level")
async def get_low_level_workflows(
    page: int = 1,
    limit: int = 20,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Paginated list of low-level workflows (workflow_models.WorkflowExecution).
    
    Args:
        page: Page number (1-indexed)
        limit: Items per page (max 100)
        status: Filter by status (queued, processing, completed, failed)
        
    Returns:
        dict: Paginated workflow list with metadata
    """
    try:
        # Limit max page size
        limit = min(limit, 100)
        offset = (page - 1) * limit
        
        # Build query
        query = db.query(workflow_models.WorkflowExecution)
        
        if status:
            query = query.filter(workflow_models.WorkflowExecution.status == status)
        
        # Get total count
        total = query.count()
        
        # Get paginated results
        workflows = query.order_by(workflow_models.WorkflowExecution.created_at.desc())\
            .offset(offset)\
            .limit(limit)\
            .all()
        
        return {
            "workflows": [_serialize_workflow(w) for w in workflows],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit if total > 0 else 0
            }
        }
        
    except Exception as e:
        logger.error(f"Error fetching low-level workflows: {e}", exc_info=True)
        raise


@router.get("/workflows/methods")
async def get_method_lifecycles(
    page: int = 1,
    limit: int = 20,
    status: Optional[str] = None,
    method: Optional[str] = None,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Paginated list of method lifecycles.
    
    Args:
        page: Page number (1-indexed)
        limit: Items per page (max 100)
        status: Filter by status
        method: Filter by method name (mtcnn, opencv, etc.)
        
    Returns:
        dict: Paginated method lifecycle list
    """
    try:
        limit = min(limit, 100)
        offset = (page - 1) * limit
        
        query = db.query(workflow_models.MethodLifecycle)
        
        if status:
            query = query.filter(workflow_models.MethodLifecycle.status == status)
        if method:
            query = query.filter(workflow_models.MethodLifecycle.method == method)
        
        total = query.count()
        
        methods = query.order_by(workflow_models.MethodLifecycle.started_at.desc())\
            .offset(offset)\
            .limit(limit)\
            .all()
        
        return {
            "methods": [_serialize_method_lifecycle(m) for m in methods],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit if total > 0 else 0
            }
        }
        
    except Exception as e:
        logger.error(f"Error fetching method lifecycles: {e}", exc_info=True)
        raise


@router.post("/cache/clear")
async def clear_workflow_cache() -> Dict[str, Any]:
    """
    Manually clear workflow summary cache.
    Useful for forcing refresh after system changes.
    """
    try:
        cache_service.clear_pattern("workflow_*")
        return {
            "status": "success",
            "message": "Workflow cache cleared",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


def _serialize_workflow(workflow: workflow_models.WorkflowExecution) -> Dict[str, Any]:
    """Serialize workflow_models.WorkflowExecution to dict."""
    return {
        "id": workflow.id,
        "workflow_id": workflow.workflow_id,
        "workflow_type": workflow.workflow_type,
        "status": workflow.status,
        "user_id": workflow.user_id,
        "created_at": workflow.created_at.isoformat() if workflow.created_at else None,
        "started_at": workflow.started_at.isoformat() if workflow.started_at else None,
        "completed_at": workflow.completed_at.isoformat() if workflow.completed_at else None,
        "total_media_count": workflow.total_media_count,
        "processed_media_count": workflow.processed_media_count,
        "failed_media_count": workflow.failed_media_count,
        "error_message": workflow.error_message
    }


def _serialize_method_lifecycle(method: workflow_models.MethodLifecycle) -> Dict[str, Any]:
    """Serialize workflow_models.MethodLifecycle to dict."""
    processing_time = None
    if method.started_at and method.completed_at:
        delta = method.completed_at - method.started_at
        processing_time = delta.total_seconds()
    
    return {
        "id": method.id,
        "lifecycle_id": method.lifecycle_id,
        "workflow_id": method.workflow_id,
        "method": method.method,
        "media_id": method.media_id,
        "status": method.status,
        "started_at": method.started_at.isoformat() if method.started_at else None,
        "completed_at": method.completed_at.isoformat() if method.completed_at else None,
        "processing_time_seconds": round(processing_time, 2) if processing_time else None,
        "results_count": method.results_count,
        "error_message": method.error_message
    }
