# Camera Counters Integration - Quick Test Guide

**Date**: December 25, 2025  
**Implementation**: COMPLETED ✅  
**Files Changed**: 2 files

---

## What Was Changed

### 1. Camera Stream Screen
**File**: `ppl-meta-frontend/lib/presentation/pages/camera_stream_page.dart`

**Added**: Two counter widgets in control bar
- CameraCounterWidget (left side)
- InstantDetectionWidget (right side)

### 2. Camera Card
**File**: `ppl-meta-frontend/lib/presentation/widgets/camera/camera_card.dart`

**Added**: Two counter widgets stacked vertically
- CameraCounterWidget (full width)
- InstantDetectionWidget (full width)

---

## Quick Test Steps

### Test 1: Launch App

```bash
cd ppl-meta-frontend
flutter run -d chrome
```

**Expected**: App compiles and launches without errors

---

### Test 2: Check Cameras Screen

1. Navigate to `http://localhost:3000/#/cameras`
2. Look at any camera card

**Expected to See**:
```
Camera Card:
├── Camera name and status
├── Resolution info
├── 👥 MVR Counter Widget (new!)
│   └── Shows people count, videos, demographics
├── ● Instant Detection Widget (new!)
│   └── Shows live detections, demographics
└── Action buttons
```

---

### Test 3: Check Camera Stream

1. Click on a camera card
2. Click "View stream" icon (▶️)

**Expected to See**:
```
Stream Page:
├── Video stream (top, full width)
└── Control bar (bottom)
    ├── Recording status (if recording)
    ├── [MVR Counter] [Instant Detection] (new!)
    └── [Back] [Start/Stop Recording] [Fullscreen]
```

---

### Test 4: Recording Workflow

**In Stream Page**:

1. Click "Start Recording"
   - ✅ Recording status appears
   - ✅ Counters remain visible
   - ✅ Timer updates every second
   
2. Wait 5 seconds
   - ✅ Instant detection updates
   
3. Click "Stop Recording"
   - ✅ Recording status disappears
   - ✅ Counters still visible

---

### Test 5: Multiple Cameras

**In Cameras Screen**:

1. Look at all camera cards
   - ✅ Each shows both counters
   - ✅ Counts are independent
   - ✅ Loading states work
   
2. Connect multiple cameras
   - ✅ Instant detection works per camera
   - ✅ No interference between cameras

---

## Visual Reference

### Camera Stream Control Bar

```
┌─────────────────────────────────────────┐
│ [🔴 Recording: 02:34  125 MB]           │ ← If recording
├─────────────────────────────────────────┤
│ ┌────────────┐ ┌──────────────┐        │
│ │ 👥 14 Ppl  │ │ ● Live: 3    │        │ ← New counters
│ │ 📹 10 Vids │ │ 👨 2  👩 1    │        │
│ └────────────┘ └──────────────┘        │
├─────────────────────────────────────────┤
│ [◀] [⏺️ Start Recording] [⛶]            │
└─────────────────────────────────────────┘
```

### Camera Card Layout

```
┌──────────────────────────────────────────┐
│ 📹 Camera Name             [folder] [●]  │
│ Model • 1920x1080                        │
├──────────────────────────────────────────┤
│ ┌──────────────────────────────────────┐ │
│ │ 👥 14 People  📹 10 Videos           │ │ ← MVR Counter
│ │ 👨 8  👩 6  🧒 3  👤 11              │ │
│ │ Today ▼  (5 min ago)  🔄            │ │
│ └──────────────────────────────────────┘ │
├──────────────────────────────────────────┤
│ ┌──────────────────────────────────────┐ │
│ │ ● Live: 3 people • 2.3s ago  🔄     │ │ ← Instant Detect
│ │ 👨 2  👩 1  🧒 1  👤 2              │ │
│ └──────────────────────────────────────┘ │
├──────────────────────────────────────────┤
│ [Active]     [Connect] [⏺️] [▶]          │
└──────────────────────────────────────────┘
```

---

## Common Issues & Solutions

