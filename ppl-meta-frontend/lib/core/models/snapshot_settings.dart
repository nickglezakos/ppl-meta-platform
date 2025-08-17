/// Enhanced snapshot settings models for independent resolution control
class SnapshotSettings {
  final String resolution;
  final int quality;
  final String format;
  final bool saveToFile;
  final String? filename;

  const SnapshotSettings({
    this.resolution = 'max',
    this.quality = 95,
    this.format = 'JPEG',
    this.saveToFile = true,
    this.filename,
  });

  Map<String, dynamic> toJson() {
    return {
      'resolution': resolution,
      'quality': quality,
      'format': format,
      'save_to_file': saveToFile,
      if (filename != null) 'filename': filename,
    };
  }

  factory SnapshotSettings.fromJson(Map<String, dynamic> json) {
    return SnapshotSettings(
      resolution: json['resolution'] ?? 'max',
      quality: json['quality'] ?? 95,
      format: json['format'] ?? 'JPEG',
      saveToFile: json['save_to_file'] ?? true,
      filename: json['filename'],
    );
  }

  SnapshotSettings copyWith({
    String? resolution,
    int? quality,
    String? format,
    bool? saveToFile,
    String? filename,
  }) {
    return SnapshotSettings(
      resolution: resolution ?? this.resolution,
      quality: quality ?? this.quality,
      format: format ?? this.format,
      saveToFile: saveToFile ?? this.saveToFile,
      filename: filename ?? this.filename,
    );
  }

  /// Get quality description for UI
  String get qualityDescription {
    if (quality >= 95) return 'Maximum Quality';
    if (quality >= 85) return 'High Quality';
    if (quality >= 75) return 'Good Quality';
    return 'Standard Quality';
  }

  /// Get estimated file size impact
  String get fileSizeImpact {
    if (quality >= 95) return 'Large files';
    if (quality >= 85) return 'Medium files';
    if (quality >= 75) return 'Smaller files';
    return 'Smallest files';
  }

  /// Get format description
  String get formatDescription {
    switch (format.toUpperCase()) {
      case 'JPEG':
        return 'Good compression, smaller files';
      case 'PNG':
        return 'Lossless quality, larger files';
      case 'BMP':
        return 'Uncompressed, largest files';
      default:
        return 'Standard format';
    }
  }
}

/// Camera capabilities including supported resolutions
class CameraCapabilities {
  final String deviceId;
  final CameraResolution maxResolution;
  final List<CameraResolution> supportedResolutions;
  final List<String> supportsFormats;
  final CameraResolution? currentStreamResolution;

  const CameraCapabilities({
    required this.deviceId,
    required this.maxResolution,
    required this.supportedResolutions,
    required this.supportsFormats,
    this.currentStreamResolution,
  });

  factory CameraCapabilities.fromJson(Map<String, dynamic> json) {
    final capabilities = json['capabilities'] ?? {};
    
    return CameraCapabilities(
      deviceId: json['device_id'] ?? '',
      maxResolution: CameraResolution.fromJson(capabilities['max_resolution'] ?? {}),
      supportedResolutions: (capabilities['supported_resolutions'] as List?)
          ?.map((e) => CameraResolution.fromJson(e))
          .toList() ?? [],
      supportsFormats: (capabilities['supports_formats'] as List?)
          ?.cast<String>() ?? ['JPEG'],
      currentStreamResolution: capabilities['current_stream_resolution'] != null
          ? CameraResolution.fromJson(capabilities['current_stream_resolution'])
          : null,
    );
  }

  /// Get available resolution options for UI
  List<String> get availableResolutions {
    final resolutions = <String>['max', 'stream'];
    for (final res in supportedResolutions) {
      resolutions.add('${res.width}x${res.height}');
    }
    return resolutions;
  }

