# Face Detection Workflow Management and Frontend Integration

## Document Overview
This document outlines the requirements, current implementation status, and integration plan for Flutter frontend workflow management with the PPL Meta Platform's face detection system.

## Requirements

### 1. Persistent Workflow Selection
**Requirement**: Keep the workflow method that the user chose from the dialog persistent for each camera.

**User Story**: When a user selects a face detection method (e.g., "two_stage", "mtcnn", "haar", "dlib") from the camera dialog for a specific camera, this choice should be remembered and automatically applied to future recordings from that camera.

### 2. Workflow Progress Tracking
**Requirement**: Keep track of the progress of face detection workflows so when processing finishes, the video can be marked as processed.

**User Story**: When a face detection workflow is started, the frontend should monitor its progress and update the UI to show processing status, completion, or failure. Upon completion, videos should be visually marked as "processed" in the interface.

## Current Implementation Status

### ✅ Backend Infrastructure (COMPLETED)
- **Two-Stage Default**: All services now use "two_stage" as the default face detection method
- **Workflow Tracking**: MediaWorkflow database model implemented in media service
- **Status Monitoring**: Orchestrator workflow completion monitoring fixed
- **Cross-Service Integration**: All services (orchestrator, media, cameras, vision) properly integrated
- **API Endpoints**: Complete workflow management endpoints available

### 🔄 Frontend Integration (IN PROGRESS/REQUIRED)

#### Current Flutter App Structure
- **Camera Cards**: Display available cameras with basic controls
- **Workflow Dialog**: Allows users to select face detection methods
- **Method Options**: Supports "two_stage", "mtcnn", "haar", "dlib" selection

#### Missing Frontend Components
1. **Persistent Method Storage**: Camera settings not persisted per camera
2. **Workflow Progress UI**: No real-time progress tracking interface
3. **Status Indicators**: No visual indication of processing state
4. **Completion Handling**: No automatic UI updates when workflows complete

## Technical Architecture

### Backend Workflow Flow
```
1. Camera Recording → Camera Service (8005)
2. Recording Saved → Media Service (8000) 
3. User Initiates Workflow → Orchestrator Service (8002)
4. Orchestrator → Media Service Workflow API
5. Media Service → Vision Service (8003) for processing
6. Results → Vision Service storage
7. Status Updates → Orchestrator → Frontend
```

### Key API Endpoints

#### Camera Service (Port 8005)
- `GET /api/v1/cameras/{device_id}/settings` - Get camera settings
- `PUT /api/v1/cameras/{device_id}/settings` - Update camera settings
- `POST /api/v1/streaming/{device_id}/record/start` - Start recording

#### Orchestrator Service (Port 8002) 
- `POST /workflows/face-detection/bulk-process` - Start workflow
- `GET /workflows/face-detection/status/{workflow_id}` - Get workflow status

#### Media Service (Port 8000)
- `GET /api/v1/workflow/face-detection/status/{workflow_id}` - Get detailed workflow status
- `GET /api/v1/media/search` - Search for media files

### Current Authentication
- User token from: `POST /api/v1/users/login` (Node service, port 8001)
- Token format: Bearer JWT token
- Valid across all services

## Implementation Plan

### Phase 1: Persistent Workflow Selection

#### Camera Settings Schema Enhancement
The camera settings already support `detection_methods` field:
```json
{
  "detection_methods": ["two_stage"],
  "confidence_threshold": 0.5,
  "enable_face_detection": true
}
```

#### Flutter Frontend Tasks
1. **Camera Settings Persistence**
   - Store selected method in camera settings via API
   - Load camera settings when displaying camera cards
   - Default to "two_stage" if no preference set

2. **UI State Management**
   - Update camera dialog to save selection
   - Show current method in camera card UI
   - Persist selection across app sessions

#### Implementation Steps
```dart
// Example API calls needed
class CameraSettingsService {
  Future<CameraSettings> getCameraSettings(String deviceId) async {
    // GET /api/v1/cameras/{device_id}/settings
  }
  
  Future<void> updateCameraSettings(String deviceId, CameraSettings settings) async {
    // PUT /api/v1/cameras/{device_id}/settings
  }
}

class CameraSettings {
  List<String> detectionMethods;
  double confidenceThreshold;
  bool enableFaceDetection;
}
```

