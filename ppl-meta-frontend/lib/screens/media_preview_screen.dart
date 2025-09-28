import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:video_player/video_player.dart';
import '../core/theme/app_theme.dart';
import '../models/media_models.dart';
import '../models/face_detection_models.dart';
import '../widgets/smart_video_player_widget.dart';
import '../widgets/performance/performance_metrics_dialog.dart';
import '../core/api/api_client.dart';
import '../widgets/custom_app_bar.dart';
import '../providers/workflow_providers.dart';
import '../providers/face_memory_manager.dart';
import '../widgets/face_and_person_count_widget.dart';
import '../widgets/ppl_thread_test_widget.dart';
// Phase 6: Person Objects Integration
import '../providers/person_objects_provider.dart';
import '../widgets/person_objects_components.dart';
import 'person_objects_detail_screen.dart';


/// Enhanced Media Preview Screen with integrated Workflows 4 & 5 support
/// Features smart video player, comprehensive status display, and workflow controls
class EnhancedMediaPreviewScreen extends ConsumerStatefulWidget {
  final MediaItem mediaItem;

  const EnhancedMediaPreviewScreen({
    super.key,
    required this.mediaItem,
  });

  @override
  ConsumerState<EnhancedMediaPreviewScreen> createState() => _EnhancedMediaPreviewScreenState();
}

class _EnhancedMediaPreviewScreenState extends ConsumerState<EnhancedMediaPreviewScreen> {
  VideoPlayerController? _videoController;
  bool _showWorkflowControls = false;

  @override
  void initState() {
    super.initState();
    
    // Automatically load face data when media loads
    // Note: Person objects workflow is now auto-triggered by FaceAndPersonCountWidget
    WidgetsBinding.instance.addPostFrameCallback((_) {
      EnhancedAutoFaceLoader.loadFacesForMedia(ref, widget.mediaItem.uuid);
    });
  }

