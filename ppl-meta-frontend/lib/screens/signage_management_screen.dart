/// Main Signage Management Screen
/// Provides UI for managing video lists, devices, sync, and playback control

import 'package:flutter/material.dart';
import 'package:provider/provider.dart' as provider;
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../providers/signage_provider.dart';
import '../models/signage_models.dart';
import '../widgets/signage/video_list_builder.dart';
import '../widgets/signage/device_manager.dart';
import '../widgets/signage/playback_controls.dart';
import '../widgets/custom_app_bar.dart';
import '../core/providers/auth_provider.dart';
import '../core/theme/app_theme.dart';

class SignageManagementScreen extends ConsumerStatefulWidget {
  const SignageManagementScreen({Key? key}) : super(key: key);

  @override
  ConsumerState<SignageManagementScreen> createState() => _SignageManagementScreenState();
}

class _SignageManagementScreenState extends ConsumerState<SignageManagementScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  final TextEditingController _searchController = TextEditingController();
  
  // Helper to get SignageProvider without conflict with Riverpod
  SignageProvider _getSignageProvider({bool listen = true}) {
    return provider.Provider.of<SignageProvider>(context, listen: listen);
  }

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
    
    // Load initial data
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final signageProvider = _getSignageProvider(listen: false);
      signageProvider.loadVideoLists();
      signageProvider.loadDevices();
    });
  }

  @override
  void dispose() {
    _tabController.dispose();
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: PreferredSize(
        preferredSize: const Size.fromHeight(kToolbarHeight + kTextTabBarHeight),
        child: CustomAppBar(
          title: 'Signage Management',
          actions: [
            IconButton(
              icon: const Icon(Icons.refresh),
              onPressed: _refreshAll,
              tooltip: 'Refresh all data',
            ),
          ],
        ),
      ),
      body: Column(
        children: [
          // Tab bar below the CustomAppBar
          Container(
            color: AppColors.surface,
            child: TabBar(
              controller: _tabController,
              tabs: const [
                Tab(icon: Icon(Icons.playlist_play), text: 'Playlists'),
                Tab(icon: Icon(Icons.devices), text: 'Devices'),
                Tab(icon: Icon(Icons.play_circle), text: 'Control'),
              ],
            ),
          ),
          Expanded(
            child: TabBarView(
              controller: _tabController,
              children: [
                _buildPlaylistsTab(),
                _buildDevicesTab(),
                _buildControlTab(),
              ],
            ),
          ),
        ],
      ),
      floatingActionButton: _tabController.index == 0
          ? FloatingActionButton.extended(
              onPressed: _showCreatePlaylistDialog,
              icon: const Icon(Icons.add),
              label: const Text('New Playlist'),
            )
          : null,
    );
  }

  // ==================== Playlists Tab ====================

  Widget _buildPlaylistsTab() {
    return provider.Consumer<SignageProvider>(
      builder: (context, provider, child) {
        if (provider.isLoadingLists && provider.videoLists.isEmpty) {
          return const Center(child: CircularProgressIndicator());
        }

        if (provider.listsError != null) {
          return Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(Icons.error_outline, size: 64, color: Colors.red[300]),
                const SizedBox(height: 16),
                Text(provider.listsError!),
                const SizedBox(height: 16),
                ElevatedButton(
                  onPressed: () => provider.loadVideoLists(),
                  child: const Text('Retry'),
                ),
              ],
            ),
          );
        }

        if (provider.videoLists.isEmpty) {
          return Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(Icons.playlist_add, size: 64, color: Colors.grey[400]),
                const SizedBox(height: 16),
                Text(
                  'No playlists yet',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                const SizedBox(height: 8),
                const Text('Create your first playlist to get started'),
                const SizedBox(height: 24),
                ElevatedButton.icon(
                  onPressed: _showCreatePlaylistDialog,
                  icon: const Icon(Icons.add),
                  label: const Text('Create Playlist'),
                ),
              ],
            ),
          );
        }

        return Column(
          children: [
            // Search bar
            Padding(
              padding: const EdgeInsets.all(16.0),
              child: TextField(
                controller: _searchController,
                decoration: InputDecoration(
                  hintText: 'Search playlists...',
                  prefixIcon: const Icon(Icons.search),
                  suffixIcon: _searchController.text.isNotEmpty
                      ? IconButton(
                          icon: const Icon(Icons.clear),
                          onPressed: () {
                            _searchController.clear();
                            provider.loadVideoLists();
                          },
                        )
                      : null,
                  border: const OutlineInputBorder(),
                ),
                onSubmitted: (value) {
                  provider.loadVideoLists(search: value);
                },
              ),
            ),

            // Playlists list
            Expanded(
              child: ListView.builder(
                itemCount: provider.videoLists.length,
                itemBuilder: (context, index) {
                  final playlist = provider.videoLists[index];
                  return _buildPlaylistCard(playlist);
                },
              ),
            ),
          ],
        );
      },
    );
  }

  Widget _buildPlaylistCard(VideoList playlist) {
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: ListTile(
        leading: CircleAvatar(
          child: Text(playlist.videoCount?.toString() ?? '0'),
        ),
        title: Text(playlist.name),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (playlist.description != null) Text(playlist.description!),
            const SizedBox(height: 4),
            Text(
              '${playlist.videoCount ?? 0} videos • '
              '${_formatDuration(playlist.totalDurationMs ?? 0)}',
              style: TextStyle(color: Colors.grey[600], fontSize: 12),
            ),
          ],
        ),
        trailing: PopupMenuButton<String>(
          onSelected: (value) => _handlePlaylistAction(value, playlist),
          itemBuilder: (context) => [
            const PopupMenuItem(value: 'edit', child: Text('Edit')),
            const PopupMenuItem(value: 'sync', child: Text('Sync to Devices')),
            const PopupMenuItem(value: 'duplicate', child: Text('Duplicate')),
            const PopupMenuItem(
              value: 'delete',
              child: Text('Delete', style: TextStyle(color: Colors.red)),
            ),
          ],
        ),
        onTap: () => _showPlaylistDetails(playlist),
      ),
    );
  }

  // ==================== Devices Tab ====================

  Widget _buildDevicesTab() {
    return provider.Consumer<SignageProvider>(
      builder: (context, provider, child) {
        if (provider.isLoadingDevices && provider.devices.isEmpty) {
          return const Center(child: CircularProgressIndicator());
        }

        if (provider.devicesError != null) {
          return Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(Icons.error_outline, size: 64, color: Colors.red[300]),
                const SizedBox(height: 16),
                Text(provider.devicesError!),
                const SizedBox(height: 16),
                ElevatedButton(
                  onPressed: () => provider.loadDevices(),
                  child: const Text('Retry'),
                ),
              ],
            ),
          );
        }

        if (provider.devices.isEmpty) {
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
                const Text('Make sure signage devices are online'),
                const SizedBox(height: 24),
                ElevatedButton.icon(
                  onPressed: () => provider.loadDevices(),
                  icon: const Icon(Icons.refresh),
                  label: const Text('Refresh'),
                ),
              ],
            ),
          );
        }

        return ListView.builder(
          padding: const EdgeInsets.all(16),
          itemCount: provider.devices.length,
          itemBuilder: (context, index) {
            final device = provider.devices[index];
            final status = provider.deviceStatuses[device.id];
            return _buildDeviceCard(device, status);
          },
        );
      },
    );
  }

  Widget _buildDeviceCard(SignageDevice device, PlaybackStatus? status) {
    final isOnline = device.isOnline;
    
    return Card(
      margin: const EdgeInsets.only(bottom: 16),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  width: 12,
                  height: 12,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: isOnline ? Colors.green : Colors.red,
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
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      Text(
                        '${device.host}:${device.port}',
                        style: TextStyle(color: Colors.grey[600], fontSize: 12),
                      ),
                    ],
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.more_vert),
                  onPressed: () => _showDeviceOptions(device),
                ),
              ],
            ),
            
            if (status != null) ...[
              const Divider(height: 24),
              _buildDeviceStatus(status),
            ],

            const SizedBox(height: 16),
            // Simplified actions - Playback controls on Control tab
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: [
                _buildDeviceAction(
                  icon: Icons.sync,
                  label: 'Sync',
                  onPressed: isOnline ? () => _syncToDevice(device) : null,
                ),
                _buildDeviceAction(
                  icon: Icons.info_outline,
                  label: 'Details',
                  onPressed: () => _showDeviceOptions(device),
                ),
                _buildDeviceAction(
                  icon: Icons.settings_remote,
                  label: 'Control',
                  onPressed: isOnline ? () => _goToControl(device) : null,
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDeviceStatus(PlaybackStatus status) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (status.currentVideo != null) ...[
          Text(
            'Now Playing:',
            style: TextStyle(
              fontWeight: FontWeight.bold,
              color: Colors.grey[600],
            ),
          ),
          const SizedBox(height: 4),
          Text(status.currentVideo!.title),
          LinearProgressIndicator(
            value: status.currentVideo!.progressPercent / 100,
          ),
        ],
        if (status.playlist != null) ...[
          const SizedBox(height: 8),
          Text(
            'Playlist: ${status.playlist!.name}',
            style: TextStyle(color: Colors.grey[600], fontSize: 12),
          ),
          Text(
            'Video ${status.playlist!.currentIndex + 1} of ${status.playlist!.totalVideos}',
            style: TextStyle(color: Colors.grey[600], fontSize: 12),
          ),
        ],
      ],
    );
  }

  Widget _buildDeviceAction({
    required IconData icon,
    required String label,
    VoidCallback? onPressed,
  }) {
    final isEnabled = onPressed != null;
    return Column(
      children: [
        IconButton(
          icon: Icon(icon),
          onPressed: onPressed,
          color: isEnabled ? Theme.of(context).colorScheme.primary : null,
          disabledColor: Colors.grey[400],
        ),
        Text(
          label,
          style: TextStyle(
            fontSize: 12,
            color: isEnabled ? Theme.of(context).colorScheme.onSurface : Colors.grey[600],
          ),
        ),
      ],
    );
  }

  // ==================== Control Tab ====================

  Widget _buildControlTab() {
    return provider.Consumer<SignageProvider>(
      builder: (context, provider, child) {
        if (provider.selectedDevice == null) {
          return Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(Icons.touch_app, size: 64, color: Colors.grey[400]),
                const SizedBox(height: 16),
                Text(
                  'Select a device',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                const SizedBox(height: 8),
                const Text('Go to Devices tab and select a device to control'),
              ],
            ),
          );
        }

        return PlaybackControls(device: provider.selectedDevice!);
      },
    );
  }

  // ==================== Actions ====================

  Future<void> _refreshAll() async {
    final provider = _getSignageProvider(listen: false);
    await Future.wait([
      provider.loadVideoLists(),
      provider.refreshDevices(),
    ]);
  }

  void _showCreatePlaylistDialog() {
    showDialog(
      context: context,
      builder: (dialogContext) => provider.ChangeNotifierProvider<SignageProvider>.value(
        value: _getSignageProvider(listen: false),
        child: const VideoListBuilder(),
      ),
    );
  }

  void _showPlaylistDetails(VideoList playlist) {
    _getSignageProvider(listen: false).selectVideoList(playlist);
    showDialog(
      context: context,
      builder: (dialogContext) => provider.ChangeNotifierProvider<SignageProvider>.value(
        value: _getSignageProvider(listen: false),
        child: VideoListBuilder(videoList: playlist),
      ),
    );
  }

  void _handlePlaylistAction(String action, VideoList playlist) async {
    final provider = _getSignageProvider(listen: false);
    
    switch (action) {
      case 'edit':
        _showPlaylistDetails(playlist);
        break;
      case 'sync':
        _showSyncDialog(playlist);
        break;
      case 'duplicate':
        // TODO: Implement duplicate
        break;
      case 'delete':
        _confirmDeletePlaylist(playlist);
        break;
    }
  }

  void _showSyncDialog(VideoList playlist) {
    final signageProvider = _getSignageProvider(listen: false);
    final onlineDevices = signageProvider.onlineDevices;
    
    showDialog(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: Text('Sync "${playlist.name}"'),
        content: onlineDevices.isEmpty
            ? const Text('No online devices available')
            : Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Text('Select devices to sync:'),
                  const SizedBox(height: 16),
                  ...onlineDevices.map((device) => CheckboxListTile(
                    title: Text(device.name),
                    value: true,
                    onChanged: (value) {},
                  )),
                ],
              ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () async {
              final signageProvider = _getSignageProvider(listen: false);
              final success = await signageProvider.syncToAllDevices(playlist.id);
              if (mounted && dialogContext.mounted) {
                Navigator.pop(dialogContext);
                if (mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(
                      content: Text(success
                          ? 'Sync started successfully'
                          : 'Failed to start sync'),
                    ),
                  );
                }
              }
            },
            child: const Text('Sync'),
          ),
        ],
      ),
    );
  }

  void _confirmDeletePlaylist(VideoList playlist) {
    showDialog(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Delete Playlist'),
        content: Text('Are you sure you want to delete "${playlist.name}"?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () async {
              final provider = _getSignageProvider(listen: false);
              final success = await provider.deleteVideoList(playlist.id);
              if (mounted && dialogContext.mounted) {
                Navigator.pop(dialogContext);
                if (mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(
                      content: Text(success
                          ? 'Playlist deleted'
                          : 'Failed to delete playlist'),
                    ),
                  );
                }
              }
            },
            style: ElevatedButton.styleFrom(backgroundColor: Colors.red),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
  }

  void _showDeviceOptions(SignageDevice device) {
    _getSignageProvider(listen: false).selectDevice(device);
    _tabController.animateTo(2); // Switch to Control tab
  }

  Future<void> _syncToDevice(SignageDevice device) async {
    // Show playlist selection dialog
    final provider = _getSignageProvider(listen: false);
    
    if (provider.videoLists.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('No playlists available to sync')),
      );
      return;
    }

    final playlist = await showDialog<VideoList>(
      context: context,
      builder: (context) => SimpleDialog(
        title: const Text('Select Playlist to Sync'),
        children: provider.videoLists.map((list) {
          return SimpleDialogOption(
            child: Text(list.name),
            onPressed: () => Navigator.pop(context, list),
          );
        }).toList(),
      ),
    );

    if (playlist != null) {
      final success = await provider.syncVideoListToDevices(
        videoListId: playlist.id,
        deviceIds: [device.id],
      );

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(success
                ? 'Sync started successfully'
                : 'Failed to start sync'),
          ),
        );
      }
    }
  }

  void _goToControl(SignageDevice device) {
    // Select this device and navigate to Control tab
    _getSignageProvider(listen: false).selectDevice(device);
    _tabController.animateTo(2); // Switch to Control tab (index 2)
  }

  // ==================== Utilities ====================

  String _formatDuration(int milliseconds) {
    final duration = Duration(milliseconds: milliseconds);
    final hours = duration.inHours;
    final minutes = duration.inMinutes.remainder(60);
    
    if (hours > 0) {
      return '${hours}h ${minutes}m';
    }
    return '${minutes}m';
  }
}
