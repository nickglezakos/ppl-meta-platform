import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../../core/core.dart';

/// Screen for connecting to PPL Meta Platform and registering as camera
class PlatformConnectionScreen extends StatefulWidget {
  const PlatformConnectionScreen({Key? key}) : super(key: key);

  @override
  State<PlatformConnectionScreen> createState() => _PlatformConnectionScreenState();
}

class _PlatformConnectionScreenState extends State<PlatformConnectionScreen> {
  final _ipController = TextEditingController(text: '192.168.1.68');
  final _portController = TextEditingController(text: '8005');
  final _cameraNameController = TextEditingController();
  
  @override
  void initState() {
    super.initState();
    _cameraNameController.text = 'Mobile Camera ${DateTime.now().millisecondsSinceEpoch % 1000}';
    
    // Automatically load platform services if user is authenticated
    WidgetsBinding.instance.addPostFrameCallback((_) {
      print('🚀 [PLATFORM_CONNECTION] Screen initialized, checking authentication...');
      final authService = AuthenticationService.instance;
      final streamingProvider = Provider.of<PlatformStreamingProvider>(context, listen: false);
      
      if (authService.isAuthenticated) {
        print('✅ [PLATFORM_CONNECTION] User is authenticated, automatically loading platform services');
        _loadPlatformServicesFromAuth(streamingProvider, authService);
      } else {
        print('❌ [PLATFORM_CONNECTION] User not authenticated, manual discovery required');
      }
    });
  }

