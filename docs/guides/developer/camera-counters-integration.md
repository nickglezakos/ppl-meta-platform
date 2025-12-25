# Camera Counters Integration Guide

**Date**: December 25, 2025  
**Status**: Implementation in Progress  
**Features**: MVR People Counter + Instant Detection Widget

---

## Overview

This document describes the integration of two counter widgets into the camera interface:

1. **CameraCounterWidget** - Shows unique MVR people detected (historical data from database)
2. **InstantDetectionWidget** - Shows real-time face detection from instant detection cache

### Integration Locations

Both counters will appear in two places:

#### 1. Camera Stream Screen
**Location**: `ppl-meta-frontend/lib/presentation/pages/camera_stream_page.dart`  
**Placement**: In the control bar below the video stream, alongside the start/stop recording button and timer

#### 2. Camera Card
**Location**: `ppl-meta-frontend/lib/presentation/widgets/camera/camera_card.dart`  
**Placement**: Within the camera card, below camera details

---

## Widget Specifications

### CameraCounterWidget

**File**: `ppl-meta-frontend/lib/widgets/camera/camera_counter_widget.dart`

**Features**:
- Displays unique MVR people count
- Time filter options (today, week, month, all time)
- Auto-refresh every 5 minutes
- Manual refresh button
- Shows demographics (gender, age breakdown)
- Cache status indicator

**Display Format**:
```
👥 14 People
📹 10 Videos
👨 8  👩 6
🧒 3  👤 11
(cached: 5 min ago)
```

**Props**:
```dart
CameraCounterWidget({
  required String cameraId,
  Duration refreshInterval = const Duration(minutes: 5),
})
```

---

### InstantDetectionWidget

**File**: `ppl-meta-frontend/lib/widgets/camera/instant_detection_widget.dart`

**Features**:
- Real-time face detection results
- Auto-refresh every 5 seconds
- Shows person count with demographics
- Active/inactive status indicator
- Iteration counter

**Display Format**:
```
● Live: 3 people • 2.3s ago  🔄
  👨 2  👩 1  🧒 1  👤 2
```

**Props**:
```dart
InstantDetectionWidget({
  required String cameraId,
  Duration refreshInterval = const Duration(seconds: 5),
})
```

---

## Implementation Changes

### 1. Camera Stream Screen Integration

**File**: `ppl-meta-frontend/lib/presentation/pages/camera_stream_page.dart`

**Location**: In the control bar `Container` (currently at line 49), after the recording status bar

**Changes**:
1. Add imports for both widgets
2. Add counter widgets in the Column layout
3. Place them before or after the control buttons Row

**Layout Structure** (after changes):
```dart
Container(
  color: Colors.black.withOpacity(0.8),
  padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 16),
  child: Column(
    mainAxisSize: MainAxisSize.min,
    children: [
      // Recording status (if recording)
      if (recordingState.isRecording) ...[
        _RecordingStatusBar(cameraId: camera.deviceId),
        const SizedBox(height: 8),
      ],
      
      // ✨ NEW: Counter Widgets
      Row(
        children: [
          Expanded(
            child: CameraCounterWidget(cameraId: camera.deviceId),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: InstantDetectionWidget(cameraId: camera.deviceId),
          ),
        ],
      ),
      const SizedBox(height: 8),
      
      // Control buttons row
      Row(
        mainAxisAlignment: MainAxisAlignment.spaceEvenly,
        children: [
          // ... existing buttons
        ],
      ),
    ],
  ),
)
```

**Visual Layout**:
```
┌─────────────────────────────────────────────────┐
│          CAMERA STREAM (video)                  │
│                                                 │
└─────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────┐
│ Control Bar (black with opacity)                │
│                                                 │
│ [Recording Status Bar] (if recording)           │
│                                                 │
│ ┌──────────────────┐ ┌──────────────────┐     │
│ │ MVR Counter      │ │ Instant Detect   │     │
│ │ 👥 14 People     │ │ ● Live: 3 people │     │
│ │ 📹 10 Videos     │ │ 👨 2  👩 1        │     │
│ └──────────────────┘ └──────────────────┘     │
│                                                 │
│ [◀ Back]  [⏺️ Stop Recording]  [⛶ Fullscreen] │
│                                                 │
└─────────────────────────────────────────────────┘
```

