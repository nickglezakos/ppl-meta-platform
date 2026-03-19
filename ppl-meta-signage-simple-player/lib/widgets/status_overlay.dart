import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:signage_simple_player/services/player_engine.dart';
import 'package:signage_simple_player/services/discovery_service.dart';
import 'package:signage_simple_player/services/history_tracking_service.dart';
import 'package:signage_simple_player/api/signage_api_client.dart';
import 'package:signage_simple_player/config/app_config.dart';

/// Status overlay widget
/// 
/// Displays system information in the top portion of the screen:
/// - Current playlist and video info
/// - Network connectivity status
/// - Discovery service registration
/// - Playback statistics
/// - System time
class StatusOverlay extends StatelessWidget {
  final VoidCallback? onClose;

  const StatusOverlay({
    super.key,
    this.onClose,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            Colors.black.withOpacity(0.9),
            Colors.black.withOpacity(0.7),
            Colors.transparent,
          ],
        ),
      ),
      padding: const EdgeInsets.fromLTRB(24, 24, 24, 48),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: _buildHeader(),
              ),
              if (onClose != null)
                IconButton(
                  icon: const Icon(Icons.close, size: 20),
                  color: Colors.white.withOpacity(0.7),
                  onPressed: onClose,
                ),
            ],
          ),
          const SizedBox(height: 16),
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                flex: 2,
                child: _buildPlaylistInfo(context),
              ),
              const SizedBox(width: 24),
              Expanded(
                child: _buildSystemStatus(context),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildHeader() {
    return Row(
      children: [
        Image.asset(
          'assets/images/eyenet-logo.png',
          height: 40,
          errorBuilder: (context, error, stackTrace) {
            return const SizedBox.shrink();
          },
        ),
      ],
    );
  }

  Widget _buildPlaylistInfo(BuildContext context) {
    final playerEngine = context.watch<SignagePlayerEngine>();
    final currentPlaylist = playerEngine.currentPlaylist;
    final currentVideo = playerEngine.currentVideo;

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(
                Icons.playlist_play,
                color: Colors.white,
                size: 20,
              ),
              const SizedBox(width: 8),
              const Text(
                'Playlist',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          if (currentPlaylist != null) ...[
            _buildInfoRow('Name', currentPlaylist.name),
            _buildInfoRow('Videos', '${currentPlaylist.videos.length}'),
            _buildInfoRow('Loop Mode', _loopModeText(currentPlaylist.loopMode)),
            if (currentVideo != null) ...[
              const Divider(color: Colors.white24, height: 24),
              _buildInfoRow('Now Playing', currentVideo.title),
              _buildInfoRow(
                'Progress',
                '${playerEngine.progressPercent.toStringAsFixed(1)}%',
              ),
            ],
          ] else
            Text(
              'No playlist loaded',
              style: TextStyle(
                color: Colors.white.withOpacity(0.5),
                fontSize: 14,
                fontStyle: FontStyle.italic,
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildSystemStatus(BuildContext context) {
    final discoveryService = context.watch<SignageDiscoveryService>();
    final apiClient = context.watch<SignageApiClient>();
    final historyTracker = context.watch<HistoryTrackingService>();

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(
                Icons.settings_system_daydream,
                color: Colors.white,
                size: 20,
              ),
              const SizedBox(width: 8),
              const Text(
                'System',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          _buildStatusRow(
            'Backend',
            discoveryService.isRegistered,
            discoveryService.isRegistered ? 'Connected' : 'Offline',
          ),
          _buildStatusRow(
            'Discovery',
            discoveryService.isRegistered,
            discoveryService.isRegistered ? 'Registered' : 'Not registered',
          ),
          _buildStatusRow(
            'History',
            historyTracker.isTracking,
            historyTracker.isTracking ? 'Tracking' : 'Paused',
          ),
          const Divider(color: Colors.white24, height: 20),
          _buildInfoRow('HTTP Server', ':${AppConfig.httpServerPort}'),
          _buildInfoRow('Time', _formatTime(DateTime.now())),
        ],
      ),
    );
  }

  Widget _buildInfoRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Flexible(
            flex: 1,
            child: Text(
              label,
              style: TextStyle(
                color: Colors.white.withOpacity(0.7),
                fontSize: 13,
              ),
            ),
          ),
          const SizedBox(width: 8),
          Flexible(
            flex: 2,
            child: Text(
              value,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 13,
                fontWeight: FontWeight.w500,
              ),
              textAlign: TextAlign.right,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildStatusRow(String label, bool isOnline, String status) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Flexible(
            flex: 1,
            child: Text(
              label,
              style: TextStyle(
                color: Colors.white.withOpacity(0.7),
                fontSize: 13,
              ),
            ),
          ),
          const SizedBox(width: 8),
          Flexible(
            flex: 2,
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  width: 8,
                  height: 8,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: isOnline ? Colors.green : Colors.red,
                  ),
                ),
                const SizedBox(width: 6),
                Flexible(
                  child: Text(
                    status,
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 13,
                      fontWeight: FontWeight.w500,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  String _loopModeText(loopMode) {
    switch (loopMode.toString().split('.').last) {
      case 'continuous':
        return 'Continuous';
      case 'once':
        return 'Once';
      case 'single':
        return 'Single';
      default:
        return 'Unknown';
    }
  }

  String _formatTime(DateTime time) {
    return '${time.hour.toString().padLeft(2, '0')}:'
        '${time.minute.toString().padLeft(2, '0')}:'
        '${time.second.toString().padLeft(2, '0')}';
  }
}
