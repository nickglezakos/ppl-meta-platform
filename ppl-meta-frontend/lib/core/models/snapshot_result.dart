import 'dart:convert';
import 'dart:typed_data';

/// Basic snapshot result model for Phase 1 implementation
class SnapshotResult {
  final String deviceId;
  final String base64Image;
  final DateTime capturedAt;
  final int? fileSizeBytes;
  final String? filename;
  final Map<String, dynamic>? metadata;

  const SnapshotResult({
    required this.deviceId,
    required this.base64Image,
    required this.capturedAt,
    this.fileSizeBytes,
    this.filename,
    this.metadata,
  });

  /// Create snapshot result from binary data (base64)
  factory SnapshotResult.fromBinary({
    required String deviceId,
    required String base64Image,
    String? filename,
    Map<String, dynamic>? metadata,
  }) {
    return SnapshotResult(
      deviceId: deviceId,
      base64Image: base64Image,
      capturedAt: DateTime.now(),
      fileSizeBytes: _calculateBase64Size(base64Image),
      filename: filename ?? 'snapshot_${DateTime.now().millisecondsSinceEpoch}.jpg',
      metadata: metadata ?? {},
    );
  }

  /// Create snapshot result from JSON response
  factory SnapshotResult.fromJson(Map<String, dynamic> json) {
    return SnapshotResult(
      deviceId: json['device_id'] ?? '',
      base64Image: json['base64_image'] ?? json['data'] ?? '',
      capturedAt: json['captured_at'] != null
          ? DateTime.tryParse(json['captured_at']) ?? DateTime.now()
          : DateTime.now(),
      fileSizeBytes: json['file_size_bytes'] as int?,
      filename: json['filename'],
      metadata: json['metadata'] as Map<String, dynamic>?,
    );
  }

  /// Convert to JSON for storage
  Map<String, dynamic> toJson() {
    return {
      'device_id': deviceId,
      'base64_image': base64Image,
      'captured_at': capturedAt.toIso8601String(),
      'file_size_bytes': fileSizeBytes,
      'filename': filename,
      'metadata': metadata,
    };
  }

  /// Get image data as Uint8List for display
  Uint8List get imageBytes {
    try {
      String base64Data = base64Image;
      
      // If the base64Image contains a data URL, extract just the base64 part
      if (base64Data.startsWith('data:image/')) {
        final colonIndex = base64Data.indexOf(',');
        if (colonIndex != -1) {
          base64Data = base64Data.substring(colonIndex + 1);
        }
      }
      
      return base64Decode(base64Data);
    } catch (e) {
      print('Error decoding base64 image: $e');
      print('Base64 data starts with: ${base64Image.substring(0, base64Image.length > 50 ? 50 : base64Image.length)}...');
      // Return empty bytes if decode fails
      return Uint8List(0);
    }
  }

  /// Get data URL for display in web widgets
  String get dataUrl {
    return 'data:image/jpeg;base64,$base64Image';
  }

  /// Compatibility properties for gallery widget
  String get id => '${deviceId}_${capturedAt.millisecondsSinceEpoch}';
  String get cameraId => deviceId;
  String get formattedTimestamp => formattedCaptureTime;

  /// Get formatted file size
  String get formattedFileSize {
    if (fileSizeBytes == null) return 'Unknown size';
    final bytes = fileSizeBytes!;
    if (bytes < 1024) return '$bytes B';
    if (bytes < 1024 * 1024) return '${(bytes / 1024).toStringAsFixed(1)} KB';
    return '${(bytes / (1024 * 1024)).toStringAsFixed(1)} MB';
  }

  /// Get human-readable capture time
  String get formattedCaptureTime {
    final now = DateTime.now();
    final difference = now.difference(capturedAt);
    
    if (difference.inMinutes < 1) {
      return 'Just now';
    } else if (difference.inHours < 1) {
      return '${difference.inMinutes}m ago';
    } else if (difference.inDays < 1) {
      return '${difference.inHours}h ago';
    } else if (difference.inDays < 7) {
      return '${difference.inDays}d ago';
    } else {
      return '${capturedAt.day}/${capturedAt.month}/${capturedAt.year}';
    }
  }

  /// Create a copy with updated fields
  SnapshotResult copyWith({
    String? deviceId,
    String? base64Image,
    DateTime? capturedAt,
    int? fileSizeBytes,
    String? filename,
    Map<String, dynamic>? metadata,
  }) {
    return SnapshotResult(
      deviceId: deviceId ?? this.deviceId,
      base64Image: base64Image ?? this.base64Image,
      capturedAt: capturedAt ?? this.capturedAt,
      fileSizeBytes: fileSizeBytes ?? this.fileSizeBytes,
      filename: filename ?? this.filename,
      metadata: metadata ?? this.metadata,
    );
  }

  /// Calculate approximate file size from base64 string
  static int _calculateBase64Size(String base64String) {
    // Base64 encoding increases size by ~33%
    // So decoded size = base64Length * 3/4
    return (base64String.length * 3 / 4).round();
  }

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    return other is SnapshotResult &&
        other.deviceId == deviceId &&
        other.base64Image == base64Image &&
        other.capturedAt == capturedAt;
  }

  @override
  int get hashCode {
    return Object.hash(deviceId, base64Image, capturedAt);
  }

  @override
  String toString() {
    return 'SnapshotResult(deviceId: $deviceId, filename: $filename, capturedAt: $capturedAt, size: $formattedFileSize)';
  }
}
