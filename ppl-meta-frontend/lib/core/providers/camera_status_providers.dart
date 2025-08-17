import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter/foundation.dart';
import '../services/camera_status_monitor.dart';
import '../services/camera_service.dart';
import 'camera_providers.dart';

/// Provider for camera status monitor service
final cameraStatusMonitorProvider = Provider<CameraStatusMonitor>((ref) {
  final cameraService = ref.watch(cameraServiceProvider);
  return CameraStatusMonitor(cameraService);
});

/// Provider for camera status stream for a specific device
final cameraStatusStreamProvider = StreamProvider.family<CameraStatus, String>((ref, deviceId) {
  final monitor = ref.watch(cameraStatusMonitorProvider);
  
  // Get the stream, or return empty stream if not monitoring
  final stream = monitor.getStatusStream(deviceId);
  if (stream == null) {
    return Stream.value(CameraStatus(
      deviceId: deviceId,
      connectionStatus: 'unknown',
      streamStatus: 'inactive',
      lastUpdated: DateTime.now(),
    ));
  }
  
  return stream;
});

/// Provider for last known camera status
final lastKnownCameraStatusProvider = Provider.family<CameraStatus?, String>((ref, deviceId) {
  final monitor = ref.watch(cameraStatusMonitorProvider);
  return monitor.getLastKnownStatus(deviceId);
});

/// Provider for monitoring statistics
final monitoringStatsProvider = Provider<Map<String, Map<String, dynamic>>>((ref) {
  final monitor = ref.watch(cameraStatusMonitorProvider);
  return monitor.getMonitoringStats();
});

/// State notifier for managing camera monitoring sessions
class CameraMonitoringNotifier extends StateNotifier<Map<String, MonitoringMode>> {
  final CameraStatusMonitor _monitor;
  final Ref _ref;

  CameraMonitoringNotifier(this._monitor, this._ref) : super({});

  /// Start monitoring a camera with the specified mode
  void startMonitoring(String deviceId, {MonitoringMode mode = MonitoringMode.active}) {
    debugPrint('🔄 CameraMonitoringNotifier: Starting monitoring for $deviceId with mode: $mode');
    
    _monitor.startMonitoring(deviceId, mode: mode);
    state = {...state, deviceId: mode};
  }

  /// Stop monitoring a camera
  void stopMonitoring(String deviceId) {
    debugPrint('⏹️ CameraMonitoringNotifier: Stopping monitoring for $deviceId');
    
    _monitor.stopMonitoring(deviceId);
    final newState = Map<String, MonitoringMode>.from(state);
    newState.remove(deviceId);
    state = newState;
  }

  /// Update monitoring mode for a camera
  void updateMonitoringMode(String deviceId, MonitoringMode mode) {
    debugPrint('🔄 CameraMonitoringNotifier: Updating mode for $deviceId to $mode');
    
    if (state.containsKey(deviceId)) {
      _monitor.updateMonitoringMode(deviceId, mode);
      state = {...state, deviceId: mode};
    }
  }

  /// Start monitoring multiple cameras
  void startMonitoringMultiple(List<String> deviceIds, {MonitoringMode mode = MonitoringMode.active}) {
    final newState = Map<String, MonitoringMode>.from(state);
    
    for (final deviceId in deviceIds) {
      _monitor.startMonitoring(deviceId, mode: mode);
      newState[deviceId] = mode;
    }
    
    state = newState;
  }

  /// Stop all monitoring
  void stopAllMonitoring() {
    debugPrint('⏹️ CameraMonitoringNotifier: Stopping all monitoring');
    
    _monitor.stopAllMonitoring();
    state = {};
  }

  /// Check if a camera is being monitored
  bool isMonitoring(String deviceId) {
    return state.containsKey(deviceId);
  }

  /// Get current monitoring mode for a camera
  MonitoringMode? getMonitoringMode(String deviceId) {
    return state[deviceId];
  }

  /// Optimize monitoring based on app lifecycle
  void optimizeForBackground() {
    debugPrint('🔋 CameraMonitoringNotifier: Optimizing for background mode');
    
    final newState = <String, MonitoringMode>{};
    for (final entry in state.entries) {
      final deviceId = entry.key;
      final currentMode = entry.value;
      
      // Only downgrade if not already in background mode
      if (currentMode != MonitoringMode.background && currentMode != MonitoringMode.disabled) {
        _monitor.updateMonitoringMode(deviceId, MonitoringMode.background);
        newState[deviceId] = MonitoringMode.background;
      } else {
        newState[deviceId] = currentMode;
      }
    }
    state = newState;
  }

