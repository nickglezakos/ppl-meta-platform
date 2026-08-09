import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/providers/roles_provider.dart';
import '../../../core/providers/capabilities_provider.dart';
import '../../../core/models/role.dart';
import '../../../core/models/capability.dart';
import '../../../widgets/custom_app_bar.dart';

class RoleDetailScreen extends ConsumerStatefulWidget {
  final int roleId;
  const RoleDetailScreen({super.key, required this.roleId});

  @override
  ConsumerState<RoleDetailScreen> createState() => _RoleDetailScreenState();
}

class _RoleDetailScreenState extends ConsumerState<RoleDetailScreen> {
  Role? _role;
  List<Capability> _capabilities = [];
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() { _isLoading = true; _error = null; });
    try {
      final rolesN = ref.read(rolesNotifierProvider.notifier);
      await rolesN.loadRoles();
      final role = ref.read(rolesNotifierProvider).roles.where((r) => r.id == widget.roleId).firstOrNull;
      if (role == null) { setState(() { _error = 'Role not found'; _isLoading = false; }); return; }
      final capsSvc = ref.read(capabilitiesServiceProvider);
      final caps = await capsSvc.getCapabilitiesByRole(widget.roleId);
      setState(() { _role = role; _capabilities = caps; _isLoading = false; });
    } catch (e) {
      setState(() { _error = e.toString(); _isLoading = false; });
    }
  }

  Future<void> _removeCapability(Capability cap) async {
    try {
      await ref.read(rolesNotifierProvider.notifier).removeCapabilityFromRole(widget.roleId, cap.id);
      setState(() => _capabilities.removeWhere((c) => c.id == cap.id));
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Removed ${cap.name}')));
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Error: $e'), backgroundColor: Colors.red));
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) return Scaffold(appBar: const CustomAppBar(title: 'Role Detail'), body: const Center(child: CircularProgressIndicator()));
    if (_error != null) return Scaffold(appBar: const CustomAppBar(title: 'Role Detail'), body: Center(child: Text(_error!, style: const TextStyle(color: Colors.red))));
    if (_role == null) return Scaffold(appBar: const CustomAppBar(title: 'Role Detail'), body: const Center(child: Text('Role not found')));

    final role = _role!;
    final grouped = <String, List<Capability>>{};
    for (final c in _capabilities) { grouped.putIfAbsent(_namespace(c.name), () => []).add(c); }

    return Scaffold(
      appBar: CustomAppBar(title: 'Role: ${role.name}'),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Card(child: Padding(padding: const EdgeInsets.all(16), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [Icon(_icon(role.name), color: _color(role.name), size: 28), const SizedBox(width: 12),
              Text(role.name, style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.bold, color: _color(role.name)))]),
            const SizedBox(height: 8),
            Text('Type: ${role.isSystemRole ? "System role (immutable)" : "Custom role"}'),
            Text('Capabilities: ${_capabilities.length}'),
          ]))),
          const SizedBox(height: 16),
          Text('Capabilities', style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold)),
          const SizedBox(height: 8),
          ...grouped.entries.map((entry) => Card(
            margin: const EdgeInsets.only(bottom: 8),
            child: ExpansionTile(
              title: Text(_nsLabel(entry.key), style: const TextStyle(fontWeight: FontWeight.w600)),
              subtitle: Text('${entry.value.length} capabilities'),
              initiallyExpanded: true,
              children: entry.value.map((cap) => ListTile(
                dense: true,
                leading: const Icon(Icons.check_circle, color: Colors.green, size: 18),
                title: Text(cap.name, style: const TextStyle(fontSize: 13, fontFamily: 'monospace')),
                trailing: IconButton(icon: const Icon(Icons.remove_circle_outline, color: Colors.red, size: 20), onPressed: () => _removeCapability(cap), tooltip: 'Remove'),
              )).toList(),
            ),
          )),
        ]),
      ),
    );
  }

  String _namespace(String name) { if (name.contains(':')) return name.split(':').first; if (name.contains('.')) return name.split('.').first; return 'other'; }
  String _nsLabel(String ns) { const labels = {'auth':'Auth','users':'Users','cameras':'Cameras','media':'Media','analytics':'Analytics','workflows':'Workflows','operations':'Operations','system':'System','vision':'Vision'}; return labels[ns] ?? ns; }
  IconData _icon(String name) { switch(name){ case 'owner': return Icons.workspace_premium; case 'admin': return Icons.shield; case 'user': return Icons.person; default: return Icons.badge; } }
  Color _color(String name) { switch(name){ case 'owner': return Colors.amber.shade800; case 'admin': return Colors.deepPurple; case 'user': return Colors.blue; default: return Colors.teal; } }
}