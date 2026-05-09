import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../core/providers/auth_provider.dart';
import '../core/theme/app_theme.dart';
import '../presentation/pages/people_counters_page.dart';
import '../services/people_counters_api_client.dart';

/// Compact dashboard tile summarizing People Counters automation health.
///
/// Renders only for admin users. Tap navigates to the full
/// PeopleCountersPage management surface.
class PeopleCountersTile extends ConsumerStatefulWidget {
  const PeopleCountersTile({super.key});

  @override
  ConsumerState<PeopleCountersTile> createState() => _PeopleCountersTileState();
}

class _PeopleCountersTileState extends ConsumerState<PeopleCountersTile> {
  final _client = PeopleCountersApiClient();
  Map<String, dynamic>? _status;
  String? _error;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    final res = await _client.getStatus();
    if (!mounted) return;
    setState(() {
      _loading = false;
      if (res.success) {
        _status = res.data;
      } else {
        _error = res.error ?? 'Failed to load status';
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final auth = ref.watch(authNotifierProvider);
    if (!(auth.user?.isAdmin ?? false)) {
      return const SizedBox.shrink();
    }

    final enabled = (_status?['enabled'] ?? false) == true;
    final paused = (_status?['paused'] ?? false) == true;
    final inflight = _status?['inflight'] ?? 0;
    final counts = (_status?['job_counts'] as Map?)?.cast<String, dynamic>() ?? const {};
    final lastSuccess = _status?['last_successful_batch_at']?.toString();

    return Card(
      margin: const EdgeInsets.symmetric(horizontal: AppSpacing.md, vertical: AppSpacing.sm),
      child: InkWell(
        onTap: () {
          Navigator.of(context).push(
            MaterialPageRoute(builder: (_) => const PeopleCountersPage()),
          );
        },
        child: Padding(
          padding: const EdgeInsets.all(AppSpacing.md),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(
                    Icons.groups,
                    color: enabled
                        ? (paused ? Colors.orange : Colors.green)
                        : Colors.grey,
                  ),
                  const SizedBox(width: 8),
                  const Expanded(
                    child: Text(
                      'People Counters',
                      style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.refresh, size: 20),
                    onPressed: _loading ? null : _load,
                    tooltip: 'Refresh',
                  ),
                ],
              ),
              const SizedBox(height: 8),
              if (_loading && _status == null)
                const Padding(
                  padding: EdgeInsets.symmetric(vertical: 8.0),
                  child: LinearProgressIndicator(minHeight: 2),
                )
              else if (_error != null)
                Text(_error!, style: const TextStyle(color: Colors.red))
              else ...[
                Row(
                  children: [
                    _StatusChip(
                      label: enabled
                          ? (paused ? 'Paused' : 'Enabled')
                          : 'Disabled',
                      color: enabled
                          ? (paused ? Colors.orange : Colors.green)
                          : Colors.grey,
                    ),
                    const SizedBox(width: 8),
                    _StatusChip(label: 'Inflight: $inflight', color: Colors.blue),
                  ],
                ),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 12,
                  runSpacing: 4,
                  children: [
                    _CountText('Success', counts['success'] ?? 0, Colors.green),
                    _CountText('Running', counts['running'] ?? 0, Colors.blue),
                    _CountText('Pending', counts['pending'] ?? 0, Colors.grey),
                    _CountText('Failed', counts['failed'] ?? 0, Colors.red),
                    _CountText('Dead-letter', counts['dead_letter'] ?? 0, Colors.deepOrange),
                  ],
                ),
                if (lastSuccess != null) ...[
                  const SizedBox(height: 8),
                  Text(
                    'Last success: $lastSuccess',
                    style: TextStyle(color: Colors.grey[600], fontSize: 12),
                  ),
                ],
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _StatusChip extends StatelessWidget {
  final String label;
  final Color color;
  const _StatusChip({required this.label, required this.color});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withOpacity(0.15),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withOpacity(0.4)),
      ),
      child: Text(
        label,
        style: TextStyle(color: color, fontSize: 12, fontWeight: FontWeight.w600),
      ),
    );
  }
}

class _CountText extends StatelessWidget {
  final String label;
  final dynamic value;
  final Color color;
  const _CountText(this.label, this.value, this.color);

  @override
  Widget build(BuildContext context) {
    return RichText(
      text: TextSpan(
        style: DefaultTextStyle.of(context).style,
        children: [
          TextSpan(
            text: '$value ',
            style: TextStyle(color: color, fontWeight: FontWeight.bold),
          ),
          TextSpan(
            text: label,
            style: TextStyle(color: Colors.grey[700], fontSize: 12),
          ),
        ],
      ),
    );
  }
}
