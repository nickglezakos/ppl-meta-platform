import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../services/orchestrator_api_client.dart';
import '../models/api_models.dart';

// ====================
// Camera API Providers
// ====================

/// Provider for getting all cameras
final camerasProvider = FutureProvider<List<CameraDevice>>((ref) async {
  final apiClient = ref.watch(orchestratorApiClientProvider);
  final response = await apiClient.getCameras();
  
  return response.when(
    success: (cameras) => cameras,
    error: (error) => throw error,
  );
});

/// Provider for getting a specific camera by ID
final cameraProvider = FutureProvider.family<CameraDevice, String>((ref, cameraId) async {
  final apiClient = ref.watch(orchestratorApiClientProvider);
  final response = await apiClient.getCameraById(cameraId);
  
  return response.when(
    success: (camera) => camera,
    error: (error) => throw error,
  );
});

/// Provider for camera recordings
final cameraRecordingsProvider = FutureProvider.family<List<RecordingSession>, String>((ref, cameraId) async {
  final apiClient = ref.watch(orchestratorApiClientProvider);
  final response = await apiClient.getRecordings(cameraId);
  
  return response.when(
    success: (recordings) => recordings,
    error: (error) => throw error,
  );
});

/// Provider for face detection history
final faceDetectionHistoryProvider = FutureProvider.family<List<FaceDetectionResult>, FaceDetectionHistoryParams>((ref, params) async {
  final apiClient = ref.watch(orchestratorApiClientProvider);
  final response = await apiClient.getFaceDetectionHistory(
    params.cameraId,
    startTime: params.startTime,
    endTime: params.endTime,
    limit: params.limit,
  );
  
  return response.when(
    success: (results) => results,
    error: (error) => throw error,
  );
});

// ====================
// Workflow API Providers
// ====================

/// Provider for workflow templates
final workflowTemplatesProvider = FutureProvider<List<WorkflowTemplate>>((ref) async {
  final apiClient = ref.watch(orchestratorApiClientProvider);
  final response = await apiClient.getWorkflowTemplates();
  
  return response.when(
    success: (templates) => templates,
    error: (error) => throw error,
  );
});

/// Provider for workflow executions with optional filtering
final workflowExecutionsProvider = FutureProvider.family<List<WorkflowExecution>, WorkflowExecutionsParams>((ref, params) async {
  final apiClient = ref.watch(orchestratorApiClientProvider);
  final response = await apiClient.getWorkflowExecutions(
    status: params.status,
    limit: params.limit,
    offset: params.offset,
  );
  
  return response.when(
    success: (executions) => executions,
    error: (error) => throw error,
  );
});

/// Provider for a specific workflow execution
final workflowExecutionProvider = FutureProvider.family<WorkflowExecution, String>((ref, workflowId) async {
  final apiClient = ref.watch(orchestratorApiClientProvider);
  final response = await apiClient.getWorkflowExecution(workflowId);
  
  return response.when(
    success: (execution) => execution,
    error: (error) => throw error,
  );
});

// ====================
// Automation API Providers
// ====================

/// Provider for automation rules
final automationRulesProvider = FutureProvider<List<AutomationRule>>((ref) async {
  final apiClient = ref.watch(orchestratorApiClientProvider);
  final response = await apiClient.getAutomationRules();
  
  return response.when(
    success: (rules) => rules,
    error: (error) => throw error,
  );
});

/// Provider for automation execution history
final automationHistoryProvider = FutureProvider.family<List<AutomationExecution>, AutomationHistoryParams>((ref, params) async {
  final apiClient = ref.watch(orchestratorApiClientProvider);
  final response = await apiClient.getAutomationHistory(
    ruleId: params.ruleId,
    startTime: params.startTime,
    endTime: params.endTime,
    limit: params.limit,
  );
  
  return response.when(
    success: (executions) => executions,
    error: (error) => throw error,
  );
});

// ====================
// Analytics API Providers
// ====================

/// Provider for analytics overview
final analyticsOverviewProvider = FutureProvider.family<AnalyticsOverview, AnalyticsTimeRange>((ref, timeRange) async {
  final apiClient = ref.watch(orchestratorApiClientProvider);
  final response = await apiClient.getAnalyticsOverview(
    startTime: timeRange.startTime,
    endTime: timeRange.endTime,
  );
  
  return response.when(
    success: (overview) => overview,
    error: (error) => throw error,
  );
});

