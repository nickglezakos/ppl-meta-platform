# Orchestrator Face Detection Flutter Integration Guide

**Objective**: Integrate the working Orchestrator face detection endpoints with Flutter frontend to:
1. Display correct face detection counts in widgets
2. Feed green rectangle coordinates to video overlay

**Status**: ✅ Backend endpoints working, ✅ Flutter app running, 🔄 Integration needed

---

## 📋 Current Architecture Overview

### ✅ Working Backend Components
- **Orchestrator Service**: `http://localhost:8002`
  - `POST /api/v1/face-detection` - Creates face detection sessions
  - `GET /api/v1/sessions/{session_id}` - Retrieves session results
- **Vision Service**: `http://localhost:8003` - Process face detection
- **Gateway Service**: `http://localhost:8080` - Routes requests via Nginx
- **Authentication**: JWT tokens via Node service

### ✅ Working Frontend Components
- **Flutter App**: Running on `http://localhost:3000`
- **Face Count Widgets**: Need data source update
- **Video Overlay**: Needs rectangle coordinate feed

---

## 🎯 Integration Requirements

### 1. Face Detection Count Widget
**Current Issue**: Likely calling Vision service directly or using stale data
**Target**: Use Orchestrator session-based face detection results

**Required Changes**:
```dart
// Instead of direct Vision service calls:
// GET http://localhost:8003/faces/media/{media_id}

// Use Orchestrator workflow:
// 1. POST http://localhost:8002/api/v1/face-detection
// 2. Poll GET http://localhost:8002/api/v1/sessions/{session_id}
// 3. Extract total_faces from results
```

### 2. Green Rectangle Video Overlay
**Current Issue**: No coordinate data source or using incompatible format
**Target**: Use Orchestrator session results for rectangle coordinates

**Required Changes**:
```dart
// Extract from session results:
// results.faces_by_frame[frame_number][face_index].bbox
// Format: [x, y, width, height] with confidence scores
```

---

## 📂 Flutter Code Analysis Required

### Files to Examine
1. **Face Count Widgets**:
   - `lib/widgets/face_detection_count_widget.dart` (if exists)
   - `lib/widgets/performance/simple_performance_metrics_widget.dart`
   - `lib/providers/simple_performance_providers.dart`

2. **Video Overlay Components**:
   - `lib/widgets/video_face_detection_overlay.dart`
   - `lib/widgets/face_detection_overlay.dart`
   - `lib/widgets/workflow/workflow_widget_registry.dart`

3. **API Integration**:
   - `lib/services/orchestrator_api_client.dart`
   - `lib/providers/workflow_providers.dart`
   - `lib/services/vision_api_client.dart`

### Search Patterns
```bash
# Find face count implementations
grep -r "total_faces\|face.*count\|faces.*detected" lib/

# Find video overlay implementations  
grep -r "rectangle\|bbox\|overlay\|face.*detection" lib/

# Find Vision service API calls
grep -r "vision.*api\|faces/media" lib/

# Find Orchestrator API usage
grep -r "orchestrator.*api\|face-detection" lib/
```

---

## 🔧 Implementation Strategy

### Phase 1: Code Discovery & Mapping
1. **Locate Current Implementations**
   - Find existing face count widget implementations
   - Identify current data sources (Vision vs Orchestrator vs Mock)
   - Map video overlay rendering logic

2. **API Client Analysis**
   - Verify `OrchestratorApiClient` has face detection methods
   - Check if session polling is implemented
   - Identify missing API integration methods

### Phase 2: Orchestrator API Integration
1. **Update/Create Orchestrator API Methods**
   ```dart
   class OrchestratorApiClient {
     Future<FaceDetectionSession> createFaceDetectionSession(String mediaId);
     Future<FaceDetectionSession> getSessionStatus(String sessionId);
     Future<List<FaceDetectionSession>> getAllSessions();
   }
   ```

2. **Create Session Management Provider**
   ```dart
   final faceDetectionSessionProvider = StateNotifierProvider<FaceDetectionSessionNotifier, AsyncValue<FaceDetectionSession?>>();
   ```

### Phase 3: Widget Integration
1. **Face Count Widget Update**
   ```dart
   Consumer(
     builder: (context, ref, child) {
       final sessionAsync = ref.watch(faceDetectionSessionProvider);
       return sessionAsync.when(
         data: (session) => Text('${session?.results?.totalFaces ?? 0} faces'),
         loading: () => CircularProgressIndicator(),
         error: (error, stack) => Text('Error: $error'),
       );
     },
   )
   ```

2. **Video Overlay Update**
   ```dart
   class VideoFaceDetectionOverlay extends ConsumerWidget {
     Widget build(BuildContext context, WidgetRef ref) {
       final session = ref.watch(faceDetectionSessionProvider);
       final rectangles = extractRectanglesForCurrentFrame(session);
       return CustomPaint(painter: FaceRectanglePainter(rectangles));
     }
   }
   ```

