import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'dart:async';
import '../../../core/models/camera.dart';
import '../../../core/providers/camera_providers.dart';
import '../../../core/providers/camera_status_providers.dart';
import '../../../core/providers/multi_camera_providers.dart';
import '../../../core/services/camera_service.dart';
import '../../../core/services/auth_service.dart';
import '../../../core/config/app_config.dart';
import '../../pages/camera_stream_page.dart';
import '../../screens/cameras/camera_pipeline_settings_screen.dart';
import '../../../widgets/camera/camera_counter_widget.dart';
import '../../../widgets/camera/instant_detection_widget.dart';
import 'rtsp_camera_dialog.dart';

class CameraCard extends ConsumerWidget {
  final Camera camera;
  final VoidCallback? onTap;

  const CameraCard({
    super.key,
    required this.camera,
    this.onTap,
  });

  static IconData _getCameraIcon(CameraType type) {
    switch (type) {
      case CameraType.mobile:
        return Icons.smartphone;
      case CameraType.edge:
        return Icons.router; // RPi5 edge device icon
      case CameraType.rtsp:
        return Icons.videocam_outlined;
      case CameraType.usb:
      case CameraType.webRtc:
      case CameraType.mjpeg:
      case CameraType.virtual:
      default:
        return Icons.videocam;
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colorScheme = Theme.of(context).colorScheme;
    final textTheme = Theme.of(context).textTheme;
    
    // Watch camera list to rebuild when camera status changes
    final cameraListState = ref.watch(cameraListProvider);
    final updatedCamera = cameraListState.cameras.firstWhere(
      (c) => c.deviceId == camera.deviceId,
      orElse: () => camera,
    );
    
    debugPrint('🔄 [CameraCard] BUILD triggered for ${camera.deviceId}');
    
    // Watch WebSocket status for this camera
    final cameraStatus = ref.watch(cameraStatusProvider(updatedCamera.deviceId));
    
    // For mobile and edge cameras, use the camera's own status field since they don't use backend WebSocket
    // For USB/RTSP cameras, use WebSocket status if available, otherwise use camera status
    final bool isConnected = (updatedCamera.type == CameraType.mobile || updatedCamera.type == CameraType.edge)
        ? updatedCamera.status.toLowerCase() == 'connected'
        : (cameraStatus?.isConnected ?? updatedCamera.status.toLowerCase() == 'connected');
    
    // 🔍 DEBUG: Log camera status evaluation
    debugPrint('🎥 [CameraCard] ${updatedCamera.deviceId}:');
    debugPrint('   📌 Type: ${updatedCamera.type}');
    debugPrint('   📌 Camera.status: ${updatedCamera.status}');
    debugPrint('   📌 WebSocket.status: ${cameraStatus?.status}');
    debugPrint('   📌 WebSocket.isConnected: ${cameraStatus?.isConnected}');
    debugPrint('   ✅ Final isConnected: $isConnected');
    debugPrint('   🎬 Play button visible: $isConnected');

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
                    _getCameraIcon(updatedCamera.type),
                    color: isConnected ? Colors.green : Colors.grey,
                    size: 24,
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      updatedCamera.name,
                      style: textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  // Pipeline status indicators
                  if (updatedCamera.instantDetectionEnabled)
                    Tooltip(
                      message: 'Instant Detection Active',
                      child: Container(
                        padding: const EdgeInsets.all(4),
                        decoration: BoxDecoration(
                          color: Colors.orange.withOpacity(0.1),
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: const Icon(
                          Icons.bolt,
                          color: Colors.orange,
                          size: 16,
                        ),
                      ),
                    ),
                  const SizedBox(width: 4),
                  if (updatedCamera.recordingPipelineEnabled)
                    Tooltip(
                      message: 'Recording Pipeline Active',
                      child: Container(
                        padding: const EdgeInsets.all(4),
                        decoration: BoxDecoration(
                          color: Colors.red.withOpacity(0.1),
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: const Icon(
                          Icons.fiber_manual_record,
                          color: Colors.red,
                          size: 16,
                        ),
                      ),
                    ),
                  const SizedBox(width: 4),
                  // Pipeline settings button
                  IconButton(
                    onPressed: () => _showPipelineSettings(context, ref, updatedCamera),
                    icon: const Icon(Icons.tune, size: 20),
                    iconSize: 20,
                    padding: const EdgeInsets.all(4),
                    constraints: const BoxConstraints(),
                    tooltip: 'Pipeline Settings',
                  ),
                  const SizedBox(width: 4),
                  // Collection status indicator
                  _CollectionStatusIndicator(cameraId: updatedCamera.deviceId),
                  const SizedBox(width: 8),
                  _StatusIndicator(camera: updatedCamera),
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
              
              const SizedBox(height: 12),
              
              // Counter widgets - MVR People Counter
              CameraCounterWidget(
                cameraId: camera.deviceId,
              ),
              const SizedBox(height: 8),
              
              // Counter widgets - Instant Detection
              InstantDetectionWidget(
                cameraId: camera.deviceId,
              ),
              
              const SizedBox(height: 12),
              
              // Inline stream preview (thumbnail) when connected - TEMPORARILY DISABLED
              // Uncomment to enable inline thumbnails:
              // if (isConnected)
              //   _StreamThumbnail(camera: camera),
              // 
              // if (isConnected)
              //   const SizedBox(height: 12),
              
              // Recording status row (isolated widget)
              if (isConnected)
                _RecordingStatusRow(cameraId: camera.deviceId),
              
              if (isConnected)
                const SizedBox(height: 8),
              
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
                  
                  // RTSP Edit button (only for RTSP cameras)
                  if (updatedCamera.type == CameraType.rtsp) ...[
                    IconButton(
                      onPressed: () => _showEditRTSPDialog(context, ref, updatedCamera),
                      icon: const Icon(Icons.edit),
                      iconSize: 28,
                      padding: const EdgeInsets.all(8),
                      constraints: const BoxConstraints(),
                      tooltip: 'Edit camera',
                    ),
                    const SizedBox(width: 12),
                    IconButton(
                      onPressed: () => _showDeleteRTSPDialog(context, ref, updatedCamera),
                      icon: const Icon(Icons.delete, color: Colors.red),
                      iconSize: 28,
                      padding: const EdgeInsets.all(8),
                      constraints: const BoxConstraints(),
                      tooltip: 'Delete camera',
                    ),
                    const SizedBox(width: 8),
                  ],
                  
                  // Edge Camera Settings button (only for Edge cameras)
                  if (updatedCamera.type == CameraType.edge) ...[
                    IconButton(
                      onPressed: () {
                        context.go('/edge-cameras/${updatedCamera.deviceId}?name=${Uri.encodeComponent(updatedCamera.name)}');
                      },
                      icon: const Icon(Icons.settings),
                      iconSize: 28,
                      padding: const EdgeInsets.all(8),
                      constraints: const BoxConstraints(),
                      tooltip: 'Edge Camera Settings',
                    ),
                    const SizedBox(width: 8),
                  ],
                  
                  // Archive/Unarchive button
                  IconButton(
                    onPressed: () async {
                      print('🗃️ [CameraCard] Archive button pressed for camera: ${updatedCamera.deviceId}');
                      print('🗃️ [CameraCard] Current archived state: ${updatedCamera.archived}');
                      
                      final cameraActions = ref.read(cameraActionsProvider);
                      final scaffoldMessenger = ScaffoldMessenger.of(context);
                      
                      try {
                        if (updatedCamera.archived) {
                          // Unarchive camera
                          print('🗃️ [CameraCard] Calling unarchiveCamera for ${updatedCamera.deviceId}');
                          final success = await cameraActions.unarchiveCamera(updatedCamera.deviceId);
                          print('🗃️ [CameraCard] Unarchive result: $success');
                          
                          if (success) {
                            scaffoldMessenger.showSnackBar(
                              SnackBar(
                                content: Text('${updatedCamera.name} restored from archive'),
                                backgroundColor: Colors.green,
                              ),
                            );
                          } else {
                            print('❌ [CameraCard] Unarchive failed for ${updatedCamera.deviceId}');
                            scaffoldMessenger.showSnackBar(
                              SnackBar(
                                content: Text('Failed to unarchive ${updatedCamera.name}'),
                                backgroundColor: Colors.red,
                              ),
                            );
                          }
                        } else {
                          // Archive camera
                          print('🗃️ [CameraCard] Calling archiveCamera for ${updatedCamera.deviceId}');
                          final success = await cameraActions.archiveCamera(updatedCamera.deviceId);
                          print('🗃️ [CameraCard] Archive result: $success');
                          
                          if (success) {
                            scaffoldMessenger.showSnackBar(
                              SnackBar(
                                content: Text('${updatedCamera.name} archived'),
                                backgroundColor: Colors.orange,
                              ),
                            );
                          } else {
                            print('❌ [CameraCard] Archive failed for ${updatedCamera.deviceId}');
                            scaffoldMessenger.showSnackBar(
                              SnackBar(
                                content: Text('Failed to archive ${updatedCamera.name}'),
                                backgroundColor: Colors.red,
                              ),
                            );
                          }
                        }
                      } catch (e, stackTrace) {
                        print('❌ [CameraCard] Archive/unarchive error: $e');
                        print('❌ [CameraCard] Stack trace: $stackTrace');
                        scaffoldMessenger.showSnackBar(
                          SnackBar(
                            content: Text('Failed to ${updatedCamera.archived ? "unarchive" : "archive"} camera: $e'),
                            backgroundColor: Colors.red,
                          ),
                        );
                      }
                    },
                    icon: Icon(
                      Icons.archive,
                      color: updatedCamera.archived ? Colors.orange : Colors.grey,
                    ),
                    iconSize: 28,
                    padding: const EdgeInsets.all(8),
                    constraints: const BoxConstraints(),
                    tooltip: updatedCamera.archived ? 'Unarchive camera' : 'Archive camera',
                  ),
                  const SizedBox(width: 8),
                  
                  // Connection toggle button
                  _ConnectionButton(camera: updatedCamera),
                  const SizedBox(width: 12),
                  
                  // Recording and stream controls
                  if (isConnected) ...[
                    // For USB/RTSP/edge cameras, show recording controls
                    if (updatedCamera.type != CameraType.edge) ...[
                      _RecordingControls(cameraId: updatedCamera.deviceId),
                      const SizedBox(width: 12),
                    ],
                    IconButton(
                      onPressed: () {
                        // 🔍 DEBUG: Log navigation attempt
                        debugPrint('🎬 [CameraCard] Navigating to stream for ${updatedCamera.deviceId}');
                        debugPrint('🎬 [CameraCard] Camera: ${updatedCamera.toJson()}');
                        
                        // Navigate to full-screen stream page
                        Navigator.of(context).push(
                          MaterialPageRoute(
                            builder: (context) => CameraStreamPage(camera: updatedCamera),
                          ),
                        );
                      },
                      icon: const Icon(Icons.play_circle_outline),
                      iconSize: 28,
                      padding: const EdgeInsets.all(8),
                      constraints: const BoxConstraints(),
                      tooltip: 'View stream',
                    ),
                  ] else ...[
                    // 🔍 DEBUG: Show why play button is hidden
                    Tooltip(
                      message: 'Camera must be connected to view stream',
                      child: Icon(
                        Icons.play_circle_outline,
                        size: 28,
                        color: Colors.grey.withOpacity(0.3),
                      ),
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
  
  static void _showPipelineSettings(BuildContext context, WidgetRef ref, Camera camera) {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (context) => CameraPipelineSettingsScreen(camera: camera),
      ),
    ).then((result) {
      if (result == true) {
        // Reload cameras after settings change
        ref.read(cameraListProvider.notifier).loadCameras();
      }
    });
  }
  
  static void _showEditRTSPDialog(BuildContext context, WidgetRef ref, Camera camera) {
    showDialog(
      context: context,
      builder: (context) => RTSPCameraDialog(
        camera: camera,
        isEditing: true,
      ),
    ).then((result) {
      if (result == true) {
        // Reload cameras after edit
        ref.read(cameraListProvider.notifier).loadCameras();
      }
    });
  }
  
  static void _showDeleteRTSPDialog(BuildContext context, WidgetRef ref, Camera camera) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Camera'),
        content: Text('Are you sure you want to delete ${camera.name}? This action cannot be undone.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () async {
              Navigator.of(context).pop();
              
              // Show loading
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('Deleting camera...')),
              );
              
              final cameraActions = ref.read(cameraActionsProvider);
              final success = await cameraActions.removeRTSPCamera(camera.deviceId);
              
              if (success) {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                    content: Text('Camera deleted successfully'),
                    backgroundColor: Colors.green,
                  ),
                );
              } else {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                    content: Text('Failed to delete camera'),
                    backgroundColor: Colors.red,
                  ),
                );
              }
            },
            style: FilledButton.styleFrom(backgroundColor: Colors.red),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
  }
}

