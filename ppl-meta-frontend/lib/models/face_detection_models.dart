import 'package:json_annotation/json_annotation.dart';

part 'face_detection_models.g.dart';

/// Face Detection Session model for Workflow 4
/// Represents a session-based face detection process for a media item
@JsonSerializable()
class FaceDetectionSession {
  /// Unique identifier for the session
  @JsonKey(name: 'session_uuid')
  final String sessionUuid;
  
  /// UUID of the media item being processed
  @JsonKey(name: 'media_uuid')
  final String mediaUuid;
  
  /// Session status: 'active', 'completed', 'failed', 'cancelled'
  final String status;
  
  /// When the session was created
  @JsonKey(name: 'created_at')
  final DateTime createdAt;
  
  /// When the session was completed (if applicable)
  @JsonKey(name: 'completed_at')
  final DateTime? completedAt;
  
  /// Total number of frames processed in this session
  @JsonKey(name: 'total_frames_processed')
  final int? totalFramesProcessed;
  
  /// Estimated total number of frames to be processed
  @JsonKey(name: 'estimated_total_frames')
  final int? estimatedTotalFrames;
  
  /// Total number of faces detected in this session
  @JsonKey(name: 'total_faces_detected')
  final int? totalFacesDetected;
  
  /// Confidence threshold used for detection
  @JsonKey(name: 'confidence_threshold')
  final double? confidenceThreshold;
  
  /// Detection methods used in this session
  @JsonKey(name: 'detection_methods')
  final List<String> detectionMethods;
  
  /// Session progress percentage (0.0 to 1.0)
  final double? progress;
  
  /// Error message if session failed
  @JsonKey(name: 'error_message')
  final String? errorMessage;

  const FaceDetectionSession({
    required this.sessionUuid,
    required this.mediaUuid,
    required this.status,
    required this.createdAt,
    this.completedAt,
    this.totalFramesProcessed,
    this.estimatedTotalFrames,
    this.totalFacesDetected,
    this.confidenceThreshold,
    this.detectionMethods = const [],
    this.progress,
    this.errorMessage,
  });

  factory FaceDetectionSession.fromJson(Map<String, dynamic> json) =>
      _$FaceDetectionSessionFromJson(json);

  Map<String, dynamic> toJson() => _$FaceDetectionSessionToJson(this);

  /// Check if the session is currently active
  bool get isActive => status == 'active';

  /// Check if the session completed successfully
  bool get isCompleted => status == 'completed';

  /// Check if the session failed
  bool get isFailed => status == 'failed';

  /// Get display-friendly status text
  String get displayStatus {
    switch (status) {
      case 'active':
        return 'Processing...';
      case 'completed':
        return 'Completed';
      case 'failed':
        return 'Failed';
      case 'cancelled':
        return 'Cancelled';
      default:
        return status;
    }
  }

  /// Get duration of the session
  Duration? get duration {
    if (completedAt != null) {
      return completedAt!.difference(createdAt);
    } else if (isActive) {
      return DateTime.now().difference(createdAt);
    }
    return null;
  }
}

/// Processing Status model for Workflow 5
/// Represents the processing status of a media item for optimized playback
@JsonSerializable()
class ProcessingStatus {
  /// UUID of the media item
  @JsonKey(name: 'media_uuid')
  final String mediaUuid;
  
  /// Processing status: 'not_started', 'processing', 'completed', 'error'
  @JsonKey(name: 'status')
  final String status;
  
  /// Whether face detection has been processed for this media
  @JsonKey(name: 'face_detection_processed')
  final bool faceDetectionProcessed;
  
  /// Current active session UUID (if processing)
  @JsonKey(name: 'current_session')
  final String? currentSession;
  
  /// Processing progress information
  @JsonKey(name: 'processing_progress')
  final Map<String, dynamic>? processingProgress;
  
  /// Total faces detected during processing
  @JsonKey(name: 'total_faces_detected')
  final int? totalFacesDetected;
  
  /// Total frames processed during the session
  @JsonKey(name: 'total_frames_processed')
  final int? totalFramesProcessed;
  
  /// Method used for processing
  @JsonKey(name: 'processing_method')
  final String? processingMethod;
  
  /// Optimal playback mode for this media
  @JsonKey(name: 'optimal_playback_mode')
  final String? optimalPlaybackMode;
  
