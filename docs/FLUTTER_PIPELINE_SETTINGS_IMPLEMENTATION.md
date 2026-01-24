# Flutter Frontend - Pipeline Settings Integration

**Date**: January 24, 2026  
**Status**: ✅ Complete and Ready for Testing

## Overview

The Flutter frontend now includes a complete pipeline settings interface that allows users to configure instant detection and recording pipelines on a per-camera basis. The implementation follows Material Design principles with an intuitive, accessible UI.

## Features Implemented

### 1. Data Models

#### CameraPipelineSettings Model
**Location**: `lib/core/models/camera_pipeline_settings.dart`

- Complete pipeline configuration model
- JSON serialization/deserialization
- Validation helpers
- Mode description getters

**Key Methods**:
```dart
- fromJson() / toJson() - API serialization
- toUpdateJson() - Update payload generation
- copyWith() - Immutable updates
- modeDescription - Human-readable mode
- isValid / hasValidInterval / hasValidDuration - Validation
```

#### Camera Model Extensions
**Location**: `lib/core/models/camera.dart`

**Added Fields**:
```dart
final bool instantDetectionEnabled;
final bool recordingPipelineEnabled;
final int instantDetectionIntervalSeconds;
final int segmentDurationSeconds;
```

**Helper Methods**:
```dart
String get pipelineModeDescription - Full description
String get pipelineMode - Short mode name
```

### 2. API Service Integration

**Location**: `lib/core/services/camera_service.dart`

**New Methods**:
```dart
/// Get pipeline settings for a camera
Future<Map<String, dynamic>> getPipelineSettings(String deviceId)

/// Update pipeline settings
Future<Map<String, dynamic>> updatePipelineSettings(
  String deviceId, {
  bool? instantDetectionEnabled,
  bool? recordingPipelineEnabled,
  int? instantDetectionIntervalSeconds,
  int? segmentDurationSeconds,
})
```

**Endpoints**:
- GET `/api/v1/cameras/{device_id}/pipeline-settings`
- PATCH `/api/v1/cameras/{device_id}/pipeline-settings`

### 3. Pipeline Settings Screen

**Location**: `lib/presentation/screens/cameras/camera_pipeline_settings_screen.dart`

#### UI Components

**Camera Info Card**:
- Camera icon (USB/RTSP/Mobile)
- Camera name and device ID
- Resolution display

**Pipeline Toggles Card**:
- ⚡ Instant Detection toggle with icon
- 🔴 Recording Pipeline toggle with icon
- Descriptive subtitles for each pipeline

**Advanced Settings Card** (Expandable):
- Instant detection interval slider (1-60 seconds)
- Segment duration slider (5-300 seconds)
- Only shows relevant sliders based on enabled pipelines

**Mode Description Card**:
- Color-coded mode indicator
- Current mode name (Both/Detection Only/Recording Only)
- Detailed mode explanation

**Resource Impact Card**:
- Disk space savings estimates
- CPU usage comparisons
- Network bandwidth impact

**Save Button**:
- Full-width elevated button
- Loading state during save
- Disabled when invalid

#### Validation

**Client-Side Validation**:
- At least one pipeline must be enabled
- Interval: 1-60 seconds
- Duration: 5-300 seconds
- Error snackbars for validation failures

#### State Management

**Loading States**:
- Initial settings load (on screen open)
- Save operation (with loading indicator)

**Error Handling**:
- API error display
- Network error handling
- User-friendly error messages

### 4. Camera Card Updates

**Location**: `lib/presentation/widgets/camera/camera_card.dart`

#### Pipeline Status Indicators

**Instant Detection Indicator** (⚡):
- Orange lightning bolt icon
- Shown when `instantDetectionEnabled = true`
- Tooltip: "Instant Detection Active"

**Recording Pipeline Indicator** (🔴):
- Red recording dot icon
- Shown when `recordingPipelineEnabled = true`
- Tooltip: "Recording Pipeline Active"

#### Settings Button

**Tune Icon** (⚙️):
- Small icon button next to status indicators
- Opens pipeline settings screen
- Tooltip: "Pipeline Settings"
- Navigates to `CameraPipelineSettingsScreen`

#### Navigation

**Settings Navigation**:
```dart
Navigator.of(context).push(
  MaterialPageRoute(
    builder: (context) => CameraPipelineSettingsScreen(camera: camera),
  ),
).then((result) {
  if (result == true) {
    // Reload cameras after settings change
    ref.read(cameraListProvider.notifier).loadCameras();
  }
});
```

## User Flow

### Viewing Pipeline Status

1. User opens Cameras screen
2. Each camera card shows:
   - ⚡ icon if instant detection enabled
   - 🔴 icon if recording enabled
   - ⚙️ settings button

### Configuring Pipeline Settings

1. User taps ⚙️ settings button on camera card
2. Pipeline settings screen opens
3. User sees current mode and settings
4. User toggles pipelines on/off
5. User expands advanced settings (optional)
6. User adjusts intervals/durations
7. User sees real-time mode updates
8. User taps "Save Settings"
9. Settings saved to backend
10. Camera list refreshed with new settings
11. User returned to cameras screen

### Validation Flow

**Invalid Configuration Attempt**:
1. User disables both pipelines
2. User taps "Save Settings"
3. Red snackbar appears: "At least one pipeline must be enabled"
4. Settings not saved

**Out of Range Value**:
1. User sets interval to 100 seconds (via hypothetical text input)
2. Validation catches invalid value
3. Error shown: "Interval must be between 1 and 60 seconds"

## Visual Design

### Color Coding

