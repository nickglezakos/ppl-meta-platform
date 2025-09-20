import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import '../models/face_detection_models.dart';
import '../models/api_response.dart';
import '../core/api/api_client.dart';
import '../core/config/app_config.dart';
import 'media_api_client.dart'; // For FaceDetection model

/// Workflow API client for face detection workflows (4 & 5)
/// Handles session management, processing status, and performance metrics
class WorkflowApiClient {
  late final ApiClient _apiClient;
  final String baseUrl;

  WorkflowApiClient({
    String? baseUrl,
    ApiClient? apiClient,
  }) : baseUrl = baseUrl ?? 'http://localhost:8080' {
    // Use provided ApiClient or create new one
    _apiClient = apiClient ?? ApiClient(AppConfig.instance);
    
    // Configure additional settings for workflow APIs
    _apiClient.dio.options.connectTimeout = const Duration(seconds: 30);
    _apiClient.dio.options.receiveTimeout = const Duration(seconds: 60);
    
    // Add workflow-specific request interceptor
    if (kDebugMode) {
      _apiClient.dio.interceptors.add(LogInterceptor(
        requestBody: true,
        responseBody: true,
        logPrint: (object) => debugPrint('WorkflowAPI: $object'),
      ));
    }
  }

  /// Get the base URL for workflow endpoints
  String get _workflowBaseUrl => baseUrl;

  // =====================================================
  // WORKFLOW 4 - SESSION MANAGEMENT ENDPOINTS
  // =====================================================

  /// Create a new face detection session for a media item
  Future<ApiResponse<FaceDetectionSession>> createFaceDetectionSession({
    required String mediaUuid,
    double? confidenceThreshold,
    List<String>? detectionMethods,
    String? priority,
    bool? enableProgressUpdates,
  }) async {
    try {
      final requestData = {
        'media_uuid': mediaUuid,
        'confidence_threshold': confidenceThreshold ?? 0.7,
        'detection_methods': detectionMethods ?? ['two_stage'],
        'priority': priority ?? 'normal',
        'enable_progress_updates': enableProgressUpdates ?? true,
      };

      final response = await _apiClient.dio.post(
        '$_workflowBaseUrl/sessions/',
        data: requestData,
      );

      final session = FaceDetectionSession.fromJson(response.data);
      return ApiResponse.success(session);
    } on DioException catch (e) {
      return _handleApiError<FaceDetectionSession>(e);
    } catch (e) {
      return ApiResponse.error('Failed to create session: $e');
    }
  }

  /// Get the status of a specific face detection session
  Future<ApiResponse<FaceDetectionSession>> getSessionStatus(String sessionUuid) async {
    try {
      final response = await _apiClient.dio.get(
        '$_workflowBaseUrl/sessions/$sessionUuid',
      );

      final session = FaceDetectionSession.fromJson(response.data);
      return ApiResponse.success(session);
    } on DioException catch (e) {
      return _handleApiError<FaceDetectionSession>(e);
    } catch (e) {
      return ApiResponse.error('Failed to get session status: $e');
    }
  }

  /// Get all sessions for a specific media item
  Future<ApiResponse<List<FaceDetectionSession>>> getSessionsForMedia(String mediaUuid) async {
    try {
      final response = await _apiClient.dio.get(
        '$_workflowBaseUrl/sessions/',
        queryParameters: {'media_uuid': mediaUuid},
      );

      final sessions = (response.data as List)
          .map((json) => FaceDetectionSession.fromJson(json))
          .toList();
      
      return ApiResponse.success(sessions);
    } on DioException catch (e) {
      return _handleApiError<List<FaceDetectionSession>>(e);
    } catch (e) {
      return ApiResponse.error('Failed to get media sessions: $e');
    }
  }

  /// Get all active sessions across the system
  Future<ApiResponse<List<FaceDetectionSession>>> getAllActiveSessions() async {
    try {
      final response = await _apiClient.dio.get(
        '/api/v1/sessions/active/overview',
      );

      final sessions = (response.data as List)
          .map((json) => FaceDetectionSession.fromJson(json))
          .toList();
      
      return ApiResponse.success(sessions);
    } on DioException catch (e) {
      return _handleApiError<List<FaceDetectionSession>>(e);
    } catch (e) {
      return ApiResponse.error('Failed to get active sessions: $e');
    }
  }

