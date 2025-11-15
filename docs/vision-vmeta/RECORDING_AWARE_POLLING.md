# Recording-Aware MVR Polling System

## Overview

The upgraded polling system only runs during active camera recordings, triggered by recording start/stop events. This eliminates unnecessary processing and ensures batch completion when recording stops.

## Key Features

### 1. **Event-Driven Lifecycle**
- Polling activates when user starts recording
- Polling stops when user stops recording
- No processing when camera is idle

### 2. **Incremental Batching**
- Processes videos in batches of 5 during recording
- Continues polling and batching as recording progresses
- Triggers final batch for remaining videos on stop

### 3. **Multi-Recording Support**
- Can handle multiple simultaneous recordings
- Each recording tracked independently
- Collection-specific session management

## Architecture

```
Camera Service                VMeta Service
    │                              │
    ├─► Recording Started ────────►│ Start Polling
    │   (POST /api/v1/recording/started)
    │                              │
    │                        [Polling Loop]
    │                              │
    │                         Check Videos
    │                              │
    │                         Check Faces
    │                              │
    │                        Accumulate (5)
    │                              │
    │                         Trigger Batch
    │                              │
    │                        [Continue Polling]
    │                              │
    ├─► Recording Stopped ────────►│ Stop Polling
        (POST /api/v1/recording/stopped)
                                   │
                            Trigger Final Batch
                                   │
                            Process Remaining Videos
```

## API Endpoints

### Start Recording Event
```http
POST /api/v1/recording/started
Authorization: Bearer <token>

{
  "collection_id": "usb_camera_0",
  "session_uuid": "abc-def-ghi",
  "device_id": "usb_camera_0",
  "user_id": "user123",
  "timestamp": "2025-01-01T12:00:00Z",
  "metadata": {}
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Polling activated for collection usb_camera_0",
  "collection_id": "usb_camera_0",
  "session_uuid": "abc-def-ghi",
  "polling_active": true
}
```

### Stop Recording Event
```http
POST /api/v1/recording/stopped
Authorization: Bearer <token>

{
  "collection_id": "usb_camera_0",
  "session_uuid": "abc-def-ghi",
  "device_id": "usb_camera_0",
  "user_id": "user123",
  "timestamp": "2025-01-01T12:05:00Z",
  "video_count": 8,
  "metadata": {}
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Recording stopped and final batch triggered",
  "collection_id": "usb_camera_0",
  "session_uuid": "abc-def-ghi",
  "polling_active": false,
  "videos_processed": 3,
  "total_batches": 2,
  "session_duration": 300.5
}
```

### Get Polling Status
```http
GET /api/v1/recording/status
Authorization: Bearer <token>
```

**Response:**
```json
{
  "status": "success",
  "polling_manager": {
    "enabled": true,
    "running": true,
    "poll_interval": 30,
    "batch_size": 5,
    "active_recordings": 1,
    "recordings": {
      "usb_camera_0": {
        "session_uuid": "abc-def-ghi",
        "started_at": "2025-01-01T12:00:00",
        "duration_seconds": 150.2,
        "batches_triggered": 1
      }
    },
    "pending_videos": 3,
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

## Configuration

### VMeta Service (main.py)
```python
polling_manager = PollingFallbackManager(
    batch_monitor=batch_monitor,
    poll_interval_seconds=30,    # Check every 30 seconds
    enabled=True,                # Enable polling
    media_url="http://localhost:8000",
    vision_url="http://localhost:8003",
    vmeta_url="http://localhost:8008",
    node_url="http://localhost:8001",
    batch_size=5,                # Trigger every 5 videos
    collection_id="usb_camera_0" # Default collection
)
```

## Integration with Camera Service

### Camera Service Changes Needed

The Camera Service needs to send recording events to VMeta:

```python
# In Camera Service stop_recording() method:

async def stop_recording(device_id: str, user_id: str):
    # Existing code to stop recording...
    
    # Send event to VMeta
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

# Later in stop_recording():

