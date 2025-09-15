# PPL Meta Frontend - Workflows 4 & 5 Integration Outline

**Target**: Expose new Workflow 4 & 5 functionality in Flutter frontend  
**Focus**: User experience for session-based face detection and optimized playback  
**Date**: September 15, 2025  

## 🎯 Overview

Integration outline for exposing **Workflow 4 (Session-Based Face Detection)** and **Workflow 5 (Optimized Playback for Processed Videos)** functionality in the PPL Meta Flutter frontend application.

## 📱 Current Frontend Architecture Analysis

### ✅ Current State
- **Media Preview**: `MediaPreviewScreen` with basic face detection overlay
- **Face Detection Widgets**: Multiple overlay widgets (`FaceDetectionOverlay`, `VideoFaceDetectionOverlay`, `SimpleFaceDetectionOverlay`)
- **Vision API Client**: `VisionApiClient` for face detection services
- **Media Models**: `MediaItem`, `FaceDetection` models
- **Video Player**: `VideoPlayerWidget` with basic streaming

### 🎯 Integration Requirements
1. **Workflow 4**: Session-based face detection with session management UI
2. **Workflow 5**: Smart playback mode selection and processing status display
3. **User Controls**: Face detection settings, session management, processing indicators
4. **Performance UI**: Show CPU/performance benefits from Workflow 5

---

## 🏗️ Frontend Integration Plan

### **1. Data Models & API Extensions**

#### **A. New Models to Add**

```dart
// lib/models/face_detection_models.dart

@JsonSerializable()
class FaceDetectionSession {
  final String sessionUuid;
  final String mediaUuid;
  final String status; // 'active', 'completed', 'failed'
  final DateTime createdAt;
  final DateTime? completedAt;
  final int? totalFramesProcessed;
  final int? totalFacesDetected;
  final double? confidenceThreshold;
  final List<String> detectionMethods;
  
  const FaceDetectionSession({
    required this.sessionUuid,
    required this.mediaUuid,
    required this.status,
    required this.createdAt,
    this.completedAt,
    this.totalFramesProcessed,
    this.totalFacesDetected,
    this.confidenceThreshold,
    this.detectionMethods = const [],
  });
}

@JsonSerializable()
class ProcessingStatus {
  final String mediaUuid;
  final bool faceDetectionProcessed;
  final String? sessionUuid;
  final DateTime? processingCompletedAt;
  final int? totalFramesProcessed;
  final int? totalFacesDetected;
  final String processingMethod; // 'workflow4', 'workflow5', 'realtime'
  final double? qualityScore;
  
  const ProcessingStatus({
    required this.mediaUuid,
    required this.faceDetectionProcessed,
    this.sessionUuid,
    this.processingCompletedAt,
    this.totalFramesProcessed,
    this.totalFacesDetected,
    required this.processingMethod,
    this.qualityScore,
  });
}

@JsonSerializable()
class PlaybackMode {
  final String mode; // 'stored_data', 'realtime_with_session', 'realtime_only'
  final String description;
  final bool cpuOptimized;
  final double? expectedCpuReduction;
  
  const PlaybackMode({
    required this.mode,
    required this.description,
    required this.cpuOptimized,
    this.expectedCpuReduction,
  });
}
```

#### **B. API Service Extensions**

```dart
// lib/services/workflow_api_client.dart

class WorkflowApiClient {
  final Dio _dio;
  final String baseUrl;

  // Workflow 4 - Session Management
  Future<FaceDetectionSession> createFaceDetectionSession({
    required String mediaUuid,
    double? confidenceThreshold,
    List<String>? detectionMethods,
  });
  
  Future<FaceDetectionSession> getSessionStatus(String sessionUuid);
  
  Future<List<FaceDetectionSession>> getSessionsForMedia(String mediaUuid);
  
  Future<void> deleteSession(String sessionUuid);
  
  // Workflow 5 - Processing Status & Smart Playback
  Future<ProcessingStatus> getProcessingStatus(String mediaUuid);
  
  Future<PlaybackMode> getOptimalPlaybackMode(String mediaUuid);
  
  Future<List<FaceDetection>> getStoredFaceData({
    required String mediaUuid,
    int? startFrame,
    int? endFrame,
  });
  
  Future<void> markVideoAsProcessed({
    required String mediaUuid,
    required String sessionUuid,
  });
}
```

