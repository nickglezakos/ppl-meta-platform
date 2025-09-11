import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';
import 'dart:developer' as developer;
import 'package:connectivity_plus/connectivity_plus.dart';
import 'mobile_camera_ip_update_service.dart';
import '../core/services/orientation_service.dart';
import 'package:camera/camera.dart';
import 'package:http/http.dart' as http;
import 'package:image/image.dart' as img;
import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';

/// Mobile camera streaming service for PPL Meta Platform
/// Handles streaming from mobile device cameras to backend
class MobileStreamingService {
  static const String _logTag = 'MobileStreamingService';
  
  // Backend connection info
  String? _backendUrl;
  String? _accessToken;
  String? _deviceId; // Add device ID storage
  
  // Streaming state
  bool _isStreaming = false;
  bool _isInitialized = false;
  String? _currentStreamUrl;
  StreamingSession? _currentSession;
  
  // Camera and streaming controllers
  CameraController? _cameraController;
  StreamController<StreamingStatus>? _statusController;
  StreamController<StreamingStats>? _statsController;
  
  // Network monitoring - Fixed for new connectivity API
  late StreamSubscription<List<ConnectivityResult>> _connectivitySubscription;
  ConnectivityResult _currentConnectivity = ConnectivityResult.none;
  
  // IP update service for dynamic network changes
  MobileCameraIPUpdateService? _ipUpdateService;
  
  // Configuration
  StreamConfig _currentConfig = StreamConfig.medium();
  
  // Singleton pattern
  static final MobileStreamingService _instance = MobileStreamingService._internal();
  factory MobileStreamingService() => _instance;
  MobileStreamingService._internal();
  
  /// Initialize the streaming service
  Future<bool> initialize() async {
    if (_isInitialized) return true;
    
    try {
      developer.log('Initializing Mobile Streaming Service', name: _logTag);
      
      // Initialize status and stats streams
      _statusController = StreamController<StreamingStatus>.broadcast();
      _statsController = StreamController<StreamingStats>.broadcast();
      
      // Setup network monitoring - Fixed for new connectivity API
      _connectivitySubscription = Connectivity().onConnectivityChanged.listen(
        (List<ConnectivityResult> results) => _onConnectivityChanged(results.isNotEmpty ? results.first : ConnectivityResult.none),
      );
      
      // Check initial connectivity - Fixed for new connectivity API
      final connectivityResults = await Connectivity().checkConnectivity();
      _currentConnectivity = connectivityResults.isNotEmpty ? connectivityResults.first : ConnectivityResult.none;
      
      _isInitialized = true;
      developer.log('Mobile Streaming Service initialized successfully', name: _logTag);
      return true;
      
    } catch (e) {
      developer.log('Failed to initialize streaming service: $e', name: _logTag, level: 1000);
      return false;
    }
  }
  
    /// Set backend connection information
  void setBackendConnection(String backendUrl, String accessToken, {String? deviceId}) {
    _backendUrl = backendUrl;
    _accessToken = accessToken;
    _deviceId = deviceId;
    developer.log('Backend connection set: $backendUrl, deviceId: ${deviceId ?? "not provided"}', name: _logTag);
  }
  
  /// Enable frame sending for session-based streaming (without RTMP)
  void enableFrameSending() {
    _isStreaming = true;
    developer.log('Frame sending enabled for session-based streaming', name: _logTag);
  }
  
