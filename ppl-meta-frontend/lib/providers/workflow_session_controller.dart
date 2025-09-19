import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../services/workflow_api_client.dart';
import '../models/face_detection_models.dart';
import 'workflow_providers.dart';

// =============================================================================
// WORKFLOW SESSION CONTROLLER
// =============================================================================
// 
// This provider manages comprehensive session control operations for
// Workflows 4 & 5, providing stateful session management with UI integration.
//
// Key Features:
// • Session lifecycle management (create, start, stop, reset)
// • Real-time session monitoring and status updates
// • Processing control for Workflow 5 optimization
// • Error handling and retry logic
// • UI state management for session controls
//
// =============================================================================

/// Session control state for UI management
enum SessionControlState {
  idle,
  creating,
  starting,
  stopping,
  deleting,
  processing,
  error,
}

/// Processing control state for Workflow 5
enum ProcessingControlState {
  idle,
  analyzing,
  optimizing,
  completing,
  error,
}

/// Combined state for session controls
class WorkflowSessionState {
  final SessionControlState sessionState;
  final ProcessingControlState processingState;
  final String? activeSessionId;
  final String? currentMediaId;
  final double? processingProgress;
  final String? errorMessage;
  final DateTime? lastUpdated;

  const WorkflowSessionState({
    this.sessionState = SessionControlState.idle,
    this.processingState = ProcessingControlState.idle,
    this.activeSessionId,
    this.currentMediaId,
    this.processingProgress,
    this.errorMessage,
    this.lastUpdated,
  });

  WorkflowSessionState copyWith({
    SessionControlState? sessionState,
    ProcessingControlState? processingState,
    String? activeSessionId,
    String? currentMediaId,
    double? processingProgress,
    String? errorMessage,
    DateTime? lastUpdated,
  }) {
    return WorkflowSessionState(
      sessionState: sessionState ?? this.sessionState,
      processingState: processingState ?? this.processingState,
      activeSessionId: activeSessionId ?? this.activeSessionId,
      currentMediaId: currentMediaId ?? this.currentMediaId,
      processingProgress: processingProgress ?? this.processingProgress,
      errorMessage: errorMessage ?? this.errorMessage,
      lastUpdated: lastUpdated ?? this.lastUpdated,
    );
  }

  bool get isIdle => sessionState == SessionControlState.idle && 
                     processingState == ProcessingControlState.idle;
  
  bool get hasActiveSession => activeSessionId != null;
  
  bool get isProcessing => processingState != ProcessingControlState.idle;
  
  bool get hasError => sessionState == SessionControlState.error ||
                       processingState == ProcessingControlState.error;
}

/// Session creation parameters
class SessionCreationParams {
  final String mediaUuid;
  final double? confidenceThreshold;
  final List<String>? detectionMethods;
  final String? priority;
  final bool enableProgressUpdates;

  const SessionCreationParams({
    required this.mediaUuid,
    this.confidenceThreshold,
    this.detectionMethods,
    this.priority,
    this.enableProgressUpdates = true,
  });
}

/// Processing trigger parameters for Workflow 5
class ProcessingTriggerParams {
  final String mediaUuid;
  final double? confidenceThreshold;
  final List<String>? detectionMethods;
  final bool forceReprocess;

  const ProcessingTriggerParams({
    required this.mediaUuid,
    this.confidenceThreshold,
    this.detectionMethods,
    this.forceReprocess = false,
  });
}

// =============================================================================
// SESSION CONTROLLER NOTIFIER
// =============================================================================

class WorkflowSessionController extends StateNotifier<WorkflowSessionState> {
  final WorkflowApiClient _apiClient;
  Timer? _progressTimer;
  Timer? _statusTimer;

  WorkflowSessionController(this._apiClient) : super(const WorkflowSessionState());

  // ---------------------------------------------------------------------------
  // WORKFLOW 4 - SESSION MANAGEMENT OPERATIONS
  // ---------------------------------------------------------------------------

