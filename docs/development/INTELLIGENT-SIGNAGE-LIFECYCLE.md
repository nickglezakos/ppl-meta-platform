# Intelligent Signage Lifecycle - Real-Time Demographic Content Delivery

**Document Purpose**: Complete architecture and implementation guide for connecting instant face detection to digital signage triggers for demographic-based content switching.

**Last Updated**: December 13, 2025

---

## Use Case

Enable real-time demographic-based content delivery to digital signage displays. When a camera detects certain demographic profiles (e.g., predominantly male audience, young viewers, etc.), automatically switch the displayed content to relevant playlists or videos.

**Example Scenarios**:
- 👨 **>60% male audience** → Show men's product advertisements
- 👩 **>70% female audience** → Show women's fashion content  
- 🧒 **>50% young viewers** → Display youth-targeted content
- 👔 **>80% adult audience** → Show professional/luxury products
- 👥 **Multiple people detected** → Switch from idle to active content

---

## Architecture Overview

**Integration Note**: This system integrates with the **existing PPL Meta Signage Management System** (documented in `ppl-meta-signage.md`). The trigger actions call existing signage endpoints - no new signage infrastructure required.

```
Camera Instant Detection (Backend)
  ↓ [Real-time push every 5s]
Media Service Trigger System (NEW)
  ↓ [Evaluate demographic conditions]
Trigger Action
  ↓ [Calls EXISTING signage API]
Media Service Signage Endpoints (EXISTING)
  ↓ [Routes to registered devices]
Digital Signage Android Player (EXISTING)
  ↓ [Executes playlist switch]
```

## Complete Flow Diagram

**Data Flow Mechanism**: **Webhook PUSH** (not polling)

The camera service **actively sends** demographic data to the media service every 5 seconds. The media service does NOT poll the camera - it receives data via HTTP POST webhook.

```
┌─────────────────────────────────────────────────────────────┐
│ ppl-meta-cameras (Port 8005)                                │
│                                                              │
│  Instant Detection Loop (every 5s)                          │
│    ├─ Detect faces                                          │
│    ├─ Calculate demographics                                │
│    ├─ Update memory cache                                   │
│    └─ PUSH via HTTP POST to webhook ◄──── PUSH NOT POLL    │
│         asyncio.create_task(_push_to_webhook())             │
│         {                                                    │
│           "camera_id": "usb_camera_0",                      │
│           "timestamp": "2025-12-13T10:30:00",               │
│           "people_count": 3,                                │
│           "demographics": {                                  │
│             "percent_male": 67,                             │
│             "percent_female": 33,                           │
│             "percent_young": 0,                             │
│             "percent_adult": 100                            │
│           }                                                  │
│         }                                                    │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP POST (async, non-blocking)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ ppl-meta-media (Port 8000)                                  │
│                                                              │
│  POST /api/v1/triggers/instant-detection ◄──── NEW         │
│    ├─ RECEIVE webhook (FastAPI endpoint)                   │
│    ├─ Find matching triggers                                │
│    │    Example: "IF percent_male > 60 THEN..."           │
│    ├─ Evaluate conditions (AND logic)                       │
│    ├─ Check cooldown (don't spam)                          │
│    └─ Execute actions if triggered                          │
│         └─ Call EXISTING Signage API ▼                      │
│                                                              │
│  POST /api/v1/signage/playback/start ◄──── EXISTING        │
│    ├─ Receive device_ids + playlist_id                      │
│    ├─ Route to registered devices                           │
│    └─ Send control command to device                        │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP POST (via discovery routing)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ Digital Signage Android Player (Port 8080) ◄── EXISTING    │
│                                                              │
│  POST /api/v1/control                                       │
│    ├─ Receive playlist_id and action                        │
│    ├─ Stop current video (if playing)                       │
│    └─ Start new playlist                                    │
└─────────────────────────────────────────────────────────────┘
```

---

## How It Works: Webhook Push Mechanism

### Question: How does the trigger "know" the demographic values?

**Answer**: The camera service **actively pushes** data to the media service via HTTP POST webhook. This is **NOT polling**.

### Detailed Flow:

**1. Camera Service (Every 5 seconds)**
```python
# In instant detection loop
async def update_instant_detection_cache(camera_id, results):
    # Update local cache
    self._cache[camera_id] = results
    
    # PUSH to webhook (async, non-blocking)
    if self.webhook_enabled:
        asyncio.create_task(self._push_to_webhook(camera_id, results))
        # ↑ This fires HTTP POST immediately, doesn't wait
```

**2. Media Service (Receives webhook)**
```python
# FastAPI endpoint - receives incoming POST requests
@router.post("/api/v1/triggers/instant-detection")
async def process_instant_detection_webhook(payload: InstantDetectionPayload):
    # Called automatically when camera POSTs data
    # Evaluate triggers synchronously
    # Execute actions if conditions met
```

**3. Execution Timeline with Cooldown**
```
T=0s:    Camera detects (67% male), POSTs webhook
         → Trigger evaluates → Conditions met → ACTION FIRES ✅
         → Signage switches to men's playlist
         → Cooldown starts (60s)

T=5s:    Camera detects, POSTs webhook
         → Trigger evaluates → Cooldown active → SKIP ❌

T=10s:   Camera detects, POSTs webhook
         → Cooldown active → SKIP ❌

T=15s:   Camera detects, POSTs webhook
         → Cooldown active → SKIP ❌
         
... [webhooks continue every 5s, all skipped due to cooldown]

T=60s:   Camera detects, POSTs webhook
         → Cooldown active (60s not yet expired) → SKIP ❌

T=65s:   Camera detects (still 67% male), POSTs webhook
         → Cooldown expired → Conditions still met → ACTION FIRES ✅
         → Cooldown resets (60s)

T=70s:   Camera detects, POSTs webhook
         → Cooldown active → SKIP ❌
```