---

### 2. Camera Card Integration

**File**: `ppl-meta-frontend/lib/presentation/widgets/camera/camera_card.dart`

**Location**: In the card's Column widget (around line 40), after camera details and before action buttons

**Changes**:
1. Add imports for both widgets
2. Add counter widgets after the resolution/device ID section
3. Place them before the stream section or recording controls

**Layout Structure** (after changes):
```dart
Card(
  child: InkWell(
    child: Padding(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header with status indicator
          Row(...),  // Camera name, status
          
          const SizedBox(height: 12),
          
          // Camera details (manufacturer, model, resolution, etc.)
          // ... existing widgets ...
          
          const SizedBox(height: 12),
          
          // ✨ NEW: Counter Widgets
          CameraCounterWidget(
            cameraId: camera.deviceId,
          ),
          const SizedBox(height: 8),
          InstantDetectionWidget(
            cameraId: camera.deviceId,
          ),
          
          const SizedBox(height: 12),
          
          // Action buttons, stream player, etc.
          // ... existing widgets ...
        ],
      ),
    ),
  ),
)
```

**Visual Layout**:
```
┌─────────────────────────────────────────────────┐
│ 📹 Front Door Camera              [folder] [●]  │
│                                                 │
│ Manufacturer Model                              │
│ 🎬 1920x1080                                    │
│ 📱 usb_camera_0                                 │
│                                                 │
│ ╔═════════════════════════════════════════════╗ │
│ ║ 👥 14 People  📹 10 Videos                  ║ │
│ ║ 👨 8  👩 6  🧒 3  👤 11                      ║ │
│ ║ (cached: 5 min ago)  🔄                     ║ │
│ ╚═════════════════════════════════════════════╝ │
│                                                 │
│ ╔═════════════════════════════════════════════╗ │
│ ║ ● Live: 3 people • 2.3s ago  🔄             ║ │
│ ║ 👨 2  👩 1  🧒 1  👤 2                       ║ │
│ ╚═════════════════════════════════════════════╝ │
│                                                 │
│ [Connect]  [⏺️ Start Recording]                │
│                                                 │
│ [STREAM VIEW if connected]                      │
│                                                 │
└─────────────────────────────────────────────────┘
```

---

## Key Design Decisions

### 1. Placement Strategy

**Camera Stream Screen**:
- **Before control buttons**: Shows context before user takes action
- **Side-by-side layout**: Efficient use of horizontal space
- **Compact mode**: Both widgets show condensed information

**Camera Card**:
- **After details, before actions**: Logical flow of information
- **Stacked layout**: Each widget gets full width for better readability
- **Full detail mode**: Widgets show complete information including demographics

### 2. Responsive Design

Both placements respect the existing layout:
- **No overlay**: Counters are adjacent widgets, not stacked
- **RepaintBoundary**: Stream player remains isolated
- **Independent rebuilds**: Counters don't affect stream performance

### 3. Visual Consistency

**Color Scheme**:
- MVR Counter: Green accent (historical data)
- Instant Detection: Blue accent (real-time data)
- Recording status: Red accent (active recording)

**Typography**:
- Consistent icon sizes (16px for counters)
- Clear labels with emojis for quick recognition
- Monospace for timer displays

---

## Implementation Status

### ✅ Completed Changes

#### 1. Camera Stream Screen
**File**: `ppl-meta-frontend/lib/presentation/pages/camera_stream_page.dart`

**Changes Made**:
- ✅ Added imports for `CameraCounterWidget` and `InstantDetectionWidget`
- ✅ Added counter widgets in side-by-side layout within control bar
- ✅ Positioned counters between recording status and control buttons
- ✅ Used `Row` with `Expanded` for responsive layout

**Code Added** (lines ~8-9):
```dart
import '../../widgets/camera/camera_counter_widget.dart';
import '../../widgets/camera/instant_detection_widget.dart';
```

**Code Added** (lines ~56-72):
```dart
// Counter widgets - side by side
Row(
  children: [
    Expanded(
      child: CameraCounterWidget(
        cameraId: camera.deviceId,
      ),
    ),
    const SizedBox(width: 8),
    Expanded(
      child: InstantDetectionWidget(
        cameraId: camera.deviceId,
      ),
    ),
  ],
),
const SizedBox(height: 8),
```

