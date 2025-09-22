import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/automatic_face_detection_provider.dart';
import '../core/providers/features_provider.dart';

/// Widget to display automatic face detection status in cameras screen
class AutomaticFaceDetectionStatus extends ConsumerWidget {
  const AutomaticFaceDetectionStatus({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final automaticState = ref.watch(automaticFaceDetectionProvider);
    final featuresState = ref.watch(featuresNotifierProvider);

    return featuresState.when(
      data: (features) => Container(
        padding: const EdgeInsets.all(12),
        margin: const EdgeInsets.only(bottom: 8),
        decoration: BoxDecoration(
          color: automaticState.isGloballyEnabled
              ? Colors.green.withValues(alpha: 0.1)
              : Colors.grey.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(
            color: automaticState.isGloballyEnabled
                ? Colors.green.withValues(alpha: 0.3)
                : Colors.grey.withValues(alpha: 0.3),
          ),
        ),
        child: Row(
          children: [
            Icon(
              automaticState.isGloballyEnabled ? Icons.auto_awesome : Icons.auto_awesome_outlined,
              color: automaticState.isGloballyEnabled ? Colors.green : Colors.grey,
              size: 20,
            ),
            const SizedBox(width: 8),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Automatic Face Detection',
                    style: TextStyle(
                      fontWeight: FontWeight.w600,
                      fontSize: 12,
                      color: automaticState.isGloballyEnabled ? Colors.green : Colors.grey[600],
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    automaticState.isGloballyEnabled
                        ? 'Camera recordings will trigger face detection automatically'
                        : 'Disabled - recordings will not trigger face detection',
                    style: TextStyle(
                      fontSize: 10,
                      color: automaticState.isGloballyEnabled ? Colors.green[700] : Colors.grey[600],
                    ),
                  ),
                  if (automaticState.lastUpdated != null) ...[
                    const SizedBox(height: 2),
                    Text(
                      'Last updated: ${_formatDateTime(automaticState.lastUpdated!)}',
                      style: TextStyle(
                        fontSize: 9,
                        color: Colors.grey[500],
                        fontStyle: FontStyle.italic,
                      ),
                    ),
                  ],
                ],
              ),
            ),
            Switch(
              value: features.faceDetectionOnSaveEnabled,
              onChanged: (value) {
                ref.read(featuresNotifierProvider.notifier).toggleFaceDetectionOnSave(value);
              },
              materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
            ),
          ],
        ),
      ),
      loading: () => Container(
        padding: const EdgeInsets.all(12),
        margin: const EdgeInsets.only(bottom: 8),
        decoration: BoxDecoration(
          color: Colors.grey.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(8),
        ),
        child: const Row(
          children: [
            SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2)),
            SizedBox(width: 8),
            Text('Loading automatic face detection settings...'),
          ],
        ),
      ),
      error: (error, stack) => Container(
        padding: const EdgeInsets.all(12),
        margin: const EdgeInsets.only(bottom: 8),
        decoration: BoxDecoration(
          color: Colors.red.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Row(
          children: [
            const Icon(Icons.error_outline, color: Colors.red, size: 20),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                'Error loading face detection settings: ${error.toString()}',
                style: const TextStyle(color: Colors.red, fontSize: 12),
              ),
            ),
          ],
        ),
      ),
    );
  }

  String _formatDateTime(DateTime dateTime) {
    final now = DateTime.now();
    final diff = now.difference(dateTime);
    
    if (diff.inMinutes < 1) {
      return 'Just now';
    } else if (diff.inMinutes < 60) {
      return '${diff.inMinutes}m ago';
    } else if (diff.inHours < 24) {
      return '${diff.inHours}h ago';
    } else {
      return '${diff.inDays}d ago';
    }
  }
}