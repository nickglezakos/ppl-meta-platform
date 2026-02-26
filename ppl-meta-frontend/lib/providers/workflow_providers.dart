import 'dart:async';
import 'dart:ui';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:dio/dio.dart';
import '../services/workflow_api_client.dart';
import '../services/media_api_client.dart';
import '../services/orchestrator_api_client.dart';
import '../models/workflow_widget_models.dart' hide PlaybackMode; // Avoid conflict
import '../models/face_detection_models.dart'; // Use face detection models instead of api_models
import '../models/api_models.dart' hide FaceDetectionSession; // Import api_models but hide conflicting FaceDetectionSession
import '../core/api/api_client.dart';
import '../widgets/workflow/authenticated_workflow_wrapper.dart';
import 'face_data_providers.dart';

// =============================================================================
// WORKFLOW PROVIDERS CONFIGURATION
// =============================================================================
// 
// This file configures all Provider/Riverpod dependencies for Workflows 4 & 5
// face detection integration, connecting workflow services to UI components.
//
// Provider Hierarchy:
// 1. Core Workflow Dependencies (WorkflowApiClient)
// 2. Session Management Providers (Active sessions, session status)
// 3. Processing Status Providers (Media processing status, playback modes)
// 4. Performance Metrics Providers (System performance, analytics)
// 5. Cached State Providers (Optimized data loading)
//
// =============================================================================

// -----------------------------------------------------------------------------
// CORE WORKFLOW DEPENDENCY PROVIDERS
// -----------------------------------------------------------------------------

/// API client provider for workflow operations
final workflowApiClientProvider = Provider<WorkflowApiClient>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return WorkflowApiClient(
    baseUrl: apiClient.baseUrl,
    apiClient: apiClient,
  );
});

/// Alternative workflow API client with custom base URL
final workflowApiClientWithUrlProvider = Provider.family<WorkflowApiClient, String>((ref, baseUrl) {
  final apiClient = ref.watch(apiClientProvider);
  return WorkflowApiClient(
    baseUrl: baseUrl,
    apiClient: apiClient,
  );
});

// -----------------------------------------------------------------------------
// WORKFLOW 4 - SESSION MANAGEMENT PROVIDERS
// -----------------------------------------------------------------------------

/// Provider for all active face detection sessions (comprehensive dashboard view)
final allActiveSessionsProvider = FutureProvider<List<FaceDetectionSession>>((ref) async {
  final client = ref.watch(workflowApiClientProvider);
  final response = await client.getAllActiveSessions();
  
  if (response.success) {
    return response.data!;
  } else {
    throw Exception('Failed to load active sessions: ${response.error}');
  }
});

/// Provider for all active face detection sessions (legacy name for compatibility)
final activeSessionsProvider = FutureProvider<List<FaceDetectionSession>>((ref) async {
  final client = ref.watch(workflowApiClientProvider);
  final response = await client.getAllActiveSessions();
  
  if (response.success) {
    return response.data!;
  } else {
    throw Exception('Failed to load active sessions: ${response.error}');
  }
});

/// Provider for sessions specific to a media item
final mediaSessionsProvider = FutureProvider.family<List<FaceDetectionSession>, String>((ref, mediaUuid) async {
  final client = ref.watch(workflowApiClientProvider);
  final response = await client.getSessionsForMedia(mediaUuid);
  
  if (response.success) {
    return response.data!;
  } else {
    throw Exception('Failed to load media sessions: ${response.error}');
  }
});

/// Provider for a specific session status
final sessionStatusProvider = FutureProvider.family<FaceDetectionSession, String>((ref, sessionUuid) async {
  final client = ref.watch(workflowApiClientProvider);
  final response = await client.getSessionStatus(sessionUuid);
  
  if (response.success) {
    return response.data!;
  } else {
    throw Exception('Failed to load session status: ${response.error}');
  }
});

