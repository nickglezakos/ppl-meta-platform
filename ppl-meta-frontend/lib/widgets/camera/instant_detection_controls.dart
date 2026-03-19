import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/providers/camera_providers.dart';

/// Compact eye icon button for toggling instant detection on/off.
/// Used in camera card and stream page, next to the recording button.
class InstantDetectionControls extends ConsumerWidget {
  final String cameraId;
  const InstantDetectionControls({super.key, required this.cameraId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final detectionState =
        ref.watch(cameraInstantDetectionProvider(cameraId));
    final detectionNotifier =
        ref.read(cameraInstantDetectionProvider(cameraId).notifier);

    final isActive = detectionState.isDetecting;

    return IconButton(
      onPressed: detectionState.isLoading
          ? null
          : () => detectionNotifier.toggleDetection(),
      icon: detectionState.isLoading
          ? const SizedBox(
              width: 18,
              height: 18,
              child: CircularProgressIndicator(strokeWidth: 2.5),
            )
          : Icon(
              isActive ? Icons.visibility : Icons.visibility_off,
              color: isActive ? Colors.blue : Colors.grey,
            ),
      tooltip: detectionState.isLoading
          ? (isActive ? 'Stopping...' : 'Starting...')
          : (isActive ? 'Stop detection' : 'Start detection'),
    );
  }
}

/// Larger button variant for the stream page controls row.
class StreamInstantDetectionControls extends ConsumerWidget {
  final String cameraId;
  const StreamInstantDetectionControls({super.key, required this.cameraId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final detectionState =
        ref.watch(cameraInstantDetectionProvider(cameraId));
    final detectionNotifier =
        ref.read(cameraInstantDetectionProvider(cameraId).notifier);

    final isActive = detectionState.isDetecting;

    return ElevatedButton.icon(
      onPressed: detectionState.isLoading
          ? null
          : () => detectionNotifier.toggleDetection(),
      icon: detectionState.isLoading
          ? const SizedBox(
              width: 16,
              height: 16,
              child: CircularProgressIndicator(
                strokeWidth: 2,
                color: Colors.white,
              ),
            )
          : Icon(
              isActive ? Icons.visibility : Icons.visibility_off,
              size: 24,
            ),
      label: Text(
        detectionState.isLoading
            ? (isActive ? 'Stopping...' : 'Starting...')
            : (isActive ? 'Stop Detection' : 'Start Detection'),
      ),
      style: ElevatedButton.styleFrom(
        backgroundColor: isActive ? Colors.blue : Colors.grey.shade700,
        foregroundColor: Colors.white,
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
      ),
    );
  }
}
