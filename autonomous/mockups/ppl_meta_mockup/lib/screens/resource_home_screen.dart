/// The unified resource home (plan §2, §3) shared by all four objects.
/// Demonstrates list/grid + search + filter + master/detail + the three
/// editor surfaces + the unified toggle. State is local & UI-only.
library;

import 'dart:async';

import 'package:flutter/material.dart';
import '../models/mock_data.dart';
import '../ux/breakpoints.dart';
import 'editor.dart';
import 'filter_panel.dart';
import 'item_views.dart';

enum _SimState { normal, loading, empty, error }

class ResourceHomeScreen extends StatefulWidget {
  const ResourceHomeScreen({super.key, required this.resource});
  final MockResource resource;

  @override
  State<ResourceHomeScreen> createState() => _ResourceHomeScreenState();
}

class _ResourceHomeScreenState extends State<ResourceHomeScreen> {
  final TextEditingController _search = TextEditingController();
  late bool _isGrid = widget.resource.defaultGrid;
  var _filter = const FilterSpec();
  _SimState _sim = _SimState.normal;
  bool _simulateFailure = false;

  /// Desktop master/detail + inline-editor state.
  String? _selectedId;
  MockItem? _editing; // inline editor working copy (existing item)
  bool _creatingInline = false; // inline editor is in create mode

  List<String> get _allTags => {
        for (final it in widget.resource.items) ...it.tags,
      }.toList()..sort();

  List<MockItem> get _visibleItems {
    final q = _search.text.trim().toLowerCase();
    final out = widget.resource.items.where((it) {
      if (q.isNotEmpty &&
          !it.name.toLowerCase().contains(q) &&
          !it.subtitle.toLowerCase().contains(q) &&
          !it.tags.any((t) => t.toLowerCase().contains(q))) {
        return false;
      }
      switch (_filter.enabled) {
        case EnabledFilter.onlyEnabled:
          if (!it.enabled) return false;
        case EnabledFilter.onlyDisabled:
          if (it.enabled) return false;
        case EnabledFilter.all:
          break;
      }
      if (_filter.tags.isNotEmpty && !_filter.tags.any(it.tags.contains)) {
        return false;
      }
      return true;
    }).toList();

    out.sort((a, b) {
      final cmp = _filter.sortBy == 'created'
          ? a.created.compareTo(b.created)
          : a.name.toLowerCase().compareTo(b.name.toLowerCase());
      return _filter.ascending ? cmp : -cmp;
    });
    return out;
  }

  /// Simulated optimistic commit with latency; optionally fails to demo revert.
  Future<bool> _commit() async {
    await Future<void>.delayed(const Duration(milliseconds: 700));
    return !_simulateFailure;
  }

  void _snack(String msg) {
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(SnackBar(content: Text(msg)));
  }

  // ---- CRUD ---------------------------------------------------------------

  Future<void> _openEditor({MockItem? item}) async {
    if (isWide(context)) {
      // Desktop: inline editor panel (surface from §5.1).
      setState(() {
        _creatingInline = item == null;
        _editing = item?.copy();
      });
      return;
    }
    final saved = isMobile(context)
        ? await showFullScreenEditor(
            context: context, resource: widget.resource, item: item)
        : await showTabletEditor(
            context: context, resource: widget.resource, item: item);
    if (saved == null || !mounted) return;
    _upsert(saved);
  }

  void _upsert(MockItem saved) {
    final i = widget.resource.items.indexWhere((it) => it.id == saved.id);
    setState(() {
      if (i >= 0) {
        widget.resource.items[i] = saved;
      } else {
        widget.resource.items.insert(0, saved);
      }
      _editing = null;
      _creatingInline = false;
      _selectedId = saved.id;
    });
    _snack('Saved "${saved.name}"');
  }

  void _requestDelete(MockItem item) async {
    final ok = await _confirmDelete(item.name);
    if (ok != true || !mounted) return;
    _deleteItem(item);
  }

  Future<bool?> _confirmDelete(String name) {
    return showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Confirm delete'),
        content: Text('"$name" will be removed. This cannot be undone.'),
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
  }

  // ---- Header / section toggles (optimistic via UnifiedToggle) ------------