**Mode Colors**:
- 🟢 Green: Both pipelines active (full monitoring)
- 🟠 Orange: Instant detection only (privacy mode)
- 🔵 Blue: Recording only (archival mode)
- 🔴 Red: Both disabled (invalid)

**Pipeline Icons**:
- ⚡ Orange lightning: Instant detection
- 🔴 Red dot: Recording pipeline
- ⚙️ Gray tune icon: Settings access

### Card Layout

```
┌─────────────────────────────────────────┐
│ Camera Info Card                        │
│  📷 Camera Icon  Camera Name            │
│                 device_id_here          │
│  Resolution: 1280x720                   │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ Pipelines                               │
│                                         │
│  ⚡  Instant Detection          [✓]     │
│     Real-time person detection...      │
│                                         │
│  ─────────────────────────────────      │
│                                         │
│  🔴  Recording Pipeline         [✓]     │
│     Video segments with face...        │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ ⚙️  Advanced Settings         ▼         │
│                                         │
│  Detection Interval: 5 seconds         │
│  ─────●────────────────────────────     │
│  How often to detect people...         │
│                                         │
│  Segment Duration: 30 seconds          │
│  ─────────────●────────────────────     │
│  Length of each video segment...       │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ ℹ️  Current Mode                         │
│                                         │
│  Both Pipelines Active                  │
│  Real-time person detection with...    │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│       [  Save Settings  ]               │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ 💡 Resource Impact                      │
│                                         │
│  Both pipelines: Full monitoring...    │
│  Highest resource usage...             │
└─────────────────────────────────────────┘
```

## API Integration

### Get Settings Request

```dart
final cameraService = ref.read(cameraServiceProvider);
final settings = await cameraService.getPipelineSettings('usb_camera_0');
```

**Response**:
```json
{
  "device_id": "usb_camera_0",
  "camera_name": "USB Camera 0",
  "instant_detection_enabled": true,
  "recording_pipeline_enabled": true,
  "instant_detection_interval_seconds": 5,
  "segment_duration_seconds": 30
}
```

### Update Settings Request

```dart
await cameraService.updatePipelineSettings(
  'usb_camera_0',
  instantDetectionEnabled: true,
  recordingPipelineEnabled: false,
  instantDetectionIntervalSeconds: 10,
);
```

**Request Body**:
```json
{
  "instant_detection_enabled": true,
  "recording_pipeline_enabled": false,
  "instant_detection_interval_seconds": 10
}
```

## Testing Checklist

### Manual Testing

- [ ] Open cameras screen and verify status indicators appear
- [ ] Tap settings button and verify screen opens
- [ ] Toggle both pipelines on/off
- [ ] Verify mode description updates in real-time
- [ ] Expand advanced settings
- [ ] Adjust interval slider (1-60 range)
- [ ] Adjust duration slider (5-300 range)
- [ ] Save with both enabled
- [ ] Verify settings persist after save
- [ ] Try to save with both disabled (should fail)
- [ ] Verify error message appears
- [ ] Save instant-detection-only mode
- [ ] Verify camera card shows only ⚡ icon
- [ ] Save recording-only mode
- [ ] Verify camera card shows only 🔴 icon
- [ ] Verify camera list refreshes after save
- [ ] Test on different camera types (USB/RTSP/Mobile)

### Edge Cases

- [ ] Network error during load
- [ ] Network error during save
- [ ] Invalid response format
- [ ] Concurrent settings changes
- [ ] Screen rotation (if mobile)
- [ ] Back button during save
- [ ] Multiple rapid saves

### Accessibility

- [ ] Screen reader support for all controls
- [ ] Tooltip text on all icons
- [ ] Color contrast for text
- [ ] Touch target sizes (44x44 minimum)
- [ ] Keyboard navigation
- [ ] Focus indicators

## Known Limitations

1. **No Undo**: Settings are saved immediately, no draft mode
2. **No Bulk Edit**: Must configure cameras one at a time
3. **No Presets**: Cannot save/load configuration presets
4. **No History**: No view of previous configurations

## Future Enhancements

### Phase 4 (Potential)

1. **Configuration Templates**:
   - Save settings as named templates
   - Apply template to multiple cameras
   - Template library (Privacy, Performance, Full)

2. **Bulk Operations**:
   - Select multiple cameras
   - Apply settings to selection
   - "Copy settings from..." option

3. **Advanced Analytics**:
   - Resource usage graphs per mode
   - Cost estimates based on settings
   - Performance recommendations

4. **Schedule Support**:
   - Different settings for different times
   - Automatic mode switching
   - Business hours vs off-hours

5. **Camera Groups**:
   - Group cameras by location/purpose
   - Apply settings per group
   - Group-level defaults

## Troubleshooting

### Settings Not Saving

**Symptom**: Save button pressed but settings don't persist

**Solutions**:
1. Check network connectivity
2. Verify backend service is running
3. Check browser console for errors
4. Verify JWT token is valid

### Status Indicators Not Showing

**Symptom**: ⚡ and 🔴 icons missing on camera cards

**Solutions**:
1. Verify camera list has been refreshed
2. Check camera model has pipeline fields
3. Verify fromJson parsing is working
4. Check backend is returning pipeline fields

### Validation Errors

**Symptom**: Cannot save even with valid settings

**Solutions**:
1. Check both pipelines not disabled
2. Verify interval is 1-60
3. Verify duration is 5-300
4. Check backend validation rules match

---

**Implementation Status**: ✅ Complete  
**Backend Status**: ✅ Complete  
**Ready for**: End-to-end testing and deployment
