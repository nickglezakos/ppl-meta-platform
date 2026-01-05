# Bug Report: Continuous Pipeline Not Processing RTSP Camera Videos

**Date**: January 5, 2026  
**Reporter**: Quality Metrics Testing  
**Severity**: High  
**Status**: RESOLVED - Fixed on January 5, 2026

---

## Resolution Summary

**Root Cause**: RTSP cameras (via `camera_detection.py`) were NOT sending recording start/stop events to vmeta service, while USB cameras (via `streaming.py`) were. The PollingFallbackManager operates in "recording-aware mode" and requires these events to activate polling.

**Fix**: Added vmeta recording event notifications to `camera_detection.py` (lines ~1088 and ~1610)
- Sends POST `/api/v1/recording/started` when recording begins
- Sends POST `/api/v1/recording/stopped` when recording ends

**Files Modified**: `/ppl-meta-cameras/src/services/camera_detection.py`

---

## Summary

Videos recorded from RTSP camera collection `rtsp_192.168.1.77_554 Collection` on January 4, 2026 have NOT been processed through the continuous cross-video tracking pipeline. This means no individuals were created, resulting in zero quality metrics data.

---

## Expected Behavior

According to the **Continuous Individuals and MVR Pipeline** design:

1. When camera records video segments, they are saved to Media service
2. Face detection should run automatically (Enhanced Logic V2)
3. After accumulating batch_size videos (default: 5), the continuous pipeline should:
   - Automatically trigger cross-video tracking
   - Create individuals in vmeta database
   - Create MVR people records
   - Cache results for future batches

**Expected Flow**:
```
Video Recording → Face Detection → Batch Accumulation (5 videos) 
→ Automatic Cross-Video Tracking → Individuals Created → MVR Created
```

---

## Actual Behavior

Videos exist in Media service but were **NOT processed**:

**Videos Found**: 18 videos in collection `rtsp_192.168.1.77_554 Collection`

**Sample Videos**:
- `cad497adf7ad54cad73123675f3bf578.mp4` - 2026-01-04T11:58:22
- `0f3baf0611195f9a620c374460d67dce.mp4` - 2026-01-04T11:58:19
- `e58a8ad8de55902882ab2815694f51f6.mp4` - 2026-01-04T11:58:17
- `3e0b071010a097a236250e0ef54ca996.mp4` - 2026-01-04T11:43:06
- `319d94069a15cd4773ceca795de10df6.mp4` - 2026-01-04T11:43:04

**Verification Commands**:
```bash
# Videos exist in Media service
curl -s "http://localhost:8000/api/v1/media/search?collection=rtsp_192.168.1.77_554%20Collection&limit=5" \
  -H "Authorization: Bearer $TOKEN"
# Result: 18 videos found

# Quality metrics endpoint returns NO individuals
curl -s "http://localhost:8080/api/v1/analytics/quality-metrics?time_filter=last_week&collection_ids=rtsp_192.168.1.77_554%20Collection" \
  -H "Authorization: Bearer $TOKEN"
# Result: total_individuals: 0, active_collections: 0
```

---

## Impact

1. **Quality Metrics Unavailable**: New quality metrics endpoint cannot provide data
2. **No Individual Tracking**: Cross-video tracking not functioning for this collection
3. **No MVR People**: No MVR people records created
4. **Analytics Incomplete**: Analytics dashboard shows zero data for this camera
5. **Continuous Pipeline Broken**: The automatic processing pipeline is not working

---

## Investigation Questions

### 1. Is Face Detection Running?
- Are face detection results being saved to database?
- Is Enhanced Logic V2 enabled for this collection?
- Check: `ppl-meta-vision` logs for face detection activity

### 2. Is Batch Monitor Active?
- Is the PollingFallbackManager running?
- Is it monitoring the correct collection?
- Check: `ppl-meta-vmeta` logs for batch accumulation messages

### 3. Was Recording Session Tracked?
- Was a recording session UUID created for this camera?
- Is the recording session properly registered with the continuous pipeline?
- Check: Camera service logs for recording start/stop events

### 4. Are Batches Being Triggered?
- Should have triggered 3 batches (5 + 5 + 8 videos)
- Check: vmeta service logs for batch trigger events
- Check: Batch processing repository for batch records

### 5. Configuration Issues?
- Is batch size correctly set (default: 5)?
- Is the collection ID correctly mapped?
- Is continuous pipeline enabled for RTSP cameras?

---

## Diagnostic Commands

```bash
# 1. Check if face detection ran on these videos
curl -s "http://localhost:8003/api/v1/person-objects/[VIDEO_UUID]" \
  -H "Authorization: Bearer $TOKEN"

# 2. Check batch processing status
curl -s "http://localhost:8008/api/v1/batch-processing/batches?limit=10" \
  -H "Authorization: Bearer $TOKEN"

# 3. Check tracking sessions
curl -s "http://localhost:8008/api/v1/cross-video/individuals/tracking/sessions?limit=10" \
  -H "Authorization: Bearer $TOKEN"

# 4. Check vmeta logs
tail -n 200 /Users/nickgklezakos/Documents/ppl-meta-code/logs/ppl-meta-vmeta.log

# 5. Check camera service logs
tail -n 200 /Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-cameras/logs/ppl-meta-cameras.log

# 6. Check vision service logs
tail -n 200 /Users/nickgklezakos/Documents/ppl-meta-code/logs/ppl-meta-vision.log
```

---

## Relevant Code Components

