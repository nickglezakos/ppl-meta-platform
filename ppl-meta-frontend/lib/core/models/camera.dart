/// Camera device model with enhanced metadata and multi-camera support
class Camera {
  final String id;
  final String deviceId;
  final String name;
  final String? manufacturer;
  final String? model;
  final String? resolution;
  final String status;
  final bool isActive;
  final DateTime? lastSeen;
  final String? streamUrl;
  final CameraType type;
  final Map<String, dynamic>? metadata;
  final bool supportsRecording;
  
  // Pipeline settings
  final bool instantDetectionEnabled;
  final bool recordingPipelineEnabled;
  final int instantDetectionIntervalSeconds;
  final int segmentDurationSeconds;

  // Workflow settings (face detection & performance)
  final bool autoFaceDetection;
  final List<String> detectionMethods;
  final Map<String, dynamic> processingOptions;
  final double confidenceThreshold;
  final bool enablePerformanceOptimization;
  final bool showPerformanceIndicators;
  final String defaultPlaybackMode;
  final double mvrQualityThreshold;

  const Camera({
    required this.id,
    required this.deviceId,
    required this.name,
    this.manufacturer,
    this.model,
    this.resolution,
    required this.status,
    this.isActive = false,
    this.lastSeen,
    this.streamUrl,
    this.type = CameraType.usb,
    this.metadata,
    this.supportsRecording = false,
    this.instantDetectionEnabled = true,
    this.recordingPipelineEnabled = true,
    this.instantDetectionIntervalSeconds = 5,
    this.segmentDurationSeconds = 30,
    this.autoFaceDetection = false,
    this.detectionMethods = const ['opencv', 'dlib'],
    this.processingOptions = const {},
    this.confidenceThreshold = 0.7,
    this.enablePerformanceOptimization = true,
    this.showPerformanceIndicators = true,
    this.defaultPlaybackMode = 'auto',
    this.mvrQualityThreshold = 0.20,
  });