  /// Start streaming with the given configuration
  Future<bool> startStreaming({
    required String rtmpUrl,
    required StreamConfig config,
    required CameraDescription camera,
  }) async {
    if (_isStreaming) {
      developer.log('Streaming already active', name: _logTag, level: 900);
      return false;
    }
    
    if (!_isInitialized) {
      bool initialized = await initialize();
      if (!initialized) return false;
    }
    
    try {
      developer.log('Starting streaming to: $rtmpUrl', name: _logTag);
      
      // Check network connectivity
      if (_currentConnectivity == ConnectivityResult.none) {
        _updateStatus(StreamingStatus.error('No network connection'));
        return false;
      }
      
      // Initialize camera
      bool cameraReady = await _initializeCamera(camera, config);
      if (!cameraReady) {
        _updateStatus(StreamingStatus.error('Failed to initialize camera'));
        return false;
      }
      
      // Create streaming session
      _currentSession = StreamingSession(
        rtmpUrl: rtmpUrl,
        config: config,
        startTime: DateTime.now(),
      );
      
      // Start RTMP streaming
      bool streamStarted = await _startRTMPStream(rtmpUrl, config);
      if (!streamStarted) {
        _updateStatus(StreamingStatus.error('Failed to start RTMP stream'));
        await _cleanup();
        return false;
      }
      
      // Update state
      _isStreaming = true;
      _currentStreamUrl = rtmpUrl;
      _currentConfig = config;
      
      _updateStatus(StreamingStatus.streaming());
      developer.log('Streaming started successfully', name: _logTag);
      
      // Start monitoring
      _startMonitoring();
      
      return true;
      
    } catch (e) {
      developer.log('Error starting stream: $e', name: _logTag, level: 1000);
      _updateStatus(StreamingStatus.error('Failed to start streaming: $e'));
      await _cleanup();
      return false;
    }
  }
  
  /// Stop streaming
  Future<void> stopStreaming() async {
    if (!_isStreaming) return;
    
    developer.log('Stopping streaming', name: _logTag);
    
    try {
      _isStreaming = false;
      _updateStatus(StreamingStatus.stopping());
      
      // Stop monitoring
      _stopMonitoring();
      
      // Stop RTMP stream
      await _stopRTMPStream();
      
      // Cleanup resources
      await _cleanup();
      
      _updateStatus(StreamingStatus.stopped());
      developer.log('Streaming stopped successfully', name: _logTag);
      
    } catch (e) {
      developer.log('Error stopping stream: $e', name: _logTag, level: 1000);
      _updateStatus(StreamingStatus.error('Error stopping stream: $e'));
    }
  }
  
  /// Update streaming quality in real-time
  Future<bool> updateStreamQuality(StreamQuality quality) async {
    if (!_isStreaming) return false;
    
    try {
      developer.log('Updating stream quality to: ${quality.name}', name: _logTag);
      
      StreamConfig newConfig = StreamConfig.fromQuality(quality);
      
      // Update camera settings
      if (_cameraController != null) {
        // Note: Actual implementation would update camera resolution/fps
        // This is a simplified version
        _currentConfig = newConfig;
      }
      
      _updateStatus(StreamingStatus.streaming(quality: quality));
      return true;
      
    } catch (e) {
      developer.log('Error updating stream quality: $e', name: _logTag, level: 1000);
      return false;
    }
  }
  
  /// Initialize camera with streaming configuration
  Future<bool> _initializeCamera(CameraDescription camera, StreamConfig config) async {
    // List of resolution presets to try, in order of preference
    final resolutionPresets = [
      ResolutionPreset.medium,   // Try medium first for better compatibility
      ResolutionPreset.low,      // Fallback to low
      ResolutionPreset.high,     // Try high last
    ];
    
    // Use YUV420 format for better streaming compatibility
    const imageFormat = ImageFormatGroup.yuv420;
    
    for (final preset in resolutionPresets) {
      try {
        developer.log('Trying camera initialization with ${preset.name} resolution', name: _logTag);
        
        _cameraController = CameraController(
          camera,
          preset,
          enableAudio: config.enableAudio,
          imageFormatGroup: imageFormat,
        );
        
        await _cameraController!.initialize();
        
        // Verify camera is properly initialized
        if (!_cameraController!.value.isInitialized) {
          developer.log('Camera controller not properly initialized', name: _logTag, level: 900);
          await _cameraController!.dispose();
          _cameraController = null;
          continue;
        }
        
        // Try to start image streaming
        await _cameraController!.startImageStream(_onCameraFrame);
        
        developer.log('Camera initialized successfully with ${preset.name} resolution', name: _logTag);
        developer.log('Camera preview size: ${_cameraController!.value.previewSize}', name: _logTag);
        return true;
        
      } catch (e) {
        developer.log('Camera initialization failed with ${preset.name}: $e', name: _logTag, level: 900);
        
        // Clean up failed attempt
        if (_cameraController != null) {
          try {
            await _cameraController!.dispose();
          } catch (disposeError) {
            developer.log('Error disposing failed camera controller: $disposeError', name: _logTag, level: 900);
          }
          _cameraController = null;
        }
        
        // If this was the last preset, return false
        if (preset == resolutionPresets.last) {
          developer.log('All camera initialization attempts failed', name: _logTag, level: 1000);
          return false;
        }
        
        // Wait a bit before trying next preset
        await Future.delayed(const Duration(milliseconds: 500));
      }
    }
    
    return false;
  }
  