  /// Whether cache is available for optimized playback
  @JsonKey(name: 'cache_available')
  final bool? cacheAvailable;
  
  /// When the status was last updated
  @JsonKey(name: 'last_updated')
  final DateTime? lastUpdated;
  
  /// Error message if processing failed
  @JsonKey(name: 'error_message')
  final String? errorMessage;

  const ProcessingStatus({
    required this.mediaUuid,
    required this.status,
    required this.faceDetectionProcessed,
    this.currentSession,
    this.processingProgress,
    this.totalFacesDetected,
    this.totalFramesProcessed,
    this.processingMethod,
    this.optimalPlaybackMode,
    this.cacheAvailable,
    this.lastUpdated,
    this.errorMessage,
  });

  factory ProcessingStatus.fromJson(Map<String, dynamic> json) =>
      _$ProcessingStatusFromJson(json);

  Map<String, dynamic> toJson() => _$ProcessingStatusToJson(this);

  /// Check if this media is ready for optimized playback
  bool get isOptimizedPlaybackReady => 
      faceDetectionProcessed && optimalPlaybackMode == 'optimized';

  /// Get display-friendly processing method name
  String get displayProcessingMethod {
    if (processingMethod == null) return 'Not Started';
    switch (processingMethod) {
      case 'workflow4':
        return 'Session-Based';
      case 'workflow5':
        return 'Optimized';
      case 'realtime':
        return 'Real-time';
      default:
        return processingMethod!;
    }
  }

  /// Get display-friendly status
  String get displayStatus {
    switch (status) {
      case 'not_started':
        return 'Not Started';
      case 'processing':
        return 'Processing';
      case 'completed':
        return 'Completed';
      case 'error':
        return 'Error';
      default:
        return status;
    }
  }

  /// Get processing efficiency (faces per frame if available)
  double? get processingEfficiency {
    if (totalFacesDetected != null && totalFramesProcessed != null && totalFramesProcessed! > 0) {
      return totalFacesDetected! / totalFramesProcessed!;
    }
    return null;
  }
}

/// Playback Mode model for smart video playback selection
/// Represents the optimal playback mode for a media item
@JsonSerializable()
class PlaybackMode {
  /// Playback mode: 'stored_data', 'realtime_with_session', 'realtime_only'
  final String mode;
  
  /// Human-readable description of this mode
  final String description;
  
  /// Whether this mode provides CPU optimization
  @JsonKey(name: 'cpu_optimized')
  final bool cpuOptimized;
  
  /// Expected CPU reduction percentage (0.0 to 1.0)
  @JsonKey(name: 'expected_cpu_reduction')
  final double? expectedCpuReduction;
  
  /// Whether this mode provides memory optimization
  @JsonKey(name: 'memory_optimized')
  final bool? memoryOptimized;
  
  /// Expected memory reduction percentage (0.0 to 1.0)
  @JsonKey(name: 'expected_memory_reduction')
  final double? expectedMemoryReduction;
  
  /// Recommended reason for using this mode
  @JsonKey(name: 'recommendation_reason')
  final String? recommendationReason;
  
  /// Performance score for this mode (0.0 to 1.0, higher is better)
  @JsonKey(name: 'performance_score')
  final double? performanceScore;

  const PlaybackMode({
    required this.mode,
    required this.description,
    required this.cpuOptimized,
    this.expectedCpuReduction,
    this.memoryOptimized,
    this.expectedMemoryReduction,
    this.recommendationReason,
    this.performanceScore,
  });

  factory PlaybackMode.fromJson(Map<String, dynamic> json) =>
      _$PlaybackModeFromJson(json);

  Map<String, dynamic> toJson() => _$PlaybackModeToJson(this);

  /// Get display-friendly mode name
  String get displayName {
    switch (mode) {
      case 'stored_data':
        return 'Optimized Playback';
      case 'realtime_with_session':
        return 'Session Playback';
      case 'realtime_only':
        return 'Real-time';
      default:
        return mode;
    }
  }

  /// Get mode icon name for UI
  String get iconName {
    switch (mode) {
      case 'stored_data':
        return 'flash_on'; // Lightning bolt for optimized
      case 'realtime_with_session':
        return 'play_circle'; // Play circle for session
      case 'realtime_only':
        return 'memory'; // Memory chip for real-time
      default:
        return 'help';
    }
  }