class _StatusIndicator extends ConsumerWidget {
  final Camera camera;

  const _StatusIndicator({required this.camera});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // Watch WebSocket status for this camera
    final status = ref.watch(cameraStatusProvider(camera.deviceId));
    
    Color statusColor;
    IconData statusIcon;
    String tooltip;

    if (status == null) {
      statusColor = Colors.grey;
      statusIcon = Icons.circle;
      tooltip = 'Unknown';
    } else if (status.isConnected) {
      statusColor = Colors.green;
      statusIcon = Icons.circle;
      tooltip = 'Connected';
    } else if (status.isConnecting) {
      statusColor = Colors.orange;
      statusIcon = Icons.circle;
      tooltip = 'Connecting...';
    } else if (status.hasError) {
      statusColor = Colors.red;
      statusIcon = Icons.error;
      tooltip = status.error ?? 'Error';
    } else {
      statusColor = Colors.grey;
      statusIcon = Icons.circle;
      tooltip = 'Disconnected';
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
          const SizedBox(width: 8),
          // Stop recording button
          IconButton(
            onPressed: recordingState.isLoading 
                ? null 
                : () => recordingNotifier.stopRecording(),
            icon: recordingState.isLoading
                ? const SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(strokeWidth: 2.5),
                  )
                : const Icon(Icons.stop_circle, color: Colors.red),
            iconSize: 28,
            padding: const EdgeInsets.all(8),
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
                width: 18,
                height: 18,
                child: CircularProgressIndicator(strokeWidth: 2.5),
              )
            : const Icon(Icons.fiber_manual_record, color: Colors.red),
        iconSize: 28,
        padding: const EdgeInsets.all(8),
        constraints: const BoxConstraints(),
        tooltip: recordingState.isLoading ? 'Starting...' : 'Start recording',
      );
    }
  }
}