  /// Handle camera frames for streaming to backend
  void _onCameraFrame(CameraImage image) {
    if (!_isStreaming) return;
    
    // Send frame to backend asynchronously (don't block camera stream)
    _sendFrameToBackend(image);
    
    // Update stats
    _updateStats(StreamingStats.fromFrame(image));
  }
  
  /// Public method to send frame to backend (called by CameraService)
  Future<void> sendFrameToBackend(CameraImage image) async {
    developer.log('sendFrameToBackend called - _isStreaming: $_isStreaming, _backendUrl: $_backendUrl, _accessToken: ${_accessToken != null ? "present" : "null"}', name: _logTag);
    if (!_isStreaming || _backendUrl == null || _accessToken == null) {
      developer.log('Skipping frame send - conditions not met', name: _logTag);
      return;
    }
    developer.log('Sending frame to backend: ${image.width}x${image.height}', name: _logTag);
    await _sendFrameToBackend(image);
  }
  
  /// Send camera frame to backend
  Future<void> _sendFrameToBackend(CameraImage image) async {
    try {
      // Convert CameraImage to JPEG bytes
      final bytes = await _convertCameraImageToJpeg(image);
      if (bytes == null) return;
      
      // Encode as base64
      final base64Data = base64Encode(bytes);
      
      // Get device ID from stored value or session fallback
      final deviceId = _deviceId ?? _currentSession?.rtmpUrl.split('/').last ?? 'unknown';
      
      // Send to backend frame endpoint
      await _sendFrameDataToBackend(deviceId, base64Data, image);
      
    } catch (e) {
      developer.log('Error sending frame to backend: $e', name: _logTag, level: 900);
    }
  }
  
  /// Convert CameraImage to JPEG bytes
  Future<Uint8List?> _convertCameraImageToJpeg(CameraImage image) async {
    try {
      // Convert YUV420 to RGB
      final int width = image.width;
      final int height = image.height;
      
      // Create RGB image data
      final Uint8List rgbBytes = Uint8List(width * height * 3);
      
      // Simple YUV to RGB conversion
      final yPlane = image.planes[0];
      final uPlane = image.planes[1]; 
      final vPlane = image.planes[2];
      
      for (int y = 0; y < height; y++) {
        for (int x = 0; x < width; x++) {
          final int yIndex = y * yPlane.bytesPerRow + x;
          final int uvIndex = (y ~/ 2) * uPlane.bytesPerRow + (x ~/ 2);
          
          final int yValue = yPlane.bytes[yIndex];
          final int uValue = uPlane.bytes[uvIndex];
          final int vValue = vPlane.bytes[uvIndex];
          
          // YUV to RGB conversion
          final int r = (yValue + 1.402 * (vValue - 128)).clamp(0, 255).toInt();
          final int g = (yValue - 0.344 * (uValue - 128) - 0.714 * (vValue - 128)).clamp(0, 255).toInt();
          final int b = (yValue + 1.772 * (uValue - 128)).clamp(0, 255).toInt();
          
          final int rgbIndex = (y * width + x) * 3;
          rgbBytes[rgbIndex] = r;
          rgbBytes[rgbIndex + 1] = g;
          rgbBytes[rgbIndex + 2] = b;
        }
      }
      
      // Convert RGB to JPEG using image package
      final img.Image rgbImage = img.Image.fromBytes(
        width: width,
        height: height,
        bytes: rgbBytes.buffer,
        order: img.ChannelOrder.rgb,
      );
      
      return Uint8List.fromList(img.encodeJpg(rgbImage, quality: 80));
      
    } catch (e) {
      developer.log('Error converting camera image: $e', name: _logTag, level: 1000);
      return null;
    }
  }
  
