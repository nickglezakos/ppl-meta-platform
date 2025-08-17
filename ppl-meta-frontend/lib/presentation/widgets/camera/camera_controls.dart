import 'package:flutter/material.dart';
import '../../../core/models/camera.dart';
import '../../../core/services/camera_service.dart';
import '../../../core/providers/camera_providers.dart';

class CameraControls extends StatelessWidget {
  final Camera camera;
  final CameraStreamState streamState;
  final VoidCallback onStartStream;
  final VoidCallback onStopStream;

  const CameraControls({
    super.key,
    required this.camera,
    required this.streamState,
    required this.onStartStream,
    required this.onStopStream,
  });

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Stream controls
        Row(
          children: [
            // Start/Stop stream button
            Expanded(
              child: ElevatedButton.icon(
                onPressed: streamState.isLoading
                    ? null
                    : streamState.isStreaming
                        ? onStopStream
                        : onStartStream,
                icon: streamState.isLoading
                    ? const SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : Icon(
                        streamState.isStreaming
                            ? Icons.stop_circle
                            : Icons.play_circle,
                      ),
                label: Text(
                  streamState.isLoading
                      ? 'Loading...'
                      : streamState.isStreaming
                          ? 'Stop Stream'
                          : 'Start Stream',
                ),
                style: ElevatedButton.styleFrom(
                  backgroundColor: streamState.isStreaming
                      ? Colors.red.withOpacity(0.1)
                      : colorScheme.primary.withOpacity(0.1),
                  foregroundColor: streamState.isStreaming
                      ? Colors.red
                      : colorScheme.primary,
                  padding: const EdgeInsets.symmetric(vertical: 12),
                ),
              ),
            ),
          ],
        ),

        const SizedBox(height: 12),

        // Stream status info
        if (streamState.isStreaming && streamState.streamUrl != null)
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: colorScheme.surface,
              borderRadius: BorderRadius.circular(8),
              border: Border.all(
                color: colorScheme.outline.withOpacity(0.2),
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Stream Information',
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 8),
                _StreamInfoRow(
                  'Status',
                  'ACTIVE',
                ),
                _StreamInfoRow(
                  'Stream URL',
                  streamState.streamUrl!,
                ),
              ],
            ),
          ),

        // Camera connection status
        const SizedBox(height: 12),
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: camera.isConnected
                ? Colors.green.withOpacity(0.1)
                : Colors.orange.withOpacity(0.1),
            borderRadius: BorderRadius.circular(8),
            border: Border.all(
              color: camera.isConnected
                  ? Colors.green.withOpacity(0.3)
                  : Colors.orange.withOpacity(0.3),
            ),
          ),
          child: Row(
            children: [
              Icon(
                camera.isConnected ? Icons.check_circle : Icons.warning,
                color: camera.isConnected ? Colors.green : Colors.orange,
                size: 20,
              ),
              const SizedBox(width: 8),
              Text(
                camera.isConnected
                    ? 'Camera is connected and ready'
                    : 'Camera connection status: ${camera.status}',
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: camera.isConnected ? Colors.green : Colors.orange,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ],
          ),
        ),

        // Quick actions
        const SizedBox(height: 16),
        Text(
          'Quick Actions',
          style: Theme.of(context).textTheme.titleSmall?.copyWith(
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            _QuickActionChip(
              label: 'Test Connection',
              icon: Icons.network_check,
              onTap: () {
                // TODO: Implement test connection
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                    content: Text('Testing camera connection...'),
                  ),
                );
              },
            ),
            _QuickActionChip(
              label: 'Refresh Status',
              icon: Icons.refresh,
              onTap: () {
                // TODO: Implement refresh status
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                    content: Text('Refreshing camera status...'),
                  ),
                );
              },
            ),
            if (camera.isActive)
              _QuickActionChip(
                label: 'View Gallery',
                icon: Icons.photo_library,
                onTap: () {
                  // TODO: Navigate to camera gallery
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(
                      content: Text('Camera gallery coming soon...'),
                    ),
                  );
                },
              ),
          ],
        ),
      ],
    );
  }

  String _formatDateTime(DateTime dateTime) {
    return '${dateTime.day}/${dateTime.month}/${dateTime.year} ${dateTime.hour}:${dateTime.minute.toString().padLeft(2, '0')}';
  }
}

class _StreamInfoRow extends StatelessWidget {
  final String label;
  final String value;

  const _StreamInfoRow(this.label, this.value);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        children: [
          SizedBox(
            width: 80,
            child: Text(
              label,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: Theme.of(context).colorScheme.outline,
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
}

class _QuickActionChip extends StatelessWidget {
  final String label;
  final IconData icon;
  final VoidCallback onTap;

  const _QuickActionChip({
    required this.label,
    required this.icon,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return ActionChip(
      avatar: Icon(icon, size: 16),
      label: Text(label),
      onPressed: onTap,
      backgroundColor: Theme.of(context).colorScheme.surface,
      side: BorderSide(
        color: Theme.of(context).colorScheme.outline.withOpacity(0.2),
      ),
    );
  }
}
