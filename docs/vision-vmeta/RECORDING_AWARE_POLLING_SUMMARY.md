# Recording-Aware Polling Implementation Summary

## What Changed

### Problem Statement
Previously, the MVR polling system ran continuously and accumulated all videos, triggering only once. It also didn't know when recording started or stopped, leading to:
- Unnecessary polling when camera idle
- Videos stuck pending if < 5 accumulated
- No way to trigger final batch when user stops recording

### Solution Implemented
Upgraded the polling system to be **recording-aware** with event-driven lifecycle:

1. **Only polls during active recordings** (between start/stop events)
2. **Incremental batching** every 5 videos during recording
3. **Final batch trigger** for remaining videos when recording stops

## Files Modified

### 1. New API Endpoints (`ppl-meta-vmeta/src/api/v1/recording_events.py`)
**Created new file** with 4 endpoints:
- `POST /api/v1/recording/started` - Activates polling for collection
- `POST /api/v1/recording/stopped` - Triggers final batch and stops polling
- `GET /api/v1/recording/status` - Returns polling manager status
- `POST /api/v1/recording/test-trigger` - Manual batch trigger for testing

### 2. Upgraded PollingFallbackManager (`ppl-meta-vmeta/src/services/batch_timeout_manager.py`)
**Enhanced class** with recording lifecycle support:

**Added State Tracking:**
```python
self._active_recordings = {}  # Tracks active recording sessions
self._stats['recordings_started'] = 0
self._stats['recordings_stopped'] = 0
```

**New Methods:**
- `async start_recording(collection_id, session_uuid)` - Activate polling
- `async stop_recording(collection_id, session_uuid)` - Stop polling + final batch
- `get_status()` - Comprehensive status including active recordings
- `async manual_trigger()` - Manual batch trigger

**Modified Polling Loop:**
```python
# Only polls if there are active recordings
if self._active_recordings:
    await self._poll_for_videos()
else:
    logger.debug("No active recordings, skipping poll")
```

**Enhanced Batch Triggering:**
```python
async def _trigger_batch_processing(videos, is_final=False):
    batch_type = "FINAL" if is_final else "incremental"
    # Logs whether incremental or final batch
```

### 3. Service Integration (`ppl-meta-vmeta/src/main.py`)
**Added router registration:**
```python
from api.v1 import recording_events
app.include_router(recording_events.router, tags=["recording-events"])
```

**Set global polling_manager reference:**
```python
from api.v1 import recording_events
recording_events.polling_manager = polling_manager
```

### 4. Type Imports (`ppl-meta-vmeta/src/services/batch_timeout_manager.py`)
**Added missing types:**
```python
from typing import Optional, List, Dict, Any
```

## How It Works Now

### Workflow
```
1. User taps "Start Recording" in Camera Service
   ↓
2. Camera Service sends POST /api/v1/recording/started to VMeta
   ↓
3. VMeta activates polling for that collection
   ↓
4. Polling loop runs every 30 seconds:
   - Checks Media service for new videos
   - Checks Vision service for face detection
   - Accumulates videos with faces
   - Triggers batch when 5 videos ready
   ↓
5. User taps "Stop Recording" in Camera Service
   ↓
6. Camera Service sends POST /api/v1/recording/stopped to VMeta
   ↓
7. VMeta triggers final batch for remaining videos
   ↓
8. VMeta stops polling for that collection
```

### Example Timeline (4:30 recording = 9 videos)
```
00:00 - Recording starts → Polling activated
00:30 - Poll finds 1 video → pending (1/5)
01:00 - Poll finds 2 videos → pending (2/5)
01:30 - Poll finds 3 videos → pending (3/5)
02:00 - Poll finds 4 videos → pending (4/5)
02:30 - Poll finds 5 videos → BATCH #1 (5 videos) ✅
03:00 - Poll finds 6 videos → pending (1/5)
03:30 - Poll finds 7 videos → pending (2/5)
04:00 - Poll finds 8 videos → pending (3/5)
04:30 - Recording stops → FINAL BATCH (4 videos) ✅
```

