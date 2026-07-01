"""Matrix Group-Level Aggregated Reporting API.

Phase 4: Provides aggregated cross-installation reports with caching.
Six report types: summary, presence, gate-activity, camera-events,
demographics, logs.

Each endpoint queries all member installations in parallel,
aggregates results via AggregationService, and caches with 60s TTL.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from services.aggregation_service import aggregation_service
from services.matrix_service import matrix_service

logger = logging.getLogger(__name__)
router = APIRouter(tags=["matrix-reports"])


def _get_member_installations(group_id: str) -> list[dict]:
    """Get all member installations for a Matrix group."""
    memberships = matrix_service.list_installations(group_id)
    if not memberships:
        raise HTTPException(status_code=404, detail="Group not found or has no installations")

    return [
        {
            "installation_uuid": m.installation_uuid,
            "installation_name": m.installation_name or m.installation_uuid,
            "node_url": m.node_url,
        }
        for m in memberships
    ]


@router.get("/groups/{group_id}/reports/summary")
async def report_summary(
    group_id: str,
    from_time: Optional[str] = Query(None, alias="from", description="ISO-8601 start timestamp"),
    to_time: Optional[str] = Query(None, alias="to", description="ISO-8601 end timestamp"),
):
    """Aggregated dashboard summary across all member installations."""
    installations = _get_member_installations(group_id)
    return await aggregation_service.get_report(
        matrix_group_id=group_id,
        report_type="summary",
        member_installations=installations,
        from_time=from_time,
        to_time=to_time,
    )


@router.get("/groups/{group_id}/reports/presence")
async def report_presence(
    group_id: str,
    from_time: Optional[str] = Query(None, alias="from"),
    to_time: Optional[str] = Query(None, alias="to"),
):
    """Aggregated presence analytics across all member installations."""
    installations = _get_member_installations(group_id)
    return await aggregation_service.get_report(
        matrix_group_id=group_id,
        report_type="presence",
        member_installations=installations,
        from_time=from_time,
        to_time=to_time,
    )


@router.get("/groups/{group_id}/reports/gate-activity")
async def report_gate_activity(
    group_id: str,
    from_time: Optional[str] = Query(None, alias="from"),
    to_time: Optional[str] = Query(None, alias="to"),
):
    """Aggregated gate activity / crowd metrics across all member installations."""
    installations = _get_member_installations(group_id)
    return await aggregation_service.get_report(
        matrix_group_id=group_id,
        report_type="gate-activity",
        member_installations=installations,
        from_time=from_time,
        to_time=to_time,
    )


@router.get("/groups/{group_id}/reports/camera-events")
async def report_camera_events(
    group_id: str,
    from_time: Optional[str] = Query(None, alias="from"),
    to_time: Optional[str] = Query(None, alias="to"),
):
    """Aggregated camera event summaries across all member installations."""
    installations = _get_member_installations(group_id)
    return await aggregation_service.get_report(
        matrix_group_id=group_id,
        report_type="camera-events",
        member_installations=installations,
        from_time=from_time,
        to_time=to_time,
    )


@router.get("/groups/{group_id}/reports/demographics")
async def report_demographics(
    group_id: str,
    from_time: Optional[str] = Query(None, alias="from"),
    to_time: Optional[str] = Query(None, alias="to"),
):
    """Aggregated demographic data across all member installations."""
    installations = _get_member_installations(group_id)
    return await aggregation_service.get_report(
        matrix_group_id=group_id,
        report_type="demographics",
        member_installations=installations,
        from_time=from_time,
        to_time=to_time,
    )


@router.get("/groups/{group_id}/reports/logs")
async def report_logs(
    group_id: str,
    from_time: Optional[str] = Query(None, alias="from"),
    to_time: Optional[str] = Query(None, alias="to"),
    level: Optional[str] = Query(None, description="Log level: info, warning, error"),
    installation_uuid: Optional[str] = Query(None, description="Filter to a single installation"),
):
    """Aggregated log reports across all member installations."""
    installations = _get_member_installations(group_id)
    return await aggregation_service.get_report(
        matrix_group_id=group_id,
        report_type="logs",
        member_installations=installations,
        from_time=from_time,
        to_time=to_time,
        level=level,
        installation_uuid=installation_uuid,
    )