**Visual Timeline**:
```
Webhooks: ↓    ↓    ↓    ↓    ↓    ↓    ↓    ↓    ↓    ↓    ↓    ↓    ↓    ↓
Time:     0s   5s   10s  15s  20s  25s  30s  35s  40s  45s  50s  55s  60s  65s
Actions:  🎬   ❌   ❌   ❌   ❌   ❌   ❌   ❌   ❌   ❌   ❌   ❌   ❌   🎬
          |                                                           |
          Trigger fires (playlist switch)                             Fires again
          Cooldown starts (60s)                                       Cooldown resets
```

**Key Clarification**: 
- 📡 **Webhooks arrive**: Every **5 seconds** (constant)
- 🎬 **Actions execute**: Only when cooldown expired (every **60+ seconds**)
- ⏱️ **Cooldown purpose**: Prevent playlist switching every 5 seconds (viewer disruption)

### Key Points:

✅ **Push, not Poll**: Camera actively sends data (HTTP POST)  
✅ **Async/Non-blocking**: Webhook call doesn't slow detection (`asyncio.create_task`)  
✅ **Real-time**: ~350ms total latency from detection to signage switch  
✅ **Cooldown**: Prevents spam (configurable per trigger, default 30-60s)  
✅ **Webhooks always sent**: Every 5s regardless of cooldown state  
✅ **Fire-and-forget**: If webhook fails, detection continues normally  

### Why Webhook Push vs Polling?

**Webhook Push (Used Here)**:
- ✅ Real-time: Immediate notification when data changes
- ✅ Efficient: No unnecessary requests when nothing changes
- ✅ Scalable: Camera controls data flow
- ✅ Lower latency: ~350ms vs 1-5 seconds with polling

**Polling (NOT used)**:
- ❌ Delayed: Media service checks every X seconds
- ❌ Inefficient: Wastes resources checking unchanged data
- ❌ Higher load: Constant requests even when idle
- ❌ Higher latency: Average delay = poll_interval / 2

---

## Implementation Components

### Component 1: Camera Service Webhook Push

**Location**: `ppl-meta-cameras/src/services/instant_detection.py`

**Purpose**: Push instant detection results to media service in real-time via webhook

**Implementation**:

```python
# ppl-meta-cameras/src/services/instant_detection.py

import httpx
from typing import Optional, Dict, Any
import asyncio
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class InstantDetectionService:
    def __init__(self):
        self.webhook_url: Optional[str] = None
        self.webhook_enabled: bool = False
        self._http_client = httpx.AsyncClient(timeout=5.0)
    
    def configure_webhook(self, url: str, enabled: bool = True):
        """Configure webhook for pushing instant detection results"""
        self.webhook_url = url
        self.webhook_enabled = enabled
        logger.info(f"Instant detection webhook configured: {url} (enabled: {enabled})")
    
    async def _push_to_webhook(self, camera_id: str, results: Dict[str, Any]):
        """Push instant detection results to configured webhook"""
        if not self.webhook_enabled or not self.webhook_url:
            return
        
        try:
            payload = {
                "camera_id": camera_id,
                "timestamp": datetime.utcnow().isoformat(),
                "people_count": len(results.get("person_objects", [])),
                "demographics": results.get("demographics", {}),
                "metadata": {
                    "iteration": results.get("_metadata", {}).get("iteration"),
                    "age_seconds": results.get("_metadata", {}).get("age_seconds"),
                }
            }
            
            response = await self._http_client.post(
                self.webhook_url,
                json=payload,
                timeout=2.0  # Short timeout, don't block detection
            )
            
            if response.status_code == 200:
                logger.debug(f"✅ Pushed instant detection to webhook: {camera_id}")
            else:
                logger.warning(f"⚠️ Webhook returned {response.status_code} for {camera_id}")
                
        except Exception as e:
            logger.error(f"❌ Failed to push to webhook: {e}")
            # Don't fail detection if webhook fails
    
    async def update_instant_detection_cache(self, camera_id: str, results: Dict[str, Any]):
        """Update cache AND push to webhook if configured"""
        # Existing cache update logic
        self._cache[camera_id] = results
        
        # NEW: Push to webhook asynchronously
        if self.webhook_enabled:
            asyncio.create_task(self._push_to_webhook(camera_id, results))
```

**Key Features**:
- ✅ Non-blocking async webhook calls
- ✅ Short timeout (2s) to avoid detection delays
- ✅ Error handling - webhook failures don't break detection
- ✅ Configurable enable/disable
- ✅ Detailed logging for debugging

---

### Component 2: Webhook Configuration Endpoint

**Location**: `ppl-meta-cameras/src/api/v1/endpoints/instant_detection.py`

**Purpose**: API endpoint to configure webhook URL

**Implementation**:

```python
# ppl-meta-cameras/src/api/v1/endpoints/instant_detection.py

from fastapi import APIRouter, Depends
from pydantic import BaseModel, HttpUrl

router = APIRouter()

class WebhookConfig(BaseModel):
    url: HttpUrl
    enabled: bool = True

@router.post("/api/v1/instant-detection/webhook/configure")
async def configure_instant_detection_webhook(
    config: WebhookConfig,
    instant_detection: InstantDetectionService = Depends(get_instant_detection_service)
):
    """
    Configure webhook URL for instant detection results push.
    
    Use case: Real-time demographic triggers for digital signage
    
    Example:
        POST /api/v1/instant-detection/webhook/configure
        {
            "url": "http://localhost:8000/api/v1/triggers/instant-detection",
            "enabled": true
        }
    """
    instant_detection.configure_webhook(
        url=str(config.url),
        enabled=config.enabled
    )
    
    return {
        "success": True,
        "message": "Instant detection webhook configured",
        "webhook_url": str(config.url),
        "enabled": config.enabled
    }

@router.get("/api/v1/instant-detection/webhook/status")
async def get_webhook_status(
    instant_detection: InstantDetectionService = Depends(get_instant_detection_service)
):
    """Get current webhook configuration status"""
    return {
        "enabled": instant_detection.webhook_enabled,
        "url": instant_detection.webhook_url
    }
```

