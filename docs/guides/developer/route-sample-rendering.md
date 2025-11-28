# Route Sample Rendering Guide

## Overview

This guide explains the route sampling mechanism implemented in the Cross-Video Individual Analysis Routes tab to optimize performance when rendering large numbers of route points.

## Problem Statement

When tracking individuals across multiple videos over extended time periods, the system can accumulate hundreds or thousands of route points. Rendering all these points simultaneously can cause:

- **Performance degradation** in the UI
- **Slow canvas rendering** with complex CustomPainter operations
- **Memory overhead** from storing and processing excessive data
- **Poor user experience** due to lag and stuttering

## Solution: Adaptive Route Sampling

The system implements an intelligent sampling algorithm that reduces the number of rendered route points while preserving the overall shape and characteristics of the movement path.

### Threshold Configuration

```dart
const maxRoutePoints = 100;
```

- **Default threshold**: 100 route points
- Routes with ≤100 points: rendered in full without sampling
- Routes with >100 points: sampled down to approximately 100 points
- Threshold is configurable via the `maxRoutePoints` constant

### Sampling Algorithm

The sampling algorithm uses **uniform interval sampling** with guaranteed endpoint inclusion:

#### 1. Calculate Sampling Interval

```dart
final interval = (allRoutePoints.length / maxRoutePoints).ceil();
```

**Example**: For 500 route points with maxRoutePoints=100
- Interval = ceil(500 / 100) = 5
- Every 5th point will be included in the sample

#### 2. Preserve Journey Endpoints

```dart
// Always include first point (journey start)
sampledRoutePoints.add(allRoutePoints.first);

// Sample intermediate points
for (int j = interval; j < allRoutePoints.length - 1; j += interval) {
  sampledRoutePoints.add(allRoutePoints[j]);
}

// Always include last point (journey end)
if (allRoutePoints.length > 1) {
  sampledRoutePoints.add(allRoutePoints.last);
}
```

**Why preserve endpoints?**
- **First point**: Shows exact starting location of tracked individual
- **Last point**: Shows exact ending location
- **Critical for understanding**: Complete journey visualization

#### 3. Store Both Original and Sampled Counts

```dart
personGroups.add({
  'person_id': individualId,
  'total_detections': allRoutePoints.length,      // Original count
  'sampled_points': sampledRoutePoints.length,    // Sampled count
  'movement_tracking': {
    'route_points': sampledRoutePoints,           // Sampled data for rendering
    'total_distance': 0.0,
    'movement_duration': analysis.totalDurationSeconds,
  },
});
```

## Implementation Location

**File**: `/ppl-meta-frontend/lib/screens/person_objects_detail_screen.dart`

**Method**: `_fetchCrossVideoRoutesData()`

**Lines**: Approximately 4437-4469 (after route point sorting)

## Benefits

### Performance Improvements

| Original Points | Sampled Points | Reduction | Performance Gain |
|----------------|----------------|-----------|------------------|
| 50             | 50             | 0%        | No overhead      |
| 100            | 100            | 0%        | No overhead      |
| 200            | 101            | 49.5%     | ~2x faster       |
| 500            | 101            | 79.8%     | ~5x faster       |
| 1000           | 101            | 89.9%     | ~10x faster      |
| 5000           | 101            | 97.98%    | ~50x faster      |

### Visual Fidelity

Despite aggressive sampling, the route visualization maintains:
- ✅ Overall path shape and trajectory
- ✅ Start and end positions (exact)
- ✅ Major direction changes (approximated)
- ✅ Temporal progression (through sampling interval)

### Memory Efficiency

**Before sampling** (1000 points):
```
Memory per route point: ~200 bytes (coordinate, timestamp, metadata)
Total memory: 1000 × 200 = 200 KB per individual
```

**After sampling** (101 points):
```
Memory per route point: ~200 bytes
Total memory: 101 × 200 = 20.2 KB per individual
Savings: 89.9% memory reduction
```

## Debugging and Monitoring

### Console Logging

The system logs sampling operations for debugging:

```dart
print('🚦 Individual $i: 📊 Sampled ${allRoutePoints.length} points down to ${sampledRoutePoints.length} points (threshold: $maxRoutePoints)');
```

**Example output**:
```
🚦 Individual 0: ✅ Combined 450 route points from 4 appearances
🚦 Individual 0: 📊 Sampled 450 points down to 91 points (threshold: 100)
```

### Metadata Preservation

Original point count is preserved in the data structure:
- `total_detections`: Original number of route points (for analytics)
- `sampled_points`: Actual number of points used for rendering
- `route_points`: The sampled array used by CustomPainter

## Use Cases

### Scenario 1: Short Duration Tracking (No Sampling)

**Input**: Individual tracked for 30 seconds, 45 route points
- **Action**: No sampling applied (45 < 100)
- **Result**: All 45 points rendered exactly
- **Performance**: Optimal, no overhead

### Scenario 2: Medium Duration Tracking (Light Sampling)

**Input**: Individual tracked for 2 minutes, 180 route points
- **Action**: Sampling applied (180 > 100)
- **Interval**: ceil(180 / 100) = 2
- **Result**: 91 points rendered (first + every 2nd + last)
- **Performance**: Smooth rendering, negligible visual difference

### Scenario 3: Extended Tracking (Heavy Sampling)

