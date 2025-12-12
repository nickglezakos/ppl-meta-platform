# Instant Detection Widget - Visual Guide

## Widget Appearance

### Active with Detections
```
┌─────────────────────────────────────────────────┐
│ Camera: USB Camera 0                            │
│ Status: ACTIVE                                   │
│ Resolution: 1920x1080                           │
│                                                  │
│ [Stream Player]                                 │
│                                                  │
│ [Start] [Stop] [Snapshot]                      │
├─────────────────────────────────────────────────┤
│ Time Period: [Last Month ▼]                    │
│ 👤 Total: 156 people • 2,341 videos 💾         │
│ 👨 98 (63%)  👩 58 (37%)                       │
│ 🧒 Young: 45 (29%)  👤 Adult: 111 (71%)        │
│                                          🔄     │
├─────────────────────────────────────────────────┤ ← NEW WIDGET
│ ● Live: 3 people • 1.2s ago              🔄    │
│   👨 2  👩 1  🧒 1  👤 2                        │
└─────────────────────────────────────────────────┘
   ↑                                         ↑
   Blue dot = Active                  Iteration tooltip
```

### Active with No Detections
```
├─────────────────────────────────────────────────┤
│ ◉ Live: 0 people • 0.8s ago              🔄    │
└─────────────────────────────────────────────────┘
   ↑
   Grey dot = No detections
```

### Inactive
```
├─────────────────────────────────────────────────┤
│ ○ Live: 0 people                                │
└─────────────────────────────────────────────────┘
   ↑
   Empty circle = Inactive
```

### Loading State
```
├─────────────────────────────────────────────────┤
│ ● ⏳ Loading...                                 │
└─────────────────────────────────────────────────┘
```

## Color Coding

### Status Indicators
- **🔵 Blue Solid**: Active with detections
- **⚫ Grey Solid**: Active with no detections
- **⚪ Grey Outline**: Inactive

### Demographics Badges
```
👨 2  = Male count (blue background)
👩 1  = Female count (pink background)
🧒 1  = Young <21 (orange background)
👤 2  = Adult ≥21 (green background)
```

### Background Colors
- **Light Blue**: Active with detections
- **Light Grey**: Active without detections
- **Very Light Grey**: Inactive

## Side-by-Side Comparison

### Camera Counter vs Instant Detection

```
┌────────────────────────────────────────────────┐
│ CAMERA COUNTER (Historical - 5 min refresh)    │
├────────────────────────────────────────────────┤
│ Time Period: [Last Month ▼]                   │
│ 👤 Total: 156 people • 2,341 videos 💾        │
│ 👨 98 (63%)  👩 58 (37%)                      │
│ 🧒 45 (29%)  👤 111 (71%)                     │
│                                         🔄     │
└────────────────────────────────────────────────┘
        ↓
┌────────────────────────────────────────────────┐
│ INSTANT DETECTION (Real-time - 5 sec refresh)  │
├────────────────────────────────────────────────┤
│ ● Live: 3 people • 1.2s ago             🔄    │
│   👨 2  👩 1  🧒 1  👤 2                       │
└────────────────────────────────────────────────┘
```

## Responsive Behavior

### Desktop (Wide)
```
┌─────────────────────────────────────────────────────────┐
│ ● Live: 3 people • 1.2s ago                       🔄    │
│   👨 2  👩 1  🧒 1  👤 2                                │
└─────────────────────────────────────────────────────────┘
```

### Mobile (Narrow)
```
┌──────────────────────────────┐
│ ● Live: 3 people • 1.2s ago │
│   👨 2  👩 1                 │
│   🧒 1  👤 2          🔄    │
└──────────────────────────────┘
```

## Animation States

### 1. Initial Load (0-1s)
```
● ⏳ Loading...
```

### 2. First Result (1-2s)
```
● Live: 0 people • 0.0s ago  🔄
```

### 3. Person Detected (5s)
```
● Live: 1 person • 0.2s ago  🔄
  👨 1  👤 1
```

