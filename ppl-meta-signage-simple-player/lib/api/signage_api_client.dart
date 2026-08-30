import 'package:dio/dio.dart';
import 'package:logger/logger.dart';
import '../config/app_config.dart';
import '../models/video_list.dart';
import '../models/playback_models.dart';
import '../models/playback_history.dart';

/// API client for communicating with PPL Meta backend services
class SignageApiClient {
  final Dio _dio;
  final Logger _logger;
  final String baseUrl;
  final String deviceId;

  SignageApiClient({
    required this.baseUrl,
    required this.deviceId,
    Logger? logger,
    Dio? dio,
  })  : _logger = logger ?? Logger(),
        _dio = dio ??
            Dio(BaseOptions(
              baseUrl: baseUrl,
              connectTimeout: const Duration(seconds: 4),
              receiveTimeout: const Duration(seconds: 8),
              sendTimeout: const Duration(seconds: 8),
              headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
              },
            )) {
    _setupInterceptors();
  }

  /// Setup Dio interceptors for logging and error handling
  void _setupInterceptors() {
    _dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) {
        _logger.d('${options.method} ${options.uri}');
        if (options.data != null) {
          _logger.d('Request data: ${options.data}');
        }
        return handler.next(options);
      },
      onResponse: (response, handler) {
        _logger.d('Response [${response.statusCode}]: ${response.data}');
        return handler.next(response);
      },
      onError: (error, handler) {
        _logger.e(
          'API Error: ${error.message}',
          error: error,
          stackTrace: error.stackTrace,
        );
        return handler.next(error);
      },
    ));

    // Retry interceptor for transient failures
    _dio.interceptors.add(
      QueuedInterceptorsWrapper(
        onError: (error, handler) async {
          if (_shouldRetry(error)) {
            try {
              _logger.w('Retrying request after error: ${error.message}');
              final response = await _dio.fetch(error.requestOptions);
              return handler.resolve(response);
            } catch (e) {
              return handler.next(error);
            }
          }
          return handler.next(error);
        },
      ),
    );
  }

  /// Determine if a request should be retried
  bool _shouldRetry(DioException error) {
    // Retry on network errors or 5xx server errors
    if (error.type == DioExceptionType.connectionTimeout ||
        error.type == DioExceptionType.sendTimeout ||
        error.type == DioExceptionType.receiveTimeout ||
        error.type == DioExceptionType.connectionError) {
      return true;
    }

    if (error.response?.statusCode != null) {
      final statusCode = error.response!.statusCode!;
      // Retry on 500, 502, 503, 504
      return statusCode >= 500 && statusCode < 600;
    }

    return false;
  }

  /// Sync playlist data from backend ETL endpoint
  /// 
  /// Retrieves the latest playlist configuration for this device.
  /// Returns the synced VideoList or null if no playlist is assigned.
  Future<VideoList?> syncPlaylist({
    int? lastSyncVersion,
  }) async {
    try {
      _logger.i('Syncing playlist for device: $deviceId');

      final response = await _dio.post(
        '/api/v1/signage/devices/pull',
        data: {
          'device_id': deviceId,
          'last_sync_version': lastSyncVersion,
          'capabilities': AppConfig.capabilities,
        },
      );

      if (response.statusCode == 200) {
        final data = response.data;
        
        // Check if playlist data is present
        if (data['playlist'] != null) {
          final videoList = VideoList.fromJson(data['playlist']);
          _logger.i('Synced playlist: ${videoList.name} (${videoList.videos.length} videos)');
          return videoList;
        } else {
          _logger.i('No playlist assigned to this device');
          return null;
        }
      } else if (response.statusCode == 304) {
        // Not modified - playlist unchanged
        _logger.i('Playlist unchanged (304 Not Modified)');
        return null;
      } else {
        _logger.w('Unexpected status code: ${response.statusCode}');
        return null;
      }
    } on DioException catch (e) {
      _logger.e('Sync playlist failed', error: e);
      rethrow;
    }
  }

  /// Send playback control command
  /// 
  /// Controls playback on the signage device remotely.
  Future<PlaybackStatus> sendControlCommand({
    required String command,
    Map<String, dynamic>? parameters,
  }) async {
    try {
      _logger.i('Sending control command: $command');

      final response = await _dio.post(
        '/api/v1/signage/playback/control',
        data: {
          'device_id': deviceId,
          'command': command,
          'parameters': parameters ?? {},
          'timestamp': DateTime.now().toIso8601String(),
        },
      );

      if (response.statusCode == 200) {
        final state = PlaybackStatus.fromJson(response.data);
        _logger.i('Command executed, new state: ${state.playbackState}');
        return state;
      } else {
        throw DioException(
          requestOptions: response.requestOptions,
          response: response,
          message: 'Control command failed with status ${response.statusCode}',
        );
      }
    } on DioException catch (e) {
      _logger.e('Control command failed', error: e);
      rethrow;
    }
  }

  /// Report current playback status to backend
  /// 
  /// Sends periodic status updates to the backend for monitoring.
  Future<void> reportStatus({
    required PlaybackStatus currentState,
  }) async {
    try {
      _logger.d('Reporting status: ${currentState.playbackState}');

      final response = await _dio.post(
        '/api/v1/signage/status/report',
        data: {
          'device_id': deviceId,
          'state': currentState.toJson(),
          'timestamp': DateTime.now().toIso8601String(),
        },
      );

      if (response.statusCode == 200) {
        _logger.d('Status reported successfully');
      } else {
        _logger.w('Status report returned ${response.statusCode}');
      }
    } on DioException catch (e) {
      // Don't throw on status report failures - these are non-critical
      _logger.w('Status report failed: ${e.message}');
    }
  }

  /// Upload playback history to backend
  /// 
  /// Sends accumulated playback history for analytics and monitoring.
  Future<void> uploadHistory({
    required List<PlaybackHistoryEntry> entries,
  }) async {
    try {
      _logger.i('Uploading ${entries.length} history entries');

      final response = await _dio.post(
        '/api/v1/signage/history/upload',
        data: {
          'device_id': deviceId,
          'entries': entries.map((e) => e.toJson()).toList(),
          'timestamp': DateTime.now().toIso8601String(),
        },
      );

      if (response.statusCode == 200) {
        _logger.i('History uploaded successfully');
      } else {
        _logger.w('History upload returned ${response.statusCode}');
      }
    } on DioException catch (e) {
      _logger.e('History upload failed', error: e);
      rethrow;
    }
  }

  /// Check backend connectivity
  /// 
  /// Performs a health check on the backend API.
  Future<bool> checkConnectivity() async {
    try {
      final response = await _dio.get(
        '/health',
        options: Options(
          sendTimeout: const Duration(seconds: 5),
          receiveTimeout: const Duration(seconds: 5),
        ),
      );

      return response.statusCode == 200;
    } catch (e) {
      _logger.w('Connectivity check failed: $e');
      return false;
    }
  }

  /// Get backend server info
  /// 
  /// Retrieves server version and capabilities.
  Future<Map<String, dynamic>> getServerInfo() async {
    try {
      final response = await _dio.get('/api/v1/info');

      if (response.statusCode == 200) {
        return response.data as Map<String, dynamic>;
      } else {
        throw DioException(
          requestOptions: response.requestOptions,
          response: response,
          message: 'Failed to get server info',
        );
      }
    } on DioException catch (e) {
      _logger.e('Get server info failed', error: e);
      rethrow;
    }
  }

  /// Download video file metadata
  /// 
  /// Gets information about a video file (URL, size, checksum, etc.)
  Future<Map<String, dynamic>> getVideoMetadata({
    required String videoId,
  }) async {
    try {
      final response = await _dio.get(
        '/api/v1/signage/video/$videoId/metadata',
        queryParameters: {'device_id': deviceId},
      );

      if (response.statusCode == 200) {
        return response.data as Map<String, dynamic>;
      } else {
        throw DioException(
          requestOptions: response.requestOptions,
          response: response,
          message: 'Failed to get video metadata',
        );
      }
    } on DioException catch (e) {
      _logger.e('Get video metadata failed', error: e);
      rethrow;
    }
  }

  /// Report an error to the backend
  /// 
  /// Sends error information for monitoring and diagnostics.
  Future<void> reportError({
    required String errorType,
    required String errorMessage,
    String? videoId,
    String? playlistId,
    Map<String, dynamic>? context,
  }) async {
    try {
      _logger.w('Reporting error: $errorType - $errorMessage');

      final response = await _dio.post(
        '/api/v1/signage/error/report',
        data: {
          'device_id': deviceId,
          'error_type': errorType,
          'error_message': errorMessage,
          'video_id': videoId,
          'playlist_id': playlistId,
          'context': context,
          'timestamp': DateTime.now().toIso8601String(),
        },
      );

      if (response.statusCode == 200) {
        _logger.d('Error reported successfully');
      }
    } on DioException catch (e) {
      // Don't throw on error reporting failures
      _logger.e('Error reporting failed: ${e.message}');
    }
  }

  /// Close the client and release resources
  void dispose() {
    _dio.close();
    _logger.d('SignageApiClient disposed');
  }
}
