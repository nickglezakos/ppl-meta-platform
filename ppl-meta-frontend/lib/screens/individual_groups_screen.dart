/// Individual Groups List Screen
/// Displays all individual groups with search and filtering
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/individual_group_models.dart';
import '../services/individual_groups_api_client.dart';
import '../providers/mvr_image_service_provider.dart';
import '../models/mvr_best_image.dart';
import '../core/api/api_client.dart';
import '../core/config.dart';
import '../core/config/app_config.dart';
import '../widgets/individual_groups/edit_group_dialog.dart';
import '../core/theme/theme_kit.dart';
import 'individual_group_detail_screen.dart';
import 'person_objects_detail_screen.dart';
import '../widgets/individual_groups/create_group_dialog.dart';
import '../widgets/individual_groups/camera_search_dialog.dart';
import '../widgets/custom_app_bar.dart';
import '../models/cross_video_analysis_models.dart';
import '../presentation/widgets/common/ux_breakpoints.dart';
import '../presentation/widgets/common/content_pane.dart';

class IndividualGroupsScreen extends ConsumerStatefulWidget {
  const IndividualGroupsScreen({super.key});

  @override
  ConsumerState<IndividualGroupsScreen> createState() =>
      _IndividualGroupsScreenState();
}

class _IndividualGroupsScreenState
    extends ConsumerState<IndividualGroupsScreen> {
  List<IndividualGroup> _groups = [];
  bool _isLoading = true;
  String? _errorMessage;
  final TextEditingController _searchController = TextEditingController();
  String _searchQuery = '';
  GroupVisibility? _selectedVisibility;
  String? _selectedGroupId;

  IndividualGroup? get _selectedGroup {
    if (_groups.isEmpty) return null;
    for (final g in _groups) {
      if (g.id == _selectedGroupId) return g;
    }
    return _groups.first;
  }

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _loadGroups();
    });
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  IndividualGroupsApiClient get _apiClient {
    final apiClient = ref.read(apiClientProvider);
    return IndividualGroupsApiClient(apiClient);
  }

  Future<void> _loadGroups() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    final response = await _apiClient.listGroups(
      search: _searchQuery.isEmpty ? null : _searchQuery,
      visibility: _selectedVisibility,
      limit: 100,
    );

    if (response.success && response.data != null) {
      final groups = response.data!.groups;
      setState(() {
        _groups = groups;
        _isLoading = false;
        // Default-select the first group so the sidebar highlights it and the
        // right pane shows its content immediately.
        _selectedGroupId ??= groups.isNotEmpty ? groups.first.id : null;
      });
    } else {
      setState(() {
        _errorMessage = response.error;
        _isLoading = false;
      });
    }
  }

  Future<void> _showCreateGroupDialog() async {
    final request = await showDialog<CreateGroupRequest>(
      context: context,
      builder: (context) => const CreateGroupDialog(),
    );

    if (request != null && mounted) {
      final response = await _apiClient.createGroup(request);
      
      if (response.success && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Created group: ${response.data!.group.name}')),
        );
        _loadGroups();
      } else if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Error: ${response.error}'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: CustomAppBar(
        title: 'Individual Groups',
        showBackButton: true,
        showHomeButton: true,
        actions: [
          const SizedBox(width: 8),
          IconButton(
            onPressed: _showCreateGroupDialog,
            icon: const Icon(Icons.add, color: AppColors.secondary),
            tooltip: 'New Group',
          ),
        ],
      ),
      body: isWide(context) ? _buildWideLayout() : _buildNarrowLayout(),
    );
  }

  Widget _searchBar() {
    return ListableItemsActionBar(
      searchController: _searchController,
      onSearchChanged: (value) {
        setState(() {
          _searchQuery = value;
        });
      },
      filterContent: Center(child: _buildVisibilityFilterToggles()),
    );
  }

  /// Visibility filter toggles (All / Private / Shared / Public).
  Widget _buildVisibilityFilterToggles() {
    const values = <GroupVisibility?>[null, GroupVisibility.private, GroupVisibility.shared, GroupVisibility.public];
    const labels = <String>['All', 'Private', 'Shared', 'Public'];
    const icons = <IconData>[Icons.dashboard_outlined, Icons.lock_outline, Icons.group_outlined, Icons.public];

    return ToggleButtons(
      constraints: const BoxConstraints(minHeight: 32),
      borderRadius: BorderRadius.circular(AppRadius.sm),
      isSelected: [for (final v in values) v == _selectedVisibility],
      onPressed: (index) {
        setState(() => _selectedVisibility = values[index]);
        _loadGroups();
      },
      selectedColor: AppColors.accent,
      fillColor: AppColors.accent.withValues(alpha: 0.1),
      borderColor: AppColors.gray700,
      selectedBorderColor: AppColors.accent.withValues(alpha: 0.4),
      children: [
        for (var i = 0; i < labels.length; i++)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: AppSpacing.sm),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(icons[i], size: AppIconSize.sm),
                const SizedBox(width: AppSpacing.xs),
                Text(labels[i], style: AppTextStyles.caption),
              ],
            ),
          ),
      ],
    );
  }

  /// Narrow (mobile/tablet): full-width search above the list; tap pushes detail.
  Widget _buildNarrowLayout() {
    return Column(
      children: [
        _searchBar(),
        Expanded(child: _buildContent()),
      ],
    );
  }

  /// Wide (desktop): list stays left, active group's members shown right.
  Widget _buildWideLayout() {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          width: kMasterPaneWidth,
          child: Column(
            children: [
              _searchBar(),
              Expanded(child: _buildContent()),
            ],
          ),
        ),
        const VerticalDivider(width: 1),
        Expanded(child: _buildDetailPane()),
      ],
    );
  }

  /// Content-first right pane: the active group's members as avatars.
  Widget _buildDetailPane() {
    final group = _selectedGroup;
    if (group == null) {
      return const Center(
        child: Padding(
          padding: EdgeInsets.all(24),
          child: Text('Select a group to see its members.'),
        ),
      );
    }
    return Padding(
      padding: const EdgeInsets.fromLTRB(8, 8, 4, 8),
      child: ContentPane(
        title: group.name,
        subtitle:
            '${group.memberCount} members · ${group.visibility.toString().split('.').last}',
        child: ListView(
          children: [
            if (group.description != null && group.description!.isNotEmpty) ...[
              Text(
                group.description!,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                    ),
              ),
              const SizedBox(height: 16),
            ],
            Text('Members', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            _MembersGrid(
              key: ValueKey(group.id),
              groupId: group.id,
              groupName: group.name,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildContent() {
    if (_isLoading) {
      return const Center(
        child: CircularProgressIndicator(),
      );
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
              onPressed: _loadGroups,
              child: const Text('Retry'),
            ),
          ],
        ),
      );
    }

    if (_groups.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.group_outlined,
              size: 96,
              color: Colors.grey[400],
            ),
            const SizedBox(height: 16),
            Text(
              'No groups found',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 8),
            Text(
              'Create your first group to get started',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: Colors.grey[600],
                  ),
            ),
            const SizedBox(height: 24),
            ElevatedButton.icon(
              onPressed: _showCreateGroupDialog,
              icon: const Icon(Icons.add),
              label: const Text('Create Group'),
            ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: _loadGroups,
      child: _buildListView(),
    );
  }


  Widget _buildListView() {
    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: _groups.length,
      itemBuilder: (context, index) {
        final group = _groups[index];
        final selected = isWide(context) && _selectedGroupId == group.id;

        final visibilityLabel = group.visibility.toString().split('.').last;
        final IconData visibilityIcon;
        final Color visibilityColor;
        switch (group.visibility) {
          case GroupVisibility.private:
            visibilityIcon = Icons.lock_outline;
            visibilityColor = AppColors.info;
          case GroupVisibility.shared:
            visibilityIcon = Icons.people_outline;
            visibilityColor = AppColors.warning;
          case GroupVisibility.public:
            visibilityIcon = Icons.public;
            visibilityColor = AppColors.success;
        }

        return ListableCard(
          isSelected: selected,
          onTap: () {
            if (isWide(context)) {
              setState(() => _selectedGroupId = group.id);
            } else {
              _navigateToGroupDetail(group);
            }
          },
          leadingIcon: CircleAvatar(
            radius: 24,
            backgroundColor: AppColors.secondary.withValues(alpha: 0.15),
            child: Text(
              group.memberCount.toString(),
              style: AppTextStyles.h6.copyWith(
                color: AppColors.secondary, fontWeight: FontWeight.bold),
            ),
          ),
          title: Text(
            group.name,
            style: AppTextStyles.bodyLarge.copyWith(
              fontWeight: selected ? FontWeight.w600 : FontWeight.normal),
            maxLines: 1, overflow: TextOverflow.ellipsis,
          ),
          titleBadge: Container(
            padding: const EdgeInsets.symmetric(
              horizontal: AppSpacing.sm, vertical: AppSpacing.xs),
            decoration: BoxDecoration(
              color: visibilityColor.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(AppRadius.xs),
              border: Border.all(
                color: visibilityColor.withValues(alpha: 0.3), width: 1),
            ),
            child: Row(mainAxisSize: MainAxisSize.min, children: [
              Icon(visibilityIcon, size: 12, color: visibilityColor),
              SizedBox(width: AppSpacing.xs),
              Flexible(child: Text(visibilityLabel,
                style: AppTextStyles.caption.copyWith(
                  color: visibilityColor, fontWeight: FontWeight.w500),
                overflow: TextOverflow.ellipsis, maxLines: 1)),
            ]),
          ),
          body: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            if (group.description?.isNotEmpty ?? false) ...[
              const SizedBox(height: AppSpacing.xs),
              Text(group.description!,
                style: AppTextStyles.caption.copyWith(color: AppColors.textTertiary),
                maxLines: 2, overflow: TextOverflow.ellipsis),
            ],
            const SizedBox(height: AppSpacing.xs),
            Text('${group.memberCount} ${group.memberCount == 1 ? 'member' : 'members'}',
              style: AppTextStyles.caption),
            if (group.tags.isNotEmpty) ...[
              const SizedBox(height: AppSpacing.sm),
              Wrap(spacing: AppSpacing.xs, runSpacing: AppSpacing.xs,
                children: group.tags.take(3).map((tag) => Chip(
                  label: Text(tag),
                  labelStyle: AppTextStyles.caption.copyWith(fontSize: 10),
                  backgroundColor: AppColors.widgetFill,
                  padding: EdgeInsets.zero,
                  materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                )).toList(),
              ),
            ],
          ]),
          footer: Align(
            alignment: Alignment.centerRight,
            child: PopupMenuButton<String>(
              icon: const Icon(Icons.more_vert, size: 20),
              tooltip: 'Group actions',
              style: IconButton.styleFrom(
                foregroundColor: AppColors.secondary,
              ),
              onSelected: (value) {
                switch (value) {
                  case 'camera_search':
                    _showGroupCameraSearch(group);
                    break;
                  case 'edit':
                    _showEditGroupDialog(group);
                    break;
                  case 'delete':
                    _showDeleteGroupDialog(group);
                    break;
                }
              },
              itemBuilder: (context) => [
                const PopupMenuItem(
                  value: 'camera_search',
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(AppIcons.cameras, size: 18, color: AppColors.secondary),
                      SizedBox(width: AppSpacing.sm),
                      Text('Camera Search'),
                    ],
                  ),
                ),
                const PopupMenuItem(
                  value: 'edit',
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.edit_outlined, size: 18),
                      SizedBox(width: AppSpacing.sm),
                      Text('Edit Group'),
                    ],
                  ),
                ),
                const PopupMenuItem(
                  value: 'delete',
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.delete_outline, size: 18, color: AppColors.error),
                      SizedBox(width: AppSpacing.sm),
                      Text('Delete Group', style: TextStyle(color: AppColors.error)),
                    ],
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }



  void _navigateToGroupDetail(IndividualGroup group) {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => IndividualGroupDetailScreen(
          groupId: group.id,
        ),
      ),
    ).then((_) => _loadGroups()); // Refresh on return
  }

  /// Show the edit group dialog (reuses EditGroupDialog from the detail screen).
  Future<void> _showEditGroupDialog(IndividualGroup group) async {
    await showDialog(
      context: context,
      builder: (context) => EditGroupDialog(group: group),
    );
    if (mounted) _loadGroups();
  }

  /// Show a confirmation dialog and delete the group.
  Future<void> _showDeleteGroupDialog(IndividualGroup group) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Group'),
        content: Text(
          'Are you sure you want to delete "${group.name}"?\n\n'
          'This action cannot be undone.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            style: TextButton.styleFrom(foregroundColor: AppColors.error),
            child: const Text('Delete'),
          ),
        ],
      ),
    );

    if (confirmed != true || !mounted) return;

    final response = await _apiClient.deleteGroup(group.id);
    if (!mounted) return;

    if (response.success) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Group "${group.name}" deleted successfully')),
      );
      setState(() {
        if (_selectedGroupId == group.id) _selectedGroupId = null;
        _groups.removeWhere((g) => g.id == group.id);
      });
      await _loadGroups();
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(response.error ?? 'Failed to delete group'),
          backgroundColor: AppColors.error,
        ),
      );
    }
  }

