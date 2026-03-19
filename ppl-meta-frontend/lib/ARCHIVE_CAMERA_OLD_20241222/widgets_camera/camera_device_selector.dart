import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../models/camera_device.dart';
import '../../providers/camera_providers.dart';
import '../../widgets/common/status_indicator.dart';

/// Widget for selecting and managing camera devices
/// Displays available cameras with status indicators and allows device selection
class CameraDeviceSelector extends ConsumerWidget {
  final Function(String deviceId)? onDeviceSelected;
  final String? selectedDeviceId;

  const CameraDeviceSelector({
    Key? key,
    this.onDeviceSelected,
    this.selectedDeviceId,
  }) : super(key: key);

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final devicesAsyncValue = ref.watch(cameraDevicesProvider);
    final isRefreshing = ref.watch(cameraDevicesLoadingProvider);

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  'Camera Devices',
                  style: Theme.of(context).textTheme.headlineSmall,
                ),
                IconButton(
                  onPressed: isRefreshing
                      ? null
                      : () => ref.read(cameraDevicesProvider.notifier).refreshDevices(),
                  icon: isRefreshing
                      ? const SizedBox(
                          width: 20,
                          height: 20,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.refresh),
                  tooltip: 'Refresh Devices',
                ),
              ],
            ),
            const SizedBox(height: 16),
            devicesAsyncValue.when(
              data: (devices) => _buildDeviceGrid(context, devices),
              loading: () => const Center(
                child: Padding(
                  padding: EdgeInsets.all(32.0),
                  child: CircularProgressIndicator(),
                ),
              ),
              error: (error, stack) => _buildErrorState(context, error),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDeviceGrid(BuildContext context, List<CameraDevice> devices) {
    if (devices.isEmpty) {
      return _buildEmptyState(context);
    }

    return GridView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 2,
        childAspectRatio: 1.5,
        crossAxisSpacing: 8,
        mainAxisSpacing: 8,
      ),
      itemCount: devices.length,
      itemBuilder: (context, index) {
        final device = devices[index];
        return CameraDeviceCard(
          device: device,
          isSelected: device.deviceId == selectedDeviceId,
          onTap: () => onDeviceSelected?.call(device.deviceId),
        );
      },
    );
  }

  Widget _buildEmptyState(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(32),
      child: Column(
        children: [
          Icon(
            Icons.camera_alt_outlined,
            size: 64,
            color: Theme.of(context).colorScheme.outline,
          ),
          const SizedBox(height: 16),
          Text(
            'No Cameras Detected',
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          const SizedBox(height: 8),
          Text(
            'Make sure your cameras are connected and powered on',
            style: Theme.of(context).textTheme.bodyMedium,
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }

  Widget _buildErrorState(BuildContext context, Object error) {
    return Container(
      padding: const EdgeInsets.all(32),
      child: Column(
        children: [
          Icon(
            Icons.error_outline,
            size: 64,
            color: Theme.of(context).colorScheme.error,
          ),
          const SizedBox(height: 16),
          Text(
            'Failed to Load Cameras',
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          const SizedBox(height: 8),
          Text(
            error.toString(),
            style: Theme.of(context).textTheme.bodyMedium,
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }
}

/// Individual camera device card widget
class CameraDeviceCard extends StatelessWidget {
  final CameraDevice device;
  final bool isSelected;
  final VoidCallback? onTap;

  const CameraDeviceCard({
    Key? key,
    required this.device,
    this.isSelected = false,
    this.onTap,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Card(
      elevation: isSelected ? 8 : 2,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(8),
        child: Container(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(8),
            border: isSelected
                ? Border.all(
                    color: colorScheme.primary,
                    width: 2,
                  )
                : null,
          ),
          padding: const EdgeInsets.all(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      device.name,
                      style: theme.textTheme.titleMedium?.copyWith(
                        fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  StatusIndicator(
                    status: device.status,
                    size: 8,
                  ),
                ],
              ),
              const SizedBox(height: 4),
              Text(
                device.cameraType.displayName,
                style: theme.textTheme.bodySmall,
              ),
              const Spacer(),
              Row(
                children: [
                  Icon(
                    Icons.videocam,
                    size: 16,
                    color: colorScheme.outline,
                  ),
                  const SizedBox(width: 4),
                  Text(
                    device.resolution,
                    style: theme.textTheme.bodySmall,
                  ),
                  const Spacer(),
                  if (device.supportsStreaming)
                    Icon(
                      Icons.stream,
                      size: 16,
                      color: colorScheme.primary,
                    ),
                ],
              ),
              if (device.lastSeen != null)
                Padding(
                  padding: const EdgeInsets.only(top: 4),
                  child: Text(
                    'Last seen: ${_formatLastSeen(device.lastSeen!)}',
                    style: theme.textTheme.caption?.copyWith(
                      color: colorScheme.outline,
                    ),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }

  String _formatLastSeen(DateTime lastSeen) {
    final now = DateTime.now();
    final difference = now.difference(lastSeen);

    if (difference.inMinutes < 1) {
      return 'Just now';
    } else if (difference.inMinutes < 60) {
      return '${difference.inMinutes}m ago';
    } else if (difference.inHours < 24) {
      return '${difference.inHours}h ago';
    } else {
      return '${difference.inDays}d ago';
    }
  }
}