# Camera Counters Visual Integration Map

**Date**: December 25, 2025  
**Purpose**: Visual reference for where counters are integrated

---

## Camera Stream Page Layout

### Before Integration
```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│              📹 CAMERA STREAM (video)                       │
│                                                             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│  CONTROL BAR (black with opacity)                           │
│                                                             │
│  🔴 Recording: 02:34  125.3 MB  (if recording)             │
│                                                             │
│  [◀ Back]   [⏺️ Stop Recording]   [⛶ Fullscreen]          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### After Integration ✨
```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│              📹 CAMERA STREAM (video)                       │
│                                                             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│  CONTROL BAR (black with opacity)                           │
│                                                             │
│  🔴 Recording: 02:34  125.3 MB  (if recording)             │
│                                                             │
│  ╔════════════════════════╗  ╔═══════════════════════╗    │
│  ║ 👥 14 People           ║  ║ ● Live: 3 people      ║ ⬅ NEW
│  ║ 📹 10 Videos           ║  ║ 👨 2  👩 1  🧒 1       ║    │
│  ║ 👨 8  👩 6  🧒 3       ║  ║ 2.3s ago  🔄         ║    │
│  ║ Today ▼  (5m ago)  🔄  ║  ║                       ║    │
│  ╚════════════════════════╝  ╚═══════════════════════╝    │
│                                                             │
│  [◀ Back]   [⏺️ Stop Recording]   [⛶ Fullscreen]          │
│                                                             │
└─────────────────────────────────────────────────────────────┘

  Left Counter              Right Counter
  ↓                         ↓
  CameraCounterWidget       InstantDetectionWidget
  (Historical MVR)          (Real-time Detection)
```

---

## Camera Card Layout

### Before Integration
```
┌───────────────────────────────────────────────────────┐
│ 📹 Front Door Camera              [folder] [●]        │
│                                                       │
│ Logitech C920                                         │
│ 🎬 1920x1080                                          │
│ 📱 usb_camera_0                                       │
│                                                       │
│ [Recording: ● 02:34  125.3 MB]  (if recording)       │
│                                                       │
│ [Active]        [Connect]  [⏺️]  [▶]                 │
│                                                       │
│ ┌─────────────────────────────────────────────────┐  │
│ │                                                 │  │
│ │         📹 STREAM PREVIEW                       │  │
│ │        (if connected)                           │  │
│ │                                                 │  │
│ └─────────────────────────────────────────────────┘  │
│                                                       │
└───────────────────────────────────────────────────────┘
```

### After Integration ✨
```
┌───────────────────────────────────────────────────────┐
│ 📹 Front Door Camera              [folder] [●]        │
│                                                       │
│ Logitech C920                                         │
│ 🎬 1920x1080                                          │
│ 📱 usb_camera_0                                       │
│                                                       │
│ ╔═════════════════════════════════════════════════╗  │
│ ║ 👥 14 People  📹 10 Videos                      ║ ⬅ NEW
│ ║ 👨 8  👩 6  🧒 3  👤 11                         ║  │
│ ║ Today ▼  (cached: 5 min ago)  🔄              ║  │
│ ╚═════════════════════════════════════════════════╝  │
│                                                       │
│ ╔═════════════════════════════════════════════════╗  │
│ ║ ● Live: 3 people • 2.3s ago  🔄                ║ ⬅ NEW
│ ║ 👨 2  👩 1  🧒 1  👤 2                         ║  │
│ ╚═════════════════════════════════════════════════╝  │
│                                                       │
│ [Recording: ● 02:34  125.3 MB]  (if recording)       │
│                                                       │
│ [Active]        [Connect]  [⏺️]  [▶]                 │
│                                                       │
│ ┌─────────────────────────────────────────────────┐  │
│ │                                                 │  │
│ │         📹 STREAM PREVIEW                       │  │
│ │        (if connected)                           │  │
│ │                                                 │  │
│ └─────────────────────────────────────────────────┘  │
│                                                       │
└───────────────────────────────────────────────────────┘

    Top Counter: CameraCounterWidget (MVR People)
    Bottom Counter: InstantDetectionWidget (Real-time)
