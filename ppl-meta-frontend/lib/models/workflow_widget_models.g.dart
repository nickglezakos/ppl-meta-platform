// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'workflow_widget_models.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

ProcessingProgress _$ProcessingProgressFromJson(Map<String, dynamic> json) =>
    ProcessingProgress(
      currentFrame: (json['current_frame'] as num).toInt(),
      totalFrames: (json['total_frames'] as num).toInt(),
      percentage: (json['percentage'] as num).toDouble(),
      estimatedTimeRemaining:
          (json['estimated_time_remaining'] as num?)?.toInt(),
    );

Map<String, dynamic> _$ProcessingProgressToJson(ProcessingProgress instance) =>
    <String, dynamic>{
      'current_frame': instance.currentFrame,
      'total_frames': instance.totalFrames,
      'percentage': instance.percentage,
      'estimated_time_remaining': instance.estimatedTimeRemaining,
    };

SessionSummary _$SessionSummaryFromJson(Map<String, dynamic> json) =>
    SessionSummary(
      sessionUuid: json['session_uuid'] as String,
      sessionType: json['session_type'] as String,
      startedAt: DateTime.parse(json['started_at'] as String),
      endedAt: json['ended_at'] == null
          ? null
          : DateTime.parse(json['ended_at'] as String),
      totalFacesDetected: (json['total_faces_detected'] as num).toInt(),
      processingStatus: json['processing_status'] as String,
      durationSeconds: (json['duration_seconds'] as num?)?.toDouble(),
    );

Map<String, dynamic> _$SessionSummaryToJson(SessionSummary instance) =>
    <String, dynamic>{
      'session_uuid': instance.sessionUuid,
      'session_type': instance.sessionType,
      'started_at': instance.startedAt.toIso8601String(),
      'ended_at': instance.endedAt?.toIso8601String(),
      'total_faces_detected': instance.totalFacesDetected,
      'processing_status': instance.processingStatus,
      'duration_seconds': instance.durationSeconds,
    };

WidgetStatusResponse _$WidgetStatusResponseFromJson(
        Map<String, dynamic> json) =>
    WidgetStatusResponse(
      mediaUuid: json['media_uuid'] as String,
      status: $enumDecode(_$WorkflowWidgetStatusEnumMap, json['status']),
      faceDetectionProcessed: json['face_detection_processed'] as bool,
      currentSession: json['current_session'] == null
          ? null
          : SessionSummary.fromJson(
              json['current_session'] as Map<String, dynamic>),
      processingProgress: json['processing_progress'] == null
          ? null
          : ProcessingProgress.fromJson(
              json['processing_progress'] as Map<String, dynamic>),
      totalFacesDetected: (json['total_faces_detected'] as num).toInt(),
      totalFramesProcessed: (json['total_frames_processed'] as num).toInt(),
      processingMethod: json['processing_method'] as String?,
      optimalPlaybackMode:
          $enumDecode(_$PlaybackModeEnumMap, json['optimal_playback_mode']),
      cacheAvailable: json['cache_available'] as bool,
      lastUpdated: DateTime.parse(json['last_updated'] as String),
      errorMessage: json['error_message'] as String?,
    );

Map<String, dynamic> _$WidgetStatusResponseToJson(
        WidgetStatusResponse instance) =>
    <String, dynamic>{
      'media_uuid': instance.mediaUuid,
      'status': _$WorkflowWidgetStatusEnumMap[instance.status]!,
      'face_detection_processed': instance.faceDetectionProcessed,
      'current_session': instance.currentSession,
      'processing_progress': instance.processingProgress,
      'total_faces_detected': instance.totalFacesDetected,
      'total_frames_processed': instance.totalFramesProcessed,
      'processing_method': instance.processingMethod,
      'optimal_playback_mode':
          _$PlaybackModeEnumMap[instance.optimalPlaybackMode]!,
      'cache_available': instance.cacheAvailable,
      'last_updated': instance.lastUpdated.toIso8601String(),
      'error_message': instance.errorMessage,
    };

const _$WorkflowWidgetStatusEnumMap = {
  WorkflowWidgetStatus.notStarted: 'not_started',
  WorkflowWidgetStatus.inProgress: 'in_progress',
  WorkflowWidgetStatus.completed: 'completed',
  WorkflowWidgetStatus.error: 'error',
  WorkflowWidgetStatus.paused: 'paused',
};

const _$PlaybackModeEnumMap = {
  PlaybackMode.realtimeOnly: 'realtime_only',
  PlaybackMode.cachedFrames: 'cached_frames',
  PlaybackMode.hybridMode: 'hybrid_mode',
};

WidgetAnalyticsResponse _$WidgetAnalyticsResponseFromJson(
        Map<String, dynamic> json) =>
    WidgetAnalyticsResponse(
      mediaUuid: json['media_uuid'] as String,
      sessionHistory: (json['session_history'] as List<dynamic>)
          .map((e) => SessionSummary.fromJson(e as Map<String, dynamic>))
          .toList(),
      totalSessions: (json['total_sessions'] as num).toInt(),
      averageProcessingTime:
          (json['average_processing_time'] as num?)?.toDouble(),
      totalFacesDetected: (json['total_faces_detected'] as num).toInt(),
      qualityMetrics: (json['quality_metrics'] as Map<String, dynamic>).map(
        (k, e) => MapEntry(k, (e as num).toDouble()),
      ),
      recommendations: (json['recommendations'] as List<dynamic>)
          .map((e) => e as String)
          .toList(),
    );

Map<String, dynamic> _$WidgetAnalyticsResponseToJson(
        WidgetAnalyticsResponse instance) =>
    <String, dynamic>{
      'media_uuid': instance.mediaUuid,
      'session_history': instance.sessionHistory,
      'total_sessions': instance.totalSessions,
      'average_processing_time': instance.averageProcessingTime,
      'total_faces_detected': instance.totalFacesDetected,
      'quality_metrics': instance.qualityMetrics,
      'recommendations': instance.recommendations,
    };

SystemHealthResponse _$SystemHealthResponseFromJson(
        Map<String, dynamic> json) =>
    SystemHealthResponse(
      overallStatus:
          $enumDecode(_$WorkflowWidgetStatusEnumMap, json['overall_status']),
      activeSessions: (json['active_sessions'] as num).toInt(),
      processingQueueSize: (json['processing_queue_size'] as num).toInt(),
      serviceHealth: Map<String, bool>.from(json['service_health'] as Map),
      alerts:
          (json['alerts'] as List<dynamic>).map((e) => e as String).toList(),
      lastCheck: DateTime.parse(json['last_check'] as String),
    );

Map<String, dynamic> _$SystemHealthResponseToJson(
        SystemHealthResponse instance) =>
    <String, dynamic>{
      'overall_status': _$WorkflowWidgetStatusEnumMap[instance.overallStatus]!,
      'active_sessions': instance.activeSessions,
      'processing_queue_size': instance.processingQueueSize,
      'service_health': instance.serviceHealth,
      'alerts': instance.alerts,
      'last_check': instance.lastCheck.toIso8601String(),
    };
