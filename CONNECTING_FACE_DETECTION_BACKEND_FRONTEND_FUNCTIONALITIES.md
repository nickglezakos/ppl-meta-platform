# 🔗 Connecting Face Detection Backend-Frontend Functionalities

**Document**: Integration Guide for Face Detection Workflows 4 & 5  
**Date**: September 17, 2025  
**PPL Meta Version**: 2.17.2+  
**Repository**: nickglezakos/ppl-meta-platform  
**Branch**: main  
**Status**: Backend Developed ✅ | Frontend Integration Needed 🔄

## 📋 **OVERVIEW**

This document provides a comprehensive guide for connecting the already-developed backend functionalities of **Face Detection Workflows 4 & 5** with the frontend interfaces. The backend infrastructure is complete and operational - this integration focuses on exposing these capabilities through the user interface.

## 🎯 **INTEGRATION OBJECTIVES**

### **Primary Goals**
- ✅ **Connect Workflow Status Checking**: Integrate processing status APIs with frontend
- ✅ **Implement Workflow Controls**: Connect session management to UI controls
- ✅ **Enable Smart Mode Selection**: Frontend detection of processed vs unprocessed videos
- ✅ **Expose Optimization Controls**: Connect video optimization features to user interface
- ✅ **Session Management Integration**: Full session lifecycle control from frontend

### **Backend Status Verification**
- **Workflow 4**: Session-based face detection ✅ **IMPLEMENTED**
- **Workflow 5**: Optimized playback for processed videos ✅ **IMPLEMENTED**
- **Processing Status APIs**: Video processing state management ✅ **IMPLEMENTED**
- **Session Management**: Complete session lifecycle ✅ **IMPLEMENTED**
- **Face Storage**: Frame-indexed face detection storage ✅ **IMPLEMENTED**

---

## 🔍 **PHASE 1: Workflow Status & Controls Integration**

### **1.1 Backend Endpoint Analysis**

#### **Processing Status Endpoints** (Already Implemented)
```http
# Check if video has been processed for face detection
GET /api/v1/processing-status/{media_uuid}
Response: {
  "media_uuid": "string",
  "face_detection_processed": boolean,
  "face_detection_session_uuid": "string",
  "processing_completed_at": "timestamp",
  "total_frames_processed": integer,
  "total_faces_detected": integer,
  "processing_method": "string",
  "processing_quality_score": float,
  "status": "processed|unprocessed|processing"
}

# Mark video as fully processed
POST /api/v1/processing-status/{media_uuid}/complete
Request: {
  "session_uuid": "string",
  "total_frames": integer,
  "total_faces": integer,
  "method": "string"
}

# Get processing metadata
GET /api/v1/processing-status/{media_uuid}/metadata
Response: {
  "frame_analysis_metadata": object,
  "processing_quality_score": float,
  "processing_duration": integer,
  "method_used": "string"
}

# Reset processing status (for reprocessing)
DELETE /api/v1/processing-status/{media_uuid}/reset
Response: {
  "status": "reset_complete",
  "media_uuid": "string"
}
```

#### **Session Management Endpoints** (Already Implemented)
```http
# Create new face detection session
POST /api/v1/sessions/face-detection
Request: {
  "session_uuid": "string",
  "media_uuid": "string",
  "camera_device_uuid": "string",
  "session_type": "streaming|bulk_processing",
  "metadata": object
}

# Get session details and statistics
GET /api/v1/sessions/{session_uuid}
Response: {
  "session_uuid": "string",
  "media_uuid": "string",
  "session_type": "string",
  "started_at": "timestamp",
  "ended_at": "timestamp",
  "total_faces_detected": integer,
  "processing_status": "active|completed|failed",
  "metadata": object
}

# Close session and finalize statistics
POST /api/v1/sessions/{session_uuid}/close
Request: {
  "total_faces": integer,
  "processing_summary": object
}

# Delete session and all associated data
DELETE /api/v1/sessions/{session_uuid}
Response: {
  "status": "deleted",
  "faces_removed": integer
}
```

### **1.2 Frontend Integration Requirements**

#### **A. Workflow Status Display Component**
**Location**: `lib/widgets/workflow_status_indicator.dart`

**Requirements**:
- Display current processing status for any media item
- Visual indicators for processed/unprocessed/processing states
- Show processing statistics (faces detected, processing time, etc.)
- Update in real-time during processing

