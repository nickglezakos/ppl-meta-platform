/// Shared search/filter/sort panel (plan §5.3).
/// Renders as a bottom sheet on mobile/tablet and as a popover on desktop,
/// using the same body either way.
library;

import 'package:flutter/material.dart';
import '../ux/breakpoints.dart';

enum EnabledFilter { all, onlyEnabled, onlyDisabled }

class FilterSpec {
  const FilterSpec({
    this.enabled = EnabledFilter.all,
    this.tags = const {},
    this.sortBy = 'name',
    this.ascending = true,
  });

  final EnabledFilter enabled;
  final Set<String> tags;
  final String sortBy;
  final bool ascending;

  bool get hasActiveFilters =>
      enabled != EnabledFilter.all ||
      tags.isNotEmpty ||
      sortBy != 'name' ||
      !ascending;
}

Future<FilterSpec?> showFilterPanel({
  required BuildContext context,
  required List<String> allTags,
  required FilterSpec current,
  required bool skipTags,
}) {
  return showModalBottomSheet<FilterSpec>(
    context: context,
    isScrollControlled: true,
    shape: const RoundedRectangleBorder(
      borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
    ),
    builder: (context) => Padding(
      padding: EdgeInsets.only(
        bottom: MediaQuery.of(context).viewInsets.bottom,
      ),
      child: _FilterPanelBody(
        allTags: allTags,
        current: current,
        skipTags: skipTags,
      ),
    ),
  );
}

class _FilterPanelBody extends StatefulWidget {
  const _FilterPanelBody({
    required this.allTags,
    required this.current,
    required this.skipTags,
  });

  final List<String> allTags;
  final FilterSpec current;
  final bool skipTags;

  @override
  State<_FilterPanelBody> createState() => _FilterPanelBodyState();
}

class _FilterPanelBodyState extends State<_FilterPanelBody> {
  late EnabledFilter _enabled = widget.current.enabled;
  late final Set<String> _tags = Set.of(widget.current.tags);
  late String _sortBy = widget.current.sortBy;
  late bool _ascending = widget.current.ascending;

  void _apply() {
    Navigator.pop(
      context,
      FilterSpec(
        enabled: _enabled,
        tags: _tags,
        sortBy: _sortBy,
        ascending: _ascending,
      ),
    );
  }
@override
  Widget build(BuildContext context) {
    final narrow = isMobile(context);

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
      child: SingleChildScrollView(
        child: ConstrainedBox(
          constraints: BoxConstraints(
            maxWidth: narrow ? double.infinity : 420,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Text('Filter & sort',
                      style: Theme.of(context).textTheme.titleMedium),
                  const Spacer(),
                  IconButton(
                    onPressed: () => Navigator.pop(context),
                    icon: const Icon(Icons.close),
                    tooltip: 'Close',
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Text('Show', style: Theme.of(context).textTheme.titleSmall),
              RadioGroup<EnabledFilter>(
                groupValue: _enabled,
                onChanged: (v) =>
                    setState(() => _enabled = v ?? EnabledFilter.all),
                child: const Column(
                  children: [
                    RadioListTile(
                      value: EnabledFilter.all,
                      title: Text('All'),
                      dense: true,
                      contentPadding: EdgeInsets.zero,
                    ),
                    RadioListTile(
                      value: EnabledFilter.onlyEnabled,
                      title: Text('Enabled only'),
                      dense: true,
                      contentPadding: EdgeInsets.zero,
                    ),
                    RadioListTile(
                      value: EnabledFilter.onlyDisabled,
                      title: Text('Disabled only'),
                      dense: true,
                      contentPadding: EdgeInsets.zero,
                    ),
                  ],
                ),
              ),
              if (!widget.skipTags && widget.allTags.isNotEmpty) ...[
                const SizedBox(height: 12),
                Text('Tags', style: Theme.of(context).textTheme.titleSmall),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  runSpacing: 4,
                  children: [
                    for (final tag in widget.allTags)
                      FilterChip(
                        label: Text(tag),
                        selected: _tags.contains(tag),
                        onSelected: (sel) => setState(() {
                          if (sel) {
                            _tags.add(tag);
                          } else {
                            _tags.remove(tag);
                          }
                        }),
                      ),
                  ],
                ),
              ],
              const SizedBox(height: 12),
              Row(
                children: [
                  DropdownButton<String>(
                    value: _sortBy,
                    onChanged: (v) => setState(() => _sortBy = v ?? 'name'),
                    items: const [
                      DropdownMenuItem(value: 'name', child: Text('Sort by name')),
                      DropdownMenuItem(value: 'created', child: Text('Sort by created')),
                    ],
                  ),
                  const Spacer(),
                  IconButton(
                    tooltip: _ascending ? 'Ascending' : 'Descending',
                    onPressed: () => setState(() => _ascending = !_ascending),
                    icon: Icon(_ascending ? Icons.arrow_upward : Icons.arrow_downward),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  TextButton(
                    onPressed: () => Navigator.pop(context, const FilterSpec()),
                    child: const Text('Reset'),
                  ),
                  const SizedBox(width: 8),
                  FilledButton(onPressed: _apply, child: const Text('Apply')),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}