  /// Get performance benefit text for UI
  String get performanceBenefitText {
    if (expectedCpuReduction != null && expectedCpuReduction! > 0) {
      final percentage = (expectedCpuReduction! * 100).round();
      return '$percentage% CPU reduction';
    }
    return cpuOptimized ? 'CPU optimized' : 'Standard performance';
  }

  /// Create PlaybackMode from string mode
  factory PlaybackMode.fromString(String modeString) {
    switch (modeString) {
      case 'stored_data':
      case 'optimized':
        return const PlaybackMode(
          mode: 'stored_data',
          description: 'Use pre-processed face detection data for optimal performance',
          cpuOptimized: true,
          expectedCpuReduction: 0.7,
          memoryOptimized: true,
          expectedMemoryReduction: 0.5,
          recommendationReason: 'Face detection has been pre-processed and cached',
          performanceScore: 0.9,
        );
      case 'realtime_with_session':
        return const PlaybackMode(
          mode: 'realtime_with_session',
          description: 'Real-time processing with session context',
          cpuOptimized: false,
          memoryOptimized: false,
          recommendationReason: 'Session is active, processing in real-time',
          performanceScore: 0.6,
        );
      case 'realtime_only':
      default:
        return const PlaybackMode(
          mode: 'realtime_only',
          description: 'Real-time face detection processing',
          cpuOptimized: false,
          memoryOptimized: false,
          recommendationReason: 'No cached data available, processing in real-time',
          performanceScore: 0.3,
        );
    }
  }
}

/// Workflow Performance Metrics model
/// Represents real-time performance metrics for workflow operations
@JsonSerializable()
class WorkflowPerformanceMetrics {
  /// Current CPU usage reduction percentage (0.0 to 1.0)
  @JsonKey(name: 'cpu_usage_reduction')
  final double cpuUsageReduction;
  
  /// Current memory usage reduction percentage (0.0 to 1.0)
  @JsonKey(name: 'memory_usage_reduction')
  final double memoryUsageReduction;
  
  /// Number of currently active face detection sessions
  @JsonKey(name: 'active_sessions_count')
  final int activeSessionsCount;
  
  /// Total number of videos processed with workflows
  @JsonKey(name: 'processed_videos_count')
  final int processedVideosCount;
  
  /// When these metrics were last updated
  @JsonKey(name: 'last_updated')
  final DateTime lastUpdated;
  
  /// Average processing time per video (in seconds)
  @JsonKey(name: 'avg_processing_time_seconds')
  final double? avgProcessingTimeSeconds;
  
  /// Total faces detected across all processed videos
  @JsonKey(name: 'total_faces_detected')
  final int? totalFacesDetected;
  
  /// System CPU usage percentage (0.0 to 1.0)
  @JsonKey(name: 'system_cpu_usage')
  final double? systemCpuUsage;
  
  /// System memory usage percentage (0.0 to 1.0)
  @JsonKey(name: 'system_memory_usage')
  final double? systemMemoryUsage;
  
  /// Workflow processing throughput (videos per hour)
  @JsonKey(name: 'processing_throughput')
  final double? processingThroughput;

  const WorkflowPerformanceMetrics({
    required this.cpuUsageReduction,
    required this.memoryUsageReduction,
    required this.activeSessionsCount,
    required this.processedVideosCount,
    required this.lastUpdated,
    this.avgProcessingTimeSeconds,
    this.totalFacesDetected,
    this.systemCpuUsage,
    this.systemMemoryUsage,
    this.processingThroughput,
  });

  factory WorkflowPerformanceMetrics.fromJson(Map<String, dynamic> json) =>
      _$WorkflowPerformanceMetricsFromJson(json);

  Map<String, dynamic> toJson() => _$WorkflowPerformanceMetricsToJson(this);

  /// Get CPU savings as percentage string
  String get cpuSavingsText {
    final percentage = (cpuUsageReduction * 100).round();
    return '$percentage%';
  }

  /// Get memory savings as percentage string
  String get memorySavingsText {
    final percentage = (memoryUsageReduction * 100).round();
    return '$percentage%';
  }

