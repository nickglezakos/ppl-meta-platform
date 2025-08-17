import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../core/services/camera_service.dart';
import '../../../core/services/collection_detection_helper.dart';
import '../../../core/providers/camera_providers.dart';
import '../../../core/models/camera.dart';
import '../../widgets/common/error_widget.dart';
import '../../widgets/camera/camera_stream_player_simple.dart';
import '../../widgets/camera/camera_controls.dart';
import '../../widgets/camera/streaming_controls.dart';
import '../../widgets/camera/snapshot_capture_button.dart';
import '../../widgets/camera/snapshot_gallery_widget.dart';
import '../camera/snapshot_gallery_screen.dart';
import '../../../widgets/custom_app_bar.dart';

class CameraDetailScreen extends ConsumerStatefulWidget {
  final String cameraId;

  const CameraDetailScreen({
    super.key,
    required this.cameraId,
  });

  @override
  ConsumerState<CameraDetailScreen> createState() => _CameraDetailScreenState();
}

class _CameraDetailScreenState extends ConsumerState<CameraDetailScreen> {
  // Streaming settings state
  String _streamQuality = 'high';
  int _streamFps = 30;
  String _streamResolution = '1280x720';
  bool _hasInitializedStatus = false;
  
  @override
  void initState() {
    super.initState();
    // Note: We'll get streaming status after camera data is loaded
  }