**Component Structure**:
```dart
class WorkflowStatusIndicator extends StatefulWidget {
  final String mediaUuid;
  final bool showDetailedStats;
  final VoidCallback? onStatusChange;
  
  const WorkflowStatusIndicator({
    Key? key,
    required this.mediaUuid,
    this.showDetailedStats = false,
    this.onStatusChange,
  }) : super(key: key);
}

class _WorkflowStatusIndicatorState extends State<WorkflowStatusIndicator> {
  ProcessingStatus? _status;
  Timer? _statusUpdateTimer;
  
  @override
  void initState() {
    super.initState();
    _loadProcessingStatus();
    _startStatusMonitoring();
  }
  
  Future<void> _loadProcessingStatus() async {
    // Call GET /api/v1/processing-status/{media_uuid}
    final status = await WorkflowApiClient.getProcessingStatus(widget.mediaUuid);
    setState(() {
      _status = status;
    });
  }
  
  void _startStatusMonitoring() {
    _statusUpdateTimer = Timer.periodic(Duration(seconds: 5), (timer) {
      if (_status?.status == 'processing') {
        _loadProcessingStatus();
      }
    });
  }
  
  @override
  Widget build(BuildContext context) {
    if (_status == null) {
      return CircularProgressIndicator();
    }
    
    return Container(
      child: Column(
        children: [
          _buildStatusIcon(),
          _buildStatusText(),
          if (widget.showDetailedStats) _buildDetailedStats(),
        ],
      ),
    );
  }
  
  Widget _buildStatusIcon() {
    switch (_status!.status) {
      case 'processed':
        return Icon(Icons.check_circle, color: Colors.green, size: 24);
      case 'processing':
        return SizedBox(
          width: 24,
          height: 24,
          child: CircularProgressIndicator(strokeWidth: 2),
        );
      case 'unprocessed':
        return Icon(Icons.schedule, color: Colors.orange, size: 24);
      default:
        return Icon(Icons.help_outline, color: Colors.grey, size: 24);
    }
  }
  
  Widget _buildStatusText() {
    switch (_status!.status) {
      case 'processed':
        return Text(
          '${_status!.totalFacesDetected} faces detected',
          style: TextStyle(fontSize: 12, color: Colors.green),
        );
      case 'processing':
        return Text(
          'Processing...',
          style: TextStyle(fontSize: 12, color: Colors.blue),
        );
      case 'unprocessed':
        return Text(
          'Not processed',
          style: TextStyle(fontSize: 12, color: Colors.orange),
        );
      default:
        return Text(
          'Unknown status',
          style: TextStyle(fontSize: 12, color: Colors.grey),
        );
    }
  }
  
  Widget _buildDetailedStats() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (_status!.totalFramesProcessed != null)
          Text('Frames: ${_status!.totalFramesProcessed}'),
        if (_status!.processingMethod != null)
          Text('Method: ${_status!.processingMethod}'),
        if (_status!.processingQualityScore != null)
          Text('Quality: ${(_status!.processingQualityScore! * 100).toStringAsFixed(1)}%'),
        if (_status!.processingCompletedAt != null)
          Text('Completed: ${_formatTimestamp(_status!.processingCompletedAt!)}'),
      ],
    );
  }
  
  String _formatTimestamp(DateTime timestamp) {
    // Format timestamp for display
    return DateFormat('MMM dd, yyyy HH:mm').format(timestamp);
  }
}
```

#### **B. Workflow Controls Popup Component**
**Location**: `lib/widgets/workflow_controls_popup.dart`

**Requirements**:
- Start/stop face detection sessions
- Trigger video processing/optimization
- Display session management controls
- Show processing progress and statistics

