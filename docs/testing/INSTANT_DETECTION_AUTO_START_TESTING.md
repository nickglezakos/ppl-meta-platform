# Testing Instant Detection Auto-Start Fix

## Prerequisites
- Camera service running on port 8005
- Vision service running on port 8003
- Celery worker running for instant detection tasks
- A camera connected (e.g., `usb_camera_0`)

## Test Steps

### 1. Backend Test - Verify Instant Detection Auto-Starts

```bash
# Terminal 1: Watch camera service logs
tail -f logs/ppl-meta-cameras.log | grep -i "instant\|detection"

# Terminal 2: Start recording
curl -X POST "http://localhost:8005/api/v1/streaming/usb_camera_0/record/start" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Expected logs:
# ✅ Detection enabled in worker usb_camera_0
# ✅ Instant detection started for worker usb_camera_0
# ✅ Starting new detection sample for usb_camera_0
# ✅ Sampled frame 0/3 for usb_camera_0
# ✅ Sampled frame 1/3 for usb_camera_0
# ✅ Sampled frame 2/3 for usb_camera_0
# ✅ Submitted instant detection batch for usb_camera_0
```

### 2. Check Results After 6 Seconds

```bash
# Wait 6 seconds after starting recording, then:
curl -s "http://localhost:8005/api/v1/instant-detection/results/usb_camera_0" | jq

# Expected response:
{
  "success": true,
  "camera_id": "usb_camera_0",
  "person_objects": [
    {
      "person_id": "instant_person_001",
      "face_count": 3,
      "age_gender": {
        "gender": "Male",
        "age_range": "(25-32)"
      }
    }
  ],
  "_metadata": {
    "cached_at": 1234567890.123,
    "iteration": 1,
    "age_seconds": 2.5
  }
}

# If you get 404, instant detection didn't start - check logs
```

### 3. Frontend Test - Widget Display

1. **Open Camera Stream Page**
   - Navigate to camera details/stream page
   - Should see two counter widgets side-by-side

2. **Start Recording**
   - Click "Start Recording" button
   - Instant detection widget should show: `"Start recording to see live detection"`
   - After ~6 seconds, should show people count and demographics

3. **Verify Auto-Refresh**
   - Widget should update every 5 seconds
   - Check browser console for poll logs:
     ```
     🔍 [INSTANT_DETECTION_WIDGET] Periodic fetch tick (5s interval)
     ```

4. **Stop Recording**
   - Click "Stop Recording" button
   - Widget should immediately stop polling and show: `"Start recording to see live detection"`

### 4. Camera Card Test

1. **Navigate to Cameras List**
   - Should see instant detection widget below camera details
   - Start recording from the camera card
   - Wait ~6 seconds
   - Should see detection results in the card

## Expected Behavior

### ✅ Correct Behavior
- Instant detection starts automatically when recording starts
- No manual API calls needed
- Widget polls and displays results within 6-10 seconds
- Widget stops polling when recording stops
- Results update every 5 seconds during recording

### ❌ Incorrect Behavior (Before Fix)
- Widget always shows "inactive" state
- 404 errors when polling `/api/v1/instant-detection/results/{camera_id}`
- No detection logs in camera service
- Required manual POST to `/api/v1/instant-detection/start/{camera_id}`

## Troubleshooting

### Issue: Still Getting 404 on Results Endpoint

**Check:**
1. Is Celery worker running?
   ```bash
   ps aux | grep celery
   ```

2. Are frames being processed?
   ```bash
   tail -f logs/ppl-meta-cameras.log | grep "Sampled frame"
   ```

3. Is detection_sampler created?
   ```bash
   tail -f logs/ppl-meta-cameras.log | grep "Instant detection started"
   ```

### Issue: No Logs About Instant Detection

**Check:**
1. Is `enable_instant_detection` parameter true?
   ```bash
   tail -f logs/ppl-meta-cameras.log | grep "enable_instant_detection"
   # Should see: enable_instant_detection parameter: True
   ```

2. Did worker.start_detection() get called?
   ```bash
   tail -f logs/ppl-meta-cameras.log | grep "start_detection"
   ```

### Issue: Widget Not Updating

**Check:**
1. Browser console for errors:
   ```javascript
   // Should see periodic logs:
   🔍 [INSTANT_DETECTION_WIDGET] Periodic fetch tick (5s interval)
   ```

2. Network tab - verify API calls to:
   ```
   GET /api/v1/instant-detection/results/{camera_id}
   ```

3. Check recording state provider:
   ```dart
   // In widget, check if recordingState.isRecording is true
   ```

## Success Criteria

✅ Recording starts → Instant detection automatically starts  
✅ Wait 6 seconds → Results available at API endpoint  
✅ Frontend widget displays people count and demographics  
✅ Widget updates every 5 seconds during recording  
✅ Recording stops → Instant detection automatically stops  
✅ Widget stops polling and shows "start recording" message  

## Performance Notes

- First detection results appear after ~6 seconds (3 frames + processing)
- Updates occur every 5 seconds (sampling interval)
- Detection is non-blocking (Celery background tasks)
- No impact on recording quality or frame rate

## Related Documentation

- [Instant Detection Auto-Start Fix](./INSTANT_DETECTION_AUTO_START_FIX.md) - Root cause and fix explanation
- [Counter Widget Integration](../development/COUNTER_WIDGET_INTEGRATION.md) - Widget integration details
- [Instant Detection Implementation](../guides/developer/instant-detection-implementation.md) - API and architecture guide