**Endpoints**:
- `POST /api/v1/instant-detection/webhook/configure` - Set webhook URL
- `GET /api/v1/instant-detection/webhook/status` - Check configuration

---

### Component 3: Media Service Trigger System

**Location**: `ppl-meta-media/src/api/v1/endpoints/triggers.py`

**Purpose**: Receive demographics, evaluate conditions, execute actions

**Data Models**:

```python
from pydantic import BaseModel
from typing import Dict, Any, List

class InstantDetectionPayload(BaseModel):
    """Payload received from camera service"""
    camera_id: str
    timestamp: str
    people_count: int
    demographics: Dict[str, Any]
    metadata: Dict[str, Any] = {}

class TriggerCondition(BaseModel):
    """Trigger condition for demographic-based actions"""
    field: str  # e.g., "percent_male", "percent_female", "percent_young", "people_count"
    operator: str  # "gt", "lt", "gte", "lte", "eq"
    value: float
    
    # Examples:
    # {"field": "percent_male", "operator": "gte", "value": 60}
    # {"field": "people_count", "operator": "gte", "value": 2}
    # {"field": "percent_young", "operator": "gt", "value": 50}

class TriggerAction(BaseModel):
    """Action to execute when trigger fires"""
    type: str  # "signage_playback", "http_call", "webhook"
    device_ids: List[str]  # Target signage device IDs (from discovery service)
    video_list_id: str  # Playlist UUID from existing signage system
    start_index: int = 0  # Optional: Start at specific video index
    volume: int = 80  # Optional: Set volume (0-100)
    transition_mode: str = "immediate"  # "immediate", "after_current", "fade"
    fade_duration_ms: int = 2000  # Only used if transition_mode="fade"
    
    # Example - Uses EXISTING /api/v1/signage/playback/start endpoint:
    # {
    #   "type": "signage_playback",
    #   "device_ids": ["device-uuid-from-discovery"],
    #   "video_list_id": "playlist-uuid-mens-products",
    #   "start_index": 0,
    #   "volume": 80,
    #   "transition_mode": "after_current",  // User decides transition behavior
    #   "fade_duration_ms": 2000
    # }

class DemographicTrigger(BaseModel):
    """Complete trigger configuration"""
    name: str
    description: str = ""
    camera_ids: List[str]  # Which cameras trigger this
    conditions: List[TriggerCondition]  # AND logic - all must be true
    actions: List[TriggerAction]  # All executed if conditions met
    enabled: bool = True
    cooldown_seconds: int = 30  # Don't fire more than once per X seconds
```

**Main Webhook Endpoint**:

```python
# ppl-meta-media/src/api/v1/endpoints/triggers.py

from fastapi import APIRouter, HTTPException
import httpx
from datetime import datetime
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# In-memory trigger storage (replace with database in production)
TRIGGERS: Dict[str, DemographicTrigger] = {}
LAST_TRIGGERED: Dict[str, datetime] = {}

@router.post("/api/v1/triggers/instant-detection")
async def process_instant_detection_webhook(payload: InstantDetectionPayload):
    """
    Receive instant detection results and evaluate triggers.
    Called by ppl-meta-cameras service every 5 seconds.
    
    Flow:
    1. Find triggers matching the camera
    2. Check cooldown period
    3. Evaluate conditions (AND logic)
    4. Execute actions if all conditions met
    5. Return results
    """
    logger.info(f"📡 Received instant detection: {payload.camera_id} - {payload.people_count} people")
    
    # Find triggers matching this camera
    matching_triggers = [
        trigger for trigger in TRIGGERS.values()
        if trigger.enabled and payload.camera_id in trigger.camera_ids
    ]
    
    if not matching_triggers:
        return {"message": "No triggers configured for this camera", "triggered": []}
    
    triggered_actions = []
    
    for trigger in matching_triggers:
        # Check cooldown
        last_trigger_time = LAST_TRIGGERED.get(trigger.name)
        if last_trigger_time:
            time_since_trigger = (datetime.utcnow() - last_trigger_time).total_seconds()
            if time_since_trigger < trigger.cooldown_seconds:
                logger.debug(f"⏱️ Trigger {trigger.name} in cooldown ({time_since_trigger:.1f}s)")
                continue
        
        # Evaluate conditions (AND logic)
        conditions_met = True
        for condition in trigger.conditions:
            actual_value = payload.demographics.get(condition.field)
            if actual_value is None:
                if condition.field == "people_count":
                    actual_value = payload.people_count
                else:
                    conditions_met = False
                    break
            
            # Evaluate operator
            if condition.operator == "gt" and not (actual_value > condition.value):
                conditions_met = False
                break
            elif condition.operator == "gte" and not (actual_value >= condition.value):
                conditions_met = False
                break
            elif condition.operator == "lt" and not (actual_value < condition.value):
                conditions_met = False
                break
            elif condition.operator == "lte" and not (actual_value <= condition.value):
                conditions_met = False
                break
            elif condition.operator == "eq" and not (actual_value == condition.value):
                conditions_met = False
                break
        
        # Execute actions if conditions met
        if conditions_met:
            logger.info(f"🎯 Trigger fired: {trigger.name}")
            LAST_TRIGGERED[trigger.name] = datetime.utcnow()
            
            for action in trigger.actions:
                try:
                    await _execute_action(action, payload)
                    triggered_actions.append({
                        "trigger_name": trigger.name,
                        "action_type": action.type,
                        "device_ids": action.device_ids,
                        "success": True
                    })
                    logger.info(f"✅ Action executed successfully: {action.type}")
                except Exception as e:
                    logger.error(f"❌ Failed to execute action: {e}")
                    triggered_actions.append({
                        "trigger_name": trigger.name,
                        "action_type": action.type,
                        "device_ids": action.device_ids,
                        "success": False,
                        "error": str(e)
                    })
    
    return {
        "camera_id": payload.camera_id,
        "timestamp": payload.timestamp,
        "triggers_evaluated": len(matching_triggers),
        "triggered": triggered_actions
    }

async def _execute_action(action: TriggerAction, context: InstantDetectionPayload):
    """Execute a trigger action using EXISTING signage infrastructure"""
    async with httpx.AsyncClient(timeout=10.0) as client:
        if action.type == "signage_playback":
            # Use EXISTING /api/v1/signage/playback/start endpoint
            # This integrates with existing signage management system
            payload = {
                "device_ids": action.device_ids,
                "video_list_id": action.video_list_id,
                "start_index": action.start_index,
                "volume": action.volume,
                "transition_mode": action.transition_mode,  # Pass to signage API
                "fade_duration_ms": action.fade_duration_ms,  # For fade transitions
                "_trigger_context": {  # Optional metadata
                    "camera_id": context.camera_id,
                    "timestamp": context.timestamp,
                    "demographics": context.demographics
                }
            }
                "_trigger_context": {  # Optional metadata
                    "camera_id": context.camera_id,
                    "timestamp": context.timestamp,
                    "demographics": context.demographics
                }
            }
            
            # Call existing signage API (same service, port 8000)
            response = await client.post(
                "http://localhost:8000/api/v1/signage/playback/start",
                json=payload
            )
        
        elif action.type == "http_call":
            # Generic HTTP call for custom integrations
            response = await client.post(
                action.endpoint,
                json=action.payload
            )
        
        else:
            raise ValueError(f"Unsupported action type: {action.type}")
        
        response.raise_for_status()
        logger.info(f"✅ Action executed: {action.type} -> {response.status_code}")
        return response.json()
        
        response.raise_for_status()
        logger.info(f"✅ Action executed: {action.endpoint} -> {response.status_code}")
        return response.json()
```

