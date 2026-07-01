import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../../services/edge_camera_api_client.dart';
import '../../../services/dynamic_service_provider.dart';
import '../../../core/providers/auth_provider.dart';
import '../../../core/theme/app_theme.dart';
import '../../../widgets/custom_app_bar.dart';
import '../../widgets/camera/edge_camera_config_dialog.dart';
import '../../../services/auth_manager.dart';
import '../../../core/config/app_config.dart';


// Shared preferences provider
final sharedPreferencesProvider = FutureProvider<SharedPreferences>((ref) async {
  return await SharedPreferences.getInstance();
});

/// Edge Camera Management Screen
/// Provides remote control and monitoring for edge cameras on RPi5
class EdgeCameraManagementScreen extends ConsumerStatefulWidget {
  final String deviceId;
  final String cameraName;

  const EdgeCameraManagementScreen({
    super.key,
    required this.deviceId,
    required this.cameraName,
  });

  @override
  ConsumerState<EdgeCameraManagementScreen> createState() =>
      _EdgeCameraManagementScreenState();
}

class _EdgeCameraManagementScreenState
    extends ConsumerState<EdgeCameraManagementScreen> {
  EdgeCameraApiClient? _apiClient;
  Map<String, dynamic>? _status;
  Map<String, dynamic>? _config;
  List<String> _logs = [];
  bool _isLoading = true;
  String? _error;
  bool _isStreaming = false;

  @override
  void initState() {
    super.initState();
    _initializeClient();
  }

  Future<void> _initializeClient() async {
    final baseUrl = AppConfig.instance.apiBaseUrl; // Routed via Gateway for VPN/remote access
    final token = ref.read(authNotifierProvider).user?.id; // Get user for auth context
    
    // Create a simple auth manager wrapper
    final authManager = AuthManager(await ref.read(sharedPreferencesProvider.future));
    
    _apiClient = EdgeCameraApiClient(
      baseUrl: baseUrl,
      authManager: authManager,
    );
    
    await _loadStatus();
  }

  Future<void> _loadStatus() async {
    if (_apiClient == null) return;
    
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final statusResponse = await _apiClient!.getStatus(widget.deviceId);
      final configResponse = await _apiClient!.getConfiguration(widget.deviceId);
      
      if (statusResponse.isSuccess && statusResponse.data != null) {
        setState(() {
          _status = statusResponse.data;
          _isStreaming = statusResponse.data?['streaming']?['active'] ?? false;
          _isLoading = false;
        });
      } else {
        setState(() {
          _error = statusResponse.error ?? 'Failed to load status';
          _isLoading = false;
        });
      }
      
      if (configResponse.isSuccess && configResponse.data != null) {
        setState(() {
          _config = configResponse.data;
        });
      }
    } catch (e) {
      setState(() {
        _error = 'Error loading status: $e';
        _isLoading = false;
      });
    }
  }

  Future<void> _loadLogs() async {
    if (_apiClient == null) return;

    try {
      final response = await _apiClient!.getLogs(widget.deviceId, lines: 100);
      
      if (response.isSuccess && response.data != null) {
        setState(() {
          _logs = List<String>.from(response.data?['logs'] ?? []);
        });
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error loading logs: $e')),
      );
    }
  }

  Future<void> _startStreaming() async {
    if (_apiClient == null) return;

    final response = await _apiClient!.startStreaming(widget.deviceId);
    
    if (response.isSuccess) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('✅ Streaming started')),
        );
        
        // Redirect to camera detail screen to view the stream
        context.go('/cameras/${widget.deviceId}');
      }
    } else {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('❌ Failed to start streaming: ${response.error}'),
            backgroundColor: Colors.red,
            duration: const Duration(seconds: 5),
          ),
        );
      }
    }
  }

  Future<void> _stopStreaming() async {
    if (_apiClient == null) return;

    final response = await _apiClient!.stopStreaming(widget.deviceId);
    
    if (response.isSuccess) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('✅ Streaming stopped')),
      );
      await _loadStatus();
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('❌ ${response.error}')),
      );
    }
  }

  Future<void> _restart(String scope) async {
    if (_apiClient == null) return;

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Restart ${scope == 'application' ? 'Application' : 'System'}?'),
        content: Text(
          scope == 'application'
            ? 'This will restart the edge camera application.'
            : 'This will reboot the entire Raspberry Pi system.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('Restart'),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      final response = await _apiClient!.restart(widget.deviceId, scope: scope);
      
      if (response.isSuccess) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('✅ Restarting $scope...')),
        );
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('❌ ${response.error}')),
        );
      }
    }
  }

  Future<void> _runNetworkDiagnostics() async {
    if (_apiClient == null) return;

    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => const AlertDialog(
        content: Row(
          children: [
            CircularProgressIndicator(),
            SizedBox(width: 20),
            Text('Running network diagnostics...'),
          ],
        ),
      ),
    );

    try {
      final response = await _apiClient!.getNetworkDiagnostics(widget.deviceId);
      Navigator.of(context).pop(); // Close loading dialog
      
      if (response.isSuccess && response.data != null) {
        _showDiagnosticsDialog(response.data!);
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('❌ ${response.error}')),
        );
      }
    } catch (e) {
      Navigator.of(context).pop();
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error: $e')),
      );
    }
  }

  void _showDiagnosticsDialog(Map<String, dynamic> diagnostics) {
    final tests = List<Map<String, dynamic>>.from(diagnostics['tests'] ?? []);
    
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Network Diagnostics'),
        content: SizedBox(
          width: double.maxFinite,
          child: ListView.builder(
            shrinkWrap: true,
            itemCount: tests.length,
            itemBuilder: (context, index) {
              final test = tests[index];
              final reachable = test['reachable'] ?? false;
              
              return ListTile(
                leading: Icon(
                  reachable ? Icons.check_circle : Icons.error,
                  color: reachable ? Colors.green : Colors.red,
                ),
                title: Text(test['service'] ?? ''),
                subtitle: Text(test['url'] ?? ''),
                trailing: reachable
                    ? Text('${test['latency_ms']}ms')
                    : const Text('Failed'),
              );
            },
          ),
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

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: CustomAppBar(
        title: widget.cameraName,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadStatus,
            tooltip: 'Refresh Status',
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Text(_error!, style: const TextStyle(color: Colors.red)),
                      const SizedBox(height: 16),
                      ElevatedButton(
                        onPressed: _loadStatus,
                        child: const Text('Retry'),
                      ),
                    ],
                  ),
                )
              : SingleChildScrollView(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _buildStatusCard(),
                      const SizedBox(height: 16),
                      _buildControlsCard(),
                      const SizedBox(height: 16),
                      _buildSystemInfoCard(),
                      const SizedBox(height: 16),
                      _buildLogsCard(),
                    ],
                  ),
                ),
    );
  }

  Widget _buildStatusCard() {
    final application = _status?['application'] ?? {};
    final streaming = _status?['streaming'] ?? {};
    final camera = _status?['camera'] ?? {};
    
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Status',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 12),
            _buildStatusRow(
              'Application',
              application['status'] ?? 'unknown',
              application['status'] == 'running',
            ),
            _buildStatusRow(
              'Camera',
              camera['connected'] == true ? 'connected' : 'disconnected',
              camera['connected'] == true,
            ),
            _buildStatusRow(
              'Streaming',
              streaming['active'] == true ? 'active' : 'stopped',
              streaming['active'] == true,
            ),
            const Divider(),
            Text('Uptime: ${_formatUptime(application['uptime_seconds'])}'),
            Text('Version: ${application['version'] ?? 'unknown'}'),
          ],
        ),
      ),
    );
  }

  Widget _buildStatusRow(String label, String value, bool isGood) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          Icon(
            isGood ? Icons.check_circle : Icons.cancel,
            color: isGood ? Colors.green : Colors.grey,
            size: 20,
          ),
          const SizedBox(width: 8),
          Text('$label: '),
          Text(
            value,
            style: TextStyle(
              color: isGood ? Colors.green : Colors.grey,
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildControlsCard() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Controls',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                ElevatedButton.icon(
                  onPressed: _isStreaming ? null : _startStreaming,
                  icon: const Icon(Icons.play_arrow),
                  label: const Text('Start Streaming'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.green,
                  ),
                ),
                ElevatedButton.icon(
                  onPressed: _isStreaming ? _stopStreaming : null,
                  icon: const Icon(Icons.stop),
                  label: const Text('Stop Streaming'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.orange,
                  ),
                ),
                ElevatedButton.icon(
                  onPressed: () => _restart('application'),
                  icon: const Icon(Icons.restart_alt),
                  label: const Text('Restart App'),
                ),
                ElevatedButton.icon(
                  onPressed: () => _restart('system'),
                  icon: const Icon(Icons.power_settings_new),
                  label: const Text('Reboot System'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.red,
                  ),
                ),
                ElevatedButton.icon(
                  onPressed: _runNetworkDiagnostics,
                  icon: const Icon(Icons.network_check),
                  label: const Text('Network Test'),
                ),
                ElevatedButton.icon(
                  onPressed: () async {
                    final result = await showDialog<bool>(
                      context: context,
                      builder: (context) => EdgeCameraConfigDialog(
                        deviceId: widget.deviceId,
                        cameraName: widget.cameraName,
                        existingConfig: _config,
                      ),
                    );
                    
                    if (result == true) {
                      await _loadStatus(); // Reload config after save
                    }
                  },
                  icon: const Icon(Icons.settings),
                  label: const Text('Configure'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.blue,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSystemInfoCard() {
    final system = _status?['system'] ?? {};
    
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'System Info',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 12),
            Text('CPU: ${system['cpu_usage']?.toStringAsFixed(1) ?? '0'}%'),
            Text('Memory: ${system['memory_percent']?.toStringAsFixed(1) ?? '0'}% (${system['memory_usage_mb']} MB)'),
            Text('Disk: ${system['disk_usage_percent']?.toStringAsFixed(1) ?? '0'}%'),
            if (system['temperature_c'] != null)
              Text('Temperature: ${system['temperature_c']?.toStringAsFixed(1)}°C'),
          ],
        ),
      ),
    );
  }

  Widget _buildLogsCard() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text(
                  'Logs',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                ),
                TextButton.icon(
                  onPressed: _loadLogs,
                  icon: const Icon(Icons.refresh, size: 16),
                  label: const Text('Load Logs'),
                ),
              ],
            ),
            const SizedBox(height: 12),
            _logs.isEmpty
                ? const Text('No logs loaded')
                : Container(
                    height: 300,
                    decoration: BoxDecoration(
                      color: Colors.black,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    padding: const EdgeInsets.all(8),
                    child: ListView.builder(
                      itemCount: _logs.length,
                      itemBuilder: (context, index) {
                        return Text(
                          _logs[index],
                          style: const TextStyle(
                            fontFamily: 'monospace',
                            fontSize: 12,
                            color: Colors.green,
                          ),
                        );
                      },
                    ),
                  ),
          ],
        ),
      ),
    );
  }

  String _formatUptime(dynamic seconds) {
    if (seconds == null) return 'unknown';
    final duration = Duration(seconds: seconds as int);
    final hours = duration.inHours;
    final minutes = duration.inMinutes.remainder(60);
    return '${hours}h ${minutes}m';
  }
}
