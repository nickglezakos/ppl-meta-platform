import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';
import 'package:camera/camera.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:web_socket_channel/status.dart' as status;
import '../models/camera_config.dart';
import '../services/camera_service.dart';

/// Streaming service for live video streaming to PPL Meta platform
class StreamingService {
  static StreamingService? _instance;
  static StreamingService get instance => _instance ??= StreamingService._();
  StreamingService._();

  WebSocketChannel? _wsChannel;
  StreamSubscription? _streamSubscription;
  Timer? _heartbeatTimer;
  
  bool _isConnected = false;
  bool _isStreaming = false;
  String? _streamId;
  String? _serverUrl;
  String? _deviceId;  // Add device ID for mobile cameras
  Map<String, String>? _authHeaders;
  
  // Stream metrics
  int _framesSent = 0;
  int _bytesTransferred = 0;
  DateTime? _streamStartTime;
  DateTime? _lastFrameTime;
  StreamQuality _currentQuality = StreamQuality.medium;
  String? _roomId;
  Duration _streamDuration = Duration.zero;
  
  // Connection settings
  static const int _heartbeatInterval = 30; // seconds
  static const int _connectionTimeout = 10; // seconds
  static const int _maxReconnectAttempts = 5;
  int _reconnectAttempts = 0;

  // Getters
  bool get isConnected => _isConnected;
  bool get isStreaming => _isStreaming;
  String? get streamId => _streamId;
  int get framesSent => _framesSent;
  int get bytesTransferred => _bytesTransferred;
  Duration get streamDuration => _streamDuration;

  /// Initialize streaming service with server configuration
  Future<bool> initializeStreaming({
    required String serverUrl,
    required Map<String, String> authHeaders,
    String? deviceId,  // Add optional device ID for mobile cameras
  }) async {
    try {
      _serverUrl = serverUrl;
      _authHeaders = authHeaders;
      _deviceId = deviceId;
      
      print('🔗 [STREAMING_DEBUG] Initialized with:');
      print('   Server URL: $serverUrl');
      print('   Device ID: $deviceId');
      
      return true;
    } catch (e) {
      print('Failed to initialize streaming: $e');
      return false;
    }
  }

  /// Connect to streaming server
  Future<bool> connect() async {
    try {
      if (_isConnected || _serverUrl == null) {
        return _isConnected;
      }

      // Build WebSocket URL for mobile camera streaming
      print('🔗 [STREAMING_DEBUG] Building WebSocket URL:');
      print('   Server URL: $_serverUrl');
      print('   Device ID: $_deviceId');
      
      String wsUrl;
      if (_deviceId != null && _deviceId!.isNotEmpty && _deviceId != 'unknown') {
        // Use mobile-specific endpoint for mobile cameras: /api/v1/cameras/mobile/{device_id}/stream
        wsUrl = _serverUrl!.replaceFirst('http', 'ws') + '/api/v1/cameras/mobile/$_deviceId/stream';
        print('🎯 [STREAMING_DEBUG] Using mobile-specific URL: $wsUrl');
      } else {
        // Fallback to generic endpoint - should not be used for mobile cameras
        wsUrl = _serverUrl!.replaceFirst('http', 'ws') + '/api/v1/cameras/mobile/unknown/stream';
        print('⚠️ [STREAMING_DEBUG] Using fallback URL (device ID missing): $wsUrl');
      }
      
      print('🔗 [STREAMING_DEBUG] Connecting to streaming server: $wsUrl');

      try {
        // Create WebSocket connection
        _wsChannel = WebSocketChannel.connect(
          Uri.parse(wsUrl),
          protocols: ['ppl-meta-stream'],
        );
        print('🔗 [STREAMING_DEBUG] WebSocket channel created successfully');
      } catch (e) {
        print('🚨 [STREAMING_DEBUG] Failed to create WebSocket channel: $e');
        throw e;
      }

      // Set connection timeout
      final connectionCompleter = Completer<bool>();
      Timer(Duration(seconds: _connectionTimeout), () {
        if (!connectionCompleter.isCompleted) {
          print('🕐 [STREAMING_DEBUG] Connection timeout after ${_connectionTimeout}s');
          connectionCompleter.complete(false);
        }
      });

      // Listen for connection messages
      _streamSubscription = _wsChannel!.stream.listen(
        (message) {
          _onWebSocketMessage(message);
          // Complete connection when we receive connection_established
          if (!connectionCompleter.isCompleted && _isConnected) {
            connectionCompleter.complete(true);
          }
        },
        onError: (error) {
          _onWebSocketError(error);
          if (!connectionCompleter.isCompleted) {
            connectionCompleter.complete(false);
          }
        },
        onDone: _onWebSocketClosed,
      );

      // Send authentication
      await _sendMessage({
        'type': 'auth',
        'headers': _authHeaders,
        'timestamp': DateTime.now().toIso8601String(),
      });

      // Wait for connection confirmation
      final connected = await connectionCompleter.future;
      
      if (connected && _isConnected) {
        _startHeartbeat();
        _reconnectAttempts = 0;
        print('✅ [STREAMING_DEBUG] Successfully connected to streaming server');
        return true;
      }

      print('❌ [STREAMING_DEBUG] Connection failed - connected: $connected, _isConnected: $_isConnected');
      return false;
    } catch (e) {
      print('❌ [STREAMING_DEBUG] Failed to connect to streaming server: $e');
      return false;
    }
  }