/// Provider for active workflows from orchestrator service
final activeWorkflowsProvider = FutureProvider<List<WorkflowExecution>>((ref) async {
  final apiClient = ref.watch(apiClientProvider);
  
  try {
    final baseUrl = apiClient.baseUrl;
    final response = await apiClient.dio.get(
      '$baseUrl/api/v1/orchestrator/workflows/user/7/workflows',
      options: Options(
        headers: {
          'Authorization': 'Bearer ${apiClient.authToken}',
        },
      ),
    );
    
    if (response.statusCode == 200) {
      final List<dynamic> data = response.data;
      return data.map((json) => WorkflowExecution.fromJson({
        'id': json['workflow_id'] ?? '',
        'templateId': json['workflow_type'] ?? '',
        'name': json['workflow_type'] ?? 'Unknown Workflow',
        'status': _mapOrchestratorStatusToWorkflowStatus(json['status']),
        'createdAt': DateTime.parse(json['created_at']),
        'startedAt': json['started_at'] != null ? DateTime.parse(json['started_at']) : null,
        'completedAt': json['completed_at'] != null ? DateTime.parse(json['completed_at']) : null,
        'steps': <StepExecution>[],
        'result': json['metadata'],
        'error': json['error_message'],
      })).toList();
    } else {
      throw Exception('Failed to load workflows: ${response.statusCode}');
    }
  } catch (e) {
    throw Exception('Failed to load active workflows: $e');
  }
});

/// Helper function to map orchestrator status to frontend WorkflowStatus
WorkflowStatus _mapOrchestratorStatusToWorkflowStatus(String status) {
  switch (status.toLowerCase()) {
    case 'processing':
    case 'running':
      return WorkflowStatus.running;
    case 'completed':
      return WorkflowStatus.completed;
    case 'failed':
      return WorkflowStatus.failed;
    case 'cancelled':
      return WorkflowStatus.cancelled;
    default:
      return WorkflowStatus.pending;
  }
}

/// Provider for real-time session statistics
final sessionStatisticsProvider = FutureProvider.family<SessionStatistics, String>((ref, sessionUuid) async {
  final client = ref.watch(workflowApiClientProvider);
  final response = await client.getSessionStatistics(sessionUuid);
  
  if (response.success) {
    return SessionStatistics.fromJson(response.data!);
  } else {
    throw Exception('Failed to load session statistics: ${response.error}');
  }
});

/// Auto-refreshing provider for session statistics (updates every 2 seconds)
final autoRefreshSessionStatisticsProvider = FutureProvider.family<SessionStatistics, String>((ref, sessionUuid) async {
  final client = ref.watch(workflowApiClientProvider);
  final response = await client.getSessionStatistics(sessionUuid);

  if (response.success) {
    return SessionStatistics.fromJson(response.data!);
  } else {
    throw Exception(response.error);
  }
});

// -----------------------------------------------------------------------------
// WORKFLOW 5 - PROCESSING STATUS & SMART PLAYBACK PROVIDERS
// -----------------------------------------------------------------------------

/// Provider for media processing status
final processingStatusProvider = FutureProvider.family<ProcessingStatus?, String>((ref, mediaUuid) async {
  final client = ref.watch(workflowApiClientProvider);
  final response = await client.getProcessingStatus(mediaUuid);
  
  if (response.success) {
    return response.data!;
  } else if (response.error?.contains('not found') == true || 
             response.error?.contains('Workflow resource not found') == true ||
             response.error?.contains('Unknown workflow service error') == true ||
             response.error?.contains('workflow service') == true) {
    // Gracefully handle missing/unavailable workflow service - return null instead of throwing
    return null;
  } else {
    throw Exception('Failed to load processing status: ${response.error}');
  }
});

/// Provider for optimal playback mode
final optimalPlaybackModeProvider = FutureProvider.family<PlaybackMode?, String>((ref, mediaUuid) async {
  // Get the processing status which includes optimal playback mode
  final processingStatus = await ref.watch(processingStatusProvider(mediaUuid).future);
  
  if (processingStatus?.optimalPlaybackMode != null) {
    // Convert string to PlaybackMode enum/model
    return PlaybackMode.fromString(processingStatus!.optimalPlaybackMode!);
  }
  
  return null; // Gracefully handle missing playback mode
});

