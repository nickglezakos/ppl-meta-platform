# Instant Detection Counter - Troubleshooting & Optimization

**Date**: December 25, 2025  
**Issue**: Instant Detection Widget shows "inactive" / no results  
**Solution**: Start instant detection + optimize polling

---

## Issue Analysis

### Why Instant Detection Shows No Results

The **InstantDetectionWidget** is showing "Instant detection inactive" because:

**Root Cause**: Instant detection must be **explicitly started** via API call

```bash
# Instant detection is NOT automatic - it must be started:
curl -X POST http://localhost:8005/api/v1/instant-detection/start/usb_camera_0
```

**Current Behavior**:
1. Widget polls every 5-10 seconds for results
2. If instant detection not started → API returns 404/no results
3. Widget shows "Instant detection inactive" state
4. No error - this is expected behavior

---

## Solution 1: Manual Start (Quick Fix)

### Start Instant Detection Manually

```bash
# For each camera you want to monitor:
curl -X POST http://localhost:8005/api/v1/instant-detection/start/usb_camera_0
curl -X POST http://localhost:8005/api/v1/instant-detection/start/usb_camera_1
# etc.
```

**After starting**:
- Widget will auto-detect instant detection is running
- Switches to fast polling (5 seconds)
- Shows live person count with demographics

### Verify It's Working

```bash
# Check status
curl http://localhost:8005/api/v1/instant-detection/results/usb_camera_0 | jq

# Expected response:
{
  "success": true,
  "person_objects": [...],
  "_metadata": {
    "cached_at": 1735142400.0,
    "iteration": 5,
    "age_seconds": 2.3
  }
}
```

---

## Solution 2: Auto-Start with Recording (Recommended)

### Current Recording Flow

The recording start already has an `enable_instant_detection` parameter:

**Frontend** (`camera_service.dart`):
```dart
Future<RecordingResult> startRecording(
  String deviceId, 
  {bool enableInstantDetection = true}  // ✅ Already defaults to true
)
```

**Backend Endpoint**:
```
POST /api/v1/streaming/{deviceId}/record/start?enable_instant_detection=true
```

**This means**: When you start recording, instant detection **should** auto-start!

### Check If It's Working

1. **Start Recording** via UI (click red record button)
2. **Wait 5 seconds**
3. **Check Widget** - should show "Live: X people"

If still showing "inactive":

**Debug Steps**:
```bash
# 1. Check if recording is active
curl http://localhost:8005/api/v1/streaming/status

# 2. Check if instant detection started
curl http://localhost:8005/api/v1/instant-detection/results/usb_camera_0

# 3. Check backend logs
tail -f ppl-meta-cameras/logs/*.log | grep "instant.detection"
```

---

## Solution 3: Optimize Polling (Stop When Not Recording)

### Current Polling Behavior

**Current Implementation**:
- **Lazy Check**: Every 10 seconds when inactive
- **Fast Poll**: Every 5 seconds when active
- **Auto-Switch**: Detects when instant detection starts/stops

**Problem**: Continues polling even when camera not recording

### Recommended Optimization

Stop polling when recording is not active:

**Updated Widget Logic**:

```dart
class _InstantDetectionWidgetState extends ConsumerState<InstantDetectionWidget> {
  @override
  void initState() {
    super.initState();
    // Only start checking if camera is recording
    _checkAndStartPolling();
  }

  void _checkAndStartPolling() {
    // Watch recording state
    ref.listen(cameraRecordingProvider(widget.cameraId), (previous, next) {
      if (next.isRecording && !_isInstantDetectionRunning) {
        // Recording started - check for instant detection
        _fetchInstantResults();
      } else if (!next.isRecording && _isInstantDetectionRunning) {
        // Recording stopped - stop polling
        _stopAutoRefresh();
      }
    });
    
    // Initial check
    final recordingState = ref.read(cameraRecordingProvider(widget.cameraId));
    if (recordingState.isRecording) {
      _startLazyChecking();
    }
  }
}
```

**Benefits**:
- ✅ No polling when not recording
- ✅ Auto-starts when recording begins
- ✅ Auto-stops when recording ends
- ✅ Reduces network traffic
- ✅ Saves backend resources

---

## Implementation: Optimized Instant Detection Widget

### File: `ppl-meta-frontend/lib/widgets/camera/instant_detection_widget.dart`

**Changes Needed**:

1. **Add Recording State Listener**:
```dart
@override
void initState() {
  super.initState();
  print('🔍 [INSTANT_DETECTION_WIDGET] initState called for device: ${widget.cameraId}');
  
  // Watch recording state to control polling
  _setupRecordingListener();
  
  // Check if already recording
  _checkInitialRecordingState();
}

void _setupRecordingListener() {
  // This will be called whenever recording state changes
  ref.listen(cameraRecordingProvider(widget.cameraId), (previous, next) {
    print('🔍 [INSTANT_DETECTION_WIDGET] Recording state changed: ${next.isRecording}');
    
    if (next.isRecording && !_isInstantDetectionRunning) {
      // Recording started - begin checking for instant detection
      print('🔍 [INSTANT_DETECTION_WIDGET] Recording started, starting lazy checks');
      _startLazyChecking();
    } else if (!next.isRecording && _isInstantDetectionRunning) {
      // Recording stopped - stop polling
      print('🔍 [INSTANT_DETECTION_WIDGET] Recording stopped, stopping polling');
      _stopAutoRefresh();
    }
  });
}

void _checkInitialRecordingState() {
  final recordingState = ref.read(cameraRecordingProvider(widget.cameraId));
  if (recordingState.isRecording) {
    print('🔍 [INSTANT_DETECTION_WIDGET] Already recording, starting lazy checks');
    _startLazyChecking();
  } else {
    print('🔍 [INSTANT_DETECTION_WIDGET] Not recording, staying idle');
    // Don't start polling - wait for recording to begin
  }
}
```