/// Recording status row showing timer and info (isolated widget)
/// Updates every second independently without affecting stream widget
class _RecordingStatusRow extends ConsumerWidget {
  final String cameraId;

  const _RecordingStatusRow({required this.cameraId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final recordingState = ref.watch(cameraRecordingProvider(cameraId));
    
    if (!recordingState.isRecording) {
      return const SizedBox.shrink();
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: Colors.red.withOpacity(0.1),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: Colors.red.withOpacity(0.3),
          width: 1,
        ),
      ),
      child: Row(
        children: [
          // Recording indicator
          Container(
            width: 8,
            height: 8,
            decoration: const BoxDecoration(
              color: Colors.red,
              shape: BoxShape.circle,
            ),
          ),
          const SizedBox(width: 8),
          // Status text
          Text(
            'Recording',
            style: TextStyle(
              color: Colors.red,
              fontSize: 12,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(width: 8),
          // Timer (isolated widget that rebuilds independently)
          _RecordingTimer(cameraId: cameraId),
          const Spacer(),
          // Frame count (if available)
          if (recordingState.fileSizeBytes > 0)
            Text(
              '${(recordingState.fileSizeBytes / 1024 / 1024).toStringAsFixed(1)} MB',
              style: TextStyle(
                color: Colors.grey[700],
                fontSize: 11,
              ),
            ),
        ],
      ),
    );
  }
}

/// Recording timer widget that rebuilds every second independently
/// This isolation prevents the timer from triggering stream widget rebuilds
class _RecordingTimer extends StatefulWidget {
  final String cameraId;

