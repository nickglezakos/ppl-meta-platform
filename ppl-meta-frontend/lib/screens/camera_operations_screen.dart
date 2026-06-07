import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/camera_operations_models.dart';
import '../core/theme/app_theme.dart';
import '../services/camera_operations_client.dart';
import '../widgets/custom_app_bar.dart';

class CameraOperationsScreen extends ConsumerStatefulWidget {
  const CameraOperationsScreen({super.key});

  @override
  ConsumerState<CameraOperationsScreen> createState() => _CameraOperationsScreenState();
}

class _CameraOperationsScreenState extends ConsumerState<CameraOperationsScreen> {
  static const String _allFilterValue = 'ALL';

  bool _isLoading = true;
  bool _isReconciling = false;
  String? _error;
  String _selectedCameraType = _allFilterValue;
  String _selectedState = _allFilterValue;

  CameraOperationsStatusResponse? _statusPayload;
  ReconcileHealthResponse? _healthPayload;
  CameraOperationsAggregatesResponse? _aggregatesPayload;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    final client = ref.read(cameraOperationsClientProvider);
    final now = DateTime.now().toUtc();
    final from = now.subtract(const Duration(hours: 1));

    try {
      final results = await Future.wait([
        client.getStatus(
          limit: 300,
          cameraType: _selectedCameraType == _allFilterValue ? null : _selectedCameraType,
          state: _selectedState == _allFilterValue ? null : _selectedState,
        ),
        client.getReconcileHealth(),
        client.getAnalyticsAggregates(
          from: from,
          to: now,
          groupBy: 'camera_type',
          cameraType: _selectedCameraType == _allFilterValue ? null : _selectedCameraType,
        ),
      ]);

      if (!mounted) {
        return;
      }

      setState(() {
        _statusPayload = results[0] as CameraOperationsStatusResponse;
        _healthPayload = results[1] as ReconcileHealthResponse;
        _aggregatesPayload = results[2] as CameraOperationsAggregatesResponse;
        _isLoading = false;
      });
    } catch (e) {
      if (!mounted) {
        return;
      }
      setState(() {
        _error = e.toString();
        _isLoading = false;
      });
    }
  }

  Future<void> _triggerReconcile() async {
    if (_isReconciling) {
      return;
    }

    setState(() {
      _isReconciling = true;
    });

    final client = ref.read(cameraOperationsClientProvider);
    try {
      final result = await client.triggerReconcile();
      if (!mounted) {
        return;
      }

      final mode = result.meta.mode ?? 'unknown';
      final scope = result.result.scope;
      final taskId = result.result.taskId;
      final message = taskId != null && taskId.isNotEmpty
          ? 'Reconcile queued ($scope): $taskId'
          : 'Reconcile executed ($scope, $mode)';

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(message)),
      );
      await _load();
    } catch (e) {
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Reconcile failed: $e')),
      );
    } finally {
      if (mounted) {
        setState(() {
          _isReconciling = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      appBar: CustomAppBar(
        title: 'Camera Operations',
        showBackButton: true,
        showHomeButton: true,
        actions: [
          IconButton(
            onPressed: _isLoading ? null : _load,
            icon: const Icon(Icons.refresh),
            tooltip: 'Refresh',
          ),
          IconButton(
            onPressed: _isReconciling ? null : _triggerReconcile,
            icon: _isReconciling
                ? const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.sync),
            tooltip: 'Trigger Reconcile',
          ),
        ],
      ),
      backgroundColor: AppColors.background,
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(
                  child: Padding(
                    padding: const EdgeInsets.all(24),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(Icons.error_outline, color: theme.colorScheme.error, size: 42),
                        const SizedBox(height: 12),
                        Text(
                          'Failed to load camera operations data',
                          style: theme.textTheme.titleMedium,
                          textAlign: TextAlign.center,
                        ),
                        const SizedBox(height: 8),
                        Text(
                          _error!,
                          style: theme.textTheme.bodySmall,
                          textAlign: TextAlign.center,
                        ),
                        const SizedBox(height: 16),
                        ElevatedButton.icon(
                          onPressed: _load,
                          icon: const Icon(Icons.refresh),
                          label: const Text('Retry'),
                        ),
                      ],
                    ),
                  ),
                )
              : RefreshIndicator(
                  onRefresh: _load,
                  child: ListView(
                    padding: const EdgeInsets.all(16),
                    children: [
                      _buildFiltersCard(theme),
                      const SizedBox(height: 12),
                      _buildHealthCard(theme),
                      const SizedBox(height: 12),
                      _buildSummaryCard(theme),
                      const SizedBox(height: 12),
                      _buildStateTable(theme),
                      const SizedBox(height: 12),
                      _buildAggregatesCard(theme),
                    ],
                  ),
                ),
    );
  }

  Widget _buildFiltersCard(ThemeData theme) {
    final cameraTypes = <String>{_allFilterValue};
    final states = <String>{_allFilterValue};

    final summary = _statusPayload?.summary;
    if (summary != null) {
      cameraTypes.addAll(summary.byCameraType.keys);
      states.addAll(summary.byState.keys);
    }

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.filter_alt_outlined),
                const SizedBox(width: 8),
                Text('Filters', style: theme.textTheme.titleMedium),
              ],
            ),
            const SizedBox(height: 10),
            Row(
              children: [
                Expanded(
                  child: DropdownButtonFormField<String>(
                    value: cameraTypes.contains(_selectedCameraType) ? _selectedCameraType : _allFilterValue,
                    decoration: const InputDecoration(
                      labelText: 'Camera Type',
                      border: OutlineInputBorder(),
                      isDense: true,
                    ),
                    items: cameraTypes
                        .map((value) => DropdownMenuItem(value: value, child: Text(value)))
                        .toList(),
                    onChanged: (value) {
                      if (value == null) {
                        return;
                      }
                      setState(() {
                        _selectedCameraType = value;
                      });
                      _load();
                    },
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: DropdownButtonFormField<String>(
                    value: states.contains(_selectedState) ? _selectedState : _allFilterValue,
                    decoration: const InputDecoration(
                      labelText: 'State',
                      border: OutlineInputBorder(),
                      isDense: true,
                    ),
                    items: states
                        .map((value) => DropdownMenuItem(value: value, child: Text(value)))
                        .toList(),
                    onChanged: (value) {
                      if (value == null) {
                        return;
                      }
                      setState(() {
                        _selectedState = value;
                      });
                      _load();
                    },
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildHealthCard(ThemeData theme) {
    final reconcile = _healthPayload?.reconcile;
    final status = reconcile?.status ?? 'unknown';
    final ageSeconds = reconcile?.ageSeconds;
    final interval = reconcile?.intervalSeconds.toString() ?? '-';
    final enabled = (reconcile?.enabled ?? false).toString();
    final beatEnabled = (reconcile?.beatEnabled ?? false).toString();

    Color statusColor;
    switch (status) {
      case 'healthy':
        statusColor = Colors.green;
        break;
      case 'stale':
        statusColor = Colors.orange;
        break;
      case 'disabled':
        statusColor = Colors.grey;
        break;
      default:
        statusColor = Colors.blueGrey;
    }

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.health_and_safety_outlined),
                const SizedBox(width: 8),
                Text('Reconciliation Health', style: theme.textTheme.titleMedium),
                const Spacer(),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: statusColor.withValues(alpha: 0.14),
                    borderRadius: BorderRadius.circular(16),
                  ),
                  child: Text(
                    status.toUpperCase(),
                    style: theme.textTheme.labelMedium?.copyWith(color: statusColor),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            Text('Enabled: $enabled  •  Beat: $beatEnabled  •  Interval: ${interval}s'),
            const SizedBox(height: 4),
            Text('Age: ${ageSeconds ?? '-'}s  •  Last: ${reconcile?.lastReconcileAt ?? '-'}'),
          ],
        ),
      ),
    );
  }

  Widget _buildSummaryCard(ThemeData theme) {
    final summary = _statusPayload?.summary;
    final byState = summary?.byState ?? const <String, int>{};
    final byType = summary?.byCameraType ?? const <String, int>{};
    final total = _statusPayload?.meta.total?.toString() ?? '0';

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.dashboard_outlined),
                const SizedBox(width: 8),
                Text('Live Summary', style: theme.textTheme.titleMedium),
              ],
            ),
            const SizedBox(height: 10),
            Text('Total Cameras in Payload: $total'),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: byState.entries
                  .map((entry) => _chip('${entry.key}: ${entry.value}'))
                  .toList(),
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: byType.entries
                  .map((entry) => _chip('${entry.key}: ${entry.value}'))
                  .toList(),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildStateTable(ThemeData theme) {
    final items = _statusPayload?.items ?? const <CameraOperationItem>[];

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.videocam_outlined),
                const SizedBox(width: 8),
                Text('Camera States', style: theme.textTheme.titleMedium),
              ],
            ),
            const SizedBox(height: 10),
            if (items.isEmpty)
              const Text('No camera operations state available.')
            else
              SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: DataTable(
                  columns: const [
                    DataColumn(label: Text('Camera')),
                    DataColumn(label: Text('Type')),
                    DataColumn(label: Text('State')),
                    DataColumn(label: Text('Viewers')),
                    DataColumn(label: Text('Gap ms')),
                  ],
                  rows: items
                      .take(50)
                      .map(
                        (row) => DataRow(
                          cells: [
                            DataCell(Text(row.cameraName.isNotEmpty ? row.cameraName : row.cameraId)),
                            DataCell(Text(row.cameraType)),
                            DataCell(Text(row.streamState)),
                            DataCell(Text(row.activeViewers.toString())),
                            DataCell(Text(row.frameGapMs?.toString() ?? '-')),
                          ],
                        ),
                      )
                      .toList(),
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildAggregatesCard(ThemeData theme) {
    final rows = _aggregatesPayload?.rows ?? const <CameraOperationsAggregateRow>[];

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.analytics_outlined),
                const SizedBox(width: 8),
                Text('Last Hour Aggregates', style: theme.textTheme.titleMedium),
              ],
            ),
            const SizedBox(height: 10),
            if (rows.isEmpty)
              const Text('No aggregate data available yet.')
            else
              ...rows.map(
                (row) => ListTile(
                  dense: true,
                  contentPadding: EdgeInsets.zero,
                  title: Text(row.group),
                  subtitle: Text(
                    'p95 gap: ${row.frameGapP95Ms} ms • avg viewers: ${row.activeViewersAvg} • avg fps: ${row.effectiveFpsAvg}',
                  ),
                  trailing: Text('stale: ${row.staleEvents}'),
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _chip(String text) {
    return Chip(label: Text(text));
  }
}