/// Provider for detection trends
final detectionTrendsProvider = FutureProvider.family<List<DetectionTrend>, DetectionTrendsParams>((ref, params) async {
  final apiClient = ref.watch(orchestratorApiClientProvider);
  final response = await apiClient.getDetectionTrends(
    cameraId: params.cameraId,
    timeRange: params.timeRange,
  );
  
  return response.when(
    success: (trends) => trends,
    error: (error) => throw error,
  );
});

/// Provider for system metrics
final systemMetricsProvider = FutureProvider<SystemMetrics>((ref) async {
  final apiClient = ref.watch(orchestratorApiClientProvider);
  final response = await apiClient.getSystemMetrics();
  
  return response.when(
    success: (metrics) => metrics,
    error: (error) => throw error,
  );
});

// ====================
// Health Check Provider
// ====================

/// Provider for system health status
final healthStatusProvider = FutureProvider<HealthStatus>((ref) async {
  final apiClient = ref.watch(orchestratorApiClientProvider);
  final response = await apiClient.getHealthStatus();
  
  return response.when(
    success: (health) => health,
    error: (error) => throw error,
  );
});

// ====================
// State Management Providers
// ====================

/// Provider for managing API operation state
final apiOperationStateProvider = StateNotifierProvider<ApiOperationStateNotifier, ApiOperationState>((ref) {
  return ApiOperationStateNotifier();
});

class ApiOperationStateNotifier extends StateNotifier<ApiOperationState> {
  ApiOperationStateNotifier() : super(ApiOperationState.idle());

  void setLoading(String operation) {
    state = ApiOperationState.loading(operation);
  }

  void setSuccess(String operation, {String? message}) {
    state = ApiOperationState.success(operation, message: message);
  }

  void setError(String operation, String error) {
    state = ApiOperationState.error(operation, error);
  }

  void reset() {
    state = ApiOperationState.idle();
  }
}

class ApiOperationState {
  final ApiOperationStatus status;
  final String? operation;
  final String? message;
  final String? error;

  const ApiOperationState({
    required this.status,
    this.operation,
    this.message,
    this.error,
  });

  factory ApiOperationState.idle() {
    return const ApiOperationState(status: ApiOperationStatus.idle);
  }

  factory ApiOperationState.loading(String operation) {
    return ApiOperationState(
      status: ApiOperationStatus.loading,
      operation: operation,
    );
  }

  factory ApiOperationState.success(String operation, {String? message}) {
    return ApiOperationState(
      status: ApiOperationStatus.success,
      operation: operation,
      message: message,
    );
  }

  factory ApiOperationState.error(String operation, String error) {
    return ApiOperationState(
      status: ApiOperationStatus.error,
      operation: operation,
      error: error,
    );
  }

  bool get isIdle => status == ApiOperationStatus.idle;
  bool get isLoading => status == ApiOperationStatus.loading;
  bool get isSuccess => status == ApiOperationStatus.success;
  bool get isError => status == ApiOperationStatus.error;
}

enum ApiOperationStatus {
  idle,
  loading,
  success,
  error,
}

// ====================
// Parameter Classes
// ====================

class FaceDetectionHistoryParams {
  final String cameraId;
  final DateTime? startTime;
  final DateTime? endTime;
  final int? limit;

  const FaceDetectionHistoryParams({
    required this.cameraId,
    this.startTime,
    this.endTime,
    this.limit,
  });

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    return other is FaceDetectionHistoryParams &&
        other.cameraId == cameraId &&
        other.startTime == startTime &&
        other.endTime == endTime &&
        other.limit == limit;
  }

  @override
  int get hashCode {
    return Object.hash(cameraId, startTime, endTime, limit);
  }
}

class WorkflowExecutionsParams {
  final WorkflowStatus? status;
  final int? limit;
  final int? offset;

  const WorkflowExecutionsParams({
    this.status,
    this.limit,
    this.offset,
  });

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    return other is WorkflowExecutionsParams &&
        other.status == status &&
        other.limit == limit &&
        other.offset == offset;
  }

  @override
  int get hashCode {
    return Object.hash(status, limit, offset);
  }
}