  @override
  void dispose() {
    _ipController.dispose();
    _portController.dispose();
    _cameraNameController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Connect to Platform'),
        centerTitle: true,
      ),
      body: Consumer<PlatformStreamingProvider>(
        builder: (context, streamingProvider, child) {
          return SingleChildScrollView(
            padding: const EdgeInsets.all(16.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Status Card
                _buildStatusCard(streamingProvider),
                const SizedBox(height: 24),

                // Discovery Section
                _buildDiscoverySection(streamingProvider),
                const SizedBox(height: 24),

                // Manual Connection Section
                _buildManualConnectionSection(streamingProvider),
                const SizedBox(height: 24),

                // Registration Section
                if (streamingProvider.isConnectedToPlatform) ...[
                  _buildRegistrationSection(streamingProvider),
                  const SizedBox(height: 24),
                ],

                // Streaming Section
                if (streamingProvider.isRegistered) ...[
                  _buildStreamingSection(streamingProvider),
                ],
                
                // Add bottom padding for safe scrolling
                const SizedBox(height: 80),
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _buildStatusCard(PlatformStreamingProvider streamingProvider) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  _getStatusIcon(streamingProvider.status),
                  color: _getStatusColor(streamingProvider.status),
                ),
                const SizedBox(width: 8),
                Text(
                  'Status: ${streamingProvider.status.displayName}',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
              ],
            ),
            if (streamingProvider.statusMessage != null) ...[
              const SizedBox(height: 8),
              Text(
                streamingProvider.statusMessage!,
                style: Theme.of(context).textTheme.bodyMedium,
              ),
            ],
            if (streamingProvider.isConnectedToPlatform) ...[
              const SizedBox(height: 8),
              Text(
                'Platform: ${streamingProvider.platformUrl}',
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ],
            if (streamingProvider.isRegistered) ...[
              const SizedBox(height: 4),
              Text(
                'Device ID: ${streamingProvider.registeredDeviceId}',
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ],
            if (streamingProvider.isStreaming) ...[
              const SizedBox(height: 4),
              Text(
                'Clients: ${streamingProvider.connectedClients}',
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildDiscoverySection(PlatformStreamingProvider streamingProvider) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Platform Discovery',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 16),
            
            // Check if user is authenticated and has platform services
            Consumer<AuthenticationService>(
              builder: (context, authService, child) {
                final platformServices = authService.getPlatformServices();
                final isAuthenticated = authService.isAuthenticated;
                
                if (isAuthenticated && platformServices != null) {
                  // User is authenticated and we have platform services
                  return Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: Colors.green.withOpacity(0.1),
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: Colors.green.withOpacity(0.3)),
                        ),
                        child: Row(
                          children: [
                            Icon(Icons.check_circle, color: Colors.green, size: 20),
                            const SizedBox(width: 8),
                            Expanded(
                              child: Text(
                                'Platform services available from login session',
                                style: TextStyle(color: Colors.green.shade700),
                              ),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 12),
                      SizedBox(
                        width: double.infinity,
                        child: ElevatedButton.icon(
                          onPressed: streamingProvider.isDiscovering
                              ? null
                              : () => _loadPlatformServicesFromAuth(streamingProvider, authService),
                          icon: streamingProvider.isDiscovering
                              ? const SizedBox(
                                  width: 16,
                                  height: 16,
                                  child: CircularProgressIndicator(strokeWidth: 2),
                                )
                              : const Icon(Icons.cloud_download),
                          label: Text(streamingProvider.isDiscovering
                              ? 'Loading...'
                              : 'Load Platform Services'),
                        ),
                      ),
                    ],
                  );
                } else if (isAuthenticated) {
                  // Authenticated but no platform services
                  print('⚠️ [PLATFORM_CONNECTION] User authenticated but no platform services discovered');
                  print('🔍 [PLATFORM_CONNECTION] Auth token: ${authService.authToken != null}');
                  print('🌐 [PLATFORM_CONNECTION] Server URL: ${authService.serverUrl}');
                  print('📊 [PLATFORM_CONNECTION] Platform services: ${authService.getPlatformServices()}');
                  
                  return Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: Colors.orange.withOpacity(0.1),
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: Colors.orange.withOpacity(0.3)),
                        ),
                        child: Row(
                          children: [
                            Icon(Icons.warning, color: Colors.orange, size: 20),
                            const SizedBox(width: 8),
                            Expanded(
                              child: Text(
                                'Login session active but no platform services found',
                                style: TextStyle(color: Colors.orange.shade700),
                              ),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 12),
                      _buildFallbackDiscoveryButton(streamingProvider),
                    ],
                  );
                } else {
                  // Not authenticated
                  return Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: Colors.blue.withOpacity(0.1),
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: Colors.blue.withOpacity(0.3)),
                        ),
                        child: Row(
                          children: [
                            Icon(Icons.info, color: Colors.blue, size: 20),
                            const SizedBox(width: 8),
                            Expanded(
                              child: Text(
                                'Login to automatically discover platform services',
                                style: TextStyle(color: Colors.blue.shade700),
                              ),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 12),
                      _buildFallbackDiscoveryButton(streamingProvider),
                    ],
                  );
                }
              },
            ),
            
