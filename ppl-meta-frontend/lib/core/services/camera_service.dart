import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../api/api_client.dart';
import '../config/app_config.dart';
import '../models/camera.dart';
import '../models/snapshot_settings.dart';
import '../models/snapshot_result.dart';

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
  late final Dio _cameraApiClient;

  CameraService(this._apiClient) {
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

/// Provider for camera service
final cameraServiceProvider = Provider<CameraService>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return CameraService(apiClient);
});

/// Camera stream state model
class CameraStreamState {
  final bool isStreaming;
  final String? streamUrl;
  final String? error;
  final bool isLoading;

  const CameraStreamState({
    this.isStreaming = false,
    this.streamUrl,
    this.error,
    this.isLoading = false,
  });

  CameraStreamState copyWith({
    bool? isStreaming,
    String? streamUrl,
    String? error,
    bool? isLoading,
  }) {
    return CameraStreamState(
      isStreaming: isStreaming ?? this.isStreaming,
      streamUrl: streamUrl ?? this.streamUrl,
      error: error ?? this.error,
      isLoading: isLoading ?? this.isLoading,
    );
  }
}

/// Camera snapshot state model
class CameraSnapshotState {
  final bool isCapturing;
  final String? snapshotUrl;
  final String? error;

  const CameraSnapshotState({
    this.isCapturing = false,
    this.snapshotUrl,
    this.error,
  });

  CameraSnapshotState copyWith({
    bool? isCapturing,
    String? snapshotUrl,
    String? error,
  }) {
    return CameraSnapshotState(
      isCapturing: isCapturing ?? this.isCapturing,
      snapshotUrl: snapshotUrl ?? this.snapshotUrl,
      error: error ?? this.error,
    );
  }
}

/// Camera stream provider
final cameraStreamProvider = StateNotifierProvider<CameraStreamNotifier, CameraStreamState>((ref) {
  final cameraService = ref.watch(cameraServiceProvider);
  return CameraStreamNotifier(cameraService);
});

/// Camera snapshot provider
final cameraSnapshotProvider = StateNotifierProvider<CameraSnapshotNotifier, CameraSnapshotState>((ref) {
  final cameraService = ref.watch(cameraServiceProvider);
  return CameraSnapshotNotifier(cameraService);
});

/// Camera by ID provider
final cameraByIdProvider = FutureProvider.family<Camera?, String>((ref, cameraId) async {
  final cameraService = ref.watch(cameraServiceProvider);
  try {
    final cameras = await cameraService.getCameras();
    return cameras.firstWhere(
      (camera) => camera.deviceId == cameraId,
      orElse: () => throw Exception('Camera not found'),
    );
  } catch (e) {
    return null;
  }
});

/// Camera stream state notifier
class CameraStreamNotifier extends StateNotifier<CameraStreamState> {
  final CameraService _cameraService;

  CameraStreamNotifier(this._cameraService) : super(const CameraStreamState());

  Future<void> startStreaming(String cameraId, {String format = 'mjpeg', String quality = 'high'}) async {
    state = state.copyWith(isLoading: true, error: null);
    
    try {
      final result = await _cameraService.startStreaming(cameraId, format: format, quality: quality);
      final streamUrl = _cameraService.getVideoStreamUrl(cameraId);
      state = state.copyWith(
        isStreaming: true,
        streamUrl: streamUrl,
        isLoading: false,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  Future<void> stopStreaming(String cameraId) async {
    try {
      await _cameraService.stopStreaming(cameraId);
      state = const CameraStreamState();
    } catch (e) {
      state = state.copyWith(error: e.toString());
    }
  }

  Future<void> getStreamingStatus(String cameraId) async {
    try {
      final status = await _cameraService.getStreamingStatus(cameraId);
      state = state.copyWith(isStreaming: status.isActive);
    } catch (e) {
      state = state.copyWith(error: e.toString());
    }
  }

  void clearError() {
    state = state.copyWith(error: null);
  }
}

/// Camera snapshot state notifier
class CameraSnapshotNotifier extends StateNotifier<CameraSnapshotState> {
  final CameraService _cameraService;

  CameraSnapshotNotifier(this._cameraService) : super(const CameraSnapshotState());

  Future<void> captureSnapshot(String cameraId) async {
    state = state.copyWith(isCapturing: true, error: null);
    
    try {
      final snapshotResult = await _cameraService.captureSnapshot(cameraId);
      state = state.copyWith(
        isCapturing: false,
        snapshotUrl: snapshotResult.dataUrl, // Use the data URL from the result
      );
    } catch (e) {
      state = state.copyWith(
        isCapturing: false,
        error: e.toString(),
      );
    }
  }

  void clearError() {
    state = state.copyWith(error: null);
  }
}
