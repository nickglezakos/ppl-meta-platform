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
  late final Dio _directCameraClient;

  CameraService(this._apiClient) : _collectionService = CameraCollectionService(_apiClient) {
    // Use the authenticated API client for general operations (goes through gateway)
    print('Camera service using authenticated API client through gateway');
    _cameraApiClient = _apiClient.dio;
    
    // Create a direct client to cameras service for streaming/recording operations
    _directCameraClient = Dio(BaseOptions(
      baseUrl: AppConfig.instance.cameraServiceUrl,
      connectTimeout: const Duration(seconds: 30),
      receiveTimeout: const Duration(seconds: 120),
      sendTimeout: const Duration(seconds: 30),
    ));
    
    // Copy authentication interceptors to the direct client
    for (final interceptor in _apiClient.dio.interceptors) {
      if (interceptor is InterceptorsWrapper) {
        _directCameraClient.interceptors.add(interceptor);
      }
    }
    
    print('Direct camera client configured for: ${AppConfig.instance.cameraServiceUrl}');
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
      final response = await _directCameraClient.post<Map<String, dynamic>>(
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

  /// Create a streaming session for a mobile camera (browser-compatible)
  Future<Map<String, dynamic>?> createMobileStreamingSession(String deviceId) async {
    try {
      final response = await _directCameraClient.post<Map<String, dynamic>>(
        '/api/v1/streaming/mobile/$deviceId/streaming-session',
      );

      if (response.statusCode == 200 && response.data != null) {
        return response.data!;
      } else {
        throw CameraException('Failed to create mobile streaming session: ${response.statusCode}');
      }
    } catch (e) {
      print('Error creating mobile streaming session: $e');
      return null;
    }
  }

  /// Stop streaming for a camera
  Future<void> stopStreaming(String cameraId) async {
    try {
      await _directCameraClient.post<Map<String, dynamic>>(
        '/api/v1/streaming/$cameraId/stop',
      );
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// Get streaming status for a camera
  Future<StreamingStatus> getStreamingStatus(String cameraId) async {
    try {
      final response = await _directCameraClient.get<Map<String, dynamic>>(
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
      final response = await _directCameraClient.get<Map<String, dynamic>>(
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
      
      final response = await _directCameraClient.post<Map<String, dynamic>>(
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
      
      final response = await _directCameraClient.get<Map<String, dynamic>>(
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
        supportsRecording: cameraData['supports_recording'] ?? false,
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
        supportsRecording: cameraData['supports_recording'] ?? false,
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

  /// Start recording for a camera
  Future<RecordingResult> startRecording(String deviceId) async {
    print('🔥 DEBUG CORE: startRecording called for deviceId: $deviceId');
    print('🔥 DEBUG CORE: Using Gateway client for recording operations');
    
    try {
      // Use Gateway for recording operations (has CORS support for browser requests)
      final response = await _cameraApiClient.post(
        '/api/v1/streaming/$deviceId/record/start',
      );

      // Transform response to match RecordingResult format
      final sessionData = response.data as Map<String, dynamic>;
      return RecordingResult.fromJson({
        'session_id': sessionData['recording_id'] ?? sessionData['session_uuid'],
        'device_id': sessionData['device_id'],
        'status': sessionData['status'] ?? 'recording',
        'started_at': sessionData['started_at'],
        'message': sessionData['message'] ?? 'Recording started successfully',
      });
    } on DioException catch (e) {
      // Handle "already recording" state management issue
      if (e.response?.statusCode == 400 && 
          e.response?.data != null && 
          e.response!.data.toString().contains('already recording')) {
        
        print('🔧 Detected stale recording state, clearing and retrying...');
        
        // Clear the stale recording state
        await clearRecordingState(deviceId);
        
        // Retry the recording start with working API
        final retryResponse = await _directCameraClient.post(
          '/streaming/$deviceId/record/start',
        );
        
        final sessionData = retryResponse.data as Map<String, dynamic>;
        return RecordingResult.fromJson({
          'session_id': sessionData['session_uuid'],
          'device_id': sessionData['camera_device_id'],
          'status': sessionData['status'],
          'started_at': sessionData['started_at'],
          'message': 'Recording started successfully after clearing stale state',
        });
      }
      
      throw _handleDioError(e);
    }
  }

  /// Clear stale recording state for a camera
  /// This fixes the state management inconsistency between in-memory active_recordings and database session state
  Future<void> clearRecordingState(String deviceId) async {
    try {
      print('🧹 Clearing stale recording state for camera $deviceId...');
      
      // Use Gateway for recording operations (has CORS support for browser requests)
      final response = await _cameraApiClient.post(
        '/api/v1/streaming/$deviceId/record/clear-state',
      );
      
      if (response.data != null) {
        print('✅ Cleared stale recording state: ${response.data}');
      }
    } on DioException catch (e) {
      print('⚠️ Warning: Failed to clear recording state: ${e.message}');
      // Don't throw here as this is a cleanup operation
    }
  }

  /// Debug recording state for a camera
  /// Returns information about recording state inconsistencies
  Future<Map<String, dynamic>?> debugRecordingState(String deviceId) async {
    try {
      // Use Gateway for recording operations (has CORS support for browser requests)
      final response = await _cameraApiClient.get(
        '/api/v1/streaming/$deviceId/record/debug',
      );
      
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      print('⚠️ Warning: Failed to get debug recording state: ${e.message}');
      return null;
    }
  }

  /// Update camera auto face detection setting
  Future<void> updateAutoFaceDetection(String deviceId, bool enabled) async {
    try {
      await _directCameraClient.put(
        '/api/v1/cameras/$deviceId/settings',
        data: {
          'auto_face_detection': enabled,
        },
      );
    } on DioException catch (e) {
      throw _handleDioError(e);
    } catch (e) {
      print('Warning: Failed to update camera auto face detection setting: $e');
    }
  }

  /// Stop recording for a camera
  Future<RecordingResult> stopRecording(String deviceId) async {
    try {
      // Use Gateway for recording operations (has CORS support for browser requests)
      final response = await _cameraApiClient.post(
        '/api/v1/streaming/$deviceId/record/stop',
      );
      
      // Transform response to match old RecordingResult format
      return RecordingResult.fromJson({
        'session_id': response.data['recording_id'] ?? response.data['session_uuid'],
        'device_id': deviceId,
        'status': 'stopped',
        'message': response.data['message'] ?? 'Recording stopped successfully',
      });
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// Get recording status for a camera
  Future<RecordingStatus> getRecordingStatus(String deviceId) async {
    try {
      // Use Gateway for recording operations (has CORS support for browser requests)
      final response = await _cameraApiClient.get(
        '/api/v1/streaming/$deviceId/record/status',
      );
      
      final data = response.data as Map<String, dynamic>;
      
      // Transform to match RecordingStatus format
      return RecordingStatus.fromJson({
        'is_recording': data['is_recording'] ?? false,
        'session_id': data['recording_id'],
        'device_id': deviceId,
        'started_at': data['started_at'],
        'duration_seconds': data['duration_seconds'] ?? 0,
        'file_size_bytes': data['file_size_bytes'] ?? 0,
      });
    } on DioException catch (e) {
      // Return not recording status on error
      return RecordingStatus.fromJson({
        'is_recording': false,
        'session_id': null,
        'device_id': deviceId,
        'started_at': null,
        'duration_seconds': 0,
        'file_size_bytes': 0,
      });
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

/// Recording result model for start/stop operations
class RecordingResult {
  final String status;
  final String message;
  final String deviceId;
  final String? recordingId;
  final DateTime? startedAt;
  final DateTime? stoppedAt;
  final int? durationSeconds;
  final String? filePath;
  final int? fileSizeBytes;
  final String? collectionId;

  RecordingResult({
    required this.status,
    required this.message,
    required this.deviceId,
    this.recordingId,
    this.startedAt,
    this.stoppedAt,
    this.durationSeconds,
    this.filePath,
    this.fileSizeBytes,
    this.collectionId,
  });

  factory RecordingResult.fromJson(Map<String, dynamic> json) {
    return RecordingResult(
      status: json['status'] ?? '',
      message: json['message'] ?? '',
      deviceId: json['device_id'] ?? '',
      recordingId: json['recording_id'],
      startedAt: json['started_at'] != null 
          ? DateTime.parse(json['started_at']) 
          : null,
      stoppedAt: json['stopped_at'] != null 
          ? DateTime.parse(json['stopped_at']) 
          : null,
      durationSeconds: json['duration_seconds'],
      filePath: json['file_path'],
      fileSizeBytes: json['file_size_bytes'],
      collectionId: json['collection_id'],
    );
  }

  bool get isSuccess => status == 'success';
}

/// Recording status model for status queries
class RecordingStatus {
  final String deviceId;
  final bool isRecording;
  final String? recordingId;
  final DateTime? startedAt;
  final int durationSeconds;
  final int fileSizeBytes;

  RecordingStatus({
    required this.deviceId,
    required this.isRecording,
    this.recordingId,
    this.startedAt,
    this.durationSeconds = 0,
    this.fileSizeBytes = 0,
  });

  factory RecordingStatus.fromJson(Map<String, dynamic> json) {
    return RecordingStatus(
      deviceId: json['device_id'] ?? '',
      isRecording: json['is_recording'] ?? false,
      recordingId: json['recording_id'],
      startedAt: json['started_at'] != null 
          ? DateTime.parse(json['started_at']) 
          : null,
      durationSeconds: json['duration_seconds'] ?? 0,
      fileSizeBytes: json['file_size_bytes'] ?? 0,
    );
  }
}
