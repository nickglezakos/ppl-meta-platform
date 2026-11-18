/// People tab — master list of people profiles + linked MVR members pane.
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api_client.dart';
import '../../core/theme/theme_kit.dart';
import '../../models/cross_video_analysis_models.dart';
import '../../models/individual_group_models.dart';
import '../../models/mvr_best_image.dart';
import '../../models/presence_models.dart';
import '../../presentation/widgets/common/content_pane.dart';
import '../../presentation/widgets/common/ux_breakpoints.dart';
import '../../providers/mvr_image_service_provider.dart';
import '../../screens/person_objects_detail_screen.dart';
import '../../services/individual_groups_api_client.dart';
import '../../services/mvr_api_client.dart';
import '../../services/presence_api_client.dart';
import 'individual_groups_tab.dart';

class PeopleProfilesTab extends ConsumerStatefulWidget {
  final String? initialPppUuid;
  final bool showArchived;

  const PeopleProfilesTab({
    super.key,
    this.initialPppUuid,
    this.showArchived = false,
  });

  @override
  ConsumerState<PeopleProfilesTab> createState() => PeopleProfilesTabState();
}

class PeopleProfilesTabState extends ConsumerState<PeopleProfilesTab> {
  List<PresencePeopleProfile> _profiles = [];
  bool _isLoading = true;
  String? _errorMessage;
  final TextEditingController _searchController = TextEditingController();
  String _searchQuery = '';
  String? _selectedPppUuid;

  PresencePeopleProfile? _selectedDetail;
  List<LinkedMemberView> _linkedMembers = [];
  bool _loadingMembers = false;
  String? _membersError;

  final Map<String, List<IndividualSummary>> _membersByGroupCache = {};
  final Map<String, String> _groupNameCache = {};
  final Set<String> _knownGroupIds = {};
  bool _groupListWarmed = false;

  PresencePeopleProfile? get _selectedProfile {
    if (_profiles.isEmpty) return null;
    for (final p in _profiles) {
      if (p.pppUuid == _selectedPppUuid) return p;
    }
    return _profiles.first;
  }