  /// Send frame data to backend via HTTP
  Future<void> _sendFrameDataToBackend(String deviceId, String base64Data, CameraImage image) async {
    try {
      if (_backendUrl == null || _accessToken == null) {
        developer.log('Backend connection info not available', name: _logTag, level: 900);
        return;
      }
      
      final url = '$_backendUrl/api/v1/streaming/mobile/$deviceId/frame';
      
      // Get current orientation from OrientationService
      final orientationService = _getOrientationService();
      final currentOrientation = orientationService?.currentOrientation ?? DeviceOrientation.portraitUp;
      final rotationAngle = _getRotationAngle(currentOrientation);
      
      // Debug logging for orientation
      developer.log('📱 [FRAME_SEND_DEBUG] Sending frame with orientation data:', name: _logTag);
      developer.log('📱 [FRAME_SEND_DEBUG] - Orientation: $currentOrientation', name: _logTag);
      developer.log('📱 [FRAME_SEND_DEBUG] - Rotation angle: $rotationAngle°', name: _logTag);
      developer.log('📱 [FRAME_SEND_DEBUG] - Frame size: ${image.width}x${image.height}', name: _logTag);
      
      final frameData = {
        'device_id': deviceId,
        'frame_data': base64Data,
        'timestamp': DateTime.now().millisecondsSinceEpoch / 1000.0,
        'width': image.width,
        'height': image.height,
        'format': 'jpeg',
        // Add orientation information
        'orientation': currentOrientation.toString(),
        'rotation_angle': rotationAngle,
      };
      
      final response = await http.post(
        Uri.parse(url),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $_accessToken',
        },
        body: json.encode(frameData),
      );
      
      if (response.statusCode == 200) {
        developer.log('Frame sent successfully', name: _logTag);
      } else {
        developer.log('Failed to send frame: ${response.statusCode}', name: _logTag, level: 900);
      }
      
    } catch (e) {
      developer.log('Error sending frame data: $e', name: _logTag, level: 1000);
    }
  }
  
  /// Start RTMP streaming to backend
  Future<bool> _startRTMPStream(String rtmpUrl, StreamConfig config) async {
    try {
      // TODO: Implement actual RTMP streaming
      // This would use rtmp_publisher package or similar
      // For now, simulate successful connection
      
      developer.log('RTMP stream connected to: $rtmpUrl', name: _logTag);
      return true;
      
    } catch (e) {
      developer.log('RTMP connection failed: $e', name: _logTag, level: 1000);
      return false;
    }
  }
  
  /// Stop RTMP streaming
  Future<void> _stopRTMPStream() async {
    try {
      // TODO: Implement actual RTMP disconnection
      developer.log('RTMP stream disconnected', name: _logTag);
      
    } catch (e) {
      developer.log('Error disconnecting RTMP: $e', name: _logTag, level: 1000);
    }
  }
  
  /// Start monitoring streaming health
  void _startMonitoring() {
    // TODO: Implement streaming health monitoring
    // - Check frame rate
    // - Monitor network latency
    // - Track dropped frames
    // - Battery usage monitoring
  }
  
  /// Stop monitoring
  void _stopMonitoring() {
    // TODO: Stop monitoring timers/streams
  }
  
  /// Handle network connectivity changes
  void _onConnectivityChanged(ConnectivityResult result) {
    _currentConnectivity = result;
    developer.log('Network connectivity changed: ${result.name}', name: _logTag);
    
    if (_isStreaming) {
      if (result == ConnectivityResult.none) {
        _updateStatus(StreamingStatus.error('Network connection lost'));
      } else {
        _updateStatus(StreamingStatus.streaming());
        
        // Trigger IP update check when network reconnects
        if (result == ConnectivityResult.wifi || result == ConnectivityResult.ethernet) {
          _ipUpdateService?.forceIPUpdate();
        }
      }
    }
  }
  
  /// Update streaming status
  void _updateStatus(StreamingStatus status) {
    _statusController?.add(status);
  }
  
  /// Update streaming statistics
  void _updateStats(StreamingStats stats) {
    _statsController?.add(stats);
  }
  
  /// Initialize with IP update monitoring
  Future<bool> initializeWithIPMonitoring({
    required String deviceId,
    required String authToken,
    required String cameraServiceUrl,
  }) async {
    final baseInitialized = await initialize();
    if (!baseInitialized) return false;
    
    try {
      // Initialize IP update service
      _ipUpdateService = MobileCameraIPUpdateService();
      final ipServiceInitialized = await _ipUpdateService!.initialize(
        deviceId: deviceId,
        authToken: authToken,
        cameraServiceUrl: cameraServiceUrl,
      );
      
      if (ipServiceInitialized) {
        developer.log('IP monitoring service initialized successfully', name: _logTag);
      } else {
        developer.log('IP monitoring service failed to initialize', name: _logTag, level: 900);
      }
      
      return true;
    } catch (e) {
      developer.log('Failed to initialize IP monitoring: $e', name: _logTag, level: 1000);
      return baseInitialized; // Return base initialization result
    }
  }

  /// Cleanup resources
  Future<void> _cleanup() async {
    try {
      // Stop camera with improved error handling
      if (_cameraController != null) {
        try {
          if (_cameraController!.value.isStreamingImages) {
            await _cameraController!.stopImageStream();
            developer.log('Image stream stopped', name: _logTag);
          }
        } catch (e) {
          developer.log('Error stopping image stream: $e', name: _logTag, level: 900);
        }
        
        try {
          await _cameraController!.dispose();
          developer.log('Camera controller disposed', name: _logTag);
        } catch (e) {
          developer.log('Error disposing camera controller: $e', name: _logTag, level: 900);
        }
        
        _cameraController = null;
      }
      
      // Clear session
      _currentSession = null;
      _currentStreamUrl = null;
      
    } catch (e) {
      developer.log('Cleanup error: $e', name: _logTag, level: 1000);
    }
  }
  
  /// Dispose the service
  Future<void> dispose() async {
    developer.log('Disposing Mobile Streaming Service', name: _logTag);
    
    await _cleanup();
    await _connectivitySubscription.cancel();
    
    // Dispose IP update service
    await _ipUpdateService?.dispose();
    _ipUpdateService = null;
    
    _statusController?.close();
    _statsController?.close();
    
    _isInitialized = false;
    _isStreaming = false;
    
    // TODO: Stop monitoring timers/streams
  }

  /// Send orientation update to backend
  Future<void> sendOrientationUpdate(String orientation, int rotationAngle) async {
    if (_backendUrl == null || _accessToken == null) {
      developer.log('Cannot send orientation update - backend not configured', name: _logTag, level: 900);
      return;
    }

    try {
      final response = await http.post(
        Uri.parse('$_backendUrl/api/v1/mobile/orientation'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $_accessToken',
        },
        body: json.encode({
          'device_id': _deviceId,
          'orientation': orientation,
          'rotation_angle': rotationAngle,
          'timestamp': DateTime.now().toIso8601String(),
        }),
      );

      if (response.statusCode == 200) {
        developer.log('Orientation update sent successfully: $orientation ($rotationAngle°)', name: _logTag);
      } else {
        developer.log('Failed to send orientation update: ${response.statusCode}', name: _logTag, level: 900);
      }
    } catch (e) {
      developer.log('Error sending orientation update: $e', name: _logTag, level: 1000);
    }
  }

  /// Get orientation service instance (simplified approach)
  OrientationService? _getOrientationService() {
    try {
      return OrientationService.instance;
    } catch (e) {
      return null;
    }
  }

  /// Get rotation angle for the orientation
  /// Camera sensor captures in landscape, so we need to rotate frames
  /// to match the device orientation for proper display
  int _getRotationAngle(DeviceOrientation orientation) {
    switch (orientation) {
      case DeviceOrientation.portraitUp:
        // Phone held upright, camera captures landscape -> rotate 90° clockwise
        return 90;
      case DeviceOrientation.landscapeLeft:
        // Phone held landscape left, camera captures landscape -> no rotation
        return 0;
      case DeviceOrientation.portraitDown:
        // Phone held upside down, camera captures landscape -> rotate 270° clockwise  
        return 270;
      case DeviceOrientation.landscapeRight:
        // Phone held landscape right, camera captures landscape -> rotate 180°
        return 180;
    }
  }
  
  // Getters
  bool get isStreaming => _isStreaming;
  bool get isInitialized => _isInitialized;
  String? get currentStreamUrl => _currentStreamUrl;
  StreamConfig get currentConfig => _currentConfig;
  StreamingSession? get currentSession => _currentSession;
  
  // Streams
  Stream<StreamingStatus>? get statusStream => _statusController?.stream;
  Stream<StreamingStats>? get statsStream => _statsController?.stream;
}

