# Instant Detection Widget - Frontend Integration

## Overview

The **InstantDetectionWidget** is an autonomous Flutter widget that displays real-time face detection results from the Camera Service's instant detection memory cache. It appears directly below the camera counter widget on each camera card.

## Location

**File:** `ppl-meta-frontend/lib/widgets/camera/instant_detection_widget.dart`

## Features

### 1. **Real-Time Updates**
- Auto-refreshes every 5 seconds (matches backend sampling rate)
- Displays current person count from instant detection
- Shows age of cached result (e.g., "2.3s ago")

### 2. **Visual Indicators**
- **Status Dot**: 
  - Blue filled circle: Active with detections
  - Grey filled circle: Active but no detections
  - Grey outline circle: Inactive
- **Loading Spinner**: Shows while fetching results

### 3. **Demographics Display**
When people are detected, shows:
- **Gender**: 👨 (male - blue), 👩 (female - pink)
- **Age**: 🧒 (young <21 - orange), 👤 (adult ≥21 - green)
- Counts for each category with color-coded badges

### 4. **Iteration Counter**
- Shows iteration number via tooltip on refresh icon
- Indicates data is being updated every 5 seconds

## Integration

### Camera Card Structure
```
Camera Card
├── Camera Header (name, status, specs)
├── Stream Section (if active)
├── Action Buttons (start, stop, snapshot)
├── Camera Counter Widget (MVR people detected)
└── Instant Detection Widget (real-time detections) ← NEW
```

### Added to Camera Card
```dart
// In camera_card.dart
InstantDetectionWidget(
  cameraId: widget.camera.deviceId,
  refreshInterval: const Duration(seconds: 5),
),
```

## API Integration

### Backend Endpoint
```
GET /api/v1/cameras/{camera_id}/instant-detection/results
```

### Response Format
```json
{
  "success": true,
  "person_objects": [
    {
      "person_id": "person_1",
      "age_gender": {
        "gender": "Male",
        "gender_confidence": 0.91,
        "age_min": 25,
        "age_max": 32
      },
      "best_face": {...}
    }
  ],
  "_metadata": {
    "cached_at": 1702291800.0,
    "iteration": 5,
    "age_seconds": 2.3
  }
}
```

### Camera Service Method
```dart
// In camera_service.dart
Future<Map<String, dynamic>?> getInstantDetectionResults(String deviceId) async {
  final response = await http.get(
    Uri.parse('$_gatewayUrl/cameras/$deviceId/instant-detection/results'),
    headers: _authService.getAuthHeaders(),
  ).timeout(const Duration(seconds: 3));
  
  return json.decode(response.body);
}
```

## Widget State

### State Variables
```dart
List<Map<String, dynamic>>? _personObjects;  // Detected people
bool _isLoading;                              // Loading state
bool _isInstantDetectionRunning;             // Backend active status
int? _cachedIteration;                        // Iteration counter
double? _ageSeconds;                          // Result age
```

### Auto-Refresh
- Timer-based refresh every 5 seconds
- Cancels timer on dispose to prevent leaks

## Visual Design

### Layout
```
┌─────────────────────────────────────────┐
│ ● Live: 3 people • 2.3s ago  🔄        │
│   👨 2  👩 1  🧒 1  👤 2                │
└─────────────────────────────────────────┘
```

### Color Scheme
- **Background**: 
  - Blue tint when active with detections
  - Grey when inactive or no detections
- **Text**: 
  - Primary count in blue (detections) or grey (none)
  - Secondary info in lighter grey
- **Badges**: Color-coded by category

## Comparison with Camera Counter Widget

| Feature | Camera Counter | Instant Detection |
|---------|---------------|-------------------|
| **Purpose** | Historical MVR people count | Real-time face detection |
| **Update Rate** | 5 minutes | 5 seconds |
| **Data Source** | Media Service (database) | Camera Service (memory) |
| **Time Range** | Configurable (today, week, month) | Last 5 seconds |
| **Demographics** | Aggregated from videos | Live from 3 frames |
| **Cache** | Server-side (5 min TTL) | Memory-only (replaced) |

## Error Handling

### Scenarios
1. **No Results Yet**: Shows inactive state
2. **Instant Detection Not Running**: Shows grey inactive state
3. **Network Error**: Silent fail, keeps old data
4. **Timeout**: 3-second timeout to prevent UI blocking

### Silent Failures
- Doesn't show error messages (called every 5s)
- Logs to console for debugging
- Maintains last known state

## Testing

### Manual Testing
1. Start instant detection for a camera:
   ```bash
   curl -X POST http://localhost:8005/api/v1/instant-detection/start/usb_camera_0
   ```

2. Navigate to `http://localhost:3000/#/cameras`

3. Verify widget shows:
   - Blue status dot
   - Person count updates every 5s
   - Demographics badges
   - Iteration counter in tooltip

### Expected Behavior
- Widget appears below counter
- Auto-updates every 5 seconds
- Shows real-time person detections
- Demographics update instantly
- No UI blocking or stuttering

## Dependencies

### Packages
```yaml
dependencies:
  flutter_riverpod: latest
```

### Services
- Camera Service (HTTP API calls)
- Auth Service (via camera service)

### Models
- No new models required (uses Map<String, dynamic>)

## Performance

### Metrics
- **API Call**: ~10-50ms (local network)
- **Widget Rebuild**: <5ms
- **Memory**: <1MB per camera
- **Network**: ~1-5KB per request

### Optimization
- Lightweight state (no complex models)
- Silent timeouts (3 seconds)
- Efficient rebuilds (only on data change)

## Future Enhancements

### Possible Additions
1. **Click to View**: Tap widget to see face snapshots
2. **History Graph**: Mini sparkline of detections over time
3. **Alert Indicator**: Highlight when specific person detected
4. **Confidence Bars**: Show detection confidence levels

## Related Documentation

- [Instant Detection Implementation](../../../docs/guides/developer/instant-detection-implementation.md)
- [Instant Detection Quickstart](../../../docs/guides/developer/instant-detection-quickstart.md)
- [Camera Counter Optimization](../../../docs/guides/developer/camera-counter-optimization.md)
- [Face Detection Guide](../../../docs/guides/developer/ppl-meta-face-detection.md)