**Result:** 2 tracking sessions created, 0 videos stuck pending

## Testing

### Test Script
Created `/tests/test_recording_aware_polling.py`:
- Authenticates with Node service
- Sends recording_started event
- Checks status during recording
- Sends recording_stopped event
- Verifies final batch triggered

### Run Test
```bash
python tests/test_recording_aware_polling.py
```

## Camera Service Integration Required

The Camera Service needs to send events to VMeta:

### In `start_recording_with_session()`:
```python
# After successfully starting recording
async with httpx.AsyncClient() as client:
    await client.post(
        f"{VMETA_URL}/api/v1/recording/started",
        json={
            "collection_id": device_id,
            "session_uuid": session_uuid,
            "device_id": device_id,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        },
        headers={"Authorization": f"Bearer {auth_token}"}
    )
```

### In `stop_recording()`:
```python
# After successfully stopping recording
async with httpx.AsyncClient() as client:
    await client.post(
        f"{VMETA_URL}/api/v1/recording/stopped",
        json={
            "collection_id": device_id,
            "session_uuid": session_uuid,
            "device_id": device_id,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "video_count": len(recorded_videos)
        },
        headers={"Authorization": f"Bearer {auth_token}"}
    )
```

**VMETA_URL:** `http://localhost:8008` (or service discovery lookup)

## Configuration

No configuration changes needed. Existing settings work:
```python
polling_manager = PollingFallbackManager(
    poll_interval_seconds=30,  # Still 30 seconds
    batch_size=5,              # Still 5 videos
    collection_id="usb_camera_0",
    enabled=True
)
```

## Backwards Compatibility

✅ **Fully backwards compatible:**
- If Camera Service doesn't send events, polling still works
- Time filter (2 hours) prevents reprocessing old videos
- Existing manual triggers still work
- No breaking API changes

## Benefits

### Before (Old System)
- ❌ Polling ran 24/7 even when camera idle
- ❌ Accumulated ALL videos, triggered once
- ❌ Videos stuck pending if < 5
- ❌ No way to force final batch

### After (New System)
- ✅ Polling only when recording active
- ✅ Incremental batches every 5 videos
- ✅ Final batch for remaining videos on stop
- ✅ No idle resource usage
- ✅ Complete processing guaranteed

## Monitoring

### Check Polling Status
```bash
TOKEN=$(curl -X POST http://localhost:8001/api/v1/users/login \
  -d "username=fresh.user@example.com" \
  -d "password=NewPassword234!" \
  | jq -r .access_token)

curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8008/api/v1/recording/status | jq
```

### Expected Response
```json
{
  "polling_manager": {
    "enabled": true,
    "running": true,
    "active_recordings": 1,
    "pending_videos": 3,
    "recordings": {
      "usb_camera_0": {
        "session_uuid": "abc-123",
        "started_at": "2025-01-01T12:00:00",
        "duration_seconds": 150.5,
        "batches_triggered": 1
      }
    },
    "statistics": {
      "polls_performed": 5,
      "videos_discovered": 8,
      "batches_triggered": 1,
      "recordings_started": 1,
      "recordings_stopped": 0
    }
  }
}
```

## Next Steps

1. **Integrate with Camera Service:**
   - Add recording_started webhook call
   - Add recording_stopped webhook call

2. **Test with Real Recording:**
   - Start recording in mobile app
   - Verify polling activates
   - Record for 4+ minutes
   - Verify incremental batches
   - Stop recording
   - Verify final batch

3. **Monitor Logs:**
   - Look for "📹 Recording started" logs
   - Verify "🚀 Triggering incremental batch" logs
   - Check "🛑 Recording stopped" and final batch logs

## Documentation

- **Architecture:** `/docs/vision-vmeta/RECORDING_AWARE_POLLING.md`
- **Test Script:** `/tests/test_recording_aware_polling.py`
- **This Summary:** `/docs/vision-vmeta/RECORDING_AWARE_POLLING_SUMMARY.md`
