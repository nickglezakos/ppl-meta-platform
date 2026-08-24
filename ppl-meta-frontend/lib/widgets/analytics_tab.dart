import 'dart:convert';

import 'package:csv/csv.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:intl/intl.dart';
import '../core/theme/theme_kit.dart';
import '../models/communication_log_model.dart';
import '../models/trigger_model.dart';
import '../services/trigger_service.dart';
import '../presentation/widgets/common/content_pane.dart';
import '../presentation/widgets/common/item_logs_list.dart';
import '../presentation/widgets/common/ux_breakpoints.dart';
import '../utils/platform_file_download.dart';

/// Analytics tab: left filter sidebar (status / type toggles + time range)
/// and a right content pane listing communication logs for the selected
/// filters, using the same log-row UX as the triggers tab.
class AnalyticsTab extends StatefulWidget {
  const AnalyticsTab({Key? key}) : super(key: key);

  @override
  State<AnalyticsTab> createState() => _AnalyticsTabState();
}

class _AnalyticsTabState extends State<AnalyticsTab> {
  static const _statusOptions = <String?>[null, 'sent', 'pending', 'failed'];
  static const _statusLabels = ['All', 'Sent', 'Pending', 'Failed'];

  static const _typeOptions = <String?>[
    null,
    'email',
    'webhook',
    'sms',
    'push_notification',
    'audit_log',
  ];
  static const _typeLabels = [
    'All',
    'Email',
    'Webhook',
    'SMS',
    'Push',
    'Audit',
  ];

  String? _selectedStatus;
  String? _selectedType;
  DateTime? _startDate;
  DateTime? _endDate;

  List<TriggerModel> _triggers = [];
  final Set<String> _selectedTriggerIds = {};

  /// true = charts view (default), false = logs list view.
  bool _showCharts = true;
  bool _isDownloading = false;
  final GlobalKey<ItemLogsListState> _logsListKey =
      GlobalKey<ItemLogsListState>();

  @override
  void initState() {
    super.initState();
    _loadTriggers();
  }

  Future<void> _loadTriggers() async {
    try {
      final response = await TriggerService().fetchTriggers();
      if (!mounted) return;
      setState(() => _triggers = response.triggers);
    } catch (_) {
      // Non-fatal: chip selector just stays empty.
    }
  }

  void _toggleTrigger(String id) {
    setState(() {
      if (!_selectedTriggerIds.add(id)) _selectedTriggerIds.remove(id);
    });
  }

  Future<void> _pickDate({required bool isStart}) async {
    final initial = isStart
        ? (_startDate ?? DateTime.now().subtract(const Duration(days: 7)))
        : (_endDate ?? DateTime.now());
    final picked = await showDatePicker(
      context: context,
      initialDate: initial,
      firstDate: DateTime(2020),
      lastDate: DateTime.now().add(const Duration(days: 1)),
    );
    if (picked == null) return;
    setState(() {
      if (isStart) {
        _startDate = picked;
        if (_endDate != null && _endDate!.isBefore(picked)) {
          _endDate = picked;
        }
      } else {
        _endDate = picked;
        if (_startDate != null && _startDate!.isAfter(picked)) {
          _startDate = picked;
        }
      }
    });
  }

  void _applyPreset(int days) {
    setState(() {
      _startDate = DateTime.now().subtract(Duration(days: days));
      _endDate = DateTime.now();
    });
  }

  void _clearRange() {
    setState(() {
      _startDate = null;
      _endDate = null;
    });
  }

  Widget _sectionTitle(String text) {
    return Text(
      text,
      style: Theme.of(context).textTheme.titleSmall?.copyWith(
            fontWeight: FontWeight.bold,
          ),
    );
  }