/// Streaming configuration
class StreamConfig {
  final int width;
  final int height;
  final int fps;
  final int bitrate;
  final StreamQuality quality;
  final bool enableAudio;
  
  const StreamConfig({
    required this.width,
    required this.height,
    required this.fps,
    required this.bitrate,
    required this.quality,
    this.enableAudio = false,
  });
  
  // Predefined quality configurations
  factory StreamConfig.low() => const StreamConfig(
    width: 320,
    height: 240,
    fps: 15,
    bitrate: 500000, // 500kbps
    quality: StreamQuality.low,
  );
  
  factory StreamConfig.medium() => const StreamConfig(
    width: 640,
    height: 480,
    fps: 30,
    bitrate: 1000000, // 1Mbps
    quality: StreamQuality.medium,
  );
  
  factory StreamConfig.high() => const StreamConfig(
    width: 1280,
    height: 720,
    fps: 30,
    bitrate: 2500000, // 2.5Mbps
    quality: StreamQuality.high,
  );
  
  factory StreamConfig.ultra() => const StreamConfig(
    width: 1920,
    height: 1080,
    fps: 30,
    bitrate: 5000000, // 5Mbps
    quality: StreamQuality.ultra,
  );
  
  factory StreamConfig.fromQuality(StreamQuality quality) {
    switch (quality) {
      case StreamQuality.low:
        return StreamConfig.low();
      case StreamQuality.medium:
        return StreamConfig.medium();
      case StreamQuality.high:
        return StreamConfig.high();
      case StreamQuality.ultra:
        return StreamConfig.ultra();
    }
  }
  