### Issue: Counters not showing

**Check**:
1. Are the widgets imported correctly?
2. Does `camera.deviceId` exist?
3. Check browser console for errors

**Solution**:
```bash
# Restart Flutter
flutter clean
flutter pub get
flutter run -d chrome
```

---

### Issue: Compilation errors

**Error**: Cannot find CameraCounterWidget

**Solution**: Verify imports at top of files:
```dart
import '../../widgets/camera/camera_counter_widget.dart';
import '../../widgets/camera/instant_detection_widget.dart';
```

---

### Issue: Counters show 0 or no data

**Check Backend Services**:
```bash
# In separate terminals:
cd ppl-meta-media && uvicorn src.main:app --port 8000
cd ppl-meta-vmeta && uvicorn src.main:app --port 8008
cd ppl-meta-cameras && uvicorn src.main:app --port 8005
```

**Test Health**:
```bash
curl http://localhost:8000/health  # Media service
curl http://localhost:8008/health  # VMeta service
curl http://localhost:8005/health  # Camera service
```

---

### Issue: Stream freezes when counters update

**This should NOT happen** - counters are isolated

**If it does**:
1. Check RepaintBoundary is still wrapping stream player
2. Check timer intervals (should be 5s for instant, 5min for MVR)
3. Look for console warnings about rebuilds

---

## Performance Expectations

### Normal Behavior

| Metric | Expected Value |
|--------|---------------|
| Stream FPS | 15-30 fps (smooth) |
| Counter Load Time | <500ms |
| Instant Detection Update | Every 5s |
| MVR Counter Update | Every 5 min |
| Memory Usage | <200MB per camera |

### Warning Signs

- ❌ Stream drops below 10 fps
- ❌ Counters take >2 seconds to load
- ❌ Counter updates cause visible lag
- ❌ Memory increases continuously

---

## Success Criteria

### ✅ All Tests Passing

- [ ] App compiles without errors
- [ ] Counters appear in camera cards
- [ ] Counters appear in stream page
- [ ] Recording workflow works correctly
- [ ] Multiple cameras work independently
- [ ] Auto-refresh works
- [ ] Manual refresh works
- [ ] Demographics display correctly
- [ ] Stream plays smoothly
- [ ] No console errors

### 🎯 User Experience Goals

- Counter data loads quickly (<500ms)
- Updates are smooth (no stuttering)
- Visual layout is clean and readable
- Information is useful and actionable
- Multiple cameras don't interfere

---

## Next Steps After Testing

### If All Tests Pass ✅

1. Commit changes:
   ```bash
   git add ppl-meta-frontend/lib/presentation/pages/camera_stream_page.dart
   git add ppl-meta-frontend/lib/presentation/widgets/camera/camera_card.dart
   git commit -m "feat: integrate MVR counter and instant detection widgets into camera UI"
   ```

2. Update main README with new features
3. Consider adding screenshots to docs

### If Tests Fail ❌

1. Check console for specific errors
2. Verify backend services are running
3. Test each widget independently
4. Review widget implementation files
5. Check network requests in browser DevTools

---

## Support

**Documentation**:
- [Camera Counters Integration Guide](./camera-counters-integration.md)
- [Camera Card MVR Counter](./camera-card-mvr-counter.md)
- [Instant Detection Widget](./instant-detection-widget-frontend.md)

**Code Files**:
- `ppl-meta-frontend/lib/widgets/camera/camera_counter_widget.dart`
- `ppl-meta-frontend/lib/widgets/camera/instant_detection_widget.dart`
- `ppl-meta-frontend/lib/presentation/pages/camera_stream_page.dart`
- `ppl-meta-frontend/lib/presentation/widgets/camera/camera_card.dart`

**Related Services**:
- Media Service: `ppl-meta-media` (Port 8000)
- VMeta Service: `ppl-meta-vmeta` (Port 8008)
- Camera Service: `ppl-meta-cameras` (Port 8005)

---

**Last Updated**: December 25, 2025  
**Status**: Ready for Testing  
**Version**: 1.0
