import 'dart:async';
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/api_models.dart';
import '../core/services/auth_service.dart';

/// HTTP client provider with timeout configuration
final httpClientProvider = Provider<http.Client>((ref) {
  return http.Client();
});

/// Base API configuration provider
final apiConfigProvider = Provider<ApiConfig>((ref) {
  return ApiConfig(
    baseUrl: 'http://localhost:8002', // Direct Orchestrator service - Gateway routes not available for sessions
    timeout: const Duration(seconds: 30),
    retryAttempts: 3,
    retryDelay: const Duration(seconds: 2),
  );
});

/// Main API client provider
final orchestratorApiClientProvider = Provider<OrchestratorApiClient>((ref) {
  final client = ref.watch(httpClientProvider);
  final config = ref.watch(apiConfigProvider);
  final authService = ref.watch(authServiceProvider);
  return OrchestratorApiClient(client: client, config: config, authService: authService);
});

/// Comprehensive Orchestrator API Client
class OrchestratorApiClient {
  final http.Client client;
  final ApiConfig config;
  final AuthService authService;
  
  OrchestratorApiClient({
    required this.client,
    required this.config,
    required this.authService,
  });

  /// Authentication endpoints
  Future<ApiResponse<AuthResponse>> login(LoginRequest request) async {
    return _makeRequest<AuthResponse>(
      'POST',
      '/api/v1/auth/login',
      body: request.toJson(),
      fromJson: (json) => AuthResponse.fromJson(json),
    );
  }

  Future<ApiResponse<void>> logout() async {
    return _makeRequest<void>(
      'POST',
      '/api/v1/auth/logout',
      fromJson: (json) => null,
    );
  }

  /// Camera management endpoints
  Future<ApiResponse<List<CameraDevice>>> getCameras() async {
    return _makeRequest<List<CameraDevice>>(
      'GET',
      '/api/v1/cameras',
      fromJson: (json) => (json as List)
          .map((item) => CameraDevice.fromJson(item))
          .toList(),
    );
  }

  Future<ApiResponse<CameraDevice>> getCameraById(String cameraId) async {
    return _makeRequest<CameraDevice>(
      'GET',
      '/api/v1/cameras/$cameraId',
      fromJson: (json) => CameraDevice.fromJson(json),
    );
  }

  Future<ApiResponse<CameraDevice>> updateCamera(String cameraId, CameraUpdateRequest request) async {
    return _makeRequest<CameraDevice>(
      'PUT',
      '/api/v1/cameras/$cameraId',
      body: request.toJson(),
      fromJson: (json) => CameraDevice.fromJson(json),
    );
  }

  Future<ApiResponse<void>> deleteCamera(String cameraId) async {
    return _makeRequest<void>(
      'DELETE',
      '/api/v1/cameras/$cameraId',
      fromJson: (json) => null,
    );
  }

  /// Recording control endpoints
  Future<ApiResponse<RecordingSession>> startRecording(String cameraId, RecordingRequest request) async {
    return _makeRequest<RecordingSession>(
      'POST',
      '/api/v1/cameras/$cameraId/recording/start',
      body: request.toJson(),
      fromJson: (json) => RecordingSession.fromJson(json),
    );
  }

  Future<ApiResponse<void>> stopRecording(String cameraId, String sessionId) async {
    return _makeRequest<void>(
      'POST',
      '/api/v1/cameras/$cameraId/recording/$sessionId/stop',
      fromJson: (json) => null,
    );
  }

  Future<ApiResponse<List<RecordingSession>>> getRecordings(String cameraId) async {
    return _makeRequest<List<RecordingSession>>(
      'GET',
      '/api/v1/cameras/$cameraId/recordings',
      fromJson: (json) => (json as List)
          .map((item) => RecordingSession.fromJson(item))
          .toList(),
    );
  }

  /// Face detection endpoints
  Future<ApiResponse<FaceDetectionResult>> detectFaces(String cameraId, FaceDetectionRequest request) async {
    return _makeRequest<FaceDetectionResult>(
      'POST',
      '/api/v1/cameras/$cameraId/detect-faces',
      body: request.toJson(),
      fromJson: (json) => FaceDetectionResult.fromJson(json),
    );
  }