  /// Delete/cancel a face detection session
  Future<ApiResponse<void>> deleteSession(String sessionUuid) async {
    try {
      await _apiClient.dio.delete(
        '$_workflowBaseUrl/sessions/$sessionUuid',
      );

      return ApiResponse.success(null);
    } on DioException catch (e) {
      return _handleApiError<void>(e);
    } catch (e) {
      return ApiResponse.error('Failed to delete session: $e');
    }
  }

  /// Get real-time statistics for an active session
  Future<ApiResponse<Map<String, dynamic>>> getSessionStatistics(String sessionUuid) async {
    try {
      final response = await _apiClient.dio.get(
        '$_workflowBaseUrl/sessions/stats',
        queryParameters: {'session_uuid': sessionUuid},
      );

      return ApiResponse.success(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      return _handleApiError<Map<String, dynamic>>(e);
    } catch (e) {
      return ApiResponse.error('Failed to get session statistics: $e');
    }
  }

  /// Start an existing face detection session
  Future<ApiResponse<void>> startSession(String sessionUuid) async {
    try {
      await _apiClient.dio.post(
        '$_workflowBaseUrl/api/v1/sessions/$sessionUuid/start',
      );

      return ApiResponse.success(null);
    } on DioException catch (e) {
      return _handleApiError<void>(e);
    } catch (e) {
      return ApiResponse.error('Failed to start session: $e');
    }
  }

  /// Stop an active face detection session
  Future<ApiResponse<void>> stopSession(String sessionUuid) async {
    try {
      await _apiClient.dio.post(
        '$_workflowBaseUrl/api/v1/sessions/$sessionUuid/stop',
      );

      return ApiResponse.success(null);
    } on DioException catch (e) {
      return _handleApiError<void>(e);
    } catch (e) {
      return ApiResponse.error('Failed to stop session: $e');
    }
  }

  // =====================================================
  // WORKFLOW 5 - PROCESSING STATUS & PLAYBACK
  // =====================================================

  /// Get processing status with widget optimization for a media file
  Future<ApiResponse<ProcessingStatus>> getProcessingStatus(String mediaUuid) async {
    try {
      final response = await _apiClient.dio.get(
        '$_workflowBaseUrl/api/v1/processing-status/$mediaUuid/widget',
      );

      final status = ProcessingStatus.fromJson(response.data);
      return ApiResponse.success(status);
    } on DioException catch (e) {
      return _handleApiError<ProcessingStatus>(e);
    } catch (e) {
      return ApiResponse.error('Failed to get processing status: $e');
    }
  }

  /// Get optimal playback mode for a media file
  Future<ApiResponse<PlaybackMode>> getPlaybackMode(String mediaUuid) async {
    try {
      final response = await _apiClient.dio.get(
        '$_workflowBaseUrl/api/v1/playback-mode/$mediaUuid',
      );

      final playbackMode = PlaybackMode.fromJson(response.data);
      return ApiResponse.success(playbackMode);
    } on DioException catch (e) {
      return _handleApiError<PlaybackMode>(e);
    } catch (e) {
      return ApiResponse.error('Failed to get playback mode: $e');
    }
  }

  // =====================================================
  // PERFORMANCE & ANALYTICS
  // =====================================================

  /// Get stored face detection data for a media file with optimizations
  Future<ApiResponse<List<FaceDetection>>> getStoredFaceData({
    required String mediaUuid,
    bool enableCaching = true,
    int? maxFaces,
  }) async {
    try {
      final queryParams = <String, dynamic>{
        'enable_caching': enableCaching,
        if (maxFaces != null) 'max_faces': maxFaces,
      };

      final response = await _apiClient.dio.get(
        '$_workflowBaseUrl/api/v1/media/$mediaUuid/faces',
        queryParameters: queryParams,
      );

      final faces = (response.data as List)
          .map((json) => FaceDetection.fromJson(json))
          .toList();
      
      return ApiResponse.success(faces);
    } on DioException catch (e) {
      return _handleApiError<List<FaceDetection>>(e);
    } catch (e) {
      return ApiResponse.error('Failed to get stored face data: $e');
    }
  }

  /// Mark a video as completely processed
  Future<ApiResponse<void>> markVideoAsProcessed({
    required String mediaUuid,
    Map<String, dynamic>? metadata,
  }) async {
    try {
      await _apiClient.dio.post(
        '$_workflowBaseUrl/api/v1/processing-status/$mediaUuid/complete',
        data: {
          'completed_at': DateTime.now().toIso8601String(),
          if (metadata != null) 'metadata': metadata,
        },
      );

      return ApiResponse.success(null);
    } on DioException catch (e) {
      return _handleApiError<void>(e);
    } catch (e) {
      return ApiResponse.error('Failed to mark video as processed: $e');
    }
  }

  /// Trigger video analysis workflow
  Future<ApiResponse<void>> triggerVideoAnalysis({
    required String mediaUuid,
    String? workflowType,
    Map<String, dynamic>? parameters,
  }) async {
    try {
      await _apiClient.dio.post(
        '$_workflowBaseUrl/api/v1/trigger-analysis',
        data: {
          'media_uuid': mediaUuid,
          'workflow_type': workflowType ?? 'face_detection',
          if (parameters != null) 'parameters': parameters,
        },
      );

      return ApiResponse.success(null);
    } on DioException catch (e) {
      return _handleApiError<void>(e);
    } catch (e) {
      return ApiResponse.error('Failed to trigger video analysis: $e');
    }
  }

  /// Process video with optimization features
  Future<ApiResponse<FaceDetectionSession>> processVideoForOptimization({
    required String mediaUuid,
    bool enableCaching = true,
    String? priority,
  }) async {
    try {
      final response = await _apiClient.dio.post(
        '$_workflowBaseUrl/api/v1/process-for-optimization',
        data: {
          'media_uuid': mediaUuid,
          'enable_caching': enableCaching,
          'priority': priority ?? 'normal',
        },
      );

      final session = FaceDetectionSession.fromJson(response.data);
      return ApiResponse.success(session);
    } on DioException catch (e) {
      return _handleApiError<FaceDetectionSession>(e);
    } catch (e) {
      return ApiResponse.error('Failed to process video for optimization: $e');
    }
  }

  /// Get all processed videos list
  Future<ApiResponse<List<ProcessingStatus>>> getAllProcessedVideos() async {
    try {
      // Mock implementation - replace with real endpoint when available
      await Future.delayed(const Duration(milliseconds: 500));
      return ApiResponse.success(<ProcessingStatus>[]);
    } on DioException catch (e) {
      return _handleApiError<List<ProcessingStatus>>(e);
    } catch (e) {
      return ApiResponse.error('Failed to get processed videos: $e');
    }
  }

  /// Get workflow performance metrics
  Future<ApiResponse<WorkflowPerformanceMetrics>> getPerformanceMetrics() async {
    try {
      final response = await _apiClient.dio.get(
        '$_workflowBaseUrl/analytics/performance',
      );

      // Parse the response data into performance metrics
      final data = response.data as Map<String, dynamic>;
      final metrics = WorkflowPerformanceMetrics(
        cpuUsageReduction: (data['cpu_usage_reduction'] ?? 0.0).toDouble(),
        memoryUsageReduction: (data['memory_usage_reduction'] ?? 0.0).toDouble(),
        activeSessionsCount: data['active_sessions_count'] ?? 0,
        processedVideosCount: data['processed_videos_count'] ?? 0,
        lastUpdated: data['last_updated'] != null 
            ? DateTime.parse(data['last_updated'])
            : DateTime.now(),
        avgProcessingTimeSeconds: data['avg_processing_time_seconds']?.toDouble(),
        totalFacesDetected: data['total_faces_detected'],
        systemCpuUsage: data['system_cpu_usage']?.toDouble(),
        systemMemoryUsage: data['system_memory_usage']?.toDouble(),
        processingThroughput: data['processing_throughput']?.toDouble(),
      );

      return ApiResponse.success(metrics);
    } on DioException catch (e) {
      return _handleApiError<WorkflowPerformanceMetrics>(e);
    } catch (e) {
      return ApiResponse.error('Failed to get performance metrics: $e');
    }
  }

  /// Get historical performance data
  Future<ApiResponse<List<WorkflowPerformanceMetrics>>> getPerformanceHistory({
    required int days,
    String? sessionType,
  }) async {
    try {
      final queryParams = <String, dynamic>{
        'days': days,
        if (sessionType != null) 'session_type': sessionType,
      };

      final response = await _apiClient.dio.get(
        '$_workflowBaseUrl/api/v1/performance-metrics/history',
        queryParameters: queryParams,
      );

      final historyList = (response.data as List)
          .map((json) => WorkflowPerformanceMetrics.fromJson(json))
          .toList();
      
      return ApiResponse.success(historyList);
    } on DioException catch (e) {
      return _handleApiError<List<WorkflowPerformanceMetrics>>(e);
    } catch (e) {
      return ApiResponse.error('Failed to get performance history: $e');
    }
  }

  // =====================================================
  // SYSTEM STATUS & ANALYTICS
  // =====================================================

  /// Get analytics summary
  Future<ApiResponse<Map<String, dynamic>>> getAnalyticsSummary({
    int days = 7,
  }) async {
    try {
      final response = await _apiClient.dio.get(
        '$_workflowBaseUrl/analytics/summary',
        queryParameters: {'days': days},
      );

      return ApiResponse.success(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      return _handleApiError<Map<String, dynamic>>(e);
    } catch (e) {
      return ApiResponse.error('Failed to get analytics summary: $e');
    }
  }

  /// Get database status
  Future<ApiResponse<Map<String, dynamic>>> getDatabaseStatus() async {
    try {
      final response = await _apiClient.dio.get(
        '$_workflowBaseUrl/database/status',
      );

      return ApiResponse.success(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      return _handleApiError<Map<String, dynamic>>(e);
    } catch (e) {
      return ApiResponse.error('Failed to get database status: $e');
    }
  }

  // =====================================================
  // SYSTEM HEALTH & MONITORING
  // =====================================================

  /// Check workflow service health
  Future<ApiResponse<Map<String, dynamic>>> checkWorkflowHealth() async {
    try {
      final response = await _apiClient.dio.get(
        '$_workflowBaseUrl/health',
      );

      return ApiResponse.success(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      return _handleApiError<Map<String, dynamic>>(e);
    } catch (e) {
      return ApiResponse.error('Failed to check workflow health: $e');
    }
  }

  /// Get workflow service capabilities
  Future<ApiResponse<Map<String, dynamic>>> getWorkflowCapabilities() async {
    try {
      final response = await _apiClient.dio.get(
        '$_workflowBaseUrl/api/v1/capabilities',
      );

      return ApiResponse.success(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      return _handleApiError<Map<String, dynamic>>(e);
    } catch (e) {
      return ApiResponse.error('Failed to get workflow capabilities: $e');
    }
  }

  // =====================================================
  // HELPER METHODS
  // =====================================================

  /// Handle Dio errors and convert them to ApiResponse errors
  ApiResponse<T> _handleApiError<T>(DioException error) {
    String message;
    
    switch (error.type) {
      case DioExceptionType.connectionTimeout:
        message = 'Connection timeout to workflow service';
        break;
      case DioExceptionType.receiveTimeout:
        message = 'Receive timeout from workflow service';
        break;
      case DioExceptionType.badResponse:
        final statusCode = error.response?.statusCode;
        final responseData = error.response?.data;
        
        if (statusCode == 404) {
          message = 'Workflow resource not found';
        } else if (statusCode == 400) {
          message = responseData?['error'] ?? 'Invalid request to workflow service';
        } else if (statusCode == 500) {
          message = 'Workflow service internal error';
        } else {
          message = 'Workflow service error: $statusCode';
        }
        break;
      case DioExceptionType.cancel:
        message = 'Request cancelled';
        break;
      case DioExceptionType.unknown:
        message = 'Network error connecting to workflow service';
        break;
      default:
        message = 'Unknown workflow service error';
    }

    return ApiResponse.error(message);
  }

  /// Get authentication token from the underlying API client
  String? get authToken => _apiClient.authToken;

  /// Check if the client is authenticated
  bool get isAuthenticated => _apiClient.authToken != null;

  /// Set authentication token
  void setAuthToken(String token) {
    _apiClient.setAuthToken(token);
  }

  /// Clear authentication token
  void clearAuth() {
    _apiClient.clearAuthToken();
  }
}