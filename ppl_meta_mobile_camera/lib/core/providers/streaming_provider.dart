import 'package:flutter/foundation.dart';
import '../models/mobile_camera.dart';
import '../services/camera_registration_service.dart';
import '../services/mjpeg_streaming_service.dart';
import '../services/network_discovery_service.dart';
import '../services/authentication_service.dart';
import '../interfaces/camera_interface.dart';
import 'dart:convert';
import 'package:http/http.dart' as http;

/// Provider for managing mobile camera streaming functionality
class PlatformStreamingProvider extends ChangeNotifier {
  // Platform connection
  String? _platformUrl;
  bool _isConnectedToPlatform = false;
  
  // Registration state
  bool _isRegistered = false;
  String? _registeredDeviceId;
  MobileCameraInfo? _cameraInfo;
  
  // Streaming state
  bool _isStreaming = false;
  StreamingConfig _streamingConfig = StreamingConfig();
  StreamingStats? _streamingStats;
  
  // Discovery
  List<PlatformDiscoveryResult> _discoveredPlatforms = [];
  bool _isDiscovering = false;
  
  // Status
  MobileCameraStatus _status = MobileCameraStatus.offline;
  String? _statusMessage;

  // Getters
  String? get platformUrl => _platformUrl;
  bool get isConnectedToPlatform => _isConnectedToPlatform;
  bool get isRegistered => _isRegistered;
  String? get registeredDeviceId => _registeredDeviceId;
  MobileCameraInfo? get cameraInfo => _cameraInfo;
  bool get isStreaming => _isStreaming;
  StreamingConfig get streamingConfig => _streamingConfig;
  StreamingStats? get streamingStats => _streamingStats;
  List<PlatformDiscoveryResult> get discoveredPlatforms => _discoveredPlatforms;
  bool get isDiscovering => _isDiscovering;
  MobileCameraStatus get status => _status;
  String? get statusMessage => _statusMessage;
  
  int get connectedClients => MJPEGStreamingService.instance.clientCount;

  /// Backward compatibility alias for discoverPlatform()
  Future<void> discoverPlatforms() async => await discoverPlatform();
  
  /// Legacy network discovery (fallback if platform services unavailable)
  Future<void> discoverPlatform() async {
    if (_isDiscovering) return;
    
    _isDiscovering = true;
    _discoveredPlatforms.clear();
    _statusMessage = 'Scanning network for platforms (legacy)...';
    notifyListeners();

    try {
      // Add timeout to discovery process
      final results = await NetworkDiscoveryService.instance.discoverPlatform()
          .timeout(const Duration(minutes: 1));
      _discoveredPlatforms = results;
      
      if (results.isNotEmpty) {
        _statusMessage = 'Found ${results.length} platform(s). Tap to connect.';
      } else {
        _statusMessage = 'No platforms discovered. Try manual connection below.';
      }
    } catch (e) {
      _statusMessage = 'Discovery timeout or failed. Please use manual connection.';
      print('Discovery error: $e');
    } finally {
      _isDiscovering = false;
      notifyListeners();
    }
  }

