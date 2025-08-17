import 'dart:async';
import 'dart:convert';
import 'package:dio/dio.dart';
import '../models/camera.dart';
import '../models/rtsp_camera.dart';
import '../models/collection_models.dart';
import '../api/api_client.dart';
import 'camera_collection_service.dart';

/// Multi-camera management service with RTSP support
class MultiCameraService {
  final ApiClient _apiClient;
  final CameraCollectionService _collectionService;
  final Map<String, RTSPCamera> _rtspCameras = {};
  final Map<String, Timer> _connectionMonitors = {};
  
  static const String _cameraServiceUrl = String.fromEnvironment(
    'CAMERA_SERVICE_URL',
    defaultValue: 'http://localhost:8005',
  );

  MultiCameraService(this._apiClient) : _collectionService = CameraCollectionService(_apiClient);

  /// Get all cameras (USB + RTSP)
  Future<List<Camera>> getAllCameras() async {
    try {
      final usbCameras = await getUSBCameras();
      final rtspCameras = await getRTSPCameras();
      
      return [...usbCameras, ...rtspCameras];
    } catch (e) {
      throw CameraException('Failed to get all cameras: $e');
    }
  }

  /// Get USB cameras from camera service
  Future<List<Camera>> getUSBCameras() async {
    try {
      final response = await _apiClient.dio.get('$_cameraServiceUrl/api/v1/cameras');
      
      if (response.statusCode == 200) {
        // API returns direct array of cameras, not wrapped in an object
        final dynamic responseData = response.data;
        final List<dynamic> camerasJson = responseData is List 
            ? responseData 
            : (responseData['cameras'] ?? []);
            
        return camerasJson
            .map((json) => Camera.fromJson(json as Map<String, dynamic>))
            .where((camera) => camera.type == CameraType.usb)
            .toList();
      } else {
        throw CameraException('Failed to load USB cameras: ${response.statusMessage}');
      }
    } on DioException catch (e) {
      if (e.response?.statusCode == 401) {
        throw CameraException('Authentication failed');
      }
      throw CameraException('Network error: ${e.message}');
    } catch (e) {
      throw CameraException('Error loading USB cameras: $e');
    }
  }

  /// Get RTSP cameras from local storage and verify connections
  Future<List<Camera>> getRTSPCameras() async {
    final List<Camera> rtspCameras = [];
    
    for (final rtspCamera in _rtspCameras.values) {
      // Test connection to determine status
      final isConnected = await _testRTSPConnection(rtspCamera);
      final camera = rtspCamera.copyWith(
        isActive: isConnected,
        lastConnected: isConnected ? DateTime.now() : null,
      ).toCamera();
      
      rtspCameras.add(camera);
    }
    
    return rtspCameras;
  }

  /// Add RTSP camera configuration
  Future<Camera> addRTSPCamera({
    required String name,
    required String host,
    int port = 554,
    required String username,
    required String password,
    String streamPath = '/stream',
    RTSPTransport transport = RTSPTransport.tcp,
    RTSPProfile profile = RTSPProfile.main,
  }) async {
    final id = DateTime.now().millisecondsSinceEpoch.toString();
    
    final rtspCamera = RTSPCamera(
      id: id,
      name: name,
      host: host,
      port: port,
      username: username,
      password: password,
      streamPath: streamPath,
      transport: transport,
      profile: profile,
    );

    // Test connection before adding
    final isConnected = await _testRTSPConnection(rtspCamera);
    
    final activeCamera = rtspCamera.copyWith(
      isActive: isConnected,
      lastConnected: isConnected ? DateTime.now() : null,
    );

    _rtspCameras[id] = activeCamera;
    
    // Start connection monitoring
    _startConnectionMonitoring(activeCamera);
    
    final camera = activeCamera.toCamera();
    
    // Automatically create collection for this RTSP camera
    try {
      await _collectionService.setupCameraWithCollection(camera);
      print('✅ Auto-created collection for RTSP camera: $name');
    } catch (e) {
      print('⚠️ Failed to auto-create collection for RTSP camera $name: $e');
      // Don't fail the camera creation if collection creation fails
    }
    
    return camera;
  }

  /// Remove RTSP camera
  Future<void> removeRTSPCamera(String cameraId) async {
    _rtspCameras.remove(cameraId);
    _connectionMonitors[cameraId]?.cancel();
    _connectionMonitors.remove(cameraId);
  }

