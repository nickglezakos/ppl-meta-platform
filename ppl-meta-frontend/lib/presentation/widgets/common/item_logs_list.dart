import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:intl/intl.dart';
import '../../../models/communication_log_model.dart';
import '../../../services/communications_api_client.dart';
import '../../../services/auth_service.dart';

/// Log entry list for a trigger/action or an arbitrary filtered view,
/// rendered with the same card UX as the Sessions tab on the presence screen:
/// status-tinted cards with a leading type icon, headline, metadata line and
/// chips.
class ItemLogsList extends StatefulWidget {
  const ItemLogsList({
    super.key,
    this.itemId,
    this.triggerIds,
    this.type,
    this.status,
    this.startDate,
    this.endDate,
    this.pageSize = 20,
  });

  /// UUID of the trigger/action whose logs should be listed. Passed to the
  /// audit logs endpoint as `trigger_id`. When null, logs are not filtered by
  /// item (used by the analytics view).
  final String? itemId;

  /// Multiple trigger/action UUIDs to include. When non-empty, one request
  /// per UUID is issued and the results are merged (the endpoint only
  /// supports a single `trigger_id` filter).
  final List<String>? triggerIds;

  /// Optional communication-type filter (email, webhook, sms, ...).
  final String? type;

  /// Optional status filter (sent, pending, failed, ...).
  final String? status;

  /// Optional time range bounds.
  final DateTime? startDate;
  final DateTime? endDate;

  final int pageSize;

  @override
  ItemLogsListState createState() => ItemLogsListState();
}

class ItemLogsListState extends State<ItemLogsList> {
  final CommunicationsApiClient _logsClient = CommunicationsApiClient();
  final AuthService _authService = AuthService();

  /// Logs currently loaded (current page / merged selection). Exposed so
  /// parents (e.g. analytics charts/download) can read the same data.
  List<CommunicationLog> get logs => _logs;

  bool _isLoading = true;
  String? _errorMessage;
  List<CommunicationLog> _logs = [];
  int _page = 1;
  int _totalPages = 1;

  @override
  void initState() {
    super.initState();
    _loadLogs();
  }

  @override
  void didUpdateWidget(covariant ItemLogsList oldWidget) {
    super.didUpdateWidget(oldWidget);
    final oldIds = oldWidget.triggerIds ?? const <String>[];
    final newIds = widget.triggerIds ?? const <String>[];
    final idsChanged = oldIds.length != newIds.length ||
        !{for (final id in newIds) id}.containsAll(oldIds);
    if (oldWidget.itemId != widget.itemId ||
        idsChanged ||
        oldWidget.type != widget.type ||
        oldWidget.status != widget.status ||
        oldWidget.startDate != widget.startDate ||
        oldWidget.endDate != widget.endDate) {
      _page = 1;
      _loadLogs();
    }
  }