### 4. Multiple People (10s)
```
● Live: 3 people • 1.5s ago  🔄
  👨 2  👩 1  🧒 1  👤 2
```

### 5. People Leave (15s)
```
◉ Live: 0 people • 0.8s ago  🔄
```

## Tooltip Details

### Iteration Counter Tooltip
```
Hover over 🔄 icon:

┌─────────────────────┐
│ Iteration #42       │
│ Refreshes every 5s  │
└─────────────────────┘
```

## Edge Cases

### Very Long Names (Truncated)
```
┌─────────────────────────────────────────────────┐
│ Camera: Front Entrance Security Camer... 📹    │
│ ...                                              │
├─────────────────────────────────────────────────┤
│ ● Live: 3 people • 1.2s ago              🔄    │
│   👨 2  👩 1  🧒 1  👤 2                        │
└─────────────────────────────────────────────────┘
```

### Large Numbers
```
┌─────────────────────────────────────────────────┐
│ ● Live: 12 people • 2.3s ago             🔄    │
│   👨 7  👩 5  🧒 3  👤 9                        │
└─────────────────────────────────────────────────┘
```

### Zero Detections
```
┌─────────────────────────────────────────────────┐
│ ◉ Live: 0 people • 0.8s ago              🔄    │
└─────────────────────────────────────────────────┘
```

### Network Error (Maintains Last State)
```
┌─────────────────────────────────────────────────┐
│ ● Live: 3 people • 47.2s ago             🔄    │
│   👨 2  👩 1  🧒 1  👤 2                        │
└─────────────────────────────────────────────────┘
      ↑
   Old timestamp indicates stale data
```

## User Experience Flow

### 1. User Opens Cameras Page
```
Page loads → Camera cards render → Widgets initialize
     ↓
Each widget makes initial API call (within 1s)
     ↓
Loading spinner shows briefly
     ↓
Results populate (person count + demographics)
```

### 2. Auto-Refresh Cycle
```
Every 5 seconds:
  1. Widget makes API call (background, no spinner)
  2. New data received
  3. UI updates smoothly
  4. Iteration counter increments
  5. Age timestamp resets
```

### 3. Person Enters Frame
```
Backend detects face (next 5s cycle)
     ↓
Widget updates: 0 → 1 person
     ↓
Demographics badge appears: 👨 1
     ↓
Status dot turns blue (from grey)
```

### 4. Person Leaves Frame
```
Backend loses detection (next 5s cycle)
     ↓
Widget updates: 1 → 0 people
     ↓
Demographics badges disappear
     ↓
Status dot turns grey (from blue)
```

## Integration with Camera Counter

Both widgets are **completely independent**:

- **Camera Counter**: Queries Media Service, updates every 5 minutes
- **Instant Detection**: Queries Camera Service, updates every 5 seconds
- **No interference**: Different API endpoints, different refresh rates
- **Complementary**: Historical vs real-time insights

## Accessibility

### Screen Reader Support
```html
<div aria-label="Live detection: 3 people detected 1.2 seconds ago. 
                  Demographics: 2 male, 1 female, 1 young, 2 adults.
                  Iteration 42, refreshes every 5 seconds.">
```

### Keyboard Navigation
- Widget is read-only (no interactive elements except tooltip)
- Tab order flows naturally through camera card

## Print/Export View

When printing camera overview:
```
Camera: USB Camera 0
Status: ACTIVE
Real-time: 3 people (2 male, 1 female, 1 young, 2 adults)
Last updated: 1.2 seconds ago
```

## Dark Mode Support

### Light Theme
- Background: `rgba(33, 150, 243, 0.05)` (light blue)
- Text: `#1976D2` (blue)
- Border: `rgba(33, 150, 243, 0.2)`

### Dark Theme
- Background: `rgba(33, 150, 243, 0.1)` (darker blue)
- Text: `#64B5F6` (lighter blue)
- Border: `rgba(33, 150, 243, 0.3)`