### **2. Enhanced Media Preview Screen**

#### **A. Smart Playback Mode Selection**

```dart
// lib/screens/enhanced_media_preview_screen.dart

class EnhancedMediaPreviewScreen extends ConsumerStatefulWidget {
  // Add new state management for workflows
}

class _EnhancedMediaPreviewScreenState extends ConsumerState<EnhancedMediaPreviewScreen> {
  ProcessingStatus? _processingStatus;
  PlaybackMode? _currentPlaybackMode;
  FaceDetectionSession? _activeSession;
  bool _showWorkflowControls = false;
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: _buildEnhancedAppBar(),
      body: Column(
        children: [
          // Processing status indicator
          _buildProcessingStatusBar(),
          
          // Main media content with smart playback
          Expanded(child: _buildSmartMediaContent()),
          
          // Workflow controls (collapsible)
          if (_showWorkflowControls) _buildWorkflowControls(),
        ],
      ),
    );
  }
  
  Widget _buildProcessingStatusBar() {
    return Container(
      height: 40,
      color: Colors.grey[900],
      child: Row(
        children: [
          // Processing status indicator
          _buildProcessingIndicator(),
          
          // Playback mode indicator
          _buildPlaybackModeIndicator(),
          
          // Performance indicator
          _buildPerformanceIndicator(),
          
          const Spacer(),
          
          // Workflow controls toggle
          IconButton(
            icon: Icon(_showWorkflowControls 
              ? Icons.expand_less 
              : Icons.expand_more),
            onPressed: () => setState(() => 
              _showWorkflowControls = !_showWorkflowControls),
          ),
        ],
      ),
    );
  }
  
  Widget _buildProcessingIndicator() {
    if (_processingStatus == null) {
      return const SizedBox.shrink();
    }
    
    final isProcessed = _processingStatus!.faceDetectionProcessed;
    
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: isProcessed ? Colors.green[700] : Colors.orange[700],
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            isProcessed ? Icons.check_circle : Icons.hourglass_empty,
            size: 16,
            color: Colors.white,
          ),
          const SizedBox(width: 4),
          Text(
            isProcessed ? 'Processed' : 'Processing...',
            style: const TextStyle(color: Colors.white, fontSize: 12),
          ),
        ],
      ),
    );
  }
  
  Widget _buildPlaybackModeIndicator() {
    if (_currentPlaybackMode == null) return const SizedBox.shrink();
    
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: _currentPlaybackMode!.cpuOptimized 
          ? Colors.blue[700] 
          : Colors.grey[700],
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            _currentPlaybackMode!.cpuOptimized 
              ? Icons.flash_on 
              : Icons.memory,
            size: 16,
            color: Colors.white,
          ),
          const SizedBox(width: 4),
          Text(
            _getModeDisplayName(_currentPlaybackMode!.mode),
            style: const TextStyle(color: Colors.white, fontSize: 12),
          ),
        ],
      ),
    );
  }
}
```

#### **B. Workflow Controls Panel**

