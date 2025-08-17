import 'dart:async';
import 'dart:math';
import 'package:flutter/foundation.dart';
import '../models/camera.dart';
import '../services/camera_service.dart';

/// Enumeration for camera connection health
enum ConnectionHealth {
  excellent,
  good,
  poor,
  critical,
  unknown,
}

/// Enumeration for monitoring mode to optimize battery usage
enum MonitoringMode {
  active,      // Active streaming: 2-second intervals
  idle,        // Idle connection: 10-second intervals
  background,  // Background mode: 30-second intervals
  disabled,    // No monitoring
}

/// Enhanced camera status with connection health and timing information
class CameraStatus {
  final String deviceId;
  final String connectionStatus;
  final String streamStatus;
  final DateTime lastUpdated;
  final DateTime? lastSeen;
  final DateTime? sessionStartedAt;
  final Duration? sessionDuration;
  final ConnectionHealth connectionHealth;
  final int? latencyMs;
  final bool isReconnecting;
  final int reconnectAttempts;
  final String? errorMessage;
  final Map<String, dynamic>? streamInfo;
  final double? dataTransferredMb;
  final int? fps;
  final String? resolution;

  const CameraStatus({
    required this.deviceId,
    required this.connectionStatus,
    required this.streamStatus,
    required this.lastUpdated,
    this.lastSeen,
    this.sessionStartedAt,
    this.sessionDuration,
    this.connectionHealth = ConnectionHealth.unknown,
    this.latencyMs,
    this.isReconnecting = false,
    this.reconnectAttempts = 0,
    this.errorMessage,
    this.streamInfo,
    this.dataTransferredMb,
    this.fps,
    this.resolution,
  });

  bool get isConnected => connectionStatus.toLowerCase() == 'connected';
  bool get isStreaming => streamStatus.toLowerCase() == 'active';
  bool get hasError => connectionStatus.toLowerCase() == 'error' || errorMessage != null;
  bool get isHealthy => connectionHealth == ConnectionHealth.excellent || connectionHealth == ConnectionHealth.good;

  /// Get connection health based on latency and status
  static ConnectionHealth calculateConnectionHealth(int? latencyMs, String connectionStatus, String streamStatus) {
    if (connectionStatus.toLowerCase() == 'error' || streamStatus.toLowerCase() == 'error') {
      return ConnectionHealth.critical;
    }
    
    if (connectionStatus.toLowerCase() != 'connected') {
      return ConnectionHealth.unknown;
    }

    if (latencyMs == null) return ConnectionHealth.unknown;
    
    if (latencyMs <= 50) return ConnectionHealth.excellent;
    if (latencyMs <= 150) return ConnectionHealth.good;
    if (latencyMs <= 500) return ConnectionHealth.poor;
    return ConnectionHealth.critical;
  }

