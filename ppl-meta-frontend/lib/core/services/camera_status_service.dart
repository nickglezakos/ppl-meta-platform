import 'dart:async';
import 'dart:convert';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:flutter/foundation.dart';
import 'auth_service.dart';

/// Service for managing WebSocket connections to camera status updates
class CameraStatusService {
  final String baseUrl;
  final AuthService authService;
  
  WebSocketChannel? _channel;
  StreamController<CameraStatusEvent>? _eventController;
  Timer? _reconnectTimer;
  bool _isDisposed = false;
  int _reconnectAttempts = 0;
  static const int maxReconnectAttempts = 5;
  static const Duration reconnectDelay = Duration(seconds: 2);
  
  CameraStatusService({
    required this.baseUrl,
    required this.authService,
  });
  
  /// Subscribe to status updates for a specific camera
  Stream<CameraStatusEvent> subscribeToCameraStatus(String deviceId) {
    _eventController = StreamController<CameraStatusEvent>.broadcast();
    _connect(deviceId);
    return _eventController!.stream;
  }
  
  /// Subscribe to status updates for all cameras
  Stream<CameraStatusEvent> subscribeToAllCameras() {
    _eventController = StreamController<CameraStatusEvent>.broadcast();
    _connect(null);
    return _eventController!.stream;
  }
  
  void _connect(String? deviceId) async {
    if (_isDisposed) return;
    
    try {
      final authToken = await _waitForAuthToken();
      if (authToken == null || authToken.isEmpty) {
        debugPrint('⏳ [CameraStatusService] No auth token yet — deferring WebSocket connect');
        _scheduleReconnect(deviceId);
        return;
      }

      final wsUrl = _buildWebSocketUrl(deviceId, authToken);
      debugPrint('🔌 Connecting to camera status WebSocket: ${_redactToken(wsUrl, authToken)}');
      
      _channel = WebSocketChannel.connect(Uri.parse(wsUrl));
      _reconnectAttempts = 0;
      
      _channel!.stream.listen(
        _handleMessage,
        onError: _handleError,
        onDone: () => _handleDisconnect(deviceId),
        cancelOnError: false,
      );
    } catch (e) {
      debugPrint('❌ Failed to connect to WebSocket: $e');
      _scheduleReconnect(deviceId);
    }
  }

  /// Prefer stored token, then in-memory ApiClient token; wait briefly for login.
  Future<String?> _waitForAuthToken() async {
    for (var attempt = 0; attempt < 20; attempt++) {
      final token = await authService.getToken();
      if (token != null && token.isNotEmpty) {
        return token;
      }
      await Future<void>.delayed(const Duration(milliseconds: 250));
      if (_isDisposed) return null;
    }
    return await authService.getToken();
  }

  String _buildWebSocketUrl(String? deviceId, String authToken) {
    final wsBase = baseUrl.replaceFirst('http://', 'ws://').replaceFirst('https://', 'wss://');
    return deviceId != null
        ? '$wsBase/api/v1/cameras/ws/status/$deviceId?token=$authToken'
        : '$wsBase/api/v1/cameras/ws/status?token=$authToken';
  }

  String _redactToken(String wsUrl, String authToken) {
    if (authToken.isEmpty) return wsUrl;
    return wsUrl.replaceAll(authToken, '***');
  }
  
  void _handleMessage(dynamic message) {
    try {
      debugPrint('📨 [RAW WebSocket] Received message: $message');
      
      final data = jsonDecode(message as String);
      debugPrint('📦 [PARSED JSON] Data: $data');
      
      final event = CameraStatusEvent.fromJson(data);
      
      debugPrint('📡 Camera status event: ${event.eventType} for ${event.deviceId}');
      
      if (!_isDisposed) {
        _eventController?.add(event);
      }
    } catch (e) {
      debugPrint('❌ Failed to parse camera status event: $e');
    }
  }
  
  void _handleError(dynamic error) {
    // Do not surface as stream errors — that throws Uncaught Error in the UI
    // and breaks the cameras page. Reconnect quietly instead.
    debugPrint('❌ WebSocket error: $error');
  }
  
  void _handleDisconnect(String? deviceId) {
    debugPrint('🔌 WebSocket disconnected');
    _scheduleReconnect(deviceId);
  }
  
  void _scheduleReconnect(String? deviceId) {
    if (_isDisposed || _reconnectAttempts >= maxReconnectAttempts) {
      debugPrint('⚠️ Max reconnect attempts reached or service disposed');
      return;
    }
    
    _reconnectAttempts++;
    debugPrint('🔄 Scheduling reconnect attempt $_reconnectAttempts in ${reconnectDelay.inSeconds}s');
    
    _reconnectTimer?.cancel();
    _reconnectTimer = Timer(reconnectDelay, () {
      _connect(deviceId);
    });
  }
  
  void dispose() {
    _isDisposed = true;
    _reconnectTimer?.cancel();
    _channel?.sink.close();
    _eventController?.close();
  }
}

/// Camera status event from WebSocket
class CameraStatusEvent {
  final String eventType;
  final String deviceId;
  final String? status;
  final DateTime timestamp;
  final Map<String, dynamic>? data;
  
  CameraStatusEvent({
    required this.eventType,
    required this.deviceId,
    this.status,
    required this.timestamp,
    this.data,
  });
  
  factory CameraStatusEvent.fromJson(Map<String, dynamic> json) {
    return CameraStatusEvent(
      // Backend sends "event" not "event_type"
      eventType: json['event']?.toString() ?? json['event_type']?.toString() ?? json['type']?.toString() ?? 'unknown',
      deviceId: json['device_id']?.toString() ?? 'unknown',
      status: json['status']?.toString(),
      timestamp: json['timestamp'] != null 
          ? DateTime.parse(json['timestamp']) 
          : DateTime.now(),
      data: json['details'] as Map<String, dynamic>?,  // Backend sends "details" not "data"
    );
  }
  
  bool get isConnecting => eventType == 'connecting';
  bool get isConnected => eventType == 'connected';
  bool get isDisconnected => eventType == 'disconnected';
  bool get isError => eventType == 'error';
  bool get isRecordingStarted => eventType == 'recording_started';
  bool get isRecordingStopped => eventType == 'recording_stopped';
  bool get isStreamingStarted => eventType == 'streaming_started';
  bool get isStreamingStopped => eventType == 'streaming_stopped';
  
  String? get errorMessage => data?['error'];
  String? get sessionId => data?['session_id'];
  int? get frameCount => data?['frames'];
  double? get duration => data?['duration'];
  String? get filePath => data?['file_path'];
}