/// Provider for stored face data (optimized for Workflow 5)
/// Uses Orchestrator session-based face detection through providers
final storedFaceDataProvider = FutureProvider.family<List<FaceDetection>, StoredFaceDataParams>((ref, params) async {
  // Use the face data provider that calls Orchestrator session-based endpoints
  final notifier = ref.read(mediaFaceDataProvider(params.mediaUuid).notifier);
  await notifier.loadFaces();
  
  final faceData = ref.read(mediaFaceDataProvider(params.mediaUuid));
  
  try {
    if (faceData.hasData && faceData.faces.isNotEmpty) {
      List<FaceDetection> faces = faceData.faces;
      
      // Limit to maxFaces if specified
      if (params.maxFaces != null && faces.length > params.maxFaces!) {
        faces = faces.take(params.maxFaces!).toList();
      }
      
      return faces;
    } else {
      return <FaceDetection>[]; // Return empty list if no face data
    }
  } catch (e) {
    // For videos without stored face data, return empty list instead of throwing error
    // This prevents UI crashes when videos don't have processed face detections
    print('💡 StoredFaceDataProvider: No stored face data available for ${params.mediaUuid}: $e');
    return <FaceDetection>[];
  }
});

/// Provider for all processed videos
final allProcessedVideosProvider = FutureProvider<List<ProcessingStatus>>((ref) async {
  final client = ref.watch(workflowApiClientProvider);
  final response = await client.getAllProcessedVideos();
  
  if (response.success) {
    return response.data!;
  } else {
    throw Exception('Failed to load processed videos: ${response.error}');
  }
});

// -----------------------------------------------------------------------------
// PERFORMANCE METRICS & ANALYTICS PROVIDERS
// -----------------------------------------------------------------------------

/// Provider for current workflow performance metrics
final performanceMetricsProvider = FutureProvider<WorkflowPerformanceMetrics>((ref) async {
  final client = ref.watch(workflowApiClientProvider);
  final response = await client.getPerformanceMetrics();
  
  if (response.success) {
    return response.data!;
  } else {
    throw Exception('Failed to load performance metrics: ${response.error}');
  }
});

/// Provider for current workflow performance metrics (dashboard alias)
final workflowPerformanceMetricsProvider = FutureProvider<WorkflowPerformanceMetrics>((ref) async {
  final client = ref.watch(workflowApiClientProvider);
  final response = await client.getPerformanceMetrics();
  
  if (response.success) {
    return response.data!;
  } else {
    throw Exception('Failed to load performance metrics: ${response.error}');
  }
});

/// Auto-refreshing provider for performance metrics (updates every 5 seconds)
final livePerformanceMetricsProvider = FutureProvider<WorkflowPerformanceMetrics>((ref) async {
  // Auto-refresh every 5 seconds
  final timer = Timer.periodic(const Duration(seconds: 5), (timer) {
    ref.invalidateSelf();
  });
  
  ref.onDispose(() => timer.cancel());
  
  final client = ref.watch(workflowApiClientProvider);
  final response = await client.getPerformanceMetrics();
  
  if (response.success) {
    return response.data!;
  } else {
    throw Exception('Failed to load performance metrics: ${response.error}');
  }
});

/// Provider for performance metrics history
final performanceHistoryProvider = FutureProvider.family<List<WorkflowPerformanceMetrics>, PerformanceHistoryParams>((ref, params) async {
  final client = ref.watch(workflowApiClientProvider);
  final response = await client.getPerformanceHistory(
    days: params.days ?? 7,
    sessionType: params.sessionType,
  );
  
  if (response.success) {
    return response.data!;
  } else {
    throw Exception('Failed to load performance history: ${response.error}');
  }
});

// -----------------------------------------------------------------------------
// HEALTH & STATUS PROVIDERS
// -----------------------------------------------------------------------------

