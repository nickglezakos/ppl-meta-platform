# Trigger Execution Architecture - Proposal

**Date**: December 11, 2025  
**Status**: PROPOSAL - Awaiting Implementation  
**Related Docs**: TRIGGERS_IMPLEMENTATION_COMPLETE.md

---

## Executive Summary

This document proposes an event-driven architecture for automatic trigger execution in the PPL Meta platform. The system will monitor camera counter data in real-time and automatically execute user-defined actions when trigger conditions are met.

### Core Requirements

**Given**:
- (a) A trigger is **active** (`is_active = true`)
- (b) The trigger is **linked to an active user action** (`action_uuid` → `user_trigger_actions` where `is_active = true`)
- (c) The trigger is **associated with a camera** (`camera_device_id = "usb_camera_0"`)
- (d) Camera counter data is available within the **tracking duration** window

**When**:
- The trigger's conditions **evaluate to true** (person count, age range, gender filters match)

**Then**:
- Execute the linked user action (alert, email, webhook, log)

---

## Architecture: Two-Stage Decoupled Design ⭐

### Stage 1: MVR Data Collection & Caching (Camera Recording)

**Responsibility**: Continuously cache MVR search results to Redis while camera is recording

**How It Works**:
```
┌─────────────────────────────────────────────────────────────────────┐
│              STAGE 1: MVR DATA COLLECTION (RECORDING)               │
└─────────────────────────────────────────────────────────────────────┘

1. CAMERA RECORDING ACTIVE
   └─> ppl-meta-cameras records video segments to disk
   └─> Vision service processes frames
   └─> MVR people detected and stored in VMeta DB

2. MVR CACHE WORKER (runs during recording, every 10-30 seconds)
   └─> FOR EACH active recording camera:
       ├─> Fetch latest MVR results for recent video segments
       │   POST /api/v1/mvr-people/count-by-videos
       │   (videos from last N minutes based on max tracking_duration)
       │
       ├─> Build counter data with demographics:
       │   {
       │     "total_count": 15,
       │     "age_distribution": {"0-18": 3, "19-30": 7, ...},
       │     "gender_distribution": {"male": 8, "female": 7},
       │     "video_uuids": [...],
       │     "timestamp": "2025-12-11T14:30:00Z"
       │   }
       │
       └─> CACHE TO REDIS:
           Key: "camera:mvr:{camera_device_id}:latest"
           TTL: 5 minutes
           Value: JSON counter data

3. CACHE STRATEGY
   ├─> Update cache every 10-30 seconds during recording
   ├─> Store rolling window (e.g., last 1 hour of data)
   ├─> Use existing MVR counter endpoint with demographics
   └─> TTL ensures stale data auto-expires
```

**Benefits**:
- ✅ **Decoupled**: MVR collection happens independently of trigger evaluation
- ✅ **Fresh Data**: Cache updated continuously during recording
- ✅ **Performance**: Triggers read from fast Redis cache, not heavy DB queries
- ✅ **Existing Endpoint**: Uses your current `/api/v1/cameras/{camera_id}/mvr-count` endpoint
- ✅ **Auto-Cleanup**: TTL prevents stale data accumulation

---

### Stage 2: Trigger Evaluation & Action Execution

**Responsibility**: Read cached MVR data and evaluate triggers independently

**How It Works**:
```
┌─────────────────────────────────────────────────────────────────────┐
│           STAGE 2: TRIGGER EVALUATION (DECOUPLED)                   │
└─────────────────────────────────────────────────────────────────────┘

1. TRIGGER WORKER (runs every 30-60 seconds, independent of recording)
   └─> FOR EACH camera with active triggers:
       ├─> READ FROM REDIS CACHE:
       │   Key: "camera:mvr:{camera_device_id}:latest"
       │   
       ├─> If cache exists (camera is/was recently recording):
       │   ├─> Extract counter data
       │   ├─> POST /api/v1/triggers/evaluate
       │   │   {
       │   │     "camera_device_id": "usb_camera_0",
       │   │     "total_count": 15,
       │   │     "age_distribution": {...},
       │   │     "gender_distribution": {...}
       │   │   }
       │   └─> IF triggers pass:
       │       └─> Execute linked user actions
       │
       └─> If cache empty (camera not recording):
           └─> Skip evaluation (no recent data)

2. ACTION EXECUTION
   └─> Load user_trigger_action by action_uuid
   └─> Execute based on action_type:
       ├─> alert: Store in-app notification
       ├─> email: Send email via SMTP
       ├─> webhook: HTTP POST to configured URL
       └─> log: Write to execution_logs table

3. COOLDOWN PREVENTION
   └─> Track last_execution per trigger (5-minute cooldown)
   └─> Prevents same trigger firing multiple times for same event
```