```dart
Widget _buildWorkflowControls() {
  return Container(
    padding: const EdgeInsets.all(16),
    color: Colors.grey[850],
    child: Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Face Detection Workflows',
          style: AppTextStyles.h6.copyWith(color: Colors.white),
        ),
        const SizedBox(height: 12),
        
        // Workflow 4 Controls
        _buildWorkflow4Controls(),
        
        const SizedBox(height: 16),
        
        // Workflow 5 Controls
        _buildWorkflow5Controls(),
        
        const SizedBox(height: 16),
        
        // Performance Metrics
        _buildPerformanceMetrics(),
      ],
    ),
  );
}

Widget _buildWorkflow4Controls() {
  return Card(
    color: Colors.grey[800],
    child: Padding(
      padding: const EdgeInsets.all(12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.play_circle, color: Colors.blue[400]),
              const SizedBox(width: 8),
              Text(
                'Workflow 4 - Session-Based Detection',
                style: AppTextStyles.body1.copyWith(
                  color: Colors.white,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          
          if (_activeSession != null) ...[
            _buildSessionInfo(_activeSession!),
            const SizedBox(height: 8),
          ],
          
          Row(
            children: [
              // Create new session button
              ElevatedButton.icon(
                onPressed: _activeSession == null ? _createNewSession : null,
                icon: const Icon(Icons.add_circle),
                label: const Text('New Session'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.blue[600],
                ),
              ),
              
              const SizedBox(width: 8),
              
              // Stop session button
              if (_activeSession != null)
                ElevatedButton.icon(
                  onPressed: _stopCurrentSession,
                  icon: const Icon(Icons.stop_circle),
                  label: const Text('Stop'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.red[600],
                  ),
                ),
            ],
          ),
        ],
      ),
    ),
  );
}

Widget _buildWorkflow5Controls() {
  return Card(
    color: Colors.grey[800],
    child: Padding(
      padding: const EdgeInsets.all(12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.speed, color: Colors.green[400]),
              const SizedBox(width: 8),
              Text(
                'Workflow 5 - Optimized Playback',
                style: AppTextStyles.body1.copyWith(
                  color: Colors.white,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          
          if (_processingStatus?.faceDetectionProcessed == true) ...[
            _buildOptimizedPlaybackInfo(),
            const SizedBox(width: 8),
            
            // Force reprocessing button
            ElevatedButton.icon(
              onPressed: _reprocessVideo,
              icon: const Icon(Icons.refresh),
              label: const Text('Reprocess'),
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.orange[600],
              ),
            ),
          ] else ...[
            Text(
              'Video not yet processed for optimized playback',
              style: AppTextStyles.body2.copyWith(color: Colors.white70),
            ),
            const SizedBox(height: 8),
            
            ElevatedButton.icon(
              onPressed: _processForOptimizedPlayback,
              icon: const Icon(Icons.auto_awesome),
              label: const Text('Process for Optimization'),
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.green[600],
              ),
            ),
          ],
        ],
      ),
    ),
  );
}
```

### **3. New Workflow Management Screen**

#### **A. Workflow Dashboard Screen**

```dart
// lib/screens/workflow_dashboard_screen.dart

class WorkflowDashboardScreen extends ConsumerStatefulWidget {
  const WorkflowDashboardScreen({super.key});

  @override
  ConsumerState<WorkflowDashboardScreen> createState() => _WorkflowDashboardScreenState();
}

class _WorkflowDashboardScreenState extends ConsumerState<WorkflowDashboardScreen> {
  List<FaceDetectionSession> _activeSessions = [];
  List<ProcessingStatus> _processedVideos = [];
  Map<String, double> _performanceMetrics = {};
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Face Detection Workflows'),
        backgroundColor: Colors.grey[900],
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _refreshData,
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Performance overview
            _buildPerformanceOverview(),
            
            const SizedBox(height: 24),
            
            // Active sessions (Workflow 4)
            _buildActiveSessionsSection(),
            
            const SizedBox(height: 24),
            
            // Processed videos (Workflow 5)
            _buildProcessedVideosSection(),
            
            const SizedBox(height: 24),
            
            // Workflow settings
            _buildWorkflowSettings(),
          ],
        ),
      ),
    );
  }
  
  Widget _buildPerformanceOverview() {
    return Card(
      color: Colors.grey[850],
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Performance Overview',
              style: AppTextStyles.h5.copyWith(color: Colors.white),
            ),
            const SizedBox(height: 16),
            
            Row(
              children: [
                _buildMetricCard(
                  'CPU Savings',
                  '${_performanceMetrics['cpu_reduction'] ?? 0}%',
                  Icons.memory,
                  Colors.green,
                ),
                const SizedBox(width: 16),
                _buildMetricCard(
                  'Active Sessions',
                  '${_activeSessions.length}',
                  Icons.play_circle,
                  Colors.blue,
                ),
                const SizedBox(width: 16),
                _buildMetricCard(
                  'Processed Videos',
                  '${_processedVideos.length}',
                  Icons.check_circle,
                  Colors.orange,
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
```

### **4. Enhanced Video Player Widget**

#### **A. Smart Video Player with Workflow Integration**