  Future<ApiResponse<List<FaceDetectionResult>>> getFaceDetectionHistory(
    String cameraId, {
    DateTime? startTime,
    DateTime? endTime,
    int? limit,
  }) async {
    final queryParams = <String, String>{};
    if (startTime != null) queryParams['start_time'] = startTime.toIso8601String();
    if (endTime != null) queryParams['end_time'] = endTime.toIso8601String();
    if (limit != null) queryParams['limit'] = limit.toString();

    return _makeRequest<List<FaceDetectionResult>>(
      'GET',
      '/api/v1/cameras/$cameraId/face-detection/history',
      queryParams: queryParams,
      fromJson: (json) => (json as List)
          .map((item) => FaceDetectionResult.fromJson(item))
          .toList(),
    );
  }

  /// Workflow management endpoints
  Future<ApiResponse<List<WorkflowTemplate>>> getWorkflowTemplates() async {
    return _makeRequest<List<WorkflowTemplate>>(
      'GET',
      '/api/v1/workflows/templates',
      fromJson: (json) => (json as List)
          .map((item) => WorkflowTemplate.fromJson(item))
          .toList(),
    );
  }

  Future<ApiResponse<WorkflowExecution>> createWorkflow(WorkflowCreateRequest request) async {
    return _makeRequest<WorkflowExecution>(
      'POST',
      '/api/v1/workflows',
      body: request.toJson(),
      fromJson: (json) => WorkflowExecution.fromJson(json),
    );
  }

  Future<ApiResponse<WorkflowExecution>> getWorkflowExecution(String workflowId) async {
    return _makeRequest<WorkflowExecution>(
      'GET',
      '/api/v1/workflows/$workflowId',
      fromJson: (json) => WorkflowExecution.fromJson(json),
    );
  }

  Future<ApiResponse<List<WorkflowExecution>>> getWorkflowExecutions({
    WorkflowStatus? status,
    int? limit,
    int? offset,
  }) async {
    final queryParams = <String, String>{};
    if (status != null) queryParams['status'] = status.name;
    if (limit != null) queryParams['limit'] = limit.toString();
    if (offset != null) queryParams['offset'] = offset.toString();

    return _makeRequest<List<WorkflowExecution>>(
      'GET',
      '/api/v1/workflows',
      queryParams: queryParams,
      fromJson: (json) => (json as List)
          .map((item) => WorkflowExecution.fromJson(item))
          .toList(),
    );
  }

  /// Enhanced Face Detection Session Endpoints
  /// Create a new face detection session and start processing
  Future<ApiResponse<FaceDetectionSession>> createFaceDetectionSession(
    String mediaId, {
    bool deduplication = true,
    bool includeStatistics = true,
    bool sessionMonitoring = true,
    String processingMode = 'async',
    double confidenceThreshold = 0.7,
    int maxFacesPerFrame = 50,
  }) async {
    return _makeRequest<FaceDetectionSession>(
      'POST',
      '/api/v1/face-detection',
      body: {
        'media_id': mediaId,
        'options': {
          'deduplication': deduplication,
          'include_statistics': includeStatistics,
          'session_monitoring': sessionMonitoring,
          'processing_mode': processingMode,
        },
        'face_detection_settings': {
          'confidence_threshold': confidenceThreshold,
          'max_faces_per_frame': maxFacesPerFrame,
          'enable_face_clustering': true,
          'enable_emotion_detection': false,
        },
      },
      fromJson: (json) => FaceDetectionSession.fromJson(json),
    );
  }

  /// Get face detection session status and results
  Future<ApiResponse<FaceDetectionSession>> getFaceDetectionSessionStatus(String sessionId) async {
    return _makeRequest<FaceDetectionSession>(
      'GET',
      '/api/v1/sessions/$sessionId',
      fromJson: (json) => FaceDetectionSession.fromJson(json),
    );
  }

  /// List all face detection sessions
  Future<ApiResponse<FaceDetectionSessionList>> listFaceDetectionSessions() async {
    return _makeRequest<FaceDetectionSessionList>(
      'GET',
      '/api/v1/sessions',
      fromJson: (json) => FaceDetectionSessionList.fromJson(json),
    );
  }