  factory CameraStatus.fromJson(Map<String, dynamic> json) {
    final latencyMs = json['latency_ms'] as int?;
    final connectionStatus = json['connection_status']?.toString() ?? 'unknown';
    final streamStatus = json['stream_status']?.toString() ?? 'inactive';
    
    return CameraStatus(
      deviceId: json['device_id']?.toString() ?? '',
      connectionStatus: connectionStatus,
      streamStatus: streamStatus,
      lastUpdated: DateTime.tryParse(json['last_updated']?.toString() ?? '') ?? DateTime.now(),
      lastSeen: json['last_seen'] != null ? DateTime.tryParse(json['last_seen'].toString()) : null,
      sessionStartedAt: json['session_started_at'] != null ? DateTime.tryParse(json['session_started_at'].toString()) : null,
      sessionDuration: json['session_duration_seconds'] != null 
          ? Duration(seconds: json['session_duration_seconds'] as int) : null,
      connectionHealth: calculateConnectionHealth(latencyMs, connectionStatus, streamStatus),
      latencyMs: latencyMs,
      isReconnecting: json['is_reconnecting'] ?? false,
      reconnectAttempts: json['reconnect_attempts'] ?? 0,
      errorMessage: json['error_message']?.toString(),
      streamInfo: json['stream_info'] as Map<String, dynamic>?,
      dataTransferredMb: (json['data_transferred_mb'] as num?)?.toDouble(),
      fps: json['fps'] as int?,
      resolution: json['resolution']?.toString(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'device_id': deviceId,
      'connection_status': connectionStatus,
      'stream_status': streamStatus,
      'last_updated': lastUpdated.toIso8601String(),
      'last_seen': lastSeen?.toIso8601String(),
      'session_started_at': sessionStartedAt?.toIso8601String(),
      'session_duration_seconds': sessionDuration?.inSeconds,
      'connection_health': connectionHealth.name,
      'latency_ms': latencyMs,
      'is_reconnecting': isReconnecting,
      'reconnect_attempts': reconnectAttempts,
      'error_message': errorMessage,
      'stream_info': streamInfo,
      'data_transferred_mb': dataTransferredMb,
      'fps': fps,
      'resolution': resolution,
    };
  }

  CameraStatus copyWith({
    String? deviceId,
    String? connectionStatus,
    String? streamStatus,
    DateTime? lastUpdated,
    DateTime? lastSeen,
    DateTime? sessionStartedAt,
    Duration? sessionDuration,
    ConnectionHealth? connectionHealth,
    int? latencyMs,
    bool? isReconnecting,
    int? reconnectAttempts,
    String? errorMessage,
    Map<String, dynamic>? streamInfo,
    double? dataTransferredMb,
    int? fps,
    String? resolution,
  }) {
    return CameraStatus(
      deviceId: deviceId ?? this.deviceId,
      connectionStatus: connectionStatus ?? this.connectionStatus,
      streamStatus: streamStatus ?? this.streamStatus,
      lastUpdated: lastUpdated ?? this.lastUpdated,
      lastSeen: lastSeen ?? this.lastSeen,
      sessionStartedAt: sessionStartedAt ?? this.sessionStartedAt,
      sessionDuration: sessionDuration ?? this.sessionDuration,
      connectionHealth: connectionHealth ?? this.connectionHealth,
      latencyMs: latencyMs ?? this.latencyMs,
      isReconnecting: isReconnecting ?? this.isReconnecting,
      reconnectAttempts: reconnectAttempts ?? this.reconnectAttempts,
      errorMessage: errorMessage ?? this.errorMessage,
      streamInfo: streamInfo ?? this.streamInfo,
      dataTransferredMb: dataTransferredMb ?? this.dataTransferredMb,
      fps: fps ?? this.fps,
      resolution: resolution ?? this.resolution,
    );
  }
}

/// Real-time camera status monitoring service
class CameraStatusMonitor {
  final CameraService _cameraService;
  final Map<String, Timer> _statusTimers = {};
  final Map<String, StreamController<CameraStatus>> _statusControllers = {};
  final Map<String, CameraStatus> _lastKnownStatus = {};
  final Map<String, MonitoringMode> _monitoringModes = {};
  final Map<String, int> _reconnectAttempts = {};
  final Map<String, DateTime> _lastHealthChecks = {};

  static const Duration _baseRetryDelay = Duration(seconds: 1);
  static const int _maxReconnectAttempts = 3;

  CameraStatusMonitor(this._cameraService);

  /// Start monitoring a specific camera
  void startMonitoring(String deviceId, {MonitoringMode mode = MonitoringMode.active}) {
    debugPrint('🔄 Starting camera status monitoring for $deviceId with mode: $mode');
    
    // Stop existing monitoring for this device
    stopMonitoring(deviceId);
    
    // Set monitoring mode
    _monitoringModes[deviceId] = mode;
    
    // Create status stream controller
    _statusControllers[deviceId] = StreamController<CameraStatus>.broadcast();
    
    // Reset reconnect attempts
    _reconnectAttempts[deviceId] = 0;
    
    // Start monitoring based on mode
    _scheduleStatusCheck(deviceId);
  }