  String get resolution => '${width}x$height';
}

/// Stream quality levels
enum StreamQuality {
  low,
  medium,
  high,
  ultra;
  
  String get displayName {
    switch (this) {
      case StreamQuality.low:
        return 'Low (320p)';
      case StreamQuality.medium:
        return 'Medium (480p)';
      case StreamQuality.high:
        return 'High (720p)';
      case StreamQuality.ultra:
        return 'Ultra (1080p)';
    }
  }
}

/// Streaming session information
class StreamingSession {
  final String rtmpUrl;
  final StreamConfig config;
  final DateTime startTime;
  
  StreamingSession({
    required this.rtmpUrl,
    required this.config,
    required this.startTime,
  });
  
  Duration get duration => DateTime.now().difference(startTime);
}

/// Streaming status
class StreamingStatus {
  final StreamingState state;
  final String? message;
  final StreamQuality? quality;
  final DateTime timestamp;
  
  StreamingStatus._(
    this.state, {
    this.message,
    this.quality,
  }) : timestamp = DateTime.now();
  
  factory StreamingStatus.initializing() => StreamingStatus._(
    StreamingState.initializing,
    message: 'Initializing streaming...',
  );
  
  factory StreamingStatus.streaming({StreamQuality? quality}) => StreamingStatus._(
    StreamingState.streaming,
    message: 'Streaming active',
    quality: quality,
  );
  
  factory StreamingStatus.stopping() => StreamingStatus._(
    StreamingState.stopping,
    message: 'Stopping stream...',
  );
  
  factory StreamingStatus.stopped() => StreamingStatus._(
    StreamingState.stopped,
    message: 'Stream stopped',
  );
  
  factory StreamingStatus.error(String error) => StreamingStatus._(
    StreamingState.error,
    message: error,
  );
  
  bool get isStreaming => state == StreamingState.streaming;
  bool get hasError => state == StreamingState.error;
}

/// Streaming states
enum StreamingState {
  initializing,
  streaming,
  stopping,
  stopped,
  error,
}

/// Streaming statistics
class StreamingStats {
  final int frameRate;
  final int bitrate;
  final Duration latency;
  final int droppedFrames;
  final DateTime timestamp;
  
  StreamingStats({
    required this.frameRate,
    required this.bitrate,
    required this.latency,
    required this.droppedFrames,
  }) : timestamp = DateTime.now();
  
  factory StreamingStats.fromFrame(CameraImage image) {
    // TODO: Calculate actual stats from camera frame
    return StreamingStats(
      frameRate: 30,
      bitrate: 1000000,
      latency: const Duration(milliseconds: 100),
      droppedFrames: 0,
    );
  }
}