  const _RecordingTimer({required this.cameraId});

  @override
  State<_RecordingTimer> createState() => _RecordingTimerState();
}

class _RecordingTimerState extends State<_RecordingTimer> {
  late Timer _timer;
  Duration _elapsed = Duration.zero;

  @override
  void initState() {
    super.initState();
    _timer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (mounted) {
        setState(() {
          _elapsed += const Duration(seconds: 1);
        });
      }
    });
  }

  @override
  void dispose() {
    _timer.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final minutes = _elapsed.inMinutes.toString().padLeft(2, '0');
    final seconds = (_elapsed.inSeconds % 60).toString().padLeft(2, '0');
    
    return Text(
      '$minutes:$seconds',
      style: const TextStyle(
        fontSize: 12,
        fontWeight: FontWeight.w500,
        fontFamily: 'monospace',
      ),
    );
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

/// Connection button widget with loading state
class _ConnectionButton extends ConsumerStatefulWidget {
  final Camera camera;
  
  const _ConnectionButton({required this.camera});
  
  @override
  ConsumerState<_ConnectionButton> createState() => _ConnectionButtonState();
}

class _ConnectionButtonState extends ConsumerState<_ConnectionButton> {
  bool _isLoading = false;
  
  Future<void> _toggleConnection() async {
    if (_isLoading) return;
    
    setState(() => _isLoading = true);
    
    try {
      final cameraService = ref.read(cameraServiceProvider);
      final status = ref.read(cameraStatusProvider(widget.camera.deviceId));
      
      // For mobile and edge cameras, use camera.status since they don't use backend WebSocket
      // For USB/RTSP cameras, use WebSocket status if available, otherwise camera.status
      final isConnected = (widget.camera.type == CameraType.mobile || widget.camera.type == CameraType.edge)
          ? widget.camera.status.toLowerCase() == 'connected'
          : (status?.isConnected ?? widget.camera.status.toLowerCase() == 'connected');
      
      debugPrint('🔌 [ConnectionButton] Toggle check: deviceId=${widget.camera.deviceId}, type=${widget.camera.type}, isConnected=$isConnected');
      
      if (isConnected) {
        // Disconnect
        debugPrint('🔌 [ConnectionButton] Starting disconnect for ${widget.camera.deviceId}');
        await cameraService.disconnectCamera(widget.camera.deviceId);
        debugPrint('🔌 [ConnectionButton] Disconnect API call completed');
        
        // Wait a moment for backend to update status
        debugPrint('⏳ [ConnectionButton] Waiting 500ms for backend status update...');
        await Future.delayed(const Duration(milliseconds: 500));
        
        // Refresh camera list to get updated disconnection status
        debugPrint('🔄 [ConnectionButton] Calling loadCameras() to refresh list...');
        await ref.read(cameraListProvider.notifier).loadCameras();
        debugPrint('✅ [ConnectionButton] Camera disconnected and status refreshed');
      } else {
        // Connect
        debugPrint('🔌 [ConnectionButton] Starting connect for ${widget.camera.deviceId}');
        final success = await cameraService.connectCamera(widget.camera.deviceId);
        debugPrint('🔌 [ConnectionButton] Connect API call completed: success=$success');
        
        if (success) {
          // Wait a moment for backend to update status
          debugPrint('⏳ [ConnectionButton] Waiting 500ms for backend status update...');
          await Future.delayed(const Duration(milliseconds: 500));
          
          // Refresh camera list to get updated connection status
          debugPrint('🔄 [ConnectionButton] Calling loadCameras() to refresh list...');
          await ref.read(cameraListProvider.notifier).loadCameras();
          debugPrint('✅ [ConnectionButton] Camera connected and status refreshed');
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Connection failed: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }
  
  @override
  Widget build(BuildContext context) {
    final status = ref.watch(cameraStatusProvider(widget.camera.deviceId));
    
    // For mobile and edge cameras, use camera.status since they don't use backend WebSocket
    // For USB/RTSP cameras, use WebSocket status if available, otherwise camera.status
    final isConnected = (widget.camera.type == CameraType.mobile || widget.camera.type == CameraType.edge)
        ? widget.camera.status.toLowerCase() == 'connected'
        : (status?.isConnected ?? widget.camera.status.toLowerCase() == 'connected');
    
    if (_isLoading) {
      return Container(
        padding: const EdgeInsets.all(8),
        child: SizedBox(
          width: 28,
          height: 28,
          child: CircularProgressIndicator(
            strokeWidth: 2.5,
            valueColor: AlwaysStoppedAnimation(Colors.blue),
          ),
        ),
      );
    }
    
    return IconButton(
      onPressed: _toggleConnection,
      icon: Icon(
        isConnected ? Icons.link_off : Icons.link,
        color: isConnected ? Colors.red : Colors.green,
      ),
      iconSize: 28,
      padding: const EdgeInsets.all(8),
      constraints: const BoxConstraints(),
      tooltip: isConnected ? 'Disconnect' : 'Connect',
    );
  }
}

/// Stream thumbnail widget for inline preview in camera card
class _StreamThumbnail extends ConsumerWidget {
  final Camera camera;
  
  const _StreamThumbnail({required this.camera});
  
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authService = ref.watch(authServiceProvider);
    
    return FutureBuilder<String?>(
      future: authService.getToken(),
      builder: (context, snapshot) {
        if (!snapshot.hasData) {
          return Container(
            height: 180,
            decoration: BoxDecoration(
              color: Colors.black12,
              borderRadius: BorderRadius.circular(8),
            ),
            child: Center(
              child: CircularProgressIndicator(),
            ),
          );
        }
        
        final token = snapshot.data!;
        final cameraServiceUrl = AppConfig.instance.cameraServiceUrl;
        final streamUrl = '$cameraServiceUrl/api/v1/streaming/${camera.deviceId}/video?token=$token';
        
        return InkWell(
          onTap: () {
            // Navigate to full-screen stream page
            Navigator.of(context).push(
              MaterialPageRoute(
                builder: (context) => CameraStreamPage(camera: camera),
              ),
            );
          },
          child: ClipRRect(
            borderRadius: BorderRadius.circular(8),
            child: Container(
              height: 180,
              decoration: BoxDecoration(
                color: Colors.black,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Image.network(
                streamUrl,
                fit: BoxFit.contain,
                loadingBuilder: (context, child, loadingProgress) {
                  if (loadingProgress == null) return child;
                  return Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        CircularProgressIndicator(
                          value: loadingProgress.expectedTotalBytes != null
                              ? loadingProgress.cumulativeBytesLoaded /
                                  loadingProgress.expectedTotalBytes!
                              : null,
                        ),
                        SizedBox(height: 8),
                        Text(
                          'Loading stream...',
                          style: TextStyle(color: Colors.white70, fontSize: 12),
                        ),
                      ],
                    ),
                  );
                },
                errorBuilder: (context, error, stackTrace) {
                  return Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.error_outline, color: Colors.red, size: 32),
                        SizedBox(height: 8),
                        Text(
                          'Stream unavailable',
                          style: TextStyle(color: Colors.red, fontSize: 12),
                        ),
                      ],
                    ),
                  );
                },
              ),
            ),
          ),
        );
      },
    );
  }
}