---

### Component 4: Trigger Management Endpoints

**CRUD operations for managing triggers**:

```python
# ppl-meta-media/src/api/v1/endpoints/triggers.py (continued)

@router.post("/api/v1/triggers/demographic")
async def create_demographic_trigger(trigger: DemographicTrigger):
    """
    Create a new demographic trigger
    
    Example:
        POST /api/v1/triggers/demographic
        {
            "name": "male_dominant_audience",
            "description": "Switch to men's products when >60% male",
            "camera_ids": ["usb_camera_0"],
            "conditions": [
                {"field": "percent_male", "operator": "gte", "value": 60},
                {"field": "people_count", "operator": "gte", "value": 1}
            ],
            "actions": [{
                "type": "signage_playlist",
                "endpoint": "http://192.168.1.100:8080/api/v1/playlist/switch",
                "method": "POST",
                "payload": {"playlist_id": "mens_products_2024"}
            }],
            "enabled": true,
            "cooldown_seconds": 60
        }
    """
    if trigger.name in TRIGGERS:
        raise HTTPException(status_code=400, detail="Trigger already exists")
    
    TRIGGERS[trigger.name] = trigger
    logger.info(f"✅ Trigger created: {trigger.name}")
    return {"success": True, "trigger": trigger}

@router.get("/api/v1/triggers/demographic")
async def list_demographic_triggers():
    """List all configured triggers"""
    return {"triggers": list(TRIGGERS.values())}

@router.get("/api/v1/triggers/demographic/{trigger_name}")
async def get_demographic_trigger(trigger_name: str):
    """Get specific trigger configuration"""
    if trigger_name not in TRIGGERS:
        raise HTTPException(status_code=404, detail="Trigger not found")
    return {"trigger": TRIGGERS[trigger_name]}

@router.put("/api/v1/triggers/demographic/{trigger_name}")
async def update_demographic_trigger(trigger_name: str, trigger: DemographicTrigger):
    """Update existing trigger"""
    if trigger_name not in TRIGGERS:
        raise HTTPException(status_code=404, detail="Trigger not found")
    
    TRIGGERS[trigger_name] = trigger
    logger.info(f"🔄 Trigger updated: {trigger_name}")
    return {"success": True, "trigger": trigger}

@router.delete("/api/v1/triggers/demographic/{trigger_name}")
async def delete_demographic_trigger(trigger_name: str):
    """Delete trigger"""
    if trigger_name not in TRIGGERS:
        raise HTTPException(status_code=404, detail="Trigger not found")
    
    del TRIGGERS[trigger_name]
    if trigger_name in LAST_TRIGGERED:
        del LAST_TRIGGERED[trigger_name]
    
    logger.info(f"🗑️ Trigger deleted: {trigger_name}")
    return {"success": True, "message": "Trigger deleted"}

@router.post("/api/v1/triggers/demographic/{trigger_name}/enable")
async def enable_trigger(trigger_name: str):
    """Enable trigger"""
    if trigger_name not in TRIGGERS:
        raise HTTPException(status_code=404, detail="Trigger not found")
    
    TRIGGERS[trigger_name].enabled = True
    logger.info(f"✅ Trigger enabled: {trigger_name}")
    return {"success": True, "enabled": True}

@router.post("/api/v1/triggers/demographic/{trigger_name}/disable")
async def disable_trigger(trigger_name: str):
    """Disable trigger"""
    if trigger_name not in TRIGGERS:
        raise HTTPException(status_code=404, detail="Trigger not found")
    
    TRIGGERS[trigger_name].enabled = False
    logger.info(f"⏸️ Trigger disabled: {trigger_name}")
    return {"success": True, "enabled": False}
```

---

## Setup & Configuration

### Step 1: Camera Service Startup Configuration

**Location**: `ppl-meta-cameras/src/main.py`

```python
# ppl-meta-cameras/src/main.py

import os
from fastapi import FastAPI

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    """Configure instant detection webhook on startup"""
    # Get media service URL from environment
    media_service_url = os.getenv("MEDIA_SERVICE_URL", "http://localhost:8000")
    webhook_url = f"{media_service_url}/api/v1/triggers/instant-detection"
    
    instant_detection_service = get_instant_detection_service()
    instant_detection_service.configure_webhook(
        url=webhook_url,
        enabled=True
    )
    
    logger.info(f"✅ Instant detection webhook configured: {webhook_url}")
```

### Step 2: Environment Configuration

```bash
# ppl-meta-cameras/.env
MEDIA_SERVICE_URL=http://localhost:8000
```