  /// Disconnect from streaming server
  Future<void> disconnect() async {
    try {
      if (_isStreaming) {
        await stopStream();
      }

      _stopHeartbeat();
      
      await _wsChannel?.sink.close(status.normalClosure);
      await _streamSubscription?.cancel();
      
      _wsChannel = null;
      _streamSubscription = null;
      _isConnected = false;
      _streamId = null;
      
      print('Disconnected from streaming server');
    } catch (e) {
      print('Error during disconnect: $e');
    }
  }

  /// Update device ID and reconnect to streaming server
  Future<bool> updateDeviceIdAndReconnect(String newDeviceId) async {
    print('🔄 [STREAMING_DEBUG] Updating device ID and reconnecting...');
    print('🔄 [STREAMING_DEBUG] Old device ID: $_deviceId');
    print('🔄 [STREAMING_DEBUG] New device ID: $newDeviceId');
    
    try {
      // Disconnect first if connected
      if (_isConnected) {
        await disconnect();
        print('🔄 [STREAMING_DEBUG] Disconnected from previous connection');
      }
      
      // Update device ID
      _deviceId = newDeviceId;
      print('🔄 [STREAMING_DEBUG] Device ID updated');
      
      // Reconnect with new device ID
      final connected = await connect();
      if (connected) {
        print('✅ [STREAMING_DEBUG] Successfully reconnected with new device ID: $newDeviceId');
      } else {
        print('❌ [STREAMING_DEBUG] Failed to reconnect with new device ID: $newDeviceId');
      }
      
      return connected;
    } catch (e) {
      print('❌ [STREAMING_DEBUG] Error during device ID update and reconnect: $e');
      return false;
    }
  }

  /// Start streaming video
  Future<bool> startStream({
    String? streamTitle,
    String? streamDescription,
    StreamQuality? quality,
  }) async {
    try {
      if (!_isConnected || _isStreaming) {
        return false;
      }

      // Ensure camera is ready
      final cameraService = CameraService.instance;
      if (!cameraService.isInitialized || cameraService.controller == null) {
        return false;
      }

      // Apply quality settings if provided
      if (quality != null) {
        await cameraService.updateStreamQuality(quality);
      }

      // Generate stream ID
      _streamId = 'stream_${DateTime.now().millisecondsSinceEpoch}';
      
      // Send stream start request
      await _sendMessage({
        'type': 'start_stream',
        'streamId': _streamId,
        'title': streamTitle ?? 'PPL Meta Mobile Stream',
        'description': streamDescription ?? 'Live stream from PPL Meta Mobile Camera',
        'quality': quality?.toJson() ?? StreamQuality.medium.toJson(),
        'timestamp': DateTime.now().toIso8601String(),
      });

      // Start camera streaming
      final streamStarted = await cameraService.startStreaming();
      if (!streamStarted) {
        return false;
      }

      // Initialize metrics
      _framesSent = 0;
      _bytesTransferred = 0;
      _streamStartTime = DateTime.now();
      _isStreaming = true;

      // Start frame transmission
      _startFrameTransmission();
      
      print('Started streaming with ID: $_streamId');
      return true;
    } catch (e) {
      print('Failed to start stream: $e');
      return false;
    }
  }