**Component Structure**:
```dart
class WorkflowControlsPopup extends StatefulWidget {
  final String mediaUuid;
  final ProcessingStatus? currentStatus;
  final VoidCallback? onWorkflowStarted;
  final VoidCallback? onWorkflowCompleted;
  
  const WorkflowControlsPopup({
    Key? key,
    required this.mediaUuid,
    this.currentStatus,
    this.onWorkflowStarted,
    this.onWorkflowCompleted,
  }) : super(key: key);
}

class _WorkflowControlsPopupState extends State<WorkflowControlsPopup> {
  SessionDetails? _activeSession;
  bool _isProcessing = false;
  String? _processingError;
  
  @override
  void initState() {
    super.initState();
    _checkActiveSession();
  }
  
  Future<void> _checkActiveSession() async {
    // Check if there's an active session for this media
    try {
      final sessions = await WorkflowApiClient.getActiveSessions(widget.mediaUuid);
      if (sessions.isNotEmpty) {
        setState(() {
          _activeSession = sessions.first;
        });
      }
    } catch (e) {
      // No active sessions or error
    }
  }
  
  @override
  Widget build(BuildContext context) {
    return Dialog(
      child: Container(
        width: 400,
        padding: EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildHeader(),
            SizedBox(height: 16),
            _buildCurrentStatus(),
            SizedBox(height: 16),
            _buildWorkflowControls(),
            if (_activeSession != null) ...[
              SizedBox(height: 16),
              _buildSessionDetails(),
            ],
            if (_processingError != null) ...[
              SizedBox(height: 16),
              _buildErrorDisplay(),
            ],
            SizedBox(height: 24),
            _buildActionButtons(),
          ],
        ),
      ),
    );
  }
  
  Widget _buildHeader() {
    return Row(
      children: [
        Icon(Icons.face, size: 28, color: Theme.of(context).primaryColor),
        SizedBox(width: 12),
        Text(
          'Face Detection Workflow',
          style: Theme.of(context).textTheme.headlineSmall,
        ),
        Spacer(),
        IconButton(
          onPressed: () => Navigator.of(context).pop(),
          icon: Icon(Icons.close),
        ),
      ],
    );
  }
  
  Widget _buildCurrentStatus() {
    return Container(
      padding: EdgeInsets.all(16),
      decoration: BoxDecoration(
        border: Border.all(color: Colors.grey.shade300),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Current Status',
            style: TextStyle(fontWeight: FontWeight.bold),
          ),
          SizedBox(height: 8),
          WorkflowStatusIndicator(
            mediaUuid: widget.mediaUuid,
            showDetailedStats: true,
          ),
        ],
      ),
    );
  }
  
  Widget _buildWorkflowControls() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Available Actions',
          style: TextStyle(fontWeight: FontWeight.bold),
        ),
        SizedBox(height: 12),
        
        // Session Controls
        if (_activeSession == null && !_isProcessing)
          _buildActionTile(
            icon: Icons.play_arrow,
            title: 'Start Face Detection Session',
            subtitle: 'Begin real-time face detection processing',
            onTap: _startFaceDetectionSession,
          ),
        
        if (_activeSession != null && _activeSession!.processingStatus == 'active')
          _buildActionTile(
            icon: Icons.stop,
            title: 'Stop Current Session',
            subtitle: 'End the active face detection session',
            onTap: _stopFaceDetectionSession,
            isDestructive: true,
          ),
        
        // Processing Controls
        if (widget.currentStatus?.status != 'processed' && _activeSession == null)
          _buildActionTile(
            icon: Icons.auto_fix_high,
            title: 'Process Video for Optimization',
            subtitle: 'Run complete face detection and optimization',
            onTap: _processVideoForOptimization,
          ),
        
        if (widget.currentStatus?.status == 'processed')
          _buildActionTile(
            icon: Icons.refresh,
            title: 'Reprocess Video',
            subtitle: 'Clear existing data and reprocess',
            onTap: _reprocessVideo,
            isDestructive: true,
          ),
      ],
    );
  }
  
  Widget _buildActionTile({
    required IconData icon,
    required String title,
    required String subtitle,
    required VoidCallback onTap,
    bool isDestructive = false,
  }) {
    return Card(
      child: ListTile(
        leading: Icon(
          icon,
          color: isDestructive ? Colors.red : Theme.of(context).primaryColor,
        ),
        title: Text(title),
        subtitle: Text(subtitle),
        trailing: Icon(Icons.arrow_forward_ios, size: 16),
        onTap: onTap,
      ),
    );
  }
  
  Widget _buildSessionDetails() {
    return Container(
      padding: EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.blue.shade50,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Active Session Details',
            style: TextStyle(fontWeight: FontWeight.bold, color: Colors.blue.shade800),
          ),
          SizedBox(height: 8),
          _buildSessionDetailRow('Session ID', _activeSession!.sessionUuid.substring(0, 8) + '...'),
          _buildSessionDetailRow('Started', _formatTimestamp(_activeSession!.startedAt)),
          _buildSessionDetailRow('Faces Detected', _activeSession!.totalFacesDetected.toString()),
          _buildSessionDetailRow('Status', _activeSession!.processingStatus.toUpperCase()),
        ],
      ),
    );
  }
  
  Widget _buildSessionDetailRow(String label, String value) {
    return Padding(
      padding: EdgeInsets.symmetric(vertical: 2),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: TextStyle(fontSize: 12)),
          Text(value, style: TextStyle(fontSize: 12, fontWeight: FontWeight.w500)),
        ],
      ),
    );
  }
  
  Widget _buildErrorDisplay() {
    return Container(
      padding: EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.red.shade50,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.red.shade200),
      ),
      child: Row(
        children: [
          Icon(Icons.error, color: Colors.red),
          SizedBox(width: 12),
          Expanded(
            child: Text(
              _processingError!,
              style: TextStyle(color: Colors.red.shade800),
            ),
          ),
        ],
      ),
    );
  }
  
  Widget _buildActionButtons() {
    return Row(
      mainAxisAlignment: MainAxisAlignment.end,
      children: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: Text('Close'),
        ),
        if (_isProcessing) ...[
          SizedBox(width: 16),
          ElevatedButton.icon(
            onPressed: null,
            icon: SizedBox(
              width: 16,
              height: 16,
              child: CircularProgressIndicator(strokeWidth: 2),
            ),
            label: Text('Processing...'),
          ),
        ],
      ],
    );
  }
  
  // Action Methods
  Future<void> _startFaceDetectionSession() async {
    setState(() {
      _isProcessing = true;
      _processingError = null;
    });
    
    try {
      final sessionUuid = uuid.v4();
      await WorkflowApiClient.createFaceDetectionSession(
        sessionUuid: sessionUuid,
        mediaUuid: widget.mediaUuid,
        sessionType: 'streaming',
      );
      
      await _checkActiveSession();
      widget.onWorkflowStarted?.call();
      
      setState(() {
        _isProcessing = false;
      });
    } catch (e) {
      setState(() {
        _isProcessing = false;
        _processingError = 'Failed to start session: ${e.toString()}';
      });
    }
  }
  
  Future<void> _stopFaceDetectionSession() async {
    if (_activeSession == null) return;
    
    setState(() {
      _isProcessing = true;
      _processingError = null;
    });
    
    try {
      await WorkflowApiClient.closeFaceDetectionSession(
        sessionUuid: _activeSession!.sessionUuid,
        totalFaces: _activeSession!.totalFacesDetected,
      );
      
      setState(() {
        _activeSession = null;
        _isProcessing = false;
      });
      
      widget.onWorkflowCompleted?.call();
    } catch (e) {
      setState(() {
        _isProcessing = false;
        _processingError = 'Failed to stop session: ${e.toString()}';
      });
    }
  }
  
  Future<void> _processVideoForOptimization() async {
    setState(() {
      _isProcessing = true;
      _processingError = null;
    });
    
    try {
      await WorkflowApiClient.processVideoForOptimization(
        mediaUuid: widget.mediaUuid,
        detectionMethods: ['opencv', 'dlib'],  // As per requirement
        confidenceThreshold: 0.5,
        enableCpuOptimization: true,
      );
      
      widget.onWorkflowStarted?.call();
      
      setState(() {
        _isProcessing = false;
      });
    } catch (e) {
      setState(() {
        _isProcessing = false;
        _processingError = 'Failed to start processing: ${e.toString()}';
      });
    }
  }
  
  Future<void> _reprocessVideo() async {
    // Confirm with user first
    final confirm = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Confirm Reprocessing'),
        content: Text('This will delete all existing face detection data and reprocess the video. Continue?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: Text('Reprocess'),
          ),
        ],
      ),
    );
    
    if (confirm != true) return;
    
    setState(() {
      _isProcessing = true;
      _processingError = null;
    });
    
    try {
      // Reset processing status
      await WorkflowApiClient.resetProcessingStatus(widget.mediaUuid);
      
      // Start new processing
      await _processVideoForOptimization();
      
    } catch (e) {
      setState(() {
        _isProcessing = false;
        _processingError = 'Failed to reprocess video: ${e.toString()}';
      });
    }
  }
  
  String _formatTimestamp(DateTime timestamp) {
    return DateFormat('MMM dd, HH:mm:ss').format(timestamp);
  }
}
```