  Future<bool> _toggleEnabled(MockItem item) async {
    final next = !item.enabled;
    final ok = await _commit();
    if (!mounted) return ok;
    setState(() => item.enabled = next);
    return ok;
  }

  Future<bool> _toggleSetting(MockItem item, String key) async {
    final next = !item.toggles[key]!;
    final ok = await _commit();
    if (!mounted) return ok;
    setState(() => item.toggles[key] = next);
    return ok;
  }

  MockItem? get _selectedItem {
    for (final it in widget.resource.items) {
      if (it.id == _selectedId) return it;
    }
    return widget.resource.items.isEmpty ? null : widget.resource.items.first;
  }

  void _deleteItem(MockItem item) {
    setState(() {
      widget.resource.items.removeWhere((it) => it.id == item.id);
      if (_selectedId == item.id) _selectedId = null;
      _editing = null;
      _creatingInline = false;
    });
    _snack('Deleted "${item.name}"');
  }

  Future<void> _refresh() async {
    setState(() => _sim = _SimState.loading);
    await Future<void>.delayed(const Duration(milliseconds: 900));
    if (!mounted) return;
    setState(() => _sim = _SimState.normal);
  }

  Future<void> _openFilter() async {
    final result = await showFilterPanel(
      context: context,
      allTags: _allTags,
      current: _filter,
      skipTags: widget.resource.items.isEmpty,
    );
    if (result != null && mounted) setState(() => _filter = result);
  }

  /// Mobile/tablet detail = a pushed route reusing ItemDetailView.
  void _openMobileDetail(MockItem item) {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (detailCtx) => Scaffold(
          appBar: AppBar(title: Text(item.name)),
          body: ItemDetailView(
            item: item,
            onEdit: () {
              Navigator.pop(detailCtx);
              _openEditor(item: item);
            },
            onToggleEnabled: (b) => _toggleEnabled(item),
            onToggleSetting: (k, b) => _toggleSetting(item, k),
            onDelete: () async {
              if (await _confirmDelete(item.name) == true) {
                // ignore: use_build_context_synchronously
                if (detailCtx.mounted) Navigator.pop(detailCtx);
                _deleteItem(item);
              }
            },
          ),
        ),
      ),
    );
  }

  void _selectOnDesktop(MockItem item) => setState(() {
        _selectedId = item.id;
        _editing = null;
        _creatingInline = false;
      });

  @override
  void dispose() {
    _search.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final wide = isWide(context);
    return Scaffold(
      backgroundColor: Theme.of(context).colorScheme.surface,
      appBar: AppBar(
        title: Text(widget.resource.name),
        actions: _appBarActions(wide),
      ),
      body: wide ? _buildDesktop() : _buildMobile(),
      floatingActionButton: wide
          ? null
          : FloatingActionButton.extended(
              onPressed: () => _openEditor(),
              icon: const Icon(Icons.add),
              label: const Text('New'),
            ),
    );
  }

  List<Widget> _appBarActions(bool wide) => [
        if (wide)
          Padding(
            padding: const EdgeInsets.only(right: 8),
            child: FilledButton.icon(
              onPressed: () => _openEditor(),
              icon: const Icon(Icons.add),
              label: Text('New ${widget.resource.name}'),
            ),
          ),
        IconButton(
          tooltip: _isGrid ? 'Switch to list' : 'Switch to grid',
          onPressed: () =>
              setState(() => _isGrid = !_isGrid),
          icon: Icon(_isGrid ? Icons.view_list : Icons.grid_view),
        ),
        IconButton(
          tooltip: 'Filter & sort',
          onPressed: _openFilter,
          icon: Badge(
            isLabelVisible: _filter.hasActiveFilters,
            child: const Icon(Icons.filter_list),
          ),
        ),
        IconButton(
          tooltip: 'Refresh',
          onPressed: _refresh,
          icon: const Icon(Icons.refresh),
        ),
        _simMenu(),
      ];

  Widget _simMenu() => PopupMenuButton<_SimState>(
        tooltip: 'Simulate L-E-R / failure (prototype only)',
        onSelected: (v) => setState(() => _sim = v),
        itemBuilder: (context) => [
          const PopupMenuItem(
            value: _SimState.normal,
            child: Text('State: Normal'),
          ),
          const PopupMenuItem(
            value: _SimState.loading,
            child: Text('State: Loading'),
          ),
          const PopupMenuItem(
            value: _SimState.empty,
            child: Text('State: Empty'),
          ),
          const PopupMenuItem(
            value: _SimState.error,
            child: Text('State: Error'),
          ),
          const PopupMenuDivider(),
          CheckedPopupMenuItem(
            value: _SimState.normal,
            checked: _simulateFailure,
            onTap: () => setState(() => _simulateFailure = !_simulateFailure),
            child: const Text('Simulate commit failure'),
          ),
        ],
      );

