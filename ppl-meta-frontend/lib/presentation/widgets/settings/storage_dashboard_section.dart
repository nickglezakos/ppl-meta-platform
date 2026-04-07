import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../models/storage_location.dart';
import '../../../services/storage_service.dart';
import '../../../core/theme/app_theme.dart';
import 'storage_location_form.dart';

/// Storage dashboard showing overall usage, per-location cards, and alerts.
class StorageDashboardSection extends ConsumerStatefulWidget {
  const StorageDashboardSection({super.key});

  @override
  ConsumerState<StorageDashboardSection> createState() =>
      _StorageDashboardSectionState();
}

class _StorageDashboardSectionState
    extends ConsumerState<StorageDashboardSection> {
  StorageDashboard? _dashboard;
  List<StorageLocation> _locations = [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final service = ref.read(storageServiceProvider);
      final results = await Future.wait([
        service.getStorageDashboard(),
        service.getStorageLocations(),
      ]);

      if (mounted) {
        setState(() {
          _dashboard = results[0] as StorageDashboard;
          _locations = results[1] as List<StorageLocation>;
          _loading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = e.toString();
          _loading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_error != null) {
      return _buildErrorWidget();
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Default active storage card
        if (_dashboard != null) _buildDefaultStorageCard(),

        // Alerts banner
        if (_dashboard != null && _dashboard!.alerts.isNotEmpty)
          _buildAlertsBanner(),

        // Overall summary
        if (_dashboard != null) _buildOverallSummary(),

        const SizedBox(height: 24),

        // Locations header + add button
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text('Storage Locations',
                style: Theme.of(context).textTheme.titleMedium),
            IconButton(
              icon: const Icon(Icons.add_circle_outline),
              tooltip: 'Add Location',
              onPressed: _addLocation,
            ),
          ],
        ),
        const SizedBox(height: 12),

        // Per-location cards
        if (_locations.isEmpty)
          _buildEmptyState()
        else
          ..._locations.map(_buildLocationCard),
      ],
    );
  }

  Widget _buildDefaultStorageCard() {
    final d = _dashboard!;
    final def = d.defaultActiveLocation;

    return Card(
      margin: const EdgeInsets.only(bottom: 16),
      color: AppColors.primary.withOpacity(0.05),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(8),
        side: BorderSide(color: AppColors.primary.withOpacity(0.3)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            Icon(Icons.folder_special, color: AppColors.primary, size: 32),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Default Active Storage',
                      style: TextStyle(
                        fontSize: 12,
                        color: AppColors.primary,
                        fontWeight: FontWeight.w600,
                      )),
                  const SizedBox(height: 4),
                  if (def != null) ...[
                    Text(def['name'] as String? ?? 'Unknown',
                        style: const TextStyle(
                            fontSize: 16, fontWeight: FontWeight.bold)),
                    const SizedBox(height: 2),
                    Text(
                      def['base_path'] as String? ?? '',
                      style: TextStyle(
                          fontSize: 12, color: Colors.grey.shade600),
                    ),
                  ] else
                    const Text('No default location configured',
                        style: TextStyle(
                            fontSize: 14, fontStyle: FontStyle.italic)),
                ],
              ),
            ),
            if (def != null) ...[
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text(
                    '${((def['used_gb'] as num?) ?? 0).toStringAsFixed(1)} GB used',
                    style: const TextStyle(fontWeight: FontWeight.w600),
                  ),
                  if (def['total_capacity_gb'] != null)
                    Text(
                      'of ${((def['total_capacity_gb'] as num?)!).toStringAsFixed(1)} GB',
                      style: TextStyle(
                          fontSize: 12, color: Colors.grey.shade600),
                    ),
                ],
              ),
            ] else
              ElevatedButton.icon(
                onPressed: _addLocation,
                icon: const Icon(Icons.add, size: 16),
                label: const Text('Add'),
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(
                      horizontal: 12, vertical: 8),
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildAlertsBanner() {
    final alerts = _dashboard!.alerts;
    final hasCritical =
        alerts.any((a) => a['level'] == 'critical');

    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(bottom: 16),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: hasCritical
            ? AppColors.error.withOpacity(0.1)
            : Colors.orange.withOpacity(0.1),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: hasCritical ? AppColors.error : Colors.orange,
          width: 1,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: alerts.map<Widget>((alert) {
          final isCritical = alert['level'] == 'critical';
          return Padding(
            padding: const EdgeInsets.symmetric(vertical: 2),
            child: Row(
              children: [
                Icon(
                  isCritical ? Icons.error : Icons.warning_amber,
                  size: 18,
                  color: isCritical ? AppColors.error : Colors.orange,
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    alert['message'] ?? '',
                    style: TextStyle(
                      color: isCritical ? AppColors.error : Colors.orange[800],
                      fontSize: 13,
                    ),
                  ),
                ),
              ],
            ),
          );
        }).toList(),
      ),
    );
  }

  Widget _buildOverallSummary() {
    final d = _dashboard!;
    final hasCapacity = d.totalCapacityGb != null && d.totalCapacityGb! > 0;

    // Use real media stats when location-tracked stats are zero
    final effectiveUsedGb =
        d.totalUsedGb > 0 ? d.totalUsedGb : d.mediaRealUsedGb;
    final effectiveFiles =
        d.activeFiles > 0 ? d.activeFiles : d.mediaRealFiles;
    final effectivePct = hasCapacity
        ? (effectiveUsedGb / d.totalCapacityGb! * 100)
        : 0.0;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Total Storage',
                style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 12),

            // Usage bar
            if (hasCapacity) ...[
              ClipRRect(
                borderRadius: BorderRadius.circular(4),
                child: LinearProgressIndicator(
                  value: (effectivePct / 100).clamp(0.0, 1.0),
                  minHeight: 12,
                  backgroundColor: Colors.grey.shade200,
                  valueColor: AlwaysStoppedAnimation<Color>(
                    effectivePct >= 95
                        ? AppColors.error
                        : effectivePct >= 80
                            ? Colors.orange
                            : AppColors.success,
                  ),
                ),
              ),
              const SizedBox(height: 8),
              Text(
                '${effectiveUsedGb.toStringAsFixed(1)} GB / ${d.totalCapacityGb!.toStringAsFixed(1)} GB  (${effectivePct.toStringAsFixed(0)}%)',
                style: Theme.of(context).textTheme.bodyMedium,
              ),
            ] else
              Text(
                '${effectiveUsedGb.toStringAsFixed(1)} GB used  •  ${effectiveFiles} files',
                style: Theme.of(context).textTheme.bodyMedium,
              ),

            const Divider(height: 24),

            // Active / Archive split
            Row(
              children: [
                _buildStatChip(
                  'Active',
                  '${effectiveUsedGb.toStringAsFixed(1)} GB',
                  '$effectiveFiles files',
                  AppColors.primary,
                ),
                const SizedBox(width: 16),
                _buildStatChip(
                  'Archive',
                  '${(d.archiveUsedBytes / (1024 * 1024 * 1024)).toStringAsFixed(1)} GB',
                  '${d.archiveFiles} files',
                  Colors.orange,
                ),
                if (d.freeGb != null) ...[
                  const SizedBox(width: 16),
                  _buildStatChip(
                    'Free',
                    '${d.freeGb!.toStringAsFixed(1)} GB',
                    '',
                    Colors.grey,
                  ),
                ],
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildStatChip(
      String label, String value, String subtitle, Color color) {
    return Expanded(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label,
              style: TextStyle(fontSize: 12, color: color, fontWeight: FontWeight.w600)),
          Text(value,
              style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
          if (subtitle.isNotEmpty)
            Text(subtitle,
                style: TextStyle(fontSize: 11, color: Colors.grey.shade600)),
        ],
      ),
    );
  }

  Widget _buildLocationCard(StorageLocation loc) {
    final hasCapacity = loc.totalCapacityGb != null;
    final pct = loc.usagePercentage;

    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: ListTile(
        leading: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(loc.typeIcon, style: const TextStyle(fontSize: 24)),
            Icon(
              Icons.circle,
              size: 10,
              color: loc.isActive ? AppColors.success : AppColors.error,
            ),
          ],
        ),
        title: Row(
          children: [
            Expanded(child: Text(loc.name)),
            if (loc.isDefault)
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: AppColors.primary.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text('Default',
                    style: TextStyle(
                        fontSize: 10,
                        color: AppColors.primary,
                        fontWeight: FontWeight.w600)),
              ),
            const SizedBox(width: 4),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
              decoration: BoxDecoration(
                color: loc.tier == 'active'
                    ? Colors.blue.withOpacity(0.1)
                    : Colors.orange.withOpacity(0.1),
                borderRadius: BorderRadius.circular(4),
              ),
              child: Text(
                loc.tier == 'active' ? 'Active' : 'Archive',
                style: TextStyle(
                  fontSize: 10,
                  color: loc.tier == 'active' ? Colors.blue : Colors.orange,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          ],
        ),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const SizedBox(height: 6),
            if (hasCapacity) ...[
              ClipRRect(
                borderRadius: BorderRadius.circular(3),
                child: LinearProgressIndicator(
                  value: (pct / 100).clamp(0.0, 1.0),
                  minHeight: 6,
                  backgroundColor: Colors.grey.shade200,
                  valueColor: AlwaysStoppedAnimation<Color>(
                    pct >= 95
                        ? AppColors.error
                        : pct >= 80
                            ? Colors.orange
                            : AppColors.success,
                  ),
                ),
              ),
              const SizedBox(height: 4),
              Text(
                '${loc.usedGb.toStringAsFixed(1)} / ${loc.totalCapacityGb!.toStringAsFixed(1)} GB · ${loc.fileCount} files',
                style: const TextStyle(fontSize: 12),
              ),
            ] else
              Text(
                '${loc.usedGb.toStringAsFixed(1)} GB · ${loc.fileCount} files · Unlimited',
                style: const TextStyle(fontSize: 12),
              ),
          ],
        ),
        trailing: PopupMenuButton<String>(
          onSelected: (action) => _handleLocationAction(action, loc),
          itemBuilder: (_) => [
            const PopupMenuItem(value: 'edit', child: Text('Edit')),
            const PopupMenuItem(value: 'verify', child: Text('Verify')),
            if (!loc.isDefault)
              const PopupMenuItem(
                  value: 'set_default', child: Text('Set as Default')),
            const PopupMenuDivider(),
            const PopupMenuItem(
              value: 'delete',
              child: Text('Delete', style: TextStyle(color: Colors.red)),
            ),
          ],
        ),
        isThreeLine: true,
      ),
    );
  }

  Widget _buildEmptyState() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Center(
          child: Column(
            children: [
              Icon(Icons.storage_outlined,
                  size: 48, color: Colors.grey.shade400),
              const SizedBox(height: 12),
              const Text('No storage locations configured'),
              const SizedBox(height: 8),
              ElevatedButton.icon(
                onPressed: _addLocation,
                icon: const Icon(Icons.add),
                label: const Text('Add Location'),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildErrorWidget() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          children: [
            Icon(Icons.error_outline, size: 36, color: AppColors.error),
            const SizedBox(height: 8),
            Text('Failed to load storage data',
                style: TextStyle(color: AppColors.error)),
            const SizedBox(height: 4),
            Text(_error ?? '', style: const TextStyle(fontSize: 12)),
            const SizedBox(height: 12),
            ElevatedButton(
              onPressed: _loadData,
              child: const Text('Retry'),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _addLocation() async {
    final created = await showDialog<bool>(
      context: context,
      builder: (_) => const StorageLocationFormDialog(),
    );
    if (created == true) _loadData();
  }

  Future<void> _handleLocationAction(
      String action, StorageLocation loc) async {
    final service = ref.read(storageServiceProvider);

    switch (action) {
      case 'edit':
        final updated = await showDialog<bool>(
          context: context,
          builder: (_) => StorageLocationFormDialog(existing: loc),
        );
        if (updated == true) _loadData();
        break;

      case 'verify':
        try {
          final result = await service.verifyStorageLocation(loc.uuid);
          if (mounted) {
            final ok = result['is_accessible'] == true;
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                content: Text(ok
                    ? '✅ ${loc.name} is accessible'
                    : '❌ ${loc.name}: ${result['error']}'),
                backgroundColor: ok ? AppColors.success : AppColors.error,
              ),
            );
            _loadData();
          }
        } catch (e) {
          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                  content: Text('Verification failed: $e'),
                  backgroundColor: AppColors.error),
            );
          }
        }
        break;

      case 'set_default':
        try {
          await service.setDefaultLocation(loc.uuid);
          _loadData();
        } catch (e) {
          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                  content: Text('Failed: $e'),
                  backgroundColor: AppColors.error),
            );
          }
        }
        break;

      case 'delete':
        final confirmed = await showDialog<bool>(
          context: context,
          builder: (_) => AlertDialog(
            title: const Text('Delete Storage Location'),
            content: Text(
                'Delete "${loc.name}"? This cannot be undone. '
                'The location must have no files referencing it.'),
            actions: [
              TextButton(
                  onPressed: () => Navigator.pop(context, false),
                  child: const Text('Cancel')),
              TextButton(
                onPressed: () => Navigator.pop(context, true),
                style: TextButton.styleFrom(foregroundColor: Colors.red),
                child: const Text('Delete'),
              ),
            ],
          ),
        );
        if (confirmed == true) {
          try {
            await service.deleteStorageLocation(loc.uuid);
            _loadData();
          } catch (e) {
            if (mounted) {
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(
                    content: Text('Delete failed: $e'),
                    backgroundColor: AppColors.error),
              );
            }
          }
        }
        break;
    }
  }
}
