import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/providers/camera_providers.dart';
import '../../../core/theme/theme_kit.dart';
import '../../../utils/offline_fonts.dart';

/// Camera content-pane view of Instant Detection flush logs
/// (Media `instant_detection_logs` — separate from Automation action logs).
class InstantDetectionLogsPane extends ConsumerStatefulWidget {
  const InstantDetectionLogsPane({
    super.key,
    required this.cameraDeviceId,
  });

  final String cameraDeviceId;

  @override
  ConsumerState<InstantDetectionLogsPane> createState() =>
      _InstantDetectionLogsPaneState();
}

class _InstantDetectionLogsPaneState
    extends ConsumerState<InstantDetectionLogsPane> {
  bool _loading = true;
  String? _error;
  List<Map<String, dynamic>> _logs = const [];
  int? _expandedId;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _load());
  }

  @override
  void didUpdateWidget(covariant InstantDetectionLogsPane oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.cameraDeviceId != widget.cameraDeviceId) {
      _load();
    }
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
      _expandedId = null;
    });
    try {
      final client = ref.read(mediaApiClientProvider);
      final rows = await client.listInstantDetectionLogs(
        cameraDeviceId: widget.cameraDeviceId,
        limit: 50,
      );
      if (!mounted) return;
      setState(() {
        _logs = rows;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  String _fmt(dynamic value) {
    if (value == null) return '—';
    final s = value.toString();
    if (s.length >= 19 && s.contains('T')) {
      return s.substring(0, 19).replaceFirst('T', ' ');
    }
    return s;
  }

  /// Prefer Vision person_groups; fall back to hierarchical merge / InstantMvrs.
  int _personGroupCount(Map<String, dynamic>? payload) {
    if (payload == null) return 0;
    final groups = payload['person_groups'];
    if (groups is List && groups.isNotEmpty) return groups.length;

    final merge = payload['hierarchical_merge'];
    if (merge is Map) {
      final supers = merge['super_individuals'];
      if (supers is List && supers.isNotEmpty) return supers.length;
      final stats = merge['statistics'];
      if (stats is Map) {
        final n = stats['super_individuals'];
        if (n is int) return n;
        if (n is num) return n.toInt();
      }
    }

    final mvrs = payload['instant_mvrs'];
    if (mvrs is List && mvrs.isNotEmpty) {
      // Distinct InstantMvr ids when merge payload is incomplete.
      final ids = <String>{};
      for (final m in mvrs) {
        if (m is! Map) continue;
        final id = m['instant_mvr_uuid'] ?? m['mvr_people_uuid'];
        if (id != null) ids.add(id.toString());
      }
      return ids.isNotEmpty ? ids.length : mvrs.length;
    }
    return groups is List ? groups.length : 0;
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_error != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                'Could not load Instant Detection logs',
                style: OfflineFonts.inter(
                  fontSize: 15,
                  fontWeight: FontWeight.w600,
                  color: AppColors.textPrimary,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                _error!,
                textAlign: TextAlign.center,
                style: OfflineFonts.inter(
                  fontSize: 12,
                  color: AppColors.textSecondary,
                ),
              ),
              const SizedBox(height: 16),
              TextButton.icon(
                onPressed: _load,
                icon: const Icon(Icons.refresh),
                label: const Text('Retry'),
              ),
            ],
          ),
        ),
      );
    }
    if (_logs.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                Icons.receipt_long_outlined,
                size: 48,
                color: AppColors.textSecondary.withOpacity(0.5),
              ),
              const SizedBox(height: 12),
              Text(
                'No Instant Detection flush logs yet',
                style: OfflineFonts.inter(
                  fontSize: 15,
                  fontWeight: FontWeight.w600,
                  color: AppColors.textPrimary,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                'Logs appear after Y-cycle flush (re-group + merge). '
                'They are separate from Automation action logs.',
                textAlign: TextAlign.center,
                style: OfflineFonts.inter(
                  fontSize: 13,
                  color: AppColors.textSecondary,
                ),
              ),
              const SizedBox(height: 16),
              TextButton.icon(
                onPressed: _load,
                icon: const Icon(Icons.refresh),
                label: const Text('Refresh'),
              ),
            ],
          ),
        ),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 4),
          child: Row(
            children: [
              Expanded(
                child: Text(
                  'Instant Detection logs',
                  style: OfflineFonts.inter(
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                    color: AppColors.textPrimary,
                  ),
                ),
              ),
              IconButton(
                tooltip: 'Refresh',
                onPressed: _load,
                icon: const Icon(Icons.refresh, size: 20),
              ),
            ],
          ),
        ),
        Expanded(
          child: ListView.separated(
            padding: const EdgeInsets.fromLTRB(12, 0, 12, 16),
            itemCount: _logs.length,
            separatorBuilder: (_, __) => const SizedBox(height: 8),
            itemBuilder: (context, index) {
              final log = _logs[index];
              final id = log['id'] as int?;
              final expanded = id != null && id == _expandedId;
              final people = log['people_count'] ?? 0;
              final cycles = log['cycle_count'] ?? 0;
              final threshold = log['merge_threshold'];
              final payload = log['payload_json'];
              Map<String, dynamic>? payloadMap;
              if (payload is Map<String, dynamic>) {
                payloadMap = payload;
              }

              return Material(
                color: AppColors.surface,
                borderRadius: BorderRadius.circular(AppRadius.md),
                child: InkWell(
                  borderRadius: BorderRadius.circular(AppRadius.md),
                  onTap: () {
                    if (id == null) return;
                    setState(() {
                      _expandedId = expanded ? null : id;
                    });
                  },
                  child: Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(AppRadius.md),
                      border: Border.all(
                        color: AppColors.border.withOpacity(0.6),
                      ),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Icon(
                              expanded
                                  ? Icons.expand_less
                                  : Icons.expand_more,
                              size: 20,
                              color: AppColors.textSecondary,
                            ),
                            const SizedBox(width: 6),
                            Expanded(
                              child: Text(
                                _fmt(log['flush_started_at']),
                                style: OfflineFonts.inter(
                                  fontSize: 13,
                                  fontWeight: FontWeight.w600,
                                  color: AppColors.textPrimary,
                                ),
                              ),
                            ),
                            Text(
                              '$people people · $cycles cycles',
                              style: OfflineFonts.inter(
                                fontSize: 12,
                                color: AppColors.textSecondary,
                              ),
                            ),
                          ],
                        ),
                        if (expanded) ...[
                          const SizedBox(height: 10),
                          Text(
                            'Ended ${_fmt(log['flush_ended_at'])}'
                            '${threshold != null ? ' · merge ≥ $threshold' : ''}'
                            ' · frames/cycle ${log['frames_per_cycle'] ?? '—'}',
                            style: OfflineFonts.inter(
                              fontSize: 12,
                              color: AppColors.textSecondary,
                            ),
                          ),
                          if (payloadMap != null) ...[
                            const SizedBox(height: 8),
                            Text(
                              'People groups: ${_personGroupCount(payloadMap)}'
                              ' · InstantMvrs: '
                              '${(payloadMap['instant_mvrs'] is List ? (payloadMap['instant_mvrs'] as List).length : '—')}'
                              ' · people_count: ${log['people_count'] ?? '—'}',
                              style: OfflineFonts.inter(
                                fontSize: 12,
                                color: AppColors.textPrimary,
                              ),
                            ),
                          ],
                        ],
                      ],
                    ),
                  ),
                ),
              );
            },
          ),
        ),
      ],
    );
  }
}
