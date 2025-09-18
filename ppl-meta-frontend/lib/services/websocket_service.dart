import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:web_socket_channel/io.dart';

/// WebSocket service for real-time updates from the backend
/// Manages connections for workflow progress, automation status, camera streams, and events
class WebSocketService {
  static final WebSocketService _instance = WebSocketService._internal();
  factory WebSocketService() => _instance;
  WebSocketService._internal();

  WebSocketChannel? _channel;
  final Map<String, StreamController<Map<String, dynamic>>> _topicControllers = {};
  final Map<String, StreamSubscription> _subscriptions = {};
  
  bool _isConnected = false;
  bool _isReconnecting = false;
  Timer? _heartbeatTimer;
  Timer? _reconnectTimer;
  
  final Duration _heartbeatInterval = const Duration(seconds: 30);
  final Duration _reconnectDelay = const Duration(seconds: 5);
  final int _maxReconnectAttempts = 5;
  int _reconnectAttempts = 0;

  String? _baseUrl;
  String? _authToken;

  // Connection status stream
  final StreamController<WebSocketConnectionStatus> _connectionController = 
      StreamController<WebSocketConnectionStatus>.broadcast();
  Stream<WebSocketConnectionStatus> get connectionStatus => _connectionController.stream;

  /// Initialize WebSocket connection
  Future<void> initialize({
    required String baseUrl,
    String? authToken,
  }) async {
    _baseUrl = baseUrl;
    _authToken = authToken;
    
    await _connect();
  }

  /// Connect to WebSocket server
  Future<void> _connect() async {
    if (_isConnected || _isReconnecting) return;

    try {
      _isReconnecting = true;
      _connectionController.add(WebSocketConnectionStatus.connecting);

      final wsUrl = _baseUrl!.replaceFirst('http', 'ws') + '/ws';
      final uri = Uri.parse(wsUrl);
      
      if (kIsWeb) {
        // Use web-compatible WebSocket
        _channel = WebSocketChannel.connect(uri);
      } else {
        // Use IO WebSocket with headers for authentication
        _channel = IOWebSocketChannel.connect(
          uri,
          headers: _authToken != null ? {'Authorization': 'Bearer $_authToken'} : null,
        );
      }

      // Listen to WebSocket messages
      _channel!.stream.listen(
        _handleMessage,
        onError: _handleError,
        onDone: _handleDisconnection,
      );

      _isConnected = true;
      _isReconnecting = false;
      _reconnectAttempts = 0;
      
      _connectionController.add(WebSocketConnectionStatus.connected);
      _startHeartbeat();

      if (kDebugMode) {
        print('WebSocket connected successfully');
      }
    } catch (e) {
      _isReconnecting = false;
      _connectionController.add(WebSocketConnectionStatus.error);
      
      if (kDebugMode) {
        print('WebSocket connection error: $e');
      }
      
      _scheduleReconnect();
    }
  }

  /// Handle incoming WebSocket messages
  void _handleMessage(dynamic message) {
    try {
      final data = jsonDecode(message) as Map<String, dynamic>;
      final topic = data['topic'] as String?;
      
      if (topic == 'heartbeat') {
        _handleHeartbeat(data);
        return;
      }
      
      if (topic != null && _topicControllers.containsKey(topic)) {
        _topicControllers[topic]!.add(data);
      }
      
      // Broadcast to all topic listeners for wildcard subscriptions
      for (final controller in _topicControllers.values) {
        if (!controller.isClosed) {
          controller.add(data);
        }
      }
    } catch (e) {
      if (kDebugMode) {
        print('Error parsing WebSocket message: $e');
      }
    }
  }

  /// Handle WebSocket errors
  void _handleError(dynamic error) {
    if (kDebugMode) {
      print('WebSocket error: $error');
    }
    
    _connectionController.add(WebSocketConnectionStatus.error);
    _scheduleReconnect();
  }

  /// Handle WebSocket disconnection
  void _handleDisconnection() {
    _isConnected = false;
    _stopHeartbeat();
    
    _connectionController.add(WebSocketConnectionStatus.disconnected);
    
    if (kDebugMode) {
      print('WebSocket disconnected');
    }
    
    _scheduleReconnect();
  }

  /// Handle heartbeat messages
  void _handleHeartbeat(Map<String, dynamic> data) {
    // Send heartbeat response
    _sendMessage({
      'type': 'heartbeat_response',
      'timestamp': DateTime.now().millisecondsSinceEpoch,
    });
  }

