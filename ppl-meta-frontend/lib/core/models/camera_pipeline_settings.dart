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
  final int framesPerCycle;
  final int flushIntervalCycles;
  final double flushMergeSimilarityThreshold;
  final bool normaliseEnabled;
  final int normaliseSpanSeconds;
  final double normaliseMergeThreshold;

  const CameraPipelineSettings({
    required this.deviceId,
    required this.cameraName,
    required this.instantDetectionEnabled,
    required this.recordingPipelineEnabled,
    required this.instantDetectionIntervalSeconds,
    required this.segmentDurationSeconds,
    this.storageMultiple = 1,
    this.trackingSessionDurationMinutes = 0,
    this.framesPerCycle = 3,
    this.flushIntervalCycles = 12,
    this.flushMergeSimilarityThreshold = 0.60,
    this.normaliseEnabled = true,
    this.normaliseSpanSeconds = 300,
    this.normaliseMergeThreshold = 0.70,
  });

  factory CameraPipelineSettings.fromJson(Map<String, dynamic> json) {
    return CameraPipelineSettings(
      deviceId: json['device_id']?.toString() ?? '',
      cameraName: json['camera_name']?.toString() ?? '',
      instantDetectionEnabled: json['instant_detection_enabled'] as bool? ?? true,
      recordingPipelineEnabled: json['recording_pipeline_enabled'] as bool? ?? true,
      instantDetectionIntervalSeconds:
          json['instant_detection_interval_seconds'] as int? ?? 5,
      segmentDurationSeconds: json['segment_duration_seconds'] as int? ?? 30,
      storageMultiple: json['storage_multiple'] as int? ?? 1,
      trackingSessionDurationMinutes:
          json['tracking_session_duration_minutes'] as int? ?? 0,
      framesPerCycle: json['frames_per_cycle'] as int? ?? 3,
      flushIntervalCycles: json['flush_interval_cycles'] as int? ?? 12,
      flushMergeSimilarityThreshold:
          (json['flush_merge_similarity_threshold'] as num?)?.toDouble() ?? 0.60,
      normaliseEnabled: json['normalise_enabled'] as bool? ?? true,
      normaliseSpanSeconds: json['normalise_span_seconds'] as int? ?? 300,
      normaliseMergeThreshold:
          (json['normalise_merge_threshold'] as num?)?.toDouble() ?? 0.70,
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
      'frames_per_cycle': framesPerCycle,
      'flush_interval_cycles': flushIntervalCycles,
      'flush_merge_similarity_threshold': flushMergeSimilarityThreshold,
      'normalise_enabled': normaliseEnabled,
      'normalise_span_seconds': normaliseSpanSeconds,
      'normalise_merge_threshold': normaliseMergeThreshold,
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
      'frames_per_cycle': framesPerCycle,
      'flush_interval_cycles': flushIntervalCycles,
      'flush_merge_similarity_threshold': flushMergeSimilarityThreshold,
      'normalise_enabled': normaliseEnabled,
      'normalise_span_seconds': normaliseSpanSeconds,
      'normalise_merge_threshold': normaliseMergeThreshold,
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
    int? framesPerCycle,
    int? flushIntervalCycles,
    double? flushMergeSimilarityThreshold,
    bool? normaliseEnabled,
    int? normaliseSpanSeconds,
    double? normaliseMergeThreshold,
  }) {
    return CameraPipelineSettings(
      deviceId: deviceId ?? this.deviceId,
      cameraName: cameraName ?? this.cameraName,
      instantDetectionEnabled:
          instantDetectionEnabled ?? this.instantDetectionEnabled,
      recordingPipelineEnabled:
          recordingPipelineEnabled ?? this.recordingPipelineEnabled,
      instantDetectionIntervalSeconds: instantDetectionIntervalSeconds ??
          this.instantDetectionIntervalSeconds,
      segmentDurationSeconds:
          segmentDurationSeconds ?? this.segmentDurationSeconds,
      storageMultiple: storageMultiple ?? this.storageMultiple,
      trackingSessionDurationMinutes: trackingSessionDurationMinutes ??
          this.trackingSessionDurationMinutes,
      framesPerCycle: framesPerCycle ?? this.framesPerCycle,
      flushIntervalCycles: flushIntervalCycles ?? this.flushIntervalCycles,
      flushMergeSimilarityThreshold: flushMergeSimilarityThreshold ??
          this.flushMergeSimilarityThreshold,
      normaliseEnabled: normaliseEnabled ?? this.normaliseEnabled,
      normaliseSpanSeconds: normaliseSpanSeconds ?? this.normaliseSpanSeconds,
      normaliseMergeThreshold:
          normaliseMergeThreshold ?? this.normaliseMergeThreshold,
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
    return instantDetectionIntervalSeconds >= 1 &&
        instantDetectionIntervalSeconds <= 60;
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
        other.instantDetectionIntervalSeconds ==
            instantDetectionIntervalSeconds &&
        other.segmentDurationSeconds == segmentDurationSeconds &&
        other.storageMultiple == storageMultiple &&
        other.trackingSessionDurationMinutes == trackingSessionDurationMinutes &&
        other.framesPerCycle == framesPerCycle &&
        other.flushIntervalCycles == flushIntervalCycles &&
        other.flushMergeSimilarityThreshold == flushMergeSimilarityThreshold &&
        other.normaliseEnabled == normaliseEnabled &&
        other.normaliseSpanSeconds == normaliseSpanSeconds &&
        other.normaliseMergeThreshold == normaliseMergeThreshold;
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
      framesPerCycle,
      flushIntervalCycles,
      flushMergeSimilarityThreshold,
      normaliseEnabled,
      normaliseSpanSeconds,
      normaliseMergeThreshold,
    );
  }
}