### Step 3: Obtain Device IDs and Playlist IDs from Existing Infrastructure

**Get Signage Device IDs** (from Discovery Service):
```bash
# List all registered signage devices
curl http://localhost:8006/api/v1/services?service_type=edge
```

Response shows device `service_id` (use this as `device_id` in triggers):
```json
{
  "services": [{
    "service_id": "abc-123-device-uuid",  // ← Use this in trigger actions
    "name": "Signage Device Living Room",
    "service_type": "edge",
    "host": "192.168.1.100",
    "port": 8080,
    "status": "healthy"
  }]
}
```

**Get Playlist IDs** (from Media Service):
```bash
# List all video playlists
curl http://localhost:8000/api/v1/signage/video-lists
```

Response shows playlist `uuid` (use this as `video_list_id` in triggers):
```json
{
  "results": [{
    "uuid": "xyz-789-playlist-uuid",  // ← Use this in trigger actions
    "name": "Men's Products Playlist",
    "video_count": 10,
    "is_active": true
  }]
}
```

**Important**: Use the actual UUIDs from your existing signage system in trigger configurations.

---

## Usage Examples

**Note**: All examples below use the **existing signage infrastructure**. Replace placeholder UUIDs with actual device IDs and playlist IDs from your system (see Step 3 above).

### Example 1: Configure Webhook

```bash
curl -X POST 'http://localhost:8005/api/v1/instant-detection/webhook/configure' \
  -H 'Content-Type: application/json' \
  -d '{
    "url": "http://localhost:8000/api/v1/triggers/instant-detection",
    "enabled": true
  }'
```

**Response**:
```json
{
  "success": true,
  "message": "Instant detection webhook configured",
  "webhook_url": "http://localhost:8000/api/v1/triggers/instant-detection",
  "enabled": true
}
```

---

### Example 2: Create Trigger - Male Dominant Audience

```bash
curl -X POST 'http://localhost:8000/api/v1/triggers/demographic' \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "male_dominant_audience",
    "description": "Switch to men'\''s product playlist when >60% male",
    "camera_ids": ["usb_camera_0"],
    "conditions": [
      {
        "field": "percent_male",
        "operator": "gte",
        "value": 60
      },
      {
        "field": "people_count",
        "operator": "gte",
        "value": 1
      }
    ],
    "actions": [
      {
        "type": "signage_playback",
        "device_ids": ["device-uuid-from-discovery-service"],
        "video_list_id": "playlist-uuid-mens-products",
        "start_index": 0,
        "volume": 80,
        "transition_mode": "after_current",
        "fade_duration_ms": 2000
      }
    ],
    "enabled": true,
    "cooldown_seconds": 60
  }'
```

**Configuration Explained**:
- `transition_mode: "after_current"` - Wait for current video to finish before switching
- `fade_duration_ms: 2000` - Not used with "after_current" mode (only for "fade" mode)
- Best for smooth, professional transitions with 60s cooldown

**What happens** (Technical Flow):

1. **T=0s**: Camera detects 3 people (67% male, 33% female)
2. **T=0s**: Camera **POSTs** demographics to webhook (async, non-blocking)
3. **T=0.05s**: Media service **receives** webhook at `/api/v1/triggers/instant-detection`
4. **T=0.1s**: Media service evaluates trigger conditions:
   - ✅ `percent_male (67) >= 60` → TRUE
   - ✅ `people_count (3) >= 1` → TRUE
   - ✅ Cooldown not active → TRUE
5. **T=0.15s**: Media service calls **existing** `/api/v1/signage/playback/start`
6. **T=0.2s**: Signage device receives command and switches to men's products playlist
7. **T=0.35s**: Total latency: ~350ms from detection to playlist switch
8. **T=5s**: Camera detects again → POSTs to webhook → **Cooldown active** → SKIPPED
9. **T=10s**: Camera detects again → POSTs to webhook → **Cooldown active** → SKIPPED
10. **T=65s**: Cooldown expires, trigger can fire again if conditions still met

**Important Timing Clarifications**:
- 🔄 **Webhook POSTs**: Every **5 seconds** (instant detection interval)
- ⏱️ **Cooldown**: **60 seconds** (prevents repeated triggering)
- ✅ **First trigger**: Fires immediately when conditions met
- ❌ **Subsequent POSTs**: Ignored while cooldown active (5s, 10s, 15s... up to 60s)
- ✅ **After cooldown**: Can fire again at 65s, 70s, 75s, etc. if conditions still met

**Android Player Transition Behavior** (User-Configurable):

The `transition_mode` field in the trigger action determines how the Android player handles playlist switching. Users configure this when creating triggers.

**transition_mode: "immediate"** (Default - Fast Response):
```
Current state: Playing "Women's Fashion Video 3" at 1:30 / 3:00
Receives: { transition_mode: "immediate" }
Action:
  1. STOP current video immediately (mid-playback)
  2. START new playlist from beginning
Result: Instant demographic response (~350ms), but jarring mid-video cut
Use case: Urgent content, breaking news, safety alerts
```

**transition_mode: "after_current"** (Smooth & Professional):
```
Current state: Playing "Women's Fashion Video 3" at 1:30 / 3:00
Receives: { transition_mode: "after_current" }
Action:
  1. Queue new playlist for after current video
  2. Let current video finish (1:30 remaining)
  3. Start new playlist when current ends
Result: Smooth transition, slight delay (~1.5min)
Use case: Long cooldowns (60s+), professional installations, retail
```

**transition_mode: "fade"** (Professional Crossfade):
```
Current state: Playing "Women's Fashion Video 3" at 1:30 / 3:00
Receives: { transition_mode: "fade", fade_duration_ms: 2000 }
Action:
  1. Start fading out current video (2 seconds)
  2. Fade in first video of new playlist (2 seconds)
  3. Crossfade or black frame between
Result: Professional transition, minimal disruption (2-4s delay)
Use case: High-end retail, museums, corporate lobbies
```

