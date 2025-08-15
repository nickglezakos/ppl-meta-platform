import 'package:dio/dio.dart';
import '../api/api_client.dart';
import '../config/app_config.dart';
import '../models/camera.dart';
import '../models/snapshot_settings.dart';
import '../models/snapshot_result.dart';
import 'camera_collection_service.dart';

/// API Error model for error handling
class ApiError {
  final String detail;
  final String? code;

  ApiError({required this.detail, this.code});

  factory ApiError.fromJson(Map<String, dynamic> json) {
    return ApiError(
      detail: json['detail'] ?? json['message'] ?? 'Unknown error',
      code: json['code']?.toString(),
    );
  }
}

/// Exception thrown when camera operations fail
class CameraException implements Exception {
  final String message;
  final String? code;

  const CameraException(this.message, {this.code});

  @override
  String toString() => message;
}

/// Service for camera operations
class CameraService {
  final ApiClient _apiClient;
  final CameraCollectionService _collectionService;
  late final Dio _cameraApiClient;

  CameraService(this._apiClient) : _collectionService = CameraCollectionService(_apiClient) {
    // Create dedicated camera service API client
    print('Camera service baseUrl: ${AppConfig.instance.cameraServiceUrl}');
    _cameraApiClient = Dio(BaseOptions(
      baseUrl: AppConfig.instance.cameraServiceUrl,
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 30),
      headers: {
        'Content-Type': 'application/json',
      },
    ));
    