async def stop_recording(device_id: str, user_id: str):
    # Existing code to stop recording...
    
    # Send stop event to VMeta
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{VMETA_URL}/api/v1/recording/stopped",
            json={
                "collection_id": device_id,
                "session_uuid": session_uuid,
                "device_id": device_id,
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "video_count": total_videos
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
```

## Workflow Examples

### Scenario 1: 4-Minute Recording (8 videos)

```
Time    Event                           Polling Action
─────────────────────────────────────────────────────────
00:00   User taps "Start Recording"     Polling activated
00:30   Poll #1                         Found 1 video → pending (1/5)
01:00   Poll #2                         Found 2 videos → pending (2/5)
01:30   Poll #3                         Found 3 videos → pending (3/5)
02:00   Poll #4                         Found 4 videos → pending (4/5)
02:30   Poll #5                         Found 5 videos → BATCH #1 triggered ✅
03:00   Poll #6                         Found 6 videos → pending (1/5)
03:30   Poll #7                         Found 7 videos → pending (2/5)
04:00   Poll #8                         Found 8 videos → pending (3/5)
04:00   User taps "Stop Recording"      FINAL BATCH triggered ✅
                                        Processed 3 remaining videos
```

**Result:** 2 tracking sessions created (5 + 3 videos)

### Scenario 2: 3-Minute Recording (6 videos)

```
Time    Event                           Polling Action
─────────────────────────────────────────────────────────
00:00   User taps "Start Recording"     Polling activated
00:30   Poll #1                         Found 1 video → pending (1/5)
01:00   Poll #2                         Found 2 videos → pending (2/5)
01:30   Poll #3                         Found 3 videos → pending (3/5)
02:00   Poll #4                         Found 4 videos → pending (4/5)
02:30   Poll #5                         Found 5 videos → BATCH #1 triggered ✅
03:00   Poll #6                         Found 6 videos → pending (1/5)
03:00   User taps "Stop Recording"      FINAL BATCH triggered ✅
                                        Processed 1 remaining video
```

**Result:** 2 tracking sessions created (5 + 1 videos)

## Testing

### Manual Test
```bash
# 1. Start VMeta service
cd ppl-meta-vmeta
source venv/bin/activate
uvicorn main:app --port 8008 --reload

# 2. Run test script
cd /path/to/ppl-meta-code
python tests/test_recording_aware_polling.py
```

### Expected Output
```
============================================================
Testing Recording-Aware Polling System
============================================================

1️⃣ Authenticating...
   ✅ Authenticated

2️⃣ Checking initial status...
   Enabled: True
   Running: True
   Active recordings: 0
   Pending videos: 0

3️⃣ Starting recording...
   ✅ Polling activated for collection usb_camera_0

4️⃣ Waiting for polling to detect videos (30 seconds)...

5️⃣ Checking status during recording...
   Active recordings: 1
   Pending videos: 3

6️⃣ Waiting for more polling cycles (30 seconds)...

7️⃣ Stopping recording...
   ✅ Recording stopped and final batch triggered
   Videos processed: 3
   Total batches: 2

8️⃣ Checking final status...
   Active recordings: 0
   Pending videos: 0

============================================================
✅ Test completed successfully!
============================================================
```

## Monitoring

### Check Polling Status
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8008/api/v1/recording/status
```

### VMeta Service Logs
Look for these log patterns:
```
📹 Recording started: usb_camera_0, session: abc-def-ghi
Polling activated for usb_camera_0 (active recordings: 1)
Found video 12345... with 3 faces
Pending videos: 3/5 (waiting for more)
🚀 Triggering incremental batch processing for 5 videos
✅ INCREMENTAL batch triggered! Session: xyz-789
🛑 Recording stopped: usb_camera_0, session: abc-def-ghi
Processing final batch: 3 remaining videos
🚀 Triggering FINAL batch processing for 3 videos
✅ FINAL batch triggered! Session: uvw-456
```

## Troubleshooting

### Polling Not Starting
- Check `enabled=True` in PollingFallbackManager initialization
- Verify recording events reaching VMeta service
- Check VMeta service logs for errors

### Batches Not Triggering
- Verify videos have face detection completed (Vision service)
- Check batch_size setting (default: 5)
- Verify auth token is valid
- Check time filter (only processes videos < 2 hours old)

### Final Batch Not Triggered
- Ensure recording_stopped event sent properly
- Check for pending videos in status endpoint
- Verify stop event has correct collection_id

## Benefits

1. **No Idle Polling:** Only polls when recording active
2. **Complete Processing:** Final batch ensures no videos missed
3. **Incremental Results:** Users get results during long recordings
4. **Resource Efficient:** No unnecessary background work
5. **Multiple Recordings:** Supports concurrent camera sessions

## Migration from Old System

The old polling system ran continuously. The new system requires:

1. **Camera Service Integration:** Add recording event webhooks
2. **Configuration:** Polling now event-driven (no changes needed)
3. **Backwards Compatible:** Works without events (falls back to time filter)

## Future Enhancements

1. **Configurable Batch Size:** Per-recording batch size settings
2. **Adaptive Polling:** Faster polling for active recordings
3. **Progress Callbacks:** Real-time updates to frontend
4. **Batch Priority:** Urgent vs. normal processing queues