  /// Stop streaming video
  Future<bool> stopStream() async {
    try {
      if (!_isStreaming) {
        return true;
      }

      // Stop camera streaming
      final cameraService = CameraService.instance;
      await cameraService.stopStreaming();

      // Send stream stop request
      if (_streamId != null) {
        await _sendMessage({
          'type': 'stop_stream',
          'streamId': _streamId,
          'duration': _streamDuration.inSeconds,
          'framesSent': _framesSent,
          'bytesTransferred': _bytesTransferred,
          'timestamp': DateTime.now().toIso8601String(),
        });
      }

      _isStreaming = false;
      
      // Calculate final duration
      if (_streamStartTime != null) {
        _streamDuration = DateTime.now().difference(_streamStartTime!);
      }

      print('Stopped streaming. Duration: ${_streamDuration.inSeconds}s, Frames: $_framesSent');
      return true;
    } catch (e) {
      print('Failed to stop stream: $e');
      return false;
    }
  }

  /// Send frame data to streaming server (CameraImage)
  Future<void> sendFrame(CameraImage image) async {
    try {
      if (!_isConnected || !_isStreaming || _streamId == null) {
        return;
      }

      // Convert CameraImage to JPEG bytes
      final jpegBytes = await _convertCameraImageToJpeg(image);
      if (jpegBytes != null) {
        await sendFrameData(jpegBytes);
      }
    } catch (e) {
      print('Failed to send camera frame: $e');
    }
  }

  /// Send frame data to streaming server (raw bytes)
  Future<void> sendFrameData(List<int> frameData) async {
    try {
      if (!_isConnected || !_isStreaming || _streamId == null) {
        return;
      }

      // Send frame data directly (assuming it's already JPEG)
      await _sendBinaryMessage({
        'type': 'frame',
        'streamId': _streamId!,
        'frameNumber': _framesSent,
        'timestamp': DateTime.now().millisecondsSinceEpoch,
        'format': 'jpeg',
        'data': base64Encode(frameData),
      });

      _framesSent++;
      _bytesTransferred += frameData.length;
      _lastFrameTime = DateTime.now();
    } catch (e) {
      print('Failed to send frame: $e');
    }
  }

  /// Get streaming statistics
  Future<Map<String, dynamic>> getStreamingStats() async {
    return {
      'isConnected': _isConnected,
      'isStreaming': _isStreaming,
      'streamId': _streamId,
      'framesSent': _framesSent,
      'bytesTransferred': _bytesTransferred,
      'bytesTransferredMB': (_bytesTransferred / (1024 * 1024)).toStringAsFixed(2),
      'streamDuration': _streamDuration.inSeconds,
      'averageFps': _streamStartTime != null && _streamDuration.inSeconds > 0 
          ? (_framesSent / _streamDuration.inSeconds).toStringAsFixed(2)
          : '0',
      'averageBitrate': _streamStartTime != null && _streamDuration.inSeconds > 0
          ? ((_bytesTransferred * 8) / _streamDuration.inSeconds / 1024).toStringAsFixed(2) + ' kbps'
          : '0 kbps',
    };
  }

  /// Handle WebSocket messages
  void _onWebSocketMessage(dynamic message) {
    try {
      final data = json.decode(message) as Map<String, dynamic>;
      final type = data['type'] as String?;

      switch (type) {
        case 'connection_established':
          _isConnected = true;
          print('✅ [STREAMING_DEBUG] Connection established successfully');
          break;
          
        case 'echo':
          print('✅ [STREAMING_DEBUG] Echo received from server');
          break;
          
        case 'auth_success':
          _isConnected = true;
          print('Authentication successful');
          break;
          
        case 'auth_error':
          print('Authentication failed: ${data['message']}');
          break;
          
        case 'stream_started':
          print('Stream started confirmation: ${data['streamId']}');
          break;
          
        case 'stream_stopped':
          print('Stream stopped confirmation: ${data['streamId']}');
          break;
          
        case 'pong':
          // Heartbeat response
          break;
          
        case 'stream_ready':
          print('✅ [STREAMING_DEBUG] Stream is ready for receiving data');
          break;
          
        case 'error':
          print('Server error: ${data['message']}');
          break;
          
        default:
          print('Unknown message type: $type');
      }
    } catch (e) {
      print('Failed to parse WebSocket message: $e');
    }
  }

