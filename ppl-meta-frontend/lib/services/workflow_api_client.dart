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
  }) : baseUrl = baseUrl ?? 'http://localhost:8003' {
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
      final request = SessionCreationRequest(
        mediaUuid: mediaUuid,
        confidenceThreshold: confidenceThreshold,
        detectionMethods: detectionMethods,
        priority: priority,
        enableProgressUpdates: enableProgressUpdates,
      );

      final response = await _apiClient.dio.post(
        '$_workflowBaseUrl/sessions',
        data: request.toJson(),
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
        '$_workflowBaseUrl/sessions/$sessionUuid/status',
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
        '$_workflowBaseUrl/media/$mediaUuid/sessions',
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
        '$_workflowBaseUrl/sessions',
        queryParameters: {'status': 'active'},
      );

      // Handle the API response structure with sessions array
      if (response.data['success'] == true && response.data['sessions'] != null) {
        final sessions = (response.data['sessions'] as List)
            .map((json) {
              // Map API field names to model field names
              final mappedJson = {
                'session_uuid': json['session_uuid'],
                'media_uuid': json['media_uuid'],
                'status': json['processing_status'] ?? json['status'] ?? 'unknown',
                'created_at': json['started_at'] ?? json['created_at'],
                'completed_at': json['ended_at'] ?? json['completed_at'],
                'total_frames_processed': json['total_frames_processed'],
                'estimated_total_frames': json['estimated_total_frames'],
                'total_faces_detected': json['total_faces_detected'] ?? 0,
                'confidence_threshold': json['confidence_threshold'],
                'detection_methods': json['detection_methods'] ?? <String>[],
                'progress': json['progress'],
              };
              return FaceDetectionSession.fromJson(mappedJson);
            })
            .toList();
        
        return ApiResponse.success(sessions);
      } else {
        return ApiResponse.error('No sessions data in response');
      }
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
  Future<ApiResponse<SessionStatistics>> getSessionStatistics(String sessionUuid) async {
    try {
      final response = await _apiClient.dio.get(
        '$_workflowBaseUrl/sessions/stats',
        queryParameters: {'session_uuid': sessionUuid},
      );

      final statistics = SessionStatistics.fromJson(response.data);
      return ApiResponse.success(statistics);
    } on DioException catch (e) {
      return _handleApiError<SessionStatistics>(e);
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
  // WORKFLOW 5 - PROCESSING STATUS & SMART PLAYBACK
  // =====================================================

  /// Get the processing status for a media item
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

  /// Get the optimal playback mode for a media item
  Future<ApiResponse<PlaybackMode>> getOptimalPlaybackMode(String mediaUuid) async {
    try {
      final response = await _apiClient.dio.get(
        '$_workflowBaseUrl/api/v1/playback-mode/$mediaUuid',
      );

      final mode = PlaybackMode.fromJson(response.data);
      return ApiResponse.success(mode);
    } on DioException catch (e) {
      return _handleApiError<PlaybackMode>(e);
    } catch (e) {
      return ApiResponse.error('Failed to get playback mode: $e');
    }
  }

  /// Get stored face data for a media item (Workflow 5 optimization)
  Future<ApiResponse<List<FaceDetection>>> getStoredFaceData({
    required String mediaUuid,
    int? startFrame,
    int? endFrame,
    double? confidenceThreshold,
  }) async {
    try {
      final queryParams = <String, dynamic>{
        if (startFrame != null) 'start_frame': startFrame,
        if (endFrame != null) 'end_frame': endFrame,
        if (confidenceThreshold != null) 'confidence_threshold': confidenceThreshold,
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

  /// Mark a video as processed for optimized playback
  Future<ApiResponse<void>> markVideoAsProcessed({
    required String mediaUuid,
    required String sessionUuid,
    double? qualityScore,
  }) async {
    try {
      await _apiClient.dio.post(
        '$_workflowBaseUrl/api/v1/processing-status/$mediaUuid/complete',
        data: {
          'session_uuid': sessionUuid,
          if (qualityScore != null) 'quality_score': qualityScore,
        },
      );

      return ApiResponse.success(null);
    } on DioException catch (e) {
      return _handleApiError<void>(e);
    } catch (e) {
      return ApiResponse.error('Failed to mark video as processed: $e');
    }
  }

  /// Trigger video analysis for Workflow 5 optimization
  Future<ApiResponse<void>> triggerVideoAnalysis({
    required String mediaUuid,
    double? confidenceThreshold,
    List<String>? detectionMethods,
    bool forceReprocess = false,
  }) async {
    try {
      await _apiClient.dio.post(
        '$_workflowBaseUrl/api/v1/trigger-analysis',
        data: {
          'media_uuid': mediaUuid,
          if (confidenceThreshold != null) 'confidence_threshold': confidenceThreshold,
          if (detectionMethods != null) 'detection_methods': detectionMethods,
          'force_reprocess': forceReprocess,
        },
      );

      return ApiResponse.success(null);
    } on DioException catch (e) {
      return _handleApiError<void>(e);
    } catch (e) {
      return ApiResponse.error('Failed to trigger video analysis: $e');
    }
  }

  /// Trigger processing for a video to enable optimized playback
  Future<ApiResponse<FaceDetectionSession>> processVideoForOptimization({
    required String mediaUuid,
    double? confidenceThreshold,
    List<String>? detectionMethods,
  }) async {
    try {
      final response = await _apiClient.dio.post(
        '$_workflowBaseUrl/api/v1/process-for-optimization',
        data: {
          'media_uuid': mediaUuid,
          if (confidenceThreshold != null) 'confidence_threshold': confidenceThreshold,
          if (detectionMethods != null) 'detection_methods': detectionMethods,
        },
      );

      final session = FaceDetectionSession.fromJson(response.data);
      return ApiResponse.success(session);
    } on DioException catch (e) {
      return _handleApiError<FaceDetectionSession>(e);
    } catch (e) {
      return ApiResponse.error('Failed to start optimization processing: $e');
    }
  }

  /// Get all processed videos across the system
  Future<ApiResponse<List<ProcessingStatus>>> getAllProcessedVideos() async {
    try {
      // TODO: Find appropriate backend endpoint for processed videos
      // Backend doesn't have /api/v1/processed-videos endpoint
      return ApiResponse.success(<ProcessingStatus>[]);
    } on DioException catch (e) {
      return _handleApiError<List<ProcessingStatus>>(e);
    } catch (e) {
      return ApiResponse.error('Failed to get processed videos: $e');
    }
  }

  // =====================================================
  // PERFORMANCE METRICS & ANALYTICS
  // =====================================================

  /// Get current workflow performance metrics
  Future<ApiResponse<WorkflowPerformanceMetrics>> getPerformanceMetrics() async {
    try {
      final response = await _apiClient.dio.get(
        '$_workflowBaseUrl/analytics/performance',
      );

      // Legacy error handling - if analytics contains error field (old format)
      if (response.data['analytics'] != null && 
          response.data['analytics']['error'] != null) {
        return ApiResponse.error(
          'No analytics found: ${response.data['analytics']['error']}'
        );
      }

      // Handle new format with status indicator
      if (response.data['analytics'] != null && 
          response.data['analytics']['status'] == 'no_data') {
        // Create empty metrics with the helpful message
        final noDataMetrics = WorkflowPerformanceMetrics(
          cpuUsageReduction: 0.0,
          memoryUsageReduction: 0.0,
          activeSessionsCount: 0,
          processedVideosCount: 0,
          lastUpdated: DateTime.now(),
        );
        return ApiResponse.success(noDataMetrics);
      }

      final metrics = WorkflowPerformanceMetrics.fromJson(response.data);
      return ApiResponse.success(metrics);
    } on DioException catch (e) {
      return _handleApiError<WorkflowPerformanceMetrics>(e);
    } catch (e) {
      return ApiResponse.error('Failed to get performance metrics: $e');
    }
  }

  /// Get historical performance data
  Future<ApiResponse<List<WorkflowPerformanceMetrics>>> getPerformanceHistory({
    DateTime? startDate,
    DateTime? endDate,
    String? interval, // 'hour', 'day', 'week'
  }) async {
    try {
      final queryParams = <String, dynamic>{
        if (startDate != null) 'start_date': startDate.toIso8601String(),
        if (endDate != null) 'end_date': endDate.toIso8601String(),
        if (interval != null) 'interval': interval,
      };

      final response = await _apiClient.dio.get(
        '$_workflowBaseUrl/api/v1/performance-metrics/history',
        queryParameters: queryParams,
      );

      final history = (response.data as List)
          .map((json) => WorkflowPerformanceMetrics.fromJson(json))
          .toList();
      
      return ApiResponse.success(history);
    } on DioException catch (e) {
      return _handleApiError<List<WorkflowPerformanceMetrics>>(e);
    } catch (e) {
      return ApiResponse.error('Failed to get performance history: $e');
    }
  }

  /// Get analytics summary for dashboard widgets
  Future<ApiResponse<Map<String, dynamic>>> getAnalyticsSummary({
    int days = 7,
  }) async {
    try {
      final response = await _apiClient.dio.get(
        '$_workflowBaseUrl/analytics/summary',
        queryParameters: {'days': days},
      );
      
      return ApiResponse.success(response.data);
    } on DioException catch (e) {
      return _handleApiError<Map<String, dynamic>>(e);
    } catch (e) {
      return ApiResponse.error('Failed to get analytics summary: $e');
    }
  }

  /// Get database status and statistics
  Future<ApiResponse<Map<String, dynamic>>> getDatabaseStatus() async {
    try {
      final response = await _apiClient.dio.get(
        '$_workflowBaseUrl/database/status',
      );
      
      return ApiResponse.success(response.data);
    } on DioException catch (e) {
      return _handleApiError<Map<String, dynamic>>(e);
    } catch (e) {
      return ApiResponse.error('Failed to get database status: $e');
    }
  }

  // =====================================================
  // HEALTH & STATUS ENDPOINTS
  // =====================================================

  /// Check if workflow services are healthy and available
  Future<ApiResponse<Map<String, dynamic>>> checkWorkflowHealth() async {
    try {
      final response = await _apiClient.dio.get(
        '$_workflowBaseUrl/health',
      );

      return ApiResponse.success(response.data);
    } on DioException catch (e) {
      return _handleApiError<Map<String, dynamic>>(e);
    } catch (e) {
      return ApiResponse.error('Failed to check workflow health: $e');
    }
  }

  /// Get workflow service capabilities and available methods
  Future<ApiResponse<Map<String, dynamic>>> getWorkflowCapabilities() async {
    try {
      final response = await _apiClient.dio.get(
        '$_workflowBaseUrl/api/v1/capabilities',
      );

      return ApiResponse.success(response.data);
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
