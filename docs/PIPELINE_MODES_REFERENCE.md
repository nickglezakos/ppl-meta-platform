# Pipeline Recording Modes - Quick Reference

## Mode Comparison Table

| Feature | Both Pipelines | Instant Only | Recording Only |
|---------|---------------|--------------|----------------|
| **Instant Detection** | ✅ Yes | ✅ Yes | ❌ No |
| **Video Recording** | ✅ Yes | ❌ No | ✅ Yes |
| **Trigger Evaluation** | ✅ Yes | ✅ Yes | ❌ No |
| **Segment Upload** | ✅ Yes | ❌ No | ✅ Yes |
| **VMeta Processing** | ✅ Yes | ❌ No | ✅ Yes |
| **Disk Usage** | High | Minimal | High |
| **CPU Usage** | High | Low | Medium |
| **Network Usage** | High | Minimal | High |

## Mode Configuration

### Both Pipelines (Default)
```json
{
  "instant_detection_enabled": true,
  "recording_pipeline_enabled": true,
  "instant_detection_interval_seconds": 5,
  "segment_duration_seconds": 30
}
```

### Instant Detection Only
```json
{
  "instant_detection_enabled": true,
  "recording_pipeline_enabled": false,
  "instant_detection_interval_seconds": 5
}
```

### Recording Only
```json
{
  "instant_detection_enabled": false,
  "recording_pipeline_enabled": true,
  "segment_duration_seconds": 30
}
```

## Use Cases

### When to Use Both Pipelines
- Full security monitoring
- Environments requiring both real-time alerts and evidence
- Compliance requirements for video retention
- High-value assets needing comprehensive monitoring

### When to Use Instant Detection Only
- Privacy-conscious environments (retail, healthcare)
- Testing trigger configurations
- Resource-constrained deployments
- Monitoring without storage requirements
- Temporary surveillance scenarios

### When to Use Recording Only
- Archival/evidence collection without real-time processing
- Continuous recording for later review
- Reducing CPU load from instant detection
- Scenarios where triggers are handled externally

## API Examples

### Check Current Settings
```bash
curl -X GET "http://localhost:8005/api/v1/cameras/usb_camera_0/pipeline-settings" \
  -H "Authorization: Bearer $TOKEN"
```

### Enable Both Pipelines
```bash
curl -X PATCH "http://localhost:8005/api/v1/cameras/usb_camera_0/pipeline-settings" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "instant_detection_enabled": true,
    "recording_pipeline_enabled": true
  }'
```

### Switch to Instant Detection Only
```bash
curl -X PATCH "http://localhost:8005/api/v1/cameras/usb_camera_0/pipeline-settings" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "instant_detection_enabled": true,
    "recording_pipeline_enabled": false
  }'
```

### Switch to Recording Only
```bash
curl -X PATCH "http://localhost:8005/api/v1/cameras/usb_camera_0/pipeline-settings" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "instant_detection_enabled": false,
    "recording_pipeline_enabled": true
  }'
```

### Adjust Intervals and Durations
```bash
curl -X PATCH "http://localhost:8005/api/v1/cameras/usb_camera_0/pipeline-settings" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "instant_detection_interval_seconds": 10,
    "segment_duration_seconds": 60
  }'
```

## Recording Behavior

### Starting Recording with Different Modes

**Both Pipelines**:
```bash
# Starts instant detection + video recording
POST /api/v1/cameras/{device_id}/recording/start
→ Creates video segments + performs instant detection
```

**Instant Detection Only**:
```bash
# Only enables instant detection
POST /api/v1/cameras/{device_id}/recording/start
→ No video files, only trigger evaluation
→ Response includes: {"mode": "instant_detection_only"}
```

**Recording Only**:
```bash
# Only starts video recording
POST /api/v1/cameras/{device_id}/recording/start
→ Creates video segments, no instant detection
```

### Stopping Recording

**Both Pipelines**:
```bash
POST /api/v1/cameras/{device_id}/recording/stop
→ Finalizes segments + stops detection if disabled in settings
```