**User Controls Behavior**: The trigger creator decides transition mode when configuring the trigger, giving complete flexibility per use case.

**Key**: This is a **push mechanism** - camera actively sends data, media service doesn't poll.

---

### Example 3: Create Trigger - Young Audience

```bash
curl -X POST 'http://localhost:8000/api/v1/triggers/demographic' \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "young_audience",
    "description": "Switch to youth-targeted content when >50% young",
    "camera_ids": ["usb_camera_0"],
    "conditions": [
      {
        "field": "percent_young",
        "operator": "gte",
        "value": 50
      }
    ],
    "actions": [
      {
        "type": "signage_playback",
        "device_ids": ["device-uuid-from-discovery-service"],
        "video_list_id": "playlist-uuid-youth-content",
        "start_index": 0,
        "volume": 80,
        "transition_mode": "fade",
        "fade_duration_ms": 3000
      }
    ],
    "enabled": true,
    "cooldown_seconds": 90
  }'
```

**Configuration Explained**:
- `transition_mode: "fade"` - Professional crossfade transition
- `fade_duration_ms: 3000` - 3-second fade (2s fade out + 1s fade in)
- Best for high-end retail or professional installations

---

### Example 4: Create Trigger - Female Dominant Audience

```bash
curl -X POST 'http://localhost:8000/api/v1/triggers/demographic' \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "female_dominant_audience",
    "description": "Show women'\''s products when >70% female",
    "camera_ids": ["usb_camera_0", "rtsp_192.168.1.76_554"],
    "conditions": [
      {
        "field": "percent_female",
        "operator": "gte",
        "value": 70
      }
    ],
    "actions": [
      {
        "type": "signage_playback",
        "device_ids": ["device-uuid-from-discovery-service"],
        "video_list_id": "playlist-uuid-womens-products",
        "start_index": 0,
        "volume": 80,
        "transition_mode": "immediate"
      }
    ],
    "enabled": true,
    "cooldown_seconds": 60
  }'
```

**Configuration Explained**:
- `transition_mode: "immediate"` - Switch instantly (default behavior)
- Best for fast response when demographics change quickly

---

### Example 5: Multi-Condition Trigger

```bash
curl -X POST 'http://localhost:8000/api/v1/triggers/demographic' \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "young_male_sports_audience",
    "description": "Show sports products for young male audience",
    "camera_ids": ["usb_camera_0"],
    "conditions": [
      {
        "field": "percent_male",
        "operator": "gte",
        "value": 60
      },
      {
        "field": "percent_young",
        "operator": "gte",
        "value": 40
      },
      {
        "field": "people_count",
        "operator": "gte",
        "value": 2
      }
    ],
    "actions": [
      {
        "type": "signage_playback",
        "device_ids": ["device-uuid-from-discovery-service"],
        "video_list_id": "playlist-uuid-sports-products",
        "start_index": 0,
        "volume": 80,
        "transition_mode": "after_current"
      }
    ],
    "enabled": true,
    "cooldown_seconds": 120
  }'
```

**Conditions**: ALL must be true (AND logic)
- ≥60% male
- ≥40% young
- ≥2 people detected

**Configuration Explained**:
- `transition_mode: "after_current"` - Queue playlist change smoothly
- Longer cooldown (120s) works well with "after_current" mode

---

## Complete Integration Test

### Test Flow

```bash
# 1. Start all services
# - ppl-meta-cameras (port 8005)
# - ppl-meta-media (port 8000)  
# - ppl-meta-signage-simple-player (port 8080 on Android device)

# 2. Configure webhook
curl -X POST 'http://localhost:8005/api/v1/instant-detection/webhook/configure' \
  -H 'Content-Type: application/json' \
  -d '{
    "url": "http://localhost:8000/api/v1/triggers/instant-detection",
    "enabled": true
  }'

# 3. Create test trigger
curl -X POST 'http://localhost:8000/api/v1/triggers/demographic' \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "test_trigger",
    "description": "Test trigger for any person detected",
    "camera_ids": ["usb_camera_0"],
    "conditions": [
      {
        "field": "people_count",
        "operator": "gte",
        "value": 1
      }
    ],
    "actions": [
      {
        "type": "signage_playback",
        "device_ids": ["device-uuid-test"],
        "video_list_id": "playlist-uuid-test",
        "start_index": 0,
        "volume": 80,
        "transition_mode": "immediate"
      }
    ],
    "enabled": true,
    "cooldown_seconds": 30
  }'

# 4. Start recording on camera (triggers instant detection)
curl -X POST 'http://localhost:8005/api/v1/streaming/usb_camera_0/record/start?enable_instant_detection=true'

# 5. Watch logs for trigger firing
# Camera service: "✅ Pushed instant detection to webhook: usb_camera_0"
# Media service: "🎯 Trigger fired: test_trigger"
# Media service: "✅ Action executed: http://192.168.1.100:8080/api/v1/playlist/switch -> 200"

# 6. Verify trigger status
curl -X GET 'http://localhost:8000/api/v1/triggers/demographic'

# 7. Disable trigger if needed
curl -X POST 'http://localhost:8000/api/v1/triggers/demographic/test_trigger/disable'
```

---

## Available Demographic Fields

### Fields You Can Use in Conditions

```json
{
  "people_count": 3,              // Total people detected
  "total_male": 2,                // Count of males
  "total_female": 1,              // Count of females
  "total_unknown_gender": 0,      // Count of unknown gender
  "percent_male": 67,             // Percentage male (0-100)
  "percent_female": 33,           // Percentage female (0-100)
  "percent_unknown_gender": 0,    // Percentage unknown (0-100)
  "total_young": 0,               // Count of young (0-18)
  "total_adult": 3,               // Count of adults (18+)
  "total_unknown_age": 0,         // Count of unknown age
  "percent_young": 0,             // Percentage young (0-100)
  "percent_adult": 100,           // Percentage adult (0-100)
  "percent_unknown_age": 0        // Percentage unknown (0-100)
}
```

### Supported Operators