```

---

## Widget Component Breakdown

### CameraCounterWidget (Left/Top)

```
╔════════════════════════════════════╗
║ 👥 14 People  📹 10 Videos         ║  ← Header row
║ ─────────────────────────────────  ║
║ 👨 8  👩 6        Gender breakdown ║  ← Demographics
║ 🧒 3  👤 11       Age breakdown    ║
║ ─────────────────────────────────  ║
║ Today ▼  (5 min ago)  🔄          ║  ← Controls
╚════════════════════════════════════╝
     ↑         ↑           ↑
  Filter    Cache      Refresh
            Status      Button
```

**Features**:
- 👥 Total unique MVR people detected
- 📹 Number of videos analyzed
- 👨/👩 Gender breakdown with counts
- 🧒/👤 Age breakdown (young/adult)
- Time filter dropdown (today/week/month)
- Cache age indicator
- Manual refresh button

---

### InstantDetectionWidget (Right/Bottom)

```
╔════════════════════════════════════╗
║ ● Live: 3 people • 2.3s ago  🔄   ║  ← Status row
║ ─────────────────────────────────  ║
║ 👨 2  👩 1  🧒 1  👤 2            ║  ← Demographics
╚════════════════════════════════════╝
  ↑        ↑           ↑
Status   Result     Refresh
Dot      Age        Button
```

**Features**:
- ● Status indicator (blue=active, grey=inactive)
- Current person count from last 3 frames
- Result age (time since last update)
- 👨/👩/🧒/👤 Real-time demographics
- Auto-refresh every 5 seconds
- Iteration counter (in tooltip)

---

## Layout Comparison: Stream vs Card

### Horizontal (Stream Page)
```
┌────────────────┐ ┌──────────────┐
│ MVR Counter    │ │ Instant Det  │  ← Side-by-side
│ Compact        │ │ Compact      │
│ Less detail    │ │ Less detail  │
└────────────────┘ └──────────────┘

✓ Efficient horizontal space usage
✓ Both visible simultaneously
✓ Quick glance information
✗ Less room for detail
```

### Vertical (Camera Card)
```
┌──────────────────────────────────┐
│ MVR Counter                      │  ← Stacked
│ Full width                       │
│ Complete demographics            │
└──────────────────────────────────┘
┌──────────────────────────────────┐
│ Instant Detection                │
│ Full width                       │
│ Complete demographics            │
└──────────────────────────────────┘

✓ More room for details
✓ Complete information display
✓ Better for reading
✗ Uses more vertical space
```

---

## Information Architecture

### Data Flow - Camera Stream Page

```
User Opens Stream
        ↓
┌───────────────────────────────────┐
│   CameraStreamPage Mounted        │
│   - Creates RepaintBoundary       │
│   - Sets up control bar           │
└───────────────────────────────────┘
        ↓
┌───────────────────────────────────┐
│   Counter Widgets Initialize      │
│   - CameraCounterWidget           │
│   - InstantDetectionWidget        │
└───────────────────────────────────┘
        ↓
┌───────────────────────────────────┐
│   Widgets Fetch Data              │
│   - MVR Counter → Media/VMeta API │
│   - Instant Detect → Camera API   │
└───────────────────────────────────┘
        ↓
┌───────────────────────────────────┐
│   Display Results                 │
│   - Both counters show data       │
│   - Stream plays independently    │
│   - Recording controls active     │
└───────────────────────────────────┘
```

### Data Flow - Camera Card

```
User Opens Cameras Screen
        ↓
┌───────────────────────────────────┐
│   CamerasScreen Mounted           │
│   - Loads all camera cards        │
└───────────────────────────────────┘
        ↓
┌───────────────────────────────────┐
│   Each CameraCard Renders         │
│   - Shows camera details          │
│   - Adds counter widgets          │
└───────────────────────────────────┘
        ↓
┌───────────────────────────────────┐
│   Counters Initialize Per Card    │
│   - Independent state per camera  │
│   - Parallel data fetching        │
└───────────────────────────────────┘
        ↓