  /// Start heartbeat timer
  void _startHeartbeat() {
    _heartbeatTimer?.cancel();
    _heartbeatTimer = Timer.periodic(_heartbeatInterval, (timer) {
      if (_isConnected) {
        _sendMessage({
          'type': 'heartbeat',
          'timestamp': DateTime.now().millisecondsSinceEpoch,
        });
      }
    });
  }

  /// Stop heartbeat timer
  void _stopHeartbeat() {
    _heartbeatTimer?.cancel();
    _heartbeatTimer = null;
  }

  /// Schedule reconnection attempt
  void _scheduleReconnect() {
    if (_reconnectAttempts >= _maxReconnectAttempts) {
      _connectionController.add(WebSocketConnectionStatus.failed);
      return;
    }

    _reconnectAttempts++;
    _reconnectTimer?.cancel();
    
    _reconnectTimer = Timer(_reconnectDelay, () {
      if (!_isConnected) {
        _connect();
      }
    });
  }

  /// Send message to WebSocket server
  void _sendMessage(Map<String, dynamic> message) {
    if (_isConnected && _channel != null) {
      try {
        _channel!.sink.add(jsonEncode(message));
      } catch (e) {
        if (kDebugMode) {
          print('Error sending WebSocket message: $e');
        }
      }
    }
  }

  /// Subscribe to a specific topic
  Stream<Map<String, dynamic>> subscribe(String topic) {
    if (!_topicControllers.containsKey(topic)) {
      _topicControllers[topic] = StreamController<Map<String, dynamic>>.broadcast();
    }

    // Send subscription message to server
    _sendMessage({
      'type': 'subscribe',
      'topic': topic,
      'timestamp': DateTime.now().millisecondsSinceEpoch,
    });

    return _topicControllers[topic]!.stream.where((data) {
      return data['topic'] == topic;
    });
  }

  /// Unsubscribe from a topic
  void unsubscribe(String topic) {
    _sendMessage({
      'type': 'unsubscribe',
      'topic': topic,
      'timestamp': DateTime.now().millisecondsSinceEpoch,
    });

    _topicControllers[topic]?.close();
    _topicControllers.remove(topic);
  }

  /// Subscribe to workflow progress updates
  Stream<WorkflowProgressUpdate> subscribeToWorkflowProgress() {
    return subscribe('workflow_progress').map((data) {
      return WorkflowProgressUpdate.fromJson(data);
    });
  }

  /// Subscribe to automation engine status
  Stream<AutomationEngineStatus> subscribeToAutomationStatus() {
    return subscribe('automation_status').map((data) {
      return AutomationEngineStatus.fromJson(data);
    });
  }

  /// Subscribe to camera stream status updates
  Stream<CameraStreamStatus> subscribeToCameraStatus() {
    return subscribe('camera_status').map((data) {
      return CameraStreamStatus.fromJson(data);
    });
  }

  /// Subscribe to face detection events
  Stream<FaceDetectionEvent> subscribeToFaceDetection() {
    return subscribe('face_detection').map((data) {
      return FaceDetectionEvent.fromJson(data);
    });
  }

  /// Subscribe to system performance metrics
  Stream<SystemPerformanceMetrics> subscribeToPerformanceMetrics() {
    return subscribe('performance_metrics').map((data) {
      return SystemPerformanceMetrics.fromJson(data);
    });
  }

  /// Subscribe to error notifications
  Stream<ErrorNotification> subscribeToErrors() {
    return subscribe('errors').map((data) {
      return ErrorNotification.fromJson(data);
    });
  }

  /// Subscribe to general notifications
  Stream<AppNotification> subscribeToNotifications() {
    return subscribe('notifications').map((data) {
      return AppNotification.fromJson(data);
    });
  }

  /// Send workflow command
  void sendWorkflowCommand(String workflowId, WorkflowCommand command) {
    _sendMessage({
      'type': 'workflow_command',
      'workflow_id': workflowId,
      'command': command.toJson(),
      'timestamp': DateTime.now().millisecondsSinceEpoch,
    });
  }

  /// Send automation rule command
  void sendAutomationCommand(String ruleId, AutomationCommand command) {
    _sendMessage({
      'type': 'automation_command',
      'rule_id': ruleId,
      'command': command.toJson(),
      'timestamp': DateTime.now().millisecondsSinceEpoch,
    });
  }