---

#### 2. Camera Card
**File**: `ppl-meta-frontend/lib/presentation/widgets/camera/camera_card.dart`

**Changes Made**:
- ✅ Added imports for `CameraCounterWidget` and `InstantDetectionWidget`
- ✅ Added counter widgets in stacked layout after camera details
- ✅ Positioned counters between resolution info and recording status
- ✅ Each widget gets full width for detailed information display

**Code Added** (lines ~11-12):
```dart
import '../../../widgets/camera/camera_counter_widget.dart';
import '../../../widgets/camera/instant_detection_widget.dart';
```

**Code Added** (lines ~113-122):
```dart
// Counter widgets - MVR People Counter
CameraCounterWidget(
  cameraId: camera.deviceId,
),
const SizedBox(height: 8),

// Counter widgets - Instant Detection
InstantDetectionWidget(
  cameraId: camera.deviceId,
),
```

---

## Verification Steps

### 1. Verify Compilation

Run the Flutter app to check for compilation errors:

```bash
cd ppl-meta-frontend
flutter pub get
flutter run -d chrome  # Or your preferred device
```

**Expected**: No compilation errors, app launches successfully

---

### 2. Test Camera Stream Screen

1. **Navigate to camera stream**:
   - Open app at `http://localhost:3000/#/cameras`
   - Click on a camera card
   - Click "View stream" icon (play button)

2. **Verify counter display**:
   - ✅ MVR counter appears on left side of control bar
   - ✅ Instant detection widget appears on right side
   - ✅ Both widgets show loading states initially
   - ✅ Counters update with data after loading

3. **Test recording workflow**:
   - Click "Start Recording"
   - ✅ Recording status bar appears above counters
   - ✅ Counters remain visible and functional
   - ✅ Timer updates every second
   - ✅ Stream continues playing smoothly
   - Click "Stop Recording"
   - ✅ Recording status disappears
   - ✅ Counters remain visible

4. **Test counter functionality**:
   - ✅ MVR counter shows people count
   - ✅ Instant detection shows real-time detections
   - ✅ Manual refresh works (clock icon)
   - ✅ Time filter changes work (MVR counter dropdown)
   - ✅ Demographics display correctly

---

### 3. Test Camera Card

1. **Navigate to cameras screen**:
   - Open app at `http://localhost:3000/#/cameras`

2. **Verify counter display**:
   - ✅ Each camera card shows both counters
   - ✅ MVR counter appears first (stacked vertically)
   - ✅ Instant detection widget appears below MVR counter
   - ✅ Counters take full width of card
   - ✅ Spacing looks appropriate

3. **Test multiple cameras**:
   - ✅ Each camera shows independent counts
   - ✅ Counters don't interfere with each other
   - ✅ Cards remain responsive

4. **Test camera actions**:
   - Click "Connect" on a camera
   - ✅ Counters remain visible
   - ✅ Recording controls appear
   - ✅ Stream thumbnail (if enabled) doesn't overlap counters
   - Click recording button
   - ✅ Recording status row appears
   - ✅ Counters still visible and updating

---

### 4. Performance Testing

1. **Stream performance**:
   - Open stream page
   - ✅ Video plays smoothly (no stuttering)
   - ✅ Counter updates don't cause frame drops
   - ✅ Recording timer updates smoothly

2. **Multiple cameras**:
   - Have 3+ cameras on cameras screen
   - ✅ All counters load independently
   - ✅ No cascade failures if one counter fails
   - ✅ Page remains responsive

3. **Auto-refresh behavior**:
   - Wait 5 seconds (instant detection)
   - ✅ Instant detection updates automatically
   - Wait 5 minutes (MVR counter)
   - ✅ MVR counter refreshes automatically
   - ✅ No visible performance impact

---

### 5. Visual Consistency

