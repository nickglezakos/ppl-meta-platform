import 'package:json_annotation/json_annotation.dart';

part 'workflow_widget_models.g.dart';

/// Widget-friendly status enumeration matching backend
enum WorkflowWidgetStatus {
  @JsonValue('not_started')
  notStarted,
  @JsonValue('in_progress')
  inProgress,
  @JsonValue('completed')
  completed,
  @JsonValue('error')
  error,
  @JsonValue('paused')
  paused,
}

/// Playback mode enumeration for processing optimization
enum PlaybackMode {
  @JsonValue('realtime_only')
  realtimeOnly,
  @JsonValue('cached_frames')
  cachedFrames,
  @JsonValue('hybrid_mode')
  hybridMode,
}

/// Processing progress information for widgets
@JsonSerializable()
class ProcessingProgress {
  @JsonKey(name: 'current_frame')
  final int currentFrame;
  
  @JsonKey(name: 'total_frames')
  final int totalFrames;
  
  final double percentage;
  
  @JsonKey(name: 'estimated_time_remaining')
  final int? estimatedTimeRemaining;

  const ProcessingProgress({
    required this.currentFrame,
    required this.totalFrames,
    required this.percentage,
    this.estimatedTimeRemaining,
  });

  factory ProcessingProgress.fromJson(Map<String, dynamic> json) =>
      _$ProcessingProgressFromJson(json);

  Map<String, dynamic> toJson() => _$ProcessingProgressToJson(this);

  /// Get formatted progress text
  String get progressText => '${currentFrame.toString().padLeft(4)} / ${totalFrames.toString().padLeft(4)}';

  /// Get formatted percentage text
  String get percentageText => '${percentage.toStringAsFixed(1)}%';

  /// Get estimated time remaining as formatted string
  String? get estimatedTimeText {
    if (estimatedTimeRemaining == null) return null;
    
    final seconds = estimatedTimeRemaining!;
    if (seconds < 60) {
      return '${seconds}s';
    } else if (seconds < 3600) {
      final minutes = seconds ~/ 60;
      return '${minutes}m ${seconds % 60}s';
    } else {
      final hours = seconds ~/ 3600;
      final minutes = (seconds % 3600) ~/ 60;
      return '${hours}h ${minutes}m';
    }
  }
}

/// Summary of session information for widgets
@JsonSerializable()
class SessionSummary {
  @JsonKey(name: 'session_uuid')
  final String sessionUuid;
  
  @JsonKey(name: 'session_type')
  final String sessionType;
  
  @JsonKey(name: 'started_at')
  final DateTime startedAt;
  
  @JsonKey(name: 'ended_at')
  final DateTime? endedAt;
  
  @JsonKey(name: 'total_faces_detected')
  final int totalFacesDetected;
  
  @JsonKey(name: 'processing_status')
  final String processingStatus;
  
  @JsonKey(name: 'duration_seconds')
  final double? durationSeconds;

  const SessionSummary({
    required this.sessionUuid,
    required this.sessionType,
    required this.startedAt,
    this.endedAt,
    required this.totalFacesDetected,
    required this.processingStatus,
    this.durationSeconds,
  });

  factory SessionSummary.fromJson(Map<String, dynamic> json) =>
      _$SessionSummaryFromJson(json);

  Map<String, dynamic> toJson() => _$SessionSummaryToJson(this);

  /// Check if session is currently active
  bool get isActive => processingStatus == 'active';

  /// Get formatted duration text
  String? get durationText {
    if (durationSeconds == null) return null;
    
    final seconds = durationSeconds!.round();
    if (seconds < 60) {
      return '${seconds}s';
    } else if (seconds < 3600) {
      final minutes = seconds ~/ 60;
      return '${minutes}m ${seconds % 60}s';
    } else {
      final hours = seconds ~/ 3600;
      final minutes = (seconds % 3600) ~/ 60;
      return '${hours}h ${minutes}m';
    }
  }