  /// Get resolution display name
  String getResolutionDisplayName(String resolution) {
    switch (resolution) {
      case 'max':
        return 'Maximum (${maxResolution.width}x${maxResolution.height})';
      case 'stream':
        if (currentStreamResolution != null) {
          return 'Stream Quality (${currentStreamResolution!.width}x${currentStreamResolution!.height})';
        }
        return 'Stream Quality';
      default:
        if (resolution.contains('x')) {
          final parts = resolution.split('x');
          if (parts.length == 2) {
            final width = int.tryParse(parts[0]);
            final height = int.tryParse(parts[1]);
            if (width != null && height != null) {
              return '$resolution (${_getResolutionName(width, height)})';
            }
          }
        }
        return resolution;
    }
  }

  String _getResolutionName(int width, int height) {
    if (width == 3840 && height == 2160) return '4K UHD';
    if (width == 2560 && height == 1440) return '2K QHD';
    if (width == 1920 && height == 1080) return 'Full HD';
    if (width == 1280 && height == 720) return 'HD';
    if (width == 1024 && height == 768) return 'XGA';
    if (width == 800 && height == 600) return 'SVGA';
    if (width == 640 && height == 480) return 'VGA';
    return '$width×$height';
  }
}

/// Camera resolution information
class CameraResolution {
  final int width;
  final int height;

  const CameraResolution({
    required this.width,
    required this.height,
  });

  factory CameraResolution.fromJson(Map<String, dynamic> json) {
    return CameraResolution(
      width: json['width'] ?? 0,
      height: json['height'] ?? 0,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'width': width,
      'height': height,
    };
  }

  @override
  String toString() => '${width}x$height';

  /// Get megapixel count
  double get megapixels => (width * height) / 1000000;

  /// Get aspect ratio
  double get aspectRatio => width / height;
}

/// Enhanced snapshot result with metadata
class EnhancedSnapshotResult {
  final String deviceId;
  final String filename;
  final int fileSizeBytes;
  final CameraResolution resolution;
  final String format;
  final int quality;
  final String capturedAt;
  final String base64Image;
  final String? downloadUrl;
  final SnapshotSettings settings;
  final Map<String, dynamic> metadata;

  const EnhancedSnapshotResult({
    required this.deviceId,
    required this.filename,
    required this.fileSizeBytes,
    required this.resolution,
    required this.format,
    required this.quality,
    required this.capturedAt,
    required this.base64Image,
    this.downloadUrl,
    required this.settings,
    required this.metadata,
  });

  factory EnhancedSnapshotResult.fromJson(Map<String, dynamic> json) {
    final snapshotData = json['snapshot_data'] ?? {};
    final resolutionData = snapshotData['resolution'] ?? {};
    
    return EnhancedSnapshotResult(
      deviceId: json['device_id'] ?? '',
      filename: snapshotData['filename'] ?? '',
      fileSizeBytes: snapshotData['file_size_bytes'] ?? 0,
      resolution: CameraResolution.fromJson(resolutionData),
      format: snapshotData['format'] ?? 'JPEG',
      quality: snapshotData['quality'] ?? 95,
      capturedAt: snapshotData['captured_at'] ?? '',
      base64Image: json['base64_image'] ?? '',
      downloadUrl: json['download_url'],
      settings: SnapshotSettings.fromJson(snapshotData['settings'] ?? {}),
      metadata: snapshotData['metadata'] ?? {},
    );
  }

  /// Get formatted file size
  String get formattedFileSize {
    if (fileSizeBytes < 1024) return '$fileSizeBytes B';
    if (fileSizeBytes < 1024 * 1024) return '${(fileSizeBytes / 1024).toStringAsFixed(1)} KB';
    return '${(fileSizeBytes / (1024 * 1024)).toStringAsFixed(1)} MB';
  }

  /// Get resolution description
  String get resolutionDescription {
    final mp = resolution.megapixels;
    if (mp >= 12) return '${mp.toStringAsFixed(1)}MP - Professional Quality';
    if (mp >= 8) return '${mp.toStringAsFixed(1)}MP - High Quality';
    if (mp >= 5) return '${mp.toStringAsFixed(1)}MP - Good Quality';
    if (mp >= 2) return '${mp.toStringAsFixed(1)}MP - Standard Quality';
    return '${mp.toStringAsFixed(1)}MP - Basic Quality';
  }
}
