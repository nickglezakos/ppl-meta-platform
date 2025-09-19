import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:video_player/video_player.dart';
import '../core/theme/app_theme.dart';
import '../models/media_models.dart';
import '../models/face_detection_models.dart';
import '../widgets/smart_video_player_widget.dart';
import '../widgets/workflow/workflow_session_controls_widget.dart';
import '../widgets/performance/performance_metrics_dialog.dart';
import '../widgets/performance/simple_performance_metrics_widget.dart';
import '../core/api/api_client.dart';
import '../widgets/custom_app_bar.dart';
import '../providers/workflow_providers.dart';


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
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: _buildEnhancedAppBar(context, ref),
      backgroundColor: Colors.black,
      body: Column(
        children: [
          // Performance status bar
          _buildPerformanceStatusBar(ref),
          
          // Main media content
          Expanded(
            child: Stack(
              children: [
                _buildMediaContent(context, ref),
                // Workflow Status Overlay
                _buildWorkflowStatusOverlay(ref),
              ],
            ),
          ),
          
          // Workflow Session Controls
          if (widget.mediaItem.uuid != null)
            WorkflowSessionControlsWidget(
              mediaUuid: widget.mediaItem.uuid!,
              showExpanded: _showWorkflowControls,
              onToggleExpanded: () {
                setState(() {
                  _showWorkflowControls = !_showWorkflowControls;
                });
              },
            ),
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
              
              const SizedBox(height: 12),
              
              // Enhanced Workflow Controls
              _buildEnhancedWorkflowControls(ref),
            ],
          ),
        ),
      ),
    );
  }

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
        final sessionStats = ref.watch(sessionStatisticsProvider(session.sessionUuid));
        
        return sessionStats.when(
          data: (stats) => _buildSessionProgressWidget(session, stats),
          loading: () => _buildSessionProgressWidget(session, null),
          error: (error, stack) => _buildSessionProgressWidget(session, null),
        );
      }).toList(),
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

  /// Build enhanced workflow control buttons
  Widget _buildEnhancedWorkflowControls(WidgetRef ref) {
    final processingStatus = ref.watch(processingStatusProvider(widget.mediaItem.uuid));
    
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Control section header
        const Row(
          children: [
            Icon(Icons.tune, color: Colors.white70, size: 14),
            SizedBox(width: 6),
            Text(
              'Workflow Controls',
              style: TextStyle(
                color: Colors.white70,
                fontSize: 11,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        
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
      final request = SessionCreationRequest(
        mediaUuid: widget.mediaItem.uuid,
        confidenceThreshold: 0.5,
        detectionMethods: ['opencv', 'dlib'],
        priority: 'normal',
        enableProgressUpdates: true,
      );
      
      await ref.read(createSessionProvider)(request);
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Workflow 4: Face detection session started'),
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
      // Use the API client directly for now
      final client = ref.read(workflowApiClientProvider);
      final response = await client.processVideoForOptimization(
        mediaUuid: widget.mediaItem.uuid,
        confidenceThreshold: 0.5,
        detectionMethods: ['opencv', 'dlib'],
      );
      
      if (response.success && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Workflow 5: Optimization processing started'),
            backgroundColor: Colors.purple,
            duration: Duration(seconds: 2),
          ),
        );
      } else {
        throw Exception(response.error ?? 'Unknown error');
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

  /// Stop active session
  void _stopSession(WidgetRef ref, String sessionUuid) async {
    try {
      final client = ref.read(workflowApiClientProvider);
      final response = await client.deleteSession(sessionUuid);
      
      if (response.success && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Session stopped successfully'),
            backgroundColor: Colors.orange,
            duration: Duration(seconds: 2),
          ),
        );
      } else {
        throw Exception(response.error ?? 'Unknown error');
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to stop session: $e'),
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
        // Performance metrics access button
        Consumer(
          builder: (context, ref, child) {
            final metricsAsync = ref.watch(performanceMetricsProvider);
            
            return IconButton(
              icon: Icon(
                Icons.analytics,
                color: metricsAsync.hasValue 
                    ? Colors.green[400] 
                    : Colors.white70,
              ),
              onPressed: () => _showPerformanceMetrics(context),
              tooltip: 'Performance Analytics',
            );
          },
        ),
        
        // Compact performance display
        Padding(
          padding: const EdgeInsets.only(right: 8),
          child: CompactPerformanceMetricsWidget(
            onTap: () => _showPerformanceMetrics(context),
          ),
        ),
      ],
    );
  }

  /// Build performance status bar showing key metrics
  Widget _buildPerformanceStatusBar(WidgetRef ref) {
    final metricsAsync = ref.watch(performanceMetricsProvider);
    final processingStatusAsync = ref.watch(processingStatusProvider(widget.mediaItem.uuid!));
    
    return Container(
      height: 40,
      color: Colors.grey[900],
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Row(
        children: [
          Icon(
            Icons.analytics,
            size: 16,
            color: Colors.green[400],
          ),
          const SizedBox(width: 8),
          
          Expanded(
            child: metricsAsync.when(
              data: (metrics) {
                final efficiency = _calculateEfficiencyScore(metrics);
                final processingStatus = processingStatusAsync.when(
                  data: (status) => _getProcessingStatus(status),
                  loading: () => 'Loading...',
                  error: (_, __) => 'Idle', // Gracefully handle missing workflow
                );
                return Text(
                  'Performance: ${efficiency.toStringAsFixed(0)}% • Processing: $processingStatus',
                  style: const TextStyle(
                    color: Colors.white70,
                    fontSize: 12,
                  ),
                );
              },
              loading: () => const Text(
                'Loading performance data...',
                style: TextStyle(color: Colors.white70, fontSize: 12),
              ),
              error: (error, stack) => Text(
                'Performance data unavailable',
                style: TextStyle(color: Colors.red[400], fontSize: 12),
              ),
            ),
          ),
          
          // Quick action button
          IconButton(
            icon: const Icon(Icons.tune, size: 16, color: Colors.white70),
            onPressed: () => _showPerformanceMetrics(context),
            padding: EdgeInsets.zero,
            constraints: const BoxConstraints(
              minWidth: 32,
              minHeight: 32,
            ),
          ),
        ],
      ),
    );
  }

  /// Calculate efficiency score from performance metrics
  double _calculateEfficiencyScore(WorkflowPerformanceMetrics metrics) {
    // Base score from CPU and memory usage reductions
    double score = 0.0;
    
    if (metrics.cpuUsageReduction > 0) {
      score += metrics.cpuUsageReduction * 50; // Up to 50 points
    }
    
    if (metrics.memoryUsageReduction > 0) {
      score += metrics.memoryUsageReduction * 30; // Up to 30 points
    }
    
    // Bonus for processing speed
    if (metrics.avgProcessingTimeSeconds != null && metrics.avgProcessingTimeSeconds! < 10) {
      score += 20; // Speed bonus
    }
    
    return (score * 100).clamp(0, 100);
  }

  /// Get human-readable processing status
  String _getProcessingStatus(ProcessingStatus? status) {
    if (status == null) return 'Idle';
    
    // Use the displayStatus getter from the updated ProcessingStatus model
    return status.displayStatus;
  }

  @override
  void dispose() {
    // Clear video controller reference without disposing
    // (the VideoPlayerWidget will handle its own disposal)
    _videoController = null;
    super.dispose();
  }
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