### **1.3 Backend API Client Extension**

#### **Extended WorkflowApiClient** (Location: `lib/services/workflow_api_client.dart`)

```dart
class WorkflowApiClient {
  static const String baseUrl = 'http://localhost:8003'; // Vision Service
  
  // Processing Status Methods
  static Future<ProcessingStatus> getProcessingStatus(String mediaUuid) async {
    final response = await http.get(
      Uri.parse('$baseUrl/api/v1/processing-status/$mediaUuid'),
      headers: {'Content-Type': 'application/json'},
    );
    
    if (response.statusCode == 200) {
      return ProcessingStatus.fromJson(json.decode(response.body));
    } else {
      throw Exception('Failed to get processing status: ${response.statusCode}');
    }
  }
  
  static Future<ProcessingMetadata> getProcessingMetadata(String mediaUuid) async {
    final response = await http.get(
      Uri.parse('$baseUrl/api/v1/processing-status/$mediaUuid/metadata'),
      headers: {'Content-Type': 'application/json'},
    );
    
    if (response.statusCode == 200) {
      return ProcessingMetadata.fromJson(json.decode(response.body));
    } else {
      throw Exception('Failed to get processing metadata: ${response.statusCode}');
    }
  }
  
  static Future<bool> resetProcessingStatus(String mediaUuid) async {
    final response = await http.delete(
      Uri.parse('$baseUrl/api/v1/processing-status/$mediaUuid/reset'),
      headers: {'Content-Type': 'application/json'},
    );
    
    return response.statusCode == 200;
  }
  
  // Session Management Methods
  static Future<SessionDetails> createFaceDetectionSession({
    required String sessionUuid,
    required String mediaUuid,
    String? cameraDeviceUuid,
    required String sessionType,
    Map<String, dynamic>? metadata,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/api/v1/sessions/face-detection'),
      headers: {'Content-Type': 'application/json'},
      body: json.encode({
        'session_uuid': sessionUuid,
        'media_uuid': mediaUuid,
        'camera_device_uuid': cameraDeviceUuid,
        'session_type': sessionType,
        'metadata': metadata ?? {},
      }),
    );
    
    if (response.statusCode == 200) {
      return SessionDetails.fromJson(json.decode(response.body));
    } else {
      throw Exception('Failed to create session: ${response.statusCode}');
    }
  }
  
  static Future<SessionDetails> getSessionDetails(String sessionUuid) async {
    final response = await http.get(
      Uri.parse('$baseUrl/api/v1/sessions/$sessionUuid'),
      headers: {'Content-Type': 'application/json'},
    );
    
    if (response.statusCode == 200) {
      return SessionDetails.fromJson(json.decode(response.body));
    } else {
      throw Exception('Failed to get session details: ${response.statusCode}');
    }
  }
  
  static Future<bool> closeFaceDetectionSession({
    required String sessionUuid,
    required int totalFaces,
    Map<String, dynamic>? processingSummary,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/api/v1/sessions/$sessionUuid/close'),
      headers: {'Content-Type': 'application/json'},
      body: json.encode({
        'total_faces': totalFaces,
        'processing_summary': processingSummary ?? {},
      }),
    );
    
    return response.statusCode == 200;
  }
  
  static Future<bool> deleteFaceDetectionSession(String sessionUuid) async {
    final response = await http.delete(
      Uri.parse('$baseUrl/api/v1/sessions/$sessionUuid'),
      headers: {'Content-Type': 'application/json'},
    );
    
    return response.statusCode == 200;
  }
  
  static Future<List<SessionDetails>> getActiveSessions(String mediaUuid) async {
    // This endpoint might need to be added to backend
    final response = await http.get(
      Uri.parse('$baseUrl/api/v1/sessions?media_uuid=$mediaUuid&status=active'),
      headers: {'Content-Type': 'application/json'},
    );
    
    if (response.statusCode == 200) {
      final List<dynamic> sessionsJson = json.decode(response.body);
      return sessionsJson.map((s) => SessionDetails.fromJson(s)).toList();
    } else {
      return [];
    }
  }
  
  // Video Processing Methods (Existing - keeping for reference)
  static Future<bool> processVideoForOptimization({
    required String mediaUuid,
    required List<String> detectionMethods,
    required double confidenceThreshold,
    required bool enableCpuOptimization,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/api/v1/process-for-optimization'),
      headers: {'Content-Type': 'application/json'},
      body: json.encode({
        'media_uuid': mediaUuid,
        'detection_methods': detectionMethods,
        'confidence_threshold': confidenceThreshold,
        'enable_cpu_optimization': enableCpuOptimization,
      }),
    );
    
    return response.statusCode == 200;
  }
}
```