**Benefits**:
- ✅ **Decoupled**: Trigger evaluation doesn't slow down recording/MVR processing
- ✅ **Fast**: Reads from Redis cache instead of hitting DB/API
- ✅ **Efficient**: Only evaluates when camera has recent data
- ✅ **Scalable**: Can run trigger worker on separate service/machine
- ✅ **Resilient**: If recording fails, triggers don't crash; they just skip

---

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                   TWO-STAGE DECOUPLED ARCHITECTURE                  │
└─────────────────────────────────────────────────────────────────────┘

STAGE 1: Data Collection (ppl-meta-gateway or ppl-meta-cameras)
┌──────────────────────────────────────────────────────────────────┐
│ MVR Cache Worker                                                 │
│ • Runs during camera recording                                   │
│ • Fetches MVR data every 10-30 seconds                          │
│ • Caches to Redis: "camera:mvr:{camera_id}:latest"             │
└───────────────────┬──────────────────────────────────────────────┘
                    │
                    ▼
         ┌──────────────────────┐
         │   REDIS CACHE        │  ◄── Fast, decoupled storage
         │   TTL: 5 minutes     │
         └──────────┬───────────┘
                    │
                    ▼
STAGE 2: Trigger Evaluation (ppl-meta-media)
┌──────────────────────────────────────────────────────────────────┐
│ Trigger Worker                                                   │
│ • Runs every 30-60 seconds                                       │
│ • Reads cached data from Redis                                   │
│ • Evaluates triggers for cameras with recent data                │
│ • Executes actions (alert/email/webhook/log)                     │
│ • 5-minute cooldown per trigger                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

### Why This is Better

**Before (Coupled)**:
- ❌ Trigger worker polls camera API → heavy load
- ❌ Each poll requires DB queries to count MVR people
- ❌ Trigger evaluation blocking on DB performance
- ❌ Wasted polls when camera not recording

**After (Decoupled)**:
- ✅ Recording process caches data → lightweight updates
- ✅ Trigger worker reads from cache → instant access
- ✅ MVR queries happen once per recording session, reused by all triggers
- ✅ Clear separation of concerns
- ✅ Can scale each stage independently

---

## Implementation Complexity

**Stage 1 (MVR Caching)**: 🟢 LOW (2-3 hours)
- Modify existing MVR counter worker or create new one
- Add Redis caching after fetching MVR count
- **Location**: `ppl-meta-gateway/src/workers/mvr_counter_worker.py` (already exists!)

**Stage 2 (Trigger Worker)**: 🟢 LOW (3-4 hours)  
- New worker that reads Redis cache
- Evaluates triggers using cached data
- Executes actions
- **Location**: `ppl-meta-media/src/workers/trigger_worker.py` (new file)

---

## Redis Cache Schema

**Key Pattern**: `camera:mvr:{camera_device_id}:latest`

**Value Structure** (JSON):
```json
{
  "camera_device_id": "usb_camera_0",
  "total_count": 15,
  "age_distribution": {
    "0-18": 3,
    "19-30": 7,
    "31-50": 4,
    "51+": 1
  },
  "gender_distribution": {
    "male": 8,
    "female": 7
  },
  "video_uuids": ["uuid1", "uuid2", "uuid3"],
  "video_count": 3,
  "time_window": "last_hour",
  "cached_at": "2025-12-11T14:30:00Z",
  "expires_at": "2025-12-11T14:35:00Z"
}
```