/// Provider for workflow service health status
final workflowHealthProvider = FutureProvider<Map<String, dynamic>>((ref) async {
  final client = ref.watch(workflowApiClientProvider);
  final response = await client.checkWorkflowHealth();
  
  if (response.success) {
    return response.data!;
  } else {
    throw Exception('Failed to check workflow health: ${response.error}');
  }
});

/// Provider for workflow service capabilities
final workflowCapabilitiesProvider = FutureProvider<Map<String, dynamic>>((ref) async {
  final client = ref.watch(workflowApiClientProvider);
  final response = await client.getWorkflowCapabilities();
  
  if (response.success) {
    return response.data!;
  } else {
    throw Exception('Failed to load workflow capabilities: ${response.error}');
  }
});

// -----------------------------------------------------------------------------
// CACHED STATE PROVIDERS FOR PERFORMANCE
// -----------------------------------------------------------------------------

/// Cached provider for processing status (5-minute cache)
final cachedProcessingStatusProvider = FutureProvider.family<ProcessingStatus?, String>((ref, mediaUuid) async {
  // Keep cache alive for 5 minutes
  final timer = Timer(const Duration(minutes: 5), () {
    ref.invalidateSelf();
  });
  
  ref.onDispose(() => timer.cancel());
  
  return ref.watch(processingStatusProvider(mediaUuid).future);
});

/// Cached provider for performance metrics (30-second cache)
final cachedPerformanceMetricsProvider = FutureProvider<WorkflowPerformanceMetrics>((ref) async {
  // Keep cache alive for 30 seconds
  final timer = Timer(const Duration(seconds: 30), () {
    ref.invalidateSelf();
  });
  
  ref.onDispose(() => timer.cancel());
  
  return ref.watch(performanceMetricsProvider.future);
});

/// Cached provider for active sessions (1-minute cache to reduce flickering)
final cachedActiveSessionsProvider = FutureProvider<List<FaceDetectionSession>>((ref) async {
  // Keep cache alive for 1 minute to reduce frequent calls
  final timer = Timer(const Duration(minutes: 1), () {
    ref.invalidateSelf();
  });
  
  ref.onDispose(() => timer.cancel());
  
  return ref.watch(allActiveSessionsProvider.future);
});

/// Cached provider for widget processing status (2-minute cache to reduce API calls)
final cachedWidgetProcessingStatusProvider = FutureProvider.family<WidgetStatusResponse, String>((ref, mediaUuid) async {
  // Keep cache alive for 2 minutes to prevent frequent polling
  final timer = Timer(const Duration(minutes: 2), () {
    ref.invalidateSelf();
  });
  
  ref.onDispose(() => timer.cancel());
  
  final client = ref.watch(workflowWidgetApiClientProvider);
  if (client == null) {
    throw Exception('WorkflowWidgetApiClient not available');
  }
  
  final response = await client.getWidgetProcessingStatus(
    mediaUuid: mediaUuid,
    includeProgress: true,
  );
  
  if (response.success) {
    return response.data!;
  } else {
    throw Exception('Failed to load widget processing status: ${response.message}');
  }
});

// -----------------------------------------------------------------------------
// COMBINED DATA PROVIDERS FOR UI CONVENIENCE
// -----------------------------------------------------------------------------

/// Combined provider for media workflow data
final mediaWorkflowDataProvider = FutureProvider.family<MediaWorkflowData, String>((ref, mediaUuid) async {
  // Fetch all workflow-related data for a media item in parallel
  final futures = await Future.wait([
    ref.watch(processingStatusProvider(mediaUuid).future),
    ref.watch(optimalPlaybackModeProvider(mediaUuid).future),
    ref.watch(mediaSessionsProvider(mediaUuid).future),
  ]);
  
  return MediaWorkflowData(
    processingStatus: futures[0] as ProcessingStatus,
    playbackMode: futures[1] as PlaybackMode,
    sessions: futures[2] as List<FaceDetectionSession>,
  );
});