/// Edge camera stream controls widget
class _EdgeStreamControls extends ConsumerStatefulWidget {
  final Camera camera;

  const _EdgeStreamControls({required this.camera});

  @override
  ConsumerState<_EdgeStreamControls> createState() => _EdgeStreamControlsState();
}

class _EdgeStreamControlsState extends ConsumerState<_EdgeStreamControls> {
  bool _isLoading = false;
  bool _isStreaming = false; // Track streaming state locally for now

  Future<void> _toggleStreaming() async {
    if (_isLoading) return;

    setState(() => _isLoading = true);

    try {
      final cameraService = ref.read(cameraServiceProvider);

      if (_isStreaming) {
        // Stop streaming
        debugPrint('🛑 [EdgeStreamControls] Stopping stream for ${widget.camera.deviceId}');
        final success = await cameraService.stopEdgeCameraStream(widget.camera.deviceId);
        
        if (success) {
          setState(() => _isStreaming = false);
          debugPrint('✅ [EdgeStreamControls] Stream stopped successfully');
        }
      } else {
        // Start streaming
        debugPrint('🚀 [EdgeStreamControls] Starting stream for ${widget.camera.deviceId}');
        final success = await cameraService.startEdgeCameraStream(widget.camera.deviceId);
        
        if (success) {
          setState(() => _isStreaming = true);
          debugPrint('✅ [EdgeStreamControls] Stream started successfully');
          
          // Navigate to full-screen stream page after starting
          if (mounted) {
            Navigator.of(context).push(
              MaterialPageRoute(
                builder: (context) => CameraStreamPage(camera: widget.camera),
              ),
            );
          }
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Stream control failed: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return Container(
        padding: const EdgeInsets.all(8),
        child: SizedBox(
          width: 28,
          height: 28,
          child: CircularProgressIndicator(
            strokeWidth: 2.5,
            valueColor: AlwaysStoppedAnimation(Colors.blue),
          ),
        ),
      );
    }

    return IconButton(
      onPressed: _toggleStreaming,
      icon: Icon(
        _isStreaming ? Icons.stop : Icons.play_arrow,
        color: _isStreaming ? Colors.red : Colors.green,
      ),
      iconSize: 28,
      padding: const EdgeInsets.all(8),
      constraints: const BoxConstraints(),
      tooltip: _isStreaming ? 'Stop streaming' : 'Start streaming',
    );
  }
}
