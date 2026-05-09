import 'package:flutter/material.dart';
import '../../services/people_counters_api_client.dart';
import '../../models/api_response.dart';

/// Settings → People Counters
///
/// Surface for the orchestrator-owned automation pipeline:
///   • Status / pause / resume
///   • Live numeric workflow settings (12 keys)
///   • Manual daily-batch run + backfill
///   • Recent jobs list with retry / invalidate
///   • Dead-letter inspector
///
/// See: docs/proposals/people-counters.md §5.9
class PeopleCountersPage extends StatefulWidget {
  const PeopleCountersPage({Key? key}) : super(key: key);

  @override
  State<PeopleCountersPage> createState() => _PeopleCountersPageState();
}

class _PeopleCountersPageState extends State<PeopleCountersPage>
    with SingleTickerProviderStateMixin {
  final PeopleCountersApiClient _api = PeopleCountersApiClient();
  late final TabController _tabController;

  Map<String, dynamic>? _status;
  Map<String, dynamic>? _settings;
  List<dynamic> _jobs = [];
  List<dynamic> _deadLetter = [];

  bool _loadingStatus = false;
  bool _loadingSettings = false;
  bool _loadingJobs = false;
  bool _loadingDeadLetter = false;

  String? _jobsCameraFilter;
  String? _jobsStatusFilter;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 4, vsync: this);
    _refreshAll();
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _refreshAll() async {
    await Future.wait([
      _loadStatus(),
      _loadSettings(),
      _loadJobs(),
      _loadDeadLetter(),
    ]);
  }

  Future<void> _loadStatus() async {
    setState(() => _loadingStatus = true);
    final res = await _api.getStatus();
    if (!mounted) return;
    setState(() {
      _loadingStatus = false;
      if (res.success) _status = res.data;
    });
    if (!res.success) _snack('Status: ${res.error}', isError: true);
  }

  Future<void> _loadSettings() async {
    setState(() => _loadingSettings = true);
    final res = await _api.getSettings();
    if (!mounted) return;
    setState(() {
      _loadingSettings = false;
      if (res.success) _settings = res.data;
    });
    if (!res.success) _snack('Settings: ${res.error}', isError: true);
  }

  Future<void> _loadJobs() async {
    setState(() => _loadingJobs = true);
    final res = await _api.listJobs(
      cameraId: _jobsCameraFilter,
      status: _jobsStatusFilter,
      limit: 100,
    );
    if (!mounted) return;
    setState(() {
      _loadingJobs = false;
      if (res.success) _jobs = (res.data?['jobs'] as List?) ?? [];
    });
    if (!res.success) _snack('Jobs: ${res.error}', isError: true);
  }

  Future<void> _loadDeadLetter() async {
    setState(() => _loadingDeadLetter = true);
    final res = await _api.deadLetter(limit: 100);
    if (!mounted) return;
    setState(() {
      _loadingDeadLetter = false;
      if (res.success) _deadLetter = (res.data?['jobs'] as List?) ?? [];
    });
    if (!res.success) _snack('Dead-letter: ${res.error}', isError: true);
  }

  void _snack(String msg, {bool isError = false}) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(msg),
        backgroundColor: isError ? Colors.red.shade700 : null,
      ),
    );
  }

  // ---------------------------------------------------------------------------
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('People Counters'),
        backgroundColor: Colors.indigo,
        actions: [
          IconButton(
            tooltip: 'Refresh',
            icon: const Icon(Icons.refresh),
            onPressed: _refreshAll,
          ),
        ],
        bottom: TabBar(
          controller: _tabController,
          isScrollable: true,
          labelColor: Colors.white,
          tabs: const [
            Tab(icon: Icon(Icons.dashboard), text: 'Status'),
            Tab(icon: Icon(Icons.tune), text: 'Settings'),
            Tab(icon: Icon(Icons.list_alt), text: 'Jobs'),
            Tab(icon: Icon(Icons.report_problem), text: 'Dead-letter'),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tabController,
        children: [
          _buildStatusTab(),
          _buildSettingsTab(),
          _buildJobsTab(),
          _buildDeadLetterTab(),
        ],
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // STATUS TAB
  // ---------------------------------------------------------------------------
  Widget _buildStatusTab() {
    if (_loadingStatus && _status == null) {
      return const Center(child: CircularProgressIndicator());
    }
    final s = _status ?? {};
    final enabled = s['enabled'] == true;
    final running = s['running'] == true;
    final inflight = s['inflight'] ?? 0;
    final counts = (s['counts'] as Map?) ?? {};

    return RefreshIndicator(
      onRefresh: _loadStatus,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            color: enabled
                ? Colors.green.withOpacity(0.1)
                : Colors.orange.withOpacity(0.1),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Row(
                children: [
                  Icon(
                    enabled ? Icons.play_circle : Icons.pause_circle,
                    size: 48,
                    color: enabled ? Colors.green : Colors.orange,
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          enabled ? 'Enabled' : 'Paused',
                          style: const TextStyle(
                              fontSize: 22, fontWeight: FontWeight.bold),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          'Worker: ${running ? "running" : "stopped"} • Inflight: $inflight',
                        ),
                      ],
                    ),
                  ),
                  enabled
                      ? OutlinedButton.icon(
                          icon: const Icon(Icons.pause),
                          label: const Text('Pause'),
                          onPressed: () async {
                            final res = await _api.pause();
                            if (res.success) {
                              _snack('Paused');
                              _loadStatus();
                            } else {
                              _snack(res.error ?? 'Pause failed',
                                  isError: true);
                            }
                          },
                        )
                      : ElevatedButton.icon(
                          icon: const Icon(Icons.play_arrow),
                          label: const Text('Resume'),
                          onPressed: () async {
                            final res = await _api.resume();
                            if (res.success) {
                              _snack('Resumed');
                              _loadStatus();
                            } else {
                              _snack(res.error ?? 'Resume failed',
                                  isError: true);
                            }
                          },
                        ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          const Text('Job counts',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
          const SizedBox(height: 8),
          GridView.count(
            crossAxisCount: 3,
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            childAspectRatio: 2.5,
            crossAxisSpacing: 8,
            mainAxisSpacing: 8,
            children: counts.entries
                .map((e) => _statTile(e.key.toString(), e.value))
                .toList(),
          ),
          const SizedBox(height: 16),
          ElevatedButton.icon(
            icon: const Icon(Icons.play_circle_outline),
            label: const Text('Run daily-batch (now)'),
            onPressed: _runDailyBatchDialog,
          ),
        ],
      ),
    );
  }

  Widget _statTile(String label, dynamic value) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(8),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text('$value',
                style: const TextStyle(
                    fontSize: 22, fontWeight: FontWeight.bold)),
            Text(label, style: const TextStyle(fontSize: 12)),
          ],
        ),
      ),
    );
  }

  Future<void> _runDailyBatchDialog() async {
    final cameraCtrl = TextEditingController();
    bool force = false;
    DateTime? selectedDate;

    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setLocal) => AlertDialog(
          title: const Text('Run daily-batch'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                TextField(
                  controller: cameraCtrl,
                  decoration: const InputDecoration(
                    labelText: 'Camera IDs (comma-separated, blank = all)',
                  ),
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    const Text('Date: '),
                    TextButton.icon(
                      icon: const Icon(Icons.calendar_today, size: 16),
                      label: Text(selectedDate == null
                          ? 'Today (UTC)'
                          : selectedDate!.toIso8601String().substring(0, 10)),
                      onPressed: () async {
                        final picked = await showDatePicker(
                          context: ctx,
                          initialDate: DateTime.now(),
                          firstDate: DateTime(2024),
                          lastDate: DateTime.now(),
                        );
                        if (picked != null) {
                          setLocal(() => selectedDate = picked);
                        }
                      },
                    ),
                  ],
                ),
                CheckboxListTile(
                  contentPadding: EdgeInsets.zero,
                  value: force,
                  title: const Text('Force re-run (invalidate existing batches)'),
                  onChanged: (v) => setLocal(() => force = v ?? false),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
                onPressed: () => Navigator.pop(ctx, false),
                child: const Text('Cancel')),
            ElevatedButton(
                onPressed: () => Navigator.pop(ctx, true),
                child: const Text('Run')),
          ],
        ),
      ),
    );

    if (ok != true) return;

    final cams = cameraCtrl.text
        .split(',')
        .map((s) => s.trim())
        .where((s) => s.isNotEmpty)
        .toList();

    final res = await _api.runDailyBatch(
      date: selectedDate,
      cameraIds: cams.isEmpty ? null : cams,
      force: force,
    );

    if (res.success) {
      _snack('Daily-batch enqueued');
      await _loadJobs();
      await _loadStatus();
    } else {
      _snack(res.error ?? 'Run failed', isError: true);
    }
  }

  // ---------------------------------------------------------------------------
  // SETTINGS TAB
  // ---------------------------------------------------------------------------
  Widget _buildSettingsTab() {
    if (_loadingSettings && _settings == null) {
      return const Center(child: CircularProgressIndicator());
    }
    final s = _settings ?? {};
    final entries = s.entries.toList()
      ..sort((a, b) => a.key.compareTo(b.key));

    return RefreshIndicator(
      onRefresh: _loadSettings,
      child: ListView(
        padding: const EdgeInsets.all(8),
        children: entries
            .map((e) => _settingTile(e.key, _toDouble(e.value)))
            .toList(),
      ),
    );
  }

  double _toDouble(dynamic v) {
    if (v is num) return v.toDouble();
    return double.tryParse(v?.toString() ?? '') ?? 0.0;
  }

  Widget _settingTile(String key, double value) {
    final ctrl = TextEditingController(text: value.toString());
    return Card(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        child: Row(
          children: [
            Expanded(
              flex: 3,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(key,
                      style: const TextStyle(fontWeight: FontWeight.bold)),
                  Text(_helpFor(key),
                      style:
                          TextStyle(color: Colors.grey[600], fontSize: 12)),
                ],
              ),
            ),
            const SizedBox(width: 8),
            SizedBox(
              width: 100,
              child: TextField(
                controller: ctrl,
                keyboardType: const TextInputType.numberWithOptions(
                    decimal: true, signed: false),
                textAlign: TextAlign.right,
                decoration: const InputDecoration(
                    isDense: true, border: OutlineInputBorder()),
              ),
            ),
            IconButton(
              icon: const Icon(Icons.save, color: Colors.indigo),
              onPressed: () async {
                final newValue = double.tryParse(ctrl.text);
                if (newValue == null) {
                  _snack('Invalid number', isError: true);
                  return;
                }
                final res = await _api.updateSetting(key, newValue);
                if (res.success) {
                  _snack('Saved $key=$newValue');
                  await _loadSettings();
                } else {
                  _snack(res.error ?? 'Save failed', isError: true);
                }
              },
            ),
          ],
        ),
      ),
    );
  }

  String _helpFor(String key) {
    switch (key) {
      case 'people_counters_enabled':
        return '0 = paused, 1 = enabled';
      case 'people_counters_batch_seconds':
        return 'Batch window length (default 3600 = 1h)';
      case 'people_counters_workers':
        return 'Concurrent workers during normal hours';
      case 'people_counters_quiet_workers':
        return 'Concurrent workers during quiet hours';
      case 'people_counters_max_cpu_pct':
        return 'CPU ceiling (%) before throttling';
      case 'people_counters_max_inflight':
        return 'Max simultaneously running batches';
      case 'people_counters_backoff_seconds':
        return 'Cooldown after a failed attempt';
      case 'people_counters_per_batch_timeout_seconds':
        return 'Hard timeout per batch';
      case 'people_counters_max_attempts':
        return 'Retries before dead-letter';
      case 'people_counters_backfill_daily_budget':
        return 'Max older-than-yesterday batches per day';
      case 'people_counters_quiet_hours_start':
        return 'Hour [0-23] quiet window starts';
      case 'people_counters_quiet_hours_end':
        return 'Hour [0-23] quiet window ends';
      default:
        return '';
    }
  }

  // ---------------------------------------------------------------------------
  // JOBS TAB
  // ---------------------------------------------------------------------------
  Widget _buildJobsTab() {
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.all(8),
          child: Row(
            children: [
              Expanded(
                child: TextField(
                  decoration: const InputDecoration(
                    labelText: 'Camera ID',
                    isDense: true,
                    border: OutlineInputBorder(),
                  ),
                  onSubmitted: (v) {
                    _jobsCameraFilter = v.trim().isEmpty ? null : v.trim();
                    _loadJobs();
                  },
                ),
              ),
              const SizedBox(width: 8),
              DropdownButton<String?>(
                value: _jobsStatusFilter,
                hint: const Text('Status'),
                items: const [
                  DropdownMenuItem(value: null, child: Text('All')),
                  DropdownMenuItem(value: 'pending', child: Text('Pending')),
                  DropdownMenuItem(value: 'running', child: Text('Running')),
                  DropdownMenuItem(value: 'success', child: Text('Success')),
                  DropdownMenuItem(value: 'failed', child: Text('Failed')),
                  DropdownMenuItem(
                      value: 'dead_letter', child: Text('Dead-letter')),
                ],
                onChanged: (v) {
                  setState(() => _jobsStatusFilter = v);
                  _loadJobs();
                },
              ),
              IconButton(
                icon: const Icon(Icons.refresh),
                onPressed: _loadJobs,
              ),
            ],
          ),
        ),
        Expanded(
          child: _loadingJobs
              ? const Center(child: CircularProgressIndicator())
              : _jobs.isEmpty
                  ? const Center(child: Text('No jobs'))
                  : ListView.builder(
                      itemCount: _jobs.length,
                      itemBuilder: (ctx, i) =>
                          _jobTile(_jobs[i] as Map<String, dynamic>),
                    ),
        ),
      ],
    );
  }

  Widget _jobTile(Map<String, dynamic> job) {
    final status = (job['status'] ?? 'pending').toString();
    final batchKey = (job['batch_key'] ?? '').toString();
    final cameraId = (job['camera_id'] ?? '').toString();
    final start = (job['batch_start_utc'] ?? '').toString();
    final tier = job['priority_tier'] ?? '?';
    final attempts = job['attempts'] ?? 0;
    final stale = job['is_stale_refresh'] == true;

    Color color;
    IconData icon;
    switch (status) {
      case 'success':
        color = Colors.green;
        icon = Icons.check_circle;
        break;
      case 'running':
        color = Colors.blue;
        icon = Icons.autorenew;
        break;
      case 'failed':
        color = Colors.orange;
        icon = Icons.error_outline;
        break;
      case 'dead_letter':
        color = Colors.red;
        icon = Icons.report;
        break;
      default:
        color = Colors.grey;
        icon = Icons.schedule;
    }

    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      child: ListTile(
        leading: Icon(icon, color: color),
        title: Text('$cameraId  ·  $start',
            maxLines: 1, overflow: TextOverflow.ellipsis),
        subtitle: Text(
            'tier=$tier · attempts=$attempts ${stale ? "· stale-refresh" : ""}'),
        trailing: PopupMenuButton<String>(
          onSelected: (v) async {
            if (v == 'retry') {
              final res = await _api.retryJob(batchKey);
              _snack(res.success ? 'Retry queued' : (res.error ?? 'failed'),
                  isError: !res.success);
              _loadJobs();
            } else if (v == 'invalidate') {
              final res = await _api.invalidateBatch(batchKey);
              _snack(
                  res.success ? 'Invalidated' : (res.error ?? 'failed'),
                  isError: !res.success);
              _loadJobs();
            } else if (v == 'detail') {
              _showJobDetail(batchKey);
            }
          },
          itemBuilder: (_) => const [
            PopupMenuItem(value: 'detail', child: Text('Details')),
            PopupMenuItem(value: 'retry', child: Text('Retry')),
            PopupMenuItem(value: 'invalidate', child: Text('Invalidate')),
          ],
        ),
      ),
    );
  }

  Future<void> _showJobDetail(String batchKey) async {
    final res = await _api.getJob(batchKey);
    if (!mounted) return;
    if (!res.success) {
      _snack(res.error ?? 'Lookup failed', isError: true);
      return;
    }
    final job = res.data ?? {};
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Batch detail'),
        content: SingleChildScrollView(
          child: SelectableText(
            job.entries.map((e) => '${e.key}: ${e.value}').join('\n'),
            style: const TextStyle(fontFamily: 'monospace', fontSize: 12),
          ),
        ),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('Close')),
        ],
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // DEAD-LETTER TAB
  // ---------------------------------------------------------------------------
  Widget _buildDeadLetterTab() {
    return RefreshIndicator(
      onRefresh: _loadDeadLetter,
      child: _loadingDeadLetter
          ? const Center(child: CircularProgressIndicator())
          : _deadLetter.isEmpty
              ? ListView(
                  children: const [
                    SizedBox(height: 200),
                    Center(child: Text('No dead-letter jobs')),
                  ],
                )
              : ListView.builder(
                  itemCount: _deadLetter.length,
                  itemBuilder: (ctx, i) {
                    final job = _deadLetter[i] as Map<String, dynamic>;
                    return Card(
                      margin: const EdgeInsets.symmetric(
                          horizontal: 8, vertical: 4),
                      child: ListTile(
                        leading: const Icon(Icons.report, color: Colors.red),
                        title: Text(
                            '${job['camera_id']} · ${job['batch_start_utc']}'),
                        subtitle: Text(
                          'attempts=${job['attempts']} · ${job['last_error'] ?? ""}',
                          maxLines: 3,
                          overflow: TextOverflow.ellipsis,
                        ),
                        trailing: IconButton(
                          icon: const Icon(Icons.replay),
                          tooltip: 'Retry',
                          onPressed: () async {
                            final res =
                                await _api.retryJob(job['batch_key'].toString());
                            _snack(
                                res.success
                                    ? 'Retry queued'
                                    : (res.error ?? 'failed'),
                                isError: !res.success);
                            _loadDeadLetter();
                          },
                        ),
                      ),
                    );
                  },
                ),
    );
  }
}