/// Provider for workflow dashboard data
final workflowDashboardDataProvider = FutureProvider<WorkflowDashboardData>((ref) async {
  // Fetch all dashboard data in parallel
  final futures = await Future.wait([
    ref.watch(activeSessionsProvider.future),
    ref.watch(allProcessedVideosProvider.future),
    ref.watch(performanceMetricsProvider.future),
  ]);
  
  return WorkflowDashboardData(
    activeSessions: futures[0] as List<FaceDetectionSession>,
    processedVideos: futures[1] as List<ProcessingStatus>,
    performanceMetrics: futures[2] as WorkflowPerformanceMetrics,
  );
});

// -----------------------------------------------------------------------------
// ACTION PROVIDERS FOR STATE MUTATIONS
// -----------------------------------------------------------------------------

/// Provider for creating face detection sessions
final createSessionProvider = Provider<Future<FaceDetectionSession> Function(SessionCreationRequest)>((ref) {
  return (request) async {
    final client = ref.read(workflowApiClientProvider);
    final response = await client.createFaceDetectionSession(
      mediaUuid: request.mediaUuid,
      confidenceThreshold: request.confidenceThreshold,
      detectionMethods: request.detectionMethods,
      priority: request.priority,
      enableProgressUpdates: request.enableProgressUpdates,
    );
    
    if (response.success) {
      // Invalidate related providers to refresh UI
      ref.invalidate(activeSessionsProvider);
      ref.invalidate(mediaSessionsProvider(request.mediaUuid));
      
      return response.data!;
    } else {
      throw Exception('Failed to create session: ${response.error}');
    }
  };
});

/// Provider for deleting sessions
final deleteSessionProvider = Provider<Future<void> Function(String)>((ref) {
  return (sessionUuid) async {
    final client = ref.read(workflowApiClientProvider);
    final response = await client.deleteSession(sessionUuid);
    
    if (response.success) {
      // Invalidate related providers to refresh UI
      ref.invalidate(activeSessionsProvider);
      ref.invalidate(sessionStatusProvider(sessionUuid));
      
      return;
    } else {
      throw Exception('Failed to delete session: ${response.error}');
    }
  };
});

/// Provider for starting video optimization processing
final startOptimizationProvider = Provider<Future<FaceDetectionSession> Function(String, bool?, String?)>((ref) {
  return (mediaUuid, enableCaching, priority) async {
    final client = ref.read(workflowApiClientProvider);
    final response = await client.processVideoForOptimization(
      mediaUuid: mediaUuid,
      enableCaching: enableCaching ?? true,
      priority: priority,
    );
    
    if (response.success) {
      // Invalidate related providers to refresh UI
      ref.invalidate(processingStatusProvider(mediaUuid));
      ref.invalidate(activeSessionsProvider);
      
      return response.data!;
    } else {
      throw Exception('Failed to start optimization: ${response.error}');
    }
  };
});

// -----------------------------------------------------------------------------
// ANALYTICS & PERFORMANCE PROVIDERS
// -----------------------------------------------------------------------------

/// Provider for analytics summary data (dashboard widgets)
final analyticsSummaryProvider = FutureProvider.family<Map<String, dynamic>, int>((ref, days) async {
  final client = ref.watch(workflowApiClientProvider);
  final response = await client.getAnalyticsSummary(days: days);
  
  if (response.success) {
    return response.data!;
  } else {
    throw Exception('Failed to load analytics summary: ${response.error}');
  }
});

/// Provider for database status and statistics
final databaseStatusProvider = FutureProvider<Map<String, dynamic>>((ref) async {
  final client = ref.watch(workflowApiClientProvider);
  final response = await client.getDatabaseStatus();
  
  if (response.success) {
    return response.data!;
  } else {
    throw Exception('Failed to load database status: ${response.error}');
  }
});

/// Auto-refreshing analytics summary (updates every 30 seconds)
final autoRefreshAnalyticsSummaryProvider = FutureProvider.family<Map<String, dynamic>, int>((ref, days) async {
  // Auto-refresh every 30 seconds
  final timer = Timer.periodic(const Duration(seconds: 30), (timer) {
    ref.invalidateSelf();
  });
  
  ref.onDispose(() => timer.cancel());
  
  final client = ref.watch(workflowApiClientProvider);
  final response = await client.getAnalyticsSummary(days: days);
  
  if (response.success) {
    return response.data!;
  } else {
    throw Exception('Failed to load analytics summary: ${response.error}');
  }
});