**Camera Stream Screen**:
```
Expected Layout:
┌─────────────────────────────────────────────────┐
│          CAMERA STREAM (video playing)          │
└─────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────┐
│ [Recording: ● 02:34  125.3 MB] (if recording)  │
│                                                 │
│ ┌──────────────────┐ ┌──────────────────┐     │
│ │ 👥 14 People     │ │ ● Live: 3 people │     │
│ │ 📹 10 Videos     │ │ 👨 2  👩 1        │     │
│ │ 👨 8  👩 6        │ │ 🧒 1  👤 2        │     │
│ │ (5 min ago) 🔄   │ │ 2.3s ago  🔄     │     │
│ └──────────────────┘ └──────────────────┘     │
│                                                 │
│ [◀ Back]  [⏺️ Start Recording]  [⛶ Fullscreen] │
└─────────────────────────────────────────────────┘
```

**Camera Card**:
```
Expected Layout:
┌─────────────────────────────────────────────────┐
│ 📹 Front Door Camera              [folder] [●]  │
│                                                 │
│ Manufacturer Model                              │
│ 🎬 1920x1080                                    │
│                                                 │
│ ┌───────────────────────────────────────────┐  │
│ │ 👥 14 People  📹 10 Videos                 │  │
│ │ 👨 8  👩 6  🧒 3  👤 11                     │  │
│ │ Today ▼  (cached: 5 min ago)  🔄          │  │
│ └───────────────────────────────────────────┘  │
│                                                 │
│ ┌───────────────────────────────────────────┐  │
│ │ ● Live: 3 people • 2.3s ago  🔄           │  │
│ │ 👨 2  👩 1  🧒 1  👤 2                     │  │
│ └───────────────────────────────────────────┘  │
│                                                 │
│ [Active]                [Connect]  [⏺️]  [▶]  │
└─────────────────────────────────────────────────┘
```

---

## Testing Checklist

### Camera Stream Screen

- [ ] Counters appear below recording status
- [ ] Counters are side-by-side
- [ ] Stream performance not affected by counter updates
- [ ] Recording button remains functional
- [ ] Timer updates correctly
- [ ] Counters update independently
- [ ] Back button works
- [ ] Fullscreen button works

### Camera Card

- [ ] Counters appear after camera details
- [ ] Counters are stacked vertically
- [ ] Full demographics displayed
- [ ] Manual refresh works
- [ ] Time filter changes work (MVR counter)
- [ ] Card remains responsive
- [ ] Connect/disconnect works
- [ ] Recording controls work

### Cross-Screen Consistency

- [ ] Same camera shows same counts in both places
- [ ] Updates propagate between screens
- [ ] Navigation doesn't break state
- [ ] Multiple cameras show different counts

---

## Performance Considerations

### Auto-Refresh Intervals

| Widget | Interval | Reason |
|--------|----------|--------|
| CameraCounterWidget | 5 minutes | Database query, cached data |
| InstantDetectionWidget | 5 seconds | Memory cache, lightweight |
| Recording Timer | 1 second | Local state, no API |

### Optimization Strategies

1. **Caching**: MVR counter uses 5-minute server-side cache
2. **Conditional Rendering**: Instant detection only polls when active
3. **Widget Isolation**: RepaintBoundary prevents stream rebuilds
4. **Lazy Loading**: Counters fetch data only when mounted

---

## Future Enhancements

### Possible Additions

1. **Click to Expand**: Tap counter to see detailed breakdown
2. **History Graph**: Mini sparkline showing detection trends
3. **Alert Indicators**: Highlight when specific person detected
4. **Configurable Filters**: User-selectable time ranges
5. **Export Data**: Download counter data as CSV

### WebSocket Updates

Replace polling with real-time push notifications:
- VMeta publishes MVR events to Redis
- Gateway forwards to WebSocket clients
- Counters update instantly on new detections

---

## Conclusion

This integration provides users with comprehensive visibility into camera activity:

**Benefits**:
- ✅ **Historical Context**: MVR counter shows detection patterns
- ✅ **Real-Time Awareness**: Instant detection shows live activity
- ✅ **Dual Visibility**: Same info available in stream and card views
- ✅ **Performance Optimized**: Independent widgets don't impact streaming
- ✅ **User-Friendly**: Clear visual indicators and demographics

The implementation maintains the existing architecture while adding valuable functionality without performance degradation.

**Document Version**: 1.0  
**Last Updated**: December 25, 2025  
**Status**: Implementation Ready
