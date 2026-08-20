/// Shared editor body + responsive surfaces (plan §5.1).
///
/// Only the *surface* changes with viewport:
///   desktop -> inline panel inside the master/detail split,
///   tablet  -> centered dialog,
///   mobile  -> full-screen route.
/// The body and its sticky Save/Cancel footer are the SAME widget everywhere.
library;

import 'package:flutter/material.dart';
import '../models/mock_data.dart';
import '../ux/breakpoints.dart';
import '../ux/unified_toggle.dart';

class ResourceEditor extends StatefulWidget {
  const ResourceEditor({
    super.key,
    required this.resource,
    this.item,
    this.createMode,
    required this.onSave,
    this.onCancel,
    this.onDelete,
  });

  final MockResource resource;
  final MockItem? item; // null => create mode
  final bool? createMode; // explicit override for inline desktop create
  final void Function(MockItem saved) onSave;
  final VoidCallback? onCancel;
  final void Function(MockItem item)? onDelete;

  @override
  State<ResourceEditor> createState() => _ResourceEditorState();
}

class _ResourceEditorState extends State<ResourceEditor> {
  late final bool _isNew = widget.createMode ?? widget.item == null;
  late final MockItem _draft = widget.item?.copy() ??
      MockItem(
        id: 'new-${DateTime.now().millisecondsSinceEpoch}',
        name: '',
        subtitle: '',
        icon: widget.resource.icon,
        enabled: true,
        toggles: {
          for (final k in widget.resource.items.isNotEmpty
              ? widget.resource.items.first.toggles.keys
              : <String>[])
            k: false,
        },
        created: 'just now',
        primarySetting: '—',
      );
  late final TextEditingController _name =
      TextEditingController(text: _draft.name);
  late final TextEditingController _subtitle =
      TextEditingController(text: _draft.subtitle);
  String? _nameError;

  @override
  void dispose() {
    _name.dispose();
    _subtitle.dispose();
    super.dispose();
  }

  void _save() {
    setState(() {
      _nameError = _name.text.trim().isEmpty ? 'Name is required' : null;
    });
    if (_nameError != null) return;
    _draft
      ..name = _name.text.trim()
      ..subtitle = _subtitle.text.trim();
    widget.onSave(_draft);
  }

  Future<void> _confirmDelete() async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete this item?'),
        content: Text('"${widget.item!.name}" will be removed. This cannot be undone.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            style: FilledButton.styleFrom(
              backgroundColor: Theme.of(context).colorScheme.error,
            ),
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
    if (ok == true && widget.item != null) {
      widget.onDelete?.call(widget.item!);
    }
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;

    return ConstrainedBox(
      constraints: BoxConstraints(
        maxWidth: isWide(context) ? double.infinity : 620,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        mainAxisSize: MainAxisSize.min,
        children: [
          Flexible(
            child: SingleChildScrollView(
              padding: EdgeInsets.all(isWide(context) ? 16 : 20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    _isNew ? 'New ${widget.resource.name}' : 'Edit ${widget.item!.name}',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 16),
                  TextField(
                    controller: _name,
                    decoration: InputDecoration(
                      labelText: 'Name',
                      border: const OutlineInputBorder(),
                      errorText: _nameError,
                      prefixIcon: const Icon(Icons.label_outline),
                    ),
                  ),
                  const SizedBox(height: 16),
                  TextField(
                    controller: _subtitle,
                    decoration: const InputDecoration(
                      labelText: 'Summary',
                      border: OutlineInputBorder(),
                      prefixIcon: Icon(Icons.notes),
                    ),
                  ),
                  if (widget.item?.primarySetting != null)
                    Padding(
                      padding: const EdgeInsets.only(top: 16),
                      child: TextFormField(
                        initialValue: widget.item!.primarySetting,
                        enabled: false,
                        decoration: const InputDecoration(
                          labelText: 'Source / primary',
                          border: OutlineInputBorder(),
                          prefixIcon: Icon(Icons.link),
                        ),
                      ),
                    ),
                  const SizedBox(height: 20),
                  Text('Settings',
                      style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 8),
                  // The SAME unified toggle renders in the form, on rows and
                  // on headers — §5.2.
                  for (final key in _draft.toggles.keys) ...[
                    UnifiedToggle(
                      value: _draft.toggles[key]!,
                      label: key,
                      helper: 'Toggle stored locally in this form.',
                      dangerous: key.toLowerCase().contains('public') ||
                          key.toLowerCase().contains('recording'),
                      onToggle: (next) async {
                        setState(() => _draft.toggles[key] = next);
                        return true;
                      },
                    ),
                    const SizedBox(height: 8),
                  ],
                ],
              ),
            ),
          ),
          // Sticky footer — same on every surface (mobile, tablet, desktop).
          Container(
            padding: EdgeInsets.all(isWide(context) ? 12 : 16),
            decoration: BoxDecoration(
              color: scheme.surface,
              border: Border(top: BorderSide(color: scheme.outlineVariant)),
            ),
            child: Row(
              children: [
                if (!_isNew)
                  TextButton.icon(
                    onPressed: _confirmDelete,
                    icon: const Icon(Icons.delete_outline),
                    label: const Text('Delete'),
                    style: TextButton.styleFrom(foregroundColor: scheme.error),
                  )
                else
                  const SizedBox(width: 96),
                const Spacer(),
                if (widget.onCancel != null)
                  TextButton(
                    onPressed: widget.onCancel,
                    child: const Text('Cancel'),
                  ),
                const SizedBox(width: 8),
                FilledButton.icon(
                  onPressed: _save,
                  icon: const Icon(Icons.check),
                  label: Text(_isNew ? 'Create' : 'Save'),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// Tablet surface: centered dialog wrapping the same editor body.
Future<MockItem?> showTabletEditor({
  required BuildContext context,
  required MockResource resource,
  MockItem? item,
}) {
  return showDialog<MockItem>(
    context: context,
    builder: (context) => AlertDialog(
      insetPadding: const EdgeInsets.all(32),
      contentPadding: EdgeInsets.zero,
      content: SizedBox(
        width: 540,
        height: 520,
        child: ResourceEditor(
          resource: resource,
          item: item,
          onSave: (saved) => Navigator.pop(context, saved),
          onCancel: () => Navigator.pop(context),
        ),
      ),
    ),
  );
}

/// Mobile surface: full-screen route with sticky footer.
Future<MockItem?> showFullScreenEditor({
  required BuildContext context,
  required MockResource resource,
  MockItem? item,
}) {
  return Navigator.of(context).push<MockItem>(
    MaterialPageRoute(
      fullscreenDialog: true,
      builder: (context) => Scaffold(
        appBar: AppBar(
          title: Text(item == null ? 'New ${resource.name}' : 'Edit'),
        ),
        body: ResourceEditor(
          resource: resource,
          item: item,
          onSave: (saved) => Navigator.pop(context, saved),
          onCancel: () => Navigator.pop(context),
        ),
      ),
    ),
  );
}