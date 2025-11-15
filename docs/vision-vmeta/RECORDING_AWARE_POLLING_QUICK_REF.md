# Quick Reference: Recording-Aware Polling

## What It Does
- ✅ Polls **only during active recordings**
- ✅ Triggers batch **every 5 videos** incrementally
- ✅ Triggers **final batch** when recording stops
- ✅ No videos left pending

## Key Changes

| Aspect | Before | After |
|--------|--------|-------|
| Polling | Always running | Only during recording |
| Batching | Accumulate all | Incremental (every 5) |
| Final batch | Manual only | Automatic on stop |
| Idle camera | Wastes resources | Zero overhead |

## API Endpoints

### Start Recording
```bash
POST http://localhost:8008/api/v1/recording/started
{
  "collection_id": "usb_camera_0",
  "session_uuid": "abc-123",
  "device_id": "usb_camera_0",
  "user_id": "user123",
  "timestamp": "2025-01-01T12:00:00Z"
}
```

### Stop Recording
```bash
POST http://localhost:8008/api/v1/recording/stopped
{
  "collection_id": "usb_camera_0",
  "session_uuid": "abc-123",
  "device_id": "usb_camera_0",
  "user_id": "user123",
  "timestamp": "2025-01-01T12:05:00Z",
  "video_count": 8
}
```

### Check Status
```bash
GET http://localhost:8008/api/v1/recording/status
```

## Integration Code (Camera Service)

### On Recording Start
```python
# In start_recording_with_session() after success:
async with httpx.AsyncClient() as client:
    await client.post(
        "http://localhost:8008/api/v1/recording/started",
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

### On Recording Stop
```python
# In stop_recording() after success:
async with httpx.AsyncClient() as client:
    await client.post(
        "http://localhost:8008/api/v1/recording/stopped",
        json={
            "collection_id": device_id,
            "session_uuid": session_uuid,
            "device_id": device_id,
            "user_id": "user_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "video_count": len(recorded_videos)
        },
        headers={"Authorization": f"Bearer {auth_token}"}
    )
```

## Testing

```bash
# Run test script
python tests/test_recording_aware_polling.py

# Check status manually
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8008/api/v1/recording/status
```

## Log Patterns to Watch

```
📹 Recording started: usb_camera_0, session: abc-123
Polling activated for usb_camera_0
Found video 12345... with 3 faces
Pending videos: 3/5 (waiting for more)
🚀 Triggering incremental batch processing for 5 videos
✅ INCREMENTAL batch triggered! Session: xyz-789
🛑 Recording stopped: usb_camera_0, session: abc-123
Processing final batch: 3 remaining videos
✅ FINAL batch triggered! Session: uvw-456
```

## Configuration (No Changes Needed)

```python
# In ppl-meta-vmeta/src/main.py (already configured)
polling_manager = PollingFallbackManager(
    poll_interval_seconds=30,    # Check every 30s
    batch_size=5,                # Trigger every 5 videos
    enabled=True,                # Enabled
    collection_id="usb_camera_0"
)
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Polling not starting | Check recording_started event sent |
| No batches triggered | Verify videos have face detection |
| Final batch not fired | Check recording_stopped event |
| Auth errors | Verify JWT token valid |

## Files Changed

1. `ppl-meta-vmeta/src/api/v1/recording_events.py` - New API
2. `ppl-meta-vmeta/src/services/batch_timeout_manager.py` - Enhanced
3. `ppl-meta-vmeta/src/main.py` - Router + reference setup
4. `tests/test_recording_aware_polling.py` - Test script

## Next Steps

1. Add webhook calls to Camera Service
2. Test with real recording
3. Monitor logs during test
4. Verify batches triggered correctly

## Full Documentation

- **Complete Guide:** `docs/vision-vmeta/RECORDING_AWARE_POLLING.md`
- **Implementation Summary:** `docs/vision-vmeta/RECORDING_AWARE_POLLING_SUMMARY.md`
