import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../core/providers/roles_provider.dart';
import '../../../core/models/role.dart';
import '../../../widgets/custom_app_bar.dart';

class RolesScreen extends ConsumerStatefulWidget {
  const RolesScreen({super.key});
  @override
  ConsumerState<RolesScreen> createState() => _RolesScreenState();
}

class _RolesScreenState extends ConsumerState<RolesScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(rolesNotifierProvider.notifier).loadRoles();
    });
  }

  Future<void> _createRole() async {
    final ctrl = TextEditingController();
    final name = await showDialog<String>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Create Role'),
        content: TextField(controller: ctrl, decoration: const InputDecoration(hintText: 'Role name'), autofocus: true),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.pop(context, ctrl.text.trim()), child: const Text('Create')),
        ],
      ),
    );
    if (name != null && name.isNotEmpty) {
      try {
        await ref.read(rolesNotifierProvider.notifier).createRole(name);
      } catch (e) {
        if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Error: $e')));
      }
    }
  }

  Future<void> _renameRole(Role role) async {
    final ctrl = TextEditingController(text: role.name);
    final newName = await showDialog<String>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Rename Role'),
        content: TextField(controller: ctrl, decoration: const InputDecoration(hintText: 'New name'), autofocus: true),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.pop(context, ctrl.text.trim()), child: const Text('Rename')),
        ],
      ),
    );
    if (newName != null && newName.isNotEmpty && newName != role.name) {
      try {
        await ref.read(rolesNotifierProvider.notifier).updateRole(role.id, newName);
      } catch (e) {
        if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Error: $e')));
      }
    }
  }

  Future<void> _deleteRole(Role role) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: Text('Delete "${role.name}"?'),
        content: const Text('This cannot be undone.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancel')),
          FilledButton(style: FilledButton.styleFrom(backgroundColor: Colors.red), onPressed: () => Navigator.pop(context, true), child: const Text('Delete')),
        ],
      ),
    );
    if (ok == true) {
      try {
        await ref.read(rolesNotifierProvider.notifier).deleteRole(role.id);
      } catch (e) {
        if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Error: $e')));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(rolesNotifierProvider);
    return Scaffold(
      appBar: CustomAppBar(title: 'Roles', actions: [IconButton(icon: const Icon(Icons.add), tooltip: 'Create Role', onPressed: _createRole)]),
      body: _buildBody(state),
    );
  }

  Widget _buildBody(RolesState state) {
    if (state.isLoading && state.roles.isEmpty) return const Center(child: CircularProgressIndicator());
    if (state.error != null && state.roles.isEmpty) {
      return Center(child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
        const Icon(Icons.error_outline, size: 64, color: Colors.red), const SizedBox(height: 16),
        Text(state.error!, style: const TextStyle(color: Colors.red)), const SizedBox(height: 16),
        ElevatedButton(onPressed: () => ref.read(rolesNotifierProvider.notifier).loadRoles(), child: const Text('Retry')),
      ]));
    }
    if (state.roles.isEmpty) return const Center(child: Text('No roles found'));
    return ListView.builder(
      padding: const EdgeInsets.all(12), itemCount: state.roles.length,
      itemBuilder: (_, i) => _RoleCard(
        role: state.roles[i], onTap: () => context.go('/roles/${state.roles[i].id}'),
        onRename: state.roles[i].isSystemRole ? null : () => _renameRole(state.roles[i]),
        onDelete: state.roles[i].isSystemRole ? null : () => _deleteRole(state.roles[i]),
      ),
    );
  }
}

class _RoleCard extends StatelessWidget {
  final Role role;
  final VoidCallback onTap;
  final VoidCallback? onRename;
  final VoidCallback? onDelete;

  const _RoleCard({required this.role, required this.onTap, this.onRename, this.onDelete});

  IconData _icon() {
    switch (role.name) { case 'owner': return Icons.workspace_premium; case 'admin': return Icons.shield; case 'user': return Icons.person; default: return Icons.badge; }
  }

  Color _color() {
    switch (role.name) { case 'owner': return Colors.amber.shade800; case 'admin': return Colors.deepPurple; case 'user': return Colors.blue; default: return Colors.teal; }
  }

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: ListTile(
        leading: Icon(_icon(), color: _color(), size: 32),
        title: Text(role.name, style: TextStyle(fontWeight: FontWeight.bold, color: _color())),
        subtitle: Text(role.isSystemRole ? 'System role' : 'Custom role'),
        trailing: Row(mainAxisSize: MainAxisSize.min, children: [
          if (onRename != null) IconButton(icon: const Icon(Icons.edit, size: 18), onPressed: onRename),
          if (onDelete != null) IconButton(icon: const Icon(Icons.delete, size: 18), onPressed: onDelete),
          const Icon(Icons.chevron_right),
        ]),
        onTap: onTap,
      ),
    );
  }
}