// ---- Body layouts --------------------------------------------------------

  Widget _buildMobile() => SafeArea(
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(12, 12, 12, 4),
              child: _searchBar(),
            ),
            _filterChips(),
            const SizedBox(height: 8),
            Expanded(
              child: Padding(
                padding: const EdgeInsets.only(bottom: 88),
                child: _listContent(),
              ),
            ),
          ],
        ),
      );

  Widget _buildDesktop() => Padding(
        padding: const EdgeInsets.fromLTRB(12, 12, 12, 12),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SizedBox(
              width: kMasterPaneWidth,
              child: Column(
                children: [
                  _searchBar(),
                  _filterChips(),
                  const SizedBox(height: 8),
                  Expanded(child: _listContent()),
                ],
              ),
            ),
            const SizedBox(width: 12),
            Expanded(child: _rightPane()),
          ],
        ),
      );

  Widget _searchBar() => TextField(
        controller: _search,
        onChanged: (_) => setState(() {}),
        decoration: InputDecoration(
          hintText: 'Search ${widget.resource.name.toLowerCase()}…',
          prefixIcon: const Icon(Icons.search),
          suffixIcon: _search.text.isEmpty
              ? null
              : IconButton(
                  onPressed: () => setState(_search.clear),
                  icon: const Icon(Icons.clear),
                  tooltip: 'Clear',
                ),
          border: const OutlineInputBorder(),
          isDense: true,
        ),
      );

  /// Dismissible chips for active filters + a helper hint otherwise.
  Widget _filterChips() {
    if (!_filter.hasActiveFilters && _search.text.trim().isEmpty) {
      return Padding(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
        child: Align(
          alignment: Alignment.centerLeft,
          child: Text(
            widget.resource.listHint,
            style: Theme.of(context).textTheme.bodySmall,
          ),
        ),
      );
    }
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
      child: Wrap(
        spacing: 6,
        runSpacing: 4,
        children: [
          if (_filter.enabled != EnabledFilter.all)
            Chip(
              label: Text(_filter.enabled == EnabledFilter.onlyEnabled
                  ? 'Enabled only'
                  : 'Disabled only'),
              onDeleted: () => setState(() {
                _filter = FilterSpec(
                  tags: _filter.tags,
                  sortBy: _filter.sortBy,
                  ascending: _filter.ascending,
                );
              }),
            ),
          for (final tag in _filter.tags)
            Chip(
              label: Text(tag),
              onDeleted: () => setState(() {
                final t = Set.of(_filter.tags)..remove(tag);
                _filter = FilterSpec(
                  enabled: _filter.enabled,
                  tags: t,
                  sortBy: _filter.sortBy,
                  ascending: _filter.ascending,
                );
              }),
            ),
          if (_filter.hasActiveFilters)
            TextButton(
              onPressed: () => setState(() => _filter = const FilterSpec()),
              child: const Text('Clear all'),
            ),
        ],
      ),
    );
  }
