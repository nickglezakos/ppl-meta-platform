import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../models/face_detection_models.dart'; // Use face detection models instead of api_models
import '../../providers/workflow_session_controller.dart';
import '../../providers/workflow_providers.dart';

// =============================================================================
// WORKFLOW SESSION CONTROLS WIDGET
// =============================================================================
// 
// This widget provides comprehensive session control interface for 
// Workflows 4 & 5, including:
// • Session lifecycle management (create, start, stop, reset)
// • Processing controls for Workflow 5 optimization
// • Real-time status indicators and progress tracking
// • Error handling and user feedback
//
// =============================================================================

class WorkflowSessionControlsWidget extends ConsumerStatefulWidget {
  final String mediaUuid;
  final bool showExpanded;
  final VoidCallback? onToggleExpanded;

  const WorkflowSessionControlsWidget({
    super.key,
    required this.mediaUuid,
    this.showExpanded = false,
    this.onToggleExpanded,
  });

  @override
  ConsumerState<WorkflowSessionControlsWidget> createState() => 
      _WorkflowSessionControlsWidgetState();
}

class _WorkflowSessionControlsWidgetState 
    extends ConsumerState<WorkflowSessionControlsWidget> {
  
  @override
  Widget build(BuildContext context) {
    final sessionState = ref.watch(workflowSessionControllerProvider);
    final sessionController = ref.read(workflowSessionControllerProvider.notifier);
    
    // Get processing status and other workflow data
    final processingStatusAsync = ref.watch(processingStatusProvider(widget.mediaUuid));
    final mediaSessionsAsync = ref.watch(mediaSessionsProvider(widget.mediaUuid));
    final playbackModeAsync = ref.watch(optimalPlaybackModeProvider(widget.mediaUuid));

    return AnimatedContainer(
      duration: const Duration(milliseconds: 300),
      height: widget.showExpanded ? null : 60,
      child: Container(
        color: Colors.grey[850],
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Header bar with quick controls
            _buildHeaderBar(sessionState),
            
            // Expanded controls (only visible when expanded)
            if (widget.showExpanded) ...[
              const SizedBox(height: 16),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Session controls section
                    _buildSessionControlsSection(
                      sessionState,
                      sessionController,
                      mediaSessionsAsync,
                    ),
                    
                    const SizedBox(height: 16),
                    
                    // Processing controls section
                    _buildProcessingControlsSection(
                      sessionState,
                      sessionController,
                      processingStatusAsync,
                      playbackModeAsync,
                    ),
                    
                    const SizedBox(height: 16),
                  ],
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  /// Build the header bar with quick controls
  Widget _buildHeaderBar(WorkflowSessionState sessionState) {
    return Container(
      height: 60,
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Row(
        children: [
          // Session status indicator
          _buildSessionStatusIndicator(sessionState),
          
          const SizedBox(width: 12),
          
          // Processing status indicator
          _buildProcessingStatusIndicator(sessionState),
          
          const Spacer(),
          
          // Quick action buttons
          _buildQuickActionButtons(sessionState),
          
          const SizedBox(width: 8),
          
          // Expand/collapse button
          IconButton(
            icon: Icon(
              widget.showExpanded ? Icons.expand_less : Icons.expand_more,
              color: Colors.white70,
            ),
            onPressed: widget.onToggleExpanded,
            tooltip: widget.showExpanded ? 'Collapse Controls' : 'Expand Controls',
          ),
        ],
      ),
    );
  }

  /// Build session status indicator
  Widget _buildSessionStatusIndicator(WorkflowSessionState sessionState) {
    Color color;
    IconData icon;
    String text;

    switch (sessionState.sessionState) {
      case SessionControlState.creating:
        color = Colors.blue[600]!;
        icon = Icons.add_circle_outline;
        text = 'Creating...';
        break;
      case SessionControlState.starting:
        color = Colors.green[600]!;
        icon = Icons.play_circle_outline;
        text = 'Starting...';
        break;
      case SessionControlState.stopping:
        color = Colors.orange[600]!;
        icon = Icons.stop_circle;
        text = 'Stopping...';
        break;
      case SessionControlState.error:
        color = Colors.red[600]!;
        icon = Icons.error_outline;
        text = 'Error';
        break;
      default:
        if (sessionState.hasActiveSession) {
          color = Colors.green[600]!;
          icon = Icons.radio_button_checked;
          text = 'Active';
        } else {
          color = Colors.grey[600]!;
          icon = Icons.radio_button_unchecked;
          text = 'Ready';
        }
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: color,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 16, color: Colors.white),
          const SizedBox(width: 6),
          Text(
            text,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 12,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }

  /// Build processing status indicator
  Widget _buildProcessingStatusIndicator(WorkflowSessionState sessionState) {
    Color color;
    IconData icon;
    String text;

    switch (sessionState.processingState) {
      case ProcessingControlState.analyzing:
        color = Colors.purple[600]!;
        icon = Icons.analytics_outlined;
        text = 'Analyzing...';
        break;
      case ProcessingControlState.optimizing:
        color = Colors.blue[600]!;
        icon = Icons.speed_outlined;
        text = 'Optimizing...';
        break;
      case ProcessingControlState.completing:
        color = Colors.green[600]!;
        icon = Icons.check_circle_outline;
        text = 'Completing...';
        break;
      case ProcessingControlState.error:
        color = Colors.red[600]!;
        icon = Icons.error_outline;
        text = 'Error';
        break;
      default:
        color = Colors.grey[600]!;
        icon = Icons.offline_bolt_outlined;
        text = 'Ready';
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: color,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 16, color: Colors.white),
          const SizedBox(width: 6),
          Text(
            text,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 12,
              fontWeight: FontWeight.w600,
            ),
          ),
          
          // Progress indicator for processing
          if (sessionState.processingProgress != null) ...[
            const SizedBox(width: 8),
            SizedBox(
              width: 20,
              height: 20,
              child: CircularProgressIndicator(
                value: sessionState.processingProgress! / 100.0,
                strokeWidth: 2,
                backgroundColor: Colors.white30,
                valueColor: const AlwaysStoppedAnimation<Color>(Colors.white),
              ),
            ),
          ],
        ],
      ),
    );
  }

  /// Build quick action buttons
  Widget _buildQuickActionButtons(WorkflowSessionState sessionState) {
    final sessionActions = ref.read(sessionActionsProvider);
    final processingActions = ref.read(processingActionsProvider);

    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        // Quick session create/stop button
        if (!sessionState.hasActiveSession && sessionState.sessionState == SessionControlState.idle)
          _buildQuickActionButton(
            icon: Icons.play_circle,
            label: 'Start',
            color: Colors.green[600]!,
            onPressed: () => _createQuickSession(sessionActions),
          )
        else if (sessionState.hasActiveSession && sessionState.sessionState == SessionControlState.idle)
          _buildQuickActionButton(
            icon: Icons.stop_circle,
            label: 'Stop',
            color: Colors.orange[600]!,
            onPressed: () => _stopCurrentSession(),
          ),

        const SizedBox(width: 8),

        // Quick processing button
        if (!sessionState.isProcessing && sessionState.processingState == ProcessingControlState.idle)
          _buildQuickActionButton(
            icon: Icons.speed,
            label: 'Optimize',
            color: Colors.blue[600]!,
            onPressed: () => _optimizeVideo(processingActions),
          ),
      ],
    );
  }

  /// Build a quick action button
  Widget _buildQuickActionButton({
    required IconData icon,
    required String label,
    required Color color,
    required VoidCallback onPressed,
  }) {
    return ElevatedButton.icon(
      onPressed: onPressed,
      icon: Icon(icon, size: 16),
      label: Text(label),
      style: ElevatedButton.styleFrom(
        backgroundColor: color,
        foregroundColor: Colors.white,
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        minimumSize: const Size(80, 32),
        textStyle: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600),
      ),
    );
  }

  /// Build session controls section
  Widget _buildSessionControlsSection(
    WorkflowSessionState sessionState,
    WorkflowSessionController sessionController,
    AsyncValue<List<FaceDetectionSession>> mediaSessionsAsync,
  ) {
    return Card(
      color: Colors.grey[800],
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.play_circle, color: Colors.blue[400], size: 20),
                const SizedBox(width: 8),
                Text(
                  'Workflow 4 - Session Management',
                  style: const TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.w600,
                    fontSize: 18,
                  ),
                ),
              ],
            ),
            
            const SizedBox(height: 12),
            
            // Session status and controls
            mediaSessionsAsync.when(
              data: (sessions) => _buildSessionControls(sessionState, sessionController, sessions),
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (error, stack) => _buildErrorDisplay('Failed to load sessions: $error'),
            ),
          ],
        ),
      ),
    );
  }

  /// Build session controls content
  Widget _buildSessionControls(
    WorkflowSessionState sessionState,
    WorkflowSessionController sessionController,
    List<FaceDetectionSession> sessions,
  ) {
    final activeSessions = sessions.where((s) => s.isActive).toList();
    final completedSessions = sessions.where((s) => s.isCompleted).toList();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Active sessions display
        if (activeSessions.isNotEmpty) ...[
          Text(
            'Active Sessions (${activeSessions.length})',
            style: const TextStyle(
              color: Colors.white,
              fontWeight: FontWeight.w600,
              fontSize: 14,
            ),
          ),
          const SizedBox(height: 8),
          ...activeSessions.map((session) => _buildSessionCard(session, true)),
          const SizedBox(height: 12),
        ],

        // Control buttons
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            ElevatedButton.icon(
              onPressed: sessionState.sessionState == SessionControlState.idle
                  ? () => _createDetailedSession(sessionController)
                  : null,
              icon: const Icon(Icons.add_circle, size: 18),
              label: const Text('Create Session'),
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.blue[600],
                foregroundColor: Colors.white,
              ),
            ),
            
            if (activeSessions.isNotEmpty)
              ElevatedButton.icon(
                onPressed: sessionState.sessionState == SessionControlState.idle
                    ? () => _stopAllSessions(sessionController, activeSessions)
                    : null,
                icon: const Icon(Icons.stop_circle, size: 18),
                label: const Text('Stop All'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.orange[600],
                  foregroundColor: Colors.white,
                ),
              ),
            
            TextButton.icon(
              onPressed: () => _showSessionHistory(completedSessions),
              icon: const Icon(Icons.history, size: 18),
              label: Text('History (${completedSessions.length})'),
              style: TextButton.styleFrom(
                foregroundColor: Colors.white70,
              ),
            ),
          ],
        ),

        // Error display
        if (sessionState.hasError && sessionState.errorMessage != null) ...[
          const SizedBox(height: 12),
          _buildErrorDisplay(sessionState.errorMessage!),
        ],
      ],
    );
  }

  /// Build processing controls section
  Widget _buildProcessingControlsSection(
    WorkflowSessionState sessionState,
    WorkflowSessionController sessionController,
    AsyncValue<ProcessingStatus?> processingStatusAsync,
    AsyncValue<PlaybackMode?> playbackModeAsync,
  ) {
    return Card(
      color: Colors.grey[800],
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.speed, color: Colors.green[400], size: 20),
                const SizedBox(width: 8),
                Text(
                  'Workflow 5 - Optimized Playback',
                  style: const TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.w600,
                    fontSize: 18,
                  ),
                ),
              ],
            ),
            
            const SizedBox(height: 12),
            
            // Processing status and controls
            processingStatusAsync.when(
              data: (processingStatus) => playbackModeAsync.when(
                data: (playbackMode) => _buildProcessingControls(
                  sessionState,
                  sessionController,
                  processingStatus,
                  playbackMode,
                ),
                loading: () => const Center(child: CircularProgressIndicator()),
                error: (error, stack) => _buildNoWorkflowDisplay('No workflow data available'),
              ),
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (error, stack) => _buildNoWorkflowDisplay('No workflow data available'),
            ),
          ],
        ),
      ),
    );
  }

  /// Build processing controls content
  Widget _buildProcessingControls(
    WorkflowSessionState sessionState,
    WorkflowSessionController sessionController,
    ProcessingStatus? processingStatus,
    PlaybackMode? playbackMode,
  ) {
    // Provide default values if workflow data is missing
    final effectiveProcessingStatus = processingStatus ?? ProcessingStatus(
      mediaUuid: 'unknown',
      status: 'not_started',
      faceDetectionProcessed: false,
      currentSession: null,
    );
    final effectivePlaybackMode = playbackMode ?? PlaybackMode.fromString('realtime_only');
    
    final isOptimized = effectiveProcessingStatus.isOptimizedPlaybackReady;
    final processingActions = ref.read(processingActionsProvider);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Status display
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: isOptimized ? Colors.green[700] : Colors.orange[700],
            borderRadius: BorderRadius.circular(8),
          ),
          child: Row(
            children: [
              Icon(
                isOptimized ? Icons.check_circle : Icons.hourglass_empty,
                color: Colors.white,
                size: 20,
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      isOptimized ? 'Optimized for Performance' : 'Ready for Optimization',
                      style: const TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      isOptimized
                          ? 'Video uses pre-processed face data (${playbackMode?.mode ?? 'realtime'} mode)'
                          : 'Process this video to enable 90% CPU reduction during playback',
                      style: const TextStyle(
                        color: Colors.white70,
                        fontSize: 12,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),

        const SizedBox(height: 12),

        // Control buttons
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            if (!isOptimized)
              ElevatedButton.icon(
                onPressed: sessionState.processingState == ProcessingControlState.idle
                    ? () => _optimizeVideo(processingActions)
                    : null,
                icon: const Icon(Icons.auto_awesome, size: 18),
                label: const Text('Optimize Video'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.green[600],
                  foregroundColor: Colors.white,
                ),
              )
            else ...[
              ElevatedButton.icon(
                onPressed: () => _viewOptimizedData(),
                icon: const Icon(Icons.visibility, size: 18),
                label: const Text('View Data'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.blue[600],
                  foregroundColor: Colors.white,
                ),
              ),
              
              ElevatedButton.icon(
                onPressed: sessionState.processingState == ProcessingControlState.idle
                    ? () => _reprocessVideo(processingActions)
                    : null,
                icon: const Icon(Icons.refresh, size: 18),
                label: const Text('Reprocess'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.orange[600],
                  foregroundColor: Colors.white,
                ),
              ),
            ],
          ],
        ),

        // Progress display
        if (sessionState.processingProgress != null) ...[
          const SizedBox(height: 12),
          _buildProgressDisplay(sessionState.processingProgress!),
        ],

        // Error display
        if (sessionState.hasError && sessionState.errorMessage != null) ...[
          const SizedBox(height: 12),
          _buildErrorDisplay(sessionState.errorMessage!),
        ],
      ],
    );
  }

  /// Build a session card display
  Widget _buildSessionCard(FaceDetectionSession session, bool isActive) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.grey[700],
        borderRadius: BorderRadius.circular(8),
        border: isActive 
            ? Border.all(color: Colors.green[400]!, width: 1)
            : null,
      ),
      child: Row(
        children: [
          Icon(
            isActive ? Icons.radio_button_checked : Icons.check_circle,
            size: 20,
            color: isActive ? Colors.green : Colors.blue,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Session ${session.sessionUuid.substring(0, 8)}...',
                  style: const TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.w500,
                  ),
                ),
                if (session.totalFramesProcessed != null) ...[
                  const SizedBox(height: 4),
                  Text(
                    'Frames: ${session.totalFramesProcessed} | Faces: ${session.totalFacesDetected ?? 0}',
                    style: const TextStyle(
                      color: Colors.white70,
                      fontSize: 12,
                    ),
                  ),
                ],
              ],
            ),
          ),
          Text(
            session.displayStatus,
            style: TextStyle(
              color: isActive ? Colors.green : Colors.blue,
              fontSize: 12,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }

  /// Build progress display
  Widget _buildProgressDisplay(double progress) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            const Text(
              'Processing Progress',
              style: TextStyle(color: Colors.white70, fontSize: 12),
            ),
            Text(
              '${progress.toStringAsFixed(1)}%',
              style: const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.w600),
            ),
          ],
        ),
        const SizedBox(height: 4),
        LinearProgressIndicator(
          value: progress / 100.0,
          backgroundColor: Colors.grey[600],
          valueColor: AlwaysStoppedAnimation<Color>(Colors.green[400]!),
        ),
      ],
    );
  }

  /// Build error display
  Widget _buildErrorDisplay(String errorMessage) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.red[900],
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.red[600]!),
      ),
      child: Row(
        children: [
          Icon(Icons.error_outline, color: Colors.red[300], size: 20),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              errorMessage,
              style: TextStyle(color: Colors.red[100], fontSize: 12),
            ),
          ),
          IconButton(
            icon: Icon(Icons.close, color: Colors.red[300], size: 16),
            onPressed: () {
              ref.read(workflowSessionControllerProvider.notifier).clearError();
            },
            constraints: const BoxConstraints(),
            padding: EdgeInsets.zero,
          ),
        ],
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // ACTION METHODS
  // ---------------------------------------------------------------------------

  Future<void> _createQuickSession(SessionActions sessionActions) async {
    try {
      await sessionActions.createQuickSession(widget.mediaUuid);
      _showSuccessMessage('Session created successfully');
    } catch (e) {
      _showErrorMessage('Failed to create session: $e');
    }
  }

  Future<void> _stopCurrentSession() async {
    try {
      final sessionActions = ref.read(sessionActionsProvider);
      await sessionActions.stopCurrentSession();
      _showSuccessMessage('Session stopped successfully');
    } catch (e) {
      _showErrorMessage('Failed to stop session: $e');
    }
  }

  Future<void> _optimizeVideo(ProcessingActions processingActions) async {
    try {
      await processingActions.optimizeVideo(widget.mediaUuid);
      _showSuccessMessage('Video optimization started');
    } catch (e) {
      _showErrorMessage('Failed to start optimization: $e');
    }
  }

  Future<void> _createDetailedSession(WorkflowSessionController sessionController) async {
    // Show session creation dialog
    _showInfoMessage('Detailed session creation coming soon');
  }

  Future<void> _stopAllSessions(WorkflowSessionController sessionController, List<FaceDetectionSession> activeSessions) async {
    // Stop all active sessions
    _showInfoMessage('Stopping all sessions...');
  }

  Future<void> _showSessionHistory(List<FaceDetectionSession> completedSessions) async {
    // Show session history dialog
    _showInfoMessage('Session history: ${completedSessions.length} completed sessions');
  }

  Future<void> _reprocessVideo(ProcessingActions processingActions) async {
    try {
      await processingActions.reprocessVideo(widget.mediaUuid);
      _showSuccessMessage('Video reprocessing started');
    } catch (e) {
      _showErrorMessage('Failed to start reprocessing: $e');
    }
  }

  void _viewOptimizedData() {
    _showInfoMessage('Viewing optimized data coming soon');
  }

  // ---------------------------------------------------------------------------
  // UI HELPER METHODS
  // ---------------------------------------------------------------------------

  void _showSuccessMessage(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: Colors.green[600],
        duration: const Duration(seconds: 3),
      ),
    );
  }

  void _showErrorMessage(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: Colors.red[600],
        duration: const Duration(seconds: 5),
      ),
    );
  }

  /// Build display for when no workflow data is available
  Widget _buildNoWorkflowDisplay(String message) {
    return Container(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          Icon(
            Icons.info_outline,
            color: Colors.grey[400],
            size: 32,
          ),
          const SizedBox(height: 8),
          Text(
            message,
            style: TextStyle(
              color: Colors.grey[400],
              fontSize: 14,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 8),
          Text(
            'This media item is not part of a workflow session.',
            style: TextStyle(
              color: Colors.grey[500],
              fontSize: 12,
            ),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }

  void _showInfoMessage(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: Colors.blue[600],
        duration: const Duration(seconds: 3),
      ),
    );
  }
}