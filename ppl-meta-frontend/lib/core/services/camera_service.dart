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
      connectTimeout: const Duration(seconds: 60),  // Increased for stop recording which processes video
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
  Future<List<Camera>> getCameras({bool includeArchived = false}) async {
    try {
      final response = await _cameraApiClient.get(
        '/api/v1/cameras/',
        queryParameters: {'include_archived': includeArchived},
      );

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
    print('📺📺📺 [START_STREAMING_V4] startStreaming called for camera: $cameraId 📺📺📺');
    print('📺 [VERIFY] This is camera_service.dart startStreaming() method V4!');
    print('📺 [START_STREAMING_V4] Will call POST /api/v1/streaming/$cameraId/start');
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
        print('📺❌ [START_STREAMING_V4] Invalid response from streaming service');
        throw const CameraException('Invalid response from streaming service');
      }

      print('📺✅ [START_STREAMING_V4] Successfully started streaming for camera $cameraId');
      return StreamingInfo.fromJson(response.data!);
    } on DioException catch (e) {
      print('📺❌ [START_STREAMING_V4] DioException: $e');
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
  /// 1. Connect to the specific camera
  /// 2. Auto-start streaming (USB/RTSP only, not mobile/edge)
  /// 3. Auto-create collection (USB/RTSP only, not mobile/edge)
  Future<bool> connectCamera(String deviceId) async {
    try {
      print('🔌🔌🔌 [CONNECT_CAMERA] START - Connecting to camera $deviceId...');
      
      // Step 1: Connect to the specific camera
      final response = await _cameraApiClient.post<Map<String, dynamic>>(
        '/api/v1/cameras/$deviceId/connect',
      );
      
      print('🔌🔌🔌 [CONNECT_CAMERA] Response received: ${response.statusCode}');
      
      if (response.statusCode == 200) {
        print('✅ Successfully connected to camera $deviceId');
        
        // Check camera type from response
        final cameraType = response.data?['camera_type']?.toString().toLowerCase();
        final isMobileCamera = cameraType == 'mobile';
        final isEdgeCamera = cameraType == 'edge';
        
        if (isMobileCamera) {
          // Mobile cameras don't use backend streaming - they stream directly from mobile app
          print('📱 [CONNECT_CAMERA] Mobile camera connected - skipping backend streaming setup');
          print('📱 [CONNECT_CAMERA] Mobile camera uses direct streaming from device');
          return true;
        }
        
        if (isEdgeCamera) {
          // Edge cameras use WebSocket command protocol - no auto-streaming
          print('🔷 [CONNECT_CAMERA] Edge camera connected - streaming controlled via WebSocket commands');
          print('🔷 [CONNECT_CAMERA] Edge camera waits for explicit start-stream command from UI');
          return true;
        }
        
        // Step 2: Auto-start streaming (USB/RTSP cameras only)
        try {
          print('🚀 [CONNECT_CAMERA] Auto-starting stream for $cameraType camera $deviceId...');
          final streamResponse = await _cameraApiClient.post<Map<String, dynamic>>(
            '/api/v1/streaming/$deviceId/start',
          );
          if (streamResponse.statusCode == 200) {
            print('🚀✅ [CONNECT_CAMERA] Auto-started streaming for camera $deviceId');
          } else {
            print('🚀⚠️ [CONNECT_CAMERA] Failed to auto-start streaming: ${streamResponse.statusCode}');
          }
        } catch (e) {
          print('🚀❌ [CONNECT_CAMERA] Failed to auto-start streaming for $deviceId: $e');
          // Don't fail connection if streaming start fails
        }
        
        // Step 3: Auto-create collection for USB/RTSP cameras
        try {
          // Get camera details to get the name
          final cameras = await getCameras();
          final camera = cameras.firstWhere(
            (cam) => cam.deviceId == deviceId,
            orElse: () => Camera(
              id: deviceId,
              deviceId: deviceId,
              name: 'Camera $deviceId',
              status: 'connected',
              type: CameraType.usb,
              isActive: true,
            ),
          );
          
          await _collectionService.setupCameraWithCollection(camera);
          print('✅ Auto-created collection for camera: ${camera.name}');
        } catch (e) {
          print('⚠️ Failed to auto-create collection for camera $deviceId: $e');
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

  /// Start streaming for an edge camera (via WebSocket command)
  Future<bool> startEdgeCameraStream(String deviceId) async {
    try {
      print('🚀 [START_EDGE_STREAM] Starting stream for edge camera $deviceId...');
      
      final response = await _cameraApiClient.post<Map<String, dynamic>>(
        '/api/v1/cameras/edge/$deviceId/start-stream',
      );
      
      if (response.statusCode == 200) {
        print('✅ Started streaming for edge camera $deviceId');
        return true;
      } else {
        print('❌ Failed to start edge camera stream: ${response.statusCode}');
        return false;
      }
    } catch (e) {
      print('❌ Error starting edge camera stream: $e');
      if (e is DioException) {
        throw _handleDioError(e);
      }
      throw CameraException('Failed to start edge camera stream: ${e.toString()}');
    }
  }

  /// Stop streaming for an edge camera (via WebSocket command)
  Future<bool> stopEdgeCameraStream(String deviceId) async {
    try {
      print('🛑 [STOP_EDGE_STREAM] Stopping stream for edge camera $deviceId...');
      
      final response = await _cameraApiClient.post<Map<String, dynamic>>(
        '/api/v1/cameras/edge/$deviceId/stop-stream',
      );
      
      if (response.statusCode == 200) {
        print('✅ Stopped streaming for edge camera $deviceId');
        return true;
      } else {
        print('❌ Failed to stop edge camera stream: ${response.statusCode}');
        return false;
      }
    } catch (e) {
      print('❌ Error stopping edge camera stream: $e');
      if (e is DioException) {
        throw _handleDioError(e);
      }
      throw CameraException('Failed to stop edge camera stream: ${e.toString()}');
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

  /// Archive a camera (hide from default camera list)
  Future<void> archiveCamera(String deviceId) async {
    print('🗃️ [CameraService] Archiving camera: $deviceId');
    try {
      final response = await _cameraApiClient.post('/api/v1/cameras/$deviceId/archive');
      print('✅ [CameraService] Archive successful: ${response.statusCode}');
    } on DioException catch (e) {
      print('❌ [CameraService] Archive failed (DioException): ${e.message}');
      print('❌ [CameraService] Response: ${e.response?.data}');
      throw _handleDioError(e);
    } catch (e) {
      print('❌ [CameraService] Archive failed: $e');
      throw CameraException('Failed to archive camera: $e');
    }
  }

  /// Unarchive a camera (restore to default camera list)
  Future<void> unarchiveCamera(String deviceId) async {
    print('🗃️ [CameraService] Unarchiving camera: $deviceId');
    try {
      final response = await _cameraApiClient.post('/api/v1/cameras/$deviceId/unarchive');
      print('✅ [CameraService] Unarchive successful: ${response.statusCode}');
    } on DioException catch (e) {
      print('❌ [CameraService] Unarchive failed (DioException): ${e.message}');
      print('❌ [CameraService] Response: ${e.response?.data}');
      throw _handleDioError(e);
    } catch (e) {
      print('❌ [CameraService] Unarchive failed: $e');
      throw CameraException('Failed to unarchive camera: $e');
    }
  }

  /// Start recording for a camera
  Future<RecordingResult> startRecording(String deviceId, {bool enableInstantDetection = true}) async {
    print('🔥 DEBUG CORE: startRecording called for deviceId: $deviceId');
    print('🔥 DEBUG CORE: Using Gateway client for recording operations');
    print('🔥 DEBUG CORE: enableInstantDetection: $enableInstantDetection');
    
    try {
      // ✅ USE APPROPRIATE TIMEOUTS
      // Backend needs:
      // - 2-5s: Create session, start recording loop
      // - 5-10s: Initialize instant detection (if enabled)
      // - 2-5s: Network latency, processing overhead
      // Total: 15-20s safe margin, using 30s for reliability
      final response = await _cameraApiClient.post(
        '/api/v1/streaming/$deviceId/record/start',
        queryParameters: {
          'enable_instant_detection': enableInstantDetection,
        },
        options: Options(
          receiveTimeout: const Duration(seconds: 30), // ✅ Adequate for backend
          sendTimeout: const Duration(seconds: 10),    // ✅ Adequate for request
        ),
      );

      print('🔥 DEBUG CORE: Got response from record/start: ${response.statusCode}');
      
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
      print('🔥 DEBUG CORE: DioException type: ${e.type}, statusCode: ${e.response?.statusCode}');
      
      // ✅ CRITICAL FIX: REMOVED TIMEOUT FALLBACK
      // The old code created fake session IDs on timeout, which corrupted UI state
      // and made the camera screen inaccessible. If timeout occurs, let the error
      // propagate so the user sees a proper error message and can retry.
      // Backend now returns immediately (< 5s) so 30s timeout should never trigger.
      
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
          options: Options(
            receiveTimeout: const Duration(seconds: 30),
            sendTimeout: const Duration(seconds: 10),
          ),
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

  /// Get pipeline settings for a camera
  Future<Map<String, dynamic>> getPipelineSettings(String deviceId) async {
    try {
      final response = await _cameraApiClient.get(
        '/api/v1/cameras/$deviceId/pipeline-settings',
      );

      if (response.data == null) {
        throw const CameraException('Invalid response from camera service');
      }

      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// Update pipeline settings for a camera
  Future<Map<String, dynamic>> updatePipelineSettings(
    String deviceId, {
    required bool instantDetectionEnabled,
    required bool recordingPipelineEnabled,
    required int instantDetectionIntervalSeconds,
    required int segmentDurationSeconds,
    required int storageMultiple,
    required int trackingSessionDurationMinutes,
  }) async {
    try {
      final response = await _cameraApiClient.patch(
        '/api/v1/cameras/$deviceId/pipeline-settings',
        queryParameters: {
          'instant_detection_enabled': instantDetectionEnabled,
          'recording_pipeline_enabled': recordingPipelineEnabled,
          'instant_detection_interval_seconds': instantDetectionIntervalSeconds,
          'segment_duration_seconds': segmentDurationSeconds,
          'storage_multiple': storageMultiple,
          'tracking_session_duration_minutes': trackingSessionDurationMinutes,
        },
      );

      if (response.data == null) {
        throw const CameraException('Invalid response from camera service');
      }

      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// Get workflow settings for a camera
  Future<Map<String, dynamic>> getWorkflowSettings(String deviceId) async {
    try {
      final response = await _cameraApiClient.get(
        '/api/v1/cameras/$deviceId/workflow-settings',
      );

      if (response.data == null) {
        throw const CameraException('Invalid response from camera service');
      }

      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// Update workflow settings for a camera
  Future<Map<String, dynamic>> updateWorkflowSettings(
    String deviceId, {
    bool? autoFaceDetection,
    List<String>? detectionMethods,
    Map<String, dynamic>? processingOptions,
    double? confidenceThreshold,
    int? tolerancePercent,
    bool? enablePerformanceOptimization,
    bool? showPerformanceIndicators,
    String? defaultPlaybackMode,
    double? mvrQualityThreshold,
    bool? mvrPeriodicSchedulerEnabled,
    double? mvrPeriodicSchedulerThreshold,
    int? mvrPeriodicSchedulerFrequencySeconds,
  }) async {
    try {
      final body = <String, dynamic>{};
      
      if (autoFaceDetection != null) {
        body['auto_face_detection'] = autoFaceDetection;
      }
      if (detectionMethods != null) {
        body['detection_methods'] = detectionMethods;
      }
      if (processingOptions != null) {
        body['processing_options'] = processingOptions;
      }
      if (confidenceThreshold != null) {
        body['confidence_threshold'] = confidenceThreshold;
      }
      if (tolerancePercent != null) {
        body['tolerance_percent'] = tolerancePercent;
      }
      if (enablePerformanceOptimization != null) {
        body['enable_performance_optimization'] = enablePerformanceOptimization;
      }
      if (showPerformanceIndicators != null) {
        body['show_performance_indicators'] = showPerformanceIndicators;
      }
      if (defaultPlaybackMode != null) {
        body['default_playback_mode'] = defaultPlaybackMode;
      }
      if (mvrQualityThreshold != null) {
        body['mvr_quality_threshold'] = mvrQualityThreshold;
      }
      if (mvrPeriodicSchedulerEnabled != null) {
        body['mvr_periodic_scheduler_enabled'] = mvrPeriodicSchedulerEnabled;
      }
      if (mvrPeriodicSchedulerThreshold != null) {
        body['mvr_periodic_scheduler_threshold'] = mvrPeriodicSchedulerThreshold;
      }
      if (mvrPeriodicSchedulerFrequencySeconds != null) {
        body['mvr_periodic_scheduler_frequency_seconds'] =
            mvrPeriodicSchedulerFrequencySeconds;
      }

      final response = await _cameraApiClient.patch(
        '/api/v1/cameras/$deviceId/workflow-settings',
        data: body,
      );

      if (response.data == null) {
        throw const CameraException('Invalid response from camera service');
      }

      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }


  /// Stop recording for a camera
  /// 
  /// [autoStopInstantDetection] - If false, keeps camera connected and instant detection running.
  /// Default is false to maintain streaming and instant detection after recording stops.
  Future<RecordingResult> stopRecording(String deviceId, {bool autoStopInstantDetection = false}) async {
    try {
      print('🛑 DEBUG CORE: stopRecording called for deviceId: $deviceId');
      print('🛑 DEBUG CORE: autoStopInstantDetection: $autoStopInstantDetection');
      
      // Use Gateway for recording operations (has CORS support for browser requests)
      final response = await _cameraApiClient.post(
        '/api/v1/streaming/$deviceId/record/stop',
        queryParameters: {
          'auto_stop_instant_detection': autoStopInstantDetection,
        },
      );
      
      print('✅ DEBUG CORE: stopRecording response: ${response.statusCode}');
      
      // Transform response to match old RecordingResult format
      return RecordingResult.fromJson({
        'session_id': response.data['recording_id'] ?? response.data['session_uuid'],
        'device_id': deviceId,
        'status': 'success',  // Changed from 'stopped' to 'success' so isSuccess returns true
        'message': response.data['message'] ?? 'Recording stopped successfully',
      });
    } on DioException catch (e) {
      print('❌ DEBUG CORE: stopRecording error: ${e.message}');
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

  /// Get instant detection results from camera's memory cache
  Future<Map<String, dynamic>?> getInstantDetectionResults(String deviceId) async {
    try {
      final response = await _cameraApiClient.get(
        '/api/v1/instant-detection/results/$deviceId',
      );

      if (response.statusCode == 200 && response.data != null) {
        return response.data as Map<String, dynamic>;
      } else if (response.statusCode == 404) {
        // No results cached yet - instant detection not started, this is normal
        return {'success': false, 'person_objects': []};
      }
      return null;
    } on DioException catch (e) {
      // Silently handle 404 - instant detection may not be running
      if (e.response?.statusCode == 404) {
        return {'success': false, 'person_objects': []};
      }
      // Only log non-404 errors and not timeouts (called every 10 seconds)
      if (e.type != DioExceptionType.connectionTimeout &&
          e.type != DioExceptionType.receiveTimeout &&
          e.response?.statusCode != 404) {
        print('Instant detection fetch: ${e.message}');
      }
      return null;
    } catch (e) {
      // Silent fail for other errors
      return null;
    }
  }

  /// Start instant detection for a camera (decoupled from recording)
  Future<Map<String, dynamic>?> startInstantDetection(String deviceId) async {
    try {
      final response = await _cameraApiClient.post(
        '/api/v1/instant-detection/start/$deviceId',
      );
      if (response.statusCode == 200 && response.data != null) {
        return response.data as Map<String, dynamic>;
      }
      return null;
    } catch (e) {
      print('Failed to start instant detection: $e');
      return null;
    }
  }

  /// Stop instant detection for a specific camera
  Future<Map<String, dynamic>?> stopInstantDetection(String deviceId) async {
    try {
      final response = await _cameraApiClient.post(
        '/api/v1/instant-detection/stop/$deviceId',
      );
      if (response.statusCode == 200 && response.data != null) {
        return response.data as Map<String, dynamic>;
      }
      return null;
    } catch (e) {
      print('Failed to stop instant detection: $e');
      return null;
    }
  }

  /// Get instant detection system status (used for state sync on app restart)
  Future<Map<String, dynamic>?> getInstantDetectionStatus() async {
    try {
      final response = await _cameraApiClient.get(
        '/api/v1/instant-detection/status',
      );
      if (response.statusCode == 200 && response.data != null) {
        return response.data as Map<String, dynamic>;
      }
      return null;
    } catch (e) {
      return null;
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