  @override
  void dispose() {
    // Clean up video controller
    _videoController?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: _buildEnhancedAppBar(context, ref),
      backgroundColor: Colors.black,
      body: Column(
        children: [
          // Enhanced performance status bar with overlay widgets
          _buildPerformanceStatusBar(ref),
          
          // Main media content
          Expanded(
            child: _buildMediaContent(context, ref),
          ),
          
          // Bottom control bar with workflow controls
          _buildBottomControlBar(ref),
        ],
      ),
    );
  }

  /// Build bottom control bar with workflow controls
  Widget _buildBottomControlBar(WidgetRef ref) {
    return Container(
      color: Colors.grey[850],
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Toggle button for expanded controls
          Row(
            children: [
              Icon(
                Icons.tune,
                color: Colors.white70,
                size: 16,
              ),
              const SizedBox(width: 8),
              const Text(
                'Workflow Controls',
                style: TextStyle(
                  color: Colors.white70,
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const Spacer(),
              IconButton(
                icon: Icon(
                  _showWorkflowControls ? Icons.expand_less : Icons.expand_more,
                  color: Colors.white70,
                ),
                onPressed: () {
                  setState(() {
                    _showWorkflowControls = !_showWorkflowControls;
                  });
                },
                tooltip: _showWorkflowControls ? 'Collapse' : 'Expand',
              ),
            ],
          ),
          
          // Expandable workflow controls
          if (_showWorkflowControls) ...[
            const SizedBox(height: 8),
            _buildEnhancedWorkflowControls(ref),
          ],
        ],
      ),
    );
  }

  Widget _buildMediaContent(BuildContext context, WidgetRef ref) {
    switch (widget.mediaItem.mediaType) {
      case MediaType.image:
        return _buildImagePreview(context, ref);
      case MediaType.video:
        return _buildVideoPreview(context, ref);
      default:
        return _buildUnsupportedMediaPreview(context);
    }
  }

  Widget _buildImagePreview(BuildContext context, WidgetRef ref) {
    final imageUrl = widget.mediaItem.url ?? widget.mediaItem.thumbnailUrl;
    if (imageUrl == null) {
      return _buildErrorPreview(context, 'No image URL available');
    }

    return Center(
      child: InteractiveViewer(
        panEnabled: true,
        boundaryMargin: const EdgeInsets.all(20),
        minScale: 0.5,
        maxScale: 3.0,
        child: Image.network(
          imageUrl.startsWith('/') ? 'http://localhost:8080$imageUrl' : imageUrl,
          fit: BoxFit.contain,
          width: double.infinity,
          height: double.infinity,
          headers: {
            if (ref.read(apiClientProvider).authToken != null)
              'Authorization': 'Bearer ${ref.read(apiClientProvider).authToken}',
          },
          errorBuilder: (context, error, stackTrace) {
            return _buildErrorPreview(context, 'Failed to load image');
          },
          loadingBuilder: (context, child, loadingProgress) {
            if (loadingProgress == null) return child;
            return Center(
              child: CircularProgressIndicator(
                value: loadingProgress.expectedTotalBytes != null
                    ? loadingProgress.cumulativeBytesLoaded / loadingProgress.expectedTotalBytes!
                    : null,
                valueColor: const AlwaysStoppedAnimation<Color>(Colors.white),
              ),
            );
          },
        ),
      ),
    );
  }

  Widget _buildVideoPreview(BuildContext context, WidgetRef ref) {
    final apiClient = ref.read(apiClientProvider);
    
    return Center(
      child: Container(
        constraints: BoxConstraints(
          maxWidth: MediaQuery.of(context).size.width,
          maxHeight: MediaQuery.of(context).size.height - kToolbarHeight,
        ),
        child: SmartVideoPlayerWidget(
          mediaItem: widget.mediaItem,
          headers: {
            if (apiClient.authToken != null)
              'Authorization': 'Bearer ${apiClient.authToken}',
          },
          collectionId: null, // TODO: Pass collection ID from route parameters
          onControllerReady: (controller) {
            debugPrint('🎬 Smart video controller ready with workflow integration');
            setState(() {
              _videoController = controller;
            });
          },
        ),
      ),
    );
  }

  Widget _buildUnsupportedMediaPreview(BuildContext context) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            _getMediaTypeIcon(widget.mediaItem.mediaType),
            size: 64,
            color: Colors.white70,
          ),
          const SizedBox(height: AppSpacing.md),
          Text(
            'Preview not available',
            style: AppTextStyles.h6.copyWith(
              color: Colors.white70,
            ),
          ),
          const SizedBox(height: AppSpacing.sm),
          Text(
            'This media type is not supported for preview',
            style: AppTextStyles.bodyMedium.copyWith(
              color: Colors.white54,
            ),
          ),
          const SizedBox(height: AppSpacing.lg),
          ElevatedButton.icon(
            onPressed: () {
              // TODO: Implement download functionality
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('Download functionality not implemented yet')),
              );
            },
            icon: const Icon(Icons.download),
            label: const Text('Download'),
          ),
        ],
      ),
    );
  }

  Widget _buildErrorPreview(BuildContext context, String message) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(
            Icons.error_outline,
            size: 64,
            color: Colors.red,
          ),
          const SizedBox(height: AppSpacing.md),
          Text(
            'Error',
            style: AppTextStyles.h6.copyWith(
              color: Colors.white,
            ),
          ),
          const SizedBox(height: AppSpacing.sm),
          Text(
            message,
            style: AppTextStyles.bodyMedium.copyWith(
              color: Colors.white70,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: AppSpacing.lg),
          ElevatedButton(
            onPressed: () {
              if (context.canPop()) {
                context.pop();
              } else {
                context.go('/gallery');
              }
            },
            child: const Text('Go Back'),
          ),
        ],
      ),
    );
  }

  IconData _getMediaTypeIcon(MediaType mediaType) {
    switch (mediaType) {
      case MediaType.image:
        return Icons.image;
      case MediaType.video:
        return Icons.video_library;
      case MediaType.audio:
        return Icons.audiotrack;
      case MediaType.document:
        return Icons.description;
      default:
        return Icons.insert_drive_file;
    }
  }

  /// Build enhanced workflow status overlay for Workflows 4 & 5
  // COMMENTED OUT - Overlay widgets moved to performance bar and bottom bar
  /*
  Widget _buildWorkflowStatusOverlay(WidgetRef ref) {
    final processingStatus = ref.watch(processingStatusProvider(widget.mediaItem.uuid));
    final activeSessions = ref.watch(activeSessionsProvider);
    final playbackMode = ref.watch(optimalPlaybackModeProvider(widget.mediaItem.uuid));
    
    return Positioned(
      top: 16,
      right: 16,
      child: Card(
        color: Colors.black87,
        elevation: 8,
        child: Container(
          width: 280,
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              // Enhanced Status Header
              _buildEnhancedStatusHeader(processingStatus, playbackMode),
              
              const SizedBox(height: 12),
              
              // Processing Status Indicator
              processingStatus.when(
                data: (status) => status != null 
                    ? _buildProcessingStatusWidget(status, ref)
                    : Container(
                        padding: const EdgeInsets.all(12),
                        child: const Text('No processing status available'),
                      ),
                loading: () => _buildLoadingStatusWidget(),
                error: (error, stack) => _buildErrorStatusWidget(error),
              ),
              
              const SizedBox(height: 12),
              
              // Active Sessions Status
              activeSessions.when(
                data: (sessions) => _buildActiveSessionsWidget(sessions, ref),
                loading: () => const SizedBox.shrink(),
                error: (error, stack) => const SizedBox.shrink(),
              ),
              
              // MediaWorkflow Progress (New Orchestrator-based workflows)
              _buildMediaWorkflowProgress(ref),
              
              const SizedBox(height: 12),
              
              // Enhanced Workflow Controls
              _buildEnhancedWorkflowControls(ref),
            ],
          ),
        ),
      ),
    );
  }
  */

  /// Build enhanced status header with workflow information
  Widget _buildEnhancedStatusHeader(AsyncValue<ProcessingStatus?> processingStatus, AsyncValue<PlaybackMode?> playbackMode) {
    return Row(
      children: [
        const Icon(Icons.settings_applications, color: Colors.white, size: 18),
        const SizedBox(width: 8),
        const Expanded(
          child: Text(
            'Workflow Status',
            style: TextStyle(
              color: Colors.white,
              fontSize: 14,
              fontWeight: FontWeight.bold,
            ),
          ),
        ),
        // Playback mode indicator
        playbackMode.when(
          data: (mode) => Container(
            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
            decoration: BoxDecoration(
              color: _getPlaybackModeColor(mode?.mode ?? 'standard'),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Text(
              _getPlaybackModeDisplayName(mode?.mode ?? 'standard'),
              style: const TextStyle(
                color: Colors.white,
                fontSize: 10,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
          loading: () => const SizedBox(
            width: 12,
            height: 12,
            child: CircularProgressIndicator(strokeWidth: 1),
          ),
          error: (error, stack) => const Icon(Icons.error, color: Colors.red, size: 12),
        ),
      ],
    );
  }

  /// Build loading status widget
  Widget _buildLoadingStatusWidget() {
    return const Row(
      children: [
        SizedBox(
          width: 16,
          height: 16,
          child: CircularProgressIndicator(strokeWidth: 2, color: Colors.blue),
        ),
        SizedBox(width: 8),
        Text('Loading workflow status...', style: TextStyle(color: Colors.white70, fontSize: 12)),
      ],
    );
  }

  /// Build error status widget
  Widget _buildErrorStatusWidget(Object error) {
    return Container(
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
                  color: Colors.red[900]!.withValues(alpha: 0.3),
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: Colors.red, width: 1),
      ),
      child: Row(
        children: [
          const Icon(Icons.error, color: Colors.red, size: 16),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              'Status error: ${error.toString()}',
              style: const TextStyle(color: Colors.red, fontSize: 11),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ],
      ),
    );
  }

  /// Build enhanced processing status widget
  Widget _buildProcessingStatusWidget(ProcessingStatus status, WidgetRef ref) {
    final isProcessed = status.faceDetectionProcessed;
    final hasActiveSession = status.currentSession != null;
    final faceCount = status.totalFacesDetected ?? 0;
    
    return Container(
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: _getStatusBackgroundColor(isProcessed, hasActiveSession),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(
          color: _getStatusBorderColor(isProcessed, hasActiveSession),
          width: 1,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Status header
          Row(
            children: [
              Icon(
                _getStatusIcon(isProcessed, hasActiveSession),
                color: _getStatusColor(isProcessed, hasActiveSession),
                size: 16,
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  _getStatusText(isProcessed, hasActiveSession),
                  style: TextStyle(
                    color: _getStatusColor(isProcessed, hasActiveSession),
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
              if (isProcessed) ...[
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(
                    color: Colors.green[700],
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Text(
                    '$faceCount faces',
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 10,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ],
            ],
          ),
          
          // Additional status details
          if (status.lastUpdated != null) ...[
            const SizedBox(height: 4),
            Text(
              'Last updated: ${_formatDateTime(status.lastUpdated!)}',
              style: const TextStyle(color: Colors.white70, fontSize: 10),
            ),
          ],
          
          if (status.currentSession != null) ...[
            const SizedBox(height: 4),
            Text(
              'Session: ${status.currentSession!.substring(0, 8)}...',
              style: const TextStyle(color: Colors.white70, fontSize: 10),
            ),
          ],
        ],
      ),
    );
  }

  // Helper methods for status styling
  Color _getStatusBackgroundColor(bool isProcessed, bool hasActiveSession) {
    if (isProcessed) return Colors.green[900]!.withValues(alpha: 0.3);
    if (hasActiveSession) return Colors.orange[900]!.withValues(alpha: 0.3);
    return Colors.grey[900]!.withValues(alpha: 0.3);
  }

  Color _getStatusBorderColor(bool isProcessed, bool hasActiveSession) {
    if (isProcessed) return Colors.green;
    if (hasActiveSession) return Colors.orange;
    return Colors.grey;
  }

  Color _getStatusColor(bool isProcessed, bool hasActiveSession) {
    if (isProcessed) return Colors.green;
    if (hasActiveSession) return Colors.orange;
    return Colors.grey;
  }

  IconData _getStatusIcon(bool isProcessed, bool hasActiveSession) {
    if (isProcessed) return Icons.check_circle;
    if (hasActiveSession) return Icons.pending;
    return Icons.radio_button_unchecked;
  }

  String _getStatusText(bool isProcessed, bool hasActiveSession) {
    if (isProcessed) return 'Face Detection Complete';
    if (hasActiveSession) return 'Processing in Progress';
    return 'Not Processed';
  }

  String _formatDateTime(DateTime dateTime) {
    final now = DateTime.now();
    final difference = now.difference(dateTime);
    
    if (difference.inMinutes < 1) return 'Just now';
    if (difference.inHours < 1) return '${difference.inMinutes}m ago';
    if (difference.inDays < 1) return '${difference.inHours}h ago';
    return '${difference.inDays}d ago';
  }

  /// Build active sessions widget
  Widget _buildActiveSessionsWidget(List<FaceDetectionSession> sessions, WidgetRef ref) {
    final relevantSessions = sessions.where((s) => s.mediaUuid == widget.mediaItem.uuid).toList();
    
    if (relevantSessions.isEmpty) return const SizedBox.shrink();
    
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: relevantSessions.map((session) {
        final sessionStats = ref.watch(personObjectsSessionStatisticsProvider(session.sessionUuid));
        
        return sessionStats.when(
          data: (stats) => _buildPersonObjectsSessionWidget(session, stats),
          loading: () => _buildPersonObjectsSessionWidget(session, null),
          error: (error, stack) => _buildPersonObjectsSessionWidget(session, null),
        );
      }).toList(),
    );
  }

  /// Build person objects session widget
  Widget _buildPersonObjectsSessionWidget(FaceDetectionSession session, Map<String, dynamic>? stats) {
    final isCompleted = session.status == 'completed';
    final hasError = session.status == 'failed' || session.errorMessage != null;
    
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        children: [
          Icon(
            isCompleted ? Icons.check_circle : (hasError ? Icons.error : Icons.play_circle),
            color: isCompleted ? Colors.green : (hasError ? Colors.red : Colors.blue),
            size: 14,
          ),
          const SizedBox(width: 4),
          Text(
            'Person Objects: ${session.sessionUuid.substring(0, 8)}...',
            style: const TextStyle(color: Colors.white, fontSize: 10),
          ),
          if (stats != null) ...[
            const SizedBox(width: 4),
            Text(
              '(${stats['total_person_objects'] ?? 0} persons)',
              style: const TextStyle(color: Colors.white70, fontSize: 9),
            ),
          ],
        ],
      ),
    );
  }

  /// Build session progress widget
  Widget _buildSessionProgressWidget(FaceDetectionSession session, SessionStatistics? stats) {
    final progress = stats?.progress ?? session.progress ?? 0.0;
    final isCompleted = session.status == 'completed';
    final hasError = session.status == 'failed' || session.errorMessage != null;
    
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                isCompleted ? Icons.check_circle : (hasError ? Icons.error : Icons.play_circle),
                color: isCompleted ? Colors.green : (hasError ? Colors.red : Colors.blue),
                size: 14,
              ),
              const SizedBox(width: 4),
              Text(
                'Session ${session.sessionUuid.substring(0, 8)}...',
                style: const TextStyle(color: Colors.white, fontSize: 10),
              ),
            ],
          ),
          if (!isCompleted && !hasError) ...[
            const SizedBox(height: 4),
            LinearProgressIndicator(
              value: progress,
              backgroundColor: Colors.grey[800],
              valueColor: const AlwaysStoppedAnimation<Color>(Colors.blue),
              minHeight: 2,
            ),
            const SizedBox(height: 2),
            Text(
              '${(progress * 100).toStringAsFixed(1)}%',
              style: const TextStyle(color: Colors.white70, fontSize: 10),
            ),
          ],
          if (hasError && session.errorMessage != null) ...[
            const SizedBox(height: 2),
            Text(
              session.errorMessage!,
              style: const TextStyle(color: Colors.red, fontSize: 9),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
          ],
        ],
      ),
    );
  }

  /// Build MediaWorkflow progress widget for orchestrator-based workflows
  Widget _buildMediaWorkflowProgress(WidgetRef ref) {
    final workflowState = ref.watch(mediaWorkflowProvider(widget.mediaItem.uuid));
    
    // Only show if workflow is active (not idle)
    if (workflowState.status == MediaWorkflowStatus.idle) {
      return const SizedBox.shrink();
    }
    
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: Colors.black45,
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: Colors.blue.withOpacity(0.3), width: 1),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Workflow status header
          Row(
            children: [
              Icon(
                _getWorkflowStatusIcon(workflowState.status),
                color: _getWorkflowStatusColor(workflowState.status),
                size: 14,
              ),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  'Workflow: ${workflowState.status.displayName} ${workflowState.method != null ? "(${workflowState.method})" : ""}',
                  style: TextStyle(
                    color: _getWorkflowStatusColor(workflowState.status),
                    fontSize: 11,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
              if (workflowState.workflowId != null) ...[
                Text(
                  workflowState.workflowId!.substring(0, 8),
                  style: const TextStyle(
                    color: Colors.white54,
                    fontSize: 9,
                    fontFamily: 'monospace',
                  ),
                ),
              ],
            ],
          ),
          
          if (workflowState.status == MediaWorkflowStatus.processing || 
              workflowState.status == MediaWorkflowStatus.queued) ...[
            const SizedBox(height: 6),
            LinearProgressIndicator(
              value: workflowState.progress ?? 0.0,
              backgroundColor: Colors.white24,
              valueColor: AlwaysStoppedAnimation<Color>(_getWorkflowStatusColor(workflowState.status)),
              minHeight: 2,
            ),
            const SizedBox(height: 2),
            Text(
              '${((workflowState.progress ?? 0.0) * 100).toStringAsFixed(1)}%',
              style: const TextStyle(color: Colors.white70, fontSize: 10),
            ),
          ],
          
          if (workflowState.error != null) ...[
            const SizedBox(height: 4),
            Text(
              'Error: ${workflowState.error}',
              style: const TextStyle(color: Colors.red, fontSize: 9),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
          ],
        ],
      ),
    );
  }

  IconData _getWorkflowStatusIcon(MediaWorkflowStatus status) {
    switch (status) {
      case MediaWorkflowStatus.idle:
        return Icons.radio_button_unchecked;
      case MediaWorkflowStatus.queued:
        return Icons.schedule;
      case MediaWorkflowStatus.processing:
        return Icons.pending;
      case MediaWorkflowStatus.completed:
        return Icons.check_circle;
      case MediaWorkflowStatus.failed:
        return Icons.error;
      case MediaWorkflowStatus.stopping:
        return Icons.stop_circle;
      case MediaWorkflowStatus.cancelled:
        return Icons.cancel;
    }
  }

  Color _getWorkflowStatusColor(MediaWorkflowStatus status) {
    switch (status) {
      case MediaWorkflowStatus.idle:
        return Colors.grey;
      case MediaWorkflowStatus.queued:
        return Colors.orange;
      case MediaWorkflowStatus.processing:
        return Colors.blue;
      case MediaWorkflowStatus.completed:
        return Colors.green;
      case MediaWorkflowStatus.failed:
        return Colors.red;
      case MediaWorkflowStatus.stopping:
        return Colors.orange;
      case MediaWorkflowStatus.cancelled:
        return Colors.grey;
    }
  }

  /// Build enhanced workflow control buttons
  Widget _buildEnhancedWorkflowControls(WidgetRef ref) {
    final processingStatus = ref.watch(processingStatusProvider(widget.mediaItem.uuid));
    
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Primary controls
        Wrap(
          spacing: 8,
          runSpacing: 6,
          children: [
            // Workflow 4: Session-based Face Detection
            _buildEnhancedControlButton(
              icon: Icons.face,
              label: 'Start Session',
              onTap: () => _startFaceDetection(ref),
              color: Colors.blue,
              enabled: processingStatus.when(
                data: (status) => status?.currentSession == null,
                loading: () => false,
                error: (error, stack) => true,
              ),
            ),
            
            // Phase 6: Person Objects Workflow
            _buildEnhancedControlButton(
              icon: Icons.groups,
              label: 'Group Persons',
              onTap: () => _triggerPersonObjects(ref),
              color: Colors.indigo,
              enabled: processingStatus.when(
                data: (status) => status?.faceDetectionProcessed ?? false,
                loading: () => false,
                error: (error, stack) => false,
              ),
            ),
            
            // PPL Thread: Manual Legacy Media Processing
            _buildEnhancedControlButton(
              icon: Icons.psychology,
              label: 'PPL Thread',
              onTap: () => _triggerPPLThreadForLegacy(ref),
              color: Colors.deepOrange,
              enabled: processingStatus.when(
                data: (status) => status?.currentSession == null, // Available when no active session
                loading: () => false,
                error: (error, stack) => true,
              ),
            ),
            
            // Workflow 5: Stored Face Data Processing
            _buildEnhancedControlButton(
              icon: Icons.flash_on,
              label: 'Optimize',
              onTap: () => _triggerOptimization(ref),
              color: Colors.purple,
              enabled: processingStatus.when(
                data: (status) => !(status?.faceDetectionProcessed ?? false),
                loading: () => false,
                error: (error, stack) => true,
              ),
            ),
            
            // Performance Metrics
            _buildEnhancedControlButton(
              icon: Icons.analytics,
              label: 'Metrics',
              onTap: () => _showPerformanceMetrics(context),
              color: Colors.green,
              enabled: true,
            ),
            
            // Settings
            _buildEnhancedControlButton(
              icon: Icons.settings,
              label: 'Settings',
              onTap: () => _showWorkflowSettings(ref),
              color: Colors.grey,
              enabled: true,
            ),
          ],
        ),
        
        // Phase 6: Person Objects Information Panel
        const SizedBox(height: 12),
        Container(
          width: double.infinity,
          child: PersonObjectsInfoPanel(
            mediaUuid: widget.mediaItem.uuid,
            showTriggerButton: false, // Handled by button above
            onViewDetails: () => _navigateToPersonObjectsDetail(),
          ),
        ),
        
        // Secondary controls
        const SizedBox(height: 8),
        Row(
          children: [
            // Stop/Reset Session
            processingStatus.when(
              data: (status) => status?.currentSession != null
                  ? _buildSecondaryControlButton(
                      icon: Icons.stop,
                      label: 'Stop Session',
                      onTap: () => _stopSession(ref, status!.currentSession!),
                      color: Colors.red,
                    )
                  : const SizedBox.shrink(),
              loading: () => const SizedBox.shrink(),
              error: (error, stack) => const SizedBox.shrink(),
            ),
            
            const Spacer(),
            
            // Refresh status
            _buildSecondaryControlButton(
              icon: Icons.refresh,
              label: 'Refresh',
              onTap: () => _refreshStatus(ref),
              color: Colors.white70,
            ),
          ],
        ),
      ],
    );
  }

  /// Build enhanced control button with better styling
  Widget _buildEnhancedControlButton({
    required IconData icon,
    required String label,
    required VoidCallback onTap,
    required Color color,
    required bool enabled,
  }) {
    return GestureDetector(
      onTap: enabled ? onTap : null,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          color: enabled ? color.withValues(alpha: 0.2) : Colors.grey[800]!.withValues(alpha: 0.3),
          borderRadius: BorderRadius.circular(6),
          border: Border.all(
            color: enabled ? color : Colors.grey[600]!,
            width: 1,
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              icon,
              color: enabled ? color : Colors.grey[600],
              size: 14,
            ),
            const SizedBox(width: 4),
            Text(
              label,
              style: TextStyle(
                color: enabled ? color : Colors.grey[600],
                fontSize: 10,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// Build secondary control button
  Widget _buildSecondaryControlButton({
    required IconData icon,
    required String label,
    required VoidCallback onTap,
    required Color color,
  }) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, color: color, size: 12),
            const SizedBox(width: 3),
            Text(
              label,
              style: TextStyle(
                color: color,
                fontSize: 9,
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// Start face detection for current media (Workflow 4)
  void _startFaceDetection(WidgetRef ref) async {
    try {
      // Use the new MediaWorkflowNotifier for orchestrator-based workflows
      await ref.read(mediaWorkflowProvider(widget.mediaItem.uuid).notifier).startWorkflow('two_stage');
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Workflow 4: Face detection workflow started'),
            backgroundColor: Colors.blue,
            duration: Duration(seconds: 2),
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to start face detection: $e'),
            backgroundColor: Colors.red,
            duration: const Duration(seconds: 3),
          ),
        );
      }
    }
  }

  /// Trigger optimization processing (Workflow 5)
  void _triggerOptimization(WidgetRef ref) async {
    try {
      // Use the new MediaWorkflowNotifier for orchestrator-based workflows
      await ref.read(mediaWorkflowProvider(widget.mediaItem.uuid).notifier).startWorkflow('two_stage');
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Workflow 5: Optimization processing started'),
            backgroundColor: Colors.purple,
            duration: Duration(seconds: 2),
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to trigger optimization: $e'),
            backgroundColor: Colors.red,
            duration: const Duration(seconds: 3),
          ),
        );
      }
    }
  }

  /// Trigger person objects grouping workflow
  void _triggerPersonObjects(WidgetRef ref) async {
    try {
      // Use the PersonObjectsWorkflowController for PPL Thread operations
      final controller = ref.read(personObjectsWorkflowControllerProvider.notifier);
      await controller.autoTriggerWorkflow(widget.mediaItem.uuid);
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('PPL Thread: Person grouping workflow started'),
            backgroundColor: Colors.green,
            duration: Duration(seconds: 2),
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to start person grouping: $e'),
            backgroundColor: Colors.red,
            duration: const Duration(seconds: 3),
          ),
        );
      }
    }
  }

  void _triggerPPLThreadForLegacy(WidgetRef ref) async {
    try {
      // Show confirmation dialog for legacy media processing
      final bool? confirmed = await showDialog<bool>(
        context: context,
        builder: (BuildContext context) {
          return AlertDialog(
            title: const Text('PPL Thread - Legacy Media'),
            content: const Text(
              'This will process legacy media with face detections but no active session. '
              'This creates a new session and processes person objects. Continue?'
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.of(context).pop(false),
                child: const Text('Cancel'),
              ),
              TextButton(
                onPressed: () => Navigator.of(context).pop(true),
                child: const Text('Process'),
              ),
            ],
          );
        },
      );

      if (confirmed != true || !mounted) return;

      // Call the PPL Thread workflow API for legacy media
      final controller = ref.read(personObjectsWorkflowControllerProvider.notifier);
      await controller.triggerLegacyMediaWorkflow(widget.mediaItem.uuid);
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('PPL Thread: Legacy media processing started'),
            backgroundColor: Colors.deepOrange,
            duration: Duration(seconds: 3),
          ),
        );
        
        // Refresh the processing status
        ref.refresh(processingStatusProvider(widget.mediaItem.uuid));
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to process legacy media: $e'),
            backgroundColor: Colors.red,
            duration: const Duration(seconds: 4),
          ),
        );
      }
    }
  }

  /// Check if person objects workflow should be available
  bool _shouldShowPersonObjectsButton(WidgetRef ref) {
    final detectionResult = ref.watch(personObjectsDataProvider(widget.mediaItem.uuid));
    return detectionResult.when(
                           data: (result) => result?.classifiedFaces.isNotEmpty ?? false,
      loading: () => false,
      error: (_, __) => false,
    );
  }

  /// Get person objects workflow button color based on state
  Color _getPersonObjectsButtonColor(WidgetRef ref) {
    final workflow = ref.watch(personObjectsWorkflowControllerProvider);
    switch (workflow) {
      case PersonObjectsWorkflowState.idle:
        return Colors.green;
      case PersonObjectsWorkflowState.checking:
      case PersonObjectsWorkflowState.triggering:
      case PersonObjectsWorkflowState.processing:
        return Colors.orange;
      case PersonObjectsWorkflowState.completed:
        return Colors.blue;
      case PersonObjectsWorkflowState.failed:
        return Colors.red;
      default:
        return Colors.grey;
    }
  }

  /// Navigate to person objects detail screen
  void _navigateToPersonObjectsDetail() {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (context) => PersonObjectsDetailScreen(
          mediaItem: widget.mediaItem,
        ),
      ),
    );
  }

  /// Stop active session
  void _stopSession(WidgetRef ref, String sessionUuid) async {
    try {
      // Use the new MediaWorkflowNotifier to stop workflow
      await ref.read(mediaWorkflowProvider(widget.mediaItem.uuid).notifier).stopWorkflow();
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Workflow stopped successfully'),
            backgroundColor: Colors.orange,
            duration: Duration(seconds: 2),
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to stop workflow: $e'),
            backgroundColor: Colors.red,
            duration: const Duration(seconds: 3),
          ),
        );
      }
    }
  }

  /// Refresh workflow status
  void _refreshStatus(WidgetRef ref) {
    ref.invalidate(processingStatusProvider(widget.mediaItem.uuid));
    ref.invalidate(activeSessionsProvider);
    ref.invalidate(optimalPlaybackModeProvider(widget.mediaItem.uuid));
    
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Status refreshed'),
        backgroundColor: Colors.green,
        duration: Duration(seconds: 1),
      ),
    );
  }

  /// Show workflow settings dialog
  void _showWorkflowSettings(WidgetRef ref) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Workflow Settings'),
        content: const WorkflowSettingsContent(),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.of(context).pop();
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(
                  content: Text('Settings saved'),
                  backgroundColor: Colors.green,
                ),
              );
            },
            child: const Text('Save'),
          ),
        ],
      ),
    );
  }

  // Helper methods for playback mode styling
  Color _getPlaybackModeColor(String mode) {
    switch (mode) {
      case 'stored_data':
        return Colors.blue[700]!;
      case 'realtime_with_session':
        return Colors.purple[700]!;
      case 'realtime_only':
      default:
        return Colors.grey[700]!;
    }
  }

  String _getPlaybackModeDisplayName(String mode) {
    switch (mode) {
      case 'stored_data':
        return 'Optimized';
      case 'realtime_with_session':
        return 'Session';
      case 'realtime_only':
        return 'Real-time';
      default:
        return 'Unknown';
    }
  }

  /// Show performance metrics dialog
  void _showPerformanceMetrics(BuildContext context, {String? focusedWorkflow}) {
    // Determine if we should show as a bottom sheet on mobile or dialog on desktop
    final isDesktop = MediaQuery.of(context).size.width > 768;
    
    if (!isDesktop) {
      // Show as bottom sheet on mobile
      showModalBottomSheet<void>(
        context: context,
        isScrollControlled: true,
        backgroundColor: Colors.transparent,
        builder: (context) => PerformanceMetricsBottomSheet(
          focusedWorkflow: focusedWorkflow,
          mediaUuid: widget.mediaItem.uuid,
        ),
      );
    } else {
      // Show as dialog on desktop
      PerformanceMetricsDialog.show(
        context,
        focusedWorkflow: focusedWorkflow,
        mediaUuid: widget.mediaItem.uuid,
      );
    }
  }

  /// Build enhanced app bar with performance metrics access
  PreferredSizeWidget _buildEnhancedAppBar(BuildContext context, WidgetRef ref) {
    return DarkCustomAppBar(
      title: widget.mediaItem.originalFilename ?? widget.mediaItem.filename ?? 'Media Preview',
      onBackPressed: () {
        if (context.canPop()) {
          context.pop();
        } else {
          context.go('/gallery');
        }
      },
      actions: [
        // Gallery button
        IconButton(
          icon: const Icon(Icons.photo_library),
          onPressed: () => context.go('/gallery'),
          tooltip: 'Go to Gallery',
        ),
      ],
    );
  }

  /// Build performance status bar showing key metrics
  Widget _buildPerformanceStatusBar(WidgetRef ref) {
    final processingStatus = ref.watch(processingStatusProvider(widget.mediaItem.uuid));
    final activeSessions = ref.watch(activeSessionsProvider);
    final playbackMode = ref.watch(optimalPlaybackModeProvider(widget.mediaItem.uuid));
    final workflowState = ref.watch(mediaWorkflowProvider(widget.mediaItem.uuid));
    
    return Container(
      height: 50, // Fixed height to prevent vertical stacking
      color: Colors.grey[900],
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center, // Ensure horizontal alignment
        children: [
          // 1. Playback mode indicator
          Flexible(
            flex: 1,
            child: playbackMode.when(
              data: (mode) => Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: _getPlaybackModeColor(mode?.mode ?? 'standard'),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  _getPlaybackModeDisplayName(mode?.mode ?? 'standard'),
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 10,
                    fontWeight: FontWeight.w600,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              loading: () => const SizedBox(
                width: 20,
                height: 20,
                child: CircularProgressIndicator(strokeWidth: 1),
              ),
              error: (error, stack) => const Icon(Icons.error, color: Colors.red, size: 12),
            ),
          ),
          
          const SizedBox(width: 8),
          
          // 2. Processing status display
          Flexible(
            flex: 2,
            child: processingStatus.when(
              data: (status) => status != null 
                  ? _buildCompactProcessingStatus(status, ref)
                  : const Text(
                      'No processing status',
                      style: TextStyle(color: Colors.white70, fontSize: 12),
                      overflow: TextOverflow.ellipsis,
                    ),
              loading: () => const Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  SizedBox(
                    width: 16,
                    height: 16,
                    child: CircularProgressIndicator(strokeWidth: 2, color: Colors.blue),
                  ),
                  SizedBox(width: 8),
                  Flexible(
                    child: Text('Loading...', style: TextStyle(color: Colors.white70, fontSize: 12), overflow: TextOverflow.ellipsis),
                  ),
                ],
              ),
              error: (error, stack) => const Text(
                'Status error',
                style: TextStyle(color: Colors.red, fontSize: 12),
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ),
          
          const SizedBox(width: 8),
          
          // 3. Active sessions display
          Flexible(
            flex: 1,
            child: activeSessions.when(
              data: (sessions) => _buildCompactActiveSessionsStatus(sessions),
              loading: () => const Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  SizedBox(
                    width: 12,
                    height: 12,
                    child: CircularProgressIndicator(strokeWidth: 1, color: Colors.orange),
                  ),
                  SizedBox(width: 4),
                  Text('Sessions...', style: TextStyle(color: Colors.white70, fontSize: 10)),
                ],
              ),
              error: (error, stack) => const Icon(Icons.error, color: Colors.red, size: 12),
            ),
          ),
          
          const SizedBox(width: 8),
          
          // 4. Media workflow progress
          Flexible(
            flex: 1,
            child: _buildCompactMediaWorkflowProgress(workflowState),
          ),
          
          const SizedBox(width: 4),
          
          // 5. Workflow status display 
          Flexible(
            flex: 1,
            child: _buildCompactWorkflowProgress(workflowState),
          ),

          const SizedBox(width: 4),
          
          // 6. Face and person count display (Enhanced with PPL Thread integration)
          Flexible(
            flex: 1,
            child: CompactFaceAndPersonCountWidget(
              mediaId: widget.mediaItem.uuid,
              color: Colors.white70,
            ),
          ),
          
          const SizedBox(width: 4),
          
          // DEBUG: PPL Thread test widget (horizontal layout)
          Flexible(
            flex: 1,
            child: PPLThreadTestWidget(
              mediaId: widget.mediaItem.uuid,
            ),
          ),
        ],
      ),
    );
  }

  /// Build compact workflow progress for performance bar
  Widget _buildCompactWorkflowProgress(MediaWorkflowState workflowState) {
    // Only show if workflow is active
    if (workflowState.status == MediaWorkflowStatus.idle) {
      return const SizedBox.shrink();
    }
    
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(
          _getWorkflowStatusIcon(workflowState.status),
          color: _getWorkflowStatusColor(workflowState.status),
          size: 14,
        ),
        const SizedBox(width: 4),
        Flexible(
          child: Text(
            workflowState.status == MediaWorkflowStatus.completed 
                ? 'Workflow Done'
                : 'Workflow ${workflowState.status.displayName}',
            style: TextStyle(
              color: _getWorkflowStatusColor(workflowState.status),
              fontSize: 11,
            ),
            overflow: TextOverflow.ellipsis,
          ),
        ),
        if (workflowState.progress != null && workflowState.status == MediaWorkflowStatus.processing) ...[
          const SizedBox(width: 4),
          Text(
            '${(workflowState.progress! * 100).toStringAsFixed(0)}%',
            style: TextStyle(
              color: _getWorkflowStatusColor(workflowState.status),
              fontSize: 10,
            ),
          ),
        ],
      ],
    );
  }

  /// Build compact active sessions status for performance bar
  Widget _buildCompactActiveSessionsStatus(List<FaceDetectionSession> sessions) {
    final relevantSessions = sessions.where((s) => s.mediaUuid == widget.mediaItem.uuid).toList();
    
    if (relevantSessions.isEmpty) {
      return const Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.schedule, color: Colors.grey, size: 12),
          SizedBox(width: 4),
          Text('No sessions', style: TextStyle(color: Colors.grey, fontSize: 10)),
        ],
      );
    }
    
    final activeSession = relevantSessions.firstWhere(
      (s) => s.status == 'running',
      orElse: () => relevantSessions.first,
    );
    
    final progress = activeSession.progress ?? 0.0;
    final isRunning = activeSession.status == 'running';
    
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(
          isRunning ? Icons.play_circle : Icons.check_circle,
          color: isRunning ? Colors.blue : Colors.green,
          size: 12,
        ),
        const SizedBox(width: 4),
        Flexible(
          child: Text(
            isRunning ? '${(progress * 100).toInt()}%' : 'Done',
            style: TextStyle(
              color: isRunning ? Colors.blue : Colors.green,
              fontSize: 10,
              fontWeight: FontWeight.w600,
            ),
            overflow: TextOverflow.ellipsis,
          ),
        ),
      ],
    );
  }

  /// Build compact media workflow progress for performance bar
  Widget _buildCompactMediaWorkflowProgress(MediaWorkflowState workflowState) {
    // Only show if workflow is active
    if (workflowState.status == MediaWorkflowStatus.idle) {
      return const SizedBox.shrink();
    }
    
    final progress = workflowState.progress ?? 0.0;
    final isProcessing = workflowState.status == MediaWorkflowStatus.processing;
    
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(
          isProcessing ? Icons.autorenew : _getWorkflowStatusIcon(workflowState.status),
          color: _getWorkflowStatusColor(workflowState.status),
          size: 12,
        ),
        const SizedBox(width: 4),
        Flexible(
          child: Text(
            isProcessing ? '${(progress * 100).toInt()}%' : workflowState.status.toString().split('.').last,
            style: TextStyle(
              color: _getWorkflowStatusColor(workflowState.status),
              fontSize: 10,
              fontWeight: FontWeight.w600,
            ),
            overflow: TextOverflow.ellipsis,
          ),
        ),
      ],
    );
  }

  /// Build compact processing status for performance bar with person objects integration
  Widget _buildCompactProcessingStatus(ProcessingStatus status, WidgetRef ref) {
    final isProcessed = status.faceDetectionProcessed;
    final faceCount = status.totalFacesDetected ?? 0;
    final hasActiveSession = status.currentSession != null;
    
    // Phase 6: Get person objects data
    final personObjectsAsync = ref.watch(personObjectsDataProvider(widget.mediaItem.uuid));
    final workflowState = ref.watch(personObjectsWorkflowControllerProvider);
    
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(
          isProcessed ? Icons.check_circle : (hasActiveSession ? Icons.play_circle : Icons.face),
          color: isProcessed ? Colors.green : (hasActiveSession ? Colors.blue : Colors.grey),
          size: 14,
        ),
        const SizedBox(width: 4),
        Flexible(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              // Faces detected line
              Text(
                isProcessed 
                    ? '$faceCount faces detected'
                    : hasActiveSession 
                        ? 'Processing...'
                        : 'Ready',
                style: TextStyle(
                  color: isProcessed ? Colors.green : (hasActiveSession ? Colors.blue : Colors.white70),
                  fontSize: 12,
                ),
                overflow: TextOverflow.ellipsis,
              ),
              
              // Phase 6: Person objects line
              if (isProcessed)
                personObjectsAsync.when(
                  data: (data) {
                    if (data != null) {
                      return Text(
                        '${data.totalPersons} persons grouped',
                        style: TextStyle(
                          color: Colors.blue.shade300,
                          fontSize: 11,
                        ),
                        overflow: TextOverflow.ellipsis,
                      );
                    } else if (workflowState == PersonObjectsWorkflowState.processing ||
                               workflowState == PersonObjectsWorkflowState.triggering) {
                      return Text(
                        'Grouping persons...',
                        style: TextStyle(
                          color: Colors.orange.shade300,
                          fontSize: 11,
                        ),
                        overflow: TextOverflow.ellipsis,
                      );
                    } else {
                      return Text(
                        'Person grouping available',
                        style: TextStyle(
                          color: Colors.grey.shade400,
                          fontSize: 11,
                        ),
                        overflow: TextOverflow.ellipsis,
                      );
                    }
                  },
                  loading: () => Text(
                    'Loading persons...',
                    style: TextStyle(
                      color: Colors.grey.shade400,
                      fontSize: 11,
                    ),
                    overflow: TextOverflow.ellipsis,
                  ),
                  error: (error, stack) => const SizedBox.shrink(),
                ),
            ],
          ),
        ),
      ],
    );
  }

  /// Calculate efficiency score from performance metrics
  // double _calculateEfficiencyScore(WorkflowPerformanceMetrics metrics) {
  //   // Base score from CPU and memory usage reductions
  //   double score = 0.0;
  //   
  //   if (metrics.cpuUsageReduction > 0) {
  //     score += metrics.cpuUsageReduction * 50; // Up to 50 points
  //   }
  //   
  //   if (metrics.memoryUsageReduction > 0) {
  //     score += metrics.memoryUsageReduction * 30; // Up to 30 points
  //   }
  //   
  //   // Bonus for processing speed
  //   if (metrics.avgProcessingTimeSeconds != null && metrics.avgProcessingTimeSeconds! < 10) {
  //     score += 20; // Speed bonus
  //   }
  //   
  //   return (score * 100).clamp(0, 100);
  // }

  // /// Get human-readable processing status
  // String _getProcessingStatus(ProcessingStatus? status) {
  //   if (status == null) return 'Idle';
  //   
  //   // Use the displayStatus getter from the updated ProcessingStatus model
  //   return status.displayStatus;
  // }
}

