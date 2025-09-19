// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'face_detection_models.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

FaceDetectionSession _$FaceDetectionSessionFromJson(Map<String, dynamic> json) =>
    FaceDetectionSession(
      sessionUuid: json['session_uuid'] as String,
      mediaUuid: json['media_uuid'] as String,
      status: json['status'] as String,
      createdAt: DateTime.parse(json['created_at'] as String),
      completedAt: json['completed_at'] == null
          ? null
          : DateTime.parse(json['completed_at'] as String),
      totalFramesProcessed: (json['total_frames_processed'] as num?)?.toInt(),
      estimatedTotalFrames: (json['estimated_total_frames'] as num?)?.toInt(),
      totalFacesDetected: (json['total_faces_detected'] as num?)?.toInt(),
      confidenceThreshold: (json['confidence_threshold'] as num?)?.toDouble(),
      detectionMethods: (json['detection_methods'] as List<dynamic>?)?.map((e) => e as String).toList() ?? const [],
      progress: (json['progress'] as num?)?.toDouble(),
      errorMessage: json['error_message'] as String?,
    );

Map<String, dynamic> _$FaceDetectionSessionToJson(FaceDetectionSession instance) =>
    <String, dynamic>{
      'session_uuid': instance.sessionUuid,
      'media_uuid': instance.mediaUuid,
      'status': instance.status,
      'created_at': instance.createdAt.toIso8601String(),
      'completed_at': instance.completedAt?.toIso8601String(),
      'total_frames_processed': instance.totalFramesProcessed,
      'estimated_total_frames': instance.estimatedTotalFrames,
      'total_faces_detected': instance.totalFacesDetected,
      'confidence_threshold': instance.confidenceThreshold,
      'detection_methods': instance.detectionMethods,
      'progress': instance.progress,
      'error_message': instance.errorMessage,
    };

ProcessingStatus _$ProcessingStatusFromJson(Map<String, dynamic> json) =>
    ProcessingStatus(
      mediaUuid: json['media_uuid'] as String,
      status: json['status'] as String,
      faceDetectionProcessed: json['face_detection_processed'] as bool,
      currentSession: json['current_session'] as String?,
      processingProgress: json['processing_progress'] as Map<String, dynamic>?,
      totalFacesDetected: (json['total_faces_detected'] as num?)?.toInt(),
      totalFramesProcessed: (json['total_frames_processed'] as num?)?.toInt(),
      processingMethod: json['processing_method'] as String?,
      optimalPlaybackMode: json['optimal_playback_mode'] as String?,
      cacheAvailable: json['cache_available'] as bool?,
      lastUpdated: json['last_updated'] == null
          ? null
          : DateTime.parse(json['last_updated'] as String),
      errorMessage: json['error_message'] as String?,
    );

Map<String, dynamic> _$ProcessingStatusToJson(ProcessingStatus instance) =>
    <String, dynamic>{
      'media_uuid': instance.mediaUuid,
      'status': instance.status,
      'face_detection_processed': instance.faceDetectionProcessed,
      'current_session': instance.currentSession,
      'processing_progress': instance.processingProgress,
      'total_faces_detected': instance.totalFacesDetected,
      'total_frames_processed': instance.totalFramesProcessed,
      'processing_method': instance.processingMethod,
      'optimal_playback_mode': instance.optimalPlaybackMode,
      'cache_available': instance.cacheAvailable,
      'last_updated': instance.lastUpdated?.toIso8601String(),
      'error_message': instance.errorMessage,
    };

PlaybackMode _$PlaybackModeFromJson(Map<String, dynamic> json) =>
    PlaybackMode(
      mode: json['mode'] as String,
      description: json['description'] as String,
      cpuOptimized: json['cpu_optimized'] as bool,
      expectedCpuReduction: (json['expected_cpu_reduction'] as num?)?.toDouble(),
      memoryOptimized: json['memory_optimized'] as bool?,
      expectedMemoryReduction: (json['expected_memory_reduction'] as num?)?.toDouble(),
      recommendationReason: json['recommendation_reason'] as String?,
      performanceScore: (json['performance_score'] as num?)?.toDouble(),
    );

