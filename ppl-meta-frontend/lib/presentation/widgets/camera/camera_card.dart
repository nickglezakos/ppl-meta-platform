import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/models/camera.dart';
import '../../../core/providers/camera_providers.dart';

class CameraCard extends ConsumerWidget {
  final Camera camera;
  final VoidCallback? onTap;

  const CameraCard({
    super.key,
    required this.camera,
    this.onTap,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colorScheme = Theme.of(context).colorScheme;
    final textTheme = Theme.of(context).textTheme;

    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
      ),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header with status indicator
              Row(
                children: [
                  Icon(
                    Icons.videocam,
                    color: camera.isConnected ? Colors.green : Colors.grey,
                    size: 24,
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      camera.name,
                      style: textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  // Collection status indicator
                  _CollectionStatusIndicator(cameraId: camera.deviceId),
                  const SizedBox(width: 8),
                  _StatusIndicator(camera: camera),
                ],
              ),
              
              const SizedBox(height: 12),
              
              // Camera details
              if (camera.manufacturer != null || camera.model != null)
                Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Text(
                    '${camera.manufacturer ?? ''} ${camera.model ?? ''}'.trim(),
                    style: textTheme.bodySmall?.copyWith(
                      color: colorScheme.outline,
                    ),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              
              // Resolution
              if (camera.resolution != null)
                Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Row(
                    children: [
                      Icon(
                        Icons.high_quality,
                        size: 16,
                        color: colorScheme.outline,
                      ),
                      const SizedBox(width: 4),
                      Text(
                        camera.resolution!,
                        style: textTheme.bodySmall?.copyWith(
                          color: colorScheme.outline,
                        ),
                      ),
                    ],
                  ),
                ),
              
              const Spacer(),
              
              // Bottom actions
              Row(
                children: [
                  // Active status
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 8,
                      vertical: 4,
                    ),
                    decoration: BoxDecoration(
                      color: camera.isActive 
                          ? Colors.green.withOpacity(0.1)
                          : Colors.grey.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(
                        color: camera.isActive 
                            ? Colors.green.withOpacity(0.3)
                            : Colors.grey.withOpacity(0.3),
                      ),
                    ),
                    child: Text(
                      camera.isActive ? 'Active' : 'Inactive',
                      style: textTheme.bodySmall?.copyWith(
                        color: camera.isActive ? Colors.green : Colors.grey,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ),
                  
                  const Spacer(),
                  
                  // Recording and stream controls
                  if (camera.isConnected) ...[
                    _RecordingControls(cameraId: camera.deviceId),
                    const SizedBox(width: 8),
                    IconButton(
                      onPressed: onTap,
                      icon: const Icon(Icons.play_circle_outline),
                      iconSize: 20,
                      padding: EdgeInsets.zero,
                      constraints: const BoxConstraints(),
                      tooltip: 'View stream',
                    ),
                  ],
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _StatusIndicator extends StatelessWidget {
  final Camera camera;

  const _StatusIndicator({required this.camera});

  @override
  Widget build(BuildContext context) {
    Color statusColor;
    IconData statusIcon;
    String tooltip;

    switch (camera.connectionStatus) {
      case CameraConnectionStatus.connected:
        statusColor = Colors.green;
        statusIcon = Icons.circle;
        tooltip = 'Connected';
        break;
      case CameraConnectionStatus.connecting:
        statusColor = Colors.orange;
        statusIcon = Icons.circle;
        tooltip = 'Connecting';
        break;
      case CameraConnectionStatus.error:
        statusColor = Colors.red;
        statusIcon = Icons.error;
        tooltip = 'Error';
        break;
      case CameraConnectionStatus.disconnected:
      default:
        statusColor = Colors.grey;
        statusIcon = Icons.circle;
        tooltip = 'Disconnected';
        break;
    }

    return Tooltip(
      message: tooltip,
      child: Icon(
        statusIcon,
        color: statusColor,
        size: 12,
      ),
    );
  }
}

class _CollectionStatusIndicator extends ConsumerWidget {
  final String cameraId;

  const _CollectionStatusIndicator({required this.cameraId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final hasCollection = ref.watch(cameraHasCollectionProvider(cameraId));
    
    return hasCollection.when(
      data: (hasCollection) {
        if (hasCollection) {
          return Tooltip(
            message: 'Collection linked',
            child: Icon(
              Icons.folder_outlined,
              color: Colors.blue,
              size: 16,
            ),
          );
        } else {
          return Tooltip(
            message: 'No collection',
            child: Icon(
              Icons.folder_off_outlined,
              color: Colors.grey,
              size: 16,
            ),
          );
        }
      },
      loading: () => SizedBox(
        width: 16,
        height: 16,
        child: CircularProgressIndicator(strokeWidth: 2),
      ),
      error: (_, __) => Icon(
        Icons.error_outline,
        color: Colors.red,
        size: 16,
      ),
    );
  }
}

/// Recording controls widget for camera cards
class _RecordingControls extends ConsumerWidget {
  final String cameraId;

  const _RecordingControls({required this.cameraId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final recordingState = ref.watch(cameraRecordingProvider(cameraId));
    final recordingNotifier = ref.read(cameraRecordingProvider(cameraId).notifier);

    // Recording indicator dot
    if (recordingState.isRecording) {
      return Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Recording indicator with pulsing animation
          _PulsingRecordingDot(),
          const SizedBox(width: 4),
          // Stop recording button
          IconButton(
            onPressed: recordingState.isLoading 
                ? null 
                : () => recordingNotifier.stopRecording(),
            icon: recordingState.isLoading
                ? const SizedBox(
                    width: 12,
                    height: 12,
                    child: CircularProgressIndicator(strokeWidth: 1.5),
                  )
                : const Icon(Icons.stop_circle, color: Colors.red),
            iconSize: 20,
            padding: EdgeInsets.zero,
            constraints: const BoxConstraints(),
            tooltip: recordingState.isLoading ? 'Stopping...' : 'Stop recording',
          ),
        ],
      );
    } else {
      // Start recording button
      return IconButton(
        onPressed: recordingState.isLoading 
            ? null 
            : () => recordingNotifier.startRecording(),
        icon: recordingState.isLoading
            ? const SizedBox(
                width: 12,
                height: 12,
                child: CircularProgressIndicator(strokeWidth: 1.5),
              )
            : const Icon(Icons.fiber_manual_record, color: Colors.red),
        iconSize: 20,
        padding: EdgeInsets.zero,
        constraints: const BoxConstraints(),
        tooltip: recordingState.isLoading ? 'Starting...' : 'Start recording',
      );
    }
  }
}

/// Pulsing red dot to indicate active recording
class _PulsingRecordingDot extends StatefulWidget {
  @override
  _PulsingRecordingDotState createState() => _PulsingRecordingDotState();
}

class _PulsingRecordingDotState extends State<_PulsingRecordingDot>
    with SingleTickerProviderStateMixin {
  late AnimationController _animationController;
  late Animation<double> _animation;

  @override
  void initState() {
    super.initState();
    _animationController = AnimationController(
      duration: const Duration(milliseconds: 1000),
      vsync: this,
    );
    _animation = Tween<double>(
      begin: 0.3,
      end: 1.0,
    ).animate(CurvedAnimation(
      parent: _animationController,
      curve: Curves.easeInOut,
    ));
    _animationController.repeat(reverse: true);
  }

  @override
  void dispose() {
    _animationController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _animation,
      builder: (context, child) {
        return Container(
          width: 8,
          height: 8,
          decoration: BoxDecoration(
            color: Colors.red.withOpacity(_animation.value),
            shape: BoxShape.circle,
          ),
        );
      },
    );
  }
}