            if (streamingProvider.discoveredPlatforms.isNotEmpty) ...[
              const SizedBox(height: 16),
              Text(
                'Available Services:',
                style: Theme.of(context).textTheme.titleSmall,
              ),
              const SizedBox(height: 8),
              ...streamingProvider.discoveredPlatforms.map((platform) {
                final isRecommended = platform.healthData?['recommended'] == true;
                return Card(
                  margin: const EdgeInsets.only(bottom: 8),
                  color: isRecommended ? Colors.green.withOpacity(0.05) : null,
                  child: ListTile(
                    dense: true,
                    leading: Icon(
                      isRecommended ? Icons.star : Icons.computer,
                      color: isRecommended ? Colors.amber : null,
                    ),
                    title: Row(
                      children: [
                        Expanded(
                          child: Text(
                            platform.displayName,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        if (isRecommended) ...[
                          const SizedBox(width: 4),
                          Flexible(
                            child: Container(
                              padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
                              decoration: BoxDecoration(
                                color: Colors.green,
                                borderRadius: BorderRadius.circular(8),
                              ),
                              child: const Text(
                                'REC',
                                style: TextStyle(
                                  color: Colors.white,
                                  fontSize: 9,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                            ),
                          ),
                        ],
                      ],
                    ),
                    subtitle: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(platform.baseUrl),
                        if (platform.healthData?['purpose'] != null)
                          Text(
                            platform.healthData!['purpose'],
                            style: const TextStyle(fontSize: 12, fontStyle: FontStyle.italic),
                          ),
                      ],
                    ),
                    trailing: ElevatedButton(
                      onPressed: () => streamingProvider.connectToPlatform(platform.baseUrl),
                      style: isRecommended
                          ? ElevatedButton.styleFrom(backgroundColor: Colors.green)
                          : null,
                      child: Text(isRecommended ? 'CONNECT' : 'Connect'),
                    ),
                  ),
                );
              }),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildFallbackDiscoveryButton(PlatformStreamingProvider streamingProvider) {
    return SizedBox(
      width: double.infinity,
      child: ElevatedButton.icon(
        onPressed: streamingProvider.isDiscovering
            ? null
            : () => streamingProvider.discoverPlatforms(),
        icon: streamingProvider.isDiscovering
            ? const SizedBox(
                width: 16,
                height: 16,
                child: CircularProgressIndicator(strokeWidth: 2),
              )
            : const Icon(Icons.search),
        label: Text(streamingProvider.isDiscovering
            ? 'Discovering...'
            : 'Network Discovery (Fallback)'),
        style: ElevatedButton.styleFrom(
          backgroundColor: Colors.grey.shade600,
        ),
      ),
    );
  }

  Widget _buildManualConnectionSection(PlatformStreamingProvider streamingProvider) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Manual Connection',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 16),
            
            Row(
              children: [
                Expanded(
                  flex: 3,
                  child: TextField(
                    controller: _ipController,
                    decoration: const InputDecoration(
                      labelText: 'IP Address',
                      hintText: '192.168.1.100',
                    ),
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: TextField(
                    controller: _portController,
                    decoration: const InputDecoration(
                      labelText: 'Port',
                    ),
                    keyboardType: TextInputType.number,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: () {
                  final ip = _ipController.text.trim();
                  final port = int.tryParse(_portController.text.trim()) ?? 8005;
                  if (ip.isNotEmpty) {
                    final url = 'http://$ip:$port';
                    streamingProvider.connectToPlatform(url);
                  }
                },
                child: const Text('Connect'),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildRegistrationSection(PlatformStreamingProvider streamingProvider) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Camera Registration',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 16),
            
            TextField(
              controller: _cameraNameController,
              decoration: const InputDecoration(
                labelText: 'Camera Name',
                hintText: 'My Mobile Camera',
              ),
            ),
            const SizedBox(height: 16),
            
            if (!streamingProvider.isRegistered) ...[
              SizedBox(
                width: double.infinity,
                child: ElevatedButton.icon(
                  onPressed: () {
                    final name = _cameraNameController.text.trim();
                    streamingProvider.registerCamera(
                      customName: name.isNotEmpty ? name : null,
                    );
                  },
                  icon: const Icon(Icons.app_registration),
                  label: const Text('Register Camera'),
                ),
              ),
            ] else ...[
              Row(
                children: [
                  const Icon(Icons.check_circle, color: Colors.green),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      'Camera registered successfully!',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  ),
                  TextButton(
                    onPressed: () => streamingProvider.unregisterCamera(),
                    child: const Text('Unregister'),
                  ),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildStreamingSection(PlatformStreamingProvider streamingProvider) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Camera Streaming',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 16),
            
            // Streaming Configuration
            Text(
              'Configuration: ${streamingProvider.streamingConfig}',
              style: Theme.of(context).textTheme.bodySmall,
            ),
            const SizedBox(height: 16),
            
            // Streaming Controls
            Row(
              children: [
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: streamingProvider.isStreaming
                        ? null
                        : () {
                            streamingProvider.startStreaming();
                          },
                    icon: const Icon(Icons.play_arrow),
                    label: const Text('Start Streaming'),
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: !streamingProvider.isStreaming
                        ? null
                        : () {
                            streamingProvider.stopStreaming();
                          },
                    icon: const Icon(Icons.stop),
                    label: const Text('Stop Streaming'),
                  ),
                ),
              ],
            ),
            
            // Streaming Statistics
            if (streamingProvider.streamingStats != null) ...[
              const SizedBox(height: 16),
              const Divider(),
              const SizedBox(height: 16),
              Text(
                'Streaming Statistics',
                style: Theme.of(context).textTheme.titleSmall,
              ),
              const SizedBox(height: 8),
              _buildStatsRow('Frames Sent', '${streamingProvider.streamingStats!.framesSent}'),
              _buildStatsRow('Frames Dropped', '${streamingProvider.streamingStats!.framesDropped}'),
              _buildStatsRow('Drop Rate', '${streamingProvider.streamingStats!.dropRate.toStringAsFixed(1)}%'),
              _buildStatsRow('Average FPS', '${streamingProvider.streamingStats!.averageFps.toStringAsFixed(1)}'),
              _buildStatsRow('Bandwidth', '${streamingProvider.streamingStats!.mbpsSent.toStringAsFixed(1)} Mbps'),
              _buildStatsRow('Uptime', '${streamingProvider.streamingStats!.uptime.inSeconds}s'),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildStatsRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2.0),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: Theme.of(context).textTheme.bodySmall),
          Text(value, style: Theme.of(context).textTheme.bodySmall?.copyWith(fontWeight: FontWeight.bold)),
        ],
      ),
    );
  }

  IconData _getStatusIcon(MobileCameraStatus status) {
    switch (status) {
      case MobileCameraStatus.offline:
        return Icons.cloud_off;
      case MobileCameraStatus.connecting:
        return Icons.cloud_sync;
      case MobileCameraStatus.available:
        return Icons.cloud_done;
      case MobileCameraStatus.streaming:
        return Icons.videocam;
      case MobileCameraStatus.error:
        return Icons.error;
      default:
        return Icons.help;
    }
  }

  Color _getStatusColor(MobileCameraStatus status) {
    switch (status) {
      case MobileCameraStatus.offline:
        return Colors.grey;
      case MobileCameraStatus.connecting:
        return Colors.orange;
      case MobileCameraStatus.available:
        return Colors.green;
      case MobileCameraStatus.streaming:
        return Colors.blue;
      case MobileCameraStatus.error:
        return Colors.red;
      default:
        return Colors.grey;
    }
  }

  /// Load platform services from authentication service
  void _loadPlatformServicesFromAuth(PlatformStreamingProvider streamingProvider, AuthenticationService authService) {
    print('🔍 [PLATFORM_CONNECTION] Loading platform services from auth service...');
    print('🔑 [PLATFORM_CONNECTION] Auth status: ${authService.isAuthenticated}');
    print('🌐 [PLATFORM_CONNECTION] Server URL: ${authService.serverUrl}');
    print('🎫 [PLATFORM_CONNECTION] Auth token: ${authService.authToken != null ? 'present' : 'null'}');
    
    final platformServices = authService.getPlatformServices();
    print('📊 [PLATFORM_CONNECTION] Platform services data: ${platformServices != null ? 'available' : 'null'}');
    
    if (platformServices != null && authService.authToken != null) {
      print('✅ [PLATFORM_CONNECTION] Using authenticated platform services discovery');
      print('🚀 [PLATFORM_CONNECTION] Calling streamingProvider.getPlatformServices()');
      
      // Use the authenticated platform services discovery
      streamingProvider.getPlatformServices(
        authService.serverUrl,
        authService.authToken!,
      );
    } else {
      print('❌ [PLATFORM_CONNECTION] Platform services or auth token not available');
      print('🔄 [PLATFORM_CONNECTION] Falling back to network discovery');
      // Fallback to network discovery
      streamingProvider.discoverPlatforms();
    }
  }
}
