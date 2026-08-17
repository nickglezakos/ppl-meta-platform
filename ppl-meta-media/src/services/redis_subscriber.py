"""
Redis Pub/Sub Subscriber for Trigger Evaluation
Listens to instant-detection channel and evaluates triggers in real-time
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

import httpx
import redis.asyncio as aioredis
from sqlalchemy.orm import Session

from src.database import SessionLocal
from src.models.trigger import Trigger
from src.models.trigger_execution_log import TriggerExecutionLog
from src.models.signage import SignageDevice
from src.services.signage_service import SignageService, SignagePlaybackService
from src.schemas.signage import PlaybackControlRequest, PlaybackCommand, PlaybackParameters
from src.services.communications_client import CommunicationsClient
from src.services.vprofile_match_worker import get_vprofile_worker
from src.config import get_config

logger = logging.getLogger(__name__)

AGE_COUNT_TO_PERCENT_FIELD = {
    'age_count_0_12': 'percent_age_0_12',
    'age_count_13_17': 'percent_age_13_17',
    'age_count_18_24': 'percent_age_18_24',
    'age_count_25_34': 'percent_age_25_34',
    'age_count_35_44': 'percent_age_35_44',
    'age_count_45_54': 'percent_age_45_54',
    'age_count_55_64': 'percent_age_55_64',
    'age_count_65_plus': 'percent_age_65_plus',
}

LEGACY_PERCENT_AGE_FIELDS = set(AGE_COUNT_TO_PERCENT_FIELD.values())

# Midpoint ages used for computing weighted-average age from bracket percentages
AGE_BRACKET_MIDPOINTS = {
    'percent_age_0_12': 6.0,
    'percent_age_13_17': 15.0,
    'percent_age_18_24': 21.0,
    'percent_age_25_34': 29.5,
    'percent_age_35_44': 39.5,
    'percent_age_45_54': 49.5,
    'percent_age_55_64': 59.5,
    'percent_age_65_plus': 70.0,
}

# Module-level communications client singleton
_communications_client = None


def _build_ppl_match_reason(best_match: Dict[str, Any]) -> str:
    similarity_score = best_match.get("similarity_score")
    matched_member_uuid = best_match.get("matched_member_uuid")
    existing_member_name = (best_match.get("existing_member_name") or "").strip()
    group_member_number_raw = best_match.get("group_member_number")

    group_member_number: Optional[int] = None
    if isinstance(group_member_number_raw, int):
        group_member_number = group_member_number_raw
    elif isinstance(group_member_number_raw, str) and group_member_number_raw.isdigit():
        group_member_number = int(group_member_number_raw)

    descriptor: Optional[str] = None
    if group_member_number is not None:
        descriptor = f"Group Member {group_member_number:02d}"

    if existing_member_name:
        descriptor = f"{descriptor} ({existing_member_name})" if descriptor else existing_member_name

    if not descriptor and matched_member_uuid:
        descriptor = f"member {matched_member_uuid}"

    if not descriptor:
        descriptor = "member"

    return f"Matched {descriptor} score={similarity_score}"


def _extract_ppl_match_context(match_info: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not match_info:
        return {}

    best_match = match_info.get("best_match") or {}
    match_reason = _build_ppl_match_reason(best_match)

    return {
        "match_reason": match_reason,
        "matched_member_uuid": best_match.get("matched_member_uuid") or "",
        "matched_member_name": (best_match.get("existing_member_name") or "").strip(),
        "group_member_number": best_match.get("group_member_number") or "",
        "similarity_score": best_match.get("similarity_score") if best_match.get("similarity_score") is not None else "",
    }


def _interpolate_action_message(
    base_message: str,
    trigger: Trigger,
    evaluation_reason: Optional[str],
    match_info: Optional[Dict[str, Any]],
) -> str:
    message = base_message or ""
    original_message = message

    match_context = _extract_ppl_match_context(match_info)
    replacements = {
        "trigger_name": trigger.name,
        "trigger_id": str(trigger.uuid),
        "reason": evaluation_reason or "",
        "match_reason": match_context.get("match_reason", ""),
        "matched_member_uuid": match_context.get("matched_member_uuid", ""),
        "matched_member_name": match_context.get("matched_member_name", ""),
        "group_member_number": match_context.get("group_member_number", ""),
        "similarity_score": match_context.get("similarity_score", ""),
    }

    used_template_variable = False
    for key, value in replacements.items():
        token = "{" + key + "}"
        if token in message:
            used_template_variable = True
            message = message.replace(token, str(value))

    if (
        not used_template_variable
        and match_context.get("match_reason")
        and match_info
        and (match_info.get("mode") == "ppl_match" or match_info.get("matched"))
    ):
        if message:
            message = f"{message} - {match_context['match_reason']}"
        else:
            message = match_context["match_reason"]

    if not message and original_message:
        return original_message

    return message


def get_communications_client() -> CommunicationsClient:
    """Get or create communications client singleton."""
    global _communications_client
    if _communications_client is None:
        config = get_config()
        _communications_client = CommunicationsClient(
            base_url=config.COMMUNICATIONS_SERVICE_URL
        )
    return _communications_client


class InstantDetectionSubscriber:
    """
    Subscribes to Redis instant-detection channel and evaluates triggers.
    
    This replaces the webhook-based approach with a pub/sub pattern that:
    - Doesn't block the cameras service
    - Allows multiple consumers (triggers, analytics, UI)
    - Scales better with high-frequency updates
    """
    
    def __init__(self):
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", 6379))
        redis_db = int(os.getenv("REDIS_DB", 0))
        
        self.redis_url = f"redis://{redis_host}:{redis_port}/{redis_db}"
        self.redis: aioredis.Redis = None
        self.pubsub: aioredis.client.PubSub = None
        self.running = False
        self._task = None
        
        # Message deduplication: Store processed message IDs (timestamp + camera_id)
        self._processed_messages = set()
        self._max_processed_cache = 1000
        self._current_detection_data = {}  # Store current detection data for actions  # Keep last 1000 processed messages
        self.vmeta_service_url = os.getenv("VMETA_SERVICE_URL", "http://localhost:8008")
        
    async def start(self):
        """Start subscribing to instant-detection channel"""
        if self.running:
            logger.warning("Subscriber already running")
            return
        
        try:
            # Connect to Redis
            self.redis = await aioredis.from_url(
                self.redis_url,
                decode_responses=True,
                encoding="utf-8"
            )
            
            # Create pubsub and subscribe
            self.pubsub = self.redis.pubsub()
            await self.pubsub.subscribe("instant-detection")
            
            self.running = True
            logger.info("✅ Subscribed to instant-detection Redis channel")
            
            # Start listening loop
            self._task = asyncio.create_task(self._listen_loop())
            
        except Exception as e:
            logger.error(f"❌ Failed to start Redis subscriber: {e}")
            raise
    
    async def stop(self):
        """Stop subscribing"""
        self.running = False
        
        if self._task:
            self._task.cancel()
        
        if self.pubsub:
            await self.pubsub.unsubscribe("instant-detection")
            await self.pubsub.close()
        
        if self.redis:
            await self.redis.close()
        
        logger.info("✅ Stopped instant-detection subscriber")
    
    async def _listen_loop(self):
        """Listen for messages and evaluate triggers"""
        try:
            logger.info("🎧 Listening for instant detection events...")
            
            async for message in self.pubsub.listen():
                if message["type"] == "message":
                    try:
                        # Parse message
                        data = json.loads(message["data"])
                        
                        # Create unique message ID for deduplication
                        camera_id = data.get("camera_id")
                        timestamp = data.get("timestamp")
                        message_id = f"{camera_id}:{timestamp}"
                        
                        # Skip if already processed
                        if message_id in self._processed_messages:
                            logger.debug(f"⏭️ Skipping duplicate message: {message_id}")
                            continue
                        
                        # Add to processed set
                        self._processed_messages.add(message_id)
                        
                        # Limit cache size to prevent memory growth
                        if len(self._processed_messages) > self._max_processed_cache:
                            # Remove oldest half of entries
                            to_remove = len(self._processed_messages) - (self._max_processed_cache // 2)
                            for _ in range(to_remove):
                                self._processed_messages.pop()
                        
                        # Evaluate triggers
                        await self._handle_instant_detection(data)
                        
                    except json.JSONDecodeError as e:
                        logger.error(f"❌ Invalid JSON from instant-detection: {e}")
                    except Exception as e:
                        logger.error(f"❌ Error handling instant detection: {e}", exc_info=True)
                        
        except asyncio.CancelledError:
            logger.info("🛑 Listen loop cancelled")
        except Exception as e:
            logger.error(f"❌ Listen loop error: {e}")

    def _parse_event_timestamp_utc(self, timestamp: Optional[str]) -> Optional[datetime]:
        """Parse event timestamp and normalize to timezone-aware UTC datetime."""
        if not timestamp or not isinstance(timestamp, str):
            return None

        raw_value = timestamp.strip()
        if not raw_value:
            return None

        try:
            normalized = raw_value.replace("Z", "+00:00")
            parsed = datetime.fromisoformat(normalized)
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except ValueError:
            return None
    
    async def _handle_instant_detection(self, data: Dict):
        """
        Handle instant detection event and evaluate triggers.
        
        This is the same logic as the webhook endpoint, but driven by Redis Pub/Sub.
        """
        camera_id = data.get("camera_id")
        people_count = data.get("people_count", 0)
        demographics = data.get("demographics", {})
        timestamp = data.get("timestamp")
        is_search_trigger = data.get("source") == "search_trigger"
        
        # Validate message freshness - ignore messages older than 10 seconds
        # Skip freshness check for search trigger events (they are generated on-demand)
        if not is_search_trigger:
            message_time = self._parse_event_timestamp_utc(timestamp)
            if message_time is None:
                logger.warning(f"⚠️ Could not parse timestamp '{timestamp}'")
                # Continue processing even if timestamp parsing fails
            else:
                now = datetime.now(timezone.utc)
                age_seconds = (now - message_time).total_seconds()

                if age_seconds > 10:
                    logger.warning(
                        f"⏰ Skipping stale message: {camera_id} "
                        f"(age: {age_seconds:.1f}s, threshold: 10s)"
                    )
                    return
        
        logger.info(f"\n{'='*80}")
        logger.info(f"🔔 INSTANT DETECTION EVENT (Redis Pub/Sub)")
        logger.info(f"{'='*80}")
        logger.info(f"📷 Camera ID: {camera_id}")
        logger.info(f"👥 People Count: {people_count}")
        logger.info(f"📊 Demographics: {demographics}")
        logger.info(f"⏰ Timestamp: {timestamp}")
        
        # Save original event-level source_mvr_uuids before deep extraction
        event_source_mvr_uuids = list(data.get('source_mvr_uuids', []) or [])
        
        source_mvr_uuids = self._extract_source_mvr_uuids(data)
        if not source_mvr_uuids:
            metadata_keys = []
            if isinstance(data.get("metadata"), dict):
                metadata_keys = list(data.get("metadata", {}).keys())
            logger.warning(
                "⚠️ No source IDs in instant-detection payload. data_keys=%s metadata_keys=%s",
                list(data.keys()),
                metadata_keys,
            )
        else:
            data["source_mvr_uuids"] = source_mvr_uuids

        # Store demographics data for action execution
        self._current_detection_data = {
            "people_count": people_count,
            "demographics": demographics,
            "timestamp": timestamp,
            "camera_id": camera_id,
            "source_mvr_uuids": source_mvr_uuids,
            "source": data.get("source"),
            "metadata": data.get("metadata"),
        }
        
        db: Session = SessionLocal()
        
        try:
            # Find active triggers for this camera.
            # For search triggers, camera_id is "search:<trigger_uuid>" — match by
            # camera_device_id directly (set during trigger creation) or by UUID suffix.
            if is_search_trigger and camera_id and camera_id.startswith("search:"):
                search_trigger_uuid = camera_id.split(":", 1)[1]
                triggers = db.query(Trigger).filter(
                    Trigger.is_active == True,
                    Trigger.trigger_mode.in_(["search", "search_demographic"]),
                    Trigger.uuid == search_trigger_uuid,
                ).all()
            else:
                triggers = db.query(Trigger).filter(
                    Trigger.is_active == True,
                    Trigger.camera_device_id == camera_id
                ).all()
                # Also include vprofile_match triggers (they use camera_device_ids array, not camera_device_id)
                vprofile_triggers = db.query(Trigger).filter(
                    Trigger.is_active == True,
                    Trigger.trigger_mode == 'vprofile_match'
                ).all()
                triggers = triggers + [t for t in vprofile_triggers if t not in triggers]
            
            if not triggers:
                logger.info(f"  ℹ️  No active triggers for camera {camera_id}")
                return
            
            logger.info(f"  🔍 Found {len(triggers)} active trigger(s) to evaluate")
            
            triggers_fired = 0
            fired_trigger_ids = []
            now = datetime.now(timezone.utc)
            
            # Evaluate each trigger
            for trigger in triggers:
                logger.info(f"\n--- Evaluating Trigger #{trigger.id}: '{trigger.name}' ---")
                trigger_mode = (getattr(trigger, "trigger_mode", None) or "demographic").lower()
                match_info = None
                
                # Check cooldown
                if trigger.last_fired_at:
                    cooldown_end = trigger.last_fired_at + timedelta(seconds=trigger.cooldown_seconds)
                    if now < cooldown_end:
                        remaining = (cooldown_end - now).total_seconds()
                        logger.info(f"  ⏸️  SKIP: In cooldown ({remaining:.1f}s remaining)")
                        self._log_execution(
                            db=db,
                            trigger=trigger,
                            passed=False,
                            reason=f"Cooldown active ({remaining:.1f}s remaining)",
                            match_info=None,
                            detection_data=self._current_detection_data,
                            action_executed=False,
                        )
                        continue

                if trigger_mode == "ppl_match":
                    logger.info("  🔎 Evaluating ppl_match mode")
                    passed, reason, match_info = await self._evaluate_ppl_match(trigger, data)
                    if not passed:
                        logger.info(f"  ❌ SKIP: {reason}")
                        self._log_execution(
                            db=db,
                            trigger=trigger,
                            passed=False,
                            reason=reason,
                            match_info=match_info,
                            detection_data=self._current_detection_data,
                            action_executed=False,
                        )
                        continue
                    logger.info(f"  ✅ ppl_match MET: {reason}")
                elif trigger_mode == "vprofile_match":
                    logger.info("  🔎 Evaluating vprofile_match mode (in-memory, multi-camera)")
                    worker = get_vprofile_worker()

                    # Multi-camera filter: check if this event's camera is allowed
                    event_camera_id = data.get('camera_id')
                    allowed_cameras = worker.get_camera_device_ids(trigger)
                    if allowed_cameras and event_camera_id not in allowed_cameras:
                        logger.debug("  ⏭️ Camera %s not in trigger's camera list, skipping", event_camera_id)
                        continue

                    # Ensure the trigger's group embeddings are loaded before evaluating.
                    # Lazy-loads them if the startup restore missed them (otherwise the
                    # in-memory comparison would always return 0 matches on an empty cache).
                    try:
                        groups_ready = await worker.ensure_trigger_loaded(trigger)
                    except Exception as e:
                        logger.warning("  ⚠️ Error ensuring groups loaded for trigger %s: %s", trigger.uuid, e)
                        groups_ready = False

                    if not groups_ready:
                        logger.info("  ❌ SKIP: Trigger group embeddings not available (cache not loaded)")
                        self._log_execution(
                            db=db, trigger=trigger, passed=False,
                            reason="Trigger group embeddings not available (cache not loaded)",
                            match_info=None, detection_data=self._current_detection_data,
                            action_executed=False,
                        )
                        continue

                    # Fetch source embeddings — use deep-extracted UUIDs (same as legacy ppl_match) because
                    # Redis event-level source_mvr_uuids may be empty. deep extraction finds MVR UUIDs
                    # from person_objects, metadata, and individual fields.
                    source_mvr_uuids_for_vprofile = source_mvr_uuids if source_mvr_uuids else event_source_mvr_uuids
                    logger.info("  📋 vprofile source UUIDs (deep=%d, event=%d) => using %d", 
                               len(source_mvr_uuids), len(event_source_mvr_uuids), len(source_mvr_uuids_for_vprofile))
                    source_embedding_map = await worker.fetch_source_embeddings(source_mvr_uuids_for_vprofile)

                    if not source_embedding_map:
                        logger.info("  ❌ SKIP: No source embeddings resolved")
                        self._log_execution(
                            db=db, trigger=trigger, passed=False,
                            reason="No source embeddings resolved",
                            match_info=None, detection_data=self._current_detection_data,
                            action_executed=False,
                        )
                        continue

                    passed, reason, match_info = await worker.evaluate(trigger, {**data, 'source_mvr_uuids': source_mvr_uuids_for_vprofile}, source_embedding_map)

                    if not passed:
                        logger.info(f"  ❌ SKIP: {reason}")
                        self._log_execution(
                            db=db, trigger=trigger, passed=False,
                            reason=reason, match_info=match_info,
                            detection_data=self._current_detection_data,
                            action_executed=False,
                        )
                        continue

                    logger.info(f"  ✅ vprofile_match MET: {reason}")
                else:
                    conditions = json.loads(trigger.demographic_conditions)
                    logger.info(f"  📋 Conditions to evaluate: {json.dumps(conditions, indent=4)}")

                    if not self._evaluate_conditions(conditions, demographics, people_count):
                        logger.info(f"  ❌ SKIP: Conditions NOT met")
                        self._log_execution(
                            db=db,
                            trigger=trigger,
                            passed=False,
                            reason="Demographic conditions not met",
                            match_info=None,
                            detection_data=self._current_detection_data,
                            action_executed=False,
                        )
                        continue

                    logger.info(f"  ✅ Conditions MET!")
                
                # FIRE!
                logger.info(f"\n🔥🔥🔥 TRIGGER FIRED! 🔥🔥🔥")
                triggers_fired += 1
                fired_trigger_ids.append(trigger.id)
                trigger.last_fired_at = datetime.now(timezone.utc)
                if match_info is not None:
                    trigger.last_match_info = json.dumps(match_info)
                    trigger.last_matched_at = datetime.now(timezone.utc)

                success_reason = reason if trigger_mode == "ppl_match" else "Demographic conditions met"
                
                # Execute action(s) if configured
                action_executed = False
                action_uuids_raw = getattr(trigger, 'action_uuids', None)
                action_uuid_list = []
                if action_uuids_raw:
                    try:
                        action_uuid_list = json.loads(action_uuids_raw) if isinstance(action_uuids_raw, str) else action_uuids_raw
                    except (json.JSONDecodeError, TypeError):
                        action_uuid_list = []
                
                # Fallback to legacy single action_uuid
                if not action_uuid_list and trigger.action_uuid:
                    action_uuid_list = [str(trigger.action_uuid)]
                
                for action_uuid_str in action_uuid_list:
                    await self._execute_trigger_action(
                        trigger,
                        db,
                        evaluation_reason=success_reason,
                        match_info=match_info,
                        action_uuid_override=action_uuid_str,
                    )
                    action_executed = True

                self._log_execution(
                    db=db,
                    trigger=trigger,
                    passed=True,
                    reason=success_reason,
                    match_info=match_info,
                    detection_data=self._current_detection_data,
                    action_executed=action_executed,
                )
            
            # Commit all updates
            db.commit()
            
            logger.info(f"\n✅ EVALUATION COMPLETE (Redis Pub/Sub)")
            logger.info(f"   Triggers Evaluated: {len(triggers)}")
            logger.info(f"   Triggers Fired: {triggers_fired}")
            logger.info(f"   Fired IDs: {fired_trigger_ids}")
            
        except Exception as e:
            logger.error(f"❌ Error evaluating triggers: {e}", exc_info=True)
            db.rollback()
        finally:
            db.close()

    def _log_execution(
        self,
        db: Session,
        trigger: Trigger,
        passed: bool,
        reason: str,
        match_info: Optional[Dict[str, Any]],
        detection_data: Dict[str, Any],
        action_executed: bool,
    ):
        """Persist a trigger evaluation row for auditability."""
        source_mvr_uuids = detection_data.get("source_mvr_uuids") or []
        source_mvr_uuid = None
        matched_group_id = None
        matched_member_uuid = None
        similarity_score = None
        threshold = None
        match_details_json = None

        if match_info:
            best_match = match_info.get("best_match") or {}
            source_mvr_uuid = best_match.get("source_mvr_uuid") or (source_mvr_uuids[0] if source_mvr_uuids else None)
            matched_group_id = match_info.get("group_id")
            matched_member_uuid = best_match.get("matched_member_uuid")
            similarity_score = best_match.get("similarity_score")
            threshold = match_info.get("threshold")
            match_details_json = json.dumps(match_info)
        elif source_mvr_uuids:
            source_mvr_uuid = source_mvr_uuids[0]

        log_row = TriggerExecutionLog(
            trigger_uuid=trigger.uuid,
            trigger_id=trigger.id,
            trigger_name=trigger.name,
            trigger_mode=(getattr(trigger, "trigger_mode", None) or "demographic"),
            camera_device_id=trigger.camera_device_id,
            source_mvr_uuid=source_mvr_uuid,
            matched_group_id=matched_group_id,
            matched_member_uuid=matched_member_uuid,
            similarity_score=similarity_score,
            threshold=threshold,
            match_details_json=match_details_json,
            passed=passed,
            reason=reason,
            action_executed=action_executed,
            evaluated_at=datetime.now(timezone.utc),
        )

        # Populate search trigger fields from metadata
        metadata = detection_data.get("metadata") if isinstance(detection_data.get("metadata"), dict) else {}
        if detection_data.get("source") == "search_trigger" or metadata.get("search_session_uuid"):
            search_cameras = metadata.get("search_cameras")
            if search_cameras:
                log_row.search_cameras_queried = json.dumps(search_cameras)
            log_row.search_session_uuid = metadata.get("search_session_uuid")

        db.add(log_row)

    async def _evaluate_ppl_match(self, trigger: Trigger, detection_data: Dict):
        """
        Evaluate ppl-match mode by checking source MVR UUIDs against target group via vmeta duplicate-check endpoint.

        Returns:
            tuple[passed: bool, reason: str, match_info: Optional[dict]]
        """
        group_id = getattr(trigger, "ppl_match_group_id", None)
        threshold = float(getattr(trigger, "ppl_match_similarity_threshold", 0.75) or 0.75)
        top_k = int(getattr(trigger, "ppl_match_top_k", 1) or 1)

        if not group_id:
            return False, "Missing ppl_match_group_id", None

        source_mvr_uuids = self._extract_source_mvr_uuids(detection_data)
        if not source_mvr_uuids:
            return False, "No source MVR UUIDs in evaluation context", None

        endpoint_base = f"{self.vmeta_service_url}/api/v1/individual-groups/{group_id}/check-duplicates"
        all_candidates = []

        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                for source_mvr_uuid in source_mvr_uuids:
                    payload = {
                        "candidate_mvr_uuid": source_mvr_uuid,
                        "similarity_threshold": threshold,
                    }
                    response = await client.post(endpoint_base, json=payload)
                    if response.status_code != 200:
                        logger.warning(
                            f"  ⚠️ ppl_match check failed for source {source_mvr_uuid}: "
                            f"{response.status_code} {response.text[:200]}"
                        )
                        continue

                    data = response.json()
                    if data.get("has_duplicates"):
                        for item in data.get("matches", []):
                            all_candidates.append({
                                "source_mvr_uuid": source_mvr_uuid,
                                "matched_member_uuid": item.get("existing_member_id"),
                                "similarity_score": item.get("similarity_score", 0.0),
                                "confidence": item.get("confidence"),
                                "existing_member_name": item.get("existing_member_name"),
                                "group_member_number": item.get("group_member_number"),
                            })
        except Exception as e:
            logger.error(f"  ❌ ppl_match evaluation error: {e}", exc_info=True)
            return False, f"ppl_match evaluation error: {str(e)}", None

        if not all_candidates:
            # Check if negate mode is active: fire when NO matches found
            negate = bool(getattr(trigger, "ppl_match_negate", False))
            if negate:
                no_match_info = {
                    "mode": "ppl_match",
                    "group_id": group_id,
                    "threshold": threshold,
                    "top_k": top_k,
                    "matched": False,
                    "negated": True,
                    "evaluated_source_count": len(source_mvr_uuids),
                    "evaluated_at": datetime.now(timezone.utc).isoformat(),
                }
                return True, "No group members matched (NOT mode)", no_match_info
            return False, "No group matches above threshold", None

        all_candidates = sorted(
            all_candidates,
            key=lambda x: x.get("similarity_score", 0.0),
            reverse=True,
        )
        top_candidates = all_candidates[:top_k]
        best = top_candidates[0]

        # In negate mode, matches found means the trigger should NOT fire
        negate = bool(getattr(trigger, "ppl_match_negate", False))
        if negate:
            return False, "Group member(s) matched — trigger skipped (NOT mode)", None

        match_info = {
            "mode": "ppl_match",
            "group_id": group_id,
            "threshold": threshold,
            "top_k": top_k,
            "matched": True,
            "best_match": best,
            "top_candidates": top_candidates,
            "evaluated_source_count": len(source_mvr_uuids),
            "matched_at": datetime.now(timezone.utc).isoformat(),
        }
        return True, _build_ppl_match_reason(best), match_info

    def _extract_source_mvr_uuids(self, detection_data: Dict[str, Any]) -> List[str]:
        """Extract source identity UUIDs from known payload shapes."""
        candidates: List[str] = []

        def _add_uuid(raw_value: Any) -> None:
            if not raw_value:
                return
            try:
                normalized = str(UUID(str(raw_value)))
                if normalized not in candidates:
                    candidates.append(normalized)
            except Exception:
                return

        def _collect_from_person(person_obj: Dict[str, Any]) -> None:
            _add_uuid(person_obj.get("mvr_person_uuid"))
            _add_uuid(person_obj.get("source_mvr_uuid"))
            _add_uuid(person_obj.get("person_object_uuid"))
            _add_uuid(person_obj.get("individual_uuid"))
            for face in person_obj.get("faces", []) or []:
                if not isinstance(face, dict):
                    continue
                _add_uuid(face.get("mvr_person_uuid"))
                _add_uuid(face.get("source_mvr_uuid"))
                _add_uuid(face.get("person_object_uuid"))
                _add_uuid(face.get("individual_uuid"))

        for direct in detection_data.get("source_mvr_uuids") or []:
            _add_uuid(direct)

        metadata = detection_data.get("metadata") or {}
        if isinstance(metadata, dict):
            for nested in metadata.get("source_mvr_uuids") or []:
                _add_uuid(nested)

        person_objects = detection_data.get("person_objects") or []
        if isinstance(metadata, dict):
            person_objects = person_objects or (metadata.get("person_objects") or [])

        for person in person_objects:
            if isinstance(person, dict):
                _collect_from_person(person)

        return candidates
    
    def _evaluate_conditions(self, conditions, demographics, people_count):
        """Evaluate demographic conditions (same logic as webhook endpoint)"""
        logger.info(f"  🔍 Evaluating {len(conditions)} condition(s)")
        logger.info(f"     Input people_count: {people_count}")
        logger.info(f"     Input demographics: {demographics}")
        
        for idx, condition in enumerate(conditions, 1):
            field = condition.get('field')
            operator = condition.get('operator')
            threshold = condition.get('value')
            
            logger.info(f"     Condition {idx}: {field} {operator} {threshold}")
            
            if field == 'people_count':
                actual_value = people_count
                logger.info(f"       Actual people_count: {actual_value}")
            elif field == 'age_threshold':
                # Prefer direct average_age (published by instant-detection pipeline)
                if demographics.get('average_age') is not None:
                    actual_value = float(demographics['average_age'])
                    logger.info(f"       Using average_age from demographics: {actual_value}")
                else:
                    # Fallback: compute weighted-average from bracket percentages
                    actual_value = sum(
                        float(demographics.get(k, 0)) * mid / 100.0
                        for k, mid in AGE_BRACKET_MIDPOINTS.items()
                    )
                    logger.info(f"       Computed weighted avg age from brackets: {actual_value}")
            elif isinstance(field, str) and (
                field in AGE_COUNT_TO_PERCENT_FIELD or field in LEGACY_PERCENT_AGE_FIELDS
            ):
                percent_field = AGE_COUNT_TO_PERCENT_FIELD.get(field, field)
                age_count_value = demographics.get(field) if field in AGE_COUNT_TO_PERCENT_FIELD else None
                age_percent_value = demographics.get(percent_field)

                if age_count_value is not None:
                    actual_value = float(age_count_value)
                    logger.info(f"       Actual {field}: {actual_value}")
                elif age_percent_value is not None:
                    actual_value = (float(people_count) * float(age_percent_value)) / 100.0
                    logger.info(
                        f"       Actual {percent_field}: {age_percent_value}% -> derived age_count: {actual_value}"
                    )
                else:
                    logger.info(f"       ❌ FAIL: Field '{field}' not in data")
                    return False
            else:
                actual_value = demographics.get(field)
                logger.info(f"       Actual {field}: {actual_value}")
            
            if actual_value is None:
                logger.info(f"       ❌ FAIL: Field '{field}' not in data")
                return False
            
            threshold = float(threshold)
            actual_value = float(actual_value)
            
            logger.info(f"       Comparing: {actual_value} {operator} {threshold}")
            
            if operator == 'gte' and not (actual_value >= threshold):
                logger.info(f"       ❌ FAIL: {actual_value} NOT >= {threshold}")
                return False
            elif operator == 'lte' and not (actual_value <= threshold):
                logger.info(f"       ❌ FAIL: {actual_value} NOT <= {threshold}")
                return False
            elif operator == 'eq' and not (actual_value == threshold):
                logger.info(f"       ❌ FAIL: {actual_value} NOT == {threshold}")
                return False
            elif operator == 'gt' and not (actual_value > threshold):
                logger.info(f"       ❌ FAIL: {actual_value} NOT > {threshold}")
                return False
            elif operator == 'lt' and not (actual_value < threshold):
                logger.info(f"       ❌ FAIL: {actual_value} NOT < {threshold}")
                return False
            else:
                logger.info(f"       ✅ PASS")
        
        logger.info(f"  ✅ ALL CONDITIONS PASSED")
        return True
    
    async def _execute_trigger_action(
        self,
        trigger: Trigger,
        db: Session,
        evaluation_reason: Optional[str] = None,
        match_info: Optional[Dict[str, Any]] = None,
        action_uuid_override: Optional[str] = None,
    ):
        """Execute a single action associated with this trigger.
        
        If action_uuid_override is provided, use that UUID instead of trigger.action_uuid.
        This supports multi-action execution where the caller iterates over action_uuids.
        """
        from src.models.user_trigger_action import UserTriggerAction
        
        target_uuid = action_uuid_override or str(trigger.action_uuid)
        logger.info(f"  🎬 Executing trigger action...")
        logger.info(f"     Action UUID: {target_uuid}")
        
        # Look up the action
        action = db.query(UserTriggerAction).filter(
            UserTriggerAction.uuid == target_uuid
        ).first()
        
        if not action:
            logger.error(f"     ❌ Action not found: {target_uuid}")
            return
        
        logger.info(f"     Action Type: {action.action_type}")
        logger.info(f"     Action Name: {action.name}")
        
        # Route to appropriate handler.
        #
        # Presence actions (the "Presence Action N" audit-log actions created by
        # the presence service) are `action_type = "log"` but carry a presence
        # marker. On a people-match trigger they must issue a video-only grant
        # (process_trigger_match) in addition to the normal audit-log write.
        if self._is_presence_action(action) and trigger.trigger_mode in ("ppl_match", "vprofile_match"):
            await self._execute_presence_action(
                action, trigger, db,
                evaluation_reason=evaluation_reason,
                match_info=match_info,
            )
            # Presence actions are audit-log actions; keep writing the log too.
            if getattr(action, "action_type", None) == "log":
                await self._execute_log_action(
                    action, trigger, db,
                    evaluation_reason=evaluation_reason,
                    match_info=match_info,
                )
        elif action.action_type == "digital_signage":
            await self._execute_signage_action(
                action,
                trigger,
                db,
                evaluation_reason=evaluation_reason,
                match_info=match_info,
            )
        elif action.action_type == "email":
            await self._execute_email_action(action, trigger, db, evaluation_reason=evaluation_reason, match_info=match_info)
        elif action.action_type == "webhook":
            await self._execute_webhook_action(action, trigger, db, evaluation_reason=evaluation_reason, match_info=match_info)
        elif action.action_type == "messaging_app":
            await self._execute_messaging_app_action(action, trigger, db, evaluation_reason=evaluation_reason, match_info=match_info)
        elif action.action_type == "log":
            await self._execute_log_action(action, trigger, db, evaluation_reason=evaluation_reason, match_info=match_info)
        elif action.action_type == "alert":
            await self._execute_alert_action(action, trigger, db, evaluation_reason=evaluation_reason, match_info=match_info)
        else:
            logger.warning(f"     ⚠️ Unsupported action type: {action.action_type}")

    def _is_presence_action(self, action) -> bool:
        """Return True if an action represents a presence action.

        Presence actions may be explicitly typed (`presence_grant`, ...) or be
        the audit-log actions the presence service creates (`action_type="log"`
        whose config carries a `category: "presence"` / `tags: presence` marker
        and a "Presence Action" name).
        """
        action_type = getattr(action, "action_type", None) or ""
        if action_type in ("presence_grant", "presence_log", "presence_notify", "presence_deny"):
            return True

        name = (getattr(action, "name", None) or "").strip()
        if name.lower().startswith("presence action"):
            return True

        cfg = getattr(action, "action_config", None)
        if isinstance(cfg, str) and cfg.strip():
            try:
                parsed = json.loads(cfg)
            except (json.JSONDecodeError, TypeError):
                return False
            data = parsed.get("data", {}) if isinstance(parsed, dict) else {}
            if not isinstance(data, dict):
                return False
            if data.get("category") == "presence":
                return True
            tags = data.get("tags", []) or []
            if any(str(tag).lower() == "presence" for tag in tags):
                return True
        return False
    
    
    async def _execute_signage_action(
        self,
        action,
        trigger: Trigger,
        db: Session,
        evaluation_reason: Optional[str] = None,
        match_info: Optional[Dict[str, Any]] = None,
    ):
        """Execute signage playlist switch action from action config"""
        logger.info(f"  📺 Executing digital signage action...")
        
        try:
            # Parse action_config to get signage settings
            config = json.loads(action.action_config) if isinstance(action.action_config, str) else action.action_config
            
            device_ids = config.get("device_ids", [])
            playlist_id = config.get("playlist_id")
            transition_mode = config.get("transition_mode", "immediate")
            
            logger.info(f"     Target Playlist UUID: {playlist_id}")
            logger.info(f"     Transition Mode: {transition_mode}")
            logger.info(f"     Target Device IDs: {device_ids}")
            
            if not device_ids or not playlist_id:
                logger.error(f"     ❌ Missing device_ids or playlist_id in action config")
                return
            
            playback_service = SignagePlaybackService(db)
            
            for device_uuid_str in device_ids:
                try:
                    device_uuid = UUID(device_uuid_str)
                    
                    logger.info(f"\n     📱 Sending switch command to device:")
                    logger.info(f"        Device UUID: {device_uuid}")
                    logger.info(f"        Target Playlist: {playlist_id}")
                    
                    # Create PlaybackControlRequest
                    from src.schemas.signage import PlaybackControlRequest, PlaybackCommand, PlaybackParameters
                    
                    # Create playback parameters
                    playback_params = PlaybackParameters()
                    
                    # Create control request to start new playlist
                    control_request = PlaybackControlRequest(
                        device_ids=[device_uuid],
                        command=PlaybackCommand.START,
                        video_list_id=UUID(playlist_id),
                        parameters=playback_params
                    )
                    
                    # Send the command (SignagePlaybackService will query discovery service)
                    result = await playback_service.control_playback(control_request)
                    logger.info(f"        ✅ Command result: {json.dumps(result, indent=10)}")

                    command_success = True
                    if isinstance(result, dict):
                        if isinstance(result.get("results"), list):
                            command_success = all(
                                bool(item.get("success", True))
                                for item in result.get("results", [])
                                if isinstance(item, dict)
                            )
                        elif "success" in result:
                            command_success = bool(result.get("success"))

                    detection_data = getattr(self, '_current_detection_data', {})
                    audit_event_data = {
                        "trigger_id": str(trigger.uuid),
                        "trigger_name": trigger.name,
                        "action_name": action.name,
                        "action_type": action.action_type,
                        "camera_id": detection_data.get("camera_id"),
                        "detection_timestamp": detection_data.get("timestamp"),
                        "people_count": detection_data.get("people_count", 0),
                        "demographics": detection_data.get("demographics", {}),
                        "reason": evaluation_reason,
                        "match": match_info,
                        "signage": {
                            "device_id": str(device_uuid),
                            "playlist_id": playlist_id,
                            "transition_mode": transition_mode,
                            "command": "start",
                            "success": command_success,
                        },
                    }

                    comms_client = get_communications_client()
                    audit_result = await comms_client.log_audit_event(
                        event_type="trigger_fired",
                        event_source="media_service",
                        event_data=audit_event_data,
                        severity="info" if command_success else "warning",
                    )

                    if audit_result.get("success"):
                        logger.info(f"        📋 Audit log created. Log UUID: {audit_result.get('log_uuid')}")
                    else:
                        logger.warning(f"        ⚠️ Audit log failed: {audit_result.get('message')}")
                
                except ValueError as e:
                    logger.error(f"Invalid device UUID {device_uuid_str}: {e}")
                except Exception as e:
                    logger.error(f"Error switching playlist for device {device_uuid_str}: {e}")
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse action_config: {e}")
        except Exception as e:
            logger.error(f"Error executing signage action: {e}", exc_info=True)
    
    async def _execute_email_action(
        self,
        action,
        trigger: Trigger,
        db: Session,
        evaluation_reason: Optional[str] = None,
        match_info: Optional[Dict[str, Any]] = None,
    ):
        """Execute email action via Communications Service."""
        logger.info(f"  📧 Executing email action...")
        
        try:
            # Parse action_config
            config = json.loads(action.action_config) if isinstance(action.action_config, str) else action.action_config
            
            # Handle both 'to' (single string) and 'recipients' (list) formats
            recipients = config.get("recipients")
            if not recipients:
                # Try 'to' field (Flutter UI format)
                to_field = config.get("to", "")
                if isinstance(to_field, str):
                    recipients = [email.strip() for email in to_field.split(',') if email.strip()]
                elif isinstance(to_field, list):
                    recipients = to_field
                else:
                    recipients = []
            
            # Handle CC field
            cc = config.get("cc", [])
            if not isinstance(cc, list):
                cc = [str(cc)] if cc else []
            
            subject = config.get("subject", "Trigger Alert")
            body_template = config.get("body", "Trigger '{trigger_name}' was fired.")

            interpolated_subject = _interpolate_action_message(
                base_message=subject,
                trigger=trigger,
                evaluation_reason=evaluation_reason,
                match_info=match_info,
            )
            
            # Substitute variables in template
            body = _interpolate_action_message(
                base_message=body_template,
                trigger=trigger,
                evaluation_reason=evaluation_reason,
                match_info=match_info,
            )
            
            logger.info(f"     Recipients: {recipients}")
            logger.info(f"     CC: {cc}")
            logger.info(f"     Subject: {interpolated_subject}")
            
            if not recipients:
                logger.error(f"     ❌ No recipients configured in action")
                return
            
            # Get detection data if available
            detection_data = getattr(self, '_current_detection_data', {})
            
            # Build payload with detection data and trigger info
            email_payload = {
                "trigger_name": trigger.name,
                "trigger_description": trigger.description or "",
                "camera_id": detection_data.get("camera_id"),
                "detection_timestamp": detection_data.get("timestamp"),
                "people_count": detection_data.get("people_count"),
                "demographics": detection_data.get("demographics", {}),
            }
            
            logger.info(f"     Email payload with demographics: {email_payload}")
            
            # Call Communications Service
            # Note: installation_id and tenant_name are automatically included from Communications Service config
            comms_client = get_communications_client()
            result = await comms_client.send_email(
                to=recipients,
                cc=cc if cc else None,
                subject=interpolated_subject,
                text_body=body,
                triggered_by="media_service",
                trigger_type="trigger_action",
                trigger_id=str(trigger.uuid),
                payload=email_payload,
            )
            
            if result.get("success"):
                logger.info(f"     ✅ Email sent successfully. Log UUID: {result.get('log_uuid')}")
            else:
                logger.error(f"     ❌ Email failed: {result.get('message')}")
        
        except Exception as e:
            logger.error(f"     ❌ Error executing email action: {e}", exc_info=True)
    
    async def _execute_webhook_action(
        self,
        action,
        trigger: Trigger,
        db: Session,
        evaluation_reason: Optional[str] = None,
        match_info: Optional[Dict[str, Any]] = None,
    ):
        """Execute webhook action via Communications Service."""
        logger.info(f"  🔗 Executing webhook action...")
        
        try:
            # Parse action_config
            config = json.loads(action.action_config) if isinstance(action.action_config, str) else action.action_config
            
            webhook_url = config.get("url")
            method = config.get("method", "POST")
            
            # Build payload
            payload = {
                "event": "trigger_fired",
                "trigger_id": str(trigger.uuid),
                "trigger_name": trigger.name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": config.get("payload_data", {}),
                "reason": evaluation_reason,
                "match": match_info,
            }
            
            logger.info(f"     Webhook URL: {webhook_url}")
            logger.info(f"     Method: {method}")
            
            # Call Communications Service
            # Note: installation_id and tenant_name are automatically included from Communications Service config
            comms_client = get_communications_client()
            result = await comms_client.send_webhook(
                url=webhook_url,
                payload=payload,
                method=method,
                triggered_by="media_service",
                trigger_type="trigger_action",
                trigger_id=str(trigger.uuid),
            )
            
            if result.get("success"):
                logger.info(f"     ✅ Webhook sent successfully. Log UUID: {result.get('log_uuid')}")
                logger.info(f"     Status Code: {result.get('status_code')}")
            else:
                logger.error(f"     ❌ Webhook failed: {result.get('message')}")
        
        except Exception as e:
            logger.error(f"     ❌ Error executing webhook action: {e}", exc_info=True)

    async def _execute_messaging_app_action(
        self,
        action,
        trigger: Trigger,
        db: Session,
        evaluation_reason: Optional[str] = None,
        match_info: Optional[Dict[str, Any]] = None,
    ):
        """Execute messaging app action (Slack or Teams) via a platform-formatted webhook."""
        logger.info(f"  💬 Executing messaging app action...")

        try:
            config = json.loads(action.action_config) if isinstance(action.action_config, str) else action.action_config

            platform = (config.get("platform") or "slack").lower()
            webhook_url = config.get("webhook_url")
            message_template = config.get("message_template", "")
            title = config.get("title", "")
            mention = config.get("mention", "")

            if not webhook_url:
                logger.error(f"     ❌ Missing webhook_url in messaging app action config")
                return

            message = _interpolate_action_message(
                base_message=message_template,
                trigger=trigger,
                evaluation_reason=evaluation_reason,
                match_info=match_info,
            )

            if platform == "slack":
                text = f"{mention} {message}".strip() if mention else message
                payload = {"text": text}

            elif platform == "teams":
                interpolated_title = _interpolate_action_message(
                    base_message=title,
                    trigger=trigger,
                    evaluation_reason=evaluation_reason,
                    match_info=match_info,
                ) if title else ""

                if interpolated_title:
                    payload = {
                        "type": "message",
                        "attachments": [{
                            "contentType": "application/vnd.microsoft.card.adaptive",
                            "content": {
                                "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                                "type": "AdaptiveCard",
                                "version": "1.4",
                                "body": [
                                    {
                                        "type": "TextBlock",
                                        "size": "Medium",
                                        "weight": "Bolder",
                                        "text": interpolated_title,
                                    },
                                    {
                                        "type": "TextBlock",
                                        "text": message,
                                        "wrap": True,
                                    },
                                ],
                            },
                        }],
                    }
                else:
                    payload = {"text": message}

            else:
                logger.warning(f"     ⚠️ Unknown messaging platform '{platform}', sending as plain text")
                payload = {"text": message}

            logger.info(f"     Platform: {platform}")
            logger.info(f"     Webhook URL: {webhook_url}")

            comms_client = get_communications_client()
            result = await comms_client.send_webhook(
                url=webhook_url,
                payload=payload,
                method="POST",
                triggered_by="media_service",
                trigger_type="trigger_action",
                trigger_id=str(trigger.uuid),
            )

            if result.get("success"):
                logger.info(f"     ✅ {platform.capitalize()} message sent. Log UUID: {result.get('log_uuid')}")
            else:
                logger.error(f"     ❌ {platform.capitalize()} message failed: {result.get('message')}")

        except Exception as e:
            logger.error(f"     ❌ Error executing messaging app action: {e}", exc_info=True)

    async def _execute_log_action(
        self,
        action,
        trigger: Trigger,
        db: Session,
        evaluation_reason: Optional[str] = None,
        match_info: Optional[Dict[str, Any]] = None,
    ):
        """Execute audit log action via Communications Service."""
        logger.info(f"  📋 Executing audit log action...")
        
        try:
            # Parse action_config
            config = json.loads(action.action_config) if isinstance(action.action_config, str) else action.action_config
            
            # Extract message/body from config
            message = config.get("message") or config.get("body") or config.get("content", "")
            message = _interpolate_action_message(
                base_message=message,
                trigger=trigger,
                evaluation_reason=evaluation_reason,
                match_info=match_info,
            )
            
            # Get detection data if available
            detection_data = getattr(self, '_current_detection_data', {})
            
            event_data = {
                "trigger_id": str(trigger.uuid),
                "trigger_name": trigger.name,
                "action_name": action.name,
                "message": message,
                "people_count": detection_data.get("people_count", 0),
                "demographics": detection_data.get("demographics", {}),
                "camera_id": detection_data.get("camera_id"),
                "detection_timestamp": detection_data.get("timestamp"),
                "custom_data": config.get("data", {}),
                "reason": evaluation_reason,
                "match": match_info,
            }
            
            # Call Communications Service
            # Note: installation_id and tenant_name are automatically included from Communications Service config
            comms_client = get_communications_client()
            result = await comms_client.log_audit_event(
                event_type="trigger_fired",
                event_source="media_service",
                event_data=event_data,
                severity=config.get("severity", "info"),
            )
            
            if result.get("success"):
                logger.info(f"     ✅ Audit log created. Log UUID: {result.get('log_uuid')}")
            else:
                logger.error(f"     ❌ Audit log failed: {result.get('message')}")
        
        except Exception as e:
            logger.error(f"     ❌ Error executing log action: {e}", exc_info=True)
    
    async def _execute_alert_action(
        self,
        action,
        trigger: Trigger,
        db: Session,
        evaluation_reason: Optional[str] = None,
        match_info: Optional[Dict[str, Any]] = None,
    ):
        """Execute alert action via Communications Service."""
        logger.info(f"  🔔 Executing alert action...")
        
        try:
            # Parse action_config
            config = json.loads(action.action_config) if isinstance(action.action_config, str) else action.action_config
            
            # Extract alert settings
            message = config.get("message", "Alert triggered")
            message = _interpolate_action_message(
                base_message=message,
                trigger=trigger,
                evaluation_reason=evaluation_reason,
                match_info=match_info,
            )
            severity = config.get("severity", "warning")
            duration_seconds = config.get("duration_seconds", 30)
            
            # Get detection data if available
            detection_data = getattr(self, '_current_detection_data', {})
            
            # Build alert data
            alert_data = {
                "trigger_id": str(trigger.uuid),
                "trigger_name": trigger.name,
                "action_name": action.name,
                "message": message,
                "severity": severity,
                "duration_seconds": duration_seconds,
                "people_count": detection_data.get("people_count", 0),
                "demographics": detection_data.get("demographics", {}),
                "camera_id": detection_data.get("camera_id"),
                "detection_timestamp": detection_data.get("timestamp"),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "reason": evaluation_reason,
                "match": match_info,
            }
            
            logger.info(f"     Message: {message}")
            logger.info(f"     Severity: {severity}")
            logger.info(f"     Duration: {duration_seconds}s")
            
            # Call Communications Service to log the alert
            # This creates an audit log entry that can be displayed as on-screen alerts
            comms_client = get_communications_client()
            result = await comms_client.log_audit_event(
                event_type="alert",
                event_source="media_service",
                event_data=alert_data,
                severity=severity,
            )
            
            if result.get("success"):
                logger.info(f"     ✅ Alert logged successfully. Log UUID: {result.get('log_uuid')}")
            else:
                logger.error(f"     ❌ Alert logging failed: {result.get('message')}")
        
        except Exception as e:
            logger.error(f"     ❌ Error executing alert action: {e}", exc_info=True)

    async def _execute_presence_action(
        self,
        action,
        trigger: Trigger,
        db: Session,
        evaluation_reason: Optional[str] = None,
        match_info: Optional[Dict[str, Any]] = None,
    ):
        """Issue a video-only presence grant by notifying the Presence service.

        Called when a people-match trigger (ppl_match / vprofile_match) fires
        successfully and a presence action is attached. The presence service
        creates and grades a camera-only (video-only) grant visible in the
        presence screen and analytics tabs.
        """
        logger.info("  📍 Executing presence action...")

        # Only issue grants for people-match triggers. Presence actions on other
        # trigger types (e.g. demographic) should not mint camera-only grants.
        if getattr(trigger, "trigger_mode", None) not in ("ppl_match", "vprofile_match"):
            logger.info(
                "  ⏭️ Presence action skipped for trigger mode %r (people-match only)",
                getattr(trigger, "trigger_mode", None),
            )
            return

        presence_url = os.getenv(
            "PRESENCE_SERVICE_URL",
            getattr(get_config(), "PRESENCE_SERVICE_URL", "http://localhost:8011"),
        ).rstrip("/")

        endpoint = f"{presence_url}/api/v1/presence/trigger-match"

        # Determine the camera that produced the match. vprofile_match stores
        # source_camera_id in match_info; fall back to the event/detection data
        # or the trigger's configured camera.
        camera_device_id = None
        if isinstance(match_info, dict):
            camera_device_id = match_info.get("source_camera_id") or match_info.get("camera_id")
        if not camera_device_id:
            detection_data = getattr(self, "_current_detection_data", {}) or {}
            camera_device_id = detection_data.get("camera_id")
        if not camera_device_id:
            camera_device_id = getattr(trigger, "camera_device_id", None)

        if not camera_device_id:
            logger.warning("  ⚠️ Presence action skipped: unable to resolve camera_device_id")
            return

        payload = {
            "camera_device_id": camera_device_id,
            "trigger_uuid": str(trigger.uuid),
            "action_uuid": str(action.uuid),
            "match_info": match_info or {},
        }
        if isinstance(match_info, dict):
            best = match_info.get("best_match") if isinstance(match_info.get("best_match"), dict) else {}
            payload["matched_member_uuid"] = best.get("matched_member_uuid")
            payload["similarity_score"] = best.get("similarity_score")
            payload["source_mvr_uuid"] = best.get("source_mvr_uuid")
            payload["matched_at"] = match_info.get("matched_at")

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
                response = await client.post(endpoint, json=payload)
        except httpx.HTTPError as e:
            logger.error(f"  ❌ Presence service request failed: {e}", exc_info=True)
            return

        if response.status_code >= 400:
            logger.error(
                f"  ❌ Presence service rejected trigger-match: HTTP {response.status_code} {response.text[:300]}"
            )
            return

        data = response.json()
        session_info = data.get("data", {}) if isinstance(data, dict) else {}
        logger.info(
            "  ✅ Video-only presence grant issued: session=%s decision=%s mode=%s grant=%s",
            session_info.get("session_uuid"),
            session_info.get("decision"),
            session_info.get("session_mode"),
            session_info.get("grant_type"),
        )


# Global subscriber instance
_subscriber: InstantDetectionSubscriber = None


async def start_subscriber():
    """Start the global subscriber"""
    global _subscriber
    if _subscriber is None:
        _subscriber = InstantDetectionSubscriber()
    await _subscriber.start()


async def stop_subscriber():
    """Stop the global subscriber"""
    global _subscriber
    if _subscriber:
        await _subscriber.stop()