  /// Create a new face detection session
  Future<FaceDetectionSession?> createSession(SessionCreationParams params) async {
    if (state.sessionState != SessionControlState.idle) {
      throw Exception('Cannot create session: Another operation is in progress');
    }

    state = state.copyWith(
      sessionState: SessionControlState.creating,
      currentMediaId: params.mediaUuid,
      errorMessage: null,
      lastUpdated: DateTime.now(),
    );

    try {
      final response = await _apiClient.createFaceDetectionSession(
        mediaUuid: params.mediaUuid,
        confidenceThreshold: params.confidenceThreshold,
        detectionMethods: params.detectionMethods,
        priority: params.priority,
        enableProgressUpdates: params.enableProgressUpdates,
      );

      if (response.success && response.data != null) {
        final session = response.data!;
        
        state = state.copyWith(
          sessionState: SessionControlState.idle,
          activeSessionId: session.sessionUuid,
          lastUpdated: DateTime.now(),
        );

        // Start monitoring session if it's active
        if (session.isActive) {
          _startSessionMonitoring(session.sessionUuid);
        }

        return session;
      } else {
        state = state.copyWith(
          sessionState: SessionControlState.error,
          errorMessage: response.error ?? 'Unknown error creating session',
          lastUpdated: DateTime.now(),
        );
        return null;
      }
    } catch (e) {
      state = state.copyWith(
        sessionState: SessionControlState.error,
        errorMessage: 'Failed to create session: $e',
        lastUpdated: DateTime.now(),
      );
      return null;
    }
  }

  /// Start an existing session
  Future<bool> startSession(String sessionUuid) async {
    if (state.sessionState != SessionControlState.idle) {
      throw Exception('Cannot start session: Another operation is in progress');
    }

    state = state.copyWith(
      sessionState: SessionControlState.starting,
      activeSessionId: sessionUuid,
      errorMessage: null,
      lastUpdated: DateTime.now(),
    );

    try {
      final response = await _apiClient.startSession(sessionUuid);

      if (response.success) {
        state = state.copyWith(
          sessionState: SessionControlState.idle,
          lastUpdated: DateTime.now(),
        );

        // Start monitoring the active session
        _startSessionMonitoring(sessionUuid);
        return true;
      } else {
        state = state.copyWith(
          sessionState: SessionControlState.error,
          errorMessage: response.error ?? 'Unknown error starting session',
          lastUpdated: DateTime.now(),
        );
        return false;
      }
    } catch (e) {
      state = state.copyWith(
        sessionState: SessionControlState.error,
        errorMessage: 'Failed to start session: $e',
        lastUpdated: DateTime.now(),
      );
      return false;
    }
  }

  /// Stop an active session
  Future<bool> stopSession(String sessionUuid) async {
    if (state.sessionState != SessionControlState.idle) {
      throw Exception('Cannot stop session: Another operation is in progress');
    }

    state = state.copyWith(
      sessionState: SessionControlState.stopping,
      errorMessage: null,
      lastUpdated: DateTime.now(),
    );

    try {
      final response = await _apiClient.stopSession(sessionUuid);

      if (response.success) {
        state = state.copyWith(
          sessionState: SessionControlState.idle,
          activeSessionId: null,
          lastUpdated: DateTime.now(),
        );

        // Stop monitoring
        _stopSessionMonitoring();
        return true;
      } else {
        state = state.copyWith(
          sessionState: SessionControlState.error,
          errorMessage: response.error ?? 'Unknown error stopping session',
          lastUpdated: DateTime.now(),
        );
        return false;
      }
    } catch (e) {
      state = state.copyWith(
        sessionState: SessionControlState.error,
        errorMessage: 'Failed to stop session: $e',
        lastUpdated: DateTime.now(),
      );
      return false;
    }
  }

  /// Reset session state (cleanup after completion or error)
  Future<bool> resetSession(String sessionUuid) async {
    if (state.sessionState != SessionControlState.idle) {
      throw Exception('Cannot reset session: Another operation is in progress');
    }

    state = state.copyWith(
      sessionState: SessionControlState.deleting,
      errorMessage: null,
      lastUpdated: DateTime.now(),
    );

    try {
      // First stop the session if it's active
      if (state.activeSessionId == sessionUuid) {
        await _apiClient.stopSession(sessionUuid);
      }

      // Then delete the session
      final response = await _apiClient.deleteSession(sessionUuid);

      if (response.success) {
        state = state.copyWith(
          sessionState: SessionControlState.idle,
          activeSessionId: null,
          processingProgress: null,
          lastUpdated: DateTime.now(),
        );

        _stopSessionMonitoring();
        return true;
      } else {
        state = state.copyWith(
          sessionState: SessionControlState.error,
          errorMessage: response.error ?? 'Unknown error resetting session',
          lastUpdated: DateTime.now(),
        );
        return false;
      }
    } catch (e) {
      state = state.copyWith(
        sessionState: SessionControlState.error,
        errorMessage: 'Failed to reset session: $e',
        lastUpdated: DateTime.now(),
      );
      return false;
    }
  }

  // ---------------------------------------------------------------------------
  // WORKFLOW 5 - PROCESSING CONTROL OPERATIONS
  // ---------------------------------------------------------------------------