---

## 📊 Data Flow Architecture

### Current (Problematic) Flow
```
Flutter Widget → Vision Service Direct → Display Results
```

### Target (Orchestrator) Flow
```
Flutter Widget → Orchestrator API → Session Creation → Polling → Results → Display
```

### Detailed Target Flow
1. **Trigger**: User opens media or requests face detection
2. **Session Creation**: `POST /api/v1/face-detection` with media_id
3. **Session Monitoring**: Poll `GET /api/v1/sessions/{session_id}` until completed
4. **Data Extraction**: Extract total_faces and faces_by_frame from results
5. **Widget Updates**: Update face count and video overlay via Riverpod providers

---

## 🔍 Expected Data Formats

### Orchestrator Session Response
```json
{
  "session_id": "uuid",
  "status": "completed",
  "results": {
    "media_id": "uuid",
    "total_faces": 190,
    "faces_by_frame": {
      "0": [
        {
          "bbox": [100, 150, 80, 100],
          "confidence": 0.95,
          "method": "dlib"
        }
      ],
      "1": [ ... ]
    },
    "statistics": {
      "frames_processed": 19,
      "processing_time": 5.2
    }
  }
}
```

### Flutter Widget Requirements
```dart
// Face Count: Extract total_faces
int faceCount = session.results?.totalFaces ?? 0;

// Video Overlay: Extract rectangles for specific frame
List<FaceRectangle> rectangles = session.results?.facesByFrame?[frameNumber]
  ?.map((face) => FaceRectangle(
    x: face.bbox[0],
    y: face.bbox[1], 
    width: face.bbox[2],
    height: face.bbox[3],
    confidence: face.confidence,
  ))?.toList() ?? [];
```

---

## 🚧 Known Challenges & Solutions

### Challenge 1: Async Session Processing
**Issue**: Orchestrator uses sessions, widgets expect immediate results
**Solution**: Implement proper async state management with loading states

### Challenge 2: Frame Synchronization
**Issue**: Video overlay needs frame-specific face rectangles
**Solution**: Pass current frame number to overlay widget, extract relevant rectangles

### Challenge 3: Error Handling
**Issue**: Session creation or polling might fail
**Solution**: Comprehensive error states in providers with retry logic

### Challenge 4: Performance
**Issue**: Constant polling might impact performance
**Solution**: Smart polling intervals, caching completed sessions

---

## 📋 Implementation Checklist

### Discovery Phase
- [ ] Find current face count widget implementations
- [ ] Identify video overlay rendering code
- [ ] Examine existing Orchestrator API client
- [ ] Map current data sources and providers

### API Integration Phase  
- [ ] Add/verify Orchestrator face detection API methods
- [ ] Implement session polling logic
- [ ] Create session management Riverpod providers
- [ ] Add error handling and retry logic

### Widget Integration Phase
- [ ] Update face count widgets to use Orchestrator sessions
- [ ] Modify video overlay to use session rectangle data
- [ ] Implement loading and error states
- [ ] Add frame synchronization for video overlay

### Testing Phase
- [ ] Test with known media IDs (190 faces expected)
- [ ] Verify face count accuracy
- [ ] Confirm rectangle overlay positioning
- [ ] Test error scenarios and recovery

---

## 🎯 Success Criteria

### Face Count Widget
- [ ] Displays correct count (190 for test media)
- [ ] Shows loading state during processing
- [ ] Handles errors gracefully
- [ ] Updates reactively when session completes

### Video Overlay
- [ ] Renders green rectangles at correct positions
- [ ] Synchronizes with video playback frame
- [ ] Shows confidence-based styling
- [ ] Performs smoothly without lag

### Overall Integration
- [ ] Uses Orchestrator API exclusively (no direct Vision calls)
- [ ] Maintains Flutter app responsiveness
- [ ] Provides consistent user experience
- [ ] Follows established app patterns and architecture

---

## 📖 Reference Information

### Notebook Session Results
- **Test Media ID**: `87eff63e-9a5a-4c5e-b1e8-0f033cff5658`
- **Expected Results**: 190 faces across 19 frames
- **Working Session**: `31e1af68-6e3c-4b3e-a004-4c86a5431bb3`
- **Orchestrator Endpoint**: `POST http://localhost:8002/api/v1/face-detection`
- **Session Monitor**: `GET http://localhost:8002/api/v1/sessions/{session_id}`

### Authentication
- **JWT Token**: Available and working
- **Headers**: `Authorization: Bearer {token}`

This guide provides the roadmap for successfully integrating the working Orchestrator face detection endpoints with the Flutter frontend. The key is methodical discovery of current implementations followed by systematic replacement with Orchestrator-based data sources.