Future<void> _showGroupCameraSearch(IndividualGroup group) async {
    final searchParams = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (context) => CameraSearchDialog(
        groupId: group.id,
        groupName: group.name,
        memberCount: group.memberCount,
      ),
    );

    if (searchParams != null && mounted) {
      final cameraIds = searchParams['camera_ids'] as List<dynamic>?;
      final cameraUuids = searchParams['camera_uuids'] as List<dynamic>?;
      final cameraNames = searchParams['camera_names'] as List<dynamic>?;
      final displayNames = cameraNames?.join(', ') ?? 'Unknown';

      final analysisContext = CrossVideoAnalysisContext(
        individualUuids: [],
        sessionUuid: 'camera_search_${group.id}_${DateTime.now().millisecondsSinceEpoch}',
        sessionData: {
          'source': 'individual_group_camera_search',
          'group_id': group.id,
          'group_name': group.name,
          'camera_names': displayNames,
          'search_parameters': {
            'camera_ids': cameraIds,
            'camera_uuids': cameraUuids,
            'start_time': searchParams['start_time'],
            'end_time': searchParams['end_time'],
          },
          'total_group_members': group.memberCount,
        },
      );

      Navigator.push(
        context,
        MaterialPageRoute(
          builder: (context) => PersonObjectsDetailScreen(
            crossVideoContext: analysisContext,
          ),
        ),
      );
    }
  }
}