  /// Update RTSP camera configuration
  Future<Camera> updateRTSPCamera(String cameraId, RTSPCamera updatedCamera) async {
    final oldCamera = _rtspCameras[cameraId];
    if (oldCamera == null) {
      throw CameraException('RTSP camera not found: $cameraId');
    }

    // Test new connection
    final isConnected = await _testRTSPConnection(updatedCamera);
    
    final activeCamera = updatedCamera.copyWith(
      isActive: isConnected,
      lastConnected: isConnected ? DateTime.now() : null,
    );

    _rtspCameras[cameraId] = activeCamera;
    
    // Restart connection monitoring
    _connectionMonitors[cameraId]?.cancel();
    _startConnectionMonitoring(activeCamera);
    
    return activeCamera.toCamera();
  }

  /// Test RTSP camera connection
  Future<bool> _testRTSPConnection(RTSPCamera camera) async {
    try {
      // For now, we'll use a simple TCP socket test
      // In a real implementation, you'd use an RTSP library
      final dio = Dio();
      dio.options.connectTimeout = const Duration(seconds: 5);
      dio.options.receiveTimeout = const Duration(seconds: 5);
      
      // Try to connect to RTSP describe endpoint
      final response = await dio.get(
        'http://${camera.host}:${camera.port}/describe',
        options: Options(
          headers: {
            'Authorization': 'Basic ${base64Encode(utf8.encode('${camera.username}:${camera.password}'))}',
          },
        ),
      );
      
      return response.statusCode == 200;
    } catch (e) {
      return false;
    }
  }

  /// Start monitoring RTSP camera connection
  void _startConnectionMonitoring(RTSPCamera camera) {
    _connectionMonitors[camera.id] = Timer.periodic(
      const Duration(seconds: 30),
      (timer) async {
        final isConnected = await _testRTSPConnection(camera);
        final updatedCamera = camera.copyWith(
          isActive: isConnected,
          lastConnected: isConnected ? DateTime.now() : camera.lastConnected,
        );
        
        _rtspCameras[camera.id] = updatedCamera;
      },
    );
  }

  /// Get camera by ID (USB or RTSP)
  Future<Camera?> getCameraById(String cameraId) async {
    try {
      // Check RTSP cameras first
      final rtspCamera = _rtspCameras[cameraId];
      if (rtspCamera != null) {
        return rtspCamera.toCamera();
      }

      // Check USB cameras
      final response = await _apiClient.dio.get('$_cameraServiceUrl/api/v1/cameras/$cameraId');
      
      if (response.statusCode == 200) {
        return Camera.fromJson(response.data);
      }
      
      return null;
    } catch (e) {
      return null;
    }
  }

  /// Start streaming for any camera type
  Future<void> startStreaming(String cameraId) async {
    try {
      final camera = await getCameraById(cameraId);
      if (camera == null) {
        throw CameraException('Camera not found: $cameraId');
      }

      // Ensure collection exists for this camera (will use existing or create new)
      try {
        await _collectionService.setupCameraWithCollection(camera);
        print('✅ Collection ensured for camera: ${camera.name}');
      } catch (e) {
        print('⚠️ Failed to ensure collection for camera ${camera.name}: $e');
        // Don't fail streaming if collection setup fails
      }

      if (camera.type == CameraType.rtsp) {
        // For RTSP cameras, streaming is handled differently
        await _startRTSPStreaming(cameraId);
      } else {
        // For USB cameras, use existing service
        await _apiClient.dio.post('$_cameraServiceUrl/api/v1/cameras/$cameraId/stream/start');
      }
    } on DioException catch (e) {
      if (e.response?.statusCode == 401) {
        throw CameraException('Authentication failed');
      }
      throw CameraException('Failed to start streaming: ${e.message}');
    }
  }

  /// Stop streaming for any camera type
  Future<void> stopStreaming(String cameraId) async {
    try {
      final camera = await getCameraById(cameraId);
      if (camera == null) {
        throw CameraException('Camera not found: $cameraId');
      }

      if (camera.type == CameraType.rtsp) {
        await _stopRTSPStreaming(cameraId);
      } else {
        await _apiClient.dio.post('$_cameraServiceUrl/api/v1/cameras/$cameraId/stream/stop');
      }
    } on DioException catch (e) {
      throw CameraException('Failed to stop streaming: ${e.message}');
    }
  }