### **1.4 Data Models**

#### **Processing Status Models** (Location: `lib/models/workflow_models.dart`)

```dart
class ProcessingStatus {
  final String mediaUuid;
  final bool faceDetectionProcessed;
  final String? faceDetectionSessionUuid;
  final DateTime? processingCompletedAt;
  final int? totalFramesProcessed;
  final int? totalFacesDetected;
  final String? processingMethod;
  final double? processingQualityScore;
  final String status; // 'processed', 'unprocessed', 'processing'
  
  ProcessingStatus({
    required this.mediaUuid,
    required this.faceDetectionProcessed,
    this.faceDetectionSessionUuid,
    this.processingCompletedAt,
    this.totalFramesProcessed,
    this.totalFacesDetected,
    this.processingMethod,
    this.processingQualityScore,
    required this.status,
  });
  
  factory ProcessingStatus.fromJson(Map<String, dynamic> json) {
    return ProcessingStatus(
      mediaUuid: json['media_uuid'],
      faceDetectionProcessed: json['face_detection_processed'] ?? false,
      faceDetectionSessionUuid: json['face_detection_session_uuid'],
      processingCompletedAt: json['processing_completed_at'] != null
          ? DateTime.parse(json['processing_completed_at'])
          : null,
      totalFramesProcessed: json['total_frames_processed'],
      totalFacesDetected: json['total_faces_detected'],
      processingMethod: json['processing_method'],
      processingQualityScore: json['processing_quality_score']?.toDouble(),
      status: json['status'] ?? 'unprocessed',
    );
  }
}

class ProcessingMetadata {
  final Map<String, dynamic> frameAnalysisMetadata;
  final double? processingQualityScore;
  final int? processingDuration;
  final String? methodUsed;
  
  ProcessingMetadata({
    required this.frameAnalysisMetadata,
    this.processingQualityScore,
    this.processingDuration,
    this.methodUsed,
  });
  
  factory ProcessingMetadata.fromJson(Map<String, dynamic> json) {
    return ProcessingMetadata(
      frameAnalysisMetadata: json['frame_analysis_metadata'] ?? {},
      processingQualityScore: json['processing_quality_score']?.toDouble(),
      processingDuration: json['processing_duration'],
      methodUsed: json['method_used'],
    );
  }
}

class SessionDetails {
  final String sessionUuid;
  final String mediaUuid;
  final String? cameraDeviceUuid;
  final String sessionType;
  final DateTime startedAt;
  final DateTime? endedAt;
  final int totalFacesDetected;
  final String processingStatus; // 'active', 'completed', 'failed'
  final Map<String, dynamic> metadata;
  
  SessionDetails({
    required this.sessionUuid,
    required this.mediaUuid,
    this.cameraDeviceUuid,
    required this.sessionType,
    required this.startedAt,
    this.endedAt,
    required this.totalFacesDetected,
    required this.processingStatus,
    required this.metadata,
  });
  
  factory SessionDetails.fromJson(Map<String, dynamic> json) {
    return SessionDetails(
      sessionUuid: json['session_uuid'],
      mediaUuid: json['media_uuid'],
      cameraDeviceUuid: json['camera_device_uuid'],
      sessionType: json['session_type'],
      startedAt: DateTime.parse(json['started_at']),
      endedAt: json['ended_at'] != null ? DateTime.parse(json['ended_at']) : null,
      totalFacesDetected: json['total_faces_detected'] ?? 0,
      processingStatus: json['processing_status'],
      metadata: json['metadata'] ?? {},
    );
  }
}
```