  factory Camera.fromJson(Map<String, dynamic> json) {
    // Extract connection string and other metadata for mobile camera detection
    final connectionString = json['connection_string']?.toString();
    final cameraTypeStr = json['camera_type']?.toString() ?? json['type']?.toString();
    
    // Build metadata including connection info
    final metadata = Map<String, dynamic>.from(json['metadata'] as Map<String, dynamic>? ?? {});
    if (connectionString != null) {
      metadata['connection_string'] = connectionString;
    }
    if (json['ip_address'] != null) {
      metadata['ip_address'] = json['ip_address'];
    }
    if (json['port'] != null) {
      metadata['port'] = json['port'];
    }
    
    // Determine camera type with mobile detection
    CameraType cameraType;
    if (cameraTypeStr?.toLowerCase() == 'mobile' || connectionString?.startsWith('mobile://') == true) {
      cameraType = CameraType.mobile;
    } else {
      cameraType = CameraType.values.firstWhere(
        (t) => t.name.toLowerCase() == cameraTypeStr?.toLowerCase(),
        orElse: () => CameraType.usb,
      );
    }
    
    return Camera(
      id: json['id']?.toString() ?? '',
      deviceId: json['device_id']?.toString() ?? '',
      name: json['name']?.toString() ?? '',
      manufacturer: json['manufacturer']?.toString(),
      model: json['model']?.toString(),
      resolution: json['resolution']?.toString(),
      status: json['status']?.toString() ?? 'unknown',
      isActive: json['is_active'] as bool? ?? false,
      lastSeen: json['last_seen'] != null
          ? DateTime.tryParse(json['last_seen'].toString())
          : null,
      streamUrl: json['stream_url']?.toString(),
      type: cameraType,
      metadata: metadata,
      supportsRecording: json['supports_recording'] as bool? ?? false,
      instantDetectionEnabled: json['instant_detection_enabled'] as bool? ?? true,
      recordingPipelineEnabled: json['recording_pipeline_enabled'] as bool? ?? true,
      instantDetectionIntervalSeconds: json['instant_detection_interval_seconds'] as int? ?? 5,
      segmentDurationSeconds: json['segment_duration_seconds'] as int? ?? 30,
      autoFaceDetection: json['auto_face_detection'] as bool? ?? false,
      detectionMethods: (json['detection_methods'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? ['opencv', 'dlib'],
      processingOptions: Map<String, dynamic>.from(json['processing_options'] as Map<String, dynamic>? ?? {}),
      confidenceThreshold: (json['confidence_threshold'] as num?)?.toDouble() ?? 0.7,
      enablePerformanceOptimization: json['enable_performance_optimization'] as bool? ?? true,
      showPerformanceIndicators: json['show_performance_indicators'] as bool? ?? true,
      defaultPlaybackMode: json['default_playback_mode'] as String? ?? 'auto',
      mvrQualityThreshold: (json['mvr_quality_threshold'] as num?)?.toDouble() ?? 0.20,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'device_id': deviceId,
      'manufacturer': manufacturer,
      'model': model,
      'resolution': resolution,
      'status': status,
      'is_active': isActive,
      'last_seen': lastSeen?.toIso8601String(),
      'stream_url': streamUrl,
      'type': type.name,
      'metadata': metadata,
      'supports_recording': supportsRecording,
      'instant_detection_enabled': instantDetectionEnabled,
      'recording_pipeline_enabled': recordingPipelineEnabled,
      'instant_detection_interval_seconds': instantDetectionIntervalSeconds,
      'segment_duration_seconds': segmentDurationSeconds,
      'auto_face_detection': autoFaceDetection,
      'detection_methods': detectionMethods,
      'processing_options': processingOptions,
      'confidence_threshold': confidenceThreshold,
      'enable_performance_optimization': enablePerformanceOptimization,
      'show_performance_indicators': showPerformanceIndicators,
      'default_playback_mode': defaultPlaybackMode,
      'mvr_quality_threshold': mvrQualityThreshold,
    };
  }

  Camera copyWith({
    String? id,
    String? name,
    String? deviceId,
    String? manufacturer,
    String? model,
    String? resolution,
    String? status,
    bool? isActive,
    DateTime? lastSeen,
    String? streamUrl,
    CameraType? type,
    Map<String, dynamic>? metadata,
    bool? instantDetectionEnabled,
    bool? recordingPipelineEnabled,
    int? instantDetectionIntervalSeconds,
    int? segmentDurationSeconds,
    bool? autoFaceDetection,
    List<String>? detectionMethods,
    Map<String, dynamic>? processingOptions,
    double? confidenceThreshold,
    bool? enablePerformanceOptimization,
    bool? showPerformanceIndicators,
    String? defaultPlaybackMode,
    double? mvrQualityThreshold,
  }) {
    return Camera(
      id: id ?? this.id,
      name: name ?? this.name,
      deviceId: deviceId ?? this.deviceId,
      manufacturer: manufacturer ?? this.manufacturer,
      model: model ?? this.model,
      resolution: resolution ?? this.resolution,
      status: status ?? this.status,
      isActive: isActive ?? this.isActive,
      lastSeen: lastSeen ?? this.lastSeen,
      streamUrl: streamUrl ?? this.streamUrl,
      type: type ?? this.type,
      metadata: metadata ?? this.metadata,
      instantDetectionEnabled: instantDetectionEnabled ?? this.instantDetectionEnabled,
      recordingPipelineEnabled: recordingPipelineEnabled ?? this.recordingPipelineEnabled,
      instantDetectionIntervalSeconds: instantDetectionIntervalSeconds ?? this.instantDetectionIntervalSeconds,
      segmentDurationSeconds: segmentDurationSeconds ?? this.segmentDurationSeconds,
      autoFaceDetection: autoFaceDetection ?? this.autoFaceDetection,
      detectionMethods: detectionMethods ?? this.detectionMethods,
      processingOptions: processingOptions ?? this.processingOptions,
      confidenceThreshold: confidenceThreshold ?? this.confidenceThreshold,
      enablePerformanceOptimization: enablePerformanceOptimization ?? this.enablePerformanceOptimization,
      showPerformanceIndicators: showPerformanceIndicators ?? this.showPerformanceIndicators,
      defaultPlaybackMode: defaultPlaybackMode ?? this.defaultPlaybackMode,
      mvrQualityThreshold: mvrQualityThreshold ?? this.mvrQualityThreshold,
    );
  }

  /// Check if camera is connected (based on status)
  bool get isConnected => status.toLowerCase() == 'connected';

  /// Check if this is a mobile camera
  bool get isMobileCamera => type == CameraType.mobile || 
      (metadata != null && metadata!['connection_string']?.toString().startsWith('mobile://') == true);
  
  /// Get pipeline mode description
  String get pipelineModeDescription {
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
  
  /// Get short pipeline mode
  String get pipelineMode {
    if (instantDetectionEnabled && recordingPipelineEnabled) {
      return 'Both';
    } else if (instantDetectionEnabled) {
      return 'Detection';
    } else if (recordingPipelineEnabled) {
      return 'Recording';
    } else {
      return 'None';
    }
  }

  /// Get the direct MJPEG stream URL for mobile cameras
  /// Returns null if this is not a mobile camera or if connection info is not available
  String? get directStreamUrl {
    if (!isMobileCamera) return null;
    
    // For mobile cameras, check if we have the backend server IP
    // This should be the computer's IP where the cameras service is running
    final backendIP = metadata?['backend_ip'] as String?;
    final port = metadata?['backend_port'] as int?;
    
    if (backendIP != null) {
      // Use the backend server's IP (computer where cameras service runs)
      final camerasServicePort = port ?? 8005;
      final baseUrl = 'http://$backendIP:$camerasServicePort';
      return '$baseUrl/api/v1/streaming/$deviceId/video';
    }
    
    // Fallback: For mobile cameras, use the cameras service streaming endpoint
    // This uses the backend's /api/v1/streaming/{device_id}/video endpoint
    // which can handle mobile camera frames received via the mobile app
    
    // Get the cameras service URL (typically port 8005)
    // This should be configured to match the current environment
    const camerasServiceUrl = 'http://localhost:8005'; // TODO: Make this configurable
    
    // Return the streaming endpoint URL
    return '$camerasServiceUrl/api/v1/streaming/$deviceId/video';
  }
}

/// Streaming information for a camera
class StreamingInfo {
  final String streamId;
  final String cameraId;
  final String streamUrl;
  final String status;
  final DateTime startedAt;
  final int? fps;
  final String? resolution;

  const StreamingInfo({
    required this.streamId,
    required this.cameraId,
    required this.streamUrl,
    required this.status,
    required this.startedAt,
    this.fps,
    this.resolution,
  });

  factory StreamingInfo.fromJson(Map<String, dynamic> json) {
    final deviceId = json['device_id']?.toString() ?? json['camera_id']?.toString() ?? json['cameraId']?.toString() ?? '';
    return StreamingInfo(
      streamId: json['stream_id']?.toString() ?? json['streamId']?.toString() ?? json['session_id']?.toString() ?? deviceId,
      cameraId: deviceId,
      streamUrl: json['stream_url']?.toString() ?? json['streamUrl']?.toString() ?? json['video_url']?.toString() ?? '',
      status: json['status']?.toString() ?? 'unknown',
      startedAt: DateTime.tryParse(json['started_at']?.toString() ?? json['startedAt']?.toString() ?? '') ?? DateTime.now(),
      fps: json['fps'] as int?,
      resolution: json['resolution']?.toString(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'stream_id': streamId,
      'camera_id': cameraId,
      'stream_url': streamUrl,
      'status': status,
      'started_at': startedAt.toIso8601String(),
      'fps': fps,
      'resolution': resolution,
    };
  }

  StreamingInfo copyWith({
    String? streamId,
    String? cameraId,
    String? streamUrl,
    String? status,
    DateTime? startedAt,
    int? fps,
    String? resolution,
  }) {
    return StreamingInfo(
      streamId: streamId ?? this.streamId,
      cameraId: cameraId ?? this.cameraId,
      streamUrl: streamUrl ?? this.streamUrl,
      status: status ?? this.status,
      startedAt: startedAt ?? this.startedAt,
      fps: fps ?? this.fps,
      resolution: resolution ?? this.resolution,
    );
  }
}

/// Snapshot information
class SnapshotInfo {
  final String snapshotId;
  final String cameraId;
  final String imageUrl;
  final DateTime capturedAt;
  final String? filename;
  final int? fileSize;

  const SnapshotInfo({
    required this.snapshotId,
    required this.cameraId,
    required this.imageUrl,
    required this.capturedAt,
    this.filename,
    this.fileSize,
  });

  factory SnapshotInfo.fromJson(Map<String, dynamic> json) {
    return SnapshotInfo(
      snapshotId: json['snapshot_id']?.toString() ?? json['snapshotId']?.toString() ?? '',
      cameraId: json['camera_id']?.toString() ?? json['cameraId']?.toString() ?? '',
      imageUrl: json['image_url']?.toString() ?? json['imageUrl']?.toString() ?? '',
      capturedAt: DateTime.tryParse(json['captured_at']?.toString() ?? json['capturedAt']?.toString() ?? '') ?? DateTime.now(),
      filename: json['filename']?.toString(),
      fileSize: json['file_size'] as int? ?? json['fileSize'] as int?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'snapshot_id': snapshotId,
      'camera_id': cameraId,
      'image_url': imageUrl,
      'captured_at': capturedAt.toIso8601String(),
      'filename': filename,
      'file_size': fileSize,
    };
  }
}





/// Request model for updating camera settings
class CameraUpdateRequest {
  final String? name;
  final bool? isActive;
  final String? resolution;
  final Map<String, dynamic>? metadata;

  const CameraUpdateRequest({
    this.name,
    this.isActive,
    this.resolution,
    this.metadata,
  });

  factory CameraUpdateRequest.fromJson(Map<String, dynamic> json) {
    return CameraUpdateRequest(
      name: json['name']?.toString(),
      isActive: json['is_active'] ?? json['isActive'],
      resolution: json['resolution']?.toString(),
      metadata: json['metadata'] as Map<String, dynamic>?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'name': name,
      'is_active': isActive,
      'resolution': resolution,
      'metadata': metadata,
    };
  }
}

/// Camera detection result
class CameraDetectionResult {
  final List<Camera> cameras;
  final int totalFound;
  final DateTime detectedAt;
  final bool savedToDatabase;

  const CameraDetectionResult({
    required this.cameras,
    required this.totalFound,
    required this.detectedAt,
    required this.savedToDatabase,
  });

  factory CameraDetectionResult.fromJson(Map<String, dynamic> json) {
    return CameraDetectionResult(
      cameras: (json['cameras'] as List<dynamic>?)
          ?.map((camera) => Camera.fromJson(camera as Map<String, dynamic>))
          .toList() ?? [],
      totalFound: json['total_found'] ?? json['totalFound'] ?? 0,
      detectedAt: DateTime.tryParse(json['detected_at']?.toString() ?? json['detectedAt']?.toString() ?? '') ?? DateTime.now(),
      savedToDatabase: json['saved_to_database'] ?? json['savedToDatabase'] ?? false,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'cameras': cameras.map((camera) => camera.toJson()).toList(),
      'total_found': totalFound,
      'detected_at': detectedAt.toIso8601String(),
      'saved_to_database': savedToDatabase,
    };
  }
}

/// Camera connection status
enum CameraConnectionStatus {
  connected,
  disconnected,
  connecting,
  error,
}

/// Camera streaming quality
enum StreamingQuality {
  low,
  medium,
  high,
  ultra,
}

/// Extension for camera status
extension CameraStatusExtension on Camera {
  bool get isConnected => status == 'connected';
  bool get isStreaming => status == 'streaming';
  bool get hasError => status == 'error';
  
  CameraConnectionStatus get connectionStatus {
    switch (status.toLowerCase()) {
      case 'connected':
        return CameraConnectionStatus.connected;
      case 'disconnected':
        return CameraConnectionStatus.disconnected;
      case 'connecting':
        return CameraConnectionStatus.connecting;
      case 'error':
        return CameraConnectionStatus.error;
      default:
        return CameraConnectionStatus.disconnected;
    }
  }
}

/// Streaming status model
class StreamingStatus {
  final String deviceId;
  final String streamStatus;
  final DateTime? startedAt;
  final int? durationSeconds;
  final Map<String, dynamic>? currentSettings;
  final int? viewerCount;
  final double? dataTransferredMb;

  const StreamingStatus({
    required this.deviceId,
    required this.streamStatus,
    this.startedAt,
    this.durationSeconds,
    this.currentSettings,
    this.viewerCount,
    this.dataTransferredMb,
  });

  bool get isActive => streamStatus.toLowerCase() == 'active';

  factory StreamingStatus.fromJson(Map<String, dynamic> json) {
    return StreamingStatus(
      deviceId: json['device_id']?.toString() ?? '',
      streamStatus: json['stream_status']?.toString() ?? 'inactive',
      startedAt: json['started_at'] != null 
          ? DateTime.tryParse(json['started_at'].toString()) 
          : null,
      durationSeconds: json['duration_seconds'] as int?,
      currentSettings: json['current_settings'] as Map<String, dynamic>?,
      viewerCount: json['viewer_count'] as int?,
      dataTransferredMb: (json['data_transferred_mb'] as num?)?.toDouble(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'device_id': deviceId,
      'stream_status': streamStatus,
      'started_at': startedAt?.toIso8601String(),
      'duration_seconds': durationSeconds,
      'current_settings': currentSettings,
      'viewer_count': viewerCount,
      'data_transferred_mb': dataTransferredMb,
    };
  }
}

/// Camera type enumeration for multi-camera support
enum CameraType {
  usb('USB Camera'),
  rtsp('RTSP Network Camera'),
  webRtc('WebRTC Camera'),
  mjpeg('MJPEG Camera'),
  mobile('Mobile Camera'),
  virtual('Virtual Camera');

  const CameraType(this.displayName);
  final String displayName;
}