  /// Stop monitoring a specific camera
  void stopMonitoring(String deviceId) {
    debugPrint('⏹️ Stopping camera status monitoring for $deviceId');
    
    // Cancel timer
    _statusTimers[deviceId]?.cancel();
    _statusTimers.remove(deviceId);
    
    // Close stream controller
    _statusControllers[deviceId]?.close();
    _statusControllers.remove(deviceId);
    
    // Clean up state
    _lastKnownStatus.remove(deviceId);
    _monitoringModes.remove(deviceId);
    _reconnectAttempts.remove(deviceId);
    _lastHealthChecks.remove(deviceId);
  }

  /// Stop monitoring all cameras
  void stopAllMonitoring() {
    final deviceIds = List<String>.from(_statusTimers.keys);
    for (final deviceId in deviceIds) {
      stopMonitoring(deviceId);
    }
  }

  /// Get status stream for a specific camera
  Stream<CameraStatus>? getStatusStream(String deviceId) {
    return _statusControllers[deviceId]?.stream;
  }

  /// Get last known status for a camera
  CameraStatus? getLastKnownStatus(String deviceId) {
    return _lastKnownStatus[deviceId];
  }

  /// Update monitoring mode for a camera
  void updateMonitoringMode(String deviceId, MonitoringMode mode) {
    if (_monitoringModes[deviceId] != mode) {
      debugPrint('🔄 Updating monitoring mode for $deviceId: ${_monitoringModes[deviceId]} → $mode');
      _monitoringModes[deviceId] = mode;
      
      // Reschedule with new interval
      if (_statusTimers.containsKey(deviceId)) {
        _scheduleStatusCheck(deviceId);
      }
    }
  }

  /// Schedule the next status check based on monitoring mode
  void _scheduleStatusCheck(String deviceId) {
    // Cancel existing timer
    _statusTimers[deviceId]?.cancel();
    
    final mode = _monitoringModes[deviceId] ?? MonitoringMode.active;
    Duration interval;
    
    switch (mode) {
      case MonitoringMode.active:
        interval = const Duration(seconds: 2);
        break;
      case MonitoringMode.idle:
        interval = const Duration(seconds: 10);
        break;
      case MonitoringMode.background:
        interval = const Duration(seconds: 30);
        break;
      case MonitoringMode.disabled:
        return; // Don't schedule if disabled
    }

    _statusTimers[deviceId] = Timer(interval, () => _performStatusCheck(deviceId));
  }

  /// Perform a status check for a specific camera
  Future<void> _performStatusCheck(String deviceId) async {
    try {
      final stopwatch = Stopwatch()..start();
      final status = await checkCameraStatus(deviceId);
      stopwatch.stop();

      // Update latency information
      final enhancedStatus = status.copyWith(
        latencyMs: stopwatch.elapsedMilliseconds,
        lastUpdated: DateTime.now(),
      );

      // Update last known status
      _lastKnownStatus[deviceId] = enhancedStatus;
      _lastHealthChecks[deviceId] = DateTime.now();

      // Reset reconnect attempts on successful check
      if (enhancedStatus.isConnected && !enhancedStatus.hasError) {
        _reconnectAttempts[deviceId] = 0;
      }

      // Emit status update
      if (_statusControllers.containsKey(deviceId) && !_statusControllers[deviceId]!.isClosed) {
        _statusControllers[deviceId]!.add(enhancedStatus);
      }

      // Schedule next check
      _scheduleStatusCheck(deviceId);

    } catch (error) {
      debugPrint('❌ Status check failed for $deviceId: $error');
      await _handleStatusCheckError(deviceId, error.toString());
    }
  }