  /// Trigger video analysis for Workflow 5 optimization
  Future<bool> triggerVideoAnalysis(ProcessingTriggerParams params) async {
    if (state.processingState != ProcessingControlState.idle) {
      throw Exception('Cannot trigger analysis: Processing operation in progress');
    }

    state = state.copyWith(
      processingState: ProcessingControlState.analyzing,
      currentMediaId: params.mediaUuid,
      errorMessage: null,
      lastUpdated: DateTime.now(),
    );

    try {
      final response = await _apiClient.triggerVideoAnalysis(
        mediaUuid: params.mediaUuid,
        confidenceThreshold: params.confidenceThreshold,
        detectionMethods: params.detectionMethods,
        forceReprocess: params.forceReprocess,
      );

      if (response.success) {
        state = state.copyWith(
          processingState: ProcessingControlState.optimizing,
          lastUpdated: DateTime.now(),
        );

        // Start monitoring processing progress
        _startProcessingMonitoring(params.mediaUuid);
        return true;
      } else {
        state = state.copyWith(
          processingState: ProcessingControlState.error,
          errorMessage: response.error ?? 'Unknown error triggering analysis',
          lastUpdated: DateTime.now(),
        );
        return false;
      }
    } catch (e) {
      state = state.copyWith(
        processingState: ProcessingControlState.error,
        errorMessage: 'Failed to trigger analysis: $e',
        lastUpdated: DateTime.now(),
      );
      return false;
    }
  }

  /// Complete processing and mark video as optimized
  Future<bool> completeProcessing(String mediaUuid, String sessionUuid) async {
    if (state.processingState != ProcessingControlState.optimizing) {
      throw Exception('Cannot complete processing: No active processing operation');
    }

    state = state.copyWith(
      processingState: ProcessingControlState.completing,
      errorMessage: null,
      lastUpdated: DateTime.now(),
    );

    try {
      final response = await _apiClient.markVideoAsProcessed(
        mediaUuid: mediaUuid,
        sessionUuid: sessionUuid,
      );

      if (response.success) {
        state = state.copyWith(
          processingState: ProcessingControlState.idle,
          processingProgress: 100.0,
          lastUpdated: DateTime.now(),
        );

        _stopProcessingMonitoring();
        return true;
      } else {
        state = state.copyWith(
          processingState: ProcessingControlState.error,
          errorMessage: response.error ?? 'Unknown error completing processing',
          lastUpdated: DateTime.now(),
        );
        return false;
      }
    } catch (e) {
      state = state.copyWith(
        processingState: ProcessingControlState.error,
        errorMessage: 'Failed to complete processing: $e',
        lastUpdated: DateTime.now(),
      );
      return false;
    }
  }

  /// Check processing status for a media item
  Future<ProcessingStatus?> getProcessingStatus(String mediaUuid) async {
    try {
      final response = await _apiClient.getProcessingStatus(mediaUuid);
      
      if (response.success && response.data != null) {
        return response.data!;
      } else {
        return null;
      }
    } catch (e) {
      debugPrint('Failed to get processing status: $e');
      return null;
    }
  }

  // ---------------------------------------------------------------------------
  // MONITORING & REAL-TIME UPDATES
  // ---------------------------------------------------------------------------

  /// Start monitoring session progress
  void _startSessionMonitoring(String sessionUuid) {
    _stopSessionMonitoring(); // Stop any existing monitoring

    _statusTimer = Timer.periodic(const Duration(seconds: 2), (timer) async {
      try {
        final response = await _apiClient.getSessionStatus(sessionUuid);
        
        if (response.success && response.data != null) {
          final session = response.data!;
          
          // Update state based on session status
          if (!session.isActive) {
            // Session completed or stopped
            state = state.copyWith(
              activeSessionId: null,
              processingProgress: 100.0,
              lastUpdated: DateTime.now(),
            );
            _stopSessionMonitoring();
          } else {
            // Update progress if available
            final progress = _calculateSessionProgress(session);
            state = state.copyWith(
              processingProgress: progress,
              lastUpdated: DateTime.now(),
            );
          }
        }
      } catch (e) {
        debugPrint('Session monitoring error: $e');
      }
    });
  }

  /// Start monitoring processing progress
  void _startProcessingMonitoring(String mediaUuid) {
    _stopProcessingMonitoring(); // Stop any existing monitoring

    _progressTimer = Timer.periodic(const Duration(seconds: 3), (timer) async {
      try {
        final status = await getProcessingStatus(mediaUuid);
        
        if (status != null) {
          if (status.isOptimizedPlaybackReady) {
            // Processing completed
            state = state.copyWith(
              processingState: ProcessingControlState.idle,
              processingProgress: 100.0,
              lastUpdated: DateTime.now(),
            );
            _stopProcessingMonitoring();
          } else {
            // Update progress based on processing status
            final progress = _calculateProcessingProgress(status);
            state = state.copyWith(
              processingProgress: progress,
              lastUpdated: DateTime.now(),
            );
          }
        }
      } catch (e) {
        debugPrint('Processing monitoring error: $e');
      }
    });
  }

