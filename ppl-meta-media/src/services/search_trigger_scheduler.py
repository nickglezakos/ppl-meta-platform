"""
Search Trigger Scheduler

Periodically queries vmeta camera-search for active search triggers and publishes
results to the instant-detection Redis channel for evaluation by the existing
InstantDetectionSubscriber.
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
import redis.asyncio as aioredis
from sqlalchemy.orm import Session

from src.database import SessionLocal
from src.models.trigger import Trigger
from src.services.duration_parser import parse_tracking_duration

logger = logging.getLogger(__name__)

# Age range string → standard bucket key mapping
_AGE_RANGE_BUCKET_MAP = {
    "(0-2)": "percent_age_0_12",
    "(3-9)": "percent_age_0_12",
    "(10-19)": "percent_age_13_17",  # approximate: 10-12 → 0_12, 13-17 → 13_17
    "(10-12)": "percent_age_0_12",
    "(13-17)": "percent_age_13_17",
    "(18-24)": "percent_age_18_24",
    "(20-29)": "percent_age_18_24",  # approximate
    "(25-34)": "percent_age_25_34",
    "(25-35)": "percent_age_25_34",
    "(30-39)": "percent_age_25_34",  # approximate
    "(35-44)": "percent_age_35_44",
    "(35-45)": "percent_age_35_44",
    "(40-49)": "percent_age_35_44",  # approximate
    "(45-54)": "percent_age_45_54",
    "(45-55)": "percent_age_45_54",
    "(50-59)": "percent_age_45_54",  # approximate
    "(55-64)": "percent_age_55_64",
    "(55-65)": "percent_age_55_64",
    "(60-69)": "percent_age_55_64",  # approximate
    "(65+)": "percent_age_65_plus",
    "(65-100)": "percent_age_65_plus",
    "(70+)": "percent_age_65_plus",
}

ALL_AGE_BUCKETS = [
    "percent_age_0_12",
    "percent_age_13_17",
    "percent_age_18_24",
    "percent_age_25_34",
    "percent_age_35_44",
    "percent_age_45_54",
    "percent_age_55_64",
    "percent_age_65_plus",
]


def _aggregate_demographics(matched_individuals: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate per-individual demographics into standard percentage format.

    Each individual has demographics like:
        {"gender": "Male", "age_range": "(25-35)", ...}

    Returns dict with percent_male, percent_female, and percent_age_* buckets.
    """
    total = len(matched_individuals)
    if total == 0:
        result = {"percent_male": 0.0, "percent_female": 0.0}
        for bucket in ALL_AGE_BUCKETS:
            result[bucket] = 0.0
        return result

    male_count = 0
    female_count = 0
    age_counts: Dict[str, int] = {b: 0 for b in ALL_AGE_BUCKETS}

    for individual in matched_individuals:
        demographics = individual.get("demographics") or {}
        gender = (demographics.get("gender") or "").lower()
        if gender == "male":
            male_count += 1
        elif gender == "female":
            female_count += 1

        age_range = demographics.get("age_range") or ""
        bucket = _AGE_RANGE_BUCKET_MAP.get(age_range)
        if bucket:
            age_counts[bucket] += 1

    result = {
        "percent_male": round(male_count / total * 100, 1),
        "percent_female": round(female_count / total * 100, 1),
    }
    for bucket in ALL_AGE_BUCKETS:
        result[bucket] = round(age_counts[bucket] / total * 100, 1)

    return result