  /// Get face detection results for media (handles both stored and live processing)
  Future<ApiResponse<MediaFaceDetectionResponse>> getMediaFaceDetection(String mediaId) async {
    return _makeRequest<MediaFaceDetectionResponse>(
      'GET',
      '/api/v1/face-detection/media/$mediaId',
      fromJson: (json) => MediaFaceDetectionResponse.fromJson(json),
    );
  }

  /// ENHANCED LOGIC V2: Get person objects and face count using new session-based workflow  
  /// This uses the Enhanced Logic V2 endpoint with session-based processing directly on Orchestrator
  Future<ApiResponse<PersonObjectsResponse>> getPersonObjects(String mediaId) async {
    return _makeRequestWithCustomBaseUrl<PersonObjectsResponse>(
      'GET',
      '/api/v1/media/$mediaId/faces/enhanced-v2',
      baseUrl: 'http://localhost:8002', // Call Orchestrator directly for Enhanced Logic V2
      fromJson: (json) => PersonObjectsResponse.fromEnhancedV2Json(json),
    );
  }

  /// ENHANCED LOGIC V2: Get detailed face data using Enhanced Logic V2 endpoint
  /// This returns the full Enhanced Logic V2 response with individual face data
  Future<ApiResponse<EnhancedLogicV2Response>> getEnhancedLogicV2Response(String mediaId) async {
    return _makeRequestWithCustomBaseUrl<EnhancedLogicV2Response>(
      'GET',
      '/api/v1/media/$mediaId/faces/enhanced-v2',
      baseUrl: 'http://localhost:8002', // Call Orchestrator directly for Enhanced Logic V2
      fromJson: (json) => EnhancedLogicV2Response.fromJson(json),
    );
  }

  /// NEW: Session-based face detection for media
  /// This method creates a session and polls for results, integrating with the working backend endpoints
  Future<ApiResponse<FaceDetectionSession>> getSessionBasedFaceDetection(String mediaId) async {
    try {
      // Step 1: Create face detection session
      final sessionResponse = await createFaceDetectionSession(mediaId);
      
      if (!sessionResponse.isSuccess || sessionResponse.data == null) {
        return ApiResponse.error(
          sessionResponse.error ?? ApiException('Failed to create face detection session')
        );
      }
      
      final session = sessionResponse.data!;
      final sessionId = session.sessionId;
      
      // Step 2: Poll for completion (up to 30 seconds with 1-second intervals)
      for (int i = 0; i < 30; i++) {
        final statusResponse = await getFaceDetectionSessionStatus(sessionId);
        
        if (!statusResponse.isSuccess || statusResponse.data == null) {
          return ApiResponse.error(
            statusResponse.error ?? ApiException('Failed to get session status')
          );
        }
        
        final currentSession = statusResponse.data!;
        
        // Check if completed
        if (currentSession.isCompleted || currentSession.status == 'finished' || currentSession.status == 'complete') {
          return ApiResponse.success(currentSession);
        }
        
        // Check if failed
        if (currentSession.isFailed) {
          return ApiResponse.error(
            ApiException('Face detection session failed: ${currentSession.error ?? "Unknown error"}')
          );
        }
        
        // Wait 1 second before next poll
        await Future.delayed(const Duration(seconds: 1));
      }
      
      // Timeout after 30 seconds
      return ApiResponse.error(
        ApiException('Face detection session timeout after 30 seconds')
      );
      
    } catch (e) {
      return ApiResponse.error(
        ApiException('Session-based face detection error: $e')
      );
    }
  }

  Future<ApiResponse<void>> cancelWorkflow(String workflowId) async {
    return _makeRequest<void>(
      'POST',
      '/api/v1/workflows/$workflowId/cancel',
      fromJson: (json) => null,
    );
  }

  /// Automation engine endpoints
  Future<ApiResponse<List<AutomationRule>>> getAutomationRules() async {
    return _makeRequest<List<AutomationRule>>(
      'GET',
      '/api/v1/automation/rules',
      fromJson: (json) => (json as List)
          .map((item) => AutomationRule.fromJson(item))
          .toList(),
    );
  }

  Future<ApiResponse<AutomationRule>> createAutomationRule(AutomationRuleCreateRequest request) async {
    return _makeRequest<AutomationRule>(
      'POST',
      '/api/v1/automation/rules',
      body: request.toJson(),
      fromJson: (json) => AutomationRule.fromJson(json),
    );
  }

