import 'package:camera/camera.dart';

/// Camera configuration model for PPL Meta Mobile Camera
class CameraConfig {
  final CameraDescription camera;
  final ResolutionPreset resolution;
  final int fps;
  final String quality;
  final bool enableAudio;
  final bool enableFlash;
  
  const CameraConfig({
    required this.camera,
    this.resolution = ResolutionPreset.medium,
    this.fps = 30,
    this.quality = 'medium',
    this.enableAudio = true,
    this.enableFlash = false,
  });

  CameraConfig copyWith({
    CameraDescription? camera,
    ResolutionPreset? resolution,
    int? fps,
    String? quality,
    bool? enableAudio,
    bool? enableFlash,
  }) {
    return CameraConfig(
      camera: camera ?? this.camera,
      resolution: resolution ?? this.resolution,
      fps: fps ?? this.fps,
      quality: quality ?? this.quality,
      enableAudio: enableAudio ?? this.enableAudio,
      enableFlash: enableFlash ?? this.enableFlash,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'cameraId': camera.name,
      'resolution': resolution.toString().split('.').last,
      'fps': fps,
      'quality': quality,
      'enableAudio': enableAudio,
      'enableFlash': enableFlash,
    };
  }
}

/// Stream quality enumeration
enum StreamQuality {
  low(ResolutionPreset.low, 15, 'low'),
  medium(ResolutionPreset.medium, 30, 'medium'),
  high(ResolutionPreset.high, 30, 'high'),
  veryHigh(ResolutionPreset.veryHigh, 60, 'very_high');

  const StreamQuality(this.resolution, this.fps, this.label);
  
  final ResolutionPreset resolution;
  final int fps;
  final String label;

  /// Convert to JSON representation
  Map<String, dynamic> toJson() {
    return {
      'resolution': resolution.name,
      'fps': fps,
      'label': label,
    };
  }
}

/// Capture result model
class CaptureResult {
  final String filePath;
  final DateTime timestamp;
  final int fileSize;
  final String resolution;
  final bool success;
  final String? error;
  
  const CaptureResult({
    required this.filePath,
    required this.timestamp,
    required this.fileSize,
    required this.resolution,
    this.success = true,
    this.error,
  });

  factory CaptureResult.error(String error) {
    return CaptureResult(
      filePath: '',
      timestamp: DateTime.now(),
      fileSize: 0,
      resolution: '',
      success: false,
      error: error,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'filePath': filePath,
      'timestamp': timestamp.toIso8601String(),
      'fileSize': fileSize,
      'resolution': resolution,
      'success': success,
      'error': error,
    };
  }
}