  /// Check if metrics show significant performance improvement
  bool get hasSignificantImprovement =>
      cpuUsageReduction > 0.1 || memoryUsageReduction > 0.1; // 10% threshold

  /// Get overall performance score (0.0 to 1.0)
  double get overallPerformanceScore {
    return (cpuUsageReduction + memoryUsageReduction) / 2;
  }

  /// Get system health status based on resource usage
  String get systemHealthStatus {
    final cpuHealth = systemCpuUsage ?? 0.0;
    final memoryHealth = systemMemoryUsage ?? 0.0;
    
    if (cpuHealth > 0.9 || memoryHealth > 0.9) {
      return 'critical';
    } else if (cpuHealth > 0.7 || memoryHealth > 0.7) {
      return 'warning';
    } else {
      return 'healthy';
    }
  }

  /// Check if metrics are recent (updated within last 5 minutes)
  bool get isRecent {
    final now = DateTime.now();
    final difference = now.difference(lastUpdated);
    return difference.inMinutes <= 5;
  }
}

/// Session Creation Request model
/// Used when creating a new face detection session
@JsonSerializable()
class SessionCreationRequest {
  /// UUID of the media item to process
  @JsonKey(name: 'media_uuid')
  final String mediaUuid;
  
  /// Confidence threshold for face detection (0.0 to 1.0)
  @JsonKey(name: 'confidence_threshold')
  final double? confidenceThreshold;
  
  /// Detection methods to use
  @JsonKey(name: 'detection_methods')
  final List<String>? detectionMethods;
  
  /// Processing priority: 'low', 'normal', 'high'
  final String? priority;
  
  /// Whether to enable real-time progress updates
  @JsonKey(name: 'enable_progress_updates')
  final bool? enableProgressUpdates;

  const SessionCreationRequest({
    required this.mediaUuid,
    this.confidenceThreshold,
    this.detectionMethods,
    this.priority,
    this.enableProgressUpdates,
  });

  factory SessionCreationRequest.fromJson(Map<String, dynamic> json) =>
      _$SessionCreationRequestFromJson(json);

  Map<String, dynamic> toJson() => _$SessionCreationRequestToJson(this);
}

/// Session Statistics model
/// Real-time statistics for an active session
@JsonSerializable()
class SessionStatistics {
  /// Session UUID
  @JsonKey(name: 'session_uuid')
  final String sessionUuid;
  
  /// Current processing progress (0.0 to 1.0)
  final double progress;
  
  /// Frames processed per second
  @JsonKey(name: 'frames_per_second')
  final double? framesPerSecond;
  
  /// Estimated time remaining in seconds
  @JsonKey(name: 'estimated_time_remaining_seconds')
  final double? estimatedTimeRemainingSeconds;
  
  /// Current frame being processed
  @JsonKey(name: 'current_frame')
  final int? currentFrame;
  
  /// Total frames to process
  @JsonKey(name: 'total_frames')
  final int? totalFrames;
  
  /// Faces detected so far in current session
  @JsonKey(name: 'faces_detected_current_session')
  final int? facesDetectedCurrentSession;

  const SessionStatistics({
    required this.sessionUuid,
    required this.progress,
    this.framesPerSecond,
    this.estimatedTimeRemainingSeconds,
    this.currentFrame,
    this.totalFrames,
    this.facesDetectedCurrentSession,
  });

  factory SessionStatistics.fromJson(Map<String, dynamic> json) =>
      _$SessionStatisticsFromJson(json);

  Map<String, dynamic> toJson() => _$SessionStatisticsToJson(this);

  /// Get progress as percentage string
  String get progressText {
    final percentage = (progress * 100).round();
    return '$percentage%';
  }

  /// Get estimated time remaining as human-readable string
  String? get estimatedTimeRemainingText {
    if (estimatedTimeRemainingSeconds == null) return null;
    
    final seconds = estimatedTimeRemainingSeconds!.round();
    if (seconds < 60) {
      return '${seconds}s';
    } else if (seconds < 3600) {
      final minutes = (seconds / 60).round();
      return '${minutes}m';
    } else {
      final hours = (seconds / 3600).round();
      return '${hours}h';
    }
  }

  /// Get frame progress text
  String? get frameProgressText {
    if (currentFrame != null && totalFrames != null) {
      return '$currentFrame / $totalFrames frames';
    }
    return null;
  }
}