### Phase 2: Workflow Progress Tracking

#### Workflow Status Data Structure
```json
{
  "workflow_id": "ae3151b7-39aa-4187-8e72-c1443dd50956",
  "status": "processing", // "queued", "processing", "completed", "failed"
  "progress": 0.75, // 0.0 to 1.0
  "processed_count": 3,
  "total_count": 4,
  "current_media_id": "6cb0a76c-70da-441d-9411-9f5ae579ee0c",
  "started_at": "2025-09-21T11:34:52Z",
  "completed_at": null,
  "error_message": null,
  "metadata": {
    "methods": ["two_stage"],
    "media_ids": ["..."]
  }
}
```

#### Flutter Frontend Tasks

1. **Workflow State Management**
   - **Leverage Existing:** Use `WorkflowTracker` class with Riverpod providers
   - **Extend:** `activeWorkflowsProvider` already tracks orchestrator workflows
   - **Add:** Media-to-workflow mapping in `workflow_providers.dart`
   - **Implementation:** Store workflow IDs in `Map<String, String>` (mediaId → workflowId)
   - **Pattern:** Use existing `FutureProvider.family` pattern for per-media workflow status

2. **Progress UI Components** 
   - **Existing Widgets:** Extend `_MediaGridItem` in `responsive_media_gallery.dart`
   - **Status Indicators:** Add workflow progress overlay to existing media thumbnails
   - **Progress Bars:** Use existing `CircularProgressIndicator` patterns with workflow progress data
   - **Badge System:** Extend existing `_buildTypeIndicator()` to include processing status
   - **Real-time Updates:** Leverage existing `StreamController<WorkflowStatus>` pattern

3. **Media Processing State**
   - **Visual Integration:** Enhance `_MediaGridItem` class with processing state overlays
   - **Status Types:** Add "Processing", "Processed", "Failed" states to existing media grid
   - **Indicators:** Use existing icon/badge system with workflow-specific colors
   - **Error Handling:** Extend existing `_buildErrorState()` pattern for workflow failures
   - **Completion Marking:** Add checkmark overlay similar to existing selection system

#### Implementation Steps

**Phase 2A: Enhanced Workflow State Management**
```dart
// Extend existing workflow_providers.dart with media workflow tracking
final mediaWorkflowProvider = StateNotifierProvider.family<MediaWorkflowNotifier, MediaWorkflowState, String>((ref, mediaId) {
  return MediaWorkflowNotifier(ref, mediaId);
});

final workflowProgressProvider = FutureProvider.family<WorkflowProgress, String>((ref, workflowId) async {
  final client = ref.watch(workflowApiClientProvider);
  return client.getWorkflowProgress(workflowId); // New method to implement
});

class MediaWorkflowNotifier extends StateNotifier<MediaWorkflowState> {
  final Ref ref;
  final String mediaId;
  Timer? _pollTimer;
  
  MediaWorkflowNotifier(this.ref, this.mediaId) : super(MediaWorkflowState.idle());
  
  Future<void> startWorkflow(String method) async {
    // Call orchestrator API to start workflow
    // Store workflow ID and begin progress polling
  }
  
  void _startPolling(String workflowId) {
    _pollTimer = Timer.periodic(Duration(seconds: 2), (_) async {
      // Poll workflow status and update state
    });
  }
}
```