**TTL**: 5 minutes (auto-expires if camera stops recording)

**Additional Keys** (optional, for history):
- `camera:mvr:{camera_device_id}:history` - List of last N counter snapshots
- `camera:mvr:{camera_device_id}:recording` - Boolean flag indicating if recording is active

---

## Implementation Plan

### Phase 1: Enhance Existing MVR Cache Worker (2-3 hours)

**Location**: `ppl-meta-gateway/src/workers/mvr_counter_worker.py` (already exists!)

**Current State**: Worker already fetches and caches MVR counts for cameras.

**Enhancement**: Add Redis caching with proper key structure for trigger consumption.

```python
# ppl-meta-gateway/src/workers/mvr_counter_worker.py

import json
from datetime import datetime, timedelta
import redis

class MVRCounterWorker:
    """Background worker to pre-compute and cache camera MVR counts."""
    
    def __init__(
        self, 
        interval_seconds: int = 30,  # Poll every 30 seconds during recording
        internal_token: str = None
    ):
        self.interval_seconds = interval_seconds
        self.internal_token = internal_token
        self.redis_client = redis.Redis(
            host='localhost',
            port=6379,
            db=0,
            decode_responses=True
        )
    
    async def _refresh_camera_count(self, camera_id: str) -> bool:
        """
        Refresh MVR count for a single camera and cache to Redis.
        
        NEW: Also stores in trigger-consumable format in Redis.
        """
        try:
            # Get today's date range
            now = datetime.now()
            today = now.date()
            start_time = datetime.combine(today, time.min)
            end_time = now
            
            # Fetch videos for camera
            video_uuids = await self._get_videos_for_camera(
                camera_id=camera_id,
                start_time=start_time,
                end_time=end_time
            )
            
            if not video_uuids:
                logger.debug(f"No videos for camera {camera_id}, skipping cache")
                return False
            
            # Count MVR people with demographics
            count_data = await self._count_mvr_people(video_uuids)
            
            # Build cache data structure
            cache_data = {
                "camera_device_id": camera_id,
                "total_count": count_data.get("count", 0),
                "age_distribution": count_data.get("demographics", {}).get("age_distribution", {}),
                "gender_distribution": count_data.get("demographics", {}).get("gender_distribution", {}),
                "video_uuids": video_uuids,
                "video_count": len(video_uuids),
                "time_window": "last_hour",  # Or compute based on video timestamps
                "cached_at": datetime.utcnow().isoformat(),
                "expires_at": (datetime.utcnow() + timedelta(minutes=5)).isoformat()
            }
            
            # Store in Redis with 5-minute TTL
            # Key format: camera:mvr:{camera_device_id}:latest
            cache_key = f"camera:mvr:{camera_id}:latest"
            self.redis_client.setex(
                cache_key,
                300,  # 5 minutes TTL
                json.dumps(cache_data)
            )
            
            logger.info(
                f"✅ Cached MVR data for {camera_id}: "
                f"{cache_data['total_count']} people in {len(video_uuids)} videos"
            )
            
            # Also update legacy cache format (for existing camera card counter)
            # ... existing cache logic ...
            
            return True
            
        except Exception as e:
            logger.error(f"Error refreshing count for {camera_id}: {e}")
            return False
    
    async def _count_mvr_people(self, video_uuids: List[str]) -> dict:
        """
        Count MVR people with demographics.
        
        UPDATED: Now includes demographics for trigger evaluation.
        """
        if not video_uuids:
            return {
                "count": 0, 
                "video_count": 0,
                "demographics": {
                    "age_distribution": {},
                    "gender_distribution": {}
                }
            }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Call VMeta service with demographics flag
                response = await client.post(
                    f"{VMETA_SERVICE_URL}/api/v1/mvr-people/count-by-videos",
                    json={"video_uuids": video_uuids, "include_demographics": True},
                    headers={"Authorization": f"Bearer {self.internal_token}"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Extract demographics if available
                    demographics = data.get("demographics", {})
                    
                    return {
                        "count": data.get("count", 0),
                        "video_count": data.get("video_count", 0),
                        "demographics": demographics
                    }
                else:
                    logger.error(f"VMeta count failed: {response.status_code}")
                    return {"count": 0, "video_count": 0, "demographics": {}}
                    
        except Exception as e:
            logger.error(f"Error counting MVR people: {e}")
            return {"count": 0, "video_count": 0, "demographics": {}}
```

