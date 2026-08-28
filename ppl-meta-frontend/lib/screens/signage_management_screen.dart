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
import '../presentation/widgets/common/ux_breakpoints.dart';
import '../presentation/widgets/common/content_pane.dart';
import '../widgets/responsive_media_gallery.dart';
import '../models/media_models.dart';
import '../services/media_api_client.dart';
import '../core/api/api_client.dart';

class SignageManagementScreen extends ConsumerStatefulWidget {
  const SignageManagementScreen({Key? key}) : super(key: key);

  @override
  ConsumerState<SignageManagementScreen> createState() => _SignageManagementScreenState();
}

class _SignageManagementScreenState extends ConsumerState<SignageManagementScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  final TextEditingController _searchController = TextEditingController();

  /// Currently selected playlist shown in the right detail pane
  /// (master/detail UX mirroring the Collections screen).
  VideoList? _selectedPlaylist;

  /// Whether the right pane shows the settings (edit) view instead of the
  /// playlist content. Toggled via the mode pill in the pane header.
  bool _paneShowSettings = false;

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

        // Resolve the selected playlist against freshly-loaded data so a
        // deleted/refreshed playlist does not leave a stale selection.
        VideoList? selected;
        for (final list in provider.videoLists) {
          if (list.id == _selectedPlaylist?.id) {
            selected = list;
            break;
          }
        }

        final searchAndCreate = Padding(
          padding: const EdgeInsets.all(16.0),
          child: LayoutBuilder(
            builder: (context, constraints) {
              final isCompact = constraints.maxWidth < 700;

              final searchField = TextField(
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
              );

              final newPlaylistButton = ElevatedButton.icon(
                onPressed: _showCreatePlaylistDialog,
                icon: const Icon(Icons.add),
                label: const Text('New Playlist'),
              );

              if (isCompact) {
                return Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    searchField,
                    const SizedBox(height: 12),
                    newPlaylistButton,
                  ],
                );
              }

              return Row(
                children: [
                  Expanded(child: searchField),
                  const SizedBox(width: 16),
                  newPlaylistButton,
                ],
              );
            },
          ),
        );

        final sidebar = Column(
          children: [
            searchAndCreate,
            Expanded(
              child: ListView.builder(
                itemCount: provider.videoLists.length,
                itemBuilder: (context, index) {
                  final playlist = provider.videoLists[index];
                  return _buildPlaylistSidebarTile(
                    playlist,
                    isSelected: selected?.id == playlist.id,
                  );
                },
              ),
            ),
          ],
        );

        final detailPane = selected == null
            ? ContentPane(
                title: 'Playlists',
                subtitle: 'Select a playlist to view its content',
                child: Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.playlist_play,
                          size: 48, color: Colors.grey[400]),
                      const SizedBox(height: 8),
                      Text(
                        'Select a playlist from the list to view its videos',
                        style:
                            TextStyle(color: Colors.grey[600], fontSize: 13),
                      ),
                    ],
                  ),
                ),
              )
            : _buildPlaylistDetailPane(selected);

        return isWide(context)
            ? Row(
                children: [
                  SizedBox(width: kMasterPaneWidth, child: sidebar),
                  const VerticalDivider(width: 1),
                  const SizedBox(width: 4),
                  Expanded(child: detailPane),
                ],
              )
            : (selected == null ? sidebar : detailPane);
      },
    );
  }

  /// Left-sidebar listable item for a playlist with its three-dot actions.
  Widget _buildPlaylistSidebarTile(VideoList playlist,
      {required bool isSelected}) {
    return ListTile(
      selected: isSelected,
      leading: CircleAvatar(
        child: Text(playlist.videoCount?.toString() ?? '0'),
      ),
      title: Text(
        playlist.name,
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
      ),
      subtitle: Text(
        '${playlist.videoCount ?? 0} videos • '
        '${_formatDuration(playlist.totalDurationMs ?? 0)}',
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
      ),
      trailing: PopupMenuButton<String>(
        icon: const Icon(Icons.more_vert),
        tooltip: 'Playlist actions',
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
      onTap: () => _selectPlaylist(playlist),
    );
  }

  Future<void> _selectPlaylist(VideoList playlist) async {
    setState(() {
      _selectedPlaylist = playlist;
      _paneShowSettings = false;
    });
    // The list endpoint only returns summaries (no video_items). Fetch the
    // full detail — videos aggregated from the assigned collections — and
    // update the provider, which refreshes the pane and counters.
    final signageProvider = _getSignageProvider(listen: false);
    await signageProvider.loadVideoList(playlist.id);

    // Re-point _selectedPlaylist at the hydrated full playlist (with its
    // collection_ids, video_items, loop_mode, description, ...) so the
    // settings form is populated with the stored values.
    if (mounted) {
      for (final updated in signageProvider.videoLists) {
        if (updated.id == playlist.id) {
          setState(() => _selectedPlaylist = updated);
          break;
        }
      }
    }
  }


  /// Right pane for the selected playlist: content mode shows the videos
  /// aggregated from the playlist's collections; settings mode renders the
  /// edit-playlist form inline. Switched via the mode toggle pill.
  Widget _buildPlaylistDetailPane(VideoList playlist) {
    // Resolve the latest (hydrated) copy of this playlist from the provider so
    // both the content and settings views reflect the full stored settings
    // (collection_ids, video_items, description, loop_mode, ...).
    final signageProvider = _getSignageProvider(listen: false);
    for (final updated in signageProvider.videoLists) {
      if (updated.id == playlist.id) {
        playlist = updated;
        break;
      }
    }

    final videoItems = playlist.videoItems ?? const <VideoListItem>[];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        ContentBar(
          title: playlist.name,
          subtitle:
              '${videoItems.length} videos • ${_formatDuration(playlist.totalDurationMs ?? 0)}',
          showModePill: true,
          showSettings: _paneShowSettings,
          onToggleMode: () =>
              setState(() => _paneShowSettings = !_paneShowSettings),
        ),
        const SizedBox(height: 8),
        Expanded(
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: _paneShowSettings
                ? _buildPlaylistSettings(playlist)
                : _buildPlaylistContent(playlist, videoItems),
          ),
        ),
      ],
    );
  }

  /// Content mode: the videos of the lists assigned to this playlist,
  /// rendered in the playlist's stored `sequence_order` (backend truth),
  /// with the same standard video items used by the Collections screen
  /// content pane.
  Widget _buildPlaylistContent(
      VideoList playlist, List<VideoListItem> videoItems) {
    // Reuse the authenticated API client from the provider tree so the gallery
    // can reach the media service (without it, media requests fail auth).
    final apiClient = ref.watch(apiClientProvider);
    final mediaClient = MediaApiClient(apiClient);

    // Render the playlist's video_items in their stored sequence_order.
    if (videoItems.isNotEmpty) {
      final orderedItems = [...videoItems]
        ..sort((a, b) => a.sequenceOrder.compareTo(b.sequenceOrder));
      final orderedIds = orderedItems
          .map((i) => i.videoId)
          .where((id) => id.isNotEmpty)
          .toList();

      return FutureBuilder<List<MediaItem>>(
        key: ValueKey('playlist_content_${playlist.id}_${orderedIds.join(',')}'),
        future: () async {
          // /api/v1/media/{media_id} accepts both UUIDs and integer DB IDs,
          // so the playlist's video_id works directly. Failures are skipped
          // per-item so one missing video doesn't blank the pane.
          final items = await Future.wait(
            orderedIds.map((id) async {
              try {
                return await mediaClient.getMediaByUuid(id);
              } catch (_) {
                return null;
              }
            }),
          );
          return items.whereType<MediaItem>().toList();
        }(),
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          final orderedMedia = snapshot.data ?? const <MediaItem>[];
          if (orderedMedia.isEmpty) {
            return Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.video_library_outlined,
                      size: 48, color: Colors.grey[400]),
                  const SizedBox(height: 8),
                  Text(
                    'No videos in this playlist yet',
                    style: TextStyle(color: Colors.grey[600], fontSize: 13),
                  ),
                ],
              ),
            );
          }
          return ResponsiveMediaGallery(
            key: ValueKey('playlist_preloaded_${playlist.id}_${orderedMedia.length}'),
            apiClient: apiClient,
            preloadedItems: orderedMedia, // exact sequence_order from backend
            enableInfiniteScroll: false, // static list — nothing to paginate
            showItemNames: true,
            onItemTap: _openPlaylistItem,
          );
        },
      );
    }

    // Fallback: no hydrated video_items — show the collections' media
    // (create-time playlists, or detail not yet hydrated).
    final collectionIds = <String>{
      ...(playlist.collectionIds ?? const <String>[]),
      ...videoItems.map((i) => i.collectionId).where((c) => c.isNotEmpty),
    }.toList();

    if (collectionIds.isEmpty) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.video_library_outlined,
                size: 48, color: Colors.grey[400]),
            const SizedBox(height: 8),
            Text(
              'No videos in this playlist yet',
              style: TextStyle(color: Colors.grey[600], fontSize: 13),
            ),
            const SizedBox(height: 4),
            Text(
              'Use the mode toggle to edit assigned collections',
              style: TextStyle(color: Colors.grey[500], fontSize: 12),
            ),
          ],
        ),
      );
    }

    return ResponsiveMediaGallery(
      key: ValueKey('playlist_content_${playlist.id}_${collectionIds.join(',')}'),
      apiClient: apiClient,
      filters: MediaSearchFilters(
        collectionIds: collectionIds,
        sortBy: 'created_at',
        sortOrder: 'desc',
      ),
      enableInfiniteScroll: true,
      showItemNames: true,
      onItemTap: _openPlaylistItem,
    );
  }

  /// Open the standard media preview/playback screen for a playlist video —
  /// mirroring the media service — so its back button returns to the playlist.
  void _openPlaylistItem(MediaItem item) {
    // Use push (not go) so the previous route (/signage) stays on the stack
    // and the preview's back button can pop back to it.
    context.push('/media-preview', extra: item);
  }

  /// Settings mode: the existing edit-playlist dialog rendered inline.
  Widget _buildPlaylistSettings(VideoList playlist) {
    final signageProvider = _getSignageProvider(listen: false);
    return provider.ChangeNotifierProvider<SignageProvider>.value(
      value: signageProvider,
      child: VideoListBuilder(
        key: ValueKey('playlist_settings_${playlist.id}'),
        videoList: playlist,
        signageProvider: signageProvider,
        inline: true,
        onClosed: (_) {
          if (mounted) {
            setState(() => _paneShowSettings = false);
          }
        },
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

  void _handlePlaylistAction(String action, VideoList playlist) async {
    switch (action) {
      case 'edit':
        // Open the selected playlist's settings mode in the detail pane.
        setState(() {
          _selectedPlaylist = playlist;
          _paneShowSettings = true;
        });
        _getSignageProvider(listen: false).loadVideoList(playlist.id);
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