/// Workflow Settings Content Widget
class WorkflowSettingsContent extends StatefulWidget {
  const WorkflowSettingsContent({super.key});

  @override
  State<WorkflowSettingsContent> createState() => _WorkflowSettingsContentState();
}

class _WorkflowSettingsContentState extends State<WorkflowSettingsContent> {
  double _confidenceThreshold = 0.5;
  bool _enableOptimization = true;
  String _detectionMethod = 'opencv';

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 300,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Face Detection Settings',
            style: TextStyle(fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 16),
          
          // Confidence Threshold
          Text('Confidence Threshold: ${_confidenceThreshold.toStringAsFixed(1)}'),
          Slider(
            value: _confidenceThreshold,
            min: 0.1,
            max: 1.0,
            divisions: 9,
            onChanged: (value) {
              setState(() {
                _confidenceThreshold = value;
              });
            },
          ),
          
          const SizedBox(height: 16),
          
          // Detection Method
          const Text('Detection Method:'),
          DropdownButton<String>(
            value: _detectionMethod,
            isExpanded: true,
            items: const [
              DropdownMenuItem(value: 'opencv', child: Text('OpenCV')),
              DropdownMenuItem(value: 'dlib', child: Text('DLib')),
              DropdownMenuItem(value: 'both', child: Text('Both (Hybrid)')),
            ],
            onChanged: (value) {
              if (value != null) {
                setState(() {
                  _detectionMethod = value;
                });
              }
            },
          ),
          
          const SizedBox(height: 16),
          
          // Enable Optimization
          CheckboxListTile(
            title: const Text('Enable CPU Optimization'),
            subtitle: const Text('Use Workflow 5 for better performance'),
            value: _enableOptimization,
            onChanged: (value) {
              setState(() {
                _enableOptimization = value ?? true;
              });
            },
            controlAffinity: ListTileControlAffinity.leading,
            contentPadding: EdgeInsets.zero,
          ),
        ],
      ),
    );
  }
}