**Phase 2B: Enhanced Media Grid with Workflow Status**  
```dart
// Extend existing _MediaGridItem class in responsive_media_gallery.dart
class _MediaGridItem extends StatelessWidget {
  // ... existing code ...
  
  @override
  Widget build(BuildContext context) {
    // Get workflow status for this media item
    final workflowStatus = ref.watch(mediaWorkflowProvider(item.mediaId));
    
    return GestureDetector(
      // ... existing gesture handling ...
      child: AnimatedContainer(
        // ... existing container ...
        child: ClipRRect(
          child: Stack(
            children: [
              _buildMediaContent(),
              if (item.mediaType == MediaType.video) _buildVideoPlayOverlay(),
              if (enableSelection) _buildSelectionOverlay(),
              _buildTypeIndicator(),
              if (item.duration != null) _buildDurationIndicator(),
              
              // NEW: Workflow progress overlay
              _buildWorkflowProgressOverlay(workflowStatus),
              
              // NEW: Processing status badge
              _buildProcessingStatusBadge(workflowStatus),
            ],
          ),
        ),
      ),
    );
  }
  
  Widget _buildWorkflowProgressOverlay(MediaWorkflowState workflowState) {
    if (!workflowState.isProcessing) return SizedBox.shrink();
    
    return Positioned.fill(
      child: Container(
        decoration: BoxDecoration(
          color: AppColors.black.withOpacity(0.5),
        ),
        child: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              CircularProgressIndicator(
                value: workflowState.progress,
                color: AppColors.primary,
              ),
              SizedBox(height: 8),
              Text(
                '${(workflowState.progress * 100).toInt()}%',
                style: AppTextStyles.caption.copyWith(color: AppColors.white),
              ),
            ],
          ),
        ),
      ),
    );
  }
  
  Widget _buildProcessingStatusBadge(MediaWorkflowState workflowState) {
    if (workflowState.isIdle) return SizedBox.shrink();
    
    return Positioned(
      bottom: AppSpacing.sm,
      left: AppSpacing.sm,
      child: Container(
        padding: EdgeInsets.symmetric(horizontal: 6, vertical: 2),
        decoration: BoxDecoration(
          color: _getWorkflowStatusColor(workflowState.status),
          borderRadius: BorderRadius.circular(AppRadius.xs),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              _getWorkflowStatusIcon(workflowState.status),
              size: 12,
              color: AppColors.white,
            ),
            SizedBox(width: 4),
            Text(
              workflowState.status.displayName,
              style: AppTextStyles.caption.copyWith(
                color: AppColors.white,
                fontSize: 10,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
```

**Phase 2C: Camera Settings Integration**
```dart
// Enhance existing CameraCard in camera_card.dart
class CameraCard extends ConsumerWidget {
  // ... existing code ...
  
  Widget _buildActionButtons(BuildContext context, WidgetRef ref) {
    // Get saved camera settings
    final cameraSettings = ref.watch(cameraSettingsProvider(camera.deviceId));
    
    return Row(
      children: [
        // ... existing buttons ...
        
        // NEW: Workflow method selector
        Expanded(
          child: ElevatedButton.icon(
            onPressed: () => _showWorkflowMethodDialog(context, ref),
            icon: Icon(Icons.psychology),
            label: Text(
              cameraSettings.value?.detectionMethods.first ?? "two_stage"
            ),
          ),
        ),
      ],
    );
  }
  
  Future<void> _showWorkflowMethodDialog(BuildContext context, WidgetRef ref) async {
    final currentMethod = ref.read(cameraSettingsProvider(camera.deviceId)).value?.detectionMethods.first ?? "two_stage";
    
    final method = await showDialog<String>(
      context: context,
      builder: (context) => WorkflowMethodDialog(
        currentMethod: currentMethod,
        availableMethods: ["two_stage", "mtcnn", "haar", "dlib"],
      ),
    );
    
    if (method != null) {
      // Save method to camera settings via API
      await ref.read(cameraSettingsProvider(camera.deviceId).notifier).updateDetectionMethods([method]);
    }
  }
}
```