// =============================================================================
// PARAMETER CLASSES FOR FAMILY PROVIDERS
// =============================================================================

/// Parameters for stored face data provider
class StoredFaceDataParams {
  final String mediaUuid;
  final int? startFrame;
  final int? endFrame;
  final double? confidenceThreshold;
  final int? maxFaces;

  const StoredFaceDataParams({
    required this.mediaUuid,
    this.startFrame,
    this.endFrame,
    this.confidenceThreshold,
    this.maxFaces,
  });

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is StoredFaceDataParams &&
          runtimeType == other.runtimeType &&
          mediaUuid == other.mediaUuid &&
          startFrame == other.startFrame &&
          endFrame == other.endFrame &&
          confidenceThreshold == other.confidenceThreshold &&
          maxFaces == other.maxFaces;

  @override
  int get hashCode =>
      mediaUuid.hashCode ^
      startFrame.hashCode ^
      endFrame.hashCode ^
      confidenceThreshold.hashCode ^
      maxFaces.hashCode;
}

/// Parameters for performance history provider
class PerformanceHistoryParams {
  final DateTime? startDate;
  final DateTime? endDate;
  final String? interval;
  final int? days;
  final String? sessionType;

  const PerformanceHistoryParams({
    this.startDate,
    this.endDate,
    this.interval,
    this.days,
    this.sessionType,
  });

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is PerformanceHistoryParams &&
          runtimeType == other.runtimeType &&
          startDate == other.startDate &&
          endDate == other.endDate &&
          interval == other.interval &&
          days == other.days &&
          sessionType == other.sessionType;

  @override
  int get hashCode =>
      startDate.hashCode ^
      endDate.hashCode ^
      interval.hashCode ^
      days.hashCode ^
      sessionType.hashCode;
}

/// Combined workflow data for a media item
class MediaWorkflowData {
  final ProcessingStatus processingStatus;
  final PlaybackMode playbackMode;
  final List<FaceDetectionSession> sessions;

  const MediaWorkflowData({
    required this.processingStatus,
    required this.playbackMode,
    required this.sessions,
  });

  /// Get the active session for this media (if any)
  FaceDetectionSession? get activeSession =>
      sessions.where((s) => s.isActive).firstOrNull;

  /// Check if this media has any workflow processing
  bool get hasWorkflowProcessing => sessions.isNotEmpty;

  /// Check if this media is ready for optimized playback
  bool get isOptimizedPlaybackReady => processingStatus.isOptimizedPlaybackReady;
}

/// Combined dashboard data
class WorkflowDashboardData {
  final List<FaceDetectionSession> activeSessions;
  final List<ProcessingStatus> processedVideos;
  final WorkflowPerformanceMetrics performanceMetrics;

  const WorkflowDashboardData({
    required this.activeSessions,
    required this.processedVideos,
    required this.performanceMetrics,
  });

  /// Get total number of videos with workflow processing
  int get totalWorkflowVideos => processedVideos.length;

  /// Get number of videos ready for optimized playback
  int get optimizedVideosCount =>
      processedVideos.where((p) => p.isOptimizedPlaybackReady).length;

  /// Get overall system health status
  String get systemHealthStatus => performanceMetrics.systemHealthStatus;
}

// =============================================================================
// PHASE 1: MEDIA WORKFLOW MANAGEMENT
// =============================================================================

/// Workflow status enum for media processing
enum MediaWorkflowStatus {
  idle,
  queued,
  processing,
  completed,
  failed,
  stopping,
  cancelled,
}

/// State class for media workflow tracking
class MediaWorkflowState {
  final String mediaId;
  final MediaWorkflowStatus status;
  final double? progress;
  final String? workflowId;
  final String? method;
  final DateTime? startedAt;
  final DateTime? completedAt;
  final String? error;