  @override
  void initState() {
    super.initState();
    _selectedPppUuid = widget.initialPppUuid;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _loadProfiles();
    });
  }

  @override
  void didUpdateWidget(covariant PeopleProfilesTab oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.initialPppUuid != null &&
        widget.initialPppUuid != oldWidget.initialPppUuid) {
      _selectedPppUuid = widget.initialPppUuid;
      if (_profiles.isNotEmpty) {
        _onSelectProfile(_selectedPppUuid!);
      }
    }
    if (widget.showArchived != oldWidget.showArchived) {
      _membersByGroupCache.clear();
      final selected = _selectedPppUuid;
      if (selected != null) {
        _loadLinkedMembers(selected);
      }
    }
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  PresenceApiClient get _presenceApi =>
      PresenceApiClient(ref.read(apiClientProvider));

  IndividualGroupsApiClient get _groupsApi =>
      IndividualGroupsApiClient(ref.read(apiClientProvider));

  /// Collapse dirty duplicate PPP rows (same display name). Prefer the profile
  /// that has an email, then the one with more linked members.
  static List<PresencePeopleProfile> _dedupeProfiles(
    List<PresencePeopleProfile> profiles,
  ) {
    final byName = <String, PresencePeopleProfile>{};
    for (final profile in profiles) {
      final key = profile.name.trim().toLowerCase();
      if (key.isEmpty) {
        byName.putIfAbsent(profile.pppUuid, () => profile);
        continue;
      }
      final existing = byName[key];
      if (existing == null) {
        byName[key] = profile;
        continue;
      }
      final existingEmail =
          existing.email != null && existing.email!.trim().isNotEmpty;
      final nextEmail =
          profile.email != null && profile.email!.trim().isNotEmpty;
      if (nextEmail && !existingEmail) {
        byName[key] = profile;
      } else if (nextEmail == existingEmail &&
          profile.linkedMemberCount > existing.linkedMemberCount) {
        byName[key] = profile;
      }
    }
    return byName.values.toList();
  }

  Future<void> _loadProfiles({bool showSpinner = true}) async {
    if (showSpinner || _profiles.isEmpty) {
      setState(() {
        _isLoading = true;
        _errorMessage = null;
      });
    } else {
      setState(() => _errorMessage = null);
    }

    final response = await _presenceApi.listPeopleProfiles(
      query: _searchQuery.isEmpty ? null : _searchQuery,
      limit: 100,
    );

    if (!mounted) return;

    if (response.success && response.data != null) {
      final profiles = _dedupeProfiles(response.data!);
      setState(() {
        _profiles = profiles;
        _isLoading = false;
        if (_selectedPppUuid == null && profiles.isNotEmpty) {
          _selectedPppUuid = profiles.first.pppUuid;
        } else if (_selectedPppUuid != null &&
            profiles.every((p) => p.pppUuid != _selectedPppUuid) &&
            profiles.isNotEmpty) {
          // Selected profile was a hidden duplicate — switch to survivor.
          _selectedPppUuid = profiles.first.pppUuid;
        }
      });
      final selected = _selectedPppUuid;
      if (selected != null) {
        await _loadLinkedMembers(selected);
      }
    } else {
      setState(() {
        _errorMessage = response.error;
        _isLoading = false;
      });
    }
  }

  Future<void> _onSelectProfile(String pppUuid) async {
    setState(() => _selectedPppUuid = pppUuid);
    await _loadLinkedMembers(pppUuid);
  }

  String _shortGroupLabel(String groupId) {
    if (groupId.length <= 12) return groupId;
    return '${groupId.substring(0, 10)}…';
  }

  /// Ensure [IndividualSummary.mvrPersonUuid] is set so Groups-tab image
  /// loading (keyed by mvrPersonUuid) works for presence-linked members.
  static IndividualSummary _memberWithMvrUuid(
    IndividualSummary? match,
    String mvrUuid,
  ) {
    if (match != null && match.mvrPersonUuid == mvrUuid) return match;
    if (match != null) {
      return IndividualSummary(
        id: match.id,
        mvrPersonUuid: mvrUuid,
        groupMemberNumber: match.groupMemberNumber,
        thumbnailUrl: match.thumbnailUrl,
        totalAppearances: match.totalAppearances,
        lastSeen: match.lastSeen,
        groupCount: match.groupCount,
        confidenceScore: match.confidenceScore,
        addedBy: match.addedBy,
        canManageMember: match.canManageMember,
        isArchived: match.isArchived,
        name: match.name,
        nameUpdatedAt: match.nameUpdatedAt,
        nameUpdatedBy: match.nameUpdatedBy,
      );
    }
    return IndividualSummary(
      id: mvrUuid,
      mvrPersonUuid: mvrUuid,
      name: 'Linked member',
      totalAppearances: 0,
      groupCount: 0,
      confidenceScore: 0,
      canManageMember: false,
      isArchived: false,
    );
  }

  /// Warm group id→name from listGroups so we never hit getGroup(404) for
  /// stale presence links that point at deleted groups.
  Future<void> _warmGroupListCache() async {
    if (_groupListWarmed) return;
    final resp = await _groupsApi.listGroups(limit: 200);
    if (resp.success && resp.data != null) {
      for (final g in resp.data!.groups) {
        _knownGroupIds.add(g.id);
        _groupNameCache[g.id] = g.name;
      }
    }
    _groupListWarmed = true;
  }

  Future<void> _ensureGroupMemberCache(String groupId) async {
    if (_membersByGroupCache.containsKey(groupId)) return;

    // Unknown / deleted group: do not call members or getGroup (avoids 404 noise).
    if (_groupListWarmed && !_knownGroupIds.contains(groupId)) {
      _membersByGroupCache[groupId] = [];
      _groupNameCache.putIfAbsent(groupId, () => 'Unavailable group');
      return;
    }

    final membersResp = await _groupsApi.getGroupMembers(
      groupId,
      limit: 200,
      includeArchived: widget.showArchived,
    );
    if (membersResp.success && membersResp.data != null) {
      _membersByGroupCache[groupId] = membersResp.data!.members;
      _knownGroupIds.add(groupId);
      _groupNameCache.putIfAbsent(groupId, () => _shortGroupLabel(groupId));
    } else {
      _membersByGroupCache[groupId] = [];
      _groupNameCache.putIfAbsent(groupId, () => 'Unavailable group');
    }
  }

  List<LinkedMemberView> _resolveLinkedMembers(
    List<PresencePeopleProfileLink> links,
  ) {
    // Dedupe by MVR UUID. Prefer links that resolve to a live group member
    // over stale deleted-group links (dirty PPP hierarchy).
    final byMvr = <String, LinkedMemberView>{};
    final scoreByMvr = <String, int>{};
    for (final link in links) {
      final members = _membersByGroupCache[link.groupId] ?? const [];
      IndividualSummary? match;
      for (final m in members) {
        if (m.mvrPersonUuid == link.individualId || m.id == link.individualId) {
          match = m;
          break;
        }
      }
      final mvrUuid = link.individualId.isNotEmpty
          ? link.individualId
          : (match?.mvrPersonUuid ?? match?.id ?? '');
      if (mvrUuid.isEmpty) continue;
      final groupName =
          _groupNameCache[link.groupId] ?? _shortGroupLabel(link.groupId);
      final unavailable = groupName == 'Unavailable group';
      // Higher is better: live member match > known group > deleted group.
      final score = match != null ? 3 : (unavailable ? 0 : 1);
      final existingScore = scoreByMvr[mvrUuid] ?? -1;
      if (score <= existingScore) continue;
      scoreByMvr[mvrUuid] = score;
      final member = _memberWithMvrUuid(match, mvrUuid);
      if (!widget.showArchived && member.isArchived == true) {
        continue;
      }
      byMvr[mvrUuid] = LinkedMemberView(
        member: member,
        groupId: link.groupId,
        groupName: groupName,
        mvrUuid: mvrUuid,
      );
    }
    return byMvr.values.toList();
  }

  Future<void> _loadLinkedMembers(String pppUuid) async {
    setState(() {
      _loadingMembers = true;
      _membersError = null;
      _linkedMembers = [];
      _selectedDetail = null;
    });

    final detailResp = await _presenceApi.getPeopleProfile(pppUuid);
    if (!mounted) return;

    if (!detailResp.success || detailResp.data == null) {
      setState(() {
        _loadingMembers = false;
        _membersError = detailResp.error ?? 'Failed to load people profile';
      });
      return;
    }

    final profile = detailResp.data!;
    final links = profile.links;
    if (links.isEmpty) {
      setState(() {
        _selectedDetail = profile;
        _linkedMembers = [];
        _loadingMembers = false;
      });
      return;
    }

    // Fast path (Groups-tab parity): paint stubs from presence links immediately
    // so LinkedMembersGrid can start best-image fetches without waiting on
    // listGroups / getGroupMembers. Enrich names/metadata afterwards.
    final fastResolved = <LinkedMemberView>[];
    final seenMvr = <String>{};
    for (final link in links) {
      final mvrUuid = link.individualId.trim();
      if (mvrUuid.isEmpty || !seenMvr.add(mvrUuid)) continue;
      fastResolved.add(
        LinkedMemberView(
          member: _memberWithMvrUuid(null, mvrUuid),
          groupId: link.groupId,
          groupName: _groupNameCache[link.groupId] ??
              _shortGroupLabel(link.groupId),
          mvrUuid: mvrUuid,
        ),
      );
    }
    setState(() {
      _selectedDetail = profile;
      _linkedMembers = fastResolved;
      _loadingMembers = false;
    });

    // Background enrichment — parallel group fetches, then refresh labels/names.
    await _warmGroupListCache();
    if (!mounted || _selectedPppUuid != pppUuid) return;

    final groupIds = links.map((l) => l.groupId).toSet();
    await Future.wait([
      for (final groupId in groupIds) _ensureGroupMemberCache(groupId),
    ]);
    if (!mounted || _selectedPppUuid != pppUuid) return;

    final enriched = _resolveLinkedMembers(links);
    // Soft-prune dirty hierarchy: links to deleted groups with no member match.
    final pruned = [
      for (final v in enriched)
        if (!(v.groupName == 'Unavailable group' &&
            (v.member.name == 'Linked member' ||
                (v.member.name ?? '').isEmpty)))
          v,
    ];
    setState(() {
      _linkedMembers = pruned;
    });
  }

  void _openNarrowDetail(PresencePeopleProfile profile) {
    Navigator.of(context)
        .push(
      MaterialPageRoute<void>(
        builder: (_) => _PeopleLinkedMembersPage(
          pppUuid: profile.pppUuid,
          peopleName: profile.name,
        ),
      ),
    )
        .then((_) {
      if (mounted) _loadProfiles();
    });
  }

  @override
  Widget build(BuildContext context) {
    return isWide(context) ? _buildWideLayout() : _buildNarrowLayout();
  }

  Widget _searchBar() {
    return ListableItemsActionBar(
      searchController: _searchController,
      onSearchChanged: (value) {
        setState(() => _searchQuery = value);
        _loadProfiles(showSpinner: false);
      },
    );
  }

  Widget _buildNarrowLayout() {
    return Column(
      children: [
        _searchBar(),
        Expanded(child: _buildListContent()),
      ],
    );
  }

  Widget _buildWideLayout() {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          width: kMasterPaneWidth,
          child: Column(
            children: [
              _searchBar(),
              Expanded(child: _buildListContent()),
            ],
          ),
        ),
        const VerticalDivider(width: 1),
        Expanded(child: _buildDetailPane()),
      ],
    );
  }

  Widget _buildDetailPane() {
    final profile = _selectedDetail ?? _selectedProfile;
    if (profile == null && !_loadingMembers) {
      return const Center(
        child: Padding(
          padding: EdgeInsets.all(24),
          child: Text('Select a person to see linked members.'),
        ),
      );
    }

    final title = profile?.name ?? 'People';
    final linkedCount = _selectedDetail?.linkedMemberCount ??
        profile?.linkedMemberCount ??
        _linkedMembers.length;
    final subtitle = _loadingMembers
        ? 'Loading linked members…'
        : '$linkedCount linked member${linkedCount == 1 ? '' : 's'}';

    return Padding(
      padding: const EdgeInsets.fromLTRB(8, 8, 4, 8),
      child: ContentPane(
        title: title,
        subtitle: subtitle,
        child: ListView(
          children: [
            if (profile?.email != null && profile!.email!.isNotEmpty) ...[
              Text(
                profile.email!,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                    ),
              ),
              const SizedBox(height: 8),
            ],
            if (profile?.notes != null && profile!.notes!.isNotEmpty) ...[
              Text(
                profile.notes!,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                    ),
              ),
              const SizedBox(height: 16),
            ],
            Text('Linked members',
                style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            if (_loadingMembers)
              const Padding(
                padding: EdgeInsets.all(24),
                child: Center(
                  child: SizedBox(
                    width: 28,
                    height: 28,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  ),
                ),
              )
            else if (_membersError != null)
              Padding(
                padding: const EdgeInsets.all(16),
                child: Text(_membersError!,
                    style: const TextStyle(color: Colors.red)),
              )
            else
              LinkedMembersGrid(
                key: ValueKey('${_selectedPppUuid}_${widget.showArchived}'),
                members: _linkedMembers,
                onArchived: () {
                  final selected = _selectedPppUuid;
                  if (selected != null) {
                    _membersByGroupCache.clear();
                    _loadLinkedMembers(selected);
                    _loadProfiles(showSpinner: false);
                  }
                },
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildListContent() {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_errorMessage != null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.error_outline, size: 64, color: Colors.red),
            const SizedBox(height: 16),
            Text('Error: $_errorMessage'),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: _loadProfiles,
              child: const Text('Retry'),
            ),
          ],
        ),
      );
    }

    if (_profiles.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.person_outline, size: 96, color: Colors.grey[400]),
            const SizedBox(height: 16),
            Text(
              'No people found',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 8),
            Text(
              'Create people profiles in Presence, or clear your search.',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: Colors.grey[600],
                  ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: _loadProfiles,
      child: ListView.builder(
        padding: const EdgeInsets.all(16),
        itemCount: _profiles.length,
        itemBuilder: (context, index) {
          final profile = _profiles[index];
          final selected =
              isWide(context) && _selectedPppUuid == profile.pppUuid;
          final nameKey = profile.name.trim().toLowerCase();
          final duplicateName = nameKey.isNotEmpty &&
              _profiles.where((p) => p.name.trim().toLowerCase() == nameKey).length >
                  1;
          final shortId = profile.pppUuid.length > 8
              ? profile.pppUuid.substring(0, 8)
              : profile.pppUuid;
          final identityLine = (profile.email != null && profile.email!.isNotEmpty)
              ? profile.email!
              : (duplicateName ? 'No email · $shortId' : null);
          return ListableCard(
            isSelected: selected,
            onTap: () {
              if (isWide(context)) {
                _onSelectProfile(profile.pppUuid);
              } else {
                _openNarrowDetail(profile);
              }
            },
            leadingIcon: CircleAvatar(
              radius: 24,
              backgroundColor: AppColors.secondary.withValues(alpha: 0.15),
              child: Text(
                profile.linkedMemberCount.toString(),
                style: AppTextStyles.h6.copyWith(
                  color: AppColors.secondary,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
            title: Text(
              profile.name,
              style: AppTextStyles.bodyLarge.copyWith(
                fontWeight: selected ? FontWeight.w600 : FontWeight.normal,
              ),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
            titleBadge: Container(
              padding: const EdgeInsets.symmetric(
                horizontal: AppSpacing.sm,
                vertical: AppSpacing.xs,
              ),
              decoration: BoxDecoration(
                color: AppColors.info.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(AppRadius.xs),
                border: Border.all(
                  color: AppColors.info.withValues(alpha: 0.3),
                  width: 1,
                ),
              ),
              child: Text(
                profile.status == 'active' ? 'Active' : profile.status,
                style: AppTextStyles.caption.copyWith(
                  color: AppColors.info,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ),
            body: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SizedBox(height: AppSpacing.xs),
                Text(
                  profile.linkedMemberCount > 0
                      ? '${profile.linkedMemberCount} linked member${profile.linkedMemberCount == 1 ? '' : 's'}'
                      : 'No linked members',
                  style: AppTextStyles.caption,
                ),
                if (identityLine != null) ...[
                  const SizedBox(height: AppSpacing.xs),
                  Text(
                    identityLine,
                    style: AppTextStyles.caption
                        .copyWith(color: AppColors.textTertiary),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              ],
            ),
          );
        },
      ),
    );
  }
}

/// Narrow-layout detail page for a person's linked members.
class _PeopleLinkedMembersPage extends ConsumerStatefulWidget {
  final String pppUuid;
  final String peopleName;

  const _PeopleLinkedMembersPage({
    required this.pppUuid,
    required this.peopleName,
  });

  @override
  ConsumerState<_PeopleLinkedMembersPage> createState() =>
      _PeopleLinkedMembersPageState();
}

class _PeopleLinkedMembersPageState
    extends ConsumerState<_PeopleLinkedMembersPage> {
  List<LinkedMemberView> _linkedMembers = [];
  bool _loading = true;
  String? _error;

  final Map<String, List<IndividualSummary>> _membersByGroupCache = {};
  final Map<String, String> _groupNameCache = {};

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final presence = PresenceApiClient(ref.read(apiClientProvider));
    final groupsApi = IndividualGroupsApiClient(ref.read(apiClientProvider));

    final detailResp = await presence.getPeopleProfile(widget.pppUuid);
    if (!mounted) return;
    if (!detailResp.success || detailResp.data == null) {
      setState(() {
        _loading = false;
        _error = detailResp.error ?? 'Failed to load profile';
      });
      return;
    }

    final links = detailResp.data!.links;

    // Fast path: paint stubs immediately so faces can load like Groups tab.
    final fastResolved = <LinkedMemberView>[];
    final seenMvr = <String>{};
    for (final link in links) {
      final mvrUuid = link.individualId.trim();
      if (mvrUuid.isEmpty || !seenMvr.add(mvrUuid)) continue;
      fastResolved.add(
        LinkedMemberView(
          member: PeopleProfilesTabState._memberWithMvrUuid(null, mvrUuid),
          groupId: link.groupId,
          groupName: _groupNameCache[link.groupId] ??
              (link.groupId.length <= 12
                  ? link.groupId
                  : '${link.groupId.substring(0, 10)}…'),
          mvrUuid: mvrUuid,
        ),
      );
    }
    if (!mounted) return;
    setState(() {
      _linkedMembers = fastResolved;
      _loading = false;
    });

    final knownGroupIds = <String>{};
    final listResp = await groupsApi.listGroups(limit: 200);
    if (listResp.success && listResp.data != null) {
      for (final g in listResp.data!.groups) {
        knownGroupIds.add(g.id);
        _groupNameCache[g.id] = g.name;
      }
    }

    await Future.wait([
      for (final groupId in links.map((l) => l.groupId).toSet())
        () async {
          if (!knownGroupIds.contains(groupId)) {
            _membersByGroupCache[groupId] = [];
            _groupNameCache.putIfAbsent(groupId, () => 'Unavailable group');
            return;
          }
          final membersResp =
              await groupsApi.getGroupMembers(groupId, limit: 200);
          _membersByGroupCache[groupId] =
              membersResp.success && membersResp.data != null
                  ? membersResp.data!.members
                  : [];
        }(),
    ]);

    if (!mounted) return;

    final resolved = <LinkedMemberView>[];
    final enrichSeen = <String>{};
    for (final link in links) {
      final members = _membersByGroupCache[link.groupId] ?? const [];
      IndividualSummary? match;
      for (final m in members) {
        if (m.mvrPersonUuid == link.individualId || m.id == link.individualId) {
          match = m;
          break;
        }
      }
      final mvrUuid = link.individualId.isNotEmpty
          ? link.individualId
          : (match?.mvrPersonUuid ?? match?.id ?? '');
      if (mvrUuid.isEmpty || !enrichSeen.add(mvrUuid)) continue;
      final groupName = _groupNameCache[link.groupId] ?? 'Unavailable group';
      // Drop stubs that only point at deleted groups with no member match —
      // avoids permanent best-image 404 noise from dirty PPP hierarchy.
      if (match == null && groupName == 'Unavailable group') continue;
      resolved.add(
        LinkedMemberView(
          member: PeopleProfilesTabState._memberWithMvrUuid(match, mvrUuid),
          groupId: link.groupId,
          groupName: groupName,
          mvrUuid: mvrUuid,
        ),
      );
    }

    setState(() {
      _linkedMembers = resolved;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(widget.peopleName)),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(child: Text(_error!))
              : ListView(
                  padding: const EdgeInsets.all(16),
                  children: [
                    Text('Linked members',
                        style: Theme.of(context).textTheme.titleMedium),
                    const SizedBox(height: 8),
                    LinkedMembersGrid(
                      members: _linkedMembers,
                      onArchived: () {
                        // Full-screen people detail reloads via parent route.
                      },
                    ),
                  ],
                ),
    );
  }
}

/// Grid of linked MVR members — reuses Groups-tab face image loading/rendering.
class LinkedMembersGrid extends ConsumerStatefulWidget {
  final List<LinkedMemberView> members;
  final VoidCallback? onArchived;

  const LinkedMembersGrid({
    super.key,
    required this.members,
    this.onArchived,
  });

  @override
  ConsumerState<LinkedMembersGrid> createState() => _LinkedMembersGridState();
}

class _LinkedMembersGridState extends ConsumerState<LinkedMembersGrid> {
  Map<String, BestImageResponse?> _images = {};

  MVRApiClient get _mvrApiClient =>
      MVRApiClient(ref.read(apiClientProvider));

  @override
  void initState() {
    super.initState();
    _loadImages();
  }

  @override
  void didUpdateWidget(covariant LinkedMembersGrid oldWidget) {
    super.didUpdateWidget(oldWidget);
    final oldIds = {
      for (final m in oldWidget.members) m.mvrUuid,
    };
    final newIds = {
      for (final m in widget.members) m.mvrUuid,
    };
    // Only refetch when the MVR set changes — enrichment renaming must not
    // cancel/restart in-flight best-image calls.
    if (oldIds.length != newIds.length || !oldIds.containsAll(newIds)) {
      _loadImages();
    }
  }

  Future<void> _loadImages() async {
    // Same best-image API as Groups, but keyed by stable mvrUuid so background
    // enrichment (which may change member.id) does not drop already-loaded faces.
    final ids = <String>{
      for (final v in widget.members)
        if (v.mvrUuid.isNotEmpty) v.mvrUuid,
    }.toList();
    if (ids.isEmpty) {
      if (mounted) setState(() => _images = {});
      return;
    }
    final byMvr = await ref.read(mvrImageServiceProvider).getBestImagesForMultiple(
          ids,
          includeMerged: true,
        );
    if (!mounted) return;
    setState(() {
      _images = {
        for (final v in widget.members) v.mvrUuid: byMvr[v.mvrUuid],
      };
    });
  }

  void _openMemberAnalysis(LinkedMemberView view) {
    final analysisUuid = view.member.mvrPersonUuid ?? view.mvrUuid;
    if (analysisUuid.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Cannot analyse member without an MVR UUID'),
        ),
      );
      return;
    }
    final analysisContext = CrossVideoAnalysisContext(
      individualUuids: [analysisUuid],
      sessionUuid:
          'ig_member_${view.groupId}_${view.member.id}_${DateTime.now().millisecondsSinceEpoch}',
      sessionData: {
        'source': 'individual_group_member',
        'group_id': view.groupId,
        'group_name': view.groupName,
        'member_name': view.member.name ?? 'Unnamed',
        'individuals_found': 1,
        'total_videos': 0,
        'hierarchical_merge_applied': true,
        'search_results': <dynamic>[],
      },
    );
    Navigator.of(context, rootNavigator: true).push(
      MaterialPageRoute<void>(
        builder: (_) =>
            PersonObjectsDetailScreen(crossVideoContext: analysisContext),
      ),
    );
  }

  String _label(IndividualSummary member, int index) {
    final number = member.groupMemberNumber ?? (index + 1);
    return 'Group Member ${number.toString().padLeft(2, '0')}';
  }

  Future<void> _archiveMember(LinkedMemberView view) async {
    final mvrUuid = view.mvrUuid;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Archive person'),
        content: const Text(
          'Archive this person? This cannot be undone. They will be removed '
          'from groups and people links and ignored in searches. The record '
          'is kept in the database as archived.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            style: TextButton.styleFrom(
              foregroundColor: Theme.of(context).colorScheme.error,
            ),
            child: const Text('Archive'),
          ),
        ],
      ),
    );
    if (confirmed != true || !mounted) return;

    final response = await _mvrApiClient.archiveMvrPerson(mvrUuid);
    if (!mounted) return;

    if (!response.success || response.data == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(response.error ?? 'Failed to archive person'),
          backgroundColor: Colors.red,
        ),
      );
      return;
    }

    final result = response.data!;
    final promoted = result.promotedMvrUuid;
    final promotedLabel = (result.promotedName?.trim().isNotEmpty == true)
        ? result.promotedName!.trim()
        : (promoted != null && promoted.length >= 8
            ? '${promoted.substring(0, 8)}…'
            : promoted);
    if (promoted != null && promoted.isNotEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            'Archived. Next best match $promotedLabel is now the group/search winner.',
          ),
          duration: const Duration(seconds: 5),
        ),
      );
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(result.message ?? 'Person archived')),
      );
    }
    widget.onArchived?.call();
  }

  @override
  Widget build(BuildContext context) {
    if (widget.members.isEmpty) {
      return const Padding(
        padding: EdgeInsets.all(16),
        child: Text('No linked members for this person yet.'),
      );
    }
    return GridView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 3,
        crossAxisSpacing: 10,
        mainAxisSpacing: 10,
        childAspectRatio: 0.75,
      ),
      itemCount: widget.members.length,
      itemBuilder: (context, index) =>
          _memberCard(widget.members[index], index),
    );
  }

  Widget _memberCard(LinkedMemberView view, int index) {
    final theme = Theme.of(context);
    final scheme = theme.colorScheme;
    final member = view.member;
    final archived = member.isArchived == true;
    return Opacity(
      opacity: archived ? 0.55 : 1,
      child: Card(
        clipBehavior: Clip.antiAlias,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        child: InkWell(
          onTap: () => _openMemberAnalysis(view),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Expanded(
                child: Stack(
                  fit: StackFit.expand,
                  children: [
                    GroupMemberFaceImage(bestImage: _images[view.mvrUuid]),
                    if (archived)
                      Positioned(
                        bottom: 6,
                        left: 6,
                        child: Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 6,
                            vertical: 2,
                          ),
                          decoration: BoxDecoration(
                            color: Colors.black54,
                            borderRadius: BorderRadius.circular(4),
                          ),
                          child: const Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(Icons.archive,
                                  size: 12, color: Colors.white),
                              SizedBox(width: 4),
                              Text(
                                'Archived',
                                style: TextStyle(
                                  color: Colors.white,
                                  fontSize: 10,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    if (!archived && (member.canManageMember ?? true))
                      Positioned(
                        top: 6,
                        right: 6,
                        child: Tooltip(
                          message: 'Archive person',
                          child: Material(
                            color: Colors.black54,
                            shape: const CircleBorder(),
                            child: InkWell(
                              customBorder: const CircleBorder(),
                              onTap: () => _archiveMember(view),
                              child: const Padding(
                                padding: EdgeInsets.all(6),
                                child: Icon(
                                  Icons.archive_outlined,
                                  size: 22,
                                  color: Colors.white,
                                ),
                              ),
                            ),
                          ),
                        ),
                      ),
                  ],
                ),
              ),
              Padding(
                padding: const EdgeInsets.all(8),
                child: Column(
                  children: [
                    Text(
                      _label(member, index),
                      style: theme.textTheme.labelSmall
                          ?.copyWith(fontWeight: FontWeight.w600),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      textAlign: TextAlign.center,
                    ),
                    if (member.name != null)
                      Text(
                        member.name!,
                        style: theme.textTheme.bodySmall
                            ?.copyWith(color: scheme.onSurfaceVariant),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        textAlign: TextAlign.center,
                      ),
                    const SizedBox(height: 4),
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 6,
                        vertical: 2,
                      ),
                      decoration: BoxDecoration(
                        color: AppColors.secondary.withValues(alpha: 0.12),
                        borderRadius: BorderRadius.circular(AppRadius.xs),
                      ),
                      child: Text(
                        view.groupName,
                        style: AppTextStyles.caption.copyWith(
                          fontSize: 10,
                          color: AppColors.secondary,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