  Future<ApiResponse<AutomationRule>> updateAutomationRule(String ruleId, AutomationRuleUpdateRequest request) async {
    return _makeRequest<AutomationRule>(
      'PUT',
      '/api/v1/automation/rules/$ruleId',
      body: request.toJson(),
      fromJson: (json) => AutomationRule.fromJson(json),
    );
  }

  Future<ApiResponse<void>> deleteAutomationRule(String ruleId) async {
    return _makeRequest<void>(
      'DELETE',
      '/api/v1/automation/rules/$ruleId',
      fromJson: (json) => null,
    );
  }

  Future<ApiResponse<void>> enableAutomationRule(String ruleId) async {
    return _makeRequest<void>(
      'POST',
      '/api/v1/automation/rules/$ruleId/enable',
      fromJson: (json) => null,
    );
  }

  Future<ApiResponse<void>> disableAutomationRule(String ruleId) async {
    return _makeRequest<void>(
      'POST',
      '/api/v1/automation/rules/$ruleId/disable',
      fromJson: (json) => null,
    );
  }

  Future<ApiResponse<List<AutomationExecution>>> getAutomationHistory({
    String? ruleId,
    DateTime? startTime,
    DateTime? endTime,
    int? limit,
  }) async {
    final queryParams = <String, String>{};
    if (ruleId != null) queryParams['rule_id'] = ruleId;
    if (startTime != null) queryParams['start_time'] = startTime.toIso8601String();
    if (endTime != null) queryParams['end_time'] = endTime.toIso8601String();
    if (limit != null) queryParams['limit'] = limit.toString();

    return _makeRequest<List<AutomationExecution>>(
      'GET',
      '/api/v1/automation/history',
      queryParams: queryParams,
      fromJson: (json) => (json as List)
          .map((item) => AutomationExecution.fromJson(item))
          .toList(),
    );
  }

  /// Analytics endpoints
  Future<ApiResponse<AnalyticsOverview>> getAnalyticsOverview({
    DateTime? startTime,
    DateTime? endTime,
  }) async {
    final queryParams = <String, String>{};
    if (startTime != null) queryParams['start_time'] = startTime.toIso8601String();
    if (endTime != null) queryParams['end_time'] = endTime.toIso8601String();

    return _makeRequest<AnalyticsOverview>(
      'GET',
      '/api/v1/analytics/overview',
      queryParams: queryParams,
      fromJson: (json) => AnalyticsOverview.fromJson(json),
    );
  }

  Future<ApiResponse<List<DetectionTrend>>> getDetectionTrends({
    String? cameraId,
    String? timeRange = '24h',
  }) async {
    final queryParams = <String, String>{};
    if (cameraId != null) queryParams['camera_id'] = cameraId;
    if (timeRange != null) queryParams['time_range'] = timeRange;

    return _makeRequest<List<DetectionTrend>>(
      'GET',
      '/api/v1/analytics/detection-trends',
      queryParams: queryParams,
      fromJson: (json) => (json as List)
          .map((item) => DetectionTrend.fromJson(item))
          .toList(),
    );
  }

  Future<ApiResponse<SystemMetrics>> getSystemMetrics() async {
    return _makeRequest<SystemMetrics>(
      'GET',
      '/api/v1/system/metrics',
      fromJson: (json) => SystemMetrics.fromJson(json),
    );
  }

  /// Health check endpoint
  Future<ApiResponse<HealthStatus>> getHealthStatus() async {
    return _makeRequest<HealthStatus>(
      'GET',
      '/health',
      fromJson: (json) => HealthStatus.fromJson(json),
    );
  }

  /// Private helper method for making HTTP requests with retry logic
  Future<ApiResponse<T>> _makeRequest<T>(
    String method,
    String endpoint, {
    Map<String, dynamic>? body,
    Map<String, String>? queryParams,
    Map<String, String>? headers,
    required T Function(dynamic) fromJson,
  }) async {
    final uri = _buildUri(endpoint, queryParams);
    final defaultHeaders = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };
    