┌───────────────────────────────────┐
│   Display Results Per Card        │
│   - Each card shows own counts    │
│   - No cross-card interference    │
└───────────────────────────────────┘
```

---

## Responsive Behavior

### Desktop (>1200px)
```
Camera Stream:
┌──────────────────────────────────────────────┐
│ [────────── MVR ──────────] [─ Instant ─]   │  Wide counters
└──────────────────────────────────────────────┘

Camera Card:
┌──────────────────────────────────────────────┐
│ [────────────── MVR ───────────────────────] │  Full width
│ [────────────── Instant ──────────────────] │
└──────────────────────────────────────────────┘
```

### Tablet (768-1199px)
```
Camera Stream:
┌────────────────────────────────────┐
│ [────── MVR ──────] [─ Instant ─] │  Medium counters
└────────────────────────────────────┘

Camera Card:
┌────────────────────────────────────┐
│ [────────── MVR ──────────────]    │  Full width
│ [────────── Instant ──────────]    │
└────────────────────────────────────┘
```

### Mobile (<768px)
```
Camera Stream:
┌──────────────────┐
│ [── MVR ───]     │  Compact counters
│ [─ Instant ─]    │  (may stack)
└──────────────────┘

Camera Card:
┌──────────────────┐
│ [─── MVR ────]   │  Full width
│ [─ Instant ──]   │  Compact display
└──────────────────┘
```

---

## Color Coding Reference

### Status Colors

| Element | Color | Meaning |
|---------|-------|---------|
| 👥 MVR Count (>0) | 🟢 Green | People detected |
| 👥 MVR Count (0) | ⚪ Grey | No detections |
| ● Live Status (Active) | 🔵 Blue | Detecting now |
| ● Live Status (Inactive) | ⚪ Grey | Not detecting |
| 🔴 Recording | 🔴 Red | Recording active |

### Demographic Icons

| Icon | Color | Meaning |
|------|-------|---------|
| 👨 | 🔵 Blue | Male detected |
| 👩 | 🎀 Pink | Female detected |
| 🧒 | 🟠 Orange | Young person (<21) |
| 👤 | 🟢 Green | Adult (≥21) |

---

## File Modification Map

```
ppl-meta-frontend/
├── lib/
│   ├── presentation/
│   │   ├── pages/
│   │   │   └── camera_stream_page.dart  ⬅ MODIFIED
│   │   │       ├── Added imports (lines 8-9)
│   │   │       └── Added counters (lines 56-72)
│   │   └── widgets/
│   │       └── camera/
│   │           └── camera_card.dart  ⬅ MODIFIED
│   │               ├── Added imports (lines 11-12)
│   │               └── Added counters (lines 113-122)
│   └── widgets/
│       └── camera/
│           ├── camera_counter_widget.dart  ✓ EXISTING
│           └── instant_detection_widget.dart  ✓ EXISTING
└── docs/
    └── guides/
        └── developer/
            ├── camera-counters-integration.md  ⬅ CREATED
            ├── camera-counters-quick-test.md  ⬅ CREATED
            ├── camera-counters-implementation-summary.md  ⬅ CREATED
            ├── camera-counters-visual-map.md  ⬅ THIS FILE
            └── instant-detection-widget-frontend.md  ⬅ UPDATED
```

---

## Quick Reference

### Import Statements

```dart
// For camera stream page
import '../../widgets/camera/camera_counter_widget.dart';
import '../../widgets/camera/instant_detection_widget.dart';

// For camera card
import '../../../widgets/camera/camera_counter_widget.dart';
import '../../../widgets/camera/instant_detection_widget.dart';
```

### Widget Usage

```dart
// Stream page (side-by-side)
Row(
  children: [
    Expanded(child: CameraCounterWidget(cameraId: cameraId)),
    SizedBox(width: 8),
    Expanded(child: InstantDetectionWidget(cameraId: cameraId)),
  ],
)

// Card (stacked)
CameraCounterWidget(cameraId: cameraId),
SizedBox(height: 8),
InstantDetectionWidget(cameraId: cameraId),
```

---

**Document Version**: 1.0  
**Last Updated**: December 25, 2025  
**Purpose**: Visual reference for integration changes