**Phase 2D: Real-time Status Updates**
```dart
// Add to existing workflow_providers.dart
final workflowStatusStreamProvider = StreamProvider.family<WorkflowStatus, String>((ref, workflowId) {
  return Stream.periodic(Duration(seconds: 2))
    .asyncMap((_) async {
      final client = ref.read(workflowApiClientProvider);
      final response = await client.getWorkflowStatus(workflowId);
      return response.data!;
    });
});

// Integration with existing media gallery refresh pattern
class ResponsiveMediaGallery extends StatefulWidget {
  // ... existing code with automatic refresh already implemented ...
  
  @override
  void initState() {
    super.initState();
    // Existing refresh logic can be enhanced to poll workflow status
    _startWorkflowStatusPolling();
  }
  
  void _startWorkflowStatusPolling() {
    // Poll for active workflows and update UI accordingly
    Timer.periodic(Duration(seconds: 3), (_) {
      if (mounted) {
        // Refresh workflow status for visible media items
        setState(() {});
      }
    });
  }
}
```

## Existing Flutter Widget Integration

### ✅ Available Widget Components

#### 1. **Media Gallery Infrastructure**
- **ResponsiveMediaGallery**: Main media display widget with responsive grid layout
- **_MediaGridItem**: Individual media item with thumbnail, status indicators, and selection
- **DraggableMediaItem**: Drag-and-drop functionality for media organization
- **MediaDetailsDialog**: Detailed view dialog for media items

#### 2. **Camera Management Widgets**
- **CameraCard**: Main camera display widget with status, controls, and settings
- **CameraDeviceSelector**: Camera discovery and selection interface
- **LiveCameraPreview**: Real-time camera stream display
- **CameraMonitoringDashboard**: Multi-camera status overview

#### 3. **Workflow Widgets** 
- **QuickWorkflowSettingsDialog**: Method selection dialog interface
- **WorkflowProcessedVideosWidget**: Displays processed videos with status indicators
- **WorkflowPerformanceMetricsWidget**: Performance analytics and metrics

#### 4. **State Management (Riverpod)**
- **workflow_providers.dart**: Complete workflow API integration
- **camera_providers.dart**: Camera state and settings management  
- **settings_providers.dart**: Persistent application settings

### 🔄 Required Widget Enhancements

#### 1. **_MediaGridItem Enhancements**
```dart
// Current: Basic media display with selection
// Required: Add workflow progress overlay, processing status badge
// Integration: Extend existing Stack with workflow status layers
```

#### 2. **CameraCard Workflow Integration**
```dart
// Current: Camera status, recording controls, device info
// Required: Workflow method selector, persistent method display
// Integration: Add workflow button to existing action row
```

#### 3. **Workflow Status Tracking**
```dart
// Current: Basic workflow API providers exist
// Required: Media-to-workflow mapping, real-time polling
// Integration: Extend existing FutureProvider.family patterns
```

### 🛠 Implementation Strategy

#### Phase 1: Extend Existing _MediaGridItem
- **Target Widget**: `widgets/responsive_media_gallery.dart` → `_MediaGridItem`
- **Enhancement**: Add workflow progress overlay to existing Stack
- **Pattern**: Follow existing `_buildTypeIndicator()` and `_buildDurationIndicator()` patterns
- **Integration**: Use existing `AppColors`, `AppTextStyles`, and `AppRadius` theme system

#### Phase 2: Enhance CameraCard Workflow Controls  
- **Target Widget**: `widgets/camera/camera_card.dart` → `_buildActionButtons()`
- **Enhancement**: Add workflow method selector button to existing row
- **Pattern**: Follow existing button styling and dialog patterns
- **Integration**: Use existing camera settings API and persistence patterns

#### Phase 3: Extend Workflow Providers
- **Target File**: `providers/workflow_providers.dart`
- **Enhancement**: Add media-workflow mapping and progress tracking providers  
- **Pattern**: Follow existing `FutureProvider.family` and `StateNotifierProvider` patterns
- **Integration**: Use existing `workflowApiClientProvider` and authentication

### 📱 UI Integration Points

#### Media Gallery Integration
```dart
// Extend existing _MediaGridItem build method
Stack(
  children: [
    _buildMediaContent(),                    // ✅ EXISTS
    _buildVideoPlayOverlay(),               // ✅ EXISTS  
    _buildSelectionOverlay(),               // ✅ EXISTS
    _buildTypeIndicator(),                  // ✅ EXISTS
    _buildDurationIndicator(),              // ✅ EXISTS
    
    _buildWorkflowProgressOverlay(),        // 🔄 NEW - Progress indicator
    _buildProcessingStatusBadge(),          // 🔄 NEW - Status badge
  ],
)
```

