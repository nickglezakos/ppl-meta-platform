/// Playback Controls Widget
/// Detailed remote control interface for signage devices

import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../models/signage_models.dart';
import '../../providers/signage_provider.dart';

class PlaybackControls extends StatefulWidget {
  final SignageDevice device;

  const PlaybackControls({
    Key? key,
    required this.device,
  }) : super(key: key);

  @override
  State<PlaybackControls> createState() => _PlaybackControlsState();
}

class _PlaybackControlsState extends State<PlaybackControls> {
  double _volume = 100.0;
  bool _autoRefresh = true;
  bool _isSelectingPlaylist = false;
  bool _pauseStatusRefresh = false;

  @override
  void initState() {
    super.initState();
    _loadStatus();
    _startAutoRefresh();
  }

  @override
  void dispose() {
    _autoRefresh = false;
    super.dispose();
  }

  Future<void> _loadStatus() async {
    await context.read<SignageProvider>().loadDeviceStatus(widget.device.id);
  }

  void _startAutoRefresh() {
    Future.doWhile(() async {
      if (!_autoRefresh || !mounted) return false;
      await Future.delayed(const Duration(seconds: 3));
      if (_autoRefresh && mounted && !_pauseStatusRefresh) {
        await _loadStatus();
      }
      return _autoRefresh;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<SignageProvider>(
      builder: (context, provider, child) {
        final status = provider.deviceStatuses[widget.device.id];
        final isOnline = widget.device.isOnline;

        return Card(
          margin: const EdgeInsets.all(16),
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: SingleChildScrollView(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // Device header
                  _buildDeviceHeader(isOnline),
                  const SizedBox(height: 24),
                  
                  // Current playback info
                  if (status != null) ...[
                    _buildPlaybackInfo(status),
                    const SizedBox(height: 24),
                  ],
                  
                  // Main controls
                  _buildMainControls(provider, status, isOnline),
                  const SizedBox(height: 24),
                  
                  // Playlist selector
                  _buildPlaylistSelector(provider, status, isOnline),
                  const SizedBox(height: 24),
                  
                  // Volume control
                  _buildVolumeControl(isOnline),
                  const SizedBox(height: 24),
                  
                  // Playback history
                  if (status != null && status.historyCount > 0) ...[
                    _buildHistorySection(status),
                  ],
                ],
              ),
            ),
          ),
        );
      },
    );
  }

  Widget _buildDeviceHeader(bool isOnline) {
    return Row(
      children: [
        Container(
          width: 20,
          height: 20,
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
        const SizedBox(width: 16),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                widget.device.name,
                style: const TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                ),
              ),
              Text(
                '${widget.device.host}:${widget.device.port}',
                style: TextStyle(
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                  fontSize: 14,
                ),
              ),
            ],
          ),
        ),
        IconButton(
          icon: const Icon(Icons.refresh),
          tooltip: 'Refresh Status',
          onPressed: _loadStatus,
        ),
      ],
    );
  }

  Widget _buildPlaybackInfo(PlaybackStatus status) {
    final currentVideo = status.currentVideo;
    
    if (currentVideo == null) {
      return Container(
        padding: const EdgeInsets.all(24),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceVariant,
          borderRadius: BorderRadius.circular(8),
        ),
        child: Center(
          child: Text(
            'No video currently playing',
            style: TextStyle(
              fontSize: 16,
              fontStyle: FontStyle.italic,
              color: Theme.of(context).colorScheme.onSurfaceVariant,
            ),
          ),
        ),
      );
    }

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            Theme.of(context).primaryColor.withOpacity(0.1),
            Theme.of(context).primaryColor.withOpacity(0.05),
          ],
        ),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                _getPlaybackIcon(status.playbackState),
                color: _getPlaybackColor(status.playbackState),
                size: 32,
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      currentVideo.title,
                      style: const TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                      ),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                    if (status.playlist != null)
                      Text(
                        'From: ${status.playlist!.name}',
                        style: TextStyle(
                          color: Theme.of(context).colorScheme.onSurfaceVariant,
                          fontSize: 12,
                        ),
                      ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          
          // Progress bar
          Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    _formatDuration(currentVideo.currentPosition),
                    style: TextStyle(
                      fontSize: 12,
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                    ),
                  ),
                  Text(
                    '${currentVideo.progressPercent.toStringAsFixed(1)}%',
                    style: const TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  Text(
                    _formatDuration(currentVideo.duration),
                    style: TextStyle(
                      fontSize: 12,
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              LinearProgressIndicator(
                value: currentVideo.progressPercent / 100,
                backgroundColor: Theme.of(context).colorScheme.surfaceVariant,
                minHeight: 8,
              ),
            ],
          ),
          
          if (status.playlist != null) ...[
            const SizedBox(height: 16),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  'Video ${status.playlist!.currentIndex + 1} of ${status.playlist!.totalVideos}',
                  style: TextStyle(
                    fontSize: 12,
                    color: Theme.of(context).colorScheme.onSurface,
                  ),
                ),
                Text(
                  'Loop: ${status.playlist!.loopMode}',
                  style: TextStyle(
                    fontSize: 12,
                    color: Theme.of(context).colorScheme.onSurface,
                  ),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildMainControls(
    SignageProvider provider,
    PlaybackStatus? status,
    bool isOnline,
  ) {
    final isPlaying = status?.playbackState == PlaybackState.playing;
    final isPaused = status?.playbackState == PlaybackState.paused;
    final hasPlaylist = status?.playlist != null;

    // Horizontal scroll keeps transport controls tappable on narrow Android
    // screens where a fixed Row overflows and can steal hit-tests below.
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          _buildControlButton(
            icon: Icons.skip_previous,
            tooltip: 'Previous',
            enabled: isOnline && hasPlaylist,
            onPressed: () => provider.previousVideo(widget.device.id),
          ),
          const SizedBox(width: 16),
          _buildControlButton(
            icon: Icons.stop,
            tooltip: 'Stop',
            enabled: isOnline && (isPlaying || isPaused),
            onPressed: () => provider.stopPlayback(widget.device.id),
            color: Colors.red,
          ),
          const SizedBox(width: 24),
          _buildControlButton(
            icon: isPlaying ? Icons.pause : Icons.play_arrow,
            tooltip: isPlaying ? 'Pause' : (isPaused ? 'Resume' : 'Play'),
            enabled: isOnline && !_isSelectingPlaylist,
            onPressed: () {
              if (isPlaying) {
                provider.pausePlayback(widget.device.id);
              } else if (isPaused) {
                provider.resumePlayback(widget.device.id);
              } else {
                _showPlaylistSelector(provider, status);
              }
            },
            color: Colors.green,
            size: 64,
          ),
          const SizedBox(width: 24),
          _buildControlButton(
            icon: Icons.replay,
            tooltip: 'Restart',
            enabled: isOnline && hasPlaylist,
            onPressed: () => _restartPlaylist(provider, status!),
          ),
          const SizedBox(width: 16),
          _buildControlButton(
            icon: Icons.skip_next,
            tooltip: 'Next',
            enabled: isOnline && hasPlaylist,
            onPressed: () => provider.nextVideo(widget.device.id),
          ),
        ],
      ),
    );
  }

  Widget _buildControlButton({
    required IconData icon,
    required String tooltip,
    required bool enabled,
    required VoidCallback onPressed,
    Color? color,
    double size = 48,
  }) {
    return Container(
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        boxShadow: enabled
            ? [
                BoxShadow(
                  color: (color ?? Theme.of(context).primaryColor)
                      .withOpacity(0.3),
                  blurRadius: 8,
                  spreadRadius: 2,
                )
              ]
            : null,
      ),
      child: IconButton(
        icon: Icon(icon),
        iconSize: size,
        tooltip: tooltip,
        onPressed: enabled ? onPressed : null,
        color: enabled ? (color ?? Theme.of(context).primaryColor) : Colors.grey,
      ),
    );
  }

  Widget _buildPlaylistSelector(
    SignageProvider provider,
    PlaybackStatus? status,
    bool isOnline,
  ) {
    final canOpen = !_isSelectingPlaylist;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          'Playlist',
          style: Theme.of(context).textTheme.titleMedium,
        ),
        const SizedBox(height: 8),
        ElevatedButton.icon(
          // Keep the button tappable even when discovery marks the device
          // briefly offline; we re-check reachability when starting playback.
          onPressed: canOpen
              ? () => _showPlaylistSelector(provider, status)
              : null,
          icon: _isSelectingPlaylist
              ? const SizedBox(
                  width: 18,
                  height: 18,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : const Icon(Icons.playlist_play),
          label: Text(
            _isSelectingPlaylist
                ? 'Loading playlists…'
                : (isOnline
                    ? 'Select & Play Playlist'
                    : 'Select & Play Playlist (device may be offline)'),
          ),
        ),
      ],
    );
  }

  Widget _buildVolumeControl(bool isOnline) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              'Volume',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            Text(
              '${_volume.toInt()}%',
              style: TextStyle(
                fontSize: 14,
                color: Colors.grey[600],
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        Row(
          children: [
            Icon(
              _volume == 0 ? Icons.volume_off : Icons.volume_up,
              color: isOnline ? null : Colors.grey,
            ),
            Expanded(
              child: Slider(
                value: _volume,
                min: 0,
                max: 100,
                divisions: 20,
                onChanged: isOnline
                    ? (value) {
                        setState(() {
                          _volume = value;
                        });
                      }
                    : null,
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildHistorySection(PlaybackStatus status) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              'Playback History',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            Text(
              '${status.historyCount} videos',
              style: TextStyle(
                fontSize: 12,
                color: Colors.grey[600],
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        OutlinedButton.icon(
          onPressed: () => _showFullHistory(status),
          icon: const Icon(Icons.history),
          label: const Text('View Full History'),
        ),
      ],
    );
  }

  IconData _getPlaybackIcon(PlaybackState state) {
    switch (state) {
      case PlaybackState.playing:
        return Icons.play_circle;
      case PlaybackState.paused:
        return Icons.pause_circle;
      case PlaybackState.stopped:
        return Icons.stop_circle;
      case PlaybackState.loading:
        return Icons.refresh;
      case PlaybackState.buffering:
        return Icons.hourglass_empty;
      case PlaybackState.error:
        return Icons.error;
    }
  }

  Color _getPlaybackColor(PlaybackState state) {
    switch (state) {
      case PlaybackState.playing:
        return Colors.green;
      case PlaybackState.paused:
        return Colors.orange;
      case PlaybackState.stopped:
        return Colors.grey;
      case PlaybackState.loading:
        return Colors.lightBlue;
      case PlaybackState.buffering:
        return Colors.blue;
      case PlaybackState.error:
        return Colors.red;
    }
  }

  String _formatDuration(int milliseconds) {
    final duration = Duration(milliseconds: milliseconds);
    final hours = duration.inHours;
    final minutes = duration.inMinutes.remainder(60);
    final seconds = duration.inSeconds.remainder(60);

    if (hours > 0) {
      return '${hours}h ${minutes}m ${seconds}s';
    } else if (minutes > 0) {
      return '${minutes}m ${seconds}s';
    } else {
      return '${seconds}s';
    }
  }

  Future<void> _showPlaylistSelector(
    SignageProvider provider,
    PlaybackStatus? status,
  ) async {
    if (_isSelectingPlaylist) {
      return;
    }

    setState(() {
      _isSelectingPlaylist = true;
      _pauseStatusRefresh = true;
    });

    try {
      final syncedPlaylists = await provider.loadSyncedVideoListsForDevice(
        widget.device.id,
      );

      var candidatePlaylists = List<VideoList>.from(syncedPlaylists);
      var showingFallback = false;

      var currentStatus = status ?? provider.deviceStatuses[widget.device.id];
      if (currentStatus == null) {
        await provider.loadDeviceStatus(widget.device.id);
        if (!mounted) return;
        currentStatus = provider.deviceStatuses[widget.device.id];
      }

      final currentPlaylist = currentStatus?.playlist;
      if (currentPlaylist != null &&
          candidatePlaylists.every(
            (list) =>
                list.id != (currentPlaylist.videoListId ?? currentPlaylist.id),
          )) {
        if (provider.videoLists.isEmpty) {
          await provider.loadVideoLists(limit: 200);
          if (!mounted) return;
        }

        final currentListId =
            currentPlaylist.videoListId ?? currentPlaylist.id;
        final existingCurrent = provider.videoLists
            .where((list) => list.id == currentListId);
        if (existingCurrent.isNotEmpty) {
          candidatePlaylists.insert(0, existingCurrent.first);
        }
      }

      // Android APK users often hit an empty synced list when sync-history
      // mapping fails or is stale; fall back to all playlists so the picker
      // still opens (web felt "working" because that path usually succeeded).
      if (candidatePlaylists.isEmpty) {
        if (provider.videoLists.isEmpty) {
          await provider.loadVideoLists(limit: 200);
          if (!mounted) return;
        }
        candidatePlaylists = List<VideoList>.from(provider.videoLists);
        showingFallback = candidatePlaylists.isNotEmpty;
      }

      if (candidatePlaylists.isEmpty) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text(
                'No playlists available. Sync a playlist to this device first.',
              ),
            ),
          );
        }
        return;
      }

      if (!mounted) {
        return;
      }

      final playlistId = await _pickPlaylist(
        candidatePlaylists: candidatePlaylists,
        currentPlaylist: currentPlaylist,
        showingFallback: showingFallback,
      );

      if (playlistId != null && mounted) {
        final started = await provider.startPlayback(
          deviceId: widget.device.id,
          videoListId: playlistId,
          volume: _volume.toInt(),
        );
        if (!started && mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(
                provider.playbackError ??
                    'Failed to start playback on ${widget.device.name}',
              ),
            ),
          );
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Could not open playlist picker: $e')),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isSelectingPlaylist = false;
          _pauseStatusRefresh = false;
        });
      }
    }
  }

  Future<String?> _pickPlaylist({
    required List<VideoList> candidatePlaylists,
    required PlaylistInfo? currentPlaylist,
    required bool showingFallback,
  }) async {
    final title = showingFallback
        ? 'Select Playlist'
        : 'Select Synced Playlist';
    final subtitle = showingFallback
        ? 'No sync history for this device — showing all playlists'
        : null;

    Widget buildList({required bool shrinkWrap}) {
      return ListView.builder(
        shrinkWrap: shrinkWrap,
        physics: shrinkWrap
            ? const NeverScrollableScrollPhysics()
            : const AlwaysScrollableScrollPhysics(),
        itemCount: candidatePlaylists.length,
        itemBuilder: (context, index) {
          final item = candidatePlaylists[index];
          final isCurrent = currentPlaylist != null &&
              item.id == (currentPlaylist.videoListId ?? currentPlaylist.id);
          final videoCount = item.videoCount ?? item.videoItems?.length ?? 0;

          return ListTile(
            leading: const Icon(Icons.playlist_play),
            title: Text(item.name),
            subtitle: Text(
              isCurrent
                  ? 'Currently active on this device\n$videoCount videos'
                  : '$videoCount videos',
            ),
            onTap: () =>
                Navigator.of(context, rootNavigator: true).pop(item.id),
          );
        },
      );
    }

    // Touch layouts: bottom sheet is reliable on Android. AlertDialog +
    // unbounded ListView often fails to lay out / receive taps on APK.
    final useBottomSheet = !kIsWeb &&
        MediaQuery.sizeOf(context).shortestSide < 900;

    if (useBottomSheet) {
      return showModalBottomSheet<String>(
        context: context,
        useRootNavigator: true,
        isScrollControlled: true,
        showDragHandle: true,
        builder: (context) {
          final height = MediaQuery.sizeOf(context).height * 0.65;
          return SafeArea(
            child: SizedBox(
              height: height,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Padding(
                    padding: const EdgeInsets.fromLTRB(16, 8, 16, 4),
                    child: Text(
                      title,
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                  ),
                  if (subtitle != null)
                    Padding(
                      padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
                      child: Text(
                        subtitle,
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                    ),
                  const Divider(height: 1),
                  Expanded(child: buildList(shrinkWrap: false)),
                ],
              ),
            ),
          );
        },
      );
    }

    return showDialog<String>(
      context: context,
      useRootNavigator: true,
      builder: (context) => AlertDialog(
        title: Text(title),
        content: SizedBox(
          width: 420,
          height: 360,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              if (subtitle != null) ...[
                Text(
                  subtitle,
                  style: Theme.of(context).textTheme.bodySmall,
                ),
                const SizedBox(height: 8),
              ],
              Expanded(child: buildList(shrinkWrap: false)),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () =>
                Navigator.of(context, rootNavigator: true).pop(),
            child: const Text('Cancel'),
          ),
        ],
      ),
    );
  }

  Future<void> _restartPlaylist(
    SignageProvider provider,
    PlaybackStatus status,
  ) async {
    if (status.playlist != null) {
      await provider.startPlayback(
        deviceId: widget.device.id,
        videoListId: status.playlist!.videoListId ?? status.playlist!.id,
        startIndex: 0,
        volume: _volume.toInt(),
      );
    }
  }

  void _showFullHistory(PlaybackStatus status) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Playback History'),
        content: SizedBox(
          width: double.maxFinite,
          child: Text('History count: ${status.historyCount}'),
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
}