class SearchTriggerScheduler:
    """Periodically executes search triggers by calling vmeta camera-search
    and publishing results to the instant-detection Redis channel."""

    def __init__(self):
        self.check_interval = int(os.getenv("SEARCH_TRIGGER_CHECK_INTERVAL", "10"))
        self.max_concurrent = int(os.getenv("SEARCH_TRIGGER_MAX_CONCURRENT", "3"))
        self.http_timeout = int(os.getenv("SEARCH_TRIGGER_TIMEOUT", "60"))
        self.vmeta_service_url = os.getenv("VMETA_SERVICE_URL", "http://localhost:8008")

        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", "6379"))
        redis_db = int(os.getenv("REDIS_DB", "0"))
        self.redis_url = f"redis://{redis_host}:{redis_port}/{redis_db}"

        # Auth token fetched lazily for vmeta calls that need it
        self._auth_token: Optional[str] = None
        self._auth_token_expiry: float = 0.0

        self.running = False
        self._task: Optional[asyncio.Task] = None
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._active_triggers: set = set()  # trigger UUIDs currently executing

    async def start(self):
        """Start the scheduler loop."""
        if self.running:
            logger.warning("SearchTriggerScheduler already running")
            return

        self.running = True
        self._semaphore = asyncio.Semaphore(self.max_concurrent)
        self._task = asyncio.create_task(self._scheduler_loop())
        logger.info(
            "SearchTriggerScheduler started (check_interval=%ds, max_concurrent=%d, timeout=%ds)",
            self.check_interval, self.max_concurrent, self.http_timeout,
        )

    async def stop(self):
        """Stop the scheduler loop."""
        self.running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        logger.info("SearchTriggerScheduler stopped")

    async def _scheduler_loop(self):
        """Main loop: check for due search triggers and dispatch them."""
        while self.running:
            try:
                await self._check_and_dispatch()
            except Exception:
                logger.exception("Error in search trigger scheduler loop")

            try:
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break

    async def _check_and_dispatch(self):
        """Query DB for due search triggers and launch executions."""
        db: Session = SessionLocal()
        try:
            triggers = db.query(Trigger).filter(
                Trigger.is_active == True,
                Trigger.trigger_mode.in_(["search", "search_demographic"]),
            ).all()

            if not triggers:
                return

            now = datetime.now(timezone.utc)

            for trigger in triggers:
                interval = trigger.search_interval_seconds or 300
                if trigger.last_fired_at:
                    next_run = trigger.last_fired_at.replace(tzinfo=timezone.utc) + \
                        __import__("datetime").timedelta(seconds=interval)
                    if now < next_run:
                        continue

                trigger_uuid_str = str(trigger.uuid)

                # Skip if already executing (overlap prevention)
                if trigger_uuid_str in self._active_triggers:
                    logger.warning(
                        "Search trigger %s still executing from previous interval, skipping",
                        trigger_uuid_str,
                    )
                    continue

                # Snapshot trigger data for the async task
                trigger_data = {
                    "uuid": trigger_uuid_str,
                    "id": trigger.id,
                    "trigger_mode": trigger.trigger_mode,
                    "search_camera_device_ids": trigger.search_camera_device_ids,
                    "tracking_duration": trigger.tracking_duration,
                    "ppl_match_group_id": trigger.ppl_match_group_id,
                    "ppl_match_similarity_threshold": trigger.ppl_match_similarity_threshold,
                    "ppl_match_top_k": trigger.ppl_match_top_k,
                    "ppl_match_negate": bool(getattr(trigger, "ppl_match_negate", False)),
                    "is_active": trigger.is_active,
                }

                asyncio.create_task(self._execute_search(trigger_data))

        except Exception:
            logger.exception("Error querying search triggers")
        finally:
            db.close()

    async def _execute_search(self, trigger_data: Dict[str, Any]):
        """Execute a single search trigger: call vmeta, transform, publish to Redis."""
        trigger_uuid = trigger_data["uuid"]
        self._active_triggers.add(trigger_uuid)

        try:
            async with self._semaphore:
                mode = trigger_data.get("trigger_mode", "search")
                if mode == "search_demographic":
                    await self._do_demographic_search(trigger_data)
                else:
                    await self._do_search(trigger_data)
        except Exception:
            logger.exception("Error executing search trigger %s", trigger_uuid)
        finally:
            self._active_triggers.discard(trigger_uuid)

    async def _get_auth_token(self) -> Optional[str]:
        """Get an auth token for inter-service calls. Cached until expiry."""
        now = time.monotonic()
        if self._auth_token and now < self._auth_token_expiry:
            return self._auth_token

        node_service_url = os.getenv("NODE_SERVICE_URL", "http://localhost:8001")
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    f"{node_service_url}/api/v1/users/login",
                    data={
                        "username": os.getenv("SERVICE_USERNAME", "fresh.user@example.com"),
                        "password": os.getenv("SERVICE_PASSWORD", "NewPassword234!"),
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                if resp.status_code == 200:
                    token = resp.json().get("access_token")
                    self._auth_token = f"Bearer {token}"
                    self._auth_token_expiry = now + 3500  # ~1 hour
                    return self._auth_token
        except Exception:
            logger.exception("Failed to obtain auth token for search scheduler")
        return None

    async def _do_demographic_search(self, trigger_data: Dict[str, Any]):
        """Core demographic search: call vmeta demographics-search, publish to Redis."""
        trigger_uuid = trigger_data["uuid"]
        start_time_perf = time.monotonic()

        camera_ids_raw = trigger_data["search_camera_device_ids"]
        if not camera_ids_raw:
            logger.warning("Demographic search trigger %s has no search_camera_device_ids, skipping", trigger_uuid)
            return

        try:
            camera_ids = json.loads(camera_ids_raw) if isinstance(camera_ids_raw, str) else camera_ids_raw
        except (json.JSONDecodeError, TypeError):
            logger.error("Demographic search trigger %s: invalid search_camera_device_ids JSON: %s", trigger_uuid, camera_ids_raw)
            return

        if not camera_ids or not isinstance(camera_ids, list):
            logger.warning("Demographic search trigger %s: empty or invalid camera_ids", trigger_uuid)
            return

        # Compute time window
        tracking_duration = parse_tracking_duration(trigger_data.get("tracking_duration") or "10 minutes")
        now = datetime.now(timezone.utc)
        window_start = now - tracking_duration

        # Verify trigger is still active
        db: Session = SessionLocal()
        try:
            trigger = db.query(Trigger).filter(
                Trigger.uuid == trigger_uuid,
                Trigger.is_active == True,
                Trigger.trigger_mode == "search_demographic",
            ).first()
            if not trigger:
                logger.info("Demographic search trigger %s no longer active or deleted, skipping", trigger_uuid)
                return
        finally:
            db.close()

        # Get auth token for the vmeta call (it needs it to call media service)
        auth_token = await self._get_auth_token()

        # Call vmeta demographics-search
        endpoint = f"{self.vmeta_service_url}/api/v1/analytics/cameras/demographics-search"
        payload = {
            "camera_ids": camera_ids,
            "start_time": window_start.isoformat(),
            "end_time": now.isoformat(),
        }

        headers: Dict[str, str] = {}
        if auth_token:
            headers["Authorization"] = auth_token

        logger.info(
            "Demographic search trigger %s: calling vmeta cameras=%s window=[%s, %s]",
            trigger_uuid, camera_ids, window_start.isoformat(), now.isoformat(),
        )

        try:
            async with httpx.AsyncClient(timeout=self.http_timeout) as client:
                response = await client.post(endpoint, json=payload, headers=headers)

            if response.status_code != 200:
                logger.error(
                    "Demographic search trigger %s: vmeta returned %d: %s",
                    trigger_uuid, response.status_code, response.text[:500],
                )
                return

            search_result = response.json()
        except httpx.TimeoutException:
            logger.error("Demographic search trigger %s: vmeta timed out after %ds", trigger_uuid, self.http_timeout)
            return
        except httpx.RequestError as e:
            logger.error("Demographic search trigger %s: vmeta request error: %s", trigger_uuid, e)
            return

        people_count = search_result.get("people_count", 0)
        demographics = search_result.get("demographics", {})
        processing_time = round(time.monotonic() - start_time_perf, 2)

        event = {
            "camera_id": f"search:{trigger_uuid}",
            "timestamp": now.isoformat(),
            "people_count": people_count,
            "demographics": demographics,
            "source_mvr_uuids": [],
            "source": "search_trigger",
            "metadata": {
                "trigger_uuid": trigger_uuid,
                "trigger_mode": "search_demographic",
                "search_cameras": camera_ids,
                "tracking_duration": trigger_data.get("tracking_duration", "10 minutes"),
                "time_range": [window_start.isoformat(), now.isoformat()],
                "search_session_uuid": search_result.get("search_session_uuid"),
                "processing_time": processing_time,
            },
        }

        # Publish to Redis
        try:
            redis = await aioredis.from_url(self.redis_url, decode_responses=True)
            try:
                await redis.publish("instant-detection", json.dumps(event))
                logger.info(
                    "Demographic search trigger %s: published event (people_count=%d, cameras=%d, processing=%.2fs)",
                    trigger_uuid, people_count, len(camera_ids), processing_time,
                )
            finally:
                await redis.close()
        except Exception:
            logger.exception("Demographic search trigger %s: failed to publish to Redis", trigger_uuid)

    async def _do_search(self, trigger_data: Dict[str, Any]):
        """Core search logic: call vmeta camera-search, transform response, publish."""
        trigger_uuid = trigger_data["uuid"]
        start_time_perf = time.monotonic()

        # Parse camera IDs from JSON
        camera_ids_raw = trigger_data["search_camera_device_ids"]
        if not camera_ids_raw:
            logger.warning("Search trigger %s has no search_camera_device_ids, skipping", trigger_uuid)
            return

        try:
            camera_ids = json.loads(camera_ids_raw) if isinstance(camera_ids_raw, str) else camera_ids_raw
        except (json.JSONDecodeError, TypeError):
            logger.error("Search trigger %s: invalid search_camera_device_ids JSON: %s", trigger_uuid, camera_ids_raw)
            return

        if not camera_ids or not isinstance(camera_ids, list):
            logger.warning("Search trigger %s: empty or invalid camera_ids", trigger_uuid)
            return

        # Compute time window
        tracking_duration = parse_tracking_duration(trigger_data.get("tracking_duration") or "10 minutes")
        now = datetime.now(timezone.utc)
        window_start = now - tracking_duration
        group_id = trigger_data["ppl_match_group_id"]

        if not group_id:
            logger.warning("Search trigger %s: no ppl_match_group_id configured", trigger_uuid)
            return

        # Verify trigger is still active before making the HTTP call
        db: Session = SessionLocal()
        try:
            trigger = db.query(Trigger).filter(
                Trigger.uuid == trigger_uuid,
                Trigger.is_active == True,
                Trigger.trigger_mode == "search",
            ).first()
            if not trigger:
                logger.info("Search trigger %s no longer active or deleted, skipping", trigger_uuid)
                return
        finally:
            db.close()

        # Call vmeta camera-search
        endpoint = f"{self.vmeta_service_url}/api/v1/individual-groups/{group_id}/camera-search"
        payload = {
            "camera_ids": camera_ids,
            "start_time": window_start.isoformat(),
            "end_time": now.isoformat(),
            "confidence_threshold": trigger_data.get("ppl_match_similarity_threshold", 0.5),
        }

        logger.info(
            "Search trigger %s: calling vmeta camera-search group=%s cameras=%s window=[%s, %s]",
            trigger_uuid, group_id, camera_ids, window_start.isoformat(), now.isoformat(),
        )

        try:
            async with httpx.AsyncClient(timeout=self.http_timeout) as client:
                response = await client.post(endpoint, json=payload)

            if response.status_code != 200:
                logger.error(
                    "Search trigger %s: vmeta camera-search returned %d: %s",
                    trigger_uuid, response.status_code, response.text[:500],
                )
                return

            search_result = response.json()
        except httpx.TimeoutException:
            logger.error("Search trigger %s: vmeta camera-search timed out after %ds", trigger_uuid, self.http_timeout)
            return
        except httpx.RequestError as e:
            logger.error("Search trigger %s: vmeta request error: %s", trigger_uuid, e)
            return

        # Transform response to instant-detection event format
        matched_individuals = search_result.get("matched_individuals") or []
        people_count = len(matched_individuals)
        source_mvr_uuids = [
            ind.get("mvr_person_uuid")
            for ind in matched_individuals
            if ind.get("mvr_person_uuid")
        ]

        demographics = _aggregate_demographics(matched_individuals)
        processing_time = round(time.monotonic() - start_time_perf, 2)

        negate = trigger_data.get("ppl_match_negate", False)

        # Negate mode: fire only when NO members are matched; skip when matches exist
        if negate and people_count > 0:
            logger.info(
                "Search trigger %s (NOT mode): %d match(es) found — skipping publish",
                trigger_uuid, people_count,
            )
            return
        # Normal mode: fire only when at least one match found
        if not negate and people_count == 0:
            logger.info(
                "Search trigger %s: no matches found — skipping publish",
                trigger_uuid,
            )
            return

        event = {
            "camera_id": f"search:{trigger_uuid}",
            "timestamp": now.isoformat(),
            "people_count": people_count,
            "demographics": demographics,
            "source_mvr_uuids": source_mvr_uuids,
            "source": "search_trigger",
            "metadata": {
                "trigger_uuid": trigger_uuid,
                "group_id": group_id,
                "search_cameras": camera_ids,
                "tracking_duration": trigger_data.get("tracking_duration", "10 minutes"),
                "time_range": [window_start.isoformat(), now.isoformat()],
                "members_found": search_result.get("members_found", 0),
                "total_group_members": search_result.get("total_group_members", 0),
                "search_session_uuid": search_result.get("search_session_uuid"),
                "processing_time": processing_time,
                "negated": negate,
            },
        }

        # Publish to Redis instant-detection channel
        try:
            redis = await aioredis.from_url(self.redis_url, decode_responses=True)
            try:
                await redis.publish("instant-detection", json.dumps(event))
                logger.info(
                    "Search trigger %s: published event (people_count=%d, cameras=%d, processing=%.2fs)",
                    trigger_uuid, people_count, len(camera_ids), processing_time,
                )
            finally:
                await redis.close()
        except Exception:
            logger.exception("Search trigger %s: failed to publish to Redis", trigger_uuid)

    async def execute_now(self, trigger_uuid: str) -> Dict[str, Any]:
        """Execute a search trigger immediately (for the execute-now endpoint).

        Returns a summary dict with the results.
        """
        db: Session = SessionLocal()
        try:
            trigger = db.query(Trigger).filter(
                Trigger.uuid == trigger_uuid,
                Trigger.trigger_mode.in_(["search", "search_demographic"]),
            ).first()

            if not trigger:
                return {"error": "Search trigger not found", "trigger_uuid": trigger_uuid}

            trigger_data = {
                "uuid": str(trigger.uuid),
                "id": trigger.id,
                "trigger_mode": trigger.trigger_mode,
                "search_camera_device_ids": trigger.search_camera_device_ids,
                "tracking_duration": trigger.tracking_duration,
                "ppl_match_group_id": trigger.ppl_match_group_id,
                "ppl_match_similarity_threshold": trigger.ppl_match_similarity_threshold,
                "ppl_match_top_k": trigger.ppl_match_top_k,
                "ppl_match_negate": bool(getattr(trigger, "ppl_match_negate", False)),
                "is_active": trigger.is_active,
            }
        finally:
            db.close()

        if trigger_data.get("trigger_mode") == "search_demographic":
            await self._do_demographic_search(trigger_data)
        else:
            await self._do_search(trigger_data)
        return {
            "status": "executed",
            "trigger_uuid": trigger_uuid,
            "message": "Search trigger executed and results published to Redis for evaluation",
        }


# Module-level singleton
_scheduler: Optional[SearchTriggerScheduler] = None


async def start_search_scheduler():
    """Start the global search trigger scheduler."""
    global _scheduler
    if _scheduler is None:
        _scheduler = SearchTriggerScheduler()
    await _scheduler.start()


async def stop_search_scheduler():
    """Stop the global search trigger scheduler."""
    global _scheduler
    if _scheduler:
        await _scheduler.stop()


def get_search_scheduler() -> Optional[SearchTriggerScheduler]:
    """Get the global search trigger scheduler instance."""
    return _scheduler