  /// Handle status check errors with exponential backoff retry
  Future<void> _handleStatusCheckError(String deviceId, String errorMessage) async {
    final currentAttempts = _reconnectAttempts[deviceId] ?? 0;
    _reconnectAttempts[deviceId] = currentAttempts + 1;

    final errorStatus = CameraStatus(
      deviceId: deviceId,
      connectionStatus: 'error',
      streamStatus: 'error',
      lastUpdated: DateTime.now(),
      connectionHealth: ConnectionHealth.critical,
      isReconnecting: currentAttempts < _maxReconnectAttempts,
      reconnectAttempts: currentAttempts + 1,
      errorMessage: errorMessage,
    );

    // Update last known status
    _lastKnownStatus[deviceId] = errorStatus;

    // Emit error status
    if (_statusControllers.containsKey(deviceId) && !_statusControllers[deviceId]!.isClosed) {
      _statusControllers[deviceId]!.add(errorStatus);
    }

    // Schedule retry with exponential backoff if under retry limit
    if (currentAttempts < _maxReconnectAttempts) {
      final retryDelay = Duration(
        milliseconds: _baseRetryDelay.inMilliseconds * pow(2, currentAttempts).toInt(),
      );
      
      debugPrint('🔄 Scheduling retry ${currentAttempts + 1}/$_maxReconnectAttempts for $deviceId in ${retryDelay.inSeconds}s');
      
      _statusTimers[deviceId] = Timer(retryDelay, () => _performStatusCheck(deviceId));
    } else {
      debugPrint('❌ Max reconnect attempts reached for $deviceId');
      // Schedule regular check after max attempts
      _scheduleStatusCheck(deviceId);
    }
  }

  /// Check camera status with enhanced information
  Future<CameraStatus> checkCameraStatus(String deviceId) async {
    try {
      // Get basic streaming status
      final streamingStatus = await _cameraService.getStreamingStatus(deviceId);
      
      // Calculate session duration if streaming
      Duration? sessionDuration;
      if (streamingStatus.startedAt != null) {
        sessionDuration = DateTime.now().difference(streamingStatus.startedAt!);
      }

      // Get additional camera information
      final cameras = await _cameraService.getCameras();
      final camera = cameras.firstWhere(
        (c) => c.deviceId == deviceId || c.id == deviceId,
        orElse: () => Camera(
          id: deviceId,
          name: 'Unknown Camera',
          deviceId: deviceId,
          status: 'unknown',
          isActive: false,
        ),
      );

      return CameraStatus(
        deviceId: deviceId,
        connectionStatus: camera.status,
        streamStatus: streamingStatus.streamStatus,
        lastUpdated: DateTime.now(),
        lastSeen: camera.lastSeen,
        sessionStartedAt: streamingStatus.startedAt,
        sessionDuration: sessionDuration,
        streamInfo: streamingStatus.currentSettings,
        dataTransferredMb: streamingStatus.dataTransferredMb,
        fps: streamingStatus.currentSettings?['fps'] as int?,
        resolution: streamingStatus.currentSettings?['resolution']?.toString(),
      );
    } catch (e) {
      throw Exception('Failed to check camera status: $e');
    }
  }

  /// Get monitoring statistics for all cameras
  Map<String, Map<String, dynamic>> getMonitoringStats() {
    final stats = <String, Map<String, dynamic>>{};
    
    for (final deviceId in _statusControllers.keys) {
      final lastStatus = _lastKnownStatus[deviceId];
      final mode = _monitoringModes[deviceId];
      final lastHealthCheck = _lastHealthChecks[deviceId];
      
      stats[deviceId] = {
        'monitoring_mode': mode?.name,
        'last_health_check': lastHealthCheck?.toIso8601String(),
        'reconnect_attempts': _reconnectAttempts[deviceId] ?? 0,
        'is_monitoring': _statusTimers.containsKey(deviceId),
        'connection_health': lastStatus?.connectionHealth.name,
        'latency_ms': lastStatus?.latencyMs,
        'session_duration_minutes': lastStatus?.sessionDuration?.inMinutes,
      };
    }
    
    return stats;
  }

  /// Dispose all resources
  void dispose() {
    debugPrint('🧹 Disposing CameraStatusMonitor');
    stopAllMonitoring();
  }
}