2. **Update Widget Display for Not Recording**:
```dart
// If not recording and not running, show "Start recording to see live detection"
if (!_isInstantDetectionRunning && !_isLoading) {
  final recordingState = ref.watch(cameraRecordingProvider(widget.cameraId));
  
  if (!recordingState.isRecording) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: Colors.grey.withOpacity(0.02),
        border: Border(
          top: BorderSide(
            color: Colors.grey.withOpacity(0.1),
            width: 1,
          ),
        ),
      ),
      child: Row(
        children: [
          Icon(
            Icons.videocam_off,
            size: 13,
            color: Colors.grey.shade400,
          ),
          const SizedBox(width: 6),
          Text(
            'Start recording to see live detection',
            style: OfflineFonts.inter(
              fontSize: 11,
              color: Colors.grey.shade500,
            ),
          ),
        ],
      ),
    );
  }
  
  // Recording but no instant detection - show check button
  return Container(
    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
    decoration: BoxDecoration(
      color: Colors.grey.withOpacity(0.02),
      border: Border(
        top: BorderSide(
          color: Colors.grey.withOpacity(0.1),
          width: 1,
        ),
      ),
    ),
    child: Row(
      children: [
        Icon(
          Icons.visibility_off,
          size: 13,
          color: Colors.grey.shade400,
        ),
        const SizedBox(width: 6),
        Text(
          'Instant detection inactive',
          style: OfflineFonts.inter(
            fontSize: 11,
            color: Colors.grey.shade500,
          ),
        ),
        const Spacer(),
        InkWell(
          onTap: _fetchInstantResults,
          child: Padding(
            padding: const EdgeInsets.all(4),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.refresh, size: 14, color: Colors.grey.shade600),
                const SizedBox(width: 4),
                Text(
                  'Check',
                  style: OfflineFonts.inter(
                    fontSize: 11,
                    color: Colors.grey.shade600,
                  ),
                ),
              ],
            ),
          ),
        ),
      ],
    ),
  );
}
```

---

## Testing the Optimized Version

### Test 1: Not Recording

**Initial State**:
1. Open cameras screen
2. Connect to a camera (don't start recording)
3. **Expected**: Widget shows "Start recording to see live detection"
4. **Expected**: No polling happening (check network tab)

### Test 2: Start Recording

**Recording Start**:
1. Click "Start Recording"
2. **Expected**: Widget starts lazy checking (every 10s)
3. After 5-10 seconds, if instant detection running:
   - Widget switches to fast polling (5s)
   - Shows "Live: X people"
4. **Expected**: Network requests every 5 seconds

### Test 3: Stop Recording

**Recording Stop**:
1. Click "Stop Recording"
2. **Expected**: Widget stops polling immediately
3. **Expected**: Shows "Start recording to see live detection"
4. **Expected**: No more network requests

---

## Summary of Changes

### Immediate Fix (No Code Changes)

**Manually start instant detection**:
```bash
curl -X POST http://localhost:8005/api/v1/instant-detection/start/usb_camera_0
```

Then widget will automatically detect and display results.

### Optimization (Recommended Code Changes)

**Stop polling when not recording**:
1. Add recording state listener in `initState()`
2. Only poll when `isRecording = true`
3. Auto-stop when recording ends

**Benefits**:
- ✅ Reduces unnecessary API calls
- ✅ Better performance
- ✅ Clearer user feedback
- ✅ Automatic lifecycle management

---

## Verification Checklist

### Current Behavior ✅
- [x] MVR counter working perfectly
- [ ] Instant detection showing "inactive"
- [ ] Polling continues even when not recording

### After Manual Start 🎯
- [ ] Instant detection shows live results
- [ ] Demographics display correctly
- [ ] Updates every 5 seconds
- [ ] Still polls even when not recording

### After Optimization 🚀
- [ ] Shows "Start recording" when not recording
- [ ] Auto-checks when recording starts
- [ ] Shows live results during recording
- [ ] Stops polling when recording stops
- [ ] No unnecessary network requests

---

## Next Steps

### Option A: Quick Fix (5 minutes)

1. Start instant detection manually for active cameras
2. Verify widget shows live results
3. Keep current polling behavior

### Option B: Implement Optimization (30 minutes)

1. Update `instant_detection_widget.dart` with recording listener
2. Test recording lifecycle
3. Verify polling stops when not recording
4. Deploy updated widget

### Recommendation

**Start with Option A** to verify everything works, then **implement Option B** for production optimization.

---

**Document Version**: 1.0  
**Last Updated**: December 25, 2025  
**Status**: Solution Ready