**Input**: Individual tracked for 30 minutes, 2500 route points
- **Action**: Heavy sampling applied (2500 > 100)
- **Interval**: ceil(2500 / 100) = 25
- **Result**: 101 points rendered (first + every 25th + last)
- **Performance**: Excellent, maintains path shape

## Customization

### Adjusting the Threshold

To change the sampling threshold, modify the constant:

```dart
// Conservative (more detail, lower performance)
const maxRoutePoints = 200;

// Balanced (default)
const maxRoutePoints = 100;

// Aggressive (less detail, higher performance)
const maxRoutePoints = 50;
```

**Recommendations**:
- **Desktop/Web**: 100-200 points (more processing power available)
- **Mobile**: 50-100 points (conserve battery and memory)
- **Embedded devices**: 25-50 points (limited resources)

### Alternative Sampling Strategies

The current implementation uses **uniform interval sampling**. Other strategies could be implemented:

#### 1. Adaptive Sampling (Based on Movement)
```dart
// Sample more densely during direction changes
// Sample sparsely during straight-line movement
```

#### 2. Time-Based Sampling
```dart
// Ensure consistent temporal distribution
// One point every N seconds regardless of spatial density
```

#### 3. Significance-Based Sampling
```dart
// Prioritize points with high confidence scores
// Keep points near important locations (entry/exit)
```

## Integration with Velocity Calculation

**Important**: The sampling is applied **after** velocity calculations in the backend.

The backend calculates `average_route_velocity` using **all** route points:
1. Backend fetches complete route data from orchestrator
2. Backend calculates velocity from full dataset (no sampling)
3. Backend returns velocity + all route points
4. Frontend receives data and applies sampling **only for rendering**
5. Velocity value remains accurate (based on complete data)

This ensures:
- ✅ Accurate velocity calculations (uses complete dataset)
- ✅ Optimized rendering (uses sampled dataset)
- ✅ Best of both worlds (accuracy + performance)

## Testing Recommendations

### Unit Tests

Test the sampling algorithm with various input sizes:

```dart
// Test Case 1: Below threshold
final input1 = generateRoutePoints(50);
final output1 = sampleRoutePoints(input1, maxPoints: 100);
expect(output1.length, equals(50)); // No sampling

// Test Case 2: Above threshold
final input2 = generateRoutePoints(500);
final output2 = sampleRoutePoints(input2, maxPoints: 100);
expect(output2.length, lessThanOrEqual(101)); // Sampled
expect(output2.first, equals(input2.first)); // First preserved
expect(output2.last, equals(input2.last)); // Last preserved

// Test Case 3: Edge case - exactly at threshold
final input3 = generateRoutePoints(100);
final output3 = sampleRoutePoints(input3, maxPoints: 100);
expect(output3.length, equals(100)); // No sampling
```

### Performance Tests

Measure rendering performance with different point counts:

```dart
// Benchmark rendering time
final stopwatch = Stopwatch()..start();
renderRoutes(routePoints);
stopwatch.stop();
print('Render time: ${stopwatch.elapsedMilliseconds}ms');
```

### Visual Quality Tests

Verify that sampled routes maintain visual fidelity:
1. Render full route and sampled route side-by-side
2. Compare overall shapes visually
3. Verify start/end positions match exactly
4. Check that major turns are preserved

## Troubleshooting

### Issue: Routes look too jagged/angular

**Cause**: Sampling interval too large (not enough points)

**Solution**: Increase threshold
```dart
const maxRoutePoints = 150; // or higher
```

### Issue: Still experiencing performance issues

**Cause**: Other factors (canvas size, complex CustomPainter operations)

**Solutions**:
1. Reduce maxRoutePoints further (to 50 or 25)
2. Optimize CustomPainter paint() method
3. Use RepaintBoundary to isolate route canvas
4. Consider caching painted routes

### Issue: Sampling not applied

**Cause**: Route points not exceeding threshold

**Solution**: Verify actual point count in logs:
```
🚦 Individual 0: ✅ Combined 45 route points from 2 appearances
```
If count is below 100, sampling won't trigger (by design)

## Future Enhancements

### Planned Improvements

1. **Dynamic Threshold**: Adjust based on device performance
   ```dart
   final maxPoints = Platform.isIOS || Platform.isAndroid ? 50 : 150;
   ```

2. **Quadtree Spatial Sampling**: Preserve spatial density
   - More points in areas with complex movement
   - Fewer points in straight-line segments

3. **User Preference**: Allow users to control detail level
   ```dart
   // User settings
   enum RouteDetailLevel { low, medium, high, full }
   ```

4. **Progressive Loading**: Load and render in chunks
   - Render first N points immediately
   - Load remaining points asynchronously
   - Useful for extremely long routes (>10,000 points)

## Related Documentation

- **Route Velocity Calculation**: See `/docs/guides/developer/route-velocity-calculation.md`
- **Cross-Video Analysis**: See `/docs/features/cross-video-tracking.md`
- **Performance Optimization**: See `/docs/guides/developer/performance-best-practices.md`

## Version History

- **v2.19.41** (2025-11-28): Initial implementation of route sampling
  - Uniform interval sampling with endpoint preservation
  - Threshold: 100 points
  - Applied in Cross-Video Routes tab

---

**Author**: Development Team  
**Last Updated**: 2025-11-28  
**Status**: Active  