class AutomationHistoryParams {
  final String? ruleId;
  final DateTime? startTime;
  final DateTime? endTime;
  final int? limit;

  const AutomationHistoryParams({
    this.ruleId,
    this.startTime,
    this.endTime,
    this.limit,
  });

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    return other is AutomationHistoryParams &&
        other.ruleId == ruleId &&
        other.startTime == startTime &&
        other.endTime == endTime &&
        other.limit == limit;
  }

  @override
  int get hashCode {
    return Object.hash(ruleId, startTime, endTime, limit);
  }
}

class AnalyticsTimeRange {
  final DateTime? startTime;
  final DateTime? endTime;

  const AnalyticsTimeRange({
    this.startTime,
    this.endTime,
  });

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    return other is AnalyticsTimeRange &&
        other.startTime == startTime &&
        other.endTime == endTime;
  }

  @override
  int get hashCode {
    return Object.hash(startTime, endTime);
  }
}

class DetectionTrendsParams {
  final String? cameraId;
  final String timeRange;

  const DetectionTrendsParams({
    this.cameraId,
    required this.timeRange,
  });

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    return other is DetectionTrendsParams &&
        other.cameraId == cameraId &&
        other.timeRange == timeRange;
  }

  @override
  int get hashCode {
    return Object.hash(cameraId, timeRange);
  }
}

// ====================
// Action Providers
// ====================

/// Provider for camera actions
final cameraActionsProvider = Provider<CameraActions>((ref) {
  final apiClient = ref.watch(orchestratorApiClientProvider);
  final operationState = ref.watch(apiOperationStateProvider.notifier);
  return CameraActions(apiClient, operationState);
});

class CameraActions {
  final OrchestratorApiClient _apiClient;
  final ApiOperationStateNotifier _operationState;

  CameraActions(this._apiClient, this._operationState);

  Future<bool> startRecording(String cameraId, RecordingRequest request) async {
    _operationState.setLoading('Starting recording');
    try {
      final response = await _apiClient.startRecording(cameraId, request);
      return response.when(
        success: (session) {
          _operationState.setSuccess('Recording started', message: 'Recording ${session.filename} started');
          return true;
        },
        error: (error) {
          _operationState.setError('Recording failed', error.message);
          return false;
        },
      );
    } catch (e) {
      _operationState.setError('Recording failed', e.toString());
      return false;
    }
  }

  Future<bool> stopRecording(String cameraId, String sessionId) async {
    _operationState.setLoading('Stopping recording');
    try {
      final response = await _apiClient.stopRecording(cameraId, sessionId);
      return response.when(
        success: (_) {
          _operationState.setSuccess('Recording stopped', message: 'Recording stopped successfully');
          return true;
        },
        error: (error) {
          _operationState.setError('Stop recording failed', error.message);
          return false;
        },
      );
    } catch (e) {
      _operationState.setError('Stop recording failed', e.toString());
      return false;
    }
  }

  Future<FaceDetectionResult?> detectFaces(String cameraId, FaceDetectionRequest request) async {
    _operationState.setLoading('Detecting faces');
    try {
      final response = await _apiClient.detectFaces(cameraId, request);
      return response.when(
        success: (result) {
          _operationState.setSuccess('Face detection completed', 
              message: 'Found ${result.faces.length} faces');
          return result;
        },
        error: (error) {
          _operationState.setError('Face detection failed', error.message);
          return null;
        },
      );
    } catch (e) {
      _operationState.setError('Face detection failed', e.toString());
      return null;
    }
  }

  Future<bool> updateCamera(String cameraId, CameraUpdateRequest request) async {
    _operationState.setLoading('Updating camera');
    try {
      final response = await _apiClient.updateCamera(cameraId, request);
      return response.when(
        success: (camera) {
          _operationState.setSuccess('Camera updated', message: 'Camera ${camera.name} updated');
          return true;
        },
        error: (error) {
          _operationState.setError('Camera update failed', error.message);
          return false;
        },
      );
    } catch (e) {
      _operationState.setError('Camera update failed', e.toString());
      return false;
    }
  }
}

