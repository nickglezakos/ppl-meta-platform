import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../utils/offline_fonts.dart';
import '../../../core/models/camera.dart';
import '../../../core/providers/camera_providers.dart';
import '../../../core/providers/camera_status_providers.dart';
import '../../../core/theme/app_theme.dart';
import '../../widgets/camera/camera_card.dart';
import '../../widgets/camera/rtsp_camera_dialog.dart';
import '../../widgets/camera/add_edge_camera_dialog.dart';
import '../../../widgets/custom_app_bar.dart';
import '../../../widgets/automatic_face_detection_status.dart';
import 'multi_stream_page.dart';

/// Enhanced cameras screen with real-time status monitoring
class CamerasScreen extends ConsumerStatefulWidget {
  const CamerasScreen({super.key});

  @override
  ConsumerState<CamerasScreen> createState() => _CamerasScreenState();
}

class _CamerasScreenState extends ConsumerState<CamerasScreen> {
  // REMOVED: bool _showMonitoringDashboard = false; // Complex monitoring dashboard removed
  bool _showLiveStreams = false; // Disable streaming by default to prevent auto-connection
  bool _showArchivedCameras = false; // Toggle to show/hide archived cameras

  @override
  void initState() {
    super.initState();
    // Load cameras when screen opens
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(cameraListProvider.notifier).loadCameras(includeArchived: _showArchivedCameras);
    });
  }

  @override
  Widget build(BuildContext context) {
    final cameraListState = ref.watch(cameraListProvider);

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: CustomAppBar(
        title: 'Cameras',
        actions: [
          // Multi-stream viewer button
          IconButton(
            onPressed: () {
              final connectedCameras = cameraListState.cameras.where((camera) {
                final status = ref.read(cameraStatusProvider(camera.deviceId));
                return status?.isConnected ?? false;
              }).toList();
              
              if (connectedCameras.isEmpty) {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                    content: Text('No connected cameras. Connect cameras first to view streams.'),
                    duration: Duration(seconds: 3),
                  ),
                );
                return;
              }
              
              Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (context) => MultiStreamPage(cameras: cameraListState.cameras),
                ),
              );
            },
            icon: const Icon(Icons.view_comfy),
            color: AppColors.primary,
            tooltip: 'View All Streams',
          ),
          
          // Live streaming toggle
          IconButton(
            onPressed: () {
              setState(() {
                _showLiveStreams = !_showLiveStreams;
              });
            },
            icon: Icon(
              _showLiveStreams ? Icons.videocam : Icons.videocam_off,
              color: _showLiveStreams ? Colors.green : AppColors.textSecondary,
            ),
            tooltip: _showLiveStreams ? 'Hide Live Streams' : 'Show Live Streams',
          ),
          
          // Toggle archived cameras visibility
          IconButton(
            onPressed: () {
              setState(() {
                _showArchivedCameras = !_showArchivedCameras;
              });
              // Reload cameras with updated filter
              ref.read(cameraListProvider.notifier).loadCameras(includeArchived: _showArchivedCameras);
            },
            icon: Icon(
              Icons.archive,
              color: _showArchivedCameras ? Colors.orange : AppColors.textSecondary,
            ),
            tooltip: _showArchivedCameras ? 'Hide Archived Cameras' : 'Show Archived Cameras',
          ),
          
          // Toggle monitoring dashboard - DISABLED (complex monitoring removed)
          /* IconButton(
            onPressed: () {
              setState(() {
                _showMonitoringDashboard = !_showMonitoringDashboard;
              });
            },
            icon: Icon(
              _showMonitoringDashboard ? Icons.dashboard : Icons.dashboard_outlined,
              color: AppColors.primary,
            ),
            tooltip: 'Toggle Monitoring Dashboard',
          ), */
          
          // Global monitoring toggle - DISABLED (complex monitoring removed)
          /* IconButton(
            onPressed: () {
              if (monitoringEnabled) {
                ref.read(cameraMonitoringProvider.notifier).stopAllMonitoring();
              } else {
                // Start monitoring for all cameras
                for (final camera in cameraListState.cameras) {
                  ref.read(cameraMonitoringProvider.notifier).startMonitoring(camera.deviceId);
                }
              }
            },
            icon: Icon(
              monitoringEnabled ? Icons.monitor : Icons.monitor_outlined,
              color: monitoringEnabled ? Colors.green : AppColors.textSecondary,
            ),
            tooltip: monitoringEnabled ? 'Stop All Monitoring' : 'Start All Monitoring',
          ), */
          
          // Refresh cameras
          IconButton(
            onPressed: () {
              ref.read(cameraListProvider.notifier).loadCameras(includeArchived: _showArchivedCameras);
            },
            icon: Icon(
              Icons.refresh,
              color: AppColors.primary,
            ),
            tooltip: 'Refresh Cameras',
          ),
          
          // Add RTSP Camera
          IconButton(
            onPressed: () {
              showDialog(
                context: context,
                builder: (context) => const RTSPCameraDialog(
                  isEditing: false,
                ),
              ).then((result) {
                if (result == true) {
                  // Reload cameras after adding
                  ref.read(cameraListProvider.notifier).loadCameras(includeArchived: _showArchivedCameras);
                }
              });
            },
            icon: Icon(
              Icons.add,
              color: AppColors.primary,
            ),
            tooltip: 'Add RTSP Camera',
          ),
          
          // Add Edge Camera
          IconButton(
            onPressed: () {
              showDialog(
                context: context,
                builder: (context) => const AddEdgeCameraDialog(),
              ).then((result) {
                if (result == true) {
                  // Reload cameras after adding
                  ref.read(cameraListProvider.notifier).loadCameras();
                }
              });
            },
            icon: Icon(
              Icons.camera_outdoor,
              color: AppColors.accent,
            ),
            tooltip: 'Add Edge Camera',
          ),
        ],
      ),
      body: Column(
        children: [
          // REMOVED: Monitoring dashboard (complex monitoring removed)
          /* if (_showMonitoringDashboard) ...[
            Container(
              height: 240,
              child: const CameraMonitoringDashboard(),
            ),
            const Divider(height: 1),
            
            // NEW: Automatic Face Detection Status
            const AutomaticFaceDetectionStatus(),
          ], */
          
          // Cameras list
          Expanded(
            child: _buildCamerasContent(cameraListState),
          ),
        ],
      ),
    );
  }

  Widget _buildCamerasContent(CameraListState cameraListState) {
    if (cameraListState.isLoading) {
      return const Center(
        child: CircularProgressIndicator(),
      );
    }
    
    if (cameraListState.error != null) {
      return _buildErrorView(cameraListState.error!);
    }
    
    return _buildCamerasList(cameraListState.cameras);
  }

  Widget _buildCamerasList(List<Camera> cameras) {
    if (cameras.isEmpty) {
      return _buildEmptyState();
    }

    return RefreshIndicator(
      onRefresh: () async {
        ref.read(cameraListProvider.notifier).loadCameras(includeArchived: _showArchivedCameras);
      },
      child: LayoutBuilder(
        builder: (context, constraints) {
          final isWide = constraints.maxWidth >= 700;
          return CustomScrollView(
            slivers: [
              SliverPadding(
                padding: const EdgeInsets.fromLTRB(16, 16, 16, 0),
                sliver: SliverToBoxAdapter(
                  child: Text(
                    'Cameras',
                    style: OfflineFonts.inter(
                      fontSize: 20,
                      fontWeight: FontWeight.bold,
                      color: AppColors.textPrimary,
                    ),
                  ),
                ),
              ),
              if (isWide)
                SliverPadding(
                  padding: const EdgeInsets.all(16),
                  sliver: SliverGrid(
                    gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                      crossAxisCount: 2,
                      mainAxisSpacing: 16,
                      crossAxisSpacing: 16,
                      childAspectRatio: 1.6,
                    ),
                    delegate: SliverChildBuilderDelegate(
                      (context, index) => CameraCard(
                        camera: cameras[index],
                        onTap: () {
                          context.go('/cameras/${cameras[index].deviceId}');
                        },
                      ),
                      childCount: cameras.length,
                    ),
                  ),
                )
              else
                SliverPadding(
                  padding: const EdgeInsets.all(16),
                  sliver: SliverList(
                    delegate: SliverChildBuilderDelegate(
                      (context, index) => Padding(
                        padding: const EdgeInsets.only(bottom: 16),
                        child: CameraCard(
                          camera: cameras[index],
                          onTap: () {
                            context.go('/cameras/${cameras[index].deviceId}');
                          },
                        ),
                      ),
                      childCount: cameras.length,
                    ),
                  ),
                ),
            ],
          );
        },
      ),
    );
  }

  Widget _buildInfoChip({required IconData icon, required String label}) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 16, color: AppColors.textSecondary),
        const SizedBox(width: 4),
        Text(
          label,
          style: OfflineFonts.inter(
            fontSize: 12,
            color: AppColors.textSecondary,
          ),
        ),
      ],
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.camera_alt_outlined,
            size: 64,
            color: AppColors.textSecondary.withOpacity(0.5),
          ),
          const SizedBox(height: 16),
          Text(
            'No cameras detected',
            style: OfflineFonts.inter(
              fontSize: 18,
              fontWeight: FontWeight.w500,
              color: AppColors.textSecondary,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'Connect cameras and tap "Detect Cameras" to get started',
            style: OfflineFonts.inter(
              fontSize: 14,
              color: AppColors.textSecondary.withOpacity(0.7),
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 24),
          ElevatedButton.icon(
            onPressed: _showDetectCamerasDialog,
            icon: const Icon(Icons.camera_alt),
            label: const Text('Detect Cameras'),
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.primary,
              foregroundColor: Colors.white,
              padding: const EdgeInsets.symmetric(
                horizontal: 24,
                vertical: 12,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildErrorView(String error) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.error_outline,
            size: 64,
            color: Colors.red.withOpacity(0.7),
          ),
          const SizedBox(height: 16),
          Text(
            'Error loading cameras',
            style: OfflineFonts.inter(
              fontSize: 18,
              fontWeight: FontWeight.w500,
              color: Colors.red,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            error.toString(),
            style: OfflineFonts.inter(
              fontSize: 14,
              color: AppColors.textSecondary,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 24),
          ElevatedButton.icon(
            onPressed: () {
              ref.read(cameraListProvider.notifier).loadCameras(includeArchived: _showArchivedCameras);
            },
            icon: const Icon(Icons.refresh),
            label: const Text('Retry'),
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.primary,
              foregroundColor: Colors.white,
            ),
          ),
        ],
      ),
    );
  }

  void _showDetectCamerasDialog() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Detect Cameras'),
        content: const Text(
          'This will scan for connected cameras and update the camera list. '
          'Make sure your cameras are properly connected.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () async {
              Navigator.of(context).pop();
              try {
                await ref.read(cameraListProvider.notifier).detectCameras(saveToDb: true);
                
                if (mounted) {
                  final cameras = ref.read(cameraListProvider).cameras;
                  if (cameras.isEmpty) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(
                        content: Text('No cameras detected. Check backend logs for errors.'),
                        backgroundColor: Colors.orange,
                        duration: Duration(seconds: 5),
                      ),
                    );
                  } else {
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(
                        content: Text('Detected ${cameras.length} camera(s)!'),
                        backgroundColor: Colors.green,
                      ),
                    );
                  }
                }
              } catch (e) {
                if (mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(
                      content: Text('Detection failed: $e'),
                      backgroundColor: Colors.red,
                    ),
                  );
                }
              }
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.primary,
              foregroundColor: Colors.white,
            ),
            child: const Text('Detect'),
          ),
        ],
      ),
    );
  }
}