- `gt` - Greater than (>)
- `gte` - Greater than or equal (≥)
- `lt` - Less than (<)
- `lte` - Less than or equal (≤)
- `eq` - Equal (=)

---

## Advanced Features

### Feature 1: Multi-Camera Triggers

```json
{
  "name": "store_entrance_demographics",
  "camera_ids": ["entrance_cam_1", "entrance_cam_2", "entrance_cam_3"],
  "conditions": [
    {"field": "people_count", "operator": "gte", "value": 5}
  ],
  "actions": [{
    "type": "signage_playback",
    "device_ids": ["device-uuid-1", "device-uuid-2"],
    "video_list_id": "playlist-uuid-busy-hours",
    "start_index": 0,
    "volume": 80
  }]
}
```

**Behavior**: Trigger fires if ANY of the cameras meet conditions. Can control multiple devices simultaneously.

---

### Feature 2: Multiple Actions

```json
{
  "name": "vip_audience_detected",
  "conditions": [
    {"field": "percent_adult", "operator": "gte", "value": 90}
  ],
  "actions": [
    {
      "type": "signage_playback",
      "device_ids": ["device-uuid-lobby"],
      "video_list_id": "playlist-uuid-luxury",
      "volume": 85,
      "transition_mode": "fade",
      "fade_duration_ms": 2500
    },
    {
      "type": "signage_playback",
      "device_ids": ["device-uuid-entrance"],
      "video_list_id": "playlist-uuid-luxury",
      "volume": 85,
      "transition_mode": "fade",
      "fade_duration_ms": 2500
    },
    {
      "type": "http_call",
      "endpoint": "http://192.168.1.50:9000/api/notifications",
      "payload": {"message": "VIP audience detected", "priority": "high"}
    }
  ]
}
```

**Behavior**: ALL actions execute when trigger fires. Can mix signage actions with custom HTTP calls.

---

### Feature 3: Cooldown Management

```json
{
  "name": "frequent_update_trigger",
  "cooldown_seconds": 10,  // Fire every 10 seconds max (if conditions still met)
  ...
}

{
  "name": "infrequent_update_trigger",
  "cooldown_seconds": 300,  // Fire every 5 minutes max
  ...
}
```

**Use Cases**:
- **Short cooldown (10-30s)**: Responsive content switching, less viewer disruption
- **Medium cooldown (60-120s)**: Balanced updates (recommended for most scenarios)
- **Long cooldown (300+s)**: Prevent excessive switching, let playlists complete

**Important**: Even with 10s cooldown, webhooks still arrive every 5s. The cooldown only prevents ACTION execution, not webhook reception.

---

### Feature 4: Android Player Transition Implementation

**Android player must implement** the `transition_mode` parameter received from the trigger system.

**Implementation in Android Player** (`ppl-meta-signage-simple-player`):

```kotlin
// In Android player control handler
fun handlePlaylistSwitch(request: PlaylistSwitchRequest) {
    val transitionMode = request.transition_mode ?: "immediate"
    val fadeDuration = request.fade_duration_ms ?: 2000
    
    when (transitionMode) {
        "immediate" -> {
            // Stop current video and start new playlist immediately
            stopCurrentVideo()
            startPlaylist(request.video_list_id, request.start_index)
        }
        
        "after_current" -> {
            // Queue new playlist to start after current video finishes
            queuedPlaylist = request.video_list_id
            queuedStartIndex = request.start_index
            
            // Set callback for when current video completes
            setOnVideoCompleteListener {
                startPlaylist(queuedPlaylist, queuedStartIndex)
                queuedPlaylist = null
            }
        }
        
        "fade" -> {
            // Professional crossfade transition
            lifecycleScope.launch {
                // Fade out current video
                fadeOutCurrentVideo(fadeDuration / 2)
                delay(fadeDuration / 2)
                
                // Switch playlist
                stopCurrentVideo()
                startPlaylist(request.video_list_id, request.start_index)
                
                // Fade in new video
                fadeInNewPlaylist(fadeDuration / 2)
            }
        }
        
        else -> {
            // Fallback to immediate
            stopCurrentVideo()
            startPlaylist(request.video_list_id, request.start_index)
        }
    }
}
```

**Request Format Received by Android Player**:
```json
{
  "video_list_id": "playlist-uuid",
  "start_index": 0,
  "volume": 80,
  "transition_mode": "after_current",
  "fade_duration_ms": 2000
}
```

**Recommendations**:
- Use **"after_current"** for triggers with 60s+ cooldown (smooth, professional)
- Use **"immediate"** for urgent content (breaking news, safety alerts, very short cooldowns)
- Use **"fade"** for high-end installations (retail, museums, corporate lobbies)


```

**Use Cases**:
- **Short cooldown (10-30s)**: Responsive content switching
- **Medium cooldown (60-120s)**: Balanced updates
- **Long cooldown (300+s)**: Prevent excessive switching

---

## Trigger Management

### List All Triggers

```bash
curl -X GET 'http://localhost:8000/api/v1/triggers/demographic'
```

### Get Specific Trigger

```bash
curl -X GET 'http://localhost:8000/api/v1/triggers/demographic/male_dominant_audience'
```

### Update Trigger

```bash
curl -X PUT 'http://localhost:8000/api/v1/triggers/demographic/male_dominant_audience' \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "male_dominant_audience",
    "conditions": [
      {"field": "percent_male", "operator": "gte", "value": 70}
    ],
    ...
  }'
```

### Delete Trigger

```bash
curl -X DELETE 'http://localhost:8000/api/v1/triggers/demographic/male_dominant_audience'
```

### Enable/Disable Trigger

```bash
# Disable
curl -X POST 'http://localhost:8000/api/v1/triggers/demographic/male_dominant_audience/disable'

