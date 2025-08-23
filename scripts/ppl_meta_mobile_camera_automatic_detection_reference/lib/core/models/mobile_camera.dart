/// Models for mobile camera functionality
class MobileCameraInfo {
  final String id;
  final String name;
  final String deviceName;
  final String deviceId;
  final String cameraType;
  final String status;
  final String connectionString;
  final String ipAddress;
  final int port;
  final String resolution;

  MobileCameraInfo({
    required this.id,
    required this.name,
    required this.deviceName,
    required this.deviceId,
    required this.cameraType,
    required this.status,
    required this.connectionString,
    required this.ipAddress,
    required this.port,
    required this.resolution,
  });

  factory MobileCameraInfo.fromRegistrationResponse(Map<String, dynamic> data) {
    return MobileCameraInfo(
      id: data['id']?.toString() ?? '',
      name: data['name'] ?? '',
      deviceName: data['device_name'] ?? data['name'] ?? '',
      deviceId: data['device_id'] ?? '',
      cameraType: data['camera_type'] ?? 'MOBILE',
      status: data['status'] ?? 'AVAILABLE',
      connectionString: data['connection_string'] ?? '',
      ipAddress: data['ip_address'] ?? '',
      port: data['port'] ?? 8554,
      resolution: data['resolution'] ?? '1920x1080',
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'device_name': deviceName,
      'device_id': deviceId,
      'camera_type': cameraType,
      'status': status,
      'connection_string': connectionString,
      'ip_address': ipAddress,
      'port': port,
      'resolution': resolution,
    };
  }
}

/// Configuration for mobile camera streaming
class StreamingConfig {
  final int width;
  final int height;
  final int fps;
  final int quality; // JPEG quality 1-100
  final String format; // 'mjpeg', 'h264', etc.
  final int port; // Streaming port
  
  // Compatibility getter for frameRate
  int get frameRate => fps;

  StreamingConfig({
    this.width = 1920,
    this.height = 1080,
    this.fps = 30,
    this.quality = 85,
    this.format = 'mjpeg',
    this.port = 8554,
  });

  StreamingConfig copyWith({
    int? width,
    int? height,
    int? fps,
    int? quality,
    String? format,
    int? port,
  }) {
    return StreamingConfig(
      width: width ?? this.width,
      height: height ?? this.height,
      fps: fps ?? this.fps,
      quality: quality ?? this.quality,
      format: format ?? this.format,
      port: port ?? this.port,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'width': width,
      'height': height,
      'fps': fps,
      'quality': quality,
      'format': format,
      'port': port,
    };
  }

  @override
  String toString() {
    return '${width}x${height} @ ${fps}fps (Q:$quality, $format)';
  }
}

/// Mobile camera status enum
enum MobileCameraStatus {
  offline,
  connecting,
  connected,
  registering,
  registered,
  available,
  streaming,
  error,
}

extension MobileCameraStatusExtension on MobileCameraStatus {
  String get displayName {
    switch (this) {
      case MobileCameraStatus.offline:
        return 'Offline';
      case MobileCameraStatus.connecting:
        return 'Connecting';
      case MobileCameraStatus.connected:
        return 'Connected';
      case MobileCameraStatus.registering:
        return 'Registering';
      case MobileCameraStatus.registered:
        return 'Registered';
      case MobileCameraStatus.available:
        return 'Available';
      case MobileCameraStatus.streaming:
        return 'Streaming';
      case MobileCameraStatus.error:
        return 'Error';
    }
  }

  String get apiValue {
    switch (this) {
      case MobileCameraStatus.offline:
        return 'OFFLINE';
      case MobileCameraStatus.connecting:
        return 'CONNECTING';
      case MobileCameraStatus.connected:
        return 'CONNECTED';
      case MobileCameraStatus.registering:
        return 'REGISTERING';
      case MobileCameraStatus.registered:
        return 'REGISTERED';
      case MobileCameraStatus.available:
        return 'AVAILABLE';
      case MobileCameraStatus.streaming:
        return 'STREAMING';
      case MobileCameraStatus.error:
        return 'ERROR';
    }
  }
}

/// Platform discovery result
class PlatformDiscoveryResult {
  final String ipAddress;
  final int port;
  final String baseUrl;
  final bool isReachable;
  final Duration? responseTime;
  final Map<String, dynamic>? healthData;

  PlatformDiscoveryResult({
    required this.ipAddress,
    required this.port,
    required this.baseUrl,
    required this.isReachable,
    this.responseTime,
    this.healthData,
  });

  factory PlatformDiscoveryResult.unreachable(String ipAddress, int port) {
    return PlatformDiscoveryResult(
      ipAddress: ipAddress,
      port: port,
      baseUrl: 'http://$ipAddress:$port',
      isReachable: false,
    );
  }

  factory PlatformDiscoveryResult.reachable({
    required String ipAddress,
    required int port,
    Duration? responseTime,
    Map<String, dynamic>? healthData,
  }) {
    return PlatformDiscoveryResult(
      ipAddress: ipAddress,
      port: port,
      baseUrl: 'http://$ipAddress:$port',
      isReachable: true,
      responseTime: responseTime,
      healthData: healthData,
    );
  }

  String get displayName {
    final time = responseTime != null ? ' (${responseTime!.inMilliseconds}ms)' : '';
    return '$ipAddress:$port$time';
  }
}

/// Streaming statistics
class StreamingStats {
  final int framesSent;
  final int framesDropped;
  final double averageFps;
  final double averageLatency;
  final int totalBytesSent;
  final DateTime startTime;
  final Duration uptime;

  // Compatibility getter for bytesTransferred
  int get bytesTransferred => totalBytesSent;

  StreamingStats({
    required this.framesSent,
    required this.framesDropped,
    required this.averageFps,
    required this.averageLatency,
    required this.totalBytesSent,
    required this.startTime,
    required this.uptime,
    int? bytesTransferred, // Accept but ignore, use totalBytesSent
  });

  double get dropRate {
    final total = framesSent + framesDropped;
    return total > 0 ? (framesDropped / total) * 100 : 0.0;
  }

  double get mbpsSent {
    final seconds = uptime.inSeconds;
    return seconds > 0 ? (totalBytesSent * 8 / 1000000) / seconds : 0.0;
  }

  Map<String, dynamic> toJson() {
    return {
      'frames_sent': framesSent,
      'frames_dropped': framesDropped,
      'average_fps': averageFps,
      'average_latency': averageLatency,
      'total_bytes_sent': totalBytesSent,
      'drop_rate': dropRate,
      'mbps_sent': mbpsSent,
      'uptime_seconds': uptime.inSeconds,
    };
  }
}
