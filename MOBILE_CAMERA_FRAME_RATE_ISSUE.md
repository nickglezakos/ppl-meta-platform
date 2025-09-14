# Mobile Camera Frame Rate Detection Issue

## Issue Summary

**Status**: 🔴 **OPEN - HIGH PRIORITY**  
**Type**: Video Playback Quality Issue  
**Component**: Mobile Camera Recording Pipeline  
**Impact**: User Experience - Erratic video playback affects usability

## Problem Description

Mobile camera recordings are successfully saved to the correct collections (issue #45 resolved), but video playback exhibits erratic behavior due to frame rate detection and standardization issues.

### Observed Symptoms

1. **Inconsistent Playback Speed**: Videos play too fast or too slow
2. **Stuttering Playback**: Jerky, non-smooth video playback in Flutter video player
3. **Frame Rate Mismatch**: Mobile recordings don't match expected playback frame rates
4. **Player Confusion**: Video players struggle to determine correct playback speed

### Current Implementation Analysis

#### Mobile Recording Process
```
Mobile Device → JPEG Frames → Cameras Service → Frame Buffer → H.264 MP4 → Collection Storage
```

#### Frame Rate Sources
1. **Mobile Frame Capture**: Variable frame rate depending on device performance and network
2. **VideoWriter Configuration**: Fixed frame rate set in `cv2.VideoWriter()`
3. **Playback Detection**: Flutter video player attempts to auto-detect frame rate

## Root Cause Analysis

### 1. Frame Rate Configuration Issue
**File**: `ppl-meta-cameras/src/services/camera_detection.py` - Line 759

```python
fourcc = cv2.VideoWriter_fourcc(*"H264")
out = cv2.VideoWriter(video_path, fourcc, 20.0, (width, height))
```

**Problem**: Hard-coded 20 FPS frame rate doesn't match actual mobile frame transmission rate

### 2. Variable Frame Reception Rate
- Mobile devices send frames at inconsistent intervals
- Network latency affects frame timing
- Device processing power impacts frame capture rate
- Background app behavior changes frame delivery frequency

### 3. Missing Frame Rate Metadata
- No frame rate detection during recording
- No timestamp analysis for actual frame intervals
- No adaptive frame rate adjustment based on received frames

## Technical Impact

### Video Quality Issues
- **Playback Speed**: Videos may play 2-3x faster or slower than intended
- **Motion Artifacts**: Jerky motion due to frame rate mismatches
- **User Experience**: Poor video quality affects platform usability

### Collection Management
- Videos are stored correctly but display poorly
- Users may think recordings failed when they actually succeeded
- Inconsistent quality across different mobile devices

## Proposed Solutions

### Solution 1: Dynamic Frame Rate Detection ⭐ **RECOMMENDED**

#### Implementation Strategy
1. **Frame Timestamp Analysis**: Calculate actual frame intervals during recording
2. **Adaptive Frame Rate**: Adjust VideoWriter frame rate based on measured intervals
3. **Metadata Embedding**: Store detected frame rate in video metadata

#### Code Changes Required

**Enhanced Frame Rate Detection** - `ppl-meta-cameras/src/services/mobile_frame_rate_detector.py` (NEW)
```python
class MobileFrameRateDetector:
    def __init__(self, window_size: int = 10):
        self.frame_timestamps = []
        self.window_size = window_size
        
    def add_frame_timestamp(self, timestamp: float):
        """Add frame timestamp and calculate running average FPS."""
        self.frame_timestamps.append(timestamp)
        
        if len(self.frame_timestamps) > self.window_size:
            self.frame_timestamps.pop(0)
            
    def get_detected_fps(self) -> float:
        """Calculate FPS based on recent frame intervals."""
        if len(self.frame_timestamps) < 2:
            return 20.0  # Default fallback
            
        intervals = []
        for i in range(1, len(self.frame_timestamps)):
            interval = self.frame_timestamps[i] - self.frame_timestamps[i-1]
            intervals.append(interval)
            
        avg_interval = sum(intervals) / len(intervals)
        detected_fps = 1.0 / avg_interval if avg_interval > 0 else 20.0
        
        # Clamp to reasonable range
        return max(5.0, min(30.0, detected_fps))
        
    def get_stabilized_fps(self) -> float:
        """Get stabilized FPS rounded to common frame rates."""
        detected = self.get_detected_fps()
        
        # Round to common frame rates
        common_fps = [5.0, 10.0, 15.0, 20.0, 24.0, 25.0, 30.0]
        return min(common_fps, key=lambda x: abs(x - detected))
```

**Updated Mobile Streaming Service** - `ppl-meta-cameras/src/services/mobile_streaming.py`
```python
class MobileStreamingService:
    def __init__(self):
        self.frame_rate_detectors = {}  # device_id -> detector
        
    async def receive_mobile_frame(self, device_id: str, frame_data: bytes):
        """Enhanced frame reception with FPS detection."""
        timestamp = time.time()
        
        # Initialize detector for new devices
        if device_id not in self.frame_rate_detectors:
            self.frame_rate_detectors[device_id] = MobileFrameRateDetector()
            
        detector = self.frame_rate_detectors[device_id]
        detector.add_frame_timestamp(timestamp)
        
        # Store frame with timing info
        frame_info = {
            "data": frame_data,
            "timestamp": timestamp,
            "detected_fps": detector.get_detected_fps()
        }
        
        await self._buffer_frame(device_id, frame_info)
        
    async def _start_mobile_recording(self, device_id: str, recording_path: str):
        """Start recording with dynamic frame rate."""
        # Get stabilized frame rate for this device
        detector = self.frame_rate_detectors.get(device_id)
        fps = detector.get_stabilized_fps() if detector else 20.0
        
        logger.info(f"Starting mobile recording for {device_id} at {fps} FPS")
        
        # Use detected frame rate
        fourcc = cv2.VideoWriter_fourcc(*"H264")
        out = cv2.VideoWriter(recording_path, fourcc, fps, (width, height))
        
        # Store FPS in metadata for playback
        await self._embed_fps_metadata(recording_path, fps)
```

### Solution 2: Standardized Frame Rate with Interpolation

#### Implementation Strategy
1. **Fixed Target FPS**: Use consistent 24 FPS for all mobile recordings
2. **Frame Interpolation**: Duplicate or skip frames to match target rate
3. **Smooth Playback**: Ensure consistent playback experience

#### Code Changes Required

**Frame Rate Standardizer** - `ppl-meta-cameras/src/services/frame_rate_standardizer.py` (NEW)
```python
class FrameRateStandardizer:
    TARGET_FPS = 24.0
    
    def __init__(self):
        self.frame_buffer = []
        self.last_output_time = 0.0
        
    def standardize_frame_rate(self, frames_with_timestamps: List[tuple]) -> List[bytes]:
        """Convert variable frame rate to fixed 24 FPS."""
        if not frames_with_timestamps:
            return []
            
        output_frames = []
        frame_interval = 1.0 / self.TARGET_FPS  # ~0.042 seconds per frame
        
        start_time = frames_with_timestamps[0][1]  # timestamp of first frame
        current_output_time = start_time
        frame_index = 0
        
        while frame_index < len(frames_with_timestamps):
            # Find the frame closest to current output time
            closest_frame = self._find_closest_frame(
                frames_with_timestamps, 
                current_output_time, 
                frame_index
            )
            
            output_frames.append(closest_frame[0])  # frame data
            current_output_time += frame_interval
            
            # Update frame index to avoid reusing frames
            while (frame_index < len(frames_with_timestamps) and 
                   frames_with_timestamps[frame_index][1] <= current_output_time):
                frame_index += 1
                
        return output_frames
```

### Solution 3: Client-Side Frame Rate Hint

#### Implementation Strategy
1. **Mobile App Enhancement**: Mobile app detects and reports its frame capture rate
2. **Metadata Transmission**: Send frame rate hint with initial setup
3. **Server Adaptation**: Use client-provided frame rate for recording

#### Mobile App Changes
**File**: `ppl_meta_mobile_camera/lib/services/camera_service.dart`
```dart
class CameraService {
  Future<void> setupCameraWithFrameRate() async {
    // Detect device capabilities
    final detectedFPS = await _detectOptimalFrameRate();
    
    // Send to server during setup
    await _sendCameraSetup({
      'device_id': deviceId,
      'detected_fps': detectedFPS,
      'camera_capabilities': await _getCameraCapabilities()
    });
  }
  
  Future<double> _detectOptimalFrameRate() async {
    // Test frame capture rate over short period
    final timestamps = <DateTime>[];
    
    for (int i = 0; i < 30; i++) {
      timestamps.add(DateTime.now());
      await Future.delayed(Duration(milliseconds: 33)); // ~30 FPS attempt
      // Actual frame capture here
    }
    
    // Calculate actual achieved frame rate
    final totalTime = timestamps.last.difference(timestamps.first).inMilliseconds;
    return (timestamps.length * 1000) / totalTime;
  }
}
```

## Implementation Priority

### Phase 1: Dynamic Frame Rate Detection (Immediate) ⭐
- **Effort**: 2-3 days
- **Impact**: High - Solves core playback issues
- **Complexity**: Medium
- **Files to Modify**:
  - `ppl-meta-cameras/src/services/camera_detection.py`
  - `ppl-meta-cameras/src/services/mobile_streaming.py`
  - Add: `ppl-meta-cameras/src/services/mobile_frame_rate_detector.py`

### Phase 2: Metadata Enhancement (Follow-up)
- **Effort**: 1-2 days  
- **Impact**: Medium - Improves player compatibility
- **Complexity**: Low
- **Files to Modify**:
  - Video metadata embedding
  - Frontend video player configuration

### Phase 3: Mobile App Frame Rate Hints (Future)
- **Effort**: 3-4 days
- **Impact**: Medium - Optimizes from source
- **Complexity**: High - Requires mobile app changes
- **Files to Modify**:
  - `ppl_meta_mobile_camera/lib/services/camera_service.dart`
  - Backend setup endpoints

## Testing Strategy

### Frame Rate Detection Testing
```python
# Test script: test_mobile_frame_rate_detection.py
async def test_frame_rate_detection():
    detector = MobileFrameRateDetector()
    
    # Simulate 15 FPS frame reception
    test_fps = 15.0
    frame_interval = 1.0 / test_fps
    
    for i in range(20):
        timestamp = i * frame_interval
        detector.add_frame_timestamp(timestamp)
        
    detected_fps = detector.get_detected_fps()
    stabilized_fps = detector.get_stabilized_fps()
    
    assert abs(detected_fps - test_fps) < 1.0
    assert stabilized_fps in [10.0, 15.0, 20.0]
```

### Video Playback Quality Testing
1. **Record test videos** at different simulated frame rates
2. **Verify playback smoothness** in Flutter frontend
3. **Test multiple mobile devices** with varying performance
4. **Measure frame rate accuracy** using video analysis tools

## Success Criteria

### Primary Goals
- [ ] Mobile camera recordings play smoothly without stuttering
- [ ] Video playback speed matches recording speed (±5%)
- [ ] Consistent playback experience across different mobile devices
- [ ] No regression in existing USB/RTSP camera recording quality

### Secondary Goals
- [ ] Frame rate metadata properly embedded in video files
- [ ] Automatic frame rate optimization based on device capabilities
- [ ] User-visible frame rate information in collection interface
- [ ] Performance monitoring for frame rate detection overhead

## Risk Assessment

### Technical Risks
- **Performance Impact**: Frame rate detection may add processing overhead
- **Compatibility**: Changes might affect existing recording functionality
- **Edge Cases**: Unusual mobile devices with extreme frame rates

### Mitigation Strategies
- **Gradual Rollout**: Test with single mobile device first
- **Fallback Mechanisms**: Default to 20 FPS if detection fails
- **Performance Monitoring**: Measure and optimize detection overhead
- **Backward Compatibility**: Ensure existing recordings continue working

## Related Issues

- **Issue #45**: Mobile Camera Collection Assignment ✅ **RESOLVED**
- **Video Codec Issue**: H.264 compatibility ✅ **RESOLVED**
- **Future**: Mobile camera recording UI controls
- **Future**: Advanced video quality settings

---

**Created**: September 14, 2025  
**Priority**: High  
**Assignee**: Development Team  
**Labels**: mobile-camera, video-quality, frame-rate, user-experience