# Enable
curl -X POST 'http://localhost:8000/api/v1/triggers/demographic/male_dominant_audience/enable'
```

---

## Logging & Monitoring

### Camera Service Logs

```
✅ Instant detection webhook configured: http://localhost:8000/api/v1/triggers/instant-detection
✅ Pushed instant detection to webhook: usb_camera_0
⚠️ Webhook returned 500 for usb_camera_0
❌ Failed to push to webhook: Connection timeout
```

### Media Service Logs

```
📡 Received instant detection: usb_camera_0 - 3 people
🎯 Trigger fired: male_dominant_audience
✅ Action executed: http://192.168.1.100:8080/api/v1/playlist/switch -> 200
⏱️ Trigger male_dominant_audience in cooldown (45.3s)
❌ Failed to execute action: Connection refused
```

### Signage Player Logs

```
📱 Received playlist switch request: mens_products_2024
🎬 Stopping current video: womens_fashion_01.mp4
▶️ Starting new playlist: mens_products_2024
✅ Playlist switched successfully
```

---

## Error Handling

### Webhook Push Failures

**Issue**: Camera can't reach media service

**Solution**: Non-blocking async calls with short timeout
```python
try:
    response = await self._http_client.post(url, json=payload, timeout=2.0)
except Exception as e:
    logger.error(f"Webhook failed: {e}")
    # Detection continues normally
```

---

### Action Execution Failures

**Issue**: Signage endpoint not responding

**Solution**: Log error, continue processing other triggers
```python
try:
    await _execute_action(action, payload)
    triggered_actions.append({"success": True})
except Exception as e:
    logger.error(f"Action failed: {e}")
    triggered_actions.append({"success": False, "error": str(e)})
```

---

### Trigger Condition Errors

**Issue**: Invalid field in condition

**Solution**: Gracefully handle missing fields
```python
actual_value = payload.demographics.get(condition.field)
if actual_value is None:
    if condition.field == "people_count":
        actual_value = payload.people_count
    else:
        conditions_met = False  # Fail safely
```

---

## Performance Considerations

### Webhook Push Performance

- ✅ **Async execution**: Non-blocking, doesn't slow detection
- ✅ **Short timeout**: 2 seconds max
- ✅ **Error isolation**: Failures don't break detection
- ✅ **Lightweight payload**: ~500 bytes per push

### Trigger Evaluation Performance

- ✅ **In-memory triggers**: Instant lookup
- ✅ **AND logic**: Short-circuit evaluation
- ✅ **Cooldown checks**: Skip unnecessary evaluations
- ✅ **Parallel actions**: All execute concurrently

### Recommended Limits

- **Triggers per camera**: ≤10 for optimal performance
- **Conditions per trigger**: ≤5 for fast evaluation
- **Actions per trigger**: ≤3 for quick execution
- **Cooldown minimum**: ≥10 seconds to avoid overload

---

## Production Considerations

### Database Storage

Replace in-memory dictionaries with database:

```python
# Instead of:
TRIGGERS: Dict[str, DemographicTrigger] = {}

# Use:
from sqlalchemy import create_engine
from models import TriggerModel

async def get_triggers_for_camera(camera_id: str):
    return await TriggerModel.query.filter(
        TriggerModel.camera_ids.contains([camera_id]),
        TriggerModel.enabled == True
    ).all()
```

---

### Trigger History & Analytics

```python
class TriggerExecution(BaseModel):
    trigger_name: str
    timestamp: datetime
    camera_id: str
    demographics: Dict
    success: bool
    
# Store in database for analytics
await TriggerExecution.create(**execution_data)
```

---

### Rate Limiting

```python
from slowapi import Limiter

limiter = Limiter(key_func=get_remote_address)

@router.post("/api/v1/triggers/instant-detection")
@limiter.limit("100/minute")  # Max 100 pushes per minute
async def process_instant_detection_webhook(payload):
    ...
```

---

### Authentication

```python
from fastapi import Header, HTTPException

async def verify_webhook_token(x_webhook_token: str = Header(None)):
    if x_webhook_token != os.getenv("WEBHOOK_SECRET"):
        raise HTTPException(status_code=401, detail="Invalid webhook token")

@router.post("/api/v1/triggers/instant-detection")
async def process_instant_detection_webhook(
    payload: InstantDetectionPayload,
    token: str = Depends(verify_webhook_token)
):
    ...
```

---

## Deployment Checklist

- [ ] Configure webhook URL in camera service
- [ ] Create triggers for each use case
- [ ] Test with single camera first
- [ ] Verify signage endpoint accessibility
- [ ] Set appropriate cooldown periods
- [ ] Configure authentication/rate limiting
- [ ] Set up logging and monitoring
- [ ] Test error scenarios (network failures, etc.)
- [ ] Document trigger configurations
- [ ] Train staff on trigger management

---

## Future Enhancements

### 1. Time-Based Conditions

```json
{
  "conditions": [
    {"field": "percent_male", "operator": "gte", "value": 60},
    {"field": "hour_of_day", "operator": "gte", "value": 9},
    {"field": "hour_of_day", "operator": "lt", "value": 17}
  ]
}
```

### 2. Trigger Priority

```json
{
  "name": "high_priority_trigger",
  "priority": 1,  // Higher priority executes first
  "conditions": [...],
  "actions": [...]
}
```

### 3. Trigger Groups

```json
{
  "name": "morning_triggers",
  "active_hours": {"start": 6, "end": 12},
  "triggers": [...]
}
```

### 4. A/B Testing

```json
{
  "name": "ab_test_trigger",
  "actions": [
    {"endpoint": "...", "probability": 0.5},
    {"endpoint": "...", "probability": 0.5}
  ]
}
```

---

## Related Documentation

- **[ppl-meta-signage.md](../guides/developer/ppl-meta-signage.md)** - **EXISTING Signage Management System** (playlists, devices, control)
- [PPL-META-CAMERA-SCREEN-AND-CARDS.md](PPL-META-CAMERA-SCREEN-AND-CARDS.md) - Camera frontend architecture
- [ppl-meta-face-detection.md](../guides/developer/ppl-meta-face-detection.md) - Face detection implementation
- Media Service API Documentation (if available)

**Note**: This trigger system **integrates with** the existing signage infrastructure documented in `ppl-meta-signage.md`. No new signage player or management system is required.

---

**Document End**