```dart
// lib/widgets/smart_video_player_widget.dart

class SmartVideoPlayerWidget extends ConsumerStatefulWidget {
  final String mediaUuid;
  final ProcessingStatus? processingStatus;
  final Function(FaceDetectionSession?)? onSessionChange;
  
  const SmartVideoPlayerWidget({
    super.key,
    required this.mediaUuid,
    this.processingStatus,
    this.onSessionChange,
  });

  @override
  ConsumerState<SmartVideoPlayerWidget> createState() => _SmartVideoPlayerWidgetState();
}

class _SmartVideoPlayerWidgetState extends ConsumerState<SmartVideoPlayerWidget> {
  VideoPlayerController? _controller;
  PlaybackMode? _playbackMode;
  FaceDetectionSession? _currentSession;
  List<FaceDetection> _storedFaces = [];
  bool _showPerformanceOverlay = false;
  
  @override
  void initState() {
    super.initState();
    _initializeSmartPlayback();
  }
  
  Future<void> _initializeSmartPlayback() async {
    try {
      // Determine optimal playback mode
      final workflowClient = ref.read(workflowApiClientProvider);
      _playbackMode = await workflowClient.getOptimalPlaybackMode(widget.mediaUuid);
      
      if (_playbackMode?.mode == 'stored_data') {
        // Load stored face data for Workflow 5
        _storedFaces = await workflowClient.getStoredFaceData(
          mediaUuid: widget.mediaUuid,
        );
      }
      
      setState(() {});
      _initializeVideoPlayer();
    } catch (e) {
      debugPrint('Smart playback initialization error: $e');
      _initializeVideoPlayer(); // Fallback to regular playback
    }
  }
  
  void _initializeVideoPlayer() {
    final videoUrl = _getOptimalVideoUrl();
    
    _controller = VideoPlayerController.network(
      videoUrl,
      httpHeaders: _getAuthHeaders(),
    );
    
    _controller!.initialize().then((_) {
      setState(() {});
      _controller!.play();
    });
  }
  
  String _getOptimalVideoUrl() {
    switch (_playbackMode?.mode) {
      case 'stored_data':
        // Workflow 5: Use optimized streaming with stored face overlays
        return '/api/v1/stream/video/${widget.mediaUuid}?mode=optimized&stored_faces=true';
        
      case 'realtime_with_session':
        // Workflow 4: Use session-based face detection
        return '/api/v1/stream/video/${widget.mediaUuid}?session=${_currentSession?.sessionUuid}&face_detection=true';
        
      default:
        // Fallback: Regular streaming
        return '/api/v1/media/stream/${widget.mediaUuid}';
    }
  }
  
  @override
  Widget build(BuildContext context) {
    if (_controller == null || !_controller!.value.isInitialized) {
      return const Center(child: CircularProgressIndicator());
    }
    
    return Stack(
      children: [
        // Video player
        AspectRatio(
          aspectRatio: _controller!.value.aspectRatio,
          child: VideoPlayer(_controller!),
        ),
        
        // Face detection overlay (for stored data mode)
        if (_playbackMode?.mode == 'stored_data')
          _buildStoredFaceOverlay(),
        
        // Performance overlay
        if (_showPerformanceOverlay)
          _buildPerformanceOverlay(),
        
        // Video controls
        _buildVideoControls(),
      ],
    );
  }
}
```

### **5. User Interface Enhancements**

#### **A. Settings Screen Integration**