Map<String, dynamic> _$PlaybackModeToJson(PlaybackMode instance) =>
    <String, dynamic>{
      'mode': instance.mode,
      'description': instance.description,
      'cpu_optimized': instance.cpuOptimized,
      'expected_cpu_reduction': instance.expectedCpuReduction,
      'memory_optimized': instance.memoryOptimized,
      'expected_memory_reduction': instance.expectedMemoryReduction,
      'recommendation_reason': instance.recommendationReason,
      'performance_score': instance.performanceScore,
    };

WorkflowPerformanceMetrics _$WorkflowPerformanceMetricsFromJson(Map<String, dynamic> json) =>
    WorkflowPerformanceMetrics(
      cpuUsageReduction: (json['cpu_usage_reduction'] as num).toDouble(),
      memoryUsageReduction: (json['memory_usage_reduction'] as num).toDouble(),
      activeSessionsCount: (json['active_sessions_count'] as num).toInt(),
      processedVideosCount: (json['processed_videos_count'] as num).toInt(),
      lastUpdated: DateTime.parse(json['last_updated'] as String),
      avgProcessingTimeSeconds: (json['avg_processing_time_seconds'] as num?)?.toDouble(),
      totalFacesDetected: (json['total_faces_detected'] as num?)?.toInt(),
      systemCpuUsage: (json['system_cpu_usage'] as num?)?.toDouble(),
      systemMemoryUsage: (json['system_memory_usage'] as num?)?.toDouble(),
      processingThroughput: (json['processing_throughput'] as num?)?.toDouble(),
    );

Map<String, dynamic> _$WorkflowPerformanceMetricsToJson(WorkflowPerformanceMetrics instance) =>
    <String, dynamic>{
      'cpu_usage_reduction': instance.cpuUsageReduction,
      'memory_usage_reduction': instance.memoryUsageReduction,
      'active_sessions_count': instance.activeSessionsCount,
      'processed_videos_count': instance.processedVideosCount,
      'last_updated': instance.lastUpdated.toIso8601String(),
      'avg_processing_time_seconds': instance.avgProcessingTimeSeconds,
      'total_faces_detected': instance.totalFacesDetected,
      'system_cpu_usage': instance.systemCpuUsage,
      'system_memory_usage': instance.systemMemoryUsage,
      'processing_throughput': instance.processingThroughput,
    };

SessionCreationRequest _$SessionCreationRequestFromJson(Map<String, dynamic> json) =>
    SessionCreationRequest(
      mediaUuid: json['media_uuid'] as String,
      confidenceThreshold: (json['confidence_threshold'] as num?)?.toDouble(),
      detectionMethods: (json['detection_methods'] as List<dynamic>?)?.map((e) => e as String).toList(),
      priority: json['priority'] as String?,
      enableProgressUpdates: json['enable_progress_updates'] as bool?,
    );

Map<String, dynamic> _$SessionCreationRequestToJson(SessionCreationRequest instance) =>
    <String, dynamic>{
      'media_uuid': instance.mediaUuid,
      'confidence_threshold': instance.confidenceThreshold,
      'detection_methods': instance.detectionMethods,
      'priority': instance.priority,
      'enable_progress_updates': instance.enableProgressUpdates,
    };

SessionStatistics _$SessionStatisticsFromJson(Map<String, dynamic> json) =>
    SessionStatistics(
      sessionUuid: json['session_uuid'] as String,
      progress: (json['progress'] as num).toDouble(),
      framesPerSecond: (json['frames_per_second'] as num?)?.toDouble(),
      estimatedTimeRemainingSeconds: (json['estimated_time_remaining_seconds'] as num?)?.toDouble(),
      currentFrame: (json['current_frame'] as num?)?.toInt(),
      totalFrames: (json['total_frames'] as num?)?.toInt(),
      facesDetectedCurrentSession: (json['faces_detected_current_session'] as num?)?.toInt(),
    );

Map<String, dynamic> _$SessionStatisticsToJson(SessionStatistics instance) =>
    <String, dynamic>{
      'session_uuid': instance.sessionUuid,
      'progress': instance.progress,
      'frames_per_second': instance.framesPerSecond,
      'estimated_time_remaining_seconds': instance.estimatedTimeRemainingSeconds,
      'current_frame': instance.currentFrame,
      'total_frames': instance.totalFrames,
      'faces_detected_current_session': instance.facesDetectedCurrentSession,
    };