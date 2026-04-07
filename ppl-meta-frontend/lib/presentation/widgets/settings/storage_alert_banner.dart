import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../services/storage_service.dart';
import '../../../core/theme/app_theme.dart';

/// Provider that periodically fetches storage alerts.
final storageAlertsProvider = FutureProvider<List<dynamic>>((ref) async {
  final service = ref.watch(storageServiceProvider);
  try {
    return await service.getStorageAlerts();
  } catch (_) {
    return [];
  }
});

/// A banner that shows storage warning/critical alerts at the top of screens.
class StorageAlertBanner extends ConsumerWidget {
  const StorageAlertBanner({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final alertsAsync = ref.watch(storageAlertsProvider);

    return alertsAsync.when(
      data: (alerts) {
        if (alerts.isEmpty) return const SizedBox.shrink();

        final critical =
            alerts.where((a) => a['level'] == 'critical').toList();
        final warnings =
            alerts.where((a) => a['level'] == 'warning').toList();

        // Show the most severe alert
        final topAlert =
            critical.isNotEmpty ? critical.first : warnings.first;
        final isCritical = topAlert['level'] == 'critical';

        return Container(
          width: double.infinity,
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
          color: isCritical
              ? AppColors.error.withOpacity(0.15)
              : Colors.orange.withOpacity(0.15),
          child: Row(
            children: [
              Icon(
                isCritical ? Icons.error : Icons.warning_amber_rounded,
                size: 20,
                color: isCritical ? AppColors.error : Colors.orange[800],
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  topAlert['message'] ?? 'Storage capacity alert',
                  style: TextStyle(
                    fontSize: 13,
                    color: isCritical ? AppColors.error : Colors.orange[900],
                  ),
                ),
              ),
              if (alerts.length > 1)
                Padding(
                  padding: const EdgeInsets.only(left: 8),
                  child: Text(
                    '+${alerts.length - 1} more',
                    style: TextStyle(
                      fontSize: 11,
                      color: Colors.grey.shade600,
                    ),
                  ),
                ),
              const SizedBox(width: 8),
              TextButton(
                onPressed: () {
                  // Navigate to storage settings
                  Navigator.pushNamed(context, '/settings');
                },
                child: const Text('Manage', style: TextStyle(fontSize: 12)),
              ),
            ],
          ),
        );
      },
      loading: () => const SizedBox.shrink(),
      error: (_, __) => const SizedBox.shrink(),
    );
  }
}