**What Changes**:
1. ✅ Add Redis client to worker
2. ✅ Store MVR count data in trigger-friendly format
3. ✅ Use key pattern: `camera:mvr:{camera_id}:latest`
4. ✅ Include demographics in cached data
5. ✅ Set 5-minute TTL (auto-expires)

---

### Phase 2: Create Trigger Worker (3-4 hours)

**Location**: `ppl-meta-media/src/workers/trigger_worker.py` (NEW FILE)

```python
"""
Background worker that evaluates triggers using cached MVR data from Redis.

This worker is DECOUPLED from MVR data collection. It simply reads cached
counter data and evaluates triggers against it.
"""
import asyncio
import json
import logging
import redis
from datetime import datetime, timedelta
from typing import Dict, List
from sqlalchemy.orm import Session, joinedload

from ..models.trigger import Trigger
from ..models.user_trigger_action import UserTriggerAction
from ..services.trigger_evaluation import TriggerEvaluationService, CounterData
from ..database import SessionLocal

logger = logging.getLogger(__name__)


class TriggerWorker:
    """Background worker for automatic trigger execution using Redis cache."""
    
    def __init__(self, poll_interval: int = 60):
        """
        Initialize trigger worker.
        
        Args:
            poll_interval: Seconds between polls (default: 60)
                          Can be longer since we're reading from cache,
                          not hitting APIs/DB
        """
        self.poll_interval = poll_interval
        self.running = False
        self._camera_trigger_cache: Dict[str, List[str]] = {}
        self._last_execution: Dict[str, datetime] = {}  # trigger_uuid -> last_fired
        
        # Redis client for reading cached MVR data
        self.redis_client = redis.Redis(
            host='localhost',
            port=6379,
            db=0,
            decode_responses=True
        )
        
    async def start(self):
        """Start the background worker."""
        self.running = True
        logger.info("🚀 Trigger worker started (polling every %ds)", self.poll_interval)
        
        while self.running:
            try:
                await self._poll_and_execute()
            except Exception as e:
                logger.error(f"Error in trigger worker: {e}", exc_info=True)
            
            await asyncio.sleep(self.poll_interval)
    
    async def stop(self):
        """Stop the background worker."""
        self.running = False
        logger.info("🛑 Trigger worker stopped")
    
    def _refresh_camera_trigger_cache(self, db: Session):
        """
        Build map of camera_id -> active trigger UUIDs.
        
        Only includes triggers that are:
        - Active (is_active=true)
        - Linked to active user actions
        """
        triggers = db.query(Trigger).options(
            joinedload(Trigger.user_action)
        ).filter(
            Trigger.is_active == True
        ).all()
        
        camera_map: Dict[str, List[str]] = {}
        for trigger in triggers:
            # Skip if no action linked or action is inactive
            if not trigger.action_uuid:
                continue
            if trigger.user_action and not trigger.user_action.is_active:
                continue
            
            camera_id = trigger.camera_device_id
            if camera_id not in camera_map:
                camera_map[camera_id] = []
            camera_map[camera_id].append(str(trigger.uuid))
        
        self._camera_trigger_cache = camera_map
        logger.debug(f"📊 Trigger cache refreshed: {len(camera_map)} cameras with active triggers")
        return camera_map
    
    async def _poll_and_execute(self):
        """
        Main polling logic - reads Redis cache and evaluates triggers.
        
        DECOUPLED: Only reads cached data, doesn't fetch from API/DB.
        """
        db = SessionLocal()
        try:
            # Refresh cache of which cameras have active triggers
            camera_triggers = self._refresh_camera_trigger_cache(db)
            
            if not camera_triggers:
                logger.debug("No cameras with active triggers, skipping poll")
                return
            
            # Evaluate triggers for each camera that has cached data
            for camera_id in camera_triggers.keys():
                try:
                    await self._evaluate_camera_triggers(camera_id, db)
                except Exception as e:
                    logger.error(f"Error evaluating triggers for {camera_id}: {e}")
        
        finally:
            db.close()
    
    async def _evaluate_camera_triggers(self, camera_id: str, db: Session):
        """
        Fetch cached counter data for camera and evaluate all its triggers.
        
        UPDATED: Now reads from Redis cache instead of hitting API.
        
        Args:
            camera_id: Camera device ID
            db: Database session
        """
        # Read from Redis cache
        cache_key = f"camera:mvr:{camera_id}:latest"
        
        try:
            cached_data = self.redis_client.get(cache_key)
            
            if not cached_data:
                logger.debug(f"No cached data for {camera_id} (camera not recording or cache expired)")
                return
            
            # Parse cached JSON
            data = json.loads(cached_data)
            
            # Build CounterData object
            counter_data = CounterData(
                camera_device_id=camera_id,
                total_count=data.get("total_count", 0),
                age_distribution=data.get("age_distribution", {}),
                gender_distribution=data.get("gender_distribution", {}),
                timestamp=datetime.fromisoformat(data.get("cached_at"))
            )
            
            logger.debug(
                f"📊 Loaded cached data for {camera_id}: "
                f"{counter_data.total_count} people"
            )
            
        except Exception as e:
            logger.error(f"Failed to read cache for {camera_id}: {e}")
            return
        
        # Evaluate triggers (rest of logic unchanged)
        evaluation_service = TriggerEvaluationService(db)
        results = evaluation_service.evaluate_all_active_triggers(counter_data)
        
        # Execute actions for passed triggers
        for trigger, passed, reason in results:
            if passed:
                await self._execute_trigger_action(trigger, counter_data, reason, db)
    
    async def _fetch_camera_counter(self, camera_id: str) -> CounterData:
        """
        DEPRECATED: Replaced by reading from Redis cache.
        
        Previously fetched from API, now reads from cache in _evaluate_camera_triggers.
        """
        # This method is no longer used - keeping for reference
        pass
    
    async def _execute_trigger_action(
        self,
        trigger: Trigger,
        counter_data: CounterData,
        reason: str,
        db: Session
    ):
        """
        Execute the user action linked to this trigger.
        
        Args:
            trigger: Trigger that passed evaluation
            counter_data: Counter data that caused trigger
            reason: Human-readable reason for trigger passing
            db: Database session
        """
        # Check cooldown - don't fire same trigger twice within 5 minutes
        trigger_uuid = str(trigger.uuid)
        last_fired = self._last_execution.get(trigger_uuid)
        if last_fired and (datetime.utcnow() - last_fired).seconds < 300:  # 5 minutes
            logger.debug(f"Trigger {trigger.name} in cooldown, skipping")
            return
        
        # Load user action
        if not trigger.user_action:
            logger.warning(f"Trigger {trigger.name} has no linked action")
            return
        
        action = trigger.user_action
        
        logger.info(
            f"🔥 EXECUTING TRIGGER: {trigger.name} → {action.name} ({action.action_type}) | Reason: {reason}"
        )
        
        # Execute based on action type
        try:
            if action.action_type == "alert":
                await self._execute_alert_action(trigger, action, counter_data, reason, db)
            elif action.action_type == "email":
                await self._execute_email_action(trigger, action, counter_data, reason, db)
            elif action.action_type == "webhook":
                await self._execute_webhook_action(trigger, action, counter_data, reason, db)
            elif action.action_type == "log":
                await self._execute_log_action(trigger, action, counter_data, reason, db)
            else:
                logger.warning(f"Unknown action type: {action.action_type}")
            
            # Update last execution time
            self._last_execution[trigger_uuid] = datetime.utcnow()
            
        except Exception as e:
            logger.error(f"Failed to execute action {action.name}: {e}", exc_info=True)
    
    async def _execute_alert_action(
        self, trigger: Trigger, action: UserTriggerAction,
        counter_data: CounterData, reason: str, db: Session
    ):
        """Execute alert action - store in-app notification."""
        # TODO: Implement notification storage
        # Could create a notifications table or use existing system
        logger.info(f"📢 ALERT: {action.name} | {reason}")
        # Example: db.add(Notification(user_id=..., message=reason, ...))
    
    async def _execute_email_action(
        self, trigger: Trigger, action: UserTriggerAction,
        counter_data: CounterData, reason: str, db: Session
    ):
        """Execute email action - send email notification."""
        import json
        
        # Parse action_config for email details
        config = json.loads(action.action_config) if action.action_config else {}
        recipients = config.get("recipients", [])
        subject = config.get("subject", f"Trigger Alert: {trigger.name}")
        body_template = config.get("body", "Trigger {trigger_name} fired: {reason}")
        
        body = body_template.format(
            trigger_name=trigger.name,
            reason=reason,
            camera=trigger.camera_name or trigger.camera_device_id,
            count=counter_data.total_count,
            timestamp=counter_data.timestamp.isoformat()
        )
        
        # TODO: Implement email sending
        logger.info(f"📧 EMAIL: {recipients} | Subject: {subject}")
        # Example: await send_email(recipients, subject, body)
    
    async def _execute_webhook_action(
        self, trigger: Trigger, action: UserTriggerAction,
        counter_data: CounterData, reason: str, db: Session
    ):
        """Execute webhook action - HTTP POST to configured URL."""
        import json
        import httpx
        
        config = json.loads(action.action_config) if action.action_config else {}
        url = config.get("url")
        method = config.get("method", "POST")
        headers = config.get("headers", {})
        
        if not url:
            logger.warning(f"Webhook action {action.name} has no URL configured")
            return
        
        payload = {
            "trigger_uuid": str(trigger.uuid),
            "trigger_name": trigger.name,
            "action_name": action.name,
            "reason": reason,
            "camera_device_id": trigger.camera_device_id,
            "camera_name": trigger.camera_name,
            "counter_data": {
                "total_count": counter_data.total_count,
                "age_distribution": counter_data.age_distribution,
                "gender_distribution": counter_data.gender_distribution
            },
            "timestamp": counter_data.timestamp.isoformat()
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    json=payload,
                    headers=headers
                )
                logger.info(f"🌐 WEBHOOK: {url} | Status: {response.status_code}")
        except Exception as e:
            logger.error(f"Webhook failed: {e}")
    
    async def _execute_log_action(
        self, trigger: Trigger, action: UserTriggerAction,
        counter_data: CounterData, reason: str, db: Session
    ):
        """Execute log action - write to database execution log."""
        # TODO: Create trigger_executions table
        logger.info(f"📝 LOG: {action.name} | {reason}")
        # Example: db.add(TriggerExecution(trigger_id=..., reason=reason, ...))
```

