import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/providers/camera_providers.dart';
import '../../core/providers/camera_status_providers.dart';
import '../../core/services/camera_status_monitor.dart';
import '../../widgets/camera/camera_monitoring_dashboard.dart';
import '../../widgets/camera/camera_status_card.dart';
import '../../widgets/custom_app_bar.dart';

/// Demo screen for testing real-time camera status monitoring
class CameraMonitoringDemoScreen extends ConsumerStatefulWidget {
  const CameraMonitoringDemoScreen({super.key});

  @override
  ConsumerState<CameraMonitoringDemoScreen> createState() => _CameraMonitoringDemoScreenState();
}

class _CameraMonitoringDemoScreenState extends ConsumerState<CameraMonitoringDemoScreen> {
  @override
  void initState() {
    super.initState();
    // Load cameras when screen initializes
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(cameraListProvider.notifier).loadCameras();
    });
  }

  @override
  Widget build(BuildContext context) {
    final cameraListState = ref.watch(cameraListProvider);
    final activeMonitoringCount = ref.watch(activeMonitoringCountProvider);
    final performanceMetrics = ref.watch(monitoringPerformanceProvider);

    return Scaffold(
      appBar: CustomAppBar(
        title: 'Camera Monitoring Demo',
        subtitle: 'CAM-FLUTTER-005 Real-Time Status Updates',
        actions: [
          // Status overview
          if (activeMonitoringCount > 0) 
            const Padding(
              padding: EdgeInsets.symmetric(horizontal: 8),
              child: CameraStatusOverview(),
            ),
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () {
              ref.read(cameraListProvider.notifier).loadCameras();
            },
            tooltip: 'Refresh cameras',
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Real-time monitoring dashboard
            const CameraMonitoringDashboard(),
            
            const SizedBox(height: 24),
            
            // Feature showcase header
            Row(
              children: [
                Icon(
                  Icons.star,
                  color: Colors.amber,
                  size: 24,
                ),
                const SizedBox(width: 8),
                Text(
                  'CAM-FLUTTER-005 Features',
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            
            const SizedBox(height: 16),
            
            // Feature cards
            _buildFeatureCard(
              context,
              'Real-time Status Updates',
              'Monitor camera connection status with automatic polling',
              Icons.update,
              Colors.blue,
            ),
            
            const SizedBox(height: 12),
            
            _buildFeatureCard(
              context,
              'Connection Health Monitoring',
              'Track latency and connection quality with visual indicators',
              Icons.health_and_safety,
              Colors.green,
            ),
            
            const SizedBox(height: 12),
            
            _buildFeatureCard(
              context,
              'Battery-Optimized Intervals',
              'Active (2s), Idle (10s), Background (30s) polling modes',
              Icons.battery_saver,
              Colors.orange,
            ),
            
            const SizedBox(height: 12),
            
            _buildFeatureCard(
              context,
              'Automatic Reconnection',
              'Exponential backoff retry logic for dropped connections',
              Icons.refresh,
              Colors.purple,
            ),
            
            const SizedBox(height: 24),
            
            // Demo controls
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Demo Controls',
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 16),
                    
                    // Quick action buttons
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        ElevatedButton.icon(
                          onPressed: cameraListState.cameras.isEmpty ? null : () {
                            final deviceIds = cameraListState.cameras.map((c) => c.deviceId).toList();
                            ref.read(cameraMonitoringProvider.notifier)
                                .startMonitoringMultiple(deviceIds, mode: MonitoringMode.active);
                            _showSnackBar('Started active monitoring for ${deviceIds.length} cameras');
                          },
                          icon: Icon(Icons.flash_on),
                          label: Text('Start Active Mode'),
                          style: ElevatedButton.styleFrom(
                            foregroundColor: Colors.green,
                          ),
                        ),
                        
                        ElevatedButton.icon(
                          onPressed: activeMonitoringCount == 0 ? null : () {
                            ref.read(cameraMonitoringProvider.notifier).optimizeForBackground();
                            _showSnackBar('Switched to battery-optimized mode');
                          },
                          icon: Icon(Icons.battery_saver),
                          label: Text('Battery Mode'),
                          style: ElevatedButton.styleFrom(
                            foregroundColor: Colors.blue,
                          ),
                        ),
                        
                        ElevatedButton.icon(
                          onPressed: activeMonitoringCount == 0 ? null : () {
                            ref.read(cameraMonitoringProvider.notifier).optimizeForForeground();
                            _showSnackBar('Switched to foreground mode');
                          },
                          icon: Icon(Icons.smartphone),
                          label: Text('Foreground Mode'),
                          style: ElevatedButton.styleFrom(
                            foregroundColor: Colors.orange,
                          ),
                        ),
                        
                        ElevatedButton.icon(
                          onPressed: activeMonitoringCount == 0 ? null : () {
                            ref.read(cameraMonitoringProvider.notifier).stopAllMonitoring();
                            _showSnackBar('Stopped all monitoring');
                          },
                          icon: Icon(Icons.stop),
                          label: Text('Stop All'),
                          style: ElevatedButton.styleFrom(
                            foregroundColor: Colors.red,
                          ),
                        ),
                      ],
                    ),
                    
                    const SizedBox(height: 16),
                    
                    // Performance metrics display
                    if (activeMonitoringCount > 0) ...[
                      const Divider(),
                      const SizedBox(height: 16),
                      Text(
                        'Performance Metrics',
                        style: Theme.of(context).textTheme.titleSmall?.copyWith(
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Row(
                        children: [
                          _MetricChip(
                            label: 'Active Monitors',
                            value: activeMonitoringCount.toString(),
                            color: Colors.purple,
                          ),
                          const SizedBox(width: 8),
                          _MetricChip(
                            label: 'Health',
                            value: '${performanceMetrics['health_percentage'] ?? 0}%',
                            color: (performanceMetrics['health_percentage'] ?? 0) >= 80 
                                ? Colors.green : Colors.orange,
                          ),
                          const SizedBox(width: 8),
                          _MetricChip(
                            label: 'Avg Latency',
                            value: '${performanceMetrics['average_latency_ms'] ?? 0}ms',
                            color: (performanceMetrics['average_latency_ms'] ?? 0) <= 100 
                                ? Colors.green : Colors.orange,
                          ),
                        ],
                      ),
                    ],
                  ],
                ),
              ),
            ),
            
            const SizedBox(height: 24),
            
            // Camera list with real-time status
            if (cameraListState.cameras.isNotEmpty) ...[
              Text(
                'Camera Status Cards',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 16),
              
              ...cameraListState.cameras.map((camera) => Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: CameraStatusCard(
                  deviceId: camera.deviceId,
                  cameraName: camera.name,
                  compact: false,
                ),
              )),
            ] else ...[
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(24),
                  child: Column(
                    children: [
                      Icon(
                        Icons.videocam_off,
                        size: 48,
                        color: Theme.of(context).colorScheme.outline,
                      ),
                      const SizedBox(height: 16),
                      Text(
                        'No cameras available',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'Detect cameras first to see real-time monitoring in action',
                        textAlign: TextAlign.center,
                        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                          color: Theme.of(context).colorScheme.outline,
                        ),
                      ),
                      const SizedBox(height: 16),
                      ElevatedButton.icon(
                        onPressed: cameraListState.isDetecting ? null : () {
                          ref.read(cameraListProvider.notifier).detectCameras();
                        },
                        icon: cameraListState.isDetecting
                            ? SizedBox(
                                width: 16,
                                height: 16,
                                child: CircularProgressIndicator(strokeWidth: 2),
                              )
                            : Icon(Icons.search),
                        label: Text(
                          cameraListState.isDetecting ? 'Detecting...' : 'Detect Cameras',
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildFeatureCard(
    BuildContext context,
    String title,
    String description,
    IconData icon,
    Color color,
  ) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            Container(
              width: 48,
              height: 48,
              decoration: BoxDecoration(
                color: color.withOpacity(0.1),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Icon(
                icon,
                color: color,
                size: 24,
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: Theme.of(context).textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    description,
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: Theme.of(context).colorScheme.outline,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  void _showSnackBar(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        duration: const Duration(seconds: 2),
      ),
    );
  }
}

/// Small metric display chip
class _MetricChip extends StatelessWidget {
  final String label;
  final String value;
  final Color color;

  const _MetricChip({
    required this.label,
    required this.value,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            value,
            style: Theme.of(context).textTheme.labelMedium?.copyWith(
              color: color,
              fontWeight: FontWeight.bold,
            ),
          ),
          Text(
            label,
            style: Theme.of(context).textTheme.labelSmall?.copyWith(
              color: color,
              fontSize: 10,
            ),
          ),
        ],
      ),
    );
  }
}