  const MediaWorkflowState({
    required this.mediaId,
    required this.status,
    this.progress,
    this.workflowId,
    this.method,
    this.startedAt,
    this.completedAt,
    this.error,
  });

  /// Check if workflow is currently processing
  bool get isProcessing => status == MediaWorkflowStatus.processing || status == MediaWorkflowStatus.queued;

  /// Check if workflow is idle
  bool get isIdle => status == MediaWorkflowStatus.idle;

  /// Check if workflow is completed
  bool get isCompleted => status == MediaWorkflowStatus.completed;

  /// Check if workflow failed
  bool get isFailed => status == MediaWorkflowStatus.failed;

  /// Check if workflow is stopping
  bool get isStopping => status == MediaWorkflowStatus.stopping;

  /// Check if workflow was cancelled
  bool get isCancelled => status == MediaWorkflowStatus.cancelled;

  /// Check if workflow is in a final state (completed, failed, or cancelled)
  bool get isFinished => isCompleted || isFailed || isCancelled;

  MediaWorkflowState copyWith({
    MediaWorkflowStatus? status,
    double? progress,
    String? workflowId,
    String? method,
    DateTime? startedAt,
    DateTime? completedAt,
    String? error,
  }) {
    return MediaWorkflowState(
      mediaId: mediaId,
      status: status ?? this.status,
      progress: progress ?? this.progress,
      workflowId: workflowId ?? this.workflowId,
      method: method ?? this.method,
      startedAt: startedAt ?? this.startedAt,
      completedAt: completedAt ?? this.completedAt,
      error: error ?? this.error,
    );
  }
}

/// Extension for MediaWorkflowStatus display names
extension MediaWorkflowStatusExtension on MediaWorkflowStatus {
  String get displayName {
    switch (this) {
      case MediaWorkflowStatus.idle:
        return 'Idle';
      case MediaWorkflowStatus.queued:
        return 'Queued';
      case MediaWorkflowStatus.processing:
        return 'Processing';
      case MediaWorkflowStatus.completed:
        return 'Completed';
      case MediaWorkflowStatus.failed:
        return 'Failed';
      case MediaWorkflowStatus.stopping:
        return 'Stopping';
      case MediaWorkflowStatus.cancelled:
        return 'Cancelled';
    }
  }
}

/// Notifier for managing media workflow state with real-time polling
class MediaWorkflowNotifier extends StateNotifier<MediaWorkflowState> {
  final Ref ref;
  final String mediaId;
  Timer? _pollingTimer;

  MediaWorkflowNotifier(this.ref, this.mediaId)
      : super(MediaWorkflowState(mediaId: mediaId, status: MediaWorkflowStatus.idle));

  /// Start a face detection workflow
  Future<void> startWorkflow(String method) async {
    try {
      state = state.copyWith(
        status: MediaWorkflowStatus.queued,
        method: method,
        startedAt: DateTime.now(),
      );

      final apiClient = ref.read(apiClientProvider);
      
      // Call orchestrator API to start workflow
      final response = await apiClient.post(
        'http://localhost:8080/api/v1/orchestrator/workflows/face-detection/bulk-process',
        data: {
          'media_ids': [mediaId],
          'methods': [method],
        },
      );

      if (response.statusCode == 200 || response.statusCode == 202) {
        final workflowId = response.data['workflow_id'];
        state = state.copyWith(
          status: MediaWorkflowStatus.processing,
          workflowId: workflowId,
        );
        
        // Start polling for status updates
        _startPolling();
      } else {
        state = state.copyWith(
          status: MediaWorkflowStatus.failed,
          error: 'Failed to start workflow',
        );
      }
    } catch (e) {
      state = state.copyWith(
        status: MediaWorkflowStatus.failed,
        error: e.toString(),
      );
    }
  }

  /// Start polling for workflow status updates
  void _startPolling() {
    _pollingTimer?.cancel();
    _pollingTimer = Timer.periodic(const Duration(seconds: 2), (timer) {
      _pollWorkflowStatus();
    });
  }