  /// Handle WebSocket errors
  void _onWebSocketError(error) {
    print('🚨 [WEBSOCKET_ERROR] WebSocket error: $error');
    print('🚨 [WEBSOCKET_ERROR] Error type: ${error.runtimeType}');
    print('🚨 [WEBSOCKET_ERROR] Server URL was: $_serverUrl');
    print('🚨 [WEBSOCKET_ERROR] Device ID was: $_deviceId');
    _isConnected = false;
    
    if (_reconnectAttempts < _maxReconnectAttempts) {
      _reconnectAttempts++;
      Timer(Duration(seconds: 2 * _reconnectAttempts), () {
        print('Attempting to reconnect... (${_reconnectAttempts}/$_maxReconnectAttempts)');
        connect();
      });
    }
  }

  /// Handle WebSocket closure
  void _onWebSocketClosed() {
    print('WebSocket connection closed');
    _isConnected = false;
    _isStreaming = false;
  }

  /// Send JSON message
  Future<void> _sendMessage(Map<String, dynamic> message) async {
    try {
      if (_wsChannel != null) {
        _wsChannel!.sink.add(json.encode(message));
      }
    } catch (e) {
      print('Failed to send message: $e');
    }
  }

  /// Send binary message
  Future<void> _sendBinaryMessage(Map<String, dynamic> message) async {
    try {
      if (_wsChannel != null) {
        _wsChannel!.sink.add(json.encode(message));
      }
    } catch (e) {
      print('Failed to send binary message: $e');
    }
  }

  /// Start heartbeat timer
  void _startHeartbeat() {
    _heartbeatTimer = Timer.periodic(
      Duration(seconds: _heartbeatInterval),
      (timer) {
        _sendMessage({
          'type': 'ping',
          'timestamp': DateTime.now().toIso8601String(),
        });
      },
    );
  }

  /// Stop heartbeat timer
  void _stopHeartbeat() {
    _heartbeatTimer?.cancel();
    _heartbeatTimer = null;
  }

  /// Start frame transmission
  void _startFrameTransmission() {
    final cameraService = CameraService.instance;
    
    // Hook into camera image stream
    // This would need to be integrated with CameraService's _onImageStreamData
    // For now, we'll simulate with a timer
    Timer.periodic(Duration(milliseconds: 33), (timer) { // ~30 FPS
      if (!_isStreaming) {
        timer.cancel();
        return;
      }
      
      // In real implementation, this would be called from camera stream
      // sendFrame(cameraImage);
    });
  }

  /// Convert CameraImage to JPEG bytes
  Future<Uint8List?> _convertCameraImageToJpeg(CameraImage image) async {
    try {
      // This is a simplified implementation
      // Real implementation would properly convert YUV420 to RGB then to JPEG
      // For now, return null to indicate conversion not implemented
      return null;
    } catch (e) {
      print('Failed to convert camera image: $e');
      return null;
    }
  }

  /// Dispose resources
  Future<void> dispose() async {
    await disconnect();
  }

  /// Update stream quality setting
  Future<void> updateStreamQuality(StreamQuality quality) async {
    final cameraService = CameraService.instance;
    await cameraService.updateStreamQuality(quality);
    // Update current quality setting
    _currentQuality = quality;
  }

  /// Get current stream configuration
  Map<String, dynamic> getStreamConfig() {
    return {
      'quality': _currentQuality.toJson(),
      'isStreaming': _isStreaming,
      'isConnected': _isConnected,
      'serverUrl': _serverUrl,
      'roomId': _roomId,
    };
  }

  /// Check if streaming is supported on this device
  Future<bool> isStreamingSupported() async {
    try {
      final cameraService = CameraService.instance;
      return await cameraService.isCameraAvailable();
    } catch (e) {
      print('Error checking streaming support: $e');
      return false;
    }
  }

}
