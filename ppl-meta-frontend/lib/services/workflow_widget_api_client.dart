import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import '../core/api/api_client.dart';
import '../core/config/app_config.dart';
import '../models/workflow_widget_models.dart';
import '../models/api_response.dart';

/// Workflow Widget API client for authenticated widget endpoints
/// Handles processing status, analytics, and health monitoring for Flutter widgets
class WorkflowWidgetApiClient {
  late final ApiClient _apiClient;
  final dynamic _authManager; // Accept dynamic to allow for adapter pattern
  final String baseUrl;

  WorkflowWidgetApiClient({
    String? baseUrl,
    ApiClient? apiClient,
    required dynamic authManager, // Changed from AuthManager to dynamic
  }) : baseUrl = baseUrl ?? 'http://localhost:8080', // Use gateway URL
        _authManager = authManager {
    // ALWAYS create our own ApiClient to avoid baseUrl conflicts
    // Do NOT reuse the shared instance as it causes baseUrl to be overwritten
    _apiClient = ApiClient(AppConfig.instance);
    
    // Configure for workflow widget APIs - safe because this is our own instance
    _apiClient.dio.options.baseUrl = this.baseUrl;
    _apiClient.dio.options.connectTimeout = const Duration(seconds: 30);
    _apiClient.dio.options.receiveTimeout = const Duration(seconds: 60);
    
    // Add authentication interceptor
    _apiClient.dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) async {
          // Add authentication token from AuthManager
          String? token = _authManager.token;
          
          // If token is null, try async method if available
          if (token == null) {
            try {
              // Use dynamic to check for getToken method
              final dynamic authManager = _authManager;
              if (authManager.getToken != null) {
                token = await authManager.getToken();
              }
            } catch (e) {
              debugPrint('⚠️ WorkflowWidgetAPI: Error getting token: $e');
            }
          }
          
          if (token != null) {
            options.headers['Authorization'] = 'Bearer $token';
          } else {
            debugPrint('⚠️ WorkflowWidgetAPI: No authentication token available');
          }
          handler.next(options);
        },
        onError: (error, handler) async {
          // Handle authentication errors
          if (error.response?.statusCode == 401) {
            debugPrint('🔓 WorkflowWidgetAPI: Authentication failed, token may be expired');
            // The AuthManager will handle token refresh/logout
          }
          handler.next(error);
        },
      ),
    );
    
    // Add logging interceptor for development
    if (kDebugMode) {
      _apiClient.dio.interceptors.add(LogInterceptor(
        requestBody: true,
        responseBody: true,
        logPrint: (object) => debugPrint('WorkflowWidgetAPI: $object'),
      ));
    }
  }

  // =====================================================
  // PROCESSING STATUS ENDPOINTS
  // =====================================================

  /// Get widget-optimized processing status for a media item
  Future<ApiResponse<WidgetStatusResponse>> getWidgetProcessingStatus({
    required String mediaUuid,
    bool includeProgress = true,
  }) async {
    try {
      final response = await _apiClient.get(
        '/api/v1/processing-status/$mediaUuid/widget',
        queryParameters: {
          'include_progress': includeProgress,
        },
      );

      final widgetStatus = WidgetStatusResponse.fromJson(response.data);
      
      return ApiResponse<WidgetStatusResponse>.success(
        widgetStatus,
        message: 'Widget processing status retrieved successfully',
      );
    } on DioException catch (e) {
      // 404 is expected when endpoint doesn't exist on backend yet - don't log as error
      if (e.response?.statusCode == 404) {
        debugPrint('ℹ️ Widget processing status endpoint not available (404) - feature not implemented yet');
        return ApiResponse<WidgetStatusResponse>.error(
          'Processing status not available',
        );
      }
      debugPrint('❌ Error getting widget processing status: $e');
      return ApiResponse<WidgetStatusResponse>.error(
        _handleDioError(e, 'Failed to get widget processing status'),
      );
    } catch (e) {
      debugPrint('❌ Unexpected error getting widget processing status: $e');
      return ApiResponse<WidgetStatusResponse>.error(
        'Unexpected error: $e',
      );
    }
  }

  /// Get processing analytics for widget dashboard
  Future<ApiResponse<WidgetAnalyticsResponse>> getWidgetProcessingAnalytics({
    required String mediaUuid,
  }) async {
    try {
      final response = await _apiClient.get(
        '/api/v1/processing-status/$mediaUuid/analytics',
      );

      final analytics = WidgetAnalyticsResponse.fromJson(response.data);
      
      return ApiResponse<WidgetAnalyticsResponse>.success(
        analytics,
        message: 'Widget processing analytics retrieved successfully',
      );
    } on DioException catch (e) {
      debugPrint('❌ Error getting widget processing analytics: $e');
      return ApiResponse<WidgetAnalyticsResponse>.error(
        _handleDioError(e, 'Failed to get widget processing analytics'),
      );
    } catch (e) {
      debugPrint('❌ Unexpected error getting widget processing analytics: $e');
      return ApiResponse<WidgetAnalyticsResponse>.error(
        'Unexpected error: $e',
      );
    }
  }

  // =====================================================
  // SYSTEM HEALTH ENDPOINTS
  // =====================================================

  /// Get system health status for monitoring widgets
  Future<ApiResponse<SystemHealthResponse>> getProcessingSystemHealth() async {
    try {
      final response = await _apiClient.get(
        '/api/v1/processing-status/health',
      );

      final health = SystemHealthResponse.fromJson(response.data);
      
      return ApiResponse<SystemHealthResponse>.success(
        health,
        message: 'System health retrieved successfully',
      );
    } on DioException catch (e) {
      debugPrint('❌ Error getting system health: $e');
      return ApiResponse<SystemHealthResponse>.error(
        _handleDioError(e, 'Failed to get system health'),
      );
    } catch (e) {
      debugPrint('❌ Unexpected error getting system health: $e');
      return ApiResponse<SystemHealthResponse>.error(
        'Unexpected error: $e',
      );
    }
  }

  // =====================================================
  // SESSION MANAGEMENT ENDPOINTS
  // =====================================================

  /// Get overview of all active sessions
  Future<ApiResponse<List<SessionSummary>>> getActiveSessionsOverview({
    int limit = 10,
  }) async {
    try {
      final response = await _apiClient.get(
        '/api/v1/sessions/active/overview',
        queryParameters: {
          'limit': limit,
        },
      );

      final sessions = (response.data as List)
          .map((json) => SessionSummary.fromJson(json))
          .toList();
      
      return ApiResponse<List<SessionSummary>>.success(
        sessions,
        message: 'Active sessions overview retrieved successfully',
      );
    } on DioException catch (e) {
      debugPrint('❌ Error getting active sessions overview: $e');
      return ApiResponse<List<SessionSummary>>.error(
        _handleDioError(e, 'Failed to get active sessions overview'),
      );
    } catch (e) {
      debugPrint('❌ Unexpected error getting active sessions overview: $e');
      return ApiResponse<List<SessionSummary>>.error(
        'Unexpected error: $e',
      );
    }
  }

  // =====================================================
  // UTILITY METHODS
  // =====================================================

  /// Handle Dio errors and return user-friendly messages
  String _handleDioError(DioException error, String defaultMessage) {
    switch (error.type) {
      case DioExceptionType.connectionTimeout:
        return 'Connection timeout - please check your network';
      case DioExceptionType.receiveTimeout:
        return 'Request timeout - the server took too long to respond';
      case DioExceptionType.badResponse:
        final statusCode = error.response?.statusCode;
        switch (statusCode) {
          case 401:
            return 'Authentication required - please login again';
          case 403:
            return 'Access denied - insufficient permissions';
          case 404:
            return 'Resource not found';
          case 500:
            return 'Server error - please try again later';
          default:
            return 'Request failed with status $statusCode';
        }
      case DioExceptionType.connectionError:
        return 'Network connection failed - please check your internet';
      default:
        return defaultMessage;
    }
  }

  /// Check if the client is properly authenticated
  bool get isAuthenticated => _authManager.isAuthenticated;

  /// Get current authentication token
  Future<String?> get authToken async {
    String? token = _authManager.token;
    
    if (token == null) {
      try {
        // Use dynamic to check for getToken method
        final dynamic authManager = _authManager;
        if (authManager.getToken != null) {
          token = await authManager.getToken();
        }
      } catch (e) {
        debugPrint('⚠️ WorkflowWidgetAPI: Error getting token: $e');
      }
    }
    
    return token;
  }

  /// Dispose resources
  void dispose() {
    // Clean up any resources if needed
  }
}

/// Provider for WorkflowWidgetApiClient
/// This can be used with Riverpod for dependency injection
WorkflowWidgetApiClient createWorkflowWidgetApiClient(dynamic authManager, [String? baseUrl]) {
  return WorkflowWidgetApiClient(
    authManager: authManager,
    baseUrl: baseUrl ?? 'http://localhost:8003',
  );
}