/// Device Manager Widget
/// Enhanced device list view with detailed status and controls

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'dart:async';
import '../../models/signage_models.dart';
import '../../providers/signage_provider.dart';

class DeviceManager extends StatefulWidget {
  const DeviceManager({Key? key}) : super(key: key);

  @override
  State<DeviceManager> createState() => _DeviceManagerState();
}

class _DeviceManagerState extends State<DeviceManager> {
  Timer? _refreshTimer;

  @override
  void initState() {
    super.initState();
    _loadDevices(refreshStatuses: false);  // Don't load statuses - Control tab handles that
    
    // Periodically refresh device list from discovery (every 10 seconds)
    // to keep device online/offline status up to date
    _refreshTimer = Timer.periodic(
      const Duration(seconds: 10),
      (_) {
        if (mounted) {
          _loadDevices(refreshStatuses: false);
        }
      },
    );
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    super.dispose();
  }

  Future<void> _loadDevices({bool refreshStatuses = true}) async {
    final provider = context.read<SignageProvider>();
    await provider.loadDevices();
    // Load statuses only on explicit refresh (user pulls down) or when requested
    if (refreshStatuses) {
      await provider.loadAllDeviceStatuses();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<SignageProvider>(
      builder: (context, provider, child) {
        if (provider.isLoadingDevices && provider.devices.isEmpty) {
          return const Center(child: CircularProgressIndicator());
        }

        if (provider.devicesError != null) {
          return _buildErrorState(provider.devicesError!);
        }

        if (provider.devices.isEmpty) {
          return _buildEmptyState();
        }

        return RefreshIndicator(
          onRefresh: _loadDevices,
          child: Column(
            children: [
              // Stats header
              _buildStatsHeader(provider),
              
              // Filters
              _buildFilters(),
              
              // Device grid
              Expanded(
                child: GridView.builder(
                  padding: const EdgeInsets.all(16),
                  gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
                    maxCrossAxisExtent: 400,
                    childAspectRatio: 1.2,
                    crossAxisSpacing: 16,
                    mainAxisSpacing: 16,
                  ),
                  itemCount: provider.devices.length,
                  itemBuilder: (context, index) {
                    final device = provider.devices[index];
                    final status = provider.deviceStatuses[device.id];
                    return _buildDeviceCard(device, status);
                  },
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildStatsHeader(SignageProvider provider) {
    final totalDevices = provider.devices.length;
    final onlineDevices = provider.devices.where((d) => d.isOnline).length;
    final playingDevices = provider.deviceStatuses.values
        .where((s) => s.playbackState == PlaybackState.playing)
        .length;

    return Container(
      padding: const EdgeInsets.all(16),
      color: Theme.of(context).primaryColor.withOpacity(0.1),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceEvenly,
        children: [
          _buildStatItem(
            icon: Icons.devices,
            label: 'Total',
            value: totalDevices.toString(),
            color: Colors.blue,
          ),
          _buildStatItem(
            icon: Icons.check_circle,
            label: 'Online',
            value: onlineDevices.toString(),
            color: Colors.green,
          ),
          _buildStatItem(
            icon: Icons.play_circle,
            label: 'Playing',
            value: playingDevices.toString(),
            color: Colors.orange,
          ),
          _buildStatItem(
            icon: Icons.error,
            label: 'Offline',
            value: (totalDevices - onlineDevices).toString(),
            color: Colors.red,
          ),
        ],
      ),
    );
  }

  Widget _buildStatItem({
    required IconData icon,
    required String label,
    required String value,
    required Color color,
  }) {
    return Column(
      children: [
        Icon(icon, color: color, size: 32),
        const SizedBox(height: 8),
        Text(
          value,
          style: TextStyle(
            fontSize: 24,
            fontWeight: FontWeight.bold,
            color: color,
          ),
        ),
        Text(
          label,
          style: TextStyle(color: Colors.grey[600], fontSize: 12),
        ),
      ],
    );
  }

  Widget _buildFilters() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              decoration: InputDecoration(
                hintText: 'Search devices...',
                prefixIcon: const Icon(Icons.search),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(8),
                ),
                contentPadding: const EdgeInsets.symmetric(horizontal: 16),
              ),
            ),
          ),
          const SizedBox(width: 16),
          FilterChip(
            label: const Text('Online'),
            onSelected: (value) {},
          ),
          const SizedBox(width: 8),
          FilterChip(
            label: const Text('Playing'),
            onSelected: (value) {},
          ),
        ],
      ),
    );
  }