    // Add auth interceptor for camera service
    _cameraApiClient.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) {
        final token = _apiClient.authToken;
        if (token != null) {
          options.headers['Authorization'] = 'Bearer $token';
        }
        handler.next(options);
      },
    ));
  }

  /// Detect available cameras
  Future<List<Camera>> detectCameras({bool saveToDb = true}) async {
    try {
      final response = await _cameraApiClient.post(
        '/api/v1/cameras/detect',
        queryParameters: {'save_to_db': saveToDb},
      );

      if (response.data == null) {
        throw const CameraException('Invalid response from camera service');
      }

      // The detect endpoint returns an object with 'cameras' array
      List<dynamic> camerasData;
      if (response.data is Map && response.data['cameras'] != null) {
        camerasData = response.data['cameras'] as List<dynamic>;
      } else if (response.data is List) {
        camerasData = response.data as List<dynamic>;
      } else {
        throw const CameraException('Invalid cameras data in response');
      }

      return camerasData
          .map((camera) => Camera.fromJson(camera as Map<String, dynamic>))
          .toList();
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// Get list of all cameras
  Future<List<Camera>> getCameras() async {
    try {
      final response = await _cameraApiClient.get('/api/v1/cameras/');

      if (response.data == null) {
        throw const CameraException('Invalid response from camera service');
      }

      // The cameras endpoint returns an array directly
      List<dynamic> camerasData;
      if (response.data is List) {
        camerasData = response.data as List<dynamic>;
      } else if (response.data is Map && response.data['cameras'] != null) {
        camerasData = response.data['cameras'] as List<dynamic>;
      } else {
        throw const CameraException('Invalid cameras data in response');
      }

      return camerasData
          .map((camera) => Camera.fromJson(camera as Map<String, dynamic>))
          .toList();
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// Get camera details by ID
  Future<Camera> getCameraById(String cameraId) async {
    try {
      final response = await _cameraApiClient.get<Map<String, dynamic>>(
        '/api/v1/cameras/$cameraId/info',
      );

      if (response.data == null) {
        throw const CameraException('Invalid response from camera service');
      }

      return Camera.fromJson(response.data!);
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// Start streaming for a camera with quality controls
  Future<StreamingInfo> startStreaming(
    String cameraId, {
    String quality = 'high',
    int fps = 30,
    String resolution = '1280x720',
    String format = 'MJPEG',
  }) async {
    try {
      final response = await _cameraApiClient.post<Map<String, dynamic>>(
        '/api/v1/streaming/$cameraId/start',
        data: {
          'quality': quality,
          'fps': fps,
          'resolution': resolution,
          'format': format,
        },
      );

      if (response.data == null) {
        throw const CameraException('Invalid response from streaming service');
      }

      return StreamingInfo.fromJson(response.data!);
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// Get the MJPEG video stream URL for a camera
  String getVideoStreamUrl(String cameraId) {
    // This follows the pattern from the API guide: /api/v1/streaming/{device_id}/video
    return '${AppConfig.instance.cameraServiceUrl}/api/v1/streaming/$cameraId/video';
  }

  /// Create a streaming session for browser-compatible authentication
  Future<Map<String, dynamic>?> createStreamingSession(String cameraId) async {
    try {
      final response = await _cameraApiClient.post<Map<String, dynamic>>(
        '/api/v1/auth/streaming-session/$cameraId',
      );

      if (response.statusCode == 200 && response.data != null) {
        return response.data!;
      } else {
        throw CameraException('Failed to create streaming session: ${response.statusCode}');
      }
    } catch (e) {
      print('Error creating streaming session: $e');
      return null;
    }
  }

  /// Stop streaming for a camera
  Future<void> stopStreaming(String cameraId) async {
    try {
      await _cameraApiClient.post<Map<String, dynamic>>(
        '/api/v1/streaming/$cameraId/stop',
      );
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// Get streaming status for a camera
  Future<StreamingStatus> getStreamingStatus(String cameraId) async {
    try {
      final response = await _cameraApiClient.get<Map<String, dynamic>>(
        '/api/v1/streaming/$cameraId/status',
      );

      if (response.data == null) {
        throw const CameraException('Invalid response from streaming service');
      }

      return StreamingStatus.fromJson(response.data!);
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

    /// Capture snapshot from a camera
  Future<SnapshotResult> captureSnapshot(String deviceId) async {
    try {
      final response = await _cameraApiClient.get<Map<String, dynamic>>(
        '/api/v1/streaming/$deviceId/snapshot',
      );

      if (response.statusCode == 200 && response.data != null) {
        final data = response.data!;
        
        // Extract base64 data from the data URL format
        final dataUrl = data['data'] as String? ?? '';
        String base64Image = '';
        
        if (dataUrl.startsWith('data:image/jpeg;base64,')) {
          base64Image = dataUrl.substring('data:image/jpeg;base64,'.length);
        } else {
          throw const CameraException('Invalid image data format');
        }

        return SnapshotResult.fromBinary(
          deviceId: deviceId,
          base64Image: base64Image,
        );
      } else {
        throw CameraException('Failed to capture snapshot: ${response.statusCode}');
      }
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// Update camera settings
  Future<Camera> updateCamera(String cameraId, CameraUpdateRequest request) async {
    try {
      final response = await _cameraApiClient.put<Map<String, dynamic>>(
        '/api/v1/cameras/$cameraId',
        data: request.toJson(),
      );

      if (response.data == null) {
        throw const CameraException('Invalid response from camera service');
      }

      return Camera.fromJson(response.data!);
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// Delete a camera
  Future<void> deleteCamera(String cameraId) async {
    try {
      await _cameraApiClient.delete('/api/v1/cameras/$cameraId');
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// Connect to a camera following the proper workflow:
  /// 1. Disconnect all cameras first
  /// 2. Re-detect cameras to refresh state
  /// 3. Connect to the specific camera
  /// 4. Auto-create collection for the camera
  Future<bool> connectCamera(String deviceId) async {
    try {
      print('Step 1: Disconnecting all cameras...');
      // Step 1: Disconnect all cameras first
      await disconnectAllCameras();
      
      print('Step 2: Re-detecting cameras...');
      // Step 2: Re-detect cameras to refresh state
      await detectCameras(saveToDb: true);
      
      print('Step 3: Connecting to camera $deviceId...');
      // Step 3: Connect to the specific camera
      final response = await _cameraApiClient.post<Map<String, dynamic>>(
        '/api/v1/cameras/$deviceId/connect',
      );
      
      if (response.statusCode == 200) {
        print('✅ Successfully connected to camera $deviceId');
        
        // Step 4: Auto-create collection for this USB camera
        try {
          // Get camera details to get the name
          final cameras = await getCameras();
          final camera = cameras.firstWhere(
            (cam) => cam.deviceId == deviceId,
            orElse: () => Camera(
              id: deviceId,
              deviceId: deviceId,
              name: 'USB Camera $deviceId',
              status: 'connected',
              type: CameraType.usb,
              isActive: true,
            ),
          );
          
          await _collectionService.setupCameraWithCollection(camera);
          print('✅ Auto-created collection for USB camera: ${camera.name}');
        } catch (e) {
          print('⚠️ Failed to auto-create collection for USB camera $deviceId: $e');
          // Don't fail the camera connection if collection creation fails
        }
        
        return true;
      } else {
        print('❌ Failed to connect to camera $deviceId: ${response.statusCode}');
        return false;
      }
    } catch (e) {
      print('Error in camera connection workflow: $e');
      return false;
    }
  }

  /// Disconnect from a camera
  Future<bool> disconnectCamera(String cameraId) async {
    try {
      final response = await _cameraApiClient.post<Map<String, dynamic>>(
        '/api/v1/cameras/$cameraId/disconnect',
      );

      if (response.data == null) {
        throw const CameraException('Invalid response from camera service');
      }

      // Return true if successful
      return response.data!['success'] == true || response.statusCode == 200;
    } catch (e) {
      if (e is DioException) {
        throw _handleDioError(e);
      }
      throw CameraException('Failed to disconnect camera: ${e.toString()}');
    }
  }

  /// Disconnect all cameras
  Future<bool> disconnectAllCameras() async {
    try {
      final response = await _cameraApiClient.post<Map<String, dynamic>>(
        '/api/v1/cameras/disconnect-all',
      );

      if (response.data == null) {
        throw const CameraException('Invalid response from camera service');
      }

      return response.statusCode == 200;
    } catch (e) {
      if (e is DioException) {
        throw _handleDioError(e);
      }
      throw CameraException('Failed to disconnect all cameras: ${e.toString()}');
    }
  }

  /// Handle API errors and convert to CameraException
  /// Capture enhanced snapshot with custom settings
  Future<EnhancedSnapshotResult> captureEnhancedSnapshot(
    String cameraId, {
    SnapshotSettings? settings,
  }) async {
    try {
      final snapshotSettings = settings ?? const SnapshotSettings();
      
      final response = await _cameraApiClient.post<Map<String, dynamic>>(
        '/api/v1/streaming/$cameraId/snapshot', // Direct to cameras service
        data: snapshotSettings.toJson(),
      );

      if (response.data == null) {
        throw const CameraException('Invalid response from camera service');
      }

      return EnhancedSnapshotResult.fromJson(response.data!);
    } on DioException catch (e) {
      throw _handleDioError(e);
    } catch (e) {
      throw CameraException('Failed to capture enhanced snapshot: $e');
    }
  }

  /// Get camera capabilities including supported resolutions
  Future<CameraCapabilities> getCameraCapabilities(String cameraId) async {
    try {
      final fullUrl = '${AppConfig.instance.cameraServiceUrl}/api/v1/streaming/$cameraId/capabilities';
      print('Requesting capabilities from: $fullUrl');
      
      final response = await _cameraApiClient.get<Map<String, dynamic>>(
        '/api/v1/streaming/$cameraId/capabilities', // Direct to cameras service
      );

      if (response.data == null) {
        throw const CameraException('Invalid response from camera service');
      }

      return CameraCapabilities.fromJson(response.data!);
    } on DioException catch (e) {
      print('DioException in getCameraCapabilities: ${e.message}');
      print('Request URL: ${e.requestOptions.uri}');
      throw _handleDioError(e);
    } catch (e) {
      print('Error in getCameraCapabilities: $e');
      throw CameraException('Failed to get camera capabilities: $e');
    }
  }

  /// Add RTSP camera configuration
  Future<Camera> addRTSPCamera({
    required String name,
    required String host,
    required int port,
    required String path,
    String? username,
    String? password,
  }) async {
    try {
      final response = await _cameraApiClient.post(
        '/api/v1/cameras/rtsp',
        data: {
          'name': name,
          'host': host,
          'port': port,
          'path': path,
          if (username != null && username.isNotEmpty) 'username': username,
          if (password != null && password.isNotEmpty) 'password': password,
        },
      );

      if (response.data == null || response.data['camera'] == null) {
        throw const CameraException('Invalid response from camera service');
      }

      // Convert the backend response to frontend Camera model
      final cameraData = response.data['camera'] as Map<String, dynamic>;
      
      return Camera(
        id: cameraData['device_id'] ?? 'unknown',
        deviceId: cameraData['device_id'] ?? 'unknown',
        name: cameraData['name'] ?? 'Unknown RTSP Camera',
        type: CameraType.rtsp,
        status: cameraData['status'] ?? 'disconnected',
        resolution: cameraData['resolution'] ?? '1920x1080',
        isActive: cameraData['status'] == 'connected',
        lastSeen: cameraData['last_seen'] != null 
            ? DateTime.parse(cameraData['last_seen']) 
            : DateTime.now(),
        metadata: {
          'rtsp_url': cameraData['rtsp_url'],
          'supports_streaming': cameraData['supports_streaming'] ?? true,
          'supports_recording': cameraData['supports_recording'] ?? false,
          'max_fps': cameraData['max_fps'] ?? 30,
          'created_at': cameraData['created_at'],
        },
      );
    } on DioException catch (e) {
      throw _handleDioError(e);
    } catch (e) {
      throw CameraException('Failed to add RTSP camera: $e');
    }
  }

  /// Update RTSP camera configuration
  Future<Camera> updateRTSPCamera({
    required String deviceId,
    required String name,
    required String host,
    required int port,
    required String path,
    String? username,
    String? password,
  }) async {
    try {
      final response = await _cameraApiClient.put(
        '/api/v1/cameras/rtsp/$deviceId',
        data: {
          'name': name,
          'host': host,
          'port': port,
          'path': path,
          if (username != null && username.isNotEmpty) 'username': username,
          if (password != null && password.isNotEmpty) 'password': password,
        },
      );

      if (response.data == null || response.data['camera'] == null) {
        throw const CameraException('Invalid response from camera service');
      }

      // Convert the backend response to frontend Camera model
      final cameraData = response.data['camera'] as Map<String, dynamic>;
      
      return Camera(
        id: cameraData['device_id'] ?? deviceId,
        deviceId: cameraData['device_id'] ?? deviceId,
        name: cameraData['name'] ?? 'Unknown RTSP Camera',
        type: CameraType.rtsp,
        status: cameraData['status'] ?? 'disconnected',
        resolution: cameraData['resolution'] ?? '1920x1080',
        isActive: cameraData['status'] == 'connected',
        lastSeen: cameraData['last_seen'] != null 
            ? DateTime.parse(cameraData['last_seen']) 
            : DateTime.now(),
        metadata: {
          'rtsp_url': cameraData['rtsp_url'],
          'supports_streaming': cameraData['supports_streaming'] ?? true,
          'supports_recording': cameraData['supports_recording'] ?? false,
          'max_fps': cameraData['max_fps'] ?? 30,
          'created_at': cameraData['created_at'],
        },
      );
    } on DioException catch (e) {
      throw _handleDioError(e);
    } catch (e) {
      throw CameraException('Failed to update RTSP camera: $e');
    }
  }

  /// Delete RTSP camera
  Future<void> deleteRTSPCamera(String deviceId) async {
    try {
      await _cameraApiClient.delete('/api/v1/cameras/rtsp/$deviceId');
    } on DioException catch (e) {
      throw _handleDioError(e);
    } catch (e) {
      throw CameraException('Failed to delete RTSP camera: $e');
    }
  }

  CameraException _handleDioError(DioException e) {
    if (e.response?.data != null) {
      try {
        final apiError = ApiError.fromJson(e.response!.data);
        return CameraException(
          apiError.detail,
          code: e.response?.statusCode.toString(),
        );
      } catch (parseError) {
        // If parsing fails, use status message
      }
    }

    switch (e.type) {
      case DioExceptionType.connectionTimeout:
      case DioExceptionType.receiveTimeout:
      case DioExceptionType.sendTimeout:
        return const CameraException('Connection timeout. Please check your internet connection.');
      case DioExceptionType.connectionError:
        return const CameraException('Unable to connect to camera service. Please try again later.');
      case DioExceptionType.badResponse:
        final statusCode = e.response?.statusCode;
        if (statusCode == 404) {
          return const CameraException('Camera not found.');
        } else if (statusCode == 401) {
          return const CameraException('Unauthorized access to camera service.');
        } else if (statusCode == 403) {
          return const CameraException('Insufficient permissions to access cameras.');
        }
        return CameraException(
          'Camera service error (${statusCode ?? 'unknown'}). Please try again later.',
        );
      default:
        return const CameraException('An unexpected camera error occurred. Please try again.');
    }
  }
}