---

### Phase 3: Database Schema for Execution Logs (1 hour)

**Migration**: `add_trigger_execution_logs.py`

```sql
CREATE TABLE trigger_executions (
    id SERIAL PRIMARY KEY,
    uuid UUID UNIQUE NOT NULL DEFAULT uuid_generate_v4(),
    
    -- References
    trigger_uuid UUID NOT NULL REFERENCES triggers(uuid) ON DELETE CASCADE,
    action_uuid UUID NOT NULL REFERENCES user_trigger_actions(uuid) ON DELETE CASCADE,
    
    -- Execution details
    executed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    reason TEXT NOT NULL,  -- Human-readable reason trigger passed
    counter_data JSONB,  -- Snapshot of counter data that triggered it
    
    -- Result
    success BOOLEAN NOT NULL DEFAULT true,
    error_message TEXT,  -- If execution failed
    
    -- Metadata
    camera_device_id VARCHAR(255) NOT NULL,
    person_count INTEGER,
    
    INDEX idx_trigger_exec_trigger_uuid (trigger_uuid),
    INDEX idx_trigger_exec_executed_at (executed_at),
    INDEX idx_trigger_exec_camera (camera_device_id)
);
```

---

### Phase 4: Integration with Services (1 hour)

**ppl-meta-gateway/src/main.py** (MVR Cache Worker - already integrated!)
```python
# Worker already exists and runs - just need to enhance with Redis caching
# No integration changes needed, just modify worker code
```