  @override
  Widget build(BuildContext context) {
    final cameraAsync = ref.watch(cameraByIdProvider(widget.cameraId));
    final streamState = ref.watch(cameraStreamProvider);
    final snapshotState = ref.watch(cameraSnapshotProvider);

    return cameraAsync.when(
      loading: () => const Scaffold(
        appBar: CustomAppBar(title: 'Camera'),
        body: Center(child: CircularProgressIndicator()),
      ),
      error: (error, stack) => Scaffold(
        appBar: const CustomAppBar(title: 'Camera'),
        body: Center(
          child: Text('Error loading camera: $error'),
        ),
      ),
      data: (camera) {
        if (camera == null) {
          return const Scaffold(
            appBar: CustomAppBar(title: 'Camera'),
            body: Center(
              child: Text('Camera not found'),
            ),
          );
        }

        // Get streaming status when camera data is available (only once)
        if (!_hasInitializedStatus) {
          _hasInitializedStatus = true;
          WidgetsBinding.instance.addPostFrameCallback((_) {
            ref.read(cameraStreamProvider.notifier).getStreamingStatus(camera.deviceId);
          });
        }

        return Scaffold(
          appBar: CustomAppBar(
            title: camera.name,
            actions: [
              // View Collection button
              Consumer(
                builder: (context, ref, child) {
                  final hasCollection = ref.watch(cameraHasCollectionProvider(camera.deviceId));
                  return hasCollection.when(
                    data: (hasCollection) {
                      if (hasCollection) {
                        return IconButton(
                          onPressed: () => _navigateToCollection(ref, camera.deviceId),
                          icon: const Icon(Icons.folder),
                          tooltip: 'View collection',
                        );
                      } else {
                        return IconButton(
                          onPressed: () => _createCameraCollection(ref, camera),
                          icon: const Icon(Icons.create_new_folder),
                          tooltip: 'Create collection',
                        );
                      }
                    },
                    loading: () => const SizedBox(
                      width: 24,
                      height: 24,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    ),
                    error: (_, __) => const SizedBox.shrink(),
                  );
                },
              ),
              // Debug: Manual mapping button for USB Camera 0 (hidden in production)
              // Uncomment this for troubleshooting collection detection issues
              /*
              if (camera.deviceId == 'usb_camera_0')
                IconButton(
                  onPressed: () => _createManualMapping(ref),
                  icon: const Icon(Icons.link, color: Colors.orange),
                  tooltip: 'Manual mapping (debug)',
                ),
              */
              // Settings button
              IconButton(
                onPressed: () {
                  _showCameraSettings(context, camera);
                },
                icon: const Icon(Icons.settings),
                tooltip: 'Camera settings',
              ),
            ],
          ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Camera Info Card
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(
                          Icons.info_outline,
                          color: Theme.of(context).colorScheme.primary,
                        ),
                        const SizedBox(width: 8),
                        Text(
                          'Camera Information',
                          style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 16),
                    _infoRow('Device ID', camera.deviceId),
                    if (camera.manufacturer != null)
                      _infoRow('Manufacturer', camera.manufacturer!),
                    if (camera.model != null)
                      _infoRow('Model', camera.model!),
                    if (camera.resolution != null)
                      _infoRow('Resolution', camera.resolution!),
                    _infoRow('Status', camera.status),
                    _infoRow('Active', camera.isActive ? 'Yes' : 'No'),
                    if (camera.lastSeen != null)
                      _infoRow('Last Seen', _formatDateTime(camera.lastSeen!)),
                  ],
                ),
              ),
            ),

            const SizedBox(height: 16),

            // Stream Section
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(
                          Icons.play_circle_outline,
                          color: Theme.of(context).colorScheme.primary,
                        ),
                        const SizedBox(width: 8),
                        Text(
                          'Live Stream',
                          style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        const Spacer(),
                        if (streamState.isStreaming)
                          Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 8,
                              vertical: 4,
                            ),
                            decoration: BoxDecoration(
                              color: Colors.red.withValues(alpha: 0.1),
                              borderRadius: BorderRadius.circular(12),
                              border: Border.all(color: Colors.red.withValues(alpha: 0.3)),
                            ),
                            child: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Icon(
                                  Icons.circle,
                                  color: Colors.red,
                                  size: 8,
                                ),
                                const SizedBox(width: 4),
                                Text(
                                  'LIVE',
                                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                                    color: Colors.red,
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                              ],
                            ),
                          ),
                      ],
                    ),
                    const SizedBox(height: 16),
                    
                    // Stream Player
                    if (streamState.streamUrl != null)
                      CameraStreamPlayerSimple(
                        cameraId: camera.deviceId,
                        height: 300,
                      )
                    else
                      Container(
                        height: 200,
                        decoration: BoxDecoration(
                          color: Theme.of(context).colorScheme.surface,
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(
                            color: Theme.of(context).colorScheme.outline.withValues(alpha: 0.2),
                          ),
                        ),
                        child: Center(
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Icon(
                                Icons.videocam_off,
                                size: 48,
                                color: Theme.of(context).colorScheme.outline,
                              ),
                              const SizedBox(height: 8),
                              Text(
                                'No stream available',
                                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                                  color: Theme.of(context).colorScheme.outline,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),

                    const SizedBox(height: 16),

                    // Streaming Settings
                    StreamingControls(
                      quality: _streamQuality,
                      fps: _streamFps,
                      resolution: _streamResolution,
                      isEnabled: !streamState.isStreaming,
                      onSettingsChanged: (settings) {
                        setState(() {
                          _streamQuality = settings['quality'];
                          _streamFps = settings['fps'];
                          _streamResolution = settings['resolution'];
                        });
                      },
                    ),

                    const SizedBox(height: 16),

                    // Stream Controls
                    CameraControls(
                      camera: camera,
                      streamState: streamState,
                      onStartStream: () async {
                        // First connect to the camera
                        final cameraService = ref.read(cameraServiceProvider);
                        final connected = await cameraService.connectCamera(camera.deviceId);
                        
                        if (connected) {
                          // If connection successful, start streaming
                          ref.read(cameraStreamProvider.notifier).startStreaming(
                            camera.deviceId,
                            quality: _streamQuality,
                          );
                        } else {
                          // Show error if connection failed
                          if (context.mounted) {
                            ScaffoldMessenger.of(context).showSnackBar(
                              SnackBar(
                                content: Text('Failed to connect to camera ${camera.name}'),
                                backgroundColor: Colors.red,
                              ),
                            );
                          }
                        }
                      },
                      onStopStream: () {
                        ref.read(cameraStreamProvider.notifier).stopStreaming(camera.deviceId);
                      },
                    ),

                    const SizedBox(height: 16),

                    // Enhanced Snapshot Controls
                    Card(
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                Icon(
                                  Icons.camera_alt,
                                  color: Theme.of(context).colorScheme.primary,
                                ),
                                const SizedBox(width: 8),
                                Text(
                                  'High-Resolution Snapshots',
                                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 8),
                            Text(
                              'Capture high-quality snapshots independent of streaming resolution',
                              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                                color: Theme.of(context).colorScheme.onSurface.withOpacity(0.7),
                              ),
                            ),
                            const SizedBox(height: 16),
                            Row(
                              children: [
                                Expanded(
                                  child: SnapshotCaptureButton(
                                    cameraId: camera.deviceId,
                                    onSnapshotCaptured: () {
                                      // Optional: Refresh any gallery widgets
                                      setState(() {});
                                    },
                                  ),
                                ),
                                const SizedBox(width: 16),
                                Expanded(
                                  child: ElevatedButton.icon(
                                    onPressed: () {
                                      Navigator.of(context).push(
                                        MaterialPageRoute(
                                          builder: (context) => SnapshotGalleryScreen(
                                            cameraId: camera.deviceId,
                                            title: '${camera.name} Snapshots',
                                          ),
                                        ),
                                      );
                                    },
                                    icon: const Icon(Icons.photo_library),
                                    label: const Text('Gallery'),
                                    style: ElevatedButton.styleFrom(
                                      padding: const EdgeInsets.symmetric(
                                        horizontal: 16,
                                        vertical: 12,
                                      ),
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),

            const SizedBox(height: 16),

            // Error Display
            if (streamState.error != null)
              ErrorDisplayWidget(
                message: streamState.error!,
                onRetry: () {
                  ref.read(cameraStreamProvider.notifier).clearError();
                },
              ),

            if (snapshotState.error != null)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: ErrorDisplayWidget(
                  message: snapshotState.error!,
                  onRetry: () {
                    ref.read(cameraSnapshotProvider.notifier).clearError();
                  },
                ),
              ),

          ], // End of children array for Column
        ), // End of Column
      ), // End of SingleChildScrollView
    ); // End of Scaffold
      }, // End of data callback for .when()
    ); // End of .when() method call
  } // End of build method

  Widget _infoRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 120,
            child: Text(
              label,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ),
        ],
      ),
    );
  }

  String _formatDateTime(DateTime dateTime) {
    return '${dateTime.day}/${dateTime.month}/${dateTime.year} ${dateTime.hour}:${dateTime.minute.toString().padLeft(2, '0')}';
  }

  void _showCameraSettings(BuildContext context, Camera camera) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('${camera.name} Settings'),
        content: const Text('Camera settings will be available in the next update.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Close'),
          ),
        ],
      ),
    );
  }

  /// Navigate to the camera's collection
  void _navigateToCollection(WidgetRef ref, String cameraId) async {
    try {
      final collectionId = await ref.read(cameraCollectionIdProvider(cameraId).future);
      if (collectionId != null && mounted) {
        // Navigate to collections screen with collection ID as query parameter
        context.go('/collections?collectionId=$collectionId');
      } else {
        _showSnackBar('Collection not found for this camera.');
      }
    } catch (e) {
      _showSnackBar('Error accessing camera collection: ${e.toString()}');
    }
  }

  /// Create a collection for the camera
  void _createCameraCollection(WidgetRef ref, Camera camera) async {
    try {
      final collectionService = ref.read(cameraCollectionServiceProvider);
      await collectionService.setupCameraWithCollection(camera);
      
      // Refresh the collection status
      ref.invalidate(cameraHasCollectionProvider(camera.deviceId));
      
      _showSnackBar('Collection created for ${camera.name}');
    } catch (e) {
      _showSnackBar('Error creating collection: ${e.toString()}');
    }
  }

  /// Show a snackbar message
  void _showSnackBar(String message) {
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(message),
          duration: const Duration(seconds: 3),
        ),
      );
    }
  }

  /// Create manual mapping for USB Camera 0 (debug function)
  Future<void> _createManualMapping(WidgetRef ref) async {
    if (widget.cameraId != 'usb_camera_0') return;
    
    try {
      final success = await CollectionDetectionHelper.createUsbCameraMapping();
      
      if (success) {
        // Force refresh of collection detection state
        ref.invalidate(cameraHasCollectionProvider(widget.cameraId));
        
        _showSnackBar('Manual mapping created for USB Camera 0');
      } else {
        _showSnackBar('Failed to create manual mapping');
      }
    } catch (e) {
      print('Manual mapping error: $e');
      _showSnackBar('Error: $e');
    }
  }
}