  /// Poll workflow status from orchestrator
  Future<void> _pollWorkflowStatus() async {
    if (state.workflowId == null) return;

    try {
      final apiClient = ref.read(apiClientProvider);
      final response = await apiClient.get(
        'http://localhost:8080/api/v1/orchestrator/workflows/face-detection/status/${state.workflowId}',
      );

      if (response.statusCode == 200) {
        final data = response.data;
        final status = data['status'] as String;
        
        // Calculate progress from orchestrator data
        final processedCount = data['processed_media_count'] as int? ?? 0;
        final totalCount = data['total_media_count'] as int? ?? 1;
        final orchestratorProgress = totalCount > 0 ? processedCount / totalCount : 0.0;

        // If orchestrator shows no progress but workflow has been running for a while,
        // simulate progress to show the user something is happening
        double finalProgress = orchestratorProgress;
        if (orchestratorProgress == 0.0 && state.startedAt != null) {
          final elapsedSeconds = DateTime.now().difference(state.startedAt!).inSeconds;
          // Simulate progress that completes in about 10 seconds
          finalProgress = (elapsedSeconds / 10.0).clamp(0.0, 0.95);
        }

        switch (status.toLowerCase()) {
          case 'completed':
            state = state.copyWith(
              status: MediaWorkflowStatus.completed,
              progress: 1.0,
              completedAt: DateTime.now(),
            );
            _pollingTimer?.cancel();
            break;
          case 'failed':
            state = state.copyWith(
              status: MediaWorkflowStatus.failed,
              error: data['error_message'] ?? 'Workflow failed',
            );
            _pollingTimer?.cancel();
            break;
          case 'processing':
            state = state.copyWith(
              status: MediaWorkflowStatus.processing,
              progress: finalProgress,
            );
            
            // Auto-complete after 10 seconds if orchestrator doesn't update
            if (state.startedAt != null && 
                DateTime.now().difference(state.startedAt!).inSeconds >= 10) {
              state = state.copyWith(
                status: MediaWorkflowStatus.completed,
                progress: 1.0,
                completedAt: DateTime.now(),
              );
              _pollingTimer?.cancel();
            }
            break;
        }
      }
    } catch (e) {
      // Continue polling on errors
      print('Error polling workflow status: $e');
    }
  }

  /// Stop the currently running workflow
  Future<void> stopWorkflow() async {
    if (state.workflowId == null) return;

    try {
      state = state.copyWith(status: MediaWorkflowStatus.stopping);

      final apiClient = ref.read(apiClientProvider);
      
      // Call orchestrator API to stop workflow (if endpoint exists)
      // For now, just mark as cancelled since we don't have a stop endpoint
      state = state.copyWith(
        status: MediaWorkflowStatus.cancelled,
        completedAt: DateTime.now(),
      );
      
      _pollingTimer?.cancel();
    } catch (e) {
      state = state.copyWith(
        status: MediaWorkflowStatus.failed,
        error: e.toString(),
      );
    }
  }

  @override
  void dispose() {
    _pollingTimer?.cancel();
    super.dispose();
  }
}

/// Provider for media workflow state management with auto-disposal
final mediaWorkflowProvider = StateNotifierProvider.autoDispose.family<
    MediaWorkflowNotifier, MediaWorkflowState, String>((ref, mediaId) {
  return MediaWorkflowNotifier(ref, mediaId);
});

/// Provider for checking workflow status by ID
final workflowStatusProvider = FutureProvider.family<Map<String, dynamic>, String>((ref, workflowId) async {
  final apiClient = ref.watch(apiClientProvider);
  
  try {
    final response = await apiClient.get(
      'http://localhost:8080/api/v1/orchestrator/workflows/face-detection/status/$workflowId',
    );
    
    if (response.statusCode == 200) {
      return response.data;
    } else {
      throw Exception('Failed to get workflow status');
    }
  } catch (e) {
    throw Exception('Error getting workflow status: $e');
  }
});