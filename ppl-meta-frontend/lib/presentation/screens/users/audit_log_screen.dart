import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/api/api_client.dart';
import '../../../widgets/custom_app_bar.dart';

class AuditLogScreen extends ConsumerStatefulWidget {
  const AuditLogScreen({super.key});
  @override
  ConsumerState<AuditLogScreen> createState() => _AuditLogScreenState();
}

class _AuditLogScreenState extends ConsumerState<AuditLogScreen> {
  List<Map<String, dynamic>> _actions = [];
  bool _isLoading = true;
  String? _error;
  String _filter = 'All';

  static const _filters = ['All', 'role', 'capability', 'user', 'auth'];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() { _isLoading = true; _error = null; });
    try {
      final api = ref.read(apiClientProvider);
      final resp = await api.get<List<dynamic>>('/actions/', queryParameters: {'skip': 0, 'limit': 100});
      final data = resp.data;
      if (data != null) {
        setState(() { _actions = data.cast<Map<String, dynamic>>(); _isLoading = false; });
      }
    } catch (e) {
      setState(() { _error = e.toString(); _isLoading = false; });
    }
  }

  List<Map<String, dynamic>> get _filtered {
    if (_filter == 'All') return _actions;
    return _actions.where((a) {
      final action = (a['action'] ?? '').toString();
      return action.startsWith('${_filter}_');
    }).toList();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: const CustomAppBar(title: 'Audit Log'),
      body: Column(children: [
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          child: SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: _filters.map((f) => Padding(
                padding: const EdgeInsets.only(right: 8),
                child: FilterChip(
                  label: Text(f),
                  selected: _filter == f,
                  onSelected: (_) => setState(() => _filter = f),
                ),
              )).toList(),
            ),
          ),
        ),
        Expanded(child: _buildList()),
      ]),
    );
  }

  Widget _buildList() {
    if (_isLoading) return const Center(child: CircularProgressIndicator());
    if (_error != null) return Center(child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
      Text(_error!, style: const TextStyle(color: Colors.red)), const SizedBox(height: 16),
      ElevatedButton(onPressed: _load, child: const Text('Retry')),
    ]));
    if (_filtered.isEmpty) return const Center(child: Text('No actions found'));
    return ListView.builder(
      padding: const EdgeInsets.all(12),
      itemCount: _filtered.length,
      itemBuilder: (_, i) {
        final a = _filtered[i];
        final ts = a['timestamp']?.toString() ?? '';
        final username = a['username']?.toString() ?? '?';
        final action = a['action']?.toString() ?? '';
        return Card(
          margin: const EdgeInsets.only(bottom: 6),
          child: ListTile(
            dense: true,
            leading: const Icon(Icons.history, size: 20),
            title: Text(action, style: const TextStyle(fontSize: 13, fontFamily: 'monospace')),
            subtitle: Text('$username  •  ${ts.length > 19 ? ts.substring(0, 19) : ts}', style: TextStyle(fontSize: 11, color: Colors.grey[600])),
          ),
        );
      },
    );
  }
}