    // Add authentication header if token is available
    final token = await authService.getToken();
    if (token != null) {
      defaultHeaders['Authorization'] = 'Bearer $token';
    }
    
    final requestHeaders = {...defaultHeaders, ...?headers};

    for (int attempt = 0; attempt < config.retryAttempts; attempt++) {
      try {
        late http.Response response;

        switch (method.toUpperCase()) {
          case 'GET':
            response = await client
                .get(uri, headers: requestHeaders)
                .timeout(config.timeout);
            break;
          case 'POST':
            response = await client
                .post(
                  uri,
                  headers: requestHeaders,
                  body: body != null ? jsonEncode(body) : null,
                )
                .timeout(config.timeout);
            break;
          case 'PUT':
            response = await client
                .put(
                  uri,
                  headers: requestHeaders,
                  body: body != null ? jsonEncode(body) : null,
                )
                .timeout(config.timeout);
            break;
          case 'DELETE':
            response = await client
                .delete(uri, headers: requestHeaders)
                .timeout(config.timeout);
            break;
          default:
            throw ApiException(
              'Unsupported HTTP method: $method',
              statusCode: 0,
            );
        }

        return _handleResponse<T>(response, fromJson);
      } on TimeoutException {
        if (attempt == config.retryAttempts - 1) {
          return ApiResponse.error(
            ApiException('Request timeout after ${config.timeout.inSeconds} seconds'),
          );
        }
        await Future.delayed(config.retryDelay * (attempt + 1));
      } on http.ClientException catch (e) {
        if (attempt == config.retryAttempts - 1) {
          return ApiResponse.error(ApiException('Network error: ${e.message}'));
        }
        await Future.delayed(config.retryDelay * (attempt + 1));
      } catch (e) {
        return ApiResponse.error(ApiException('Unexpected error: $e'));
      }
    }

    return ApiResponse.error(
      ApiException('Max retry attempts reached'),
    );
  }

  /// Handle HTTP response and parse JSON
  ApiResponse<T> _handleResponse<T>(
    http.Response response,
    T Function(dynamic) fromJson,
  ) {
    try {
      if (response.statusCode >= 200 && response.statusCode < 300) {
        if (response.body.isEmpty) {
          return ApiResponse.success(fromJson(null));
        }

        final jsonData = jsonDecode(response.body);
        final data = fromJson(jsonData);
        return ApiResponse.success(data);
      } else {
        final errorMessage = _extractErrorMessage(response);
        return ApiResponse.error(
          ApiException(
            errorMessage,
            statusCode: response.statusCode,
          ),
        );
      }
    } catch (e) {
      return ApiResponse.error(
        ApiException(
          'Failed to parse response: $e',
          statusCode: response.statusCode,
        ),
      );
    }
  }

  /// Extract error message from response
  String _extractErrorMessage(http.Response response) {
    try {
      final jsonData = jsonDecode(response.body);
      if (jsonData is Map<String, dynamic>) {
        return jsonData['error'] ?? 
               jsonData['message'] ?? 
               jsonData['detail'] ??
               'HTTP ${response.statusCode}';
      }
    } catch (e) {
      // If JSON parsing fails, use status code
    }
    return 'HTTP ${response.statusCode}: ${response.reasonPhrase}';
  }

  /// Make request with custom base URL (for endpoints that need different services)
  Future<ApiResponse<T>> _makeRequestWithCustomBaseUrl<T>(
    String method,
    String endpoint, {
    required String baseUrl,
    Map<String, dynamic>? body,
    Map<String, String>? queryParams,
    Map<String, String>? headers,
    required T Function(dynamic) fromJson,
  }) async {
    final uri = Uri.parse('$baseUrl$endpoint');
    final fullUri = queryParams != null && queryParams.isNotEmpty
        ? uri.replace(queryParameters: queryParams)
        : uri;
        
    final defaultHeaders = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };
    
    // Add authentication header if token is available
    final token = await authService.getToken();
    if (token != null) {
      defaultHeaders['Authorization'] = 'Bearer $token';
    }
    
    final requestHeaders = {...defaultHeaders, ...?headers};

    for (int attempt = 0; attempt < config.retryAttempts; attempt++) {
      try {
        late http.Response response;

        switch (method.toUpperCase()) {
          case 'GET':
            response = await client
                .get(fullUri, headers: requestHeaders)
                .timeout(config.timeout);
            break;
          case 'POST':
            response = await client
                .post(
                  fullUri,
                  headers: requestHeaders,
                  body: body != null ? jsonEncode(body) : null,
                )
                .timeout(config.timeout);
            break;
          case 'PUT':
            response = await client
                .put(
                  fullUri,
                  headers: requestHeaders,
                  body: body != null ? jsonEncode(body) : null,
                )
                .timeout(config.timeout);
            break;
          case 'DELETE':
            response = await client
                .delete(fullUri, headers: requestHeaders)
                .timeout(config.timeout);
            break;
          default:
            throw ApiException('Unsupported HTTP method: $method');
        }

        if (response.statusCode >= 200 && response.statusCode < 300) {
          try {
            final data = response.body.isNotEmpty 
                ? jsonDecode(response.body) 
                : null;
            return ApiResponse.success(fromJson(data));
          } catch (e) {
            return ApiResponse.error(
              ApiException('JSON parsing error: $e', statusCode: response.statusCode),
            );
          }
        } else {
          // Handle error responses
          return ApiResponse.error(
            ApiException(
              _extractErrorMessage(response),
              statusCode: response.statusCode,
            ),
          );
        }
      } catch (e) {
        if (attempt == config.retryAttempts - 1) {
          return ApiResponse.error(
            ApiException('Network error: $e'),
          );
        }
        await Future.delayed(config.retryDelay);
      }
    }

    return ApiResponse.error(
      ApiException('Request failed after ${config.retryAttempts} attempts'),
    );
  }

  /// Build URI with query parameters
  Uri _buildUri(String endpoint, Map<String, String>? queryParams) {
    final uri = Uri.parse('${config.baseUrl}$endpoint');
    if (queryParams != null && queryParams.isNotEmpty) {
      return uri.replace(queryParameters: queryParams);
    }
    return uri;
  }

  /// Dispose resources
  void dispose() {
    client.close();
  }
}