// ---- List / grid + L-E-R states ------------------------------------------

  Widget _listContent() {
    if (_sim == _SimState.loading) return _loadingState();
    if (_sim == _SimState.error) return _errorState();
    final items = _visibleItems;
    final emptyForced = _sim == _SimState.empty;
    if (emptyForced || items.isEmpty) {
      return _emptyState(forced: emptyForced);
    }
    return _isGrid ? _grid(items) : _list(items);
  }

  Widget _grid(List<MockItem> items) => LayoutBuilder(
        builder: (context, constraints) {
          final cols = constraints.maxWidth < 340
              ? 1
              : (constraints.maxWidth < 700 ? 2 : 3);
          return GridView.builder(
            padding: const EdgeInsets.all(8),
            gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: cols,
              childAspectRatio: 0.8,
              crossAxisSpacing: 6,
              mainAxisSpacing: 6,
            ),
            itemCount: items.length,
            itemBuilder: (context, i) {
              final it = items[i];
              return ItemCard(
                item: it,
                resource: widget.resource,
                isGrid: true,
                selected: isWide(context) && _selectedId == it.id,
                onTap: () =>
                    isWide(context) ? _selectOnDesktop(it) : _openMobileDetail(it),
                onToggleEnabled: (_) => _toggleEnabled(it),
                onEdit: () => _openEditor(item: it),
                onDelete: () => _requestDelete(it),
                onSettings: () => _openEditor(item: it),
              );
            },
          );
        },
      );

  Widget _list(List<MockItem> items) => ListView.builder(
        padding: const EdgeInsets.symmetric(vertical: 4),
        itemCount: items.length,
        itemBuilder: (context, i) {
          final it = items[i];
          return ItemCard(
            item: it,
            resource: widget.resource,
            isGrid: false,
            selected: isWide(context) && _selectedId == it.id,
            onTap: () =>
                isWide(context) ? _selectOnDesktop(it) : _openMobileDetail(it),
            onToggleEnabled: (_) => _toggleEnabled(it),
            onEdit: () => _openEditor(item: it),
            onDelete: () => _requestDelete(it),
            onSettings: () => _openEditor(item: it),
          );
        },
      );

  Widget _loadingState() => ListView(
        padding: const EdgeInsets.all(12),
        children: [
          for (var i = 0; i < 6; i++)
            Container(
              height: 84,
              margin: const EdgeInsets.only(bottom: 8),
              decoration: BoxDecoration(
                color: Theme.of(context).colorScheme.surfaceContainerHighest,
                borderRadius: BorderRadius.circular(12),
              ),
            ),
        ],
      );

  Widget _emptyState({required bool forced}) {
    final hasFilters = _filter.hasActiveFilters || _search.text.trim().isNotEmpty;
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.inbox_outlined,
              size: 56,
              color: Theme.of(context).colorScheme.outline,
            ),
            const SizedBox(height: 12),
            Text(
              forced
                  ? 'Nothing here'
                  : hasFilters
                      ? 'No items match your filters'
                      : widget.resource.emptyText,
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 16),
            if (forced)
              Text(
                'This is the unified Empty state (plan §3). Create action is the primary call-to-action.',
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodySmall,
              )
            else if (hasFilters)
              TextButton(
                onPressed: () => setState(() {
                  _filter = const FilterSpec();
                  _search.clear();
                }),
                child: const Text('Clear filters'),
              )
            else
              FilledButton.icon(
                onPressed: () => _openEditor(),
                icon: const Icon(Icons.add),
                label: const Text('Create'),
              ),
          ],
        ),
      ),
    );
  }

  Widget _errorState() => Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                Icons.error_outline,
                size: 56,
                color: Theme.of(context).colorScheme.error,
              ),
              const SizedBox(height: 12),
              const Text('Something went wrong loading this resource.'),
              const SizedBox(height: 16),
              FilledButton.icon(
                onPressed: _refresh,
                icon: const Icon(Icons.refresh),
                label: const Text('Retry'),
              ),
            ],
          ),
        ),
      );
