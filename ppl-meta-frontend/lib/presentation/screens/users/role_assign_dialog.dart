import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/providers/roles_provider.dart';
import '../../../core/models/role.dart';

/// Dialog for assigning and unassigning roles to/from a user.
class RoleAssignDialog extends ConsumerStatefulWidget {
  final int userId;
  final String userEmail;
  final List<String> currentRoles;

  const RoleAssignDialog({
    super.key,
    required this.userId,
    required this.userEmail,
    required this.currentRoles,
  });

  /// Show as a dialog, returning updated role names on success.
  static Future<List<String>?> show(
    BuildContext context, {
    required int userId,
    required String userEmail,
    required List<String> currentRoles,
  }) {
    return showDialog<List<String>>(
      context: context,
      builder: (_) => RoleAssignDialog(
        userId: userId,
        userEmail: userEmail,
        currentRoles: currentRoles,
      ),
    );
  }

  @override
  ConsumerState<RoleAssignDialog> createState() => _DialogState();
}

class _DialogState extends ConsumerState<RoleAssignDialog> {
  Map<int, bool> _selections = {};
  List<Role> _allRoles = [];
  bool _loading = true;
  bool _saving = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    Future.microtask(() => _load());
  }

  Future<void> _load() async {
    try {
      final n = ref.read(rolesNotifierProvider.notifier);
      await n.loadRoles();
      final roles = ref.read(rolesNotifierProvider).roles;
      setState(() {
        _allRoles = roles;
        _selections = {
          for (final r in roles) r.id: widget.currentRoles.contains(r.name),
        };
        _loading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  Future<void> _apply() async {
    setState(() => _saving = true);

    final toAssign = <int>[];
    final toUnassign = <int>[];

    for (final role in _allRoles) {
      final wasAssigned = widget.currentRoles.contains(role.name);
      final nowChecked = _selections[role.id] ?? false;
      if (!wasAssigned && nowChecked) {
        toAssign.add(role.id);
      } else if (wasAssigned && !nowChecked) {
        if (role.name == 'owner') {
          final remaining = _allRoles
              .where((r) =>
                  r.name == 'owner' &&
                  widget.currentRoles.contains(r.name) &&
                  (_selections[r.id] ?? false))
              .length;
          if (remaining <= 1) {
            setState(() {
              _error = 'Cannot remove the last owner role';
              _saving = false;
            });
            return;
          }
        }
        toUnassign.add(role.id);
      }
    }

    try {
      final n = ref.read(rolesNotifierProvider.notifier);
      for (final rid in toAssign) {
        await n.assignRoleToUser(widget.userId, rid);
      }
      for (final rid in toUnassign) {
        await n.unassignRoleFromUser(widget.userId, rid);
      }
      final updated = _allRoles
          .where((r) => _selections[r.id] == true)
          .map((r) => r.name)
          .toList();
      if (mounted) Navigator.of(context).pop(updated);
    } catch (e) {
      setState(() {
        _error = e.toString();
        _saving = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Manage Roles'),
      content: SizedBox(
        width: double.maxFinite,
        height: 400,
        child: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(widget.userEmail,
                style: TextStyle(fontSize: 12, color: Colors.grey[600])),
            const Divider(),
            if (_loading)
              const Center(child: CircularProgressIndicator())
            else if (_error != null && _allRoles.isEmpty)
              Text(_error!, style: const TextStyle(color: Colors.red))
            else ...[
              if (_error != null)
                Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Text(_error!,
                      style: const TextStyle(color: Colors.red, fontSize: 12)),
                ),
              ..._allRoles.map((role) => CheckboxListTile(
                    title: Text(role.name),
                    subtitle: Text(
                      role.isSystemRole ? 'System role' : 'Custom role',
                      style: TextStyle(fontSize: 12, color: Colors.grey[600]),
                    ),
                    value: _selections[role.id] ?? false,
                    onChanged: _saving
                        ? null
                        : (v) => setState(() {
                              _selections[role.id] = v ?? false;
                              _error = null;
                            }),
                    controlAffinity: ListTileControlAffinity.leading,
                    dense: true,
                  )),
            ],
          ],
        ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: _saving ? null : () => Navigator.of(context).pop(),
          child: const Text('Cancel'),
        ),
        FilledButton(
          onPressed: (_loading || _saving) ? null : _apply,
          child: _saving
              ? const SizedBox(
                  width: 16,
                  height: 16,
                  child: CircularProgressIndicator(
                      strokeWidth: 2, color: Colors.white))
              : const Text('Apply'),
        ),
      ],
    );
  }
}