  /// Get display-friendly status text
  String get displayStatus {
    switch (processingStatus) {
      case 'active':
        return 'Processing';
      case 'completed':
        return 'Completed';
      case 'failed':
        return 'Failed';
      case 'cancelled':
        return 'Cancelled';
      default:
        return processingStatus;
    }
  }
}

/// Widget-optimized status response
@JsonSerializable()
class WidgetStatusResponse {
  @JsonKey(name: 'media_uuid')
  final String mediaUuid;
  
  final WorkflowWidgetStatus status;
  
  @JsonKey(name: 'face_detection_processed')
  final bool faceDetectionProcessed;
  
  @JsonKey(name: 'current_session')
  final SessionSummary? currentSession;
  
  @JsonKey(name: 'processing_progress')
  final ProcessingProgress? processingProgress;
  
  @JsonKey(name: 'total_faces_detected')
  final int totalFacesDetected;
  
  @JsonKey(name: 'total_frames_processed')
  final int totalFramesProcessed;
  
  @JsonKey(name: 'processing_method')
  final String? processingMethod;
  
  @JsonKey(name: 'optimal_playback_mode')
  final PlaybackMode optimalPlaybackMode;
  
  @JsonKey(name: 'cache_available')
  final bool cacheAvailable;
  
  @JsonKey(name: 'last_updated')
  final DateTime lastUpdated;
  
  @JsonKey(name: 'error_message')
  final String? errorMessage;

  const WidgetStatusResponse({
    required this.mediaUuid,
    required this.status,
    required this.faceDetectionProcessed,
    this.currentSession,
    this.processingProgress,
    required this.totalFacesDetected,
    required this.totalFramesProcessed,
    this.processingMethod,
    required this.optimalPlaybackMode,
    required this.cacheAvailable,
    required this.lastUpdated,
    this.errorMessage,
  });

  factory WidgetStatusResponse.fromJson(Map<String, dynamic> json) =>
      _$WidgetStatusResponseFromJson(json);

  Map<String, dynamic> toJson() => _$WidgetStatusResponseToJson(this);

  /// Get display-friendly status text
  String get displayStatus {
    switch (status) {
      case WorkflowWidgetStatus.notStarted:
        return 'Not Started';
      case WorkflowWidgetStatus.inProgress:
        return 'Processing';
      case WorkflowWidgetStatus.completed:
        return 'Completed';
      case WorkflowWidgetStatus.error:
        return 'Error';
      case WorkflowWidgetStatus.paused:
        return 'Paused';
    }
  }

  /// Check if processing is currently active
  bool get isProcessing => status == WorkflowWidgetStatus.inProgress;

  /// Check if processing completed successfully
  bool get isCompleted => status == WorkflowWidgetStatus.completed;

  /// Check if there's an error
  bool get hasError => status == WorkflowWidgetStatus.error;

  /// Get processing efficiency percentage
  double? get processingEfficiency {
    if (totalFramesProcessed == 0) return null;
    if (processingProgress?.totalFrames == null) return null;
    
    return (totalFramesProcessed / processingProgress!.totalFrames) * 100;
  }
}

/// Analytics data for workflow dashboard widgets
@JsonSerializable()
class WidgetAnalyticsResponse {
  @JsonKey(name: 'media_uuid')
  final String mediaUuid;
  
  @JsonKey(name: 'session_history')
  final List<SessionSummary> sessionHistory;
  
  @JsonKey(name: 'total_sessions')
  final int totalSessions;
  
  @JsonKey(name: 'average_processing_time')
  final double? averageProcessingTime;
  
  @JsonKey(name: 'total_faces_detected')
  final int totalFacesDetected;
  
  @JsonKey(name: 'quality_metrics')
  final Map<String, double> qualityMetrics;
  
  final List<String> recommendations;