**ppl-meta-media/src/main.py** (Trigger Worker - NEW)

```python
from contextlib import asynccontextmanager
from .workers.trigger_worker import TriggerWorker

# Global worker instance
trigger_worker = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - start/stop background workers."""
    global trigger_worker
    
    # Startup
    trigger_worker = TriggerWorker(poll_interval=30)  # 30 seconds
    asyncio.create_task(trigger_worker.start())
    logger.info("✅ Trigger worker started")
    
    yield
    
    # Shutdown
    if trigger_worker:
        await trigger_worker.stop()
        logger.info("✅ Trigger worker stopped")

app = FastAPI(
    title="PPL Meta Media Service",
    lifespan=lifespan  # Add lifespan manager
)
```

---

### Phase 4: Monitoring & Observability (1-2 hours)

**Metrics to Track**:
- `triggers_evaluated_total` - Counter of trigger evaluations
- `triggers_passed_total` - Counter of triggers that passed
- `trigger_actions_executed_total` - Counter by action type
- `trigger_execution_duration_seconds` - Histogram of execution time
- `trigger_errors_total` - Counter of execution failures

**Dashboard Queries**:
```sql
-- Most frequently triggered
SELECT t.name, COUNT(*) as fire_count
FROM trigger_executions te
JOIN triggers t ON t.uuid = te.trigger_uuid
WHERE te.executed_at > NOW() - INTERVAL '24 hours'
GROUP BY t.name
ORDER BY fire_count DESC
LIMIT 10;

-- Failed executions
SELECT t.name, te.executed_at, te.error_message
FROM trigger_executions te
JOIN triggers t ON t.uuid = te.trigger_uuid
WHERE te.success = false
ORDER BY te.executed_at DESC
LIMIT 20;

-- Trigger performance
SELECT 
    t.name,
    COUNT(*) as total_evaluations,
    SUM(CASE WHEN te.success THEN 1 ELSE 0 END) as successful,
    AVG(EXTRACT(EPOCH FROM (te.executed_at - te.executed_at))) as avg_duration_seconds
FROM trigger_executions te
JOIN triggers t ON t.uuid = te.trigger_uuid
WHERE te.executed_at > NOW() - INTERVAL '7 days'
GROUP BY t.name;
```

