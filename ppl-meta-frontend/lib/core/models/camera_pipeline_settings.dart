/// Pipeline settings model for camera recording and detection configuration
class CameraPipelineSettings {
  final String deviceId;
  final String cameraName;
  final bool instantDetectionEnabled;
  final bool recordingPipelineEnabled;
  final int instantDetectionIntervalSeconds;
  final int segmentDurationSeconds;
  final int storageMultiple;
  final int trackingSessionDurationMinutes;

  const CameraPipelineSettings({
    required this.deviceId,
    required this.cameraName,
    required this.instantDetectionEnabled,
    required this.recordingPipelineEnabled,
    required this.instantDetectionIntervalSeconds,
    required this.segmentDurationSeconds,
    this.storageMultiple = 1,
    this.trackingSessionDurationMinutes = 0,
  });

  factory CameraPipelineSettings.fromJson(Map<String, dynamic> json) {
    return CameraPipelineSettings(
      deviceId: json['device_id']?.toString() ?? '',
      cameraName: json['camera_name']?.toString() ?? '',
      instantDetectionEnabled: json['instant_detection_enabled'] as bool? ?? true,
      recordingPipelineEnabled: json['recording_pipeline_enabled'] as bool? ?? true,
      instantDetectionIntervalSeconds: json['instant_detection_interval_seconds'] as int? ?? 5,
      segmentDurationSeconds: json['segment_duration_seconds'] as int? ?? 30,
      storageMultiple: json['storage_multiple'] as int? ?? 1,
      trackingSessionDurationMinutes: json['tracking_session_duration_minutes'] as int? ?? 0,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'device_id': deviceId,
      'camera_name': cameraName,
      'instant_detection_enabled': instantDetectionEnabled,
      'recording_pipeline_enabled': recordingPipelineEnabled,
      'instant_detection_interval_seconds': instantDetectionIntervalSeconds,
      'segment_duration_seconds': segmentDurationSeconds,
      'storage_multiple': storageMultiple,
      'tracking_session_duration_minutes': trackingSessionDurationMinutes,
    };
  }

  /// Create update payload (excludes read-only fields)
  Map<String, dynamic> toUpdateJson() {
    return {
      'instant_detection_enabled': instantDetectionEnabled,
      'recording_pipeline_enabled': recordingPipelineEnabled,
      'instant_detection_interval_seconds': instantDetectionIntervalSeconds,
      'segment_duration_seconds': segmentDurationSeconds,
      'storage_multiple': storageMultiple,
      'tracking_session_duration_minutes': trackingSessionDurationMinutes,
    };
  }

  CameraPipelineSettings copyWith({
    String? deviceId,
    String? cameraName,
    bool? instantDetectionEnabled,
    bool? recordingPipelineEnabled,
    int? instantDetectionIntervalSeconds,
    int? segmentDurationSeconds,
    int? storageMultiple,
    int? trackingSessionDurationMinutes,
  }) {
    return CameraPipelineSettings(
      deviceId: deviceId ?? this.deviceId,
      cameraName: cameraName ?? this.cameraName,
      instantDetectionEnabled: instantDetectionEnabled ?? this.instantDetectionEnabled,
      recordingPipelineEnabled: recordingPipelineEnabled ?? this.recordingPipelineEnabled,
      instantDetectionIntervalSeconds: instantDetectionIntervalSeconds ?? this.instantDetectionIntervalSeconds,
      segmentDurationSeconds: segmentDurationSeconds ?? this.segmentDurationSeconds,
      storageMultiple: storageMultiple ?? this.storageMultiple,
      trackingSessionDurationMinutes: trackingSessionDurationMinutes ?? this.trackingSessionDurationMinutes,
    );
  }

  /// Get pipeline mode description
  String get modeDescription {
    if (instantDetectionEnabled && recordingPipelineEnabled) {
      return 'Both Pipelines Active';
    } else if (instantDetectionEnabled) {
      return 'Instant Detection Only';
    } else if (recordingPipelineEnabled) {
      return 'Recording Only';
    } else {
      return 'Disabled';
    }
  }

  /// Check if settings are valid
  bool get isValid {
    return instantDetectionEnabled || recordingPipelineEnabled;
  }

  /// Validate instant detection interval
  bool get hasValidInterval {
    return instantDetectionIntervalSeconds >= 1 && instantDetectionIntervalSeconds <= 60;
  }

  /// Validate segment duration
  bool get hasValidDuration {
    return segmentDurationSeconds >= 5 && segmentDurationSeconds <= 300;
  }

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    return other is CameraPipelineSettings &&
        other.deviceId == deviceId &&
        other.instantDetectionEnabled == instantDetectionEnabled &&
        other.recordingPipelineEnabled == recordingPipelineEnabled &&
        other.instantDetectionIntervalSeconds == instantDetectionIntervalSeconds &&
        other.segmentDurationSeconds == segmentDurationSeconds &&
        other.storageMultiple == storageMultiple &&
        other.trackingSessionDurationMinutes == trackingSessionDurationMinutes;
  }

  @override
  int get hashCode {
    return Object.hash(
      deviceId,
      instantDetectionEnabled,
      recordingPipelineEnabled,
      instantDetectionIntervalSeconds,
      segmentDurationSeconds,
      storageMultiple,
      trackingSessionDurationMinutes,
    );
  }
}