#### Camera Settings Integration
```dart
// Extend existing CameraCard _buildActionButtons()
Row(
  children: [
    // ✅ EXISTS: Recording, stream, settings buttons
    _buildRecordingButton(),
    _buildStreamButton(), 
    _buildSettingsButton(),
    
    _buildWorkflowMethodSelector(),         // 🔄 NEW - Method selector
  ],
)
```

### 🎨 Design Consistency

#### Use Existing Theme System
- **Colors**: `AppColors.primary`, `AppColors.success`, `AppColors.warning`, `AppColors.error`
- **Typography**: `AppTextStyles.caption`, `AppTextStyles.bodyMedium`
- **Spacing**: `AppSpacing.sm`, `AppSpacing.md`, `AppSpacing.lg`
- **Radius**: `AppRadius.xs`, `AppRadius.sm`, `AppRadius.md`
- **Shadows**: `AppShadows.sm`, `AppShadows.md`

#### Follow Existing Patterns
- **Loading States**: Use existing `CircularProgressIndicator` patterns
- **Error States**: Follow existing `_buildErrorState()` approach
- **Dialogs**: Use existing dialog theming and structure
- **Animations**: Follow existing `AnimatedContainer` and transition patterns

### 💾 State Persistence Integration

#### Leverage Existing Patterns
- **Camera Settings**: Extend existing `cameraSettingsProvider` for method persistence
- **User Preferences**: Use existing SharedPreferences integration patterns
- **API Integration**: Follow existing authentication and API client patterns
- **Error Handling**: Use existing error handling and retry mechanisms

#### Test Scenarios
1. **Camera Settings Persistence**
   - Select method for camera A → restart app → verify method remembered
   - Different methods for different cameras → verify isolation
   
2. **Workflow Progress**
   - Start recording → initiate workflow → track progress → verify completion
   - Multiple simultaneous workflows → verify independent tracking
   - Workflow failures → verify error handling

3. **End-to-End Integration**
   - Record video → select custom method → monitor progress → verify processed state
   - Background processing → app restart → verify workflow recovery

## Current Verification Status

### ✅ Verified Working

#### Backend Infrastructure
- **Two-stage method standardization** across all services (8+ files updated)
- **MediaWorkflow database model** with real-time status tracking
- **Cross-service communication** orchestrator ↔ media ↔ vision ↔ cameras
- **End-to-end integration testing** completed successfully

#### Authentication (Node Service - Port 8001)
- ✅ `POST /api/v1/users/login` - User authentication with JWT token
- ✅ Token format: `Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...`
- ✅ Cross-service token validation working

#### Camera Service (Port 8005) 
- ✅ `GET /api/v1/cameras/detect?save_to_db=true` - Camera detection
- ✅ `POST /api/v1/cameras/{device_id}/connect` - Camera connection
- ✅ `GET /api/v1/cameras/{device_id}/settings` - Camera settings retrieval
- ✅ `PUT /api/v1/cameras/{device_id}/settings` - Camera settings update
- ✅ `POST /api/v1/streaming/{device_id}/record/start` - Recording start
- ✅ `POST /api/v1/streaming/{device_id}/record/stop` - Recording stop

#### Media Service (Port 8000)
- ✅ `GET /api/v1/media/search` - Media search and retrieval
- ✅ `GET /api/v1/workflow/face-detection/status/{workflow_id}` - Workflow status
- ✅ `POST /api/v1/face-detection/workflows/bulk-process` - Workflow initiation
- ✅ MediaWorkflow database persistence and status updates

#### Orchestrator Service (Port 8002)
- ✅ `POST /workflows/face-detection/bulk-process` - Workflow orchestration
- ✅ `GET /workflows/face-detection/status/{workflow_id}` - Status monitoring
- ✅ `GET /workflows/user/{user_id}/workflows` - User workflow history
- ✅ Real-time workflow completion monitoring operational

