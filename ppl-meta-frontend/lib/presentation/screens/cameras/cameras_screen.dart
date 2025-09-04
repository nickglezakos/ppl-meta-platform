import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../utils/offline_fonts.dart';
import '../../../core/providers/camera_providers.dart';
import '../../../core/providers/camera_status_providers.dart';
import '../../../core/theme/app_theme.dart';
import '../../../widgets/camera/camera_card.dart';
import '../../../widgets/camera/camera_monitoring_dashboard.dart';
import '../../../widgets/custom_app_bar.dart';

/// Enhanced cameras screen with real-time status monitoring
class CamerasScreen extends ConsumerStatefulWidget {
  const CamerasScreen({super.key});

  @override
  ConsumerState<CamerasScreen> createState() => _CamerasScreenState();
}

class _CamerasScreenState extends ConsumerState<CamerasScreen> {
  bool _showMonitoringDashboard = false;
  bool _showLiveStreams = true; // Enable streaming by default

  @override
  Widget build(BuildContext context) {
    final cameraListState = ref.watch(cameraListProvider);
    final monitoringEnabled = ref.watch(isMonitoringEnabledProvider);

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: CustomAppBar(
        title: 'Cameras',
        actions: [
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
          
          // Monitoring dashboard toggle
          IconButton(
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
          ),
          
          // Global monitoring toggle
          IconButton(
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
          ),
          
          // Refresh cameras
          IconButton(
            onPressed: () {
              ref.read(cameraListProvider.notifier).loadCameras();
            },
            icon: Icon(
              Icons.refresh,
              color: AppColors.primary,
            ),
            tooltip: 'Refresh Cameras',
          ),
        ],
      ),
      body: Column(
        children: [
          // Monitoring dashboard
          if (_showMonitoringDashboard) ...[
            Container(
              color: AppColors.surface,
              child: const CameraMonitoringDashboard(),
            ),
            const Divider(height: 1),
          ],
          
          // Cameras list
          Expanded(
            child: _buildCamerasContent(cameraListState),
          ),
        ],
      ),
      // Removed floating action button for detect cameras as per user request
      // floatingActionButton: FloatingActionButton.extended(
      //   onPressed: () {
      //     _showDetectCamerasDialog();
      //   },
      //   icon: const Icon(Icons.camera_alt),
      //   label: const Text('Detect Cameras'),
      //   backgroundColor: AppColors.primary,
      //   foregroundColor: Colors.white,
      // ),
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

  Widget _buildCamerasList(List<dynamic> cameras) {
    if (cameras.isEmpty) {
      return _buildEmptyState();
    }

    return RefreshIndicator(
      onRefresh: () async {
        ref.read(cameraListProvider.notifier).loadCameras();
      },
      child: ListView.builder(
        padding: const EdgeInsets.all(16),
        itemCount: cameras.length,
        itemBuilder: (context, index) {
          final camera = cameras[index];
          return Padding(
            padding: const EdgeInsets.only(bottom: 16),
            child: CameraCard(
              camera: camera,
              showStream: _showLiveStreams,
            ),
          );
        },
      ),
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
              ref.read(cameraListProvider.notifier).loadCameras();
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
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(
                      content: Text('Camera detection completed!'),
                      backgroundColor: Colors.green,
                    ),
                  );
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