  Future<void> _loadLogs() async {
    if (!mounted) return;
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final token = await _authService.getStoredToken();
      if (token != null) _logsClient.setAuthToken(token);

      List<CommunicationLog> logs;
      int totalPages;

      final ids = widget.triggerIds;
      if (ids != null && ids.isNotEmpty) {
        // One request per selected trigger, merged and sorted by date desc.
        final responses = await Future.wait(ids.map((id) => _logsClient
            .fetchLogs(
              page: _page,
              pageSize: widget.pageSize,
              type: widget.type,
              status: widget.status,
              triggerId: id,
              startDate: widget.startDate,
              endDate: widget.endDate,
            )
            .catchError((_) => CommunicationLogListResponse(
                total: 0,
                currentPage: 1,
                pageSize: widget.pageSize,
                totalPages: 1,
                logs: []))));
        logs = responses.expand((r) => r.logs).toList()
          ..sort((a, b) => DateTime.tryParse(b.createdAt)
                  ?.compareTo(DateTime.tryParse(a.createdAt) ?? DateTime(0)) ??
              0);
        totalPages = responses.fold<int>(0, (m, r) => m > r.totalPages ? m : r.totalPages);
      } else {
        final response = await _logsClient.fetchLogs(
          page: _page,
          pageSize: widget.pageSize,
          type: widget.type,
          status: widget.status,
          triggerId: widget.itemId,
          startDate: widget.startDate,
          endDate: widget.endDate,
        );
        logs = response.logs;
        totalPages = response.totalPages;
      }

      if (!mounted) return;
      setState(() {
        _logs = logs;
        _totalPages = totalPages;
        _isLoading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _errorMessage = 'Failed to load logs: $e';
        _isLoading = false;
      });
    }
  }

  void _goToPage(int page) {
    setState(() => _page = page);
    _loadLogs();
  }

  Color _statusColor(String status) {
    switch (status.toLowerCase()) {
      case 'sent':
      case 'delivered':
        return const Color(0xFF4CAF50);
      case 'pending':
        return const Color(0xFFFF9800);
      case 'failed':
        return const Color(0xFFF44336);
      default:
        return Colors.grey;
    }
  }

  IconData _typeIcon(String type) {
    switch (type.toLowerCase()) {
      case 'email':
        return Icons.mail_outline;
      case 'webhook':
        return Icons.webhook_outlined;
      case 'sms':
        return Icons.sms_outlined;
      case 'push_notification':
        return Icons.notifications_outlined;
      case 'audit':
      case 'audit_log':
        return Icons.article_outlined;
      default:
        return Icons.info_outline;
    }
  }

  String _headline(CommunicationLog log) {
    if (log.subjectLine != null && log.subjectLine!.trim().isNotEmpty) {
      return log.subjectLine!;
    }
    final type = log.communicationType.replaceAll('_', ' ');
    return '${type[0].toUpperCase()}${type.substring(1)} to ${log.recipient}';
  }

  Widget _chip(BuildContext context, String label, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: color.withValues(alpha: 0.45)),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.labelSmall?.copyWith(color: color),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Center(
        child: Padding(
          padding: EdgeInsets.all(24),
          child: CircularProgressIndicator(),
        ),
      );
    }

    if (_errorMessage != null) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(_errorMessage!, style: const TextStyle(color: Color(0xFFF44336))),
          const SizedBox(height: 8),
          OutlinedButton.icon(
            onPressed: _loadLogs,
            icon: const Icon(Icons.refresh),
            label: const Text('Retry'),
          ),
        ],
      );
    }

    if (_logs.isEmpty) {
      return Text(
        'No logs recorded for this item yet.',
        style: Theme.of(context).textTheme.bodyMedium,
      );
    }

    final formatter = DateFormat('MMM d, HH:mm');

    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
        for (final log in _logs)
          Builder(builder: (context) {
            final statusColor = _statusColor(log.status);
            final createdAt =
                DateTime.tryParse(log.createdAt)?.toLocal() ?? DateTime.now();
            return Card(
              margin: const EdgeInsets.only(bottom: 12),
              color: statusColor.withValues(alpha: 0.10),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12),
                side: BorderSide(color: statusColor.withValues(alpha: 0.45)),
              ),
              child: ListTile(
                contentPadding:
                    const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                leading: Container(
                  width: 40,
                  height: 40,
                  decoration: BoxDecoration(
                    color: statusColor.withValues(alpha: 0.18),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Icon(
                    _typeIcon(log.communicationType),
                    color: statusColor,
                    size: 22,
                  ),
                ),
                title: Text(_headline(log)),
                onTap: () => showCommunicationLogDetails(context, log),
                subtitle: Padding(
                  padding: const EdgeInsets.only(top: 4),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        [
                          formatter.format(createdAt),
                          log.recipient,
                          if (log.attempts > 1)
                            '${log.attempts} attempts',
                        ].join(' • '),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                      const SizedBox(height: 6),
                      Wrap(
                        spacing: 6,
                        runSpacing: 6,
                        children: [
                          _chip(
                              context, log.status.toUpperCase(), statusColor),
                          _chip(context, log.communicationType, statusColor),
                          if (log.errorMessage != null &&
                              log.errorMessage!.isNotEmpty)
                            _chip(
                                context, 'Error', const Color(0xFFF44336)),
                        ],
                      ),
                    ],
                  ),
                ),
                trailing: const Icon(Icons.chevron_right),
              ),
            );
          }),
        if (_totalPages > 1)
          Padding(
            padding: const EdgeInsets.only(top: 4),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                IconButton(
                  onPressed:
                      _page > 1 ? () => _goToPage(_page - 1) : null,
                  icon: const Icon(Icons.chevron_left),
                ),
                Text('Page $_page of $_totalPages'),
                IconButton(
                  onPressed: _page < _totalPages
                      ? () => _goToPage(_page + 1)
                      : null,
                  icon: const Icon(Icons.chevron_right),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// Log details dialogue — same content/UX as the one on the communication
/// logs screen. Shown when a log row is tapped.
void showCommunicationLogDetails(BuildContext context, CommunicationLog log) {
  showDialog(
    context: context,
    builder: (context) => AlertDialog(
      title: Text('Log Details: ${log.communicationType.toUpperCase()}'),
      content: SingleChildScrollView(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            _detailRow(context, 'UUID', log.uuid, copyable: true),
            _detailRow(context, 'Type', log.communicationType),
            _detailRow(context, 'Status', log.status),
            _detailRow(context, 'Recipient', log.recipient, copyable: true),
            if (log.subjectLine != null)
              _detailRow(context, 'Subject', log.subjectLine!),
            if (log.content != null)
              _detailRow(context, 'Content', log.content!, expandable: true),
            if (log.triggeredBy != null)
              _detailRow(context, 'Triggered By', log.triggeredBy!),
            if (log.triggerType != null)
              _detailRow(context, 'Trigger Type', log.triggerType!),
            if (log.triggerId != null)
              _detailRow(context, 'Trigger ID', log.triggerId!, copyable: true),
            if (log.payload != null &&
                log.payload!.containsKey('trigger_name'))
              _detailRow(context, 'Trigger Name',
                  log.payload!['trigger_name'].toString()),
            if (log.payload != null && log.payload!.containsKey('action_name'))
              _detailRow(context, 'Action Name',
                  log.payload!['action_name'].toString()),
            if (log.payload != null && log.payload!.containsKey('camera_id'))
              _detailRow(context, 'Camera ID',
                  log.payload!['camera_id'].toString(),
                  copyable: true),
            if (log.payload != null &&
                log.payload!.containsKey('people_count'))
              _detailRow(context, 'People Count',
                  log.payload!['people_count'].toString()),
            if (log.payload != null &&
                (log.payload!.containsKey('detection_timestamp') ||
                    log.payload!.containsKey('timestamp')))
              _detailRow(
                  context,
                  'Detection Time',
                  log.payload!['detection_timestamp']?.toString() ??
                      log.payload!['timestamp']?.toString() ??
                      ''),
            if (log.payload != null &&
                log.payload!.containsKey('demographics'))
              ..._demographicsRows(context, log.payload!['demographics']),
            if (log.responseStatusCode != null)
              _detailRow(
                  context, 'Response Status', log.responseStatusCode.toString()),
            if (log.errorMessage != null)
              _detailRow(context, 'Error', log.errorMessage!, isError: true),
            _detailRow(context, 'Attempts', log.attempts.toString()),
            if (log.installationId != null)
              _detailRow(context, 'Installation ID', log.installationId!,
                  copyable: true),
            if (log.tenantName != null)
              _detailRow(context, 'Tenant', log.tenantName!),
            if (log.payload != null && log.payload!.isNotEmpty)
              _detailRow(context, 'Full Payload', jsonEncode(log.payload),
                  expandable: true),
            _detailRow(
                context, 'Created At', _formatDateTimeString(log.createdAt)),
            _detailRow(
                context, 'Updated At', _formatDateTimeString(log.updatedAt)),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Close'),
        ),
      ],
    ),
  );
}

Widget _detailRow(
  BuildContext context,
  String label,
  String value, {
  bool copyable = false,
  bool isError = false,
  bool expandable = false,
}) {
  return Padding(
    padding: const EdgeInsets.only(bottom: 12),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: TextStyle(
            fontSize: 12,
            color: Colors.grey.shade400,
            fontWeight: FontWeight.w500,
          ),
        ),
        const SizedBox(height: 4),
        Row(
          children: [
            Expanded(
              child: Text(
                value,
                style: TextStyle(
                  fontSize: 14,
                  color: isError ? Colors.red.shade300 : Colors.white,
                ),
                maxLines: expandable ? null : 3,
                overflow: expandable ? null : TextOverflow.ellipsis,
              ),
            ),
            if (copyable)
              IconButton(
                icon: const Icon(Icons.copy, size: 16),
                onPressed: () {
                  Clipboard.setData(ClipboardData(text: value));
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(
                      content: Text('Copied to clipboard'),
                      duration: Duration(seconds: 1),
                    ),
                  );
                },
                tooltip: 'Copy',
              ),
          ],
        ),
        const Divider(height: 16),
      ],
    ),
  );
}