/// Group Card Widget

/// Tappable member cards for the content-first right pane.
/// Each card shows the member's avatar + label ("Group Member NN") + name;
/// tapping it opens the member's deeper analysis screen (read-only navigation).
/// Member management (remove/edit) stays on the existing detail screen.
class _MembersGrid extends ConsumerStatefulWidget {
  final String groupId;
  final String groupName;

  const _MembersGrid({
    super.key,
    required this.groupId,
    required this.groupName,
  });

  @override
  ConsumerState<_MembersGrid> createState() => _MembersGridState();
}

class _MembersGridState extends ConsumerState<_MembersGrid> {
  List<IndividualSummary> _members = [];
  Map<String, BestImageResponse?> _images = {};
  bool _loading = true;

  IndividualGroupsApiClient get _apiClient {
    final apiClient = ref.read(apiClientProvider);
    return IndividualGroupsApiClient(apiClient);
  }

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final response =
        await _apiClient.getGroupMembers(widget.groupId, limit: 200);
    if (!mounted) return;
    if (response.success && response.data != null) {
      setState(() {
        _members = response.data!.members;
        _loading = false;
      });
      _loadImages();
    } else {
      setState(() {
        _loading = false;
      });
    }
  }

  Future<void> _loadImages() async {
    final ids = <String>{
      for (final m in _members)
        if (m.mvrPersonUuid != null) m.mvrPersonUuid!,
    }.toList();
    if (ids.isEmpty) return;
    final images = await ref
        .read(mvrImageServiceProvider)
        .getBestImagesForMultiple(ids, includeMerged: true);
    if (!mounted) return;
    setState(() {
      _images = {
        for (final m in _members)
          m.id: m.mvrPersonUuid != null ? images[m.mvrPersonUuid] : null,
      };
    });
  }

  void _openMemberAnalysis(IndividualSummary member) {
    final analysisUuid = member.mvrPersonUuid;
    if (analysisUuid == null) {
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
          'ig_member_${widget.groupId}_${member.id}_${DateTime.now().millisecondsSinceEpoch}',
      sessionData: {
        'source': 'individual_group_member',
        'group_id': widget.groupId,
        'group_name': widget.groupName,
        'member_name': member.name ?? 'Unnamed',
        'individuals_found': 1,
        'total_videos': 0,
        'hierarchical_merge_applied': true,
        'search_results': <dynamic>[],
      },
    );
    Navigator.of(context).push(
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

  // Mirror the legacy detail screen's avatar resolution:
  // normalize the URL for the browser + attach the auth header.
  String _resolveFaceUrl(String imageUrl) {
    if (imageUrl.isEmpty) {
      return imageUrl;
    }
    final uri = Uri.tryParse(imageUrl);
    if (uri != null && uri.hasScheme) {
      return AppConfig.normalizeBrowserUrl(imageUrl);
    }
    final normalizedPath = imageUrl.startsWith('/') ? imageUrl : '/$imageUrl';
    return AppConfig.normalizeBrowserUrl('${Config.gatewayServiceUrl}$normalizedPath');
  }

  String? _avatarUrl(IndividualSummary member) {
    final best = _images[member.id];
    final face = best?.bestFace;
    if (face != null) {
      if (face.imageUrl.isNotEmpty) {
        return _resolveFaceUrl(face.imageUrl);
      }
      return _resolveFaceUrl('/api/v1/media/thumbnail/${face.videoUuid}');
    }
    final frame = best?.frameImage?.imageUrl;
    if (frame != null && frame.isNotEmpty) {
      return _resolveFaceUrl(frame);
    }
    return null;
  }

  /// Remove a member (reuses the existing `removeMembers` service endpoint —
  /// same call the legacy detail screen uses for its Remove action).
  Future<void> _removeMember(IndividualSummary member) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Remove Member'),
        content: Text('Remove ${member.name ?? 'this member'} from this group?'),
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
            child: const Text('Remove'),
          ),
        ],
      ),
    );
    if (confirmed != true || !mounted) return;

    final response = await _apiClient.removeMembers(
      widget.groupId,
      RemoveMembersRequest(individualIds: [member.id]),
    );
    if (!mounted) return;

    if (response.success) {
      setState(() {
        _members.removeWhere((m) => m.id == member.id);
        _images.remove(member.id);
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('${member.name ?? 'Member'} removed from group')),
      );
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(response.error ?? 'Failed to remove member'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }
@override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Padding(
        padding: EdgeInsets.all(24),
        child: Center(
          child: SizedBox(
            width: 28,
            height: 28,
            child: CircularProgressIndicator(strokeWidth: 2),
          ),
        ),
      );
    }
    if (_members.isEmpty) {
      return const Padding(
        padding: EdgeInsets.all(16),
        child: Text('No members in this group yet.'),
      );
    }
    return GridView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 3,
        crossAxisSpacing: 10,
        mainAxisSpacing: 10,
        childAspectRatio: 0.9,
      ),
      itemCount: _members.length,
      itemBuilder: (context, index) => _memberCard(_members[index], index),
    );
  }

  Widget _avatarFallback(ColorScheme scheme) {
    return Container(
      color: scheme.surfaceContainerHighest,
      alignment: Alignment.center,
      child: Icon(Icons.person, size: 40, color: scheme.onSurfaceVariant),
    );
  }

  Widget _memberCard(IndividualSummary member, int index) {
    final theme = Theme.of(context);
    final scheme = theme.colorScheme;
    final avatarUrl = _avatarUrl(member);
    final headers = ref.read(apiClientProvider).authToken != null
        ? {'Authorization': 'Bearer ${ref.read(apiClientProvider).authToken}'}
        : const <String, String>{};
    return Card(
      clipBehavior: Clip.antiAlias,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: InkWell(
        onTap: () => _openMemberAnalysis(member),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Expanded(
              child: Stack(
                fit: StackFit.expand,
                children: [
                  if (avatarUrl != null)
                    Image.network(
                      avatarUrl,
                      fit: BoxFit.cover,
                      headers: headers,
                      errorBuilder: (context, error, stackTrace) =>
                          _avatarFallback(scheme),
                    )
                  else
                    _avatarFallback(scheme),
                  Positioned(
                    top: 6,
                    right: 6,
                    child: InkWell(
                      onTap: () => _removeMember(member),
                      child: const DecoratedBox(
                        decoration: BoxDecoration(
                          color: Colors.black54,
                          shape: BoxShape.circle,
                        ),
                        child: Padding(
                          padding: EdgeInsets.all(4),
                          child: Icon(Icons.delete_outline,
                              size: 16, color: Colors.white),
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
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