---

## Testing Strategy

### Unit Tests

```python
# tests/test_trigger_worker.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from workers.trigger_worker import TriggerWorker

@pytest.mark.asyncio
async def test_trigger_worker_evaluates_active_cameras():
    worker = TriggerWorker(poll_interval=10)
    worker._fetch_camera_counter = AsyncMock(return_value=CounterData(...))
    
    # Mock database with active triggers
    db = MagicMock()
    # ... setup mocks
    
    await worker._poll_and_execute()
    
    # Assert camera counter was fetched
    # Assert triggers were evaluated
    # Assert actions were executed

@pytest.mark.asyncio
async def test_cooldown_prevents_spam():
    worker = TriggerWorker(poll_interval=10)
    
    trigger = MagicMock(uuid="test-uuid", name="Test Trigger")
    counter_data = CounterData(...)
    
    # First execution should work
    await worker._execute_trigger_action(trigger, counter_data, "test", db)
    assert trigger.uuid in worker._last_execution
    
    # Second execution within 5 minutes should skip
    await worker._execute_trigger_action(trigger, counter_data, "test", db)
    # Assert action not executed twice
```

### Integration Tests

```bash
# 1. Create test trigger with test action
curl -X POST http://localhost:8000/api/v1/triggers \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "name": "Test High Traffic",
    "person_count_operator": "more_than",
    "person_count_value": "5",
    "camera_device_id": "usb_camera_0",
    "action_uuid": "test-action-uuid",
    "tracking_duration": "1 hour",
    "is_active": true
  }'

# 2. Simulate camera activity (record video with 10 people)

# 3. Wait for poll cycle (30 seconds)

# 4. Check execution logs
curl http://localhost:8000/api/v1/trigger-executions?page=1

# Expected: Trigger should have fired and action executed
```

