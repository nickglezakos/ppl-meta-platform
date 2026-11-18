/// People & Groups screen — Individual Groups | People tabs.
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/theme/theme_kit.dart';
import '../widgets/custom_app_bar.dart';
import '../widgets/individual_groups/individual_groups_tab.dart';
import '../widgets/individual_groups/people_profiles_tab.dart';

class IndividualGroupsScreen extends ConsumerStatefulWidget {
  /// `groups` (default) or `people`.
  final String? initialTab;

  /// When opening the People tab, optionally select this profile.
  final String? initialPppUuid;

  const IndividualGroupsScreen({
    super.key,
    this.initialTab,
    this.initialPppUuid,
  });

  @override
  ConsumerState<IndividualGroupsScreen> createState() =>
      _IndividualGroupsScreenState();
}

class _IndividualGroupsScreenState extends ConsumerState<IndividualGroupsScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  final GlobalKey<IndividualGroupsTabState> _groupsTabKey =
      GlobalKey<IndividualGroupsTabState>();
  final GlobalKey<PeopleProfilesTabState> _peopleTabKey =
      GlobalKey<PeopleProfilesTabState>();
  bool _showArchived = false;

  static int _tabIndexFor(String? tab) {
    final normalized = (tab ?? 'groups').trim().toLowerCase();
    if (normalized == 'people' || normalized == 'person') return 1;
    return 0;
  }

  @override
  void initState() {
    super.initState();
    _tabController = TabController(
      length: 2,
      vsync: this,
      initialIndex: _tabIndexFor(widget.initialTab),
    );
    _tabController.addListener(() {
      if (!_tabController.indexIsChanging) {
        setState(() {});
      }
    });
  }

  @override
  void didUpdateWidget(covariant IndividualGroupsScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    final nextIndex = _tabIndexFor(widget.initialTab);
    if (widget.initialTab != oldWidget.initialTab &&
        _tabController.index != nextIndex) {
      _tabController.animateTo(nextIndex);
    }
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  void _toggleShowArchived() {
    setState(() => _showArchived = !_showArchived);
  }

  @override
  Widget build(BuildContext context) {
    final onGroupsTab = _tabController.index == 0;
    return Scaffold(
      appBar: CustomAppBar(
        title: 'People & Groups',
        showBackButton: true,
        showHomeButton: true,
        actions: [
          FilterChip(
            label: const Text('Show archived'),
            selected: _showArchived,
            onSelected: (_) => _toggleShowArchived(),
            avatar: Icon(
              _showArchived ? Icons.archive : Icons.archive_outlined,
              size: 18,
            ),
            visualDensity: VisualDensity.compact,
            materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
          ),
          if (onGroupsTab) ...[
            const SizedBox(width: 8),
            IconButton(
              onPressed: () =>
                  _groupsTabKey.currentState?.showCreateGroupDialog(),
              icon: const Icon(Icons.add, color: AppColors.secondary),
              tooltip: 'New Group',
            ),
          ],
        ],
        bottom: AppTabTheme.tabBar(
          controller: _tabController,
          tabs: const [
            Tab(
              icon: Icon(AppIcons.groups),
              text: 'Individual Groups',
            ),
            Tab(
              icon: Icon(Icons.person_outline),
              text: 'People',
            ),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tabController,
        children: [
          IndividualGroupsTab(
            key: _groupsTabKey,
            showArchived: _showArchived,
          ),
          PeopleProfilesTab(
            key: _peopleTabKey,
            initialPppUuid: widget.initialPppUuid,
            showArchived: _showArchived,
          ),
        ],
      ),
    );
  }
}