  /// Get platform services info after login (replaces slow network discovery)
  Future<void> getPlatformServices(String nodeServiceUrl, String bearerToken) async {
    try {
      _isDiscovering = true;
      _discoveredPlatforms.clear();
      _statusMessage = 'Getting platform services...';
      notifyListeners();

      // Call the platform services endpoint
      final uri = Uri.parse('$nodeServiceUrl/api/v1/users/platform/services');
      final response = await http.get(
        uri,
        headers: {
          'Authorization': 'Bearer $bearerToken',
          'Accept': 'application/json',
        },
      ).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        final data = json.decode(response.body) as Map<String, dynamic>;
        
        // Extract platform information
        final platformInfo = data['platform_info'] as Map<String, dynamic>;
        final connectivity = data['connectivity'] as Map<String, dynamic>;
        final microservices = data['microservices'] as Map<String, dynamic>;
        final mobileConfig = data['mobile_camera_config'] as Map<String, dynamic>;
        
        // Create platform discovery results from the microservices
        final platforms = <PlatformDiscoveryResult>[];
        
        // Add recommended media service
        if (microservices.containsKey('media')) {
          final media = microservices['media'] as Map<String, dynamic>;
          platforms.add(PlatformDiscoveryResult.reachable(
            ipAddress: connectivity['local_ip'],
            port: media['port'],
            responseTime: Duration(milliseconds: 50),
            healthData: {
              'service': 'ppl-meta-media',
              'status': 'healthy',
              'purpose': media['purpose'],
              'recommended': true,
            },
          ));
        }
        
        // Add cameras service as fallback
        if (microservices.containsKey('cameras')) {
          final cameras = microservices['cameras'] as Map<String, dynamic>;
          platforms.add(PlatformDiscoveryResult.reachable(
            ipAddress: connectivity['local_ip'],
            port: cameras['port'],
            responseTime: Duration(milliseconds: 100),
            healthData: {
              'service': 'ppl-meta-cameras',
              'status': 'healthy',
              'purpose': cameras['purpose'],
              'recommended': false,
            },
          ));
        }
        
        _discoveredPlatforms = platforms;
        _statusMessage = 'Found ${platforms.length} platform services. Recommended: Media Service.';
      } else {
        _statusMessage = 'Failed to get platform services. Try manual connection.';
      }
    } catch (e) {
      _statusMessage = 'Platform services discovery failed. Use manual connection.';
      print('Platform services error: $e');
    } finally {
      _isDiscovering = false;
      notifyListeners();
    }
  }

  /// Connect to a discovered or manually entered platform
  Future<bool> connectToPlatform([String? platformUrl]) async {
    try {
      // Use provided URL or get from authenticated session
      final authService = AuthenticationService.instance;
      final targetUrl = platformUrl ?? authService.serverUrl;
      
      if (targetUrl.isEmpty) {
        print('❌ No platform URL provided and no authenticated server URL available');
        _status = MobileCameraStatus.offline;
        _statusMessage = 'No platform URL available';
        notifyListeners();
        return false;
      }
      
      print('🔗 Connecting to platform: $targetUrl');
      _platformUrl = targetUrl;
      _status = MobileCameraStatus.connecting;
      _statusMessage = 'Connecting to platform...';
      notifyListeners();

      // Parse URL to extract IP and port
      final uri = Uri.parse(targetUrl);
      final host = uri.host;
      final port = uri.port != 0 ? uri.port : 8005; // Default to cameras service port
      
      // Test platform connectivity
      print('🔍 Testing platform connectivity to $host:$port');
      final result = await NetworkDiscoveryService.instance.testPlatformEndpoint(host, port);
      final isReachable = result.isReachable;
      if (!isReachable) {
        print('❌ Platform unreachable at $host:$port');
        _status = MobileCameraStatus.offline;
        _statusMessage = 'Platform unreachable at $host:$port';
        notifyListeners();
        return false;
      }

      print('✅ Platform connectivity confirmed');
      
      // Verify we have authentication token from user login
      if (authService.token?.isEmpty ?? true) {
        print('❌ No authentication token available - user must login first');
        _status = MobileCameraStatus.offline;
        _statusMessage = 'Authentication required - please login first';
        notifyListeners();
        return false;
      }
      
      print('✅ Using authenticated session for platform connection');
      _isConnectedToPlatform = true;
      _status = MobileCameraStatus.connected;
      _statusMessage = 'Connected to platform with authenticated session';
      notifyListeners();
      
      return true;
    } catch (e) {
      print('💥 Platform connection error: $e');
      _isConnectedToPlatform = false;
      _status = MobileCameraStatus.error;
      _statusMessage = 'Connection failed: $e';
      notifyListeners();
      return false;
    }
  }

  /// Disconnect from platform
  Future<void> disconnectFromPlatform() async {
    if (_isStreaming) {
      await stopStreaming();
    }
    
    if (_isRegistered) {
      await unregisterCamera();
    }

    _platformUrl = null;
    _isConnectedToPlatform = false;
    _status = MobileCameraStatus.offline;
    _statusMessage = 'Disconnected from platform';
    notifyListeners();
  }

  /// Register this mobile device as a camera on the platform
  Future<bool> registerCamera({String? customName}) async {
    print('🔗 registerCamera() called - customName: $customName');
    
    if (!_isConnectedToPlatform || _platformUrl == null) {
      print('❌ Registration failed - not connected to platform');
      print('   _isConnectedToPlatform: $_isConnectedToPlatform');
      print('   _platformUrl: $_platformUrl');
      _statusMessage = 'Not connected to platform';
      notifyListeners();
      return false;
    }

    try {
      print('📝 Starting camera registration process...');
      _status = MobileCameraStatus.registering;
      _statusMessage = 'Registering camera...';
      notifyListeners();

      // Get camera interface for capability info
      final cameraInterface = CameraInterface.instance;
      if (cameraInterface == null) {
        print('❌ Camera interface not available');
        throw Exception('Camera interface not available');
      }

      // Create camera info
      final deviceId = 'mobile_camera_${DateTime.now().millisecondsSinceEpoch}';
      final deviceName = customName ?? 'Mobile Camera';
      
      print('📱 Creating camera info:');
      print('   deviceId: $deviceId');
      print('   deviceName: $deviceName');
      print('   localIP: ${_getLocalIP()}');
      print('   port: ${_streamingConfig.port}');
      
      _cameraInfo = MobileCameraInfo(
        id: deviceId,
        name: deviceName,
        deviceName: deviceName,
        deviceId: deviceId,
        cameraType: 'MOBILE',
        status: 'REGISTERING',
        connectionString: 'mjpeg://${_getLocalIP()}:${_streamingConfig.port}',
        ipAddress: _getLocalIP() ?? '127.0.0.1',
        port: _streamingConfig.port,
        resolution: '${_streamingConfig.width}x${_streamingConfig.height}',
      );

      // Set platform URL for registration service
      print('🌐 Setting platform URL: $_platformUrl');
      CameraRegistrationService.instance.setPlatformUrl(_platformUrl!);
      
      print('🚀 Calling CameraRegistrationService.registerMobileCamera...');
      final result = await CameraRegistrationService.instance.registerMobileCamera(
        customName: deviceName,
        streamingPort: _streamingConfig.port,
        resolutionWidth: _streamingConfig.width,
        resolutionHeight: _streamingConfig.height,
        maxFps: _streamingConfig.fps,
        supportsAudio: false,
      );

      print('📝 Registration result received:');
      print('   success: ${result.success}');
      print('   deviceId: ${result.deviceId}');
      print('   message: ${result.message}');

      final success = result.success;

      if (success) {
        print('✅ Camera registration successful!');
        _isRegistered = true;
        _registeredDeviceId = result.deviceId ?? _cameraInfo!.deviceId;
        _status = MobileCameraStatus.registered;
        _statusMessage = 'Camera registered successfully';
        
        // Update camera info with registration response
        if (result.cameraInfo != null) {
          print('📱 Updating camera info from registration response');
          _cameraInfo = result.cameraInfo;
        }
      } else {
        print('❌ Camera registration failed: ${result.message}');
        _status = MobileCameraStatus.connected;
        _statusMessage = result.message ?? 'Registration failed';
      }
      
      notifyListeners();
      return success;
    } catch (e) {
      print('💥 Exception during camera registration: $e');
      _status = MobileCameraStatus.error;
      _statusMessage = 'Registration failed: $e';
      notifyListeners();
      return false;
    }
  }

  /// Unregister camera from platform
  Future<bool> unregisterCamera() async {
    if (!_isRegistered || _platformUrl == null || _registeredDeviceId == null) {
      return true; // Already unregistered
    }

    try {
      final success = await CameraRegistrationService.instance.unregisterCamera();

      if (success) {
        _isRegistered = false;
        _registeredDeviceId = null;
        _cameraInfo = null;
        _status = MobileCameraStatus.connected;
        _statusMessage = 'Camera unregistered';
      } else {
        _statusMessage = 'Unregistration failed';
      }
      
      notifyListeners();
      return success;
    } catch (e) {
      _statusMessage = 'Unregistration failed: $e';
      notifyListeners();
      return false;
    }
  }

  /// Start MJPEG streaming
  Future<bool> startStreaming() async {
    if (!_isRegistered || _isStreaming) {
      return false;
    }

    try {
      _status = MobileCameraStatus.streaming;
      _statusMessage = 'Starting stream...';
      notifyListeners();

      // Get camera interface
      final cameraInterface = CameraInterface.instance;
      if (cameraInterface == null || !cameraInterface.isInitialized) {
        throw Exception('Camera not available');
      }

      // Start MJPEG server
      final success = await MJPEGStreamingService.instance.startStreaming(
        port: _streamingConfig.port,
        config: StreamingConfig(
          width: _streamingConfig.width,
          height: _streamingConfig.height,
          quality: _streamingConfig.quality,
          fps: _streamingConfig.fps,
          port: _streamingConfig.port,
        ),
      );

      if (success) {
        // Start image stream from camera
        await cameraInterface.startImageStream((image) {
          MJPEGStreamingService.instance.sendFrame(image);
        });

        _isStreaming = true;
        _statusMessage = 'Streaming active';
        
        // Update streaming stats periodically
        _updateStreamingStats();
      } else {
        _status = MobileCameraStatus.registered;
        _statusMessage = 'Failed to start streaming server';
      }
      
      notifyListeners();
      return success;
    } catch (e) {
      _status = MobileCameraStatus.error;
      _statusMessage = 'Streaming failed: $e';
      notifyListeners();
      return false;
    }
  }

  /// Stop MJPEG streaming
  Future<void> stopStreaming() async {
    if (!_isStreaming) return;

    try {
      // Stop image stream from camera
      final cameraInterface = CameraInterface.instance;
      if (cameraInterface != null) {
        await cameraInterface.stopImageStream();
      }

      // Stop MJPEG server
      await MJPEGStreamingService.instance.stopStreaming();

      _isStreaming = false;
      _streamingStats = null;
      _status = _isRegistered ? MobileCameraStatus.registered : MobileCameraStatus.connected;
      _statusMessage = 'Streaming stopped';
      notifyListeners();
    } catch (e) {
      _statusMessage = 'Error stopping stream: $e';
      notifyListeners();
    }
  }

  /// Update streaming configuration
  void updateStreamingConfig(StreamingConfig config) {
    _streamingConfig = config;
    notifyListeners();
    
    // If streaming, restart with new config
    if (_isStreaming) {
      stopStreaming().then((_) => startStreaming());
    }
  }

  /// Update streaming statistics
  void _updateStreamingStats() {
    if (!_isStreaming) return;
    
    // Get stats from MJPEG service
    final mjpegStats = MJPEGStreamingService.instance.stats;
    
    if (mjpegStats != null) {
      _streamingStats = StreamingStats(
        framesSent: mjpegStats.framesSent,
        framesDropped: mjpegStats.framesDropped,
        averageFps: mjpegStats.averageFps,
        averageLatency: mjpegStats.averageLatency,
        totalBytesSent: mjpegStats.totalBytesSent,
        startTime: mjpegStats.startTime,
        uptime: mjpegStats.uptime,
      );
    }
    
    notifyListeners();
    
    // Schedule next update
    if (_isStreaming) {
      Future.delayed(const Duration(seconds: 1), () => _updateStreamingStats());
    }
  }

  /// Get streaming URL for this device
  String? getStreamingUrl() {
    if (!_isStreaming) return null;
    
    // This would typically be the device's IP address + MJPEG server port
    // For now, return a placeholder that shows the concept
    return 'http://[device-ip]:${_streamingConfig.port}/stream';
  }

  /// Get local IP address
  String? _getLocalIP() {
    try {
      // This is a simplified approach - in a real app you'd use network_info_plus
      return '192.168.1.100'; // Placeholder - should get actual IP
    } catch (e) {
      return null;
    }
  }

  @override
  void dispose() {
    if (_isStreaming) {
      stopStreaming();
    }
    if (_isConnectedToPlatform) {
      disconnectFromPlatform();
    }
    super.dispose();
  }
}