---

## Configuration

**Environment Variables**:

```bash
# ppl-meta-media/.env

# Trigger Worker Settings
TRIGGER_WORKER_ENABLED=true  # Enable/disable worker
TRIGGER_WORKER_POLL_INTERVAL=30  # Seconds between polls
TRIGGER_WORKER_COOLDOWN=300  # Seconds cooldown between same trigger fires

# Camera Counter API
CAMERA_COUNTER_ENDPOINT=http://localhost:8080/api/v1/cameras
CAMERA_COUNTER_TIMEOUT=10  # HTTP timeout in seconds

# Email Settings (for email actions)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=noreply@pplmeta.com
```

---

## Security Considerations

1. **Webhook Validation**: 
   - Only allow HTTPS webhooks in production
   - Validate webhook URLs against allowlist
   - Add HMAC signatures to webhook payloads

2. **Email Rate Limiting**:
   - Limit email actions to X per hour per user
   - Implement global rate limit for SMTP

3. **Action Permissions**:
   - Verify user has permission to execute action
   - Log all action executions for audit trail

4. **Sensitive Data**:
   - Don't include full counter_data in webhook payloads unless needed
   - Sanitize error messages in execution logs

---

## Migration Path

### Phase 1 (Current): Manual Evaluation ✅
- Triggers exist, manually call evaluate endpoint
- **Status**: COMPLETE

### Phase 2 (Next 1-2 weeks): Polling Worker 🚀
- Implement TriggerWorker with basic polling
- Add execution logs table
- Support alert and log actions
- **Estimated Effort**: 5-6 hours

### Phase 3 (Future): Email & Webhook Actions
- Implement email sending
- Implement webhook HTTP calls
- Add retry logic for failed actions
- **Estimated Effort**: 3-4 hours

### Phase 4 (Future): Event-Driven Migration
- Add message queue (Redis Pub/Sub)
- Modify vision service to publish events
- Replace polling with event consumption
- **Estimated Effort**: 8-12 hours

---

## Success Metrics

**Week 1** (Polling Worker):
- ✅ Worker successfully polls cameras with active triggers
- ✅ Triggers evaluate against real counter data
- ✅ Alert actions store notifications
- ✅ Execution logs capture trigger history

**Week 2** (Actions):
- ✅ Email actions send to configured recipients
- ✅ Webhook actions POST to external URLs
- ✅ <5% action execution failure rate
- ✅ Average execution time < 2 seconds

**Month 1** (Stability):
- ✅ Worker runs 24/7 without crashes
- ✅ <1% false positive trigger rate
- ✅ Users report triggers are useful
- ✅ Performance metrics dashboard operational

---

## Open Questions

1. **Cooldown Duration**: Should cooldown be configurable per trigger? (Currently hardcoded 5 minutes)

2. **Tracking Duration Interpretation**: Should we fetch counter data for the longest tracking_duration among all triggers for a camera, or fetch separately per trigger?

3. **Action Retry Logic**: Should failed webhook/email actions retry? With exponential backoff?

4. **Notification Storage**: Where should alert-type notifications be stored? New table or use existing notification system?

5. **Multi-Tenant**: Do we need per-user action execution limits/quotas?

---

## Conclusion

**Recommended Approach**: Implement **Option 3 (Hybrid Smart Polling)** as it provides:
- ✅ Fastest time to value (5-6 hours implementation)
- ✅ Works with existing infrastructure
- ✅ Respects tracking_duration design
- ✅ Scalable to event-driven later

**Next Steps**:
1. Review and approve architecture proposal
2. Create development branch `feature/trigger-worker`
3. Implement TriggerWorker class (Phase 1)
4. Add execution logs migration (Phase 2)
5. Integrate with Media service startup (Phase 3)
6. Test with real camera data
7. Deploy to staging for validation

**Timeline**: 1-2 weeks for full implementation including testing and monitoring.

---

**Document Status**: ✅ READY FOR REVIEW  
**Author**: GitHub Copilot  
**Reviewer**: awaiting review  
**Approved**: pending