  /// Send camera control command
  void sendCameraCommand(String cameraId, CameraCommand command) {
    _sendMessage({
      'type': 'camera_command',
      'camera_id': cameraId,
      'command': command.toJson(),
      'timestamp': DateTime.now().millisecondsSinceEpoch,
    });
  }

  /// Update authentication token
  void updateAuthToken(String token) {
    _authToken = token;
    
    _sendMessage({
      'type': 'auth_update',
      'token': token,
      'timestamp': DateTime.now().millisecondsSinceEpoch,
    });
  }

  /// Disconnect from WebSocket
  Future<void> disconnect() async {
    _stopHeartbeat();
    _reconnectTimer?.cancel();
    
    // Close all topic controllers
    for (final controller in _topicControllers.values) {
      await controller.close();
    }
    _topicControllers.clear();

    if (_channel != null) {
      await _channel!.sink.close();
      _channel = null;
    }

    _isConnected = false;
    _connectionController.add(WebSocketConnectionStatus.disconnected);
  }

  /// Check if WebSocket is connected
  bool get isConnected => _isConnected;

  /// Get current connection status
  WebSocketConnectionStatus get currentStatus {
    if (_isConnected) return WebSocketConnectionStatus.connected;
    if (_isReconnecting) return WebSocketConnectionStatus.connecting;
    return WebSocketConnectionStatus.disconnected;
  }

  /// Dispose the service
  Future<void> dispose() async {
    await disconnect();
    await _connectionController.close();
  }
}

/// WebSocket connection status enumeration
enum WebSocketConnectionStatus {
  disconnected,
  connecting,
  connected,
  error,
  failed,
}

/// Workflow progress update data class
class WorkflowProgressUpdate {
  final String workflowId;
  final String status;
  final double progress;
  final String? currentStep;
  final Map<String, dynamic>? metadata;
  final DateTime timestamp;

  WorkflowProgressUpdate({
    required this.workflowId,
    required this.status,
    required this.progress,
    this.currentStep,
    this.metadata,
    required this.timestamp,
  });

  factory WorkflowProgressUpdate.fromJson(Map<String, dynamic> json) {
    return WorkflowProgressUpdate(
      workflowId: json['workflow_id'],
      status: json['status'],
      progress: json['progress']?.toDouble() ?? 0.0,
      currentStep: json['current_step'],
      metadata: json['metadata'],
      timestamp: DateTime.fromMillisecondsSinceEpoch(json['timestamp']),
    );
  }
}

/// Automation engine status data class
class AutomationEngineStatus {
  final String status;
  final int activeRules;
  final int executionsToday;
  final double successRate;
  final Map<String, dynamic>? details;
  final DateTime timestamp;

  AutomationEngineStatus({
    required this.status,
    required this.activeRules,
    required this.executionsToday,
    required this.successRate,
    this.details,
    required this.timestamp,
  });

  factory AutomationEngineStatus.fromJson(Map<String, dynamic> json) {
    return AutomationEngineStatus(
      status: json['status'],
      activeRules: json['active_rules'],
      executionsToday: json['executions_today'],
      successRate: json['success_rate']?.toDouble() ?? 0.0,
      details: json['details'],
      timestamp: DateTime.fromMillisecondsSinceEpoch(json['timestamp']),
    );
  }
}

/// Camera stream status data class
class CameraStreamStatus {
  final String cameraId;
  final String status;
  final String? resolution;
  final int? fps;
  final double? bitrate;
  final String? errorMessage;
  final DateTime timestamp;

  CameraStreamStatus({
    required this.cameraId,
    required this.status,
    this.resolution,
    this.fps,
    this.bitrate,
    this.errorMessage,
    required this.timestamp,
  });

  factory CameraStreamStatus.fromJson(Map<String, dynamic> json) {
    return CameraStreamStatus(
      cameraId: json['camera_id'],
      status: json['status'],
      resolution: json['resolution'],
      fps: json['fps'],
      bitrate: json['bitrate']?.toDouble(),
      errorMessage: json['error_message'],
      timestamp: DateTime.fromMillisecondsSinceEpoch(json['timestamp']),
    );
  }
}

