import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/models/camera.dart';
import '../../../core/providers/multi_camera_providers.dart';

/// Enhanced camera card widget with multi-camera support
class CameraCard extends ConsumerWidget {
  final Camera camera;
  final bool showTypeIndicator;
  final VoidCallback? onTap;

  const CameraCard({
    super.key,
    required this.camera,
    this.showTypeIndicator = false,
    this.onTap,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Card(
      elevation: 2,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _buildHeader(context),
              const SizedBox(height: 12),
              _buildInfo(context),
              const SizedBox(height: 16),
              _buildActions(context, ref),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildHeader(BuildContext context) {
    return Row(
      children: [
        _buildStatusIndicator(context),
        const SizedBox(width: 8),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                camera.name,
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
              if (camera.manufacturer != null || camera.model != null)
                Text(
                  '${camera.manufacturer ?? ''} ${camera.model ?? ''}'.trim(),
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: Theme.of(context).colorScheme.onSurfaceVariant,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
            ],
          ),
        ),
        if (showTypeIndicator) _buildTypeIndicator(context),
      ],
    );
  }

  Widget _buildStatusIndicator(BuildContext context) {
    final isActive = camera.isActive;
    final color = isActive ? Colors.green : Colors.grey;
    
    return Container(
      width: 12,
      height: 12,
      decoration: BoxDecoration(
        color: color,
        shape: BoxShape.circle,
        boxShadow: isActive
            ? [
                BoxShadow(
                  color: color.withOpacity(0.3),
                  blurRadius: 4,
                  spreadRadius: 1,
                ),
              ]
            : null,
      ),
    );
  }

  Widget _buildTypeIndicator(BuildContext context) {
    IconData icon;
    String tooltip;
    
    switch (camera.type) {
      case CameraType.usb:
        icon = Icons.usb;
        tooltip = 'USB Camera';
        break;
      case CameraType.rtsp:
        icon = Icons.wifi;
        tooltip = 'RTSP Network Camera';
        break;
      case CameraType.webRtc:
        icon = Icons.web;
        tooltip = 'WebRTC Camera';
        break;
      case CameraType.mjpeg:
        icon = Icons.camera;
        tooltip = 'MJPEG Camera';
        break;
      case CameraType.virtual:
        icon = Icons.computer;
        tooltip = 'Virtual Camera';
        break;
    }

    return Tooltip(
      message: tooltip,
      child: Container(
        padding: const EdgeInsets.all(6),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.primaryContainer,
          borderRadius: BorderRadius.circular(6),
        ),
        child: Icon(
          icon,
          size: 16,
          color: Theme.of(context).colorScheme.onPrimaryContainer,
        ),
      ),
    );
  }

  Widget _buildInfo(BuildContext context) {
    return Column(
      children: [
        _buildInfoRow(context, 'Device ID', camera.deviceId),
        if (camera.resolution != null)
          _buildInfoRow(context, 'Resolution', camera.resolution!),
        _buildInfoRow(context, 'Status', _formatStatus(camera.status)),
        if (camera.lastSeen != null)
          _buildInfoRow(context, 'Last Seen', _formatDateTime(camera.lastSeen!)),
      ],
    );
  }

  Widget _buildInfoRow(BuildContext context, String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 80,
            child: Text(
              '$label:',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                fontWeight: FontWeight.w500,
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildActions(BuildContext context, WidgetRef ref) {
    return Row(
      children: [
        Expanded(
          child: ElevatedButton.icon(
            onPressed: () => _handleStreaming(context, ref),
            icon: Icon(camera.isActive ? Icons.stop : Icons.play_arrow),
            label: Text(camera.isActive ? 'Stop' : 'Start'),
            style: ElevatedButton.styleFrom(
              backgroundColor: camera.isActive
                  ? Theme.of(context).colorScheme.error
                  : Theme.of(context).colorScheme.primary,
            ),
          ),
        ),
        const SizedBox(width: 8),
        ElevatedButton.icon(
          onPressed: () => _handleSnapshot(context, ref),
          icon: const Icon(Icons.camera_alt),
          label: const Text('Snapshot'),
        ),
      ],
    );
  }

  String _formatStatus(String status) {
    return status.split('_').map((word) => 
        word[0].toUpperCase() + word.substring(1).toLowerCase()
    ).join(' ');
  }

  String _formatDateTime(DateTime dateTime) {
    final now = DateTime.now();
    final difference = now.difference(dateTime);

    if (difference.inMinutes < 1) {
      return 'Just now';
    } else if (difference.inHours < 1) {
      return '${difference.inMinutes}m ago';
    } else if (difference.inDays < 1) {
      return '${difference.inHours}h ago';
    } else {
      return '${dateTime.day}/${dateTime.month}/${dateTime.year}';
    }
  }

  Future<void> _handleStreaming(BuildContext context, WidgetRef ref) async {
    try {
      final cameraActions = ref.read(cameraActionsProvider);
      
      if (camera.isActive) {
        await cameraActions.stopStreaming(camera.id);
        if (context.mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Streaming stopped')),
          );
        }
      } else {
        await cameraActions.startStreaming(camera.id);
        if (context.mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Streaming started')),
          );
        }
      }
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Error: $e'),
            backgroundColor: Theme.of(context).colorScheme.error,
          ),
        );
      }
    }
  }

  Future<void> _handleSnapshot(BuildContext context, WidgetRef ref) async {
    try {
      final cameraActions = ref.read(cameraActionsProvider);
      final snapshotUrl = await cameraActions.takeSnapshot(camera.id);
      
      if (context.mounted) {
        _showSnapshotDialog(context, snapshotUrl);
      }
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to take snapshot: $e'),
            backgroundColor: Theme.of(context).colorScheme.error,
          ),
        );
      }
    }
  }

  void _showSnapshotDialog(BuildContext context, String snapshotUrl) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Snapshot - ${camera.name}'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              constraints: const BoxConstraints(maxHeight: 300),
              child: Image.network(
                snapshotUrl,
                fit: BoxFit.contain,
                errorBuilder: (context, error, stackTrace) {
                  return Container(
                    height: 200,
                    decoration: BoxDecoration(
                      color: Theme.of(context).colorScheme.surfaceVariant,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(
                          Icons.error_outline,
                          size: 48,
                          color: Theme.of(context).colorScheme.error,
                        ),
                        const SizedBox(height: 8),
                        Text(
                          'Failed to load snapshot',
                          style: Theme.of(context).textTheme.bodyMedium,
                        ),
                      ],
                    ),
                  );
                },
                loadingBuilder: (context, child, loadingProgress) {
                  if (loadingProgress == null) return child;
                  return Container(
                    height: 200,
                    alignment: Alignment.center,
                    child: CircularProgressIndicator(
                      value: loadingProgress.expectedTotalBytes != null
                          ? loadingProgress.cumulativeBytesLoaded /
                              loadingProgress.expectedTotalBytes!
                          : null,
                    ),
                  );
                },
              ),
            ),
            const SizedBox(height: 16),
            Text(
              'Taken: ${DateTime.now().toString().split('.')[0]}',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Close'),
          ),
          ElevatedButton.icon(
            onPressed: () {
              // TODO: Implement save/share functionality
              Navigator.of(context).pop();
            },
            icon: const Icon(Icons.save),
            label: const Text('Save'),
          ),
        ],
      ),
    );
  }
}