  Widget _buildDeviceCard(SignageDevice device, PlaybackStatus? status) {
    final isOnline = device.isOnline;
    final isPlaying = status?.playbackState == PlaybackState.playing;

    return Card(
      elevation: 4,
      child: InkWell(
        onTap: () => _showDeviceDetails(device, status),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header with status indicator
              Row(
                children: [
                  Container(
                    width: 16,
                    height: 16,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: isOnline ? Colors.green : Colors.red,
                      boxShadow: isOnline
                          ? [
                              BoxShadow(
                                color: Colors.green.withOpacity(0.5),
                                blurRadius: 8,
                                spreadRadius: 2,
                              )
                            ]
                          : null,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          device.name,
                          style: const TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.bold,
                          ),
                          overflow: TextOverflow.ellipsis,
                        ),
                        Text(
                          '${device.host}:${device.port}',
                          style: TextStyle(
                            color: Colors.grey[600],
                            fontSize: 12,
                          ),
                        ),
                      ],
                    ),
                  ),
                  if (isPlaying)
                    Icon(
                      Icons.play_circle,
                      color: Colors.green[700],
                      size: 28,
                    ),
                ],
              ),
              const SizedBox(height: 16),
              
              // Current status
              if (status != null && status.currentVideo != null) ...[
                const Divider(),
                Text(
                  'Now Playing:',
                  style: TextStyle(
                    fontWeight: FontWeight.bold,
                    color: Colors.grey[700],
                    fontSize: 12,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  status.currentVideo!.title,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: 14),
                ),
                const SizedBox(height: 8),
                LinearProgressIndicator(
                  value: status.currentVideo!.progressPercent / 100,
                  backgroundColor: Colors.grey[300],
                ),
                const SizedBox(height: 4),
                Text(
                  '${status.currentVideo!.progressPercent.toStringAsFixed(0)}%',
                  style: TextStyle(
                    fontSize: 11,
                    color: Colors.grey[600],
                  ),
                ),
              ] else if (isOnline) ...[
                const Divider(),
                Center(
                  child: Text(
                    'No active playback',
                    style: TextStyle(
                      color: Colors.grey[600],
                      fontSize: 12,
                      fontStyle: FontStyle.italic,
                    ),
                  ),
                ),
              ],
              
              const Spacer(),
              
              // Quick actions - Simplified (playback controls on Control tab)
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                children: [
                  _buildQuickAction(
                    icon: Icons.sync,
                    tooltip: 'Sync Playlist',
                    enabled: isOnline,
                    onPressed: () => _syncDevice(device),
                  ),
                  _buildQuickAction(
                    icon: Icons.info_outline,
                    tooltip: 'View Details',
                    enabled: true,
                    onPressed: () => _showDeviceDetails(device, status),
                  ),
                  _buildQuickAction(
                    icon: Icons.settings_remote,
                    tooltip: 'Go to Controls',
                    enabled: isOnline,
                    onPressed: () => _navigateToControl(device),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildQuickAction({
    required IconData icon,
    required String tooltip,
    required bool enabled,
    required VoidCallback onPressed,
  }) {
    return Tooltip(
      message: tooltip,
      child: IconButton(
        icon: Icon(icon),
        color: enabled ? Theme.of(context).colorScheme.primary : null,
        disabledColor: Colors.grey[400],
        tooltip: tooltip,
        onPressed: enabled ? onPressed : null,
        iconSize: 20,
      ),
    );
  }

  Widget _buildErrorState(String error) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.error_outline, size: 64, color: Colors.red[300]),
          const SizedBox(height: 16),
          Text(error),
          const SizedBox(height: 16),
          ElevatedButton(
            onPressed: _loadDevices,
            child: const Text('Retry'),
          ),
        ],
      ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.devices_other, size: 64, color: Colors.grey[400]),
          const SizedBox(height: 16),
          Text(
            'No devices found',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 8),
          const Text('Make sure signage devices are online and registered'),
          const SizedBox(height: 24),
          ElevatedButton.icon(
            onPressed: _loadDevices,
            icon: const Icon(Icons.refresh),
            label: const Text('Refresh'),
          ),
        ],
      ),
    );
  }

  void _showDeviceDetails(SignageDevice device, PlaybackStatus? status) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(device.name),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _buildDetailRow('Device ID', device.id),
              _buildDetailRow('Host', device.host),
              _buildDetailRow('Port', device.port.toString()),
              _buildDetailRow('Status', device.status),
              _buildDetailRow('Type', device.serviceType),
              if (device.lastHeartbeat != null)
                _buildDetailRow(
                  'Last Heartbeat',
                  _formatDateTime(device.lastHeartbeat!),
                ),
              if (device.metadata != null) ...[
                const Divider(height: 24),
                const Text(
                  'Device Metadata:',
                  style: TextStyle(fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 8),
                ...device.metadata!.entries.map((e) =>
                    _buildDetailRow(e.key, e.value.toString())),
              ],
              if (status != null) ...[
                const Divider(height: 24),
                const Text(
                  'Playback Status:',
                  style: TextStyle(fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 8),
                _buildDetailRow('State', status.playbackState.toString()),
                if (status.playlist != null)
                  _buildDetailRow('Playlist', status.playlist!.name),
                _buildDetailRow(
                    'History Count', status.historyCount.toString()),
              ],
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Close'),
          ),
        ],
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
            width: 120,
            child: Text(
              '$label:',
              style: TextStyle(
                color: Colors.grey[600],
                fontSize: 12,
              ),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: const TextStyle(fontSize: 12),
            ),
          ),
        ],
      ),
    );
  }

  String _formatDateTime(DateTime dateTime) {
    return '${dateTime.day}/${dateTime.month}/${dateTime.year} '
        '${dateTime.hour}:${dateTime.minute.toString().padLeft(2, '0')}';
  }

  Future<void> _syncDevice(SignageDevice device) async {
    final provider = context.read<SignageProvider>();
    
    if (provider.videoLists.isEmpty) {
      await provider.loadVideoLists();
    }
    
    if (provider.videoLists.isEmpty) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('No playlists available to sync')),
        );
      }
      return;
    }

    final playlist = await showDialog<VideoList>(
      context: context,
      builder: (context) => SimpleDialog(
        title: const Text('Select Playlist'),
        children: provider.videoLists.map((list) {
          return SimpleDialogOption(
            child: Text(list.name),
            onPressed: () => Navigator.pop(context, list),
          );
        }).toList(),
      ),
    );

    if (playlist != null && mounted) {
      final success = await provider.syncVideoListToDevices(
        videoListId: playlist.id,
        deviceIds: [device.id],  // Use UUID, not deviceId
      );

      if (success && mounted) {
        // Give device a moment to process sync, then load status to get playlist info
        await Future.delayed(const Duration(milliseconds: 500));
        await provider.loadDeviceStatus(device.id);
      }

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(success ? 'Playlist synced successfully' : 'Sync failed'),
          ),
        );
      }
    }
  }

  void _navigateToControl(SignageDevice device) {
    // Select this device and navigate to Control tab
    final provider = context.read<SignageProvider>();
    provider.selectDevice(device);
    
    // Use DefaultTabController to switch to Control tab (index 1)
    DefaultTabController.of(context).animateTo(1);
  }
}