  const WidgetAnalyticsResponse({
    required this.mediaUuid,
    required this.sessionHistory,
    required this.totalSessions,
    this.averageProcessingTime,
    required this.totalFacesDetected,
    required this.qualityMetrics,
    required this.recommendations,
  });

  factory WidgetAnalyticsResponse.fromJson(Map<String, dynamic> json) =>
      _$WidgetAnalyticsResponseFromJson(json);

  Map<String, dynamic> toJson() => _$WidgetAnalyticsResponseToJson(this);

  /// Get average confidence score
  double? get averageConfidence => qualityMetrics['average_confidence'];

  /// Get detection consistency score
  double? get detectionConsistency => qualityMetrics['detection_consistency'];

  /// Get processing efficiency score
  double? get processingEfficiency => qualityMetrics['processing_efficiency'];

  /// Get formatted average processing time
  String? get averageProcessingTimeText {
    if (averageProcessingTime == null) return null;
    
    final seconds = averageProcessingTime!.round();
    if (seconds < 60) {
      return '${seconds}s';
    } else if (seconds < 3600) {
      final minutes = seconds ~/ 60;
      return '${minutes}m ${seconds % 60}s';
    } else {
      final hours = seconds ~/ 3600;
      final minutes = (seconds % 3600) ~/ 60;
      return '${hours}h ${minutes}m';
    }
  }

  /// Get faces per session average
  double get facesPerSession {
    if (totalSessions == 0) return 0.0;
    return totalFacesDetected / totalSessions;
  }
}

/// System health status for workflow widgets
@JsonSerializable()
class SystemHealthResponse {
  @JsonKey(name: 'overall_status')
  final WorkflowWidgetStatus overallStatus;
  
  @JsonKey(name: 'active_sessions')
  final int activeSessions;
  
  @JsonKey(name: 'processing_queue_size')
  final int processingQueueSize;
  
  @JsonKey(name: 'service_health')
  final Map<String, bool> serviceHealth;
  
  final List<String> alerts;
  
  @JsonKey(name: 'last_check')
  final DateTime lastCheck;

  const SystemHealthResponse({
    required this.overallStatus,
    required this.activeSessions,
    required this.processingQueueSize,
    required this.serviceHealth,
    required this.alerts,
    required this.lastCheck,
  });

  factory SystemHealthResponse.fromJson(Map<String, dynamic> json) =>
      _$SystemHealthResponseFromJson(json);

  Map<String, dynamic> toJson() => _$SystemHealthResponseToJson(this);

  /// Check if system is healthy
  bool get isHealthy => overallStatus == WorkflowWidgetStatus.completed && alerts.isEmpty;

  /// Get count of healthy services
  int get healthyServicesCount => serviceHealth.values.where((health) => health).length;

  /// Get count of total services
  int get totalServicesCount => serviceHealth.length;

  /// Get service health percentage
  double get serviceHealthPercentage {
    if (totalServicesCount == 0) return 100.0;
    return (healthyServicesCount / totalServicesCount) * 100;
  }

  /// Get display-friendly overall status
  String get displayOverallStatus {
    switch (overallStatus) {
      case WorkflowWidgetStatus.completed:
        return 'Healthy';
      case WorkflowWidgetStatus.error:
        return 'Error';
      case WorkflowWidgetStatus.paused:
        return 'Warning';
      case WorkflowWidgetStatus.inProgress:
        return 'Processing';
      case WorkflowWidgetStatus.notStarted:
        return 'Starting';
    }
  }

  /// Get status color for UI
  String get statusColor {
    switch (overallStatus) {
      case WorkflowWidgetStatus.completed:
        return '#4CAF50'; // Green
      case WorkflowWidgetStatus.error:
        return '#F44336'; // Red
      case WorkflowWidgetStatus.paused:
        return '#FF9800'; // Orange
      case WorkflowWidgetStatus.inProgress:
        return '#2196F3'; // Blue
      case WorkflowWidgetStatus.notStarted:
        return '#9E9E9E'; // Grey
    }
  }
}