  /// Start RTSP streaming (implementation depends on your streaming architecture)
  Future<void> _startRTSPStreaming(String cameraId) async {
    final rtspCamera = _rtspCameras[cameraId];
    if (rtspCamera == null) {
      throw CameraException('RTSP camera not found: $cameraId');
    }

    // Here you would integrate with your streaming infrastructure
    // For now, we'll just mark it as active
    _rtspCameras[cameraId] = rtspCamera.copyWith(isActive: true);
  }

  /// Stop RTSP streaming
  Future<void> _stopRTSPStreaming(String cameraId) async {
    final rtspCamera = _rtspCameras[cameraId];
    if (rtspCamera != null) {
      _rtspCameras[cameraId] = rtspCamera.copyWith(isActive: false);
    }
  }

  /// Take snapshot from any camera type
  Future<String> takeSnapshot(String cameraId) async {
    try {
      final camera = await getCameraById(cameraId);
      if (camera == null) {
        throw CameraException('Camera not found: $cameraId');
      }

      if (camera.type == CameraType.rtsp) {
        return await _takeRTSPSnapshot(cameraId);
      } else {
        final response = await _apiClient.dio.post('$_cameraServiceUrl/api/v1/cameras/$cameraId/snapshot');
        return response.data['snapshot_url'] ?? '';
      }
    } on DioException catch (e) {
      if (e.response?.statusCode == 401) {
        throw CameraException('Authentication failed');
      }
      throw CameraException('Failed to take snapshot: ${e.message}');
    }
  }

  /// Take snapshot from RTSP camera
  Future<String> _takeRTSPSnapshot(String cameraId) async {
    final rtspCamera = _rtspCameras[cameraId];
    if (rtspCamera == null) {
      throw CameraException('RTSP camera not found: $cameraId');
    }

    // Implementation would depend on your RTSP snapshot mechanism
    // For now, return a placeholder URL
    return '${rtspCamera.rtspUrl}/snapshot';
  }

  /// Get streaming info for any camera type
  Future<StreamingInfo?> getStreamingInfo(String cameraId) async {
    try {
      final camera = await getCameraById(cameraId);
      if (camera == null) return null;

      if (camera.type == CameraType.rtsp) {
        return _getRTSPStreamingInfo(cameraId);
      } else {
        final response = await _apiClient.dio.get('$_cameraServiceUrl/api/v1/cameras/$cameraId/streaming-info');
        
        if (response.statusCode == 200) {
          return StreamingInfo.fromJson(response.data);
        }
        return null;
      }
    } catch (e) {
      return null;
    }
  }

  /// Get RTSP streaming info
  StreamingInfo? _getRTSPStreamingInfo(String cameraId) {
    final rtspCamera = _rtspCameras[cameraId];
    if (rtspCamera == null) return null;

    return StreamingInfo(
      streamId: rtspCamera.id,
      cameraId: rtspCamera.deviceId,
      streamUrl: rtspCamera.rtspUrl,
      status: rtspCamera.isActive ? 'active' : 'inactive',
      startedAt: rtspCamera.lastConnected ?? DateTime.now(),
    );
  }

  /// Get all RTSP camera configurations
  List<RTSPCamera> getRTSPConfigurations() {
    return _rtspCameras.values.toList();
  }

  /// Ensure collection exists for an existing camera (manual trigger)
  Future<MediaCollection?> ensureCameraCollection(String cameraId) async {
    try {
      final camera = await getCameraById(cameraId);
      if (camera == null) {
        throw CameraException('Camera not found: $cameraId');
      }
      
      final collection = await _collectionService.setupCameraWithCollection(camera);
      print('✅ Collection ensured for camera: ${camera.name}');
      return collection;
    } catch (e) {
      print('❌ Failed to ensure collection for camera $cameraId: $e');
      rethrow;
    }
  }

  /// Dispose resources
  void dispose() {
    for (final timer in _connectionMonitors.values) {
      timer.cancel();
    }
    _connectionMonitors.clear();
  }
}

/// Camera-specific exception
class CameraException implements Exception {
  final String message;
  
  const CameraException(this.message);
  
  @override
  String toString() => 'CameraException: $message';
}