/// Provider for workflow actions
final workflowActionsProvider = Provider<WorkflowActions>((ref) {
  final apiClient = ref.watch(orchestratorApiClientProvider);
  final operationState = ref.watch(apiOperationStateProvider.notifier);
  return WorkflowActions(apiClient, operationState);
});

class WorkflowActions {
  final OrchestratorApiClient _apiClient;
  final ApiOperationStateNotifier _operationState;

  WorkflowActions(this._apiClient, this._operationState);

  Future<WorkflowExecution?> createWorkflow(WorkflowCreateRequest request) async {
    _operationState.setLoading('Creating workflow');
    try {
      final response = await _apiClient.createWorkflow(request);
      return response.when(
        success: (execution) {
          _operationState.setSuccess('Workflow created', 
              message: 'Workflow ${execution.name} created');
          return execution;
        },
        error: (error) {
          _operationState.setError('Workflow creation failed', error.message);
          return null;
        },
      );
    } catch (e) {
      _operationState.setError('Workflow creation failed', e.toString());
      return null;
    }
  }

  Future<bool> cancelWorkflow(String workflowId) async {
    _operationState.setLoading('Cancelling workflow');
    try {
      final response = await _apiClient.cancelWorkflow(workflowId);
      return response.when(
        success: (_) {
          _operationState.setSuccess('Workflow cancelled', 
              message: 'Workflow cancelled successfully');
          return true;
        },
        error: (error) {
          _operationState.setError('Workflow cancellation failed', error.message);
          return false;
        },
      );
    } catch (e) {
      _operationState.setError('Workflow cancellation failed', e.toString());
      return false;
    }
  }
}

/// Provider for automation actions
final automationActionsProvider = Provider<AutomationActions>((ref) {
  final apiClient = ref.watch(orchestratorApiClientProvider);
  final operationState = ref.watch(apiOperationStateProvider.notifier);
  return AutomationActions(apiClient, operationState);
});

class AutomationActions {
  final OrchestratorApiClient _apiClient;
  final ApiOperationStateNotifier _operationState;

  AutomationActions(this._apiClient, this._operationState);

  Future<AutomationRule?> createRule(AutomationRuleCreateRequest request) async {
    _operationState.setLoading('Creating automation rule');
    try {
      final response = await _apiClient.createAutomationRule(request);
      return response.when(
        success: (rule) {
          _operationState.setSuccess('Automation rule created', 
              message: 'Rule ${rule.name} created');
          return rule;
        },
        error: (error) {
          _operationState.setError('Rule creation failed', error.message);
          return null;
        },
      );
    } catch (e) {
      _operationState.setError('Rule creation failed', e.toString());
      return null;
    }
  }

  Future<bool> enableRule(String ruleId) async {
    _operationState.setLoading('Enabling automation rule');
    try {
      final response = await _apiClient.enableAutomationRule(ruleId);
      return response.when(
        success: (_) {
          _operationState.setSuccess('Rule enabled', 
              message: 'Automation rule enabled');
          return true;
        },
        error: (error) {
          _operationState.setError('Rule enable failed', error.message);
          return false;
        },
      );
    } catch (e) {
      _operationState.setError('Rule enable failed', e.toString());
      return false;
    }
  }

  Future<bool> disableRule(String ruleId) async {
    _operationState.setLoading('Disabling automation rule');
    try {
      final response = await _apiClient.disableAutomationRule(ruleId);
      return response.when(
        success: (_) {
          _operationState.setSuccess('Rule disabled', 
              message: 'Automation rule disabled');
          return true;
        },
        error: (error) {
          _operationState.setError('Rule disable failed', error.message);
          return false;
        },
      );
    } catch (e) {
      _operationState.setError('Rule disable failed', e.toString());
      return false;
    }
  }

  Future<bool> deleteRule(String ruleId) async {
    _operationState.setLoading('Deleting automation rule');
    try {
      final response = await _apiClient.deleteAutomationRule(ruleId);
      return response.when(
        success: (_) {
          _operationState.setSuccess('Rule deleted', 
              message: 'Automation rule deleted');
          return true;
        },
        error: (error) {
          _operationState.setError('Rule deletion failed', error.message);
          return false;
        },
      );
    } catch (e) {
      _operationState.setError('Rule deletion failed', e.toString());
      return false;
    }
  }
}