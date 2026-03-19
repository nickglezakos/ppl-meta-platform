import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/models/camera.dart';
import '../../../core/providers/camera_status_providers.dart';
import '../../../utils/offline_fonts.dart';
import '../../../core/theme/app_theme.dart';
import '../../widgets/camera/camera_stream_player_simple.dart';

/// Multi-stream viewer showing multiple cameras simultaneously in a grid layout
class MultiStreamPage extends ConsumerStatefulWidget {
  final List<Camera> cameras;

  const MultiStreamPage({
    super.key,
    required this.cameras,
  });

  @override
  ConsumerState<MultiStreamPage> createState() => _MultiStreamPageState();
}

class _MultiStreamPageState extends ConsumerState<MultiStreamPage> {
  // Track which cameras are actually streaming (connected)
  Set<String> _activeStreams = {};
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _initializeStreams();
  }

  void _initializeStreams() {
    // Filter to only show connected cameras
    setState(() {
      _activeStreams = widget.cameras
          .where((camera) {
            final status = ref.read(cameraStatusProvider(camera.deviceId));
            return status?.isConnected ?? false;
          })
          .map((c) => c.deviceId)
          .toSet();
      _isLoading = false;
    });
  }

  int _getGridColumns() {
    final count = _activeStreams.length;
    if (count == 1) return 1;
    if (count == 2) return 2;
    if (count <= 4) return 2;
    if (count <= 6) return 3;
    return 4;
  }

  @override
  Widget build(BuildContext context) {
    final connectedCameras = widget.cameras.where((camera) {
      final status = ref.watch(cameraStatusProvider(camera.deviceId));
      return status?.isConnected ?? false;
    }).toList();

    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        title: Text(
          'Live Streams (${connectedCameras.length})',
          style: OfflineFonts.inter(
            fontSize: 18,
            fontWeight: FontWeight.w600,
            color: Colors.white,
          ),
        ),
        backgroundColor: Colors.black,
        iconTheme: const IconThemeData(color: Colors.white),
        actions: [
          // Grid layout toggle
          PopupMenuButton<int>(
            icon: const Icon(Icons.grid_view, color: Colors.white),
            tooltip: 'Grid Layout',
            itemBuilder: (context) => [
              const PopupMenuItem(
                value: 1,
                child: Text('1 Column'),
              ),
              const PopupMenuItem(
                value: 2,
                child: Text('2 Columns'),
              ),
              const PopupMenuItem(
                value: 3,
                child: Text('3 Columns'),
              ),
              const PopupMenuItem(
                value: 4,
                child: Text('4 Columns'),
              ),
            ],
            onSelected: (columns) {
              // Rebuild with new column count
              setState(() {});
            },
          ),
          IconButton(
            icon: const Icon(Icons.refresh, color: Colors.white),
            tooltip: 'Refresh Streams',
            onPressed: () {
              setState(() {
                _isLoading = true;
              });
              Future.delayed(const Duration(milliseconds: 500), () {
                if (mounted) {
                  _initializeStreams();
                }
              });
            },
          ),
        ],
      ),
      body: _isLoading
          ? const Center(
              child: CircularProgressIndicator(color: Colors.white),
            )
          : connectedCameras.isEmpty
              ? _buildEmptyState()
              : _buildStreamGrid(connectedCameras),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(
            Icons.videocam_off,
            size: 64,
            color: Colors.white54,
          ),
          const SizedBox(height: 16),
          Text(
            'No connected cameras',
            style: OfflineFonts.inter(
              fontSize: 18,
              fontWeight: FontWeight.w500,
              color: Colors.white70,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'Connect cameras first to view streams',
            style: OfflineFonts.inter(
              fontSize: 14,
              color: Colors.white54,
            ),
          ),
          const SizedBox(height: 24),
          ElevatedButton.icon(
            onPressed: () => Navigator.of(context).pop(),
            icon: const Icon(Icons.arrow_back),
            label: const Text('Back to Cameras'),
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.primary,
              foregroundColor: Colors.white,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildStreamGrid(List<Camera> connectedCameras) {
    final columns = _getGridColumns();

    return LayoutBuilder(
      builder: (context, constraints) {
        return GridView.builder(
          padding: const EdgeInsets.all(8),
          gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: columns,
            crossAxisSpacing: 8,
            mainAxisSpacing: 8,
            childAspectRatio: 16 / 9, // Standard video aspect ratio
          ),
          itemCount: connectedCameras.length,
          itemBuilder: (context, index) {
            final camera = connectedCameras[index];
            return _buildStreamTile(camera);
          },
        );
      },
    );
  }

  Widget _buildStreamTile(Camera camera) {
    final status = ref.watch(cameraStatusProvider(camera.deviceId));

    return Container(
      decoration: BoxDecoration(
        color: Colors.grey[900],
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: status?.isConnected == true ? Colors.green : Colors.red,
          width: 2,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Camera name header
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(
              color: Colors.black87,
              borderRadius: const BorderRadius.only(
                topLeft: Radius.circular(6),
                topRight: Radius.circular(6),
              ),
            ),
            child: Row(
              children: [
                // Status indicator
                Container(
                  width: 8,
                  height: 8,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: status?.isConnected == true ? Colors.green : Colors.red,
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    camera.name ?? camera.deviceId,
                    style: OfflineFonts.inter(
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                      color: Colors.white,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                // Resolution badge
                if (camera.resolution != null)
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                    decoration: BoxDecoration(
                      color: Colors.white12,
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text(
                      camera.resolution!,
                      style: OfflineFonts.inter(
                        fontSize: 10,
                        color: Colors.white70,
                      ),
                    ),
                  ),
              ],
            ),
          ),
          // Stream player
          Expanded(
            child: ClipRRect(
              borderRadius: const BorderRadius.only(
                bottomLeft: Radius.circular(6),
                bottomRight: Radius.circular(6),
              ),
              child: status?.isConnected == true
                  ? RepaintBoundary(
                      // Isolate each stream to prevent cross-interference
                      child: CameraStreamPlayerSimple(
                        key: ValueKey('multistream_${camera.deviceId}'),
                        cameraId: camera.deviceId,
                      ),
                    )
                  : _buildDisconnectedOverlay(camera),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDisconnectedOverlay(Camera camera) {
    return Container(
      color: Colors.black87,
      child: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(
              Icons.videocam_off,
              size: 32,
              color: Colors.white54,
            ),
            const SizedBox(height: 8),
            Text(
              'Disconnected',
              style: OfflineFonts.inter(
                fontSize: 12,
                color: Colors.white54,
              ),
            ),
          ],
        ),
      ),
    );
  }

  @override
  void dispose() {
    // Note: We don't stop streams here as they might be controlled elsewhere
    // The backend will auto-stop streams when no longer needed
    super.dispose();
  }
}