/// API configuration class
class ApiConfig {
  final String baseUrl;
  final Duration timeout;
  final int retryAttempts;
  final Duration retryDelay;

  const ApiConfig({
    required this.baseUrl,
    required this.timeout,
    required this.retryAttempts,
    required this.retryDelay,
  });
}

/// Generic API response wrapper
class ApiResponse<T> {
  final T? data;
  final ApiException? error;
  final bool isSuccess;

  const ApiResponse._({
    this.data,
    this.error,
    required this.isSuccess,
  });

  factory ApiResponse.success(T data) {
    return ApiResponse._(data: data, isSuccess: true);
  }

  factory ApiResponse.error(ApiException error) {
    return ApiResponse._(error: error, isSuccess: false);
  }

  /// Convenience methods
  bool get isError => !isSuccess;
  bool get hasData => data != null;

  /// Transform data if successful
  ApiResponse<R> map<R>(R Function(T) transform) {
    if (isSuccess && data != null) {
      try {
        return ApiResponse.success(transform(data as T));
      } catch (e) {
        return ApiResponse.error(ApiException('Transform error: $e'));
      }
    }
    return ApiResponse.error(error!);
  }

  /// Handle both success and error cases
  R when<R>({
    required R Function(T data) success,
    required R Function(ApiException error) error,
  }) {
    if (isSuccess && data != null) {
      return success(data as T);
    }
    return error(this.error!);
  }
}

/// API exception class
class ApiException implements Exception {
  final String message;
  final int? statusCode;
  final Map<String, dynamic>? details;

  const ApiException(
    this.message, {
    this.statusCode,
    this.details,
  });

  @override
  String toString() {
    if (statusCode != null) {
      return 'ApiException($statusCode): $message';
    }
    return 'ApiException: $message';
  }

  /// Check if this is a network error
  bool get isNetworkError => statusCode == null;

  /// Check if this is a client error (4xx)
  bool get isClientError => statusCode != null && statusCode! >= 400 && statusCode! < 500;

  /// Check if this is a server error (5xx)
  bool get isServerError => statusCode != null && statusCode! >= 500;

  /// Check if this is an authentication error
  bool get isAuthError => statusCode == 401 || statusCode == 403;
}