```dart
// Add to existing settings screen:

class WorkflowSettingsSection extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Face Detection Workflows',
          style: AppTextStyles.h6.copyWith(color: Colors.white),
        ),
        const SizedBox(height: 16),
        
        // Workflow 4 Settings
        SwitchListTile(
          title: const Text('Enable Session-Based Detection'),
          subtitle: const Text('Workflow 4: Improved session management'),
          value: ref.watch(workflow4EnabledProvider),
          onChanged: (value) => 
            ref.read(workflow4EnabledProvider.notifier).state = value,
        ),
        
        // Workflow 5 Settings
        SwitchListTile(
          title: const Text('Enable Optimized Playback'),
          subtitle: const Text('Workflow 5: 90% CPU reduction for processed videos'),
          value: ref.watch(workflow5EnabledProvider),
          onChanged: (value) => 
            ref.read(workflow5EnabledProvider.notifier).state = value,
        ),
        
        // Auto-processing setting
        SwitchListTile(
          title: const Text('Auto-Process Videos'),
          subtitle: const Text('Automatically process videos for optimized playback'),
          value: ref.watch(autoProcessVideosProvider),
          onChanged: (value) => 
            ref.read(autoProcessVideosProvider.notifier).state = value,
        ),
        
        // Performance monitoring
        SwitchListTile(
          title: const Text('Show Performance Metrics'),
          subtitle: const Text('Display CPU usage and optimization indicators'),
          value: ref.watch(showPerformanceMetricsProvider),
          onChanged: (value) => 
            ref.read(showPerformanceMetricsProvider.notifier).state = value,
        ),
      ],
    );
  }
}
```

#### **B. Navigation Integration**

```dart
// Add to existing app router:

GoRoute(
  path: '/workflows',
  name: 'workflows',
  builder: (context, state) => const WorkflowDashboardScreen(),
),

GoRoute(
  path: '/media/:mediaId/workflows',
  name: 'media-workflows',
  builder: (context, state) {
    final mediaId = state.pathParameters['mediaId']!;
    return MediaWorkflowScreen(mediaId: mediaId);
  },
),
```

---

## 🎯 Implementation Priority

### **Phase 1: Core Integration (Week 1-2)**
1. ✅ **Data Models**: Add session and processing status models
2. ✅ **API Client**: Extend with Workflow 4 & 5 endpoints
3. ✅ **Basic UI**: Add processing status indicators to media preview

### **Phase 2: Enhanced UX (Week 3-4)**
1. 🔧 **Smart Playback**: Implement intelligent mode selection
2. 🔧 **Session Management**: Add session creation/management UI
3. 🔧 **Performance Indicators**: Show CPU savings and optimization status

### **Phase 3: Advanced Features (Week 5-6)**
1. 🚀 **Workflow Dashboard**: Complete management interface
2. 🚀 **Settings Integration**: User preferences and controls
3. 🚀 **Performance Monitoring**: Real-time metrics and analytics

---

## 💡 User Experience Benefits

### **For Workflow 4 - Session-Based Detection**
- **Visual Session Management**: See active face detection sessions
- **Session Controls**: Start, stop, monitor session progress
- **Session History**: View past sessions and their results
- **Quality Indicators**: Show detection quality and confidence scores

### **For Workflow 5 - Optimized Playback**
- **Smart Mode Indicators**: Show when optimized playback is active
- **Performance Benefits**: Display CPU savings (90% reduction)
- **Processing Status**: Clear indicators for processed vs unprocessed videos
- **Auto-Optimization**: Option to automatically process videos for optimization

### **Overall Experience**
- **Seamless Integration**: Workflows work transparently with existing UI
- **Performance Awareness**: Users can see and understand performance benefits
- **Control & Visibility**: Full control over workflow features with clear status
- **Progressive Enhancement**: Advanced features available but not intrusive

---

## 🔧 Technical Notes

### **State Management**
- Use Riverpod providers for workflow state management
- Cache processing status and session data for better UX
- Implement optimistic updates for better responsiveness

### **Performance Considerations**
- Lazy load workflow data only when needed
- Use efficient state updates to minimize rebuilds
- Cache face detection data for smooth playback

### **Error Handling**
- Graceful fallback to basic face detection when workflows unavailable
- Clear error messages for workflow-specific issues
- Retry mechanisms for network-dependent workflow features

---

## 🎉 Summary

This integration plan provides a **comprehensive but non-intrusive** way to expose Workflows 4 & 5 functionality to users while maintaining the existing user experience. The approach focuses on:

1. **Progressive Enhancement**: Advanced features available but don't interfere with basic functionality
2. **Clear Benefits**: Users can see and understand the performance improvements
3. **User Control**: Full control over workflow features with sensible defaults
4. **Visual Feedback**: Clear indicators for processing status and performance benefits

The integration can be implemented **incrementally**, starting with basic status indicators and building up to the full workflow management interface.