### **1.5 Integration Points**

#### **A. Media Card Integration**
**Location**: `lib/screens/media_preview_screen.dart`

**Integration Requirements**:
1. **Add Workflow Status Indicator** to media cards
2. **Replace existing optimization dialog** with new WorkflowControlsPopup
3. **Update media card actions** based on processing status

**Implementation**:
```dart
// In media_preview_screen.dart, add to media card:
Widget _buildMediaCard(MediaItem media) {
  return Card(
    child: Column(
      children: [
        // Existing media preview content...
        
        // Add workflow status indicator
        Positioned(
          top: 8,
          right: 8,
          child: WorkflowStatusIndicator(
            mediaUuid: media.uuid,
            showDetailedStats: false,
          ),
        ),
        
        // Update action buttons
        _buildActionButtons(media),
      ],
    ),
  );
}

Widget _buildActionButtons(MediaItem media) {
  return Row(
    mainAxisAlignment: MainAxisAlignment.spaceEvenly,
    children: [
      // Existing buttons...
      
      // Replace optimization button with workflow controls
      IconButton(
        icon: Icon(Icons.face),
        onPressed: () => _showWorkflowControls(media),
        tooltip: 'Face Detection Workflow',
      ),
    ],
  );
}

void _showWorkflowControls(MediaItem media) {
  showDialog(
    context: context,
    builder: (context) => WorkflowControlsPopup(
      mediaUuid: media.uuid,
      onWorkflowStarted: () {
        // Refresh media status
        setState(() {});
      },
      onWorkflowCompleted: () {
        // Refresh media status
        setState(() {});
      },
    ),
  );
}
```

