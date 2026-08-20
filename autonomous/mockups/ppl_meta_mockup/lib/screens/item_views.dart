/// Reusable list/grid cards and the detail view (plan §3, §4).
library;

import 'package:flutter/material.dart';
import '../models/mock_data.dart';
import '../ux/unified_toggle.dart';

Color _statusColor(BuildContext context, bool on) =>
    on ? Theme.of(context).colorScheme.primary : Theme.of(context).colorScheme.outline;

class StatusChip extends StatelessWidget {
  const StatusChip({super.key, required this.on});
  final bool on;

  @override
  Widget build(BuildContext context) {
    final c = _statusColor(context, on);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: c.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: c.withValues(alpha: 0.4)),
      ),
      child: Text(
        on ? 'Enabled' : 'Disabled',
        style: Theme.of(context)
            .textTheme
            .labelSmall
            ?.copyWith(color: c, fontWeight: FontWeight.w600),
      ),
    );
  }
}

class ItemCard extends StatelessWidget {
  const ItemCard({
    super.key,
    required this.item,
    required this.resource,
    required this.isGrid,
    required this.selected,
    required this.onTap,
    required this.onToggleEnabled,
    required this.onEdit,
    required this.onDelete,
    this.onSettings,
  });

  final MockItem item;
  final MockResource resource;
  final bool isGrid;
  final bool selected;
  final VoidCallback onTap;
  final Future<bool> Function(bool) onToggleEnabled;
  final VoidCallback onEdit;
  final VoidCallback onDelete;
  final VoidCallback? onSettings;

  PopupMenuButton<String> _menu(BuildContext context) {
    final entries = <PopupMenuEntry<String>>[
      if (onSettings != null)
        const PopupMenuItem(value: 'settings', child: Text('Settings')),
      const PopupMenuItem(value: 'edit', child: Text('Edit')),
      const PopupMenuItem(value: 'delete', child: Text('Delete')),
    ];
    return PopupMenuButton<String>(
      tooltip: 'Item actions',
      onSelected: (v) {
        switch (v) {
          case 'settings':
            onSettings?.call();
          case 'edit':
            onEdit();
          case 'delete':
            onDelete();
        }
      },
      itemBuilder: (context) => entries,
    );
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;

    if (!isGrid) {
      return Card(
        margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: BorderSide(
            color: selected
                ? scheme.primary
                : scheme.outlineVariant,
            width: selected ? 2 : 1,
          ),
        ),
        child: ListTile(
          leading: CircleAvatar(backgroundColor: scheme.surfaceContainerHighest, child: Icon(item.icon)),
          title: Text(item.name, maxLines: 1, overflow: TextOverflow.ellipsis),
          subtitle: Text(item.subtitle, maxLines: 1, overflow: TextOverflow.ellipsis),
          isThreeLine: false,
          trailing: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              UnifiedToggle(
                value: item.enabled,
                showLabel: false,
                helper: 'Enable/disable',
                dangerous: true,
                confirmBody: 'Changing ${item.name} status may affect running workflows.',
                onToggle: onToggleEnabled,
              ),
              _menu(context),
            ],
          ),
          onTap: onTap,
        ),
      );
    }

    return Card(
      margin: const EdgeInsets.all(8),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: BorderSide(
          color: selected ? scheme.primary : scheme.outlineVariant,
          width: selected ? 2 : 1,
        ),
      ),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Row(
                children: [
                  CircleAvatar(radius: 22, backgroundColor: scheme.surfaceContainerHighest, child: Icon(item.icon)),
                  const Spacer(),
                  _menu(context),
                ],
              ),
              const SizedBox(height: 8),
              Text(item.name,
                  style: Theme.of(context).textTheme.titleMedium,
                  maxLines: 2, overflow: TextOverflow.ellipsis),
              const SizedBox(height: 2),
              Text(item.subtitle,
                  style: Theme.of(context).textTheme.bodySmall,
                  maxLines: 2, overflow: TextOverflow.ellipsis),
              const Spacer(),
              const SizedBox(height: 8),
              Row(
                children: [
                  StatusChip(on: item.enabled),
                  const Spacer(),
                  UnifiedToggle(
                    value: item.enabled,
                    showLabel: false,
                    dangerous: true,
                    onToggle: onToggleEnabled,
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class ItemDetailView extends StatelessWidget {
  const ItemDetailView({
    super.key,
    required this.item,
    required this.onEdit,
    required this.onToggleEnabled,
    required this.onToggleSetting,
    required this.onDelete,
  });

  final MockItem item;
  final VoidCallback onEdit;
  final Future<bool> Function(bool) onToggleEnabled;
  final Future<bool> Function(String key, bool next) onToggleSetting;
  final VoidCallback onDelete;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        // Header (identical anatomy on all four screens — plan §4)
        Row(
          children: [
            CircleAvatar(radius: 32, backgroundColor: scheme.surfaceContainerHighest, child: Icon(item.icon, size: 32)),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(item.name, style: Theme.of(context).textTheme.titleLarge),
                  Text(item.subtitle, style: Theme.of(context).textTheme.bodyMedium),
                  const SizedBox(height: 4),
                  Text('Created ${item.created}', style: Theme.of(context).textTheme.bodySmall),
                ],
              ),
            ),
          ],
        ),
        const SizedBox(height: 16),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            StatusChip(on: item.enabled),
            for (final tag in item.tags) Chip(label: Text(tag), visualDensity: VisualDensity.compact),
          ],
        ),
        if (item.primarySetting != null)
          Padding(
            padding: const EdgeInsets.only(top: 12),
            child: TextFormField(
              initialValue: item.primarySetting,
              enabled: false,
              decoration: const InputDecoration(
                labelText: 'Source / primary',
                border: OutlineInputBorder(),
                prefixIcon: Icon(Icons.link),
              ),
            ),
          ),
        const SizedBox(height: 8),
        // Persistent primary actions (Edit + header toggle + Delete)
        Row(
          children: [
            FilledButton.icon(onPressed: onEdit, icon: const Icon(Icons.edit_outlined), label: const Text('Edit')),
            const SizedBox(width: 12),
            const Spacer(),
            UnifiedToggle(
              value: item.enabled,
              showLabel: false,
              helper: 'Active',
              onToggle: onToggleEnabled,
            ),
          ],
        ),
        const Divider(height: 32),
        Text('Settings', style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: 8),
        for (final key in item.toggles.keys)
          UnifiedToggle(
            value: item.toggles[key]!,
            label: key,
            helper: 'Commits immediately (optimistic + revert shown).',
            onToggle: (next) => onToggleSetting(key, next),
          ),
        const Divider(height: 40),
        Align(
          alignment: Alignment.centerLeft,
          child: TextButton.icon(
            onPressed: onDelete,
            icon: const Icon(Icons.delete_outline),
            label: const Text('Delete this item'),
            style: TextButton.styleFrom(foregroundColor: scheme.error),
          ),
        ),
      ],
    );
  }
}