### Continuous Pipeline Components
1. **PollingFallbackManager** (`ppl-meta-vmeta/src/background/polling_fallback_manager.py`)
   - Monitors video accumulation
   - Triggers batches at threshold (5 videos)
   - Handles recording stop events

2. **BatchMonitor** (`ppl-meta-vmeta/src/background/batch_monitor.py`)
   - Tracks batch accumulation per collection
   - Manages batch triggering logic

3. **PipelineExecutor** (`ppl-meta-vmeta/src/background/pipeline_executor.py`)
   - Executes cross-video tracking for batches
   - Handles two-level caching (individuals + MVR)

4. **Recording Events** (`ppl-meta-cameras/src/recording/`)
   - Sends recording start/stop events
   - Notifies continuous pipeline of new videos

---

## Related Documentation

- **Continuous Pipeline Design**: `/docs/vision-vmeta/continuous-individuals-mvr-pipeline.md`
- **E2E Test**: `/tests/test_continuous_pipeline_e2e.sh`
- **Batch Processing**: `/docs/vision-vmeta/review/BATCH_PROCESSING_IMPLEMENTATION.md`
- **Quality Metrics**: `/docs/api/average-face-quality-endpoint.md`

---

## Possible Root Causes

1. **Pipeline Not Started**: PollingFallbackManager may not be running
2. **Collection Not Monitored**: RTSP collection may not be registered for monitoring
3. **Event System Broken**: Recording events not reaching batch monitor
4. **Face Detection Disabled**: Face detection may not be running on save
5. **Batch Size Misconfigured**: Batch threshold may be set too high
6. **Service Communication Issue**: vmeta not receiving video notifications

---

## Investigation Results

### Investigation Process (January 5, 2026)

**Phase 1: System State Verification**
- ✅ Confirmed 18 videos exist in collection (Jan 4, 11:43-11:58 AM)
- ✅ Verified services running (gateway, vmeta, media all healthy)
- ✅ Confirmed face detection data EXISTS (manual preview triggered V2 API)
- ✅ Found 6 faces for video 21a8f71f after manual detection

**Phase 2: Pipeline Component Analysis**
- ✅ Checked vmeta logs: PollingFallbackManager running, "waiting for recording events"
- ✅ Checked batch processing: No batch records found for this collection
- ✅ Checked camera logs: RTSP camera currently disconnected
- ✅ Checked vision logs: No processing activity for these video UUIDs

**Phase 3: Code Investigation**
- ✅ Located PollingFallbackManager in `batch_timeout_manager.py` (line 299)
- ✅ Confirmed "recording-aware mode" - waits for start/stop events
- ✅ Verified no hardcoded collection filters or threshold issues
- ✅ Found recording event endpoints in vmeta: `/api/v1/recording/started` and `/stopped`

**Phase 4: Root Cause Discovery**
- ✅ **USB cameras** (via `streaming.py`): DOES send recording events to vmeta
  - Line 486-520: Sends POST to vmeta on recording start
  - Line 575-640: Sends POST to vmeta on recording stop
- ❌ **RTSP cameras** (via `camera_detection.py`): Does NOT send recording start events
  - Only publishes recording completion event to orchestrator
  - MISSING: No vmeta notification when recording starts
  - MISSING: No vmeta notification when recording stops

### Root Cause

The continuous pipeline requires recording lifecycle events to activate polling. RTSP cameras were never sending these events, so the PollingFallbackManager remained in "waiting" state and never initiated batch processing.

**Impact**: All RTSP camera recordings since system deployment were not automatically processed through continuous pipeline.

---

## Next Steps

1. ✅ Root cause identified
2. ✅ Fix implemented in camera_detection.py
3. ⏳ Test with fresh RTSP recording
4. ⏳ Verify vmeta receives start/stop events
5. ⏳ Verify batch processing triggers automatically
6. ⏳ Confirm individuals created in database

---

## Testing Instructions

After deploying the fix:

```bash
# 1. Start RTSP camera recording
curl -X POST "http://localhost:8005/api/v1/cameras/rtsp_192.168.1.77_554/recording/start" \
  -H "Authorization: Bearer $TOKEN"

# 2. Check vmeta logs for recording start notification
tail -f logs/ppl-meta-vmeta.log | grep "Recording started"

# 3. Wait for 5+ videos to be recorded (batch size threshold)

# 4. Check vmeta logs for batch processing
tail -f logs/ppl-meta-vmeta.log | grep "batch\|trigger\|cross-video"

# 5. Stop recording
curl -X POST "http://localhost:8005/api/v1/cameras/rtsp_192.168.1.77_554/recording/stop" \
  -H "Authorization: Bearer $TOKEN"

# 6. Check vmeta logs for recording stop and final batch
tail -f logs/ppl-meta-vmeta.log | grep "Recording stopped\|final batch"

# 7. Verify individuals created
curl "http://localhost:8008/api/v1/analytics/quality-metrics?time_range=last_day" \
  -H "Authorization: Bearer $TOKEN" | jq
```

---

## Authentication Token

```bash
export TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI3IiwiZXhwIjoxNzY3NjE4OTM1fQ.VY2bqpByQH-f62DWWtPAmo5KhigLrhTkNG05TzN96Dk"
```

---

## Test Collection Details

- **Collection Name**: `rtsp_192.168.1.77_554 Collection`
- **Camera Type**: RTSP (Home Camera at 192.168.1.77)
- **Video Count**: 18 videos
- **Recording Date**: January 4, 2026 (11:43 AM - 11:58 AM)
- **Expected Batches**: 3 (5 + 5 + 8 videos)
- **Actual Individuals**: 0
- **Actual MVR People**: 0