List<Widget> _demographicsRows(
    BuildContext context, dynamic demographicsData) {
  if (demographicsData == null) return [];

  final rows = <Widget>[];

  try {
    final demographics = demographicsData as Map<String, dynamic>;

    // Check total_ prefixed keys (actual structure from backend)
    for (final entry in const {
      'total_young': 'Young',
      'total_adult': 'Adult',
      'total_senior': 'Senior',
      'total_male': 'Male',
      'total_female': 'Female',
    }.entries) {
      if (demographics[entry.key] != null && demographics[entry.key] != 0) {
        rows.add(_detailRow(
            context, entry.value, demographics[entry.key].toString()));
      }
    }

    // Fallback: Check nested age_group structure
    if (rows.isEmpty && demographics['age_group'] != null) {
      final ageGroup = demographics['age_group'] as Map<String, dynamic>;
      for (final entry in const {
        'young': 'Young',
        'adult': 'Adult',
        'senior': 'Senior',
      }.entries) {
        if (ageGroup[entry.key] != null && ageGroup[entry.key] != 0) {
          rows.add(_detailRow(
              context, entry.value, ageGroup[entry.key].toString()));
        }
      }
    }

    // Fallback: Check nested gender structure
    if (rows.isEmpty && demographics['gender'] != null) {
      final gender = demographics['gender'] as Map<String, dynamic>;
      for (final entry in const {
        'male': 'Male',
        'female': 'Female',
      }.entries) {
        if (gender[entry.key] != null && gender[entry.key] != 0) {
          rows.add(_detailRow(
              context, entry.value, gender[entry.key].toString()));
        }
      }
    }
  } catch (_) {}

  return rows;
}

String _formatDateTimeString(String isoString) {
  try {
    final dt = DateTime.parse(isoString);
    return '${dt.year}-${dt.month.toString().padLeft(2, '0')}-${dt.day.toString().padLeft(2, '0')} '
        '${dt.hour.toString().padLeft(2, '0')}:${dt.minute.toString().padLeft(2, '0')}';
  } catch (e) {
    return isoString;
  }
}