  /// Stop session monitoring
  void _stopSessionMonitoring() {
    _statusTimer?.cancel();
    _statusTimer = null;
  }

  /// Stop processing monitoring
  void _stopProcessingMonitoring() {
    _progressTimer?.cancel();
    _progressTimer = null;
  }

  /// Calculate session progress percentage
  double? _calculateSessionProgress(FaceDetectionSession session) {
    if (session.totalFramesProcessed != null && session.estimatedTotalFrames != null) {
      final processed = session.totalFramesProcessed!;
      final total = session.estimatedTotalFrames!;
      
      if (total > 0) {
        return (processed / total * 100.0).clamp(0.0, 100.0);
      }
    }
    return null;
  }

  /// Calculate processing progress percentage
  double? _calculateProcessingProgress(ProcessingStatus status) {
    if (status.totalFramesProcessed != null && status.totalFramesProcessed! > 0) {
      final processed = status.totalFramesProcessed!;
      final total = status.totalFramesProcessed! + 100; // Estimate total
      
      if (total > 0) {
        return (processed / total * 100.0).clamp(0.0, 100.0);
      }
    }
    return null;
  }

  // ---------------------------------------------------------------------------
  // UTILITY METHODS
  // ---------------------------------------------------------------------------

  /// Clear error state
  void clearError() {
    state = state.copyWith(
      sessionState: SessionControlState.idle,
      processingState: ProcessingControlState.idle,
      errorMessage: null,
      lastUpdated: DateTime.now(),
    );
  }

  /// Reset all state
  void reset() {
    _stopSessionMonitoring();
    _stopProcessingMonitoring();
    
    state = const WorkflowSessionState();
  }

  @override
  void dispose() {
    _stopSessionMonitoring();
    _stopProcessingMonitoring();
    super.dispose();
  }
}

// =============================================================================
// PROVIDER DEFINITIONS
// =============================================================================

/// Provider for workflow session controller
final workflowSessionControllerProvider = StateNotifierProvider<WorkflowSessionController, WorkflowSessionState>((ref) {
  final apiClient = ref.watch(workflowApiClientProvider);
  return WorkflowSessionController(apiClient);
});

/// Provider for session controller scoped to a specific media item
final mediaSessionControllerProvider = StateNotifierProvider.family<WorkflowSessionController, WorkflowSessionState, String>((ref, mediaUuid) {
  final apiClient = ref.watch(workflowApiClientProvider);
  final controller = WorkflowSessionController(apiClient);
  
  return controller;
});

/// Provider for quick session actions
final sessionActionsProvider = Provider<SessionActions>((ref) {
  final controller = ref.read(workflowSessionControllerProvider.notifier);
  return SessionActions(controller);
});

/// Provider for quick processing actions
final processingActionsProvider = Provider<ProcessingActions>((ref) {
  final controller = ref.read(workflowSessionControllerProvider.notifier);
  return ProcessingActions(controller);
});

// =============================================================================
// ACTION HELPER CLASSES
// =============================================================================

/// Helper class for session actions
class SessionActions {
  final WorkflowSessionController _controller;

  SessionActions(this._controller);

  /// Quick session creation with default parameters
  Future<FaceDetectionSession?> createQuickSession(String mediaUuid) {
    return _controller.createSession(SessionCreationParams(
      mediaUuid: mediaUuid,
      confidenceThreshold: 0.7,
      enableProgressUpdates: true,
    ));
  }

  /// Stop current active session
  Future<bool> stopCurrentSession() {
    return Future.value(false); // Will be implemented when we have access to current state
  }

  /// Reset current session
  Future<bool> resetCurrentSession() {
    return Future.value(false); // Will be implemented when we have access to current state
  }
}

/// Helper class for processing actions
class ProcessingActions {
  final WorkflowSessionController _controller;

  ProcessingActions(this._controller);

  /// Quick video optimization trigger
  Future<bool> optimizeVideo(String mediaUuid) {
    return _controller.triggerVideoAnalysis(ProcessingTriggerParams(
      mediaUuid: mediaUuid,
      confidenceThreshold: 0.7,
    ));
  }

  /// Reprocess video with higher quality
  Future<bool> reprocessVideo(String mediaUuid) {
    return _controller.triggerVideoAnalysis(ProcessingTriggerParams(
      mediaUuid: mediaUuid,
      confidenceThreshold: 0.8,
      forceReprocess: true,
    ));
  }
}