#### Vision Service (Port 8003)
- ✅ Face detection processing with two_stage method
- ✅ Integration with media service workflow tracking
- ✅ Results storage and status reporting

#### Verified Integration Workflow
1. ✅ **User Authentication**: Login → JWT token acquisition
2. ✅ **Camera Setup**: Detection → connection → settings configuration  
3. ✅ **Recording Creation**: 30-second USB camera recording (ID: 9f139302-5499-4770-828d-6da81441985f)
4. ✅ **Media Registration**: Recording saved and searchable in media service
5. ✅ **Workflow Initiation**: Orchestrator workflow created (ID: ae3151b7-39aa-4187-8e72-c1443dd50956)
6. ✅ **Method Verification**: Workflow metadata shows "methods": ["two_stage"]
7. ✅ **Status Tracking**: Real-time workflow progress monitoring functional

### 🔄 Next Steps Required
1. **Frontend workflow integration** - Connect Flutter app to workflow APIs
2. **Settings persistence** - Implement camera-specific method storage
3. **Progress monitoring** - Real-time workflow status updates in UI
4. **State management** - Track processing state for media items

## Technical Notes

### Authentication Pattern

#### Step 1: Get User Token
```bash
# Login to get JWT token
curl -X POST 'http://localhost:8001/api/v1/users/login' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=fresh.user@example.com&password=NewPassword234!'

# Response contains JWT token:
# {"access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...", "token_type": "bearer"}
```

#### Step 2: Use Token for API Calls
All workflow API calls require Bearer token:
```bash
# Extract token from login response
export AUTH_TOKEN="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."

# Use token in workflow API calls
curl -H "Authorization: Bearer $AUTH_TOKEN" http://localhost:8002/workflows/face-detection/bulk-process
curl -H "Authorization: Bearer $AUTH_TOKEN" http://localhost:8002/workflows/face-detection/status/{workflow_id}
curl -H "Authorization: Bearer $AUTH_TOKEN" http://localhost:8000/api/v1/workflow/face-detection/status/{workflow_id}
```

#### Flutter Integration
```dart
// In Flutter app - use existing authentication flow
final authToken = ref.watch(authTokenProvider);
final headers = {
  'Authorization': 'Bearer $authToken',
  'Content-Type': 'application/json',
};
```

### Error Handling
- Network failures: Implement retry logic with exponential backoff
- Workflow failures: Show user-friendly error messages
- Token expiry: Automatic re-authentication flow

### Performance Considerations
- Polling frequency: Balance real-time updates vs. server load
- State persistence: Use local storage for offline capability
- Memory management: Clean up completed workflow tracking

## Dependencies

### Backend Services Required
- ✅ Camera Service (8005) - Settings management
- ✅ Orchestrator Service (8002) - Workflow orchestration  
- ✅ Media Service (8000) - Workflow execution
- ✅ Vision Service (8003) - Face detection processing
- ✅ Node Service (8001) - User authentication

### Flutter Packages Needed
- `http` or `dio` - API communication
- `provider` or `riverpod` - State management
- `shared_preferences` - Local persistence
- `stream_builder` - Real-time UI updates

## Success Criteria

### Requirement 1: Persistent Workflow Selection
- [ ] User can select face detection method for each camera
- [ ] Selection is saved and remembered across app sessions
- [ ] Different cameras can have different method preferences
- [ ] Default to "two_stage" for new cameras

### Requirement 2: Workflow Progress Tracking  
- [ ] UI shows processing status for ongoing workflows
- [ ] Progress indicators update in real-time
- [ ] Videos are marked as "processed" upon completion
- [ ] Failed workflows show appropriate error states
- [ ] User can see processing history/status

### Integration Success
- [ ] Complete end-to-end workflow from recording to processed state
- [ ] Robust error handling and recovery
- [ ] Seamless user experience with minimal manual intervention
- [ ] Performance acceptable for real-world usage

---

**Document Status**: Initial requirements capture and technical analysis  
**Last Updated**: September 21, 2025  
**Next Review**: After Phase 1 implementation completion