#### **B. Workflow Dashboard Integration**
**Location**: `lib/screens/workflow_dashboard_screen.dart`

**Integration Requirements**:
1. **Add processing status overview** to dashboard tabs
2. **Integrate session management** in Sessions tab
3. **Show optimized videos** in Optimized tab with status indicators

---

## 🔍 **BACKEND ENDPOINT VERIFICATION**

### **Endpoints to Verify/Implement**

#### **✅ Already Implemented** (Based on Workflow 4 & 5 documents)
- `GET /api/v1/processing-status/{media_uuid}`
- `POST /api/v1/processing-status/{media_uuid}/complete`
- `GET /api/v1/processing-status/{media_uuid}/metadata`
- `DELETE /api/v1/processing-status/{media_uuid}/reset`
- `POST /api/v1/sessions/face-detection`
- `GET /api/v1/sessions/{session_uuid}`
- `POST /api/v1/sessions/{session_uuid}/close`
- `DELETE /api/v1/sessions/{session_uuid}`

#### **🔄 May Need Implementation**
- `GET /api/v1/sessions?media_uuid={uuid}&status=active` - Get active sessions for media
- `GET /api/v1/sessions/media/{media_uuid}` - Get all sessions for a media item
- `GET /api/v1/workflow/health` - Workflow system health check

---

## 🎯 **IMPLEMENTATION CHECKLIST**

### **Phase 1 Tasks**
- [ ] Create `WorkflowStatusIndicator` widget
- [ ] Create `WorkflowControlsPopup` widget
- [ ] Extend `WorkflowApiClient` with session management methods
- [ ] Create workflow data models (`ProcessingStatus`, `SessionDetails`, etc.)
- [ ] Integrate status indicator into media cards
- [ ] Replace optimization dialog with workflow controls popup
- [ ] Test backend endpoint connectivity
- [ ] Verify session management functionality

### **Backend Verification Tasks**
- [ ] Test all processing status endpoints
- [ ] Test all session management endpoints
- [ ] Verify missing endpoint: `GET /api/v1/sessions?media_uuid={uuid}&status=active`
- [ ] Confirm video optimization endpoint functionality
- [ ] Test error handling and fallback mechanisms

### **Integration Testing**
- [ ] Test complete session creation → processing → completion flow
- [ ] Test status indicator real-time updates
- [ ] Test workflow controls popup functionality
- [ ] Test error handling and user feedback
- [ ] Test concurrent session management
- [ ] Verify processing status accuracy

---

## 📋 **NEXT STEPS**

1. **Immediate**: Verify backend endpoint availability and functionality
2. **Phase 1**: Implement workflow status and controls components
3. **Phase 2**: Integrate with media cards and workflow dashboard
4. **Phase 3**: Extend to advanced features (analytics, multi-session management)
5. **Phase 4**: Performance optimization and user experience enhancements

---

**Document Status**: Phase 1 - Workflow Status & Controls ✅ **READY FOR IMPLEMENTATION**  
**Next Phase**: Backend endpoint verification and frontend component development