  Widget _buildSidebar() {
    return Padding(
      padding: const EdgeInsets.all(AppSpacing.lg),
      child: SingleChildScrollView(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _sectionTitle('Status'),
            const SizedBox(height: 8),
            ToggleButtons(
              constraints: const BoxConstraints(minHeight: 32),
              borderRadius: BorderRadius.circular(AppRadius.sm),
              isSelected: [
                for (final s in _statusOptions) s == _selectedStatus,
              ],
              onPressed: (i) =>
                  setState(() => _selectedStatus = _statusOptions[i]),
              selectedColor: AppColors.accent,
              fillColor: AppColors.accent.withValues(alpha: 0.1),
              borderColor: AppColors.gray700,
              selectedBorderColor: AppColors.accent.withValues(alpha: 0.4),
              children: [
                for (final label in _statusLabels)
                  Padding(
                    padding:
                        const EdgeInsets.symmetric(horizontal: AppSpacing.sm),
                    child: Text(label, style: AppTextStyles.caption),
                  ),
              ],
            ),
            const SizedBox(height: 20),
            _sectionTitle('Type'),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                for (var i = 0; i < _typeLabels.length; i++)
                  FilterChip(
                    label: Text(_typeLabels[i]),
                    selected: _typeOptions[i] == _selectedType,
                    onSelected: (_) =>
                        setState(() => _selectedType = _typeOptions[i]),
                  ),
              ],
            ),
            const SizedBox(height: 20),
            _sectionTitle('Triggers'),
            const SizedBox(height: 8),
            if (_triggers.isEmpty)
              Text(
                'No triggers available',
                style: Theme.of(context).textTheme.bodySmall,
              )
            else
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  for (final t in _triggers)
                    FilterChip(
                      label: Text(t.name ?? 'Unnamed'),
                      selected: _selectedTriggerIds.contains(t.uuid),
                      onSelected: (_) => _toggleTrigger(t.uuid),
                    ),
                ],
              ),
            const SizedBox(height: 20),
            _sectionTitle('Time Range'),
            const SizedBox(height: 8),
            OutlinedButton.icon(
              onPressed: () => _pickDate(isStart: true),
              icon: const Icon(Icons.event_outlined, size: 18),
              label: Text(_startDate == null
                  ? 'Start date'
                  : '${_startDate!.year}-${_startDate!.month.toString().padLeft(2, '0')}-${_startDate!.day.toString().padLeft(2, '0')}'),
            ),
            const SizedBox(height: 8),
            OutlinedButton.icon(
              onPressed: () => _pickDate(isStart: false),
              icon: const Icon(Icons.event, size: 18),
              label: Text(_endDate == null
                  ? 'End date'
                  : '${_endDate!.year}-${_endDate!.month.toString().padLeft(2, '0')}-${_endDate!.day.toString().padLeft(2, '0')}'),
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                ActionChip(
                    label: const Text('24h'), onPressed: () => _applyPreset(1)),
                ActionChip(
                    label: const Text('7d'), onPressed: () => _applyPreset(7)),
                ActionChip(
                    label: const Text('30d'),
                    onPressed: () => _applyPreset(30)),
                ActionChip(label: const Text('Clear'), onPressed: _clearRange),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildContent() {
    final scheme = Theme.of(context).colorScheme;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        ContentBar(
          title: 'Analytics',
          subtitle: 'Communication logs across all triggers and actions',
          trailing: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              IconButton(
                tooltip: 'Download logs (Excel-compatible CSV)',
                onPressed: _isDownloading ? null : _downloadLogsCsv,
                icon: _isDownloading
                    ? const SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.download_outlined),
                color: scheme.primary,
              ),
              ContentBar.modePill(
                showSettings: !_showCharts,
                onTap: () => setState(() => _showCharts = !_showCharts),
                scheme: scheme,
                firstIcon: Icons.insert_chart_outlined,
                secondIcon: Icons.format_list_bulleted,
              ),
            ],
          ),
        ),
        const SizedBox(height: 8),
        Expanded(
          child: Padding(
            padding: const EdgeInsets.all(12),
            // IndexedStack keeps the logs list mounted (and fetching) while
            // the charts view is shown, so charts always have data.
            child: IndexedStack(
              index: _showCharts ? 0 : 1,
              children: [_buildCharts(), _buildLogsList()],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildLogsList() {
    return ItemLogsList(
      key: _logsListKey,
      itemId: null,
      triggerIds:
          _selectedTriggerIds.isEmpty ? null : _selectedTriggerIds.toList(),
      status: _selectedStatus,
      type: _selectedType,
      startDate: _startDate,
      endDate: _endDate,
      pageSize: 50,
    );
  }

  Map<String, int> get _countsByStatus {
    final counts = <String, int>{};
    for (final log in _logsListKey.currentState?.logs ?? const []) {
      counts[log.status] = (counts[log.status] ?? 0) + 1;
    }
    return counts;
  }

  Map<String, int> get _countsByType {
    final counts = <String, int>{};
    for (final log in _logsListKey.currentState?.logs ?? const []) {
      counts[log.communicationType] = (counts[log.communicationType] ?? 0) + 1;
    }
    return counts;
  }

  Map<String, int> get _countsByTrigger {
    final nameById = {
      for (final t in _triggers) t.uuid: t.name,
    };
    final counts = <String, int>{};
    for (final log in _logsListKey.currentState?.logs ?? const []) {
      final label = log.triggerId == null
          ? 'Unassigned'
          : (nameById[log.triggerId] ?? log.triggerId!);
      counts[label] = (counts[label] ?? 0) + 1;
    }
    return counts;
  }

  static const _chartPalette = [
    Color(0xFF4CAF50),
    Color(0xFF2196F3),
    Color(0xFFFF9800),
    Color(0xFF9C27B0),
    Color(0xFF009688),
    Color(0xFFF44336),
    Color(0xFF3F51B5),
    Color(0xFFFFC107),
  ];

  Widget _pieCard(String title, Map<String, int> counts) {
    final total = counts.values.fold<int>(0, (s, v) => s + v);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: Theme.of(context)
                  .textTheme
                  .titleSmall
                  ?.copyWith(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 12),
            Expanded(
              child: total == 0
                  ? Center(
                      child: Text(
                        'No data for the selected filters',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                    )
                  : Row(
                      children: [
                        Expanded(
                          child: PieChart(
                            PieChartData(
                              sectionsSpace: 2,
                              centerSpaceRadius: 40,
                              sections: [
                                for (var i = 0; i < counts.length; i++)
                                  PieChartSectionData(
                                    value: counts.values
                                        .elementAt(i)
                                        .toDouble(),
                                    title:
                                        '${((counts.values.elementAt(i) / total) * 100).toStringAsFixed(0)}%',
                                    radius: 48,
                                    color: _chartPalette[
                                        i % _chartPalette.length],
                                    titleStyle: const TextStyle(
                                      fontSize: 11,
                                      fontWeight: FontWeight.bold,
                                      color: Colors.white,
                                    ),
                                  ),
                              ],
                            ),
                          ),
                        ),
                        const SizedBox(width: 12),
                        Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            for (var i = 0; i < counts.length; i++)
                              Padding(
                                padding:
                                    const EdgeInsets.symmetric(vertical: 2),
                                child: Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    Container(
                                      width: 10,
                                      height: 10,
                                      decoration: BoxDecoration(
                                        shape: BoxShape.circle,
                                        color: _chartPalette[
                                            i % _chartPalette.length],
                                      ),
                                    ),
                                    const SizedBox(width: 6),
                                    Text(
                                      '${counts.keys.elementAt(i)} (${counts.values.elementAt(i)})',
                                      style:
                                          Theme.of(context).textTheme.bodySmall,
                                    ),
                                  ],
                                ),
                              ),
                          ],
                        ),
                      ],
                    ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildCharts() {
    final statusCounts = _countsByStatus;
    final typeCounts = _countsByType;
    final triggerCounts = _countsByTrigger;
    // The logs list loads asynchronously; schedule one deferred rebuild so
    // freshly loaded data shows up in the charts.
    WidgetsBinding.instance.addPostFrameCallback((_) async {
      await Future.delayed(const Duration(milliseconds: 600));
      if (mounted && _showCharts) setState(() {});
    });
    return SingleChildScrollView(
      child: Column(
        children: [
          SizedBox(height: 360, child: _pieCard('By Status', statusCounts)),
          const SizedBox(height: 12),
          SizedBox(height: 360, child: _pieCard('By Type', typeCounts)),
          const SizedBox(height: 12),
          SizedBox(height: 360, child: _pieCard('By Trigger', triggerCounts)),
        ],
      ),
    );
  }

  /// Downloads the currently loaded logs as an Excel-compatible CSV file,
  /// using the same platform-aware download helper as the communication
  /// logs screen.
  Future<void> _downloadLogsCsv() async {
    final logs = _logsListKey.currentState?.logs ?? const <CommunicationLog>[];
    if (logs.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('No logs loaded to download')),
      );
      return;
    }

    setState(() => _isDownloading = true);
    try {
      final rows = <List<dynamic>>[
        [
          'UUID',
          'Type',
          'Status',
          'Recipient',
          'Subject',
          'Triggered By',
          'Trigger Type',
          'Trigger ID',
          'Attempts',
          'Created At',
          'Updated At',
        ],
      ];
      for (final log in logs) {
        rows.add([
          log.uuid,
          log.communicationType,
          log.status,
          log.recipient,
          log.subjectLine ?? '',
          log.triggeredBy ?? '',
          log.triggerType ?? '',
          log.triggerId ?? '',
          log.attempts.toString(),
          log.createdAt,
          log.updatedAt,
        ]);
      }

      final csvData = const ListToCsvConverter().convert(rows);
      final timestamp = DateFormat('yyyyMMdd_HHmmss').format(DateTime.now());
      final filename = 'log_analytics_$timestamp.csv';

      final savedPath = await downloadFileBytes(
        bytes: utf8.encode(csvData),
        filename: filename,
        mimeType: 'text/csv',
      );

      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content:
              Text('Downloaded ${logs.length} logs to ${savedPath ?? filename}'),
          backgroundColor: Colors.green,
        ),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Failed to download logs: $e'),
          backgroundColor: Colors.red,
        ),
      );
    } finally {
      if (mounted) setState(() => _isDownloading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final wide = constraints.maxWidth > 900;
        if (!wide) {
          return Column(
            children: [
              _buildSidebar(),
              const Divider(height: 1),
              Expanded(child: _buildContent()),
            ],
          );
        }
        return Row(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            SizedBox(width: kMasterPaneWidth, child: _buildSidebar()),
            const VerticalDivider(width: 1),
            const SizedBox(width: 4),
            Expanded(child: _buildContent()),
          ],
        );
      },
    );
  }
}