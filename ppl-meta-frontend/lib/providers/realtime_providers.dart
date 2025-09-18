import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../services/websocket_service.dart';

/// Provider for WebSocket service instance
final webSocketServiceProvider = Provider<WebSocketService>((ref) {
  return WebSocketService();
});

/// Provider for WebSocket connection status
final webSocketConnectionProvider = StreamProvider<WebSocketConnectionStatus>((ref) {
  final service = ref.watch(webSocketServiceProvider);
  return service.connectionStatus;
});

/// Provider for workflow progress updates
final workflowProgressProvider = StreamProvider<WorkflowProgressUpdate>((ref) {
  final service = ref.watch(webSocketServiceProvider);
  return service.subscribeToWorkflowProgress();
});

/// Provider for automation engine status updates
final automationStatusProvider = StreamProvider<AutomationEngineStatus>((ref) {
  final service = ref.watch(webSocketServiceProvider);
  return service.subscribeToAutomationStatus();
});

/// Provider for camera status updates
final cameraStatusProvider = StreamProvider<CameraStreamStatus>((ref) {
  final service = ref.watch(webSocketServiceProvider);
  return service.subscribeToCameraStatus();
});

/// Provider for face detection events
final faceDetectionEventsProvider = StreamProvider<FaceDetectionEvent>((ref) {
  final service = ref.watch(webSocketServiceProvider);
  return service.subscribeToFaceDetection();
});

/// Provider for system performance metrics
final performanceMetricsProvider = StreamProvider<SystemPerformanceMetrics>((ref) {
  final service = ref.watch(webSocketServiceProvider);
  return service.subscribeToPerformanceMetrics();
});

/// Provider for error notifications
final errorNotificationsProvider = StreamProvider<ErrorNotification>((ref) {
  final service = ref.watch(webSocketServiceProvider);
  return service.subscribeToErrors();
});

/// Provider for app notifications
final appNotificationsProvider = StreamProvider<AppNotification>((ref) {
  final service = ref.watch(webSocketServiceProvider);
  return service.subscribeToNotifications();
});

/// Provider for real-time workflow status by ID
final workflowStatusProvider = StreamProvider.family<WorkflowProgressUpdate?, String>((ref, workflowId) {
  final progressStream = ref.watch(workflowProgressProvider);
  
  return progressStream.when(
    data: (update) => Stream.value(update.workflowId == workflowId ? update : null),
    loading: () => const Stream.empty(),
    error: (error, stack) => Stream.error(error, stack),
  );
});

/// Provider for real-time camera status by ID
final cameraStreamStatusProvider = StreamProvider.family<CameraStreamStatus?, String>((ref, cameraId) {
  final statusStream = ref.watch(cameraStatusProvider);
  
  return statusStream.when(
    data: (status) => Stream.value(status.cameraId == cameraId ? status : null),
    loading: () => const Stream.empty(),
    error: (error, stack) => Stream.error(error, stack),
  );
});

/// Provider for aggregated face detection count
final faceDetectionCountProvider = StreamProvider<int>((ref) {
  final detectionStream = ref.watch(faceDetectionEventsProvider);
  int count = 0;
  
  return detectionStream.when(
    data: (event) {
      count++;
      return Stream.value(count);
    },
    loading: () => Stream.value(0),
    error: (error, stack) => Stream.value(0),
  );
});

/// Provider for real-time system health status
final systemHealthProvider = StreamProvider<SystemHealthStatus>((ref) {
  final metricsStream = ref.watch(performanceMetricsProvider);
  
  return metricsStream.when(
    data: (metrics) {
      final health = SystemHealthStatus.fromMetrics(metrics);
      return Stream.value(health);
    },
    loading: () => Stream.value(SystemHealthStatus.unknown()),
    error: (error, stack) => Stream.value(SystemHealthStatus.error()),
  );
});

/// System health status data class
class SystemHealthStatus {
  final HealthLevel level;
  final String message;
  final Map<String, dynamic> details;
  final DateTime timestamp;

  SystemHealthStatus({
    required this.level,
    required this.message,
    required this.details,
    required this.timestamp,
  });

  factory SystemHealthStatus.fromMetrics(SystemPerformanceMetrics metrics) {
    HealthLevel level;
    String message;
    
    final cpuHigh = metrics.cpuUsage > 80;
    final memoryHigh = metrics.memoryUsage > 80;
    final queueLong = metrics.queueLength > 50;
    
    if (cpuHigh || memoryHigh || queueLong) {
      level = HealthLevel.warning;
      message = 'System under high load';
    } else if (metrics.cpuUsage > 60 || metrics.memoryUsage > 60) {
      level = HealthLevel.caution;
      message = 'System performance moderate';
    } else {
      level = HealthLevel.healthy;
      message = 'System performing well';
    }
    
    return SystemHealthStatus(
      level: level,
      message: message,
      details: {
        'cpu_usage': metrics.cpuUsage,
        'memory_usage': metrics.memoryUsage,
        'queue_length': metrics.queueLength,
        'avg_processing_time': metrics.avgProcessingTime,
      },
      timestamp: metrics.timestamp,
    );
  }

  factory SystemHealthStatus.unknown() {
    return SystemHealthStatus(
      level: HealthLevel.unknown,
      message: 'System status unknown',
      details: {},
      timestamp: DateTime.now(),
    );
  }

  factory SystemHealthStatus.error() {
    return SystemHealthStatus(
      level: HealthLevel.error,
      message: 'Error getting system status',
      details: {},
      timestamp: DateTime.now(),
    );
  }
}

enum HealthLevel {
  healthy,
  caution,
  warning,
  error,
  unknown,
}