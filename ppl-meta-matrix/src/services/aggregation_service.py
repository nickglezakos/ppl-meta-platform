"""Cross-Installation Aggregated Reporting Service.

Phase 4: Queries each member installation's local reporting endpoints,
aggregates results, and caches them with a configurable TTL.

Report types:
- summary: Aggregated dashboard summary across all installations
- presence: Presence analytics (from ppl-meta-presence)
- gate-activity: Crowd metrics and heatmaps (from ppl-meta-orchestrator)
- camera-events: Camera event summaries (from ppl-meta-cameras)
- demographics: Age/gender distributions (from ppl-meta-orchestrator)
- logs: Aggregated log entries (from ppl-meta-node)
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

from models.database import MatrixReportCache, SessionLocal

logger = logging.getLogger(__name__)

# Default cache TTL: 60 seconds
DEFAULT_CACHE_TTL_SECONDS = 60

# Report endpoints per installation service
REPORT_ENDPOINTS = {
    "presence": "/api/v1/presence/analytics/summary",
    "gate-activity": "/api/v1/workflows/analytics",
    "camera-events": "/api/v1/cameras/events/stats",
    "demographics": "/api/v2/analytics/demographics",
    "logs": "/api/v1/logs",
    "summary": None,  # Aggregated in-memory from other endpoints
}


class AggregationService:
    """Aggregates reports across member installations in a Matrix group."""

    def __init__(self, cache_ttl: int = DEFAULT_CACHE_TTL_SECONDS):
        self.cache_ttl = cache_ttl

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_report(
        self,
        matrix_group_id: str,
        report_type: str,
        member_installations: list[dict],
        from_time: Optional[str] = None,
        to_time: Optional[str] = None,
        level: Optional[str] = None,
        installation_uuid: Optional[str] = None,
    ) -> dict:
        """Get an aggregated report for a Matrix group.

        Checks cache first; on cache miss, queries all member installations
        in parallel, aggregates results, caches, and returns.

        Args:
            matrix_group_id: UUID of the Matrix group.
            report_type: One of "summary", "presence", "gate-activity",
                         "camera-events", "demographics", "logs".
            member_installations: List of {"installation_uuid", "node_url"} dicts.
            from_time: Optional ISO-8601 start timestamp.
            to_time: Optional ISO-8601 end timestamp.
            level: Optional log level filter (for logs report).
            installation_uuid: Optional installation filter (for logs report).

        Returns:
            Aggregated report dict with `data`, `degraded` flag, and metadata.
        """
        # Try cache first
        query_params = json.dumps({
            "from": from_time, "to": to_time,
            "level": level, "installation_uuid": installation_uuid,
        })
        cached = self._get_cached(matrix_group_id, report_type, query_params)
        if cached:
            logger.debug("Returning cached %s report for group %s", report_type, matrix_group_id)
            return json.loads(cached)

        # Special case: summary is built from other endpoints
        if report_type == "summary":
            result = await self._aggregate_summary(member_installations, from_time, to_time)
        else:
            result = await self._aggregate_report(
                report_type, member_installations, from_time, to_time, level, installation_uuid
            )

        # Cache the result
        self._cache_result(matrix_group_id, report_type, query_params, result)

        return result

    # ------------------------------------------------------------------
    # Aggregation logic
    # ------------------------------------------------------------------

    async def _aggregate_summary(
        self, installations: list[dict], from_time: str, to_time: str
    ) -> dict:
        """Build an aggregated summary from presence + camera-events."""
        presence_data = await self._aggregate_report("presence", installations, from_time, to_time)
        camera_data = await self._aggregate_report("camera-events", installations, from_time, to_time)

        total_presence = sum(
            inst.get("total", 0) for inst in presence_data.get("installations", [])
        )
        total_camera_events = sum(
            inst.get("count", 0) for inst in camera_data.get("installations", [])
        )

        degraded = presence_data.get("degraded", False) or camera_data.get("degraded", False)

        return {
            "report_type": "summary",
            "installations_count": len(installations),
            "total_presence_events": total_presence,
            "total_camera_events": total_camera_events,
            "presence_details": presence_data,
            "camera_details": camera_data,
            "degraded": degraded,
            "unreachable": presence_data.get("unreachable", []) + camera_data.get("unreachable", []),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    async def _aggregate_report(
        self,
        report_type: str,
        installations: list[dict],
        from_time: str,
        to_time: str,
        level: Optional[str] = None,
        installation_uuid: Optional[str] = None,
    ) -> dict:
        """Query all member installations in parallel and aggregate results."""
        endpoint = REPORT_ENDPOINTS.get(report_type)
        if not endpoint:
            return {"error": f"Unknown report type: {report_type}", "degraded": False}

        # Filter to specific installation if requested
        if installation_uuid:
            installations = [i for i in installations if i["installation_uuid"] == installation_uuid]

        # Build query params
        params = {}
        if from_time:
            params["from"] = from_time
        if to_time:
            params["to"] = to_time
        if level and report_type == "logs":
            params["level"] = level

        # Query all installations in parallel
        results = await asyncio.gather(
            *[self._query_installation(inst, endpoint, params) for inst in installations],
            return_exceptions=True,
        )

        # Aggregate
        aggregated = []
        unreachable = []
        degraded = False

        for i, result in enumerate(results):
            inst = installations[i]
            if isinstance(result, Exception) or result is None:
                unreachable.append({
                    "installation_uuid": inst.get("installation_uuid"),
                    "installation_name": inst.get("installation_name"),
                    "error": str(result) if result else "no response",
                })
                degraded = True
            else:
                aggregated.append({
                    "installation_uuid": inst.get("installation_uuid"),
                    "installation_name": inst.get("installation_name"),
                    "data": result,
                })

        return {
            "report_type": report_type,
            "installations": aggregated,
            "unreachable": unreachable,
            "degraded": degraded,
            "total_installations": len(installations),
            "responsive_installations": len(aggregated),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    async def _query_installation(
        self, installation: dict, endpoint: str, params: dict
    ) -> Optional[dict]:
        """Query a single installation's reporting endpoint."""
        node_url = installation.get("node_url", "http://localhost:8000")
        url = f"{node_url}{endpoint}"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params=params)
                if response.status_code == 200:
                    return response.json()
                logger.warning(
                    "Installation %s returned HTTP %s for %s",
                    installation.get("installation_uuid"), response.status_code, endpoint,
                )
                return None
        except httpx.HTTPError as exc:
            logger.warning(
                "Failed to query installation %s at %s: %s",
                installation.get("installation_uuid"), url, exc,
            )
            return None
        except Exception as exc:
            logger.error("Unexpected error querying %s: %s", url, exc)
            return None

    # ------------------------------------------------------------------
    # Cache management
    # ------------------------------------------------------------------

    def _get_cached(self, matrix_group_id: str, report_type: str, query_params: str) -> Optional[str]:
        """Get a cached report result if not expired."""
        db = SessionLocal()
        try:
            entry = db.query(MatrixReportCache).filter(
                MatrixReportCache.matrix_group_id == uuid.UUID(matrix_group_id),
                MatrixReportCache.report_type == report_type,
                MatrixReportCache.query_params == query_params,
            ).first()

            if entry and entry.expires_at > datetime.now(timezone.utc):
                return entry.result_data

            # Expired — clean up
            if entry:
                db.delete(entry)
                db.commit()

            return None
        finally:
            db.close()

    def _cache_result(self, matrix_group_id: str, report_type: str, query_params: str, result: dict):
        """Cache an aggregated report result."""
        db = SessionLocal()
        try:
            # Remove old entry for same key
            db.query(MatrixReportCache).filter(
                MatrixReportCache.matrix_group_id == uuid.UUID(matrix_group_id),
                MatrixReportCache.report_type == report_type,
                MatrixReportCache.query_params == query_params,
            ).delete()

            entry = MatrixReportCache(
                matrix_group_id=uuid.UUID(matrix_group_id),
                report_type=report_type,
                query_params=query_params,
                result_data=json.dumps(result),
                expires_at=datetime.now(timezone.utc) + timedelta(seconds=self.cache_ttl),
            )
            db.add(entry)
            db.commit()
            logger.debug("Cached %s report for group %s", report_type, matrix_group_id)
        except Exception as exc:
            db.rollback()
            logger.warning("Failed to cache report: %s", exc)
        finally:
            db.close()


# Singleton
aggregation_service = AggregationService()