  /// Restore monitoring for foreground
  void optimizeForForeground() {
    debugPrint('📱 CameraMonitoringNotifier: Optimizing for foreground mode');
    
    final newState = <String, MonitoringMode>{};
    for (final entry in state.entries) {
      final deviceId = entry.key;
      final currentMode = entry.value;
      
      // Upgrade background mode to active for better responsiveness
      if (currentMode == MonitoringMode.background) {
        _monitor.updateMonitoringMode(deviceId, MonitoringMode.active);
        newState[deviceId] = MonitoringMode.active;
      } else {
        newState[deviceId] = currentMode;
      }
    }
    state = newState;
  }

  /// Dispose resources
  @override
  void dispose() {
    _monitor.dispose();
    super.dispose();
  }
}

/// Provider for camera monitoring state management
final cameraMonitoringProvider = StateNotifierProvider<CameraMonitoringNotifier, Map<String, MonitoringMode>>((ref) {
  final monitor = ref.watch(cameraStatusMonitorProvider);
  return CameraMonitoringNotifier(monitor, ref);
});

/// Provider for checking if a specific camera is being monitored
final isCameraMonitoredProvider = Provider.family<bool, String>((ref, deviceId) {
  final monitoringState = ref.watch(cameraMonitoringProvider);
  return monitoringState.containsKey(deviceId);
});

/// Provider for getting monitoring mode of a specific camera
final cameraMonitoringModeProvider = Provider.family<MonitoringMode?, String>((ref, deviceId) {
  final monitoringState = ref.watch(cameraMonitoringProvider);
  return monitoringState[deviceId];
});

/// Provider for connection health summary across all monitored cameras
final connectionHealthSummaryProvider = Provider<Map<ConnectionHealth, int>>((ref) {
  final stats = ref.watch(monitoringStatsProvider);
  final healthCounts = <ConnectionHealth, int>{
    ConnectionHealth.excellent: 0,
    ConnectionHealth.good: 0,
    ConnectionHealth.poor: 0,
    ConnectionHealth.critical: 0,
    ConnectionHealth.unknown: 0,
  };

  for (final deviceStats in stats.values) {
    final healthName = deviceStats['connection_health'] as String?;
    if (healthName != null) {
      final health = ConnectionHealth.values.firstWhere(
        (h) => h.name == healthName,
        orElse: () => ConnectionHealth.unknown,
      );
      healthCounts[health] = (healthCounts[health] ?? 0) + 1;
    }
  }

  return healthCounts;
});

/// Provider for active monitoring count
final activeMonitoringCountProvider = Provider<int>((ref) {
  final monitoringState = ref.watch(cameraMonitoringProvider);
  return monitoringState.length;
});

/// Provider to check if any monitoring is enabled
final isMonitoringEnabledProvider = Provider<bool>((ref) {
  final activeCount = ref.watch(activeMonitoringCountProvider);
  return activeCount > 0;
});

/// Provider for cameras with connection issues
final camerasWithIssuesProvider = Provider<List<String>>((ref) {
  final stats = ref.watch(monitoringStatsProvider);
  final camerasWithIssues = <String>[];

  for (final entry in stats.entries) {
    final deviceId = entry.key;
    final deviceStats = entry.value;
    
    final healthName = deviceStats['connection_health'] as String?;
    final reconnectAttempts = deviceStats['reconnect_attempts'] as int? ?? 0;
    
    if (healthName != null) {
      final health = ConnectionHealth.values.firstWhere(
        (h) => h.name == healthName,
        orElse: () => ConnectionHealth.unknown,
      );
      
      if (health == ConnectionHealth.critical || 
          health == ConnectionHealth.poor || 
          reconnectAttempts > 0) {
        camerasWithIssues.add(deviceId);
      }
    }
  }

  return camerasWithIssues;
});

/// Provider for monitoring performance metrics
final monitoringPerformanceProvider = Provider<Map<String, dynamic>>((ref) {
  final stats = ref.watch(monitoringStatsProvider);
  
  int totalCameras = stats.length;
  int healthyCameras = 0;
  int totalReconnectAttempts = 0;
  double averageLatency = 0.0;
  int latencyCount = 0;

  for (final deviceStats in stats.values) {
    // Count healthy cameras
    final healthName = deviceStats['connection_health'] as String?;
    if (healthName == ConnectionHealth.excellent.name || healthName == ConnectionHealth.good.name) {
      healthyCameras++;
    }
    
    // Sum reconnect attempts
    totalReconnectAttempts += (deviceStats['reconnect_attempts'] as int? ?? 0);
    
    // Calculate average latency
    final latency = deviceStats['latency_ms'] as int?;
    if (latency != null) {
      averageLatency += latency;
      latencyCount++;
    }
  }

  if (latencyCount > 0) {
    averageLatency /= latencyCount;
  }

  return {
    'total_cameras': totalCameras,
    'healthy_cameras': healthyCameras,
    'health_percentage': totalCameras > 0 ? (healthyCameras / totalCameras * 100).round() : 0,
    'total_reconnect_attempts': totalReconnectAttempts,
    'average_latency_ms': averageLatency.round(),
    'cameras_with_issues': stats.length - healthyCameras,
  };
});