**Instant Detection Only**:
```bash
POST /api/v1/cameras/{device_id}/recording/stop
→ Returns: {"mode": "instant_detection_only", "duration_seconds": 300}
→ No segments to finalize
```

**Recording Only**:
```bash
POST /api/v1/cameras/{device_id}/recording/stop
→ Finalizes segments, detection already stopped
```

## Resource Savings Examples

### Scenario: 10 Cameras, 8 Hours Operation

**Both Pipelines (Full)**:
- Disk: ~240 GB (10 cameras × 3 GB/hour × 8 hours)
- CPU: 100% baseline
- Network: ~240 GB upload

**Instant Detection Only**:
- Disk: ~0 GB (no video files)
- CPU: ~40% (detection only, no video encoding)
- Network: ~1 MB (only API calls)
- **Savings: 240 GB disk, 60% CPU, 240 GB network**

**Recording Only (4 cameras) + Instant Only (6 cameras)**:
- Disk: ~96 GB (4 cameras recording)
- CPU: ~64% (4 recording + 6 detection only)
- Network: ~96 GB
- **Savings: 144 GB disk, 36% CPU, 144 GB network**

## Validation Rules

### Valid Configurations
✅ Both enabled  
✅ Instant only  
✅ Recording only  

### Invalid Configurations
❌ Both disabled (returns 400 error)  
❌ Interval < 1 or > 60 seconds  
❌ Duration < 5 or > 300 seconds  

## Log Messages Reference

### Startup Logs
```
🔧 [PIPELINE-SETTINGS] device=usb_camera_0, instant_detection=true, recording=true, detection_interval=5s, segment_duration=30s
📸 [INSTANT-ONLY] Starting instant-detection-only mode for usb_camera_0
🔧 [PIPELINE-STATUS] usb_camera_0: instant_detection=✅, recording=✅
```

### Stop Logs
```
📸 [INSTANT-ONLY] Stopping instant-detection-only session for usb_camera_0
⏸️ Instant detection remains active for usb_camera_0 (enabled in settings)
✅ Auto-stopped instant detection for camera usb_camera_0 (disabled in settings)
```

## Troubleshooting

### Issue: Recording doesn't start
**Check**: Are both pipelines disabled?
```bash
curl -X GET "http://localhost:8005/api/v1/cameras/{device_id}/pipeline-settings" \
  -H "Authorization: Bearer $TOKEN"
```

### Issue: No triggers firing
**Check**: Is instant detection enabled?
```bash
# Verify instant_detection_enabled is true
# Check worker logs for detection activity
```

### Issue: No video files created
**Check**: Is recording pipeline enabled?
```bash
# Verify recording_pipeline_enabled is true
# Check for "instant_detection_only" mode in response
```

### Issue: High resource usage
**Solution**: Switch to instant-detection-only for less critical cameras
```bash
curl -X PATCH "http://localhost:8005/api/v1/cameras/{device_id}/pipeline-settings" \
  -d '{"instant_detection_enabled": true, "recording_pipeline_enabled": false}'
```

## Migration Path

### Existing Deployments
All existing cameras default to **both pipelines enabled**:
- `instant_detection_enabled = true`
- `recording_pipeline_enabled = true`
- `instant_detection_interval_seconds = 5`
- `segment_duration_seconds = 30`

No immediate changes required. Cameras continue operating as before.

### Gradual Optimization
1. **Week 1**: Identify low-priority cameras
2. **Week 2**: Switch 25% to instant-detection-only
3. **Week 3**: Monitor resource savings
4. **Week 4**: Expand to 50% if successful

## Performance Monitoring

### Metrics to Track
- Disk usage per camera
- CPU utilization per mode
- Network bandwidth per mode
- Trigger accuracy (instant vs continuous)
- Storage costs

### Expected Improvements
- **Instant-Only Migration**: 80-90% disk savings
- **Mixed Deployment**: 40-60% resource reduction
- **Recording-Only**: 30-40% CPU savings

---

**Last Updated**: January 24, 2026  
**Backend Version**: Fully Implemented ✅  
**Frontend Status**: Pending (Phase 3)