/// Face detection event data class
class FaceDetectionEvent {
  final String cameraId;
  final String detectionId;
  final String? faceId;
  final double confidence;
  final Map<String, double> boundingBox;
  final Map<String, dynamic>? attributes;
  final DateTime timestamp;

  FaceDetectionEvent({
    required this.cameraId,
    required this.detectionId,
    this.faceId,
    required this.confidence,
    required this.boundingBox,
    this.attributes,
    required this.timestamp,
  });

  factory FaceDetectionEvent.fromJson(Map<String, dynamic> json) {
    return FaceDetectionEvent(
      cameraId: json['camera_id'],
      detectionId: json['detection_id'],
      faceId: json['face_id'],
      confidence: json['confidence']?.toDouble() ?? 0.0,
      boundingBox: Map<String, double>.from(json['bounding_box']),
      attributes: json['attributes'],
      timestamp: DateTime.fromMillisecondsSinceEpoch(json['timestamp']),
    );
  }
}

/// System performance metrics data class
class SystemPerformanceMetrics {
  final double cpuUsage;
  final double memoryUsage;
  final double diskUsage;
  final int activeConnections;
  final double avgProcessingTime;
  final int queueLength;
  final DateTime timestamp;

  SystemPerformanceMetrics({
    required this.cpuUsage,
    required this.memoryUsage,
    required this.diskUsage,
    required this.activeConnections,
    required this.avgProcessingTime,
    required this.queueLength,
    required this.timestamp,
  });

  factory SystemPerformanceMetrics.fromJson(Map<String, dynamic> json) {
    return SystemPerformanceMetrics(
      cpuUsage: json['cpu_usage']?.toDouble() ?? 0.0,
      memoryUsage: json['memory_usage']?.toDouble() ?? 0.0,
      diskUsage: json['disk_usage']?.toDouble() ?? 0.0,
      activeConnections: json['active_connections'] ?? 0,
      avgProcessingTime: json['avg_processing_time']?.toDouble() ?? 0.0,
      queueLength: json['queue_length'] ?? 0,
      timestamp: DateTime.fromMillisecondsSinceEpoch(json['timestamp']),
    );
  }
}

/// Error notification data class
class ErrorNotification {
  final String id;
  final String level;
  final String message;
  final String? source;
  final Map<String, dynamic>? details;
  final DateTime timestamp;

  ErrorNotification({
    required this.id,
    required this.level,
    required this.message,
    this.source,
    this.details,
    required this.timestamp,
  });

  factory ErrorNotification.fromJson(Map<String, dynamic> json) {
    return ErrorNotification(
      id: json['id'],
      level: json['level'],
      message: json['message'],
      source: json['source'],
      details: json['details'],
      timestamp: DateTime.fromMillisecondsSinceEpoch(json['timestamp']),
    );
  }
}

/// App notification data class
class AppNotification {
  final String id;
  final String type;
  final String title;
  final String message;
  final String? actionUrl;
  final Map<String, dynamic>? data;
  final DateTime timestamp;

  AppNotification({
    required this.id,
    required this.type,
    required this.title,
    required this.message,
    this.actionUrl,
    this.data,
    required this.timestamp,
  });

  factory AppNotification.fromJson(Map<String, dynamic> json) {
    return AppNotification(
      id: json['id'],
      type: json['type'],
      title: json['title'],
      message: json['message'],
      actionUrl: json['action_url'],
      data: json['data'],
      timestamp: DateTime.fromMillisecondsSinceEpoch(json['timestamp']),
    );
  }
}

/// Workflow command data class
class WorkflowCommand {
  final String action;
  final Map<String, dynamic>? parameters;

  WorkflowCommand({
    required this.action,
    this.parameters,
  });

  Map<String, dynamic> toJson() {
    return {
      'action': action,
      'parameters': parameters,
    };
  }
}

/// Automation command data class
class AutomationCommand {
  final String action;
  final Map<String, dynamic>? parameters;

  AutomationCommand({
    required this.action,
    this.parameters,
  });

  Map<String, dynamic> toJson() {
    return {
      'action': action,
      'parameters': parameters,
    };
  }
}

/// Camera command data class
class CameraCommand {
  final String action;
  final Map<String, dynamic>? parameters;

  CameraCommand({
    required this.action,
    this.parameters,
  });

  Map<String, dynamic> toJson() {
    return {
      'action': action,
      'parameters': parameters,
    };
  }
}