// ---- Desktop detail / inline editor pane --------------------------------

  Widget _rightPane() {
    if (_creatingInline || _editing != null) return _inlineEditorPane();
    final item = _selectedItem;
    if (item == null) return _rightPlaceholder();
    // Content-first: the right side shows the ACTIVE item's content, not its
    // settings. Tapping the settings icon opens the settings editor here.
    return _contentPane(item);
  }

  /// Top bar for a content pane: the item name + a visible Settings icon
  /// that opens the settings editor (on desktop: inline on the right).
  Widget _contentBar(MockItem item) {
    final scheme = Theme.of(context).colorScheme;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      color: scheme.surfaceContainerHighest,
      child: Row(
        children: [
          Expanded(
            child: Text(item.name,
                style: Theme.of(context).textTheme.titleMedium,
                maxLines: 1,
                overflow: TextOverflow.ellipsis),
          ),
          IconButton(
            tooltip: 'Settings',
            onPressed: () => _openEditor(item: item),
            icon: const Icon(Icons.settings_outlined),
            color: scheme.primary,
          ),
        ],
      ),
    );
  }

  Widget _contentPane(MockItem item) {
    // Triggers/actions have no media — the right side stays settings-only.
    if (widget.resource.id == 'triggers') {
      return _settingsOnlyRightPane(item);
    }
    final content = switch (widget.resource.id) {
      'cameras' => _camerasContent(item),
      'collections' => _collectionsContent(item),
      'groups' => _membersContent(item),
      _ => ItemDetailView(
          item: item,
          onEdit: () => _openEditor(item: item),
          onToggleEnabled: (_) => _toggleEnabled(item),
          onToggleSetting: (k, b) => _toggleSetting(item, k),
          onDelete: () => _requestDelete(item),
        ),
    };
    return Padding(
      padding: const EdgeInsets.only(left: 4, bottom: 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _contentBar(item),
          const SizedBox(height: 8),
          Expanded(child: content),
        ],
      ),
    );
  }

  /// For resources whose right pane is the settings/detail itself
  /// (Triggers & Actions) — "stays as it is at the demo".
  Widget _settingsOnlyRightPane(MockItem item) {
    return Padding(
      padding: const EdgeInsets.only(left: 4, bottom: 8),
      child: ItemDetailView(
        item: item,
        onEdit: () => _openEditor(item: item),
        onToggleEnabled: (_) => _toggleEnabled(item),
        onToggleSetting: (k, b) => _toggleSetting(item, k),
        onDelete: () => _requestDelete(item),
      ),
    );
  }

  Widget _inlineEditorPane() {
    final scheme = Theme.of(context).colorScheme;
    return Card(
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(color: scheme.outlineVariant),
      ),
      clipBehavior: Clip.antiAlias,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
            color: scheme.surfaceContainerHighest,
            child: Row(
              children: [
                Text(
                  _creatingInline
                      ? 'New ${widget.resource.name}'
                      : 'Edit ${_editing!.name}',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const Spacer(),
                IconButton(
                  tooltip: 'Close editor',
                  onPressed: () => setState(() {
                    _editing = null;
                    _creatingInline = false;
                  }),
                  icon: const Icon(Icons.close),
                ),
              ],
            ),
          ),
          Expanded(
            child: ResourceEditor(
              resource: widget.resource,
              item: _editing,
              createMode: _creatingInline,
              onSave: _upsert,
              onCancel: () => setState(() {
                _editing = null;
                _creatingInline = false;
              }),
              onDelete:
                  _editing == null ? null : (item) => _requestDelete(item),
            ),
          ),
        ],
      ),
    );
  }

  Widget _rightPlaceholder() => Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                widget.resource.icon,
                size: 56,
                color: Theme.of(context).colorScheme.outline,
              ),
              const SizedBox(height: 12),
              Text(
                widget.resource.listHint,
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodyMedium,
              ),
            ],
          ),
        ),
      );

  Widget _camerasContent(MockItem item) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
        color: const Color(0xFF0B1418),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.all(12),
            child: Row(
              children: [
                const Icon(Icons.radio_button_checked, color: Colors.redAccent, size: 14),
                const SizedBox(width: 6),
                const Text('LIVE',
                    style: TextStyle(color: Colors.redAccent, fontSize: 12, fontWeight: FontWeight.w700, letterSpacing: 1.2)),
                const Spacer(),
                Text(item.subtitle,
                    style: const TextStyle(color: Colors.white70, fontSize: 12)),
              ],
            ),
          ),
          Expanded(
            child: Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.videocam, size: 72, color: Colors.white.withValues(alpha: 0.35)),
                  const SizedBox(height: 8),
                  const Text('Camera preview', style: TextStyle(color: Colors.white54)),
                ],
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(12),
            child: Wrap(
              spacing: 8,
              runSpacing: 6,
              children: [
                _previewTag('2 people detected'),
                _previewTag('Motion'),
                _previewTag(item.primarySetting ?? 'RTSP'),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _previewTag(String label) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
        decoration: BoxDecoration(
          color: Colors.white.withValues(alpha: 0.08),
          borderRadius: BorderRadius.circular(999),
        ),
        child: Text(label, style: const TextStyle(color: Colors.white70, fontSize: 12)),
      );

  Widget _collectionsContent(MockItem item) {
    final scheme = Theme.of(context).colorScheme;
    final dark = Theme.of(context).brightness == Brightness.dark;
    final onTile = dark ? Colors.white : Colors.black;
    final palette = [
      scheme.primaryContainer,
      scheme.tertiaryContainer,
      scheme.secondaryContainer,
      const Color(0xFF43B5A0),
      const Color(0xFF7A6FD0),
    ];
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 4),
          child: Text(item.subtitle, style: Theme.of(context).textTheme.bodySmall),
        ),
        const SizedBox(height: 4),
        Expanded(
          child: GridView.builder(
            padding: const EdgeInsets.all(4),
            gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: 3,
              crossAxisSpacing: 6,
              mainAxisSpacing: 6,
              childAspectRatio: 1.1,
            ),
            itemCount: 12,
            itemBuilder: (context, i) => Container(
              decoration: BoxDecoration(
                color: palette[i % palette.length],
                borderRadius: BorderRadius.circular(8),
              ),
              child: Center(
                child: Icon(
                  i.isEven ? Icons.play_circle_outline : Icons.movie_outlined,
                  color: onTile.withValues(alpha: 0.6),
                ),
              ),
            ),
          ),
        ),
      ],
    );
  }

  Widget _membersContent(MockItem item) {
    final scheme = Theme.of(context).colorScheme;
    final dark = Theme.of(context).brightness == Brightness.dark;
    final onTile = dark ? Colors.white : Colors.black87;
    final faint = onTile.withValues(alpha: 0.7);
    // Mirrors the Collections video cards: tinted rounded tiles in a grid.
    final palette = [
      scheme.primaryContainer,
      scheme.tertiaryContainer,
      scheme.secondaryContainer,
      const Color(0xFF43B5A0),
      const Color(0xFF7A6FD0),
    ];
    final initials = item.name
        .split(' ')
        .where((w) => w.isNotEmpty)
        .take(2)
        .map((w) => w[0].toUpperCase())
        .join();
    final raw = int.tryParse(item.primarySetting?.split(' ').first ?? '12');
    final count = (raw ?? 12).clamp(1, 20).toInt();
    final names = ['Alex Morgan', 'Jordan Lee', 'Sam Patel', 'Riley Quinn', 'Taylor Kim', 'Casey Wu'];
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 4),
          child: Row(
            children: [
              Expanded(
                  child: Text(item.subtitle,
                      style: Theme.of(context).textTheme.bodySmall)),
              ActionChip(
                avatar: const Icon(Icons.person_add_alt, size: 18),
                label: const Text('Add member'),
                visualDensity: VisualDensity.compact,
                onPressed: () => _snack('Add member (mock)'),
              ),
            ],
          ),
        ),
        const SizedBox(height: 4),
        Expanded(
          child: GridView.builder(
            padding: const EdgeInsets.all(4),
            gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: 3,
              crossAxisSpacing: 6,
              mainAxisSpacing: 6,
              childAspectRatio: 1.0,
            ),
            itemCount: count,
            itemBuilder: (context, i) {
              final color = palette[i % palette.length];
              return Container(
                decoration: BoxDecoration(
                  color: color,
                  borderRadius: BorderRadius.circular(10),
                ),
                padding: const EdgeInsets.all(8),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    // Stand-in for the member's avatar/photo.
                    CircleAvatar(
                      radius: 24,
                      backgroundColor: Colors.black.withValues(alpha: 0.18),
                      foregroundColor: Colors.white,
                      child: Text(
                        '$initials${i + 1}',
                        style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600),
                      ),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      i < names.length ? names[i] : 'Member ${i + 1}',
                      style: Theme.of(context)
                          .textTheme
                          .titleSmall
                          ?.copyWith(color: onTile),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 2),
                    Text(
                      'Seen today',
                      style: Theme.of(context)
                          .textTheme
                          .labelSmall
                          ?.copyWith(color: faint),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                ),
              );
            },
          ),
        ),
      ],
    );
  }
}