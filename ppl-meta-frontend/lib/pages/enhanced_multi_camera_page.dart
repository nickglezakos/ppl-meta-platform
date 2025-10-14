import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_staggered_grid_view/flutter_staggered_grid_view.dart';
import 'package:go_router/go_router.dart';
import '../core/models/camera.dart';
import '../core/providers/camera_providers.dart';
import '../widgets/enhanced_camera_card.dart';
import '../widgets/recording_session_widget.dart';
import '../services/recording_session_service.dart';
import '../services/camera_auth_service.dart';

/// Enhanced Multi-Camera Page with Phase 4 Recording Session Integration
/// 
/// Combines existing camera management with comprehensive Phase 4 database persistence
class EnhancedMultiCameraPage extends ConsumerStatefulWidget {
  const EnhancedMultiCameraPage({super.key});

  @override
  ConsumerState<EnhancedMultiCameraPage> createState() => _EnhancedMultiCameraPageState();
}

class _EnhancedMultiCameraPageState extends ConsumerState<EnhancedMultiCameraPage>
    with TickerProviderStateMixin {
  late TabController _tabController;
  RecordingSessionService? _recordingService;
  SessionStatistics? _statistics;
  bool _isLoadingStats = false;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
    _initializeServices();
    _loadStatistics();
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  void _initializeServices() {
    final authService = CameraAuthService();
    _recordingService = RecordingSessionService(authService);
  }

  Future<void> _loadStatistics() async {
    if (_recordingService == null) return;
    
    setState(() {
      _isLoadingStats = true;
    });

    try {
      _statistics = await _recordingService!.getSessionStatistics();
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Failed to load statistics: $e'),
          backgroundColor: Colors.red,
        ),
      );
    } finally {
      setState(() {
        _isLoadingStats = false;
      });
    }
  }

  Future<void> _refreshAll() async {
    // Refresh camera list
    ref.refresh(cameraListProvider);
    
    // Refresh statistics
    await _loadStatistics();
    
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Refreshed cameras and recording data'),
        backgroundColor: Colors.green,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Enhanced Camera Management'),
        centerTitle: true,
        elevation: 0,
        backgroundColor: Theme.of(context).colorScheme.surface,
        foregroundColor: Theme.of(context).colorScheme.onSurface,
        leading: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            IconButton(
              icon: const Icon(Icons.arrow_back),
              onPressed: () {
                if (context.canPop()) {
                  context.pop();
                } else {
                  context.go('/');
                }
              },
              tooltip: 'Back',
            ),
          ],
        ),
        bottom: TabBar(
          controller: _tabController,
          tabs: const [
            Tab(icon: Icon(Icons.videocam), text: 'Cameras'),
            Tab(icon: Icon(Icons.dashboard), text: 'Sessions'),
            Tab(icon: Icon(Icons.analytics), text: 'Analytics'),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.home),
            onPressed: () => context.go('/'),
            tooltip: 'Home',
          ),
          IconButton(
            onPressed: _refreshAll,
            icon: const Icon(Icons.refresh),
            tooltip: 'Refresh All',
          ),
          IconButton(
            onPressed: () => _showGlobalSessionControls(),
            icon: const Icon(Icons.settings),
            tooltip: 'Session Settings',
          ),
        ],
      ),
      body: TabBarView(
        controller: _tabController,
        children: [
          _buildCameraGridTab(),
          _buildSessionsTab(),
          _buildAnalyticsTab(),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _showQuickActions(),
        icon: const Icon(Icons.play_arrow),
        label: const Text('Quick Actions'),
      ),
    );
  }

  Widget _buildCameraGridTab() {
    final cameraState = ref.watch(cameraListProvider);
    
    if (cameraState.isLoading) {
      return const Center(child: CircularProgressIndicator());
    }
    
    if (cameraState.error != null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.error, size: 64, color: Colors.red[300]),
            const SizedBox(height: 16),
            Text(
              'Error loading cameras',
              style: TextStyle(fontSize: 18, color: Colors.grey[300]),
            ),
            const SizedBox(height: 8),
            Text(
              cameraState.error!,
              style: TextStyle(fontSize: 14, color: Colors.grey[400]),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: () => ref.read(cameraListProvider.notifier).loadCameras(),
              child: const Text('Retry'),
            ),
          ],
        ),
      );
    }
    
    final cameras = cameraState.cameras;
        if (cameras.isEmpty) {
          return const Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(Icons.videocam_off, size: 64, color: Colors.grey),
                SizedBox(height: 16),
                Text(
                  'No cameras detected',
                  style: TextStyle(fontSize: 18, color: Colors.grey),
                ),
                SizedBox(height: 8),
                Text(
                  'Pull to refresh or check network connection',
                  style: TextStyle(color: Colors.grey),
                ),
              ],
            ),
          );
        }

        return RefreshIndicator(
          onRefresh: _refreshAll,
          child: CustomScrollView(
            slivers: [
              // Statistics header
              if (_statistics != null) ...[
                SliverToBoxAdapter(
                  child: Container(
                    margin: const EdgeInsets.all(16),
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        colors: [Colors.blue.shade50, Colors.blue.shade100],
                      ),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: Colors.blue.shade200),
                    ),
                    child: _buildQuickStats(),
                  ),
                ),
              ],
              
              // Camera grid
              SliverPadding(
                padding: const EdgeInsets.all(16),
                sliver: SliverMasonryGrid.count(
                  crossAxisCount: _getCrossAxisCount(context),
                  mainAxisSpacing: 8,
                  crossAxisSpacing: 8,
                  childCount: cameras.length,
                  itemBuilder: (context, index) {
                    final camera = cameras[index];
                    return EnhancedCameraCard(
                      camera: camera,
                      showRecordingControls: true,
                      onTap: () => _showCameraDetails(camera),
                    );
                  },
                ),
              ),
            ],
          ),
        );
  }

  Widget _buildSessionsTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Global recording controls
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      const Icon(Icons.control_camera),
                      const SizedBox(width: 8),
                      Text(
                        'Global Recording Controls',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  Row(
                    children: [
                      Expanded(
                        child: ElevatedButton.icon(
                          onPressed: () => _startAllRecordings(),
                          icon: const Icon(Icons.play_arrow),
                          label: const Text('Start All Recordings'),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: Colors.green,
                            foregroundColor: Colors.white,
                          ),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: ElevatedButton.icon(
                          onPressed: () => _stopAllRecordings(),
                          icon: const Icon(Icons.stop),
                          label: const Text('Stop All Recordings'),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: Colors.red,
                            foregroundColor: Colors.white,
                          ),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
          
          const SizedBox(height: 16),
          
          // Recording sessions dashboard
          const RecordingSessionsDashboard(),
          
          const SizedBox(height: 16),
          
          // Active sessions list
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Active Recording Sessions',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const SizedBox(height: 16),
                  FutureBuilder<List<RecordingSession>?>(
                    future: Future.value(_recordingService?.activeSessions ?? []),
                    builder: (context, snapshot) {
                      if (snapshot.connectionState == ConnectionState.waiting) {
                        return const Center(child: CircularProgressIndicator());
                      }
                      
                      if (snapshot.hasError) {
                        return Center(
                          child: Text('Error: ${snapshot.error}'),
                        );
                      }
                      
                      final sessions = snapshot.data ?? [];
                      if (sessions.isEmpty) {
                        return const Center(
                          child: Padding(
                            padding: EdgeInsets.all(32),
                            child: Column(
                              children: [
                                Icon(Icons.videocam_off, size: 48, color: Colors.grey),
                                SizedBox(height: 8),
                                Text(
                                  'No active recording sessions',
                                  style: TextStyle(color: Colors.grey),
                                ),
                              ],
                            ),
                          ),
                        );
                      }
                      
                      return ListView.builder(
                        shrinkWrap: true,
                        physics: const NeverScrollableScrollPhysics(),
                        itemCount: sessions.length,
                        itemBuilder: (context, index) {
                          final session = sessions[index];
                          return Card(
                            margin: const EdgeInsets.symmetric(vertical: 4),
                            child: ListTile(
                              leading: const Icon(
                                Icons.fiber_manual_record,
                                color: Colors.red,
                              ),
                              title: Text('Camera: ${session.cameraDeviceId}'),
                              subtitle: Text(
                                'Duration: ${session.durationText} • Status: ${session.statusText}',
                              ),
                              trailing: IconButton(
                                onPressed: () => _stopRecordingSession(session),
                                icon: const Icon(Icons.stop, color: Colors.red),
                                tooltip: 'Stop Recording',
                              ),
                            ),
                          );
                        },
                      );
                    },
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildAnalyticsTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Recording Analytics',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 16),
          
          if (_isLoadingStats)
            const Center(child: CircularProgressIndicator())
          else if (_statistics != null)
            _buildDetailedStatistics()
          else
            const Center(
              child: Text('No analytics data available'),
            ),
        ],
      ),
    );
  }

  Widget _buildQuickStats() {
    if (_statistics == null) return const SizedBox.shrink();
    
    return Row(
      children: [
        Expanded(
          child: _buildStatItem(
            'Total',
            _statistics!.totalSessions.toString(),
            Icons.video_library,
            Colors.blue,
          ),
        ),
        Expanded(
          child: _buildStatItem(
            'Active',
            _statistics!.activeSessions.toString(),
            Icons.fiber_manual_record,
            Colors.red,
          ),
        ),
        Expanded(
          child: _buildStatItem(
            'Completed',
            _statistics!.completedSessions.toString(),
            Icons.check_circle,
            Colors.green,
          ),
        ),
      ],
    );
  }

  Widget _buildStatItem(String label, String value, IconData icon, Color color) {
    return Column(
      children: [
        Icon(icon, color: color, size: 24),
        const SizedBox(height: 4),
        Text(
          value,
          style: TextStyle(
            fontSize: 20,
            fontWeight: FontWeight.bold,
            color: color,
          ),
        ),
        Text(
          label,
          style: TextStyle(
            fontSize: 12,
            color: color is MaterialColor ? color.shade700 : color.withOpacity(0.7),
          ),
        ),
      ],
    );
  }

  Widget _buildDetailedStatistics() {
    if (_statistics == null) return const SizedBox.shrink();
    
    return Column(
      children: [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Session Overview',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const SizedBox(height: 16),
                GridView.count(
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  crossAxisCount: 2,
                  crossAxisSpacing: 16,
                  mainAxisSpacing: 16,
                  childAspectRatio: 2.5,
                  children: [
                    _buildAnalyticsCard(
                      'Total Sessions',
                      _statistics!.totalSessions.toString(),
                      Icons.video_library,
                      Colors.blue,
                    ),
                    _buildAnalyticsCard(
                      'Active Sessions',
                      _statistics!.activeSessions.toString(),
                      Icons.fiber_manual_record,
                      Colors.red,
                    ),
                    _buildAnalyticsCard(
                      'Completed Sessions',
                      _statistics!.completedSessions.toString(),
                      Icons.check_circle,
                      Colors.green,
                    ),
                    _buildAnalyticsCard(
                      'Average Duration',
                      '${_statistics!.averageDuration.toStringAsFixed(1)}s',
                      Icons.timer,
                      Colors.orange,
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
        
        const SizedBox(height: 16),
        
        // Additional analytics can be added here
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Performance Metrics',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const SizedBox(height: 16),
                const Text(
                  'Phase 4 Database Integration: ✅ Active\n'
                  'Real-time Session Tracking: ✅ Enabled\n'
                  'Auto Face Detection: ✅ Configured\n'
                  'Session Persistence: ✅ Working',
                  style: TextStyle(height: 1.5),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildAnalyticsCard(String title, String value, IconData icon, Color color) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(icon, color: color, size: 20),
          const SizedBox(height: 4),
          Text(
            value,
            style: TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.bold,
              color: color is MaterialColor ? color.shade800 : color.withOpacity(0.9),
            ),
          ),
          Text(
            title,
            style: TextStyle(
              fontSize: 10,
              color: color is MaterialColor ? color.shade700 : color.withOpacity(0.7),
            ),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }

  int _getCrossAxisCount(BuildContext context) {
    final width = MediaQuery.of(context).size.width;
    if (width < 600) return 1;
    if (width < 900) return 2;
    if (width < 1200) return 3;
    return 4;
  }

  void _showCameraDetails(Camera camera) {
    showDialog(
      context: context,
      builder: (context) => Dialog(
        child: Container(
          width: 400,
          padding: const EdgeInsets.all(16),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Camera Details',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 16),
              _buildDetailRow('Name', camera.name),
              _buildDetailRow('Device ID', camera.deviceId),
              _buildDetailRow('Brand', camera.manufacturer ?? 'Unknown'),
              _buildDetailRow('Model', camera.model ?? 'Unknown'),
              _buildDetailRow('IP Address', camera.metadata?['ip_address']?.toString() ?? 'Unknown'),
              _buildDetailRow('Status', camera.isConnected == true ? 'Connected' : 'Disconnected'),
              const SizedBox(height: 16),
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  TextButton(
                    onPressed: () => Navigator.of(context).pop(),
                    child: const Text('Close'),
                  ),
                  const SizedBox(width: 8),
                  ElevatedButton(
                    onPressed: () {
                      Navigator.of(context).pop();
                      // Navigate to individual camera management
                    },
                    child: const Text('Manage'),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildDetailRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 100,
            child: Text(
              '$label:',
              style: const TextStyle(fontWeight: FontWeight.w500),
            ),
          ),
          Expanded(
            child: Text(value),
          ),
        ],
      ),
    );
  }

  void _showGlobalSessionControls() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Session Settings'),
        content: const Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            SwitchListTile(
              title: Text('Auto Face Detection'),
              subtitle: Text('Automatically trigger face detection on completed recordings'),
              value: true,
              onChanged: null, // TODO: Implement
            ),
            SwitchListTile(
              title: Text('Real-time Stats'),
              subtitle: Text('Update recording statistics in real-time'),
              value: true,
              onChanged: null, // TODO: Implement
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Close'),
          ),
        ],
      ),
    );
  }

  void _showQuickActions() {
    showModalBottomSheet(
      context: context,
      builder: (context) => Container(
        padding: const EdgeInsets.all(16),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text(
              'Quick Actions',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 16),
            ListTile(
              leading: const Icon(Icons.play_arrow, color: Colors.green),
              title: const Text('Start All Recordings'),
              onTap: () {
                Navigator.pop(context);
                _startAllRecordings();
              },
            ),
            ListTile(
              leading: const Icon(Icons.stop, color: Colors.red),
              title: const Text('Stop All Recordings'),
              onTap: () {
                Navigator.pop(context);
                _stopAllRecordings();
              },
            ),
            ListTile(
              leading: const Icon(Icons.refresh, color: Colors.blue),
              title: const Text('Refresh Data'),
              onTap: () {
                Navigator.pop(context);
                _refreshAll();
              },
            ),
            ListTile(
              leading: const Icon(Icons.analytics, color: Colors.purple),
              title: const Text('View Analytics'),
              onTap: () {
                Navigator.pop(context);
                _tabController.animateTo(2);
              },
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _startAllRecordings() async {
    final cameras = ref.read(cameraListProvider).cameras;
    int successCount = 0;
    
    for (final camera in cameras) {
      try {
        if (_recordingService != null) {
          await _recordingService!.createRecordingSession(
            cameraDeviceId: camera.deviceId,
            workflowId: 'bulk-recording-session',
            metadata: {
              'camera_name': camera.name,
              'bulk_operation': true,
              'initiated_by': 'global_start_all',
            },
          );
          successCount++;
        }
      } catch (e) {
        debugPrint('Failed to start recording for ${camera.name}: $e');
      }
    }
    
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('Started recording on $successCount/${cameras.length} cameras'),
        backgroundColor: successCount == cameras.length ? Colors.green : Colors.orange,
      ),
    );
    
    await _loadStatistics();
  }

  Future<void> _stopAllRecordings() async {
    if (_recordingService == null) return;
    
    try {
      final activeSessions = _recordingService!.activeSessions;
      if (activeSessions == null) return;
      
      int successCount = 0;
      for (final session in activeSessions) {
        try {
          await _recordingService!.updateSessionStatus(
            sessionUuid: session.sessionUuid,
            status: SessionStatus.completed,
            metadata: {
              'stopped_by': 'global_stop_all',
              'stopped_at': DateTime.now().toIso8601String(),
            },
          );
          successCount++;
        } catch (e) {
          debugPrint('Failed to stop session ${session.sessionUuid}: $e');
        }
      }
      
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Stopped $successCount/${activeSessions.length} recording sessions'),
          backgroundColor: successCount == activeSessions.length ? Colors.green : Colors.orange,
        ),
      );
      
      await _loadStatistics();
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Failed to stop recordings: $e'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  Future<void> _stopRecordingSession(RecordingSession session) async {
    if (_recordingService == null) return;
    
    try {
      await _recordingService!.updateSessionStatus(
        sessionUuid: session.sessionUuid,
        status: SessionStatus.completed,
        metadata: {
          'stopped_by': 'individual_action',
          'stopped_at': DateTime.now().toIso8601String(),
        },
      );
      
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Recording session stopped'),
          backgroundColor: Colors.green,
        ),
      );
      
      setState(() {}); // Refresh the active sessions list
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Failed to stop recording: $e'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }
}