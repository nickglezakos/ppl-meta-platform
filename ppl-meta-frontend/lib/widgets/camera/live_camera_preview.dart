import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../models/camera_device.dart';
import '../../providers/camera_providers.dart';

/// Live camera preview widget with streaming capabilities
/// Shows real-time video feed from selected camera with control overlay
class LiveCameraPreview extends ConsumerStatefulWidget {
  final String? deviceId;
  final double? aspectRatio;
  final bool showControls;
  final Function()? onFullscreen;

  const LiveCameraPreview({
    Key? key,
    this.deviceId,
    this.aspectRatio,
    this.showControls = true,
    this.onFullscreen,
  }) : super(key: key);

  @override
  ConsumerState<LiveCameraPreview> createState() => _LiveCameraPreviewState();
}

class _LiveCameraPreviewState extends ConsumerState<LiveCameraPreview> {
  bool _isFullscreen = false;
  bool _showOverlay = true;

  @override
  Widget build(BuildContext context) {
    if (widget.deviceId == null) {
      return _buildNoDeviceState(context);
    }

    final streamState = ref.watch(cameraStreamProvider(widget.deviceId!));

    return Card(
      clipBehavior: Clip.antiAlias,
      child: AspectRatio(
        aspectRatio: widget.aspectRatio ?? 16 / 9,
        child: Stack(
          children: [
            // Video stream
            _buildVideoStream(context, streamState),
            
            // Control overlay
            if (widget.showControls && _showOverlay)
              _buildControlOverlay(context, streamState),
              
            // Stream quality indicator
            Positioned(
              top: 8,
              right: 8,
              child: StreamQualityIndicator(
                streamState: streamState,
              ),
            ),
            
            // Tap to toggle overlay
            if (widget.showControls)
              GestureDetector(
                onTap: () => setState(() => _showOverlay = !_showOverlay),
                child: Container(
                  width: double.infinity,
                  height: double.infinity,
                  color: Colors.transparent,
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildVideoStream(BuildContext context, CameraStreamState streamState) {
    switch (streamState.status) {
      case StreamStatus.disconnected:
        return _buildDisconnectedState(context);
      case StreamStatus.connecting:
        return _buildConnectingState(context);
      case StreamStatus.connected:
        return _buildConnectedStream(context, streamState);
      case StreamStatus.error:
        return _buildErrorState(context, streamState.error);
    }
  }

  Widget _buildNoDeviceState(BuildContext context) {
    return Container(
      color: Colors.black12,
      child: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.camera_alt_outlined,
              size: 64,
              color: Theme.of(context).colorScheme.outline,
            ),
            const SizedBox(height: 16),
            Text(
              'No Camera Selected',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 8),
            Text(
              'Select a camera device to start preview',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: Theme.of(context).colorScheme.outline,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDisconnectedState(BuildContext context) {
    return Container(
      color: Colors.black,
      child: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.videocam_off,
              size: 64,
              color: Colors.white70,
            ),
            const SizedBox(height: 16),
            Text(
              'Camera Disconnected',
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                color: Colors.white,
              ),
            ),
            const SizedBox(height: 16),
            ElevatedButton.icon(
              onPressed: () => _reconnectStream(),
              icon: const Icon(Icons.refresh),
              label: const Text('Reconnect'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildConnectingState(BuildContext context) {
    return Container(
      color: Colors.black,
      child: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const CircularProgressIndicator(
              color: Colors.white,
            ),
            const SizedBox(height: 16),
            Text(
              'Connecting to Camera...',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                color: Colors.white,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildConnectedStream(BuildContext context, CameraStreamState streamState) {
    // In a real implementation, this would show the actual video stream
    // For now, we'll show a placeholder with stream info
    return Container(
      color: Colors.black,
      child: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.videocam,
              size: 64,
              color: Colors.green,
            ),
            const SizedBox(height: 16),
            Text(
              'Live Stream Active',
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                color: Colors.white,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              '${streamState.resolution} @ ${streamState.fps} FPS',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: Colors.white70,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'Bitrate: ${streamState.bitrate}',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: Colors.white70,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildErrorState(BuildContext context, String? error) {
    return Container(
      color: Colors.black,
      child: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.error_outline,
              size: 64,
              color: Theme.of(context).colorScheme.error,
            ),
            const SizedBox(height: 16),
            Text(
              'Stream Error',
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                color: Colors.white,
              ),
            ),
            if (error != null) ...[
              const SizedBox(height: 8),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 32),
                child: Text(
                  error,
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: Colors.white70,
                  ),
                  textAlign: TextAlign.center,
                ),
              ),
            ],
            const SizedBox(height: 16),
            ElevatedButton.icon(
              onPressed: () => _reconnectStream(),
              icon: const Icon(Icons.refresh),
              label: const Text('Retry'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildControlOverlay(BuildContext context, CameraStreamState streamState) {
    return Positioned.fill(
      child: Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            stops: const [0.0, 0.3, 0.7, 1.0],
            colors: [
              Colors.black.withOpacity(0.5),
              Colors.transparent,
              Colors.transparent,
              Colors.black.withOpacity(0.5),
            ],
          ),
        ),
        child: Column(
          children: [
            // Top controls
            Padding(
              padding: const EdgeInsets.all(16),
              child: Row(
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: Colors.black54,
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text(
                      widget.deviceId ?? 'Unknown Device',
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 12,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ),
                  const Spacer(),
                  if (widget.onFullscreen != null)
                    IconButton(
                      onPressed: widget.onFullscreen,
                      icon: const Icon(
                        Icons.fullscreen,
                        color: Colors.white,
                      ),
                    ),
                ],
              ),
            ),
            
            const Spacer(),
            
            // Bottom controls
            Padding(
              padding: const EdgeInsets.all(16),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                children: [
                  _buildControlButton(
                    icon: Icons.screenshot,
                    label: 'Snapshot',
                    onPressed: () => _takeSnapshot(),
                  ),
                  _buildControlButton(
                    icon: streamState.status == StreamStatus.connected
                        ? Icons.pause
                        : Icons.play_arrow,
                    label: streamState.status == StreamStatus.connected 
                        ? 'Pause' 
                        : 'Play',
                    onPressed: () => _toggleStream(),
                  ),
                  _buildControlButton(
                    icon: Icons.settings,
                    label: 'Settings',
                    onPressed: () => _showStreamSettings(),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildControlButton({
    required IconData icon,
    required String label,
    required VoidCallback onPressed,
  }) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          decoration: BoxDecoration(
            color: Colors.black54,
            shape: BoxShape.circle,
          ),
          child: IconButton(
            onPressed: onPressed,
            icon: Icon(
              icon,
              color: Colors.white,
            ),
          ),
        ),
        const SizedBox(height: 4),
        Text(
          label,
          style: const TextStyle(
            color: Colors.white,
            fontSize: 12,
          ),
        ),
      ],
    );
  }

  void _reconnectStream() {
    if (widget.deviceId != null) {
      ref.read(cameraStreamProvider(widget.deviceId!).notifier).reconnect();
    }
  }

  void _toggleStream() {
    if (widget.deviceId != null) {
      final notifier = ref.read(cameraStreamProvider(widget.deviceId!).notifier);
      final currentState = ref.read(cameraStreamProvider(widget.deviceId!));
      
      if (currentState.status == StreamStatus.connected) {
        notifier.pause();
      } else {
        notifier.resume();
      }
    }
  }

  void _takeSnapshot() {
    if (widget.deviceId != null) {
      ref.read(cameraStreamProvider(widget.deviceId!).notifier).takeSnapshot();
      
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Snapshot saved'),
          duration: Duration(seconds: 2),
        ),
      );
    }
  }

  void _showStreamSettings() {
    showModalBottomSheet(
      context: context,
      builder: (context) => StreamSettingsSheet(
        deviceId: widget.deviceId,
      ),
    );
  }
}

/// Stream quality indicator widget
class StreamQualityIndicator extends StatelessWidget {
  final CameraStreamState streamState;

  const StreamQualityIndicator({
    Key? key,
    required this.streamState,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final quality = _getStreamQuality();
    
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: _getQualityColor(quality),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            _getQualityIcon(quality),
            size: 12,
            color: Colors.white,
          ),
          const SizedBox(width: 4),
          Text(
            quality.name.toUpperCase(),
            style: const TextStyle(
              color: Colors.white,
              fontSize: 10,
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
      ),
    );
  }

  StreamQuality _getStreamQuality() {
    if (streamState.status != StreamStatus.connected) {
      return StreamQuality.offline;
    }
    
    // Determine quality based on resolution and bitrate
    if (streamState.resolution?.contains('1080') == true && 
        (streamState.bitrateKbps ?? 0) > 2000) {
      return StreamQuality.excellent;
    } else if (streamState.resolution?.contains('720') == true && 
               (streamState.bitrateKbps ?? 0) > 1000) {
      return StreamQuality.good;
    } else if ((streamState.bitrateKbps ?? 0) > 500) {
      return StreamQuality.fair;
    } else {
      return StreamQuality.poor;
    }
  }

  Color _getQualityColor(StreamQuality quality) {
    switch (quality) {
      case StreamQuality.excellent:
        return Colors.green;
      case StreamQuality.good:
        return Colors.lightGreen;
      case StreamQuality.fair:
        return Colors.orange;
      case StreamQuality.poor:
        return Colors.red;
      case StreamQuality.offline:
        return Colors.grey;
    }
  }

  IconData _getQualityIcon(StreamQuality quality) {
    switch (quality) {
      case StreamQuality.excellent:
        return Icons.signal_cellular_4_bar;
      case StreamQuality.good:
        return Icons.signal_cellular_3_bar;
      case StreamQuality.fair:
        return Icons.signal_cellular_2_bar;
      case StreamQuality.poor:
        return Icons.signal_cellular_1_bar;
      case StreamQuality.offline:
        return Icons.signal_cellular_off;
    }
  }
}

/// Stream settings bottom sheet
class StreamSettingsSheet extends ConsumerWidget {
  final String? deviceId;

  const StreamSettingsSheet({
    Key? key,
    this.deviceId,
  }) : super(key: key);

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Container(
      padding: const EdgeInsets.all(16),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Stream Settings',
                style: Theme.of(context).textTheme.headlineSmall,
              ),
              IconButton(
                onPressed: () => Navigator.of(context).pop(),
                icon: const Icon(Icons.close),
              ),
            ],
          ),
          const SizedBox(height: 16),
          
          // Quality settings
          ListTile(
            leading: const Icon(Icons.high_quality),
            title: const Text('Stream Quality'),
            subtitle: const Text('Adjust video quality and bitrate'),
            trailing: const Icon(Icons.chevron_right),
            onTap: () {
              // Navigate to quality settings
            },
          ),
          
          // Resolution settings
          ListTile(
            leading: const Icon(Icons.aspect_ratio),
            title: const Text('Resolution'),
            subtitle: const Text('Change video resolution'),
            trailing: const Icon(Icons.chevron_right),
            onTap: () {
              // Navigate to resolution settings
            },
          ),
          
          // Frame rate settings
          ListTile(
            leading: const Icon(Icons.speed),
            title: const Text('Frame Rate'),
            subtitle: const Text('Adjust frames per second'),
            trailing: const Icon(Icons.chevron_right),
            onTap: () {
              // Navigate to frame rate settings
            },
          ),
          
          const SizedBox(height: 16),
        ],
      ),
    );
  }
}

/// Enums for stream state management
enum StreamStatus {
  disconnected,
  connecting,
  connected,
  error,
}

enum StreamQuality {
  excellent,
  good,
  fair,
  poor,
  offline,
}

/// Camera stream state class
class CameraStreamState {
  final StreamStatus status;
  final String? resolution;
  final int? fps;
  final String? bitrate;
  final int? bitrateKbps;
  final String? error;

  const CameraStreamState({
    required this.status,
    this.resolution,
    this.fps,
    this.bitrate,
    this.bitrateKbps,
    this.error,
  });

  CameraStreamState copyWith({
    StreamStatus? status,
    String? resolution,
    int? fps,
    String? bitrate,
    int? bitrateKbps,
    String? error,
  }) {
    return CameraStreamState(
      status: status ?? this.status,
      resolution: resolution ?? this.resolution,
      fps: fps ?? this.fps,
      bitrate: bitrate ?? this.bitrate,
      bitrateKbps: bitrateKbps ?? this.bitrateKbps,
      error: error ?? this.error,
    );
  }
}