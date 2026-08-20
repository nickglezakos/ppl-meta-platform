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
  String _searchQuery = '';
  GroupVisibility? _selectedVisibility;
  bool _isGridView = true;
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
      setState(() {
        _groups = response.data!.groups;
        _isLoading = false;
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
          IconButton(
            icon: Icon(_isGridView ? Icons.list : Icons.grid_view),
            onPressed: () {
              setState(() {
                _isGridView = !_isGridView;
              });
            },
            tooltip: _isGridView ? 'List View' : 'Grid View',
          ),
          PopupMenuButton<GroupVisibility?>(
            icon: const Icon(Icons.filter_list),
            onSelected: (visibility) {
              setState(() {
                _selectedVisibility = visibility;
              });
              _loadGroups();
            },
            itemBuilder: (context) => [
              const PopupMenuItem(
                value: null,
                child: Text('All Groups'),
              ),
              const PopupMenuItem(
                value: GroupVisibility.private,
                child: Text('Private'),
              ),
              const PopupMenuItem(
                value: GroupVisibility.shared,
                child: Text('Shared'),
              ),
              const PopupMenuItem(
                value: GroupVisibility.public,
                child: Text('Public'),
              ),
            ],
          ),
          const SizedBox(width: 8),
        ],
      ),
      body: isWide(context) ? _buildWideLayout() : _buildNarrowLayout(),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _showCreateGroupDialog,
        icon: const Icon(Icons.add),
        label: const Text('New Group'),
      ),
    );
  }

  Widget _searchBar() {
    return Padding(
      padding: const EdgeInsets.all(16.0),
      child: TextField(
        decoration: InputDecoration(
          hintText: 'Search groups...',
          prefixIcon: const Icon(Icons.search),
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
          ),
          filled: true,
        ),
        onChanged: (value) {
          setState(() {
            _searchQuery = value;
          });
        },
        onSubmitted: (_) => _loadGroups(),
      ),
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
      child: _isGridView ? _buildGridView() : _buildListView(),
    );
  }

  Widget _buildGridView() {
    return GridView.builder(
      padding: const EdgeInsets.all(16),
      gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
        maxCrossAxisExtent: 300,
        childAspectRatio: 0.85,
        crossAxisSpacing: 16,
        mainAxisSpacing: 16,
      ),
      itemCount: _groups.length,
      itemBuilder: (context, index) {
        final group = _groups[index];
        final selected = isWide(context) && _selectedGroupId == group.id;
        return _GroupCard(
          group: group,
          apiClient: _apiClient,
          selected: selected,
          onTap: () {
            if (isWide(context)) {
              setState(() => _selectedGroupId = group.id);
            } else {
              _navigateToGroupDetail(group);
            }
          },
        );
      },
    );
  }

  Widget _buildListView() {
    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: _groups.length,
      itemBuilder: (context, index) {
        final group = _groups[index];
        final selected = isWide(context) && _selectedGroupId == group.id;
        return Card(
          margin: const EdgeInsets.only(bottom: 12),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
            side: selected
                ? BorderSide(
                    color: Theme.of(context).colorScheme.primary, width: 2)
                : BorderSide.none,
          ),
          child: ListTile(
            leading: CircleAvatar(
              backgroundColor: Theme.of(context).colorScheme.primaryContainer,
              child: Text(
                group.memberCount.toString(),
                style: TextStyle(
                  color: Theme.of(context).colorScheme.onPrimaryContainer,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
            title: Text(group.name),
            subtitle: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  group.description ?? 'No description',
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
                ],
            ),
            trailing: _buildVisibilityChip(group.visibility),
            onTap: () {
              if (isWide(context)) {
                setState(() => _selectedGroupId = group.id);
              } else {
                _navigateToGroupDetail(group);
              }
            },
          ),
        );
      },
    );
  }

  Widget _buildVisibilityChip(GroupVisibility visibility) {
    IconData icon;
    Color color;
    
    switch (visibility) {
      case GroupVisibility.private:
        icon = Icons.lock_outline;
        color = Colors.blue;
        break;
      case GroupVisibility.shared:
        icon = Icons.people_outline;
        color = Colors.orange;
        break;
      case GroupVisibility.public:
        icon = Icons.public;
        color = Colors.green;
        break;
    }

    return Chip(
      avatar: Icon(icon, size: 16, color: color),
      label: Text(
        visibility.toString().split('.').last,
        style: TextStyle(color: color, fontSize: 12),
      ),
      backgroundColor: color.withOpacity(0.1),
      padding: EdgeInsets.zero,
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
}

/// Group Card Widget
class _GroupCard extends StatelessWidget {
  final IndividualGroup group;
  final IndividualGroupsApiClient apiClient;
  final VoidCallback onTap;

  const _GroupCard({
    required this.group,
    required this.apiClient,
    required this.onTap,
    this.selected = false,
  });

  final bool selected;

  @override
  Widget build(BuildContext context) {
    final coverIndividualId = group.metadata?['cover_individual_id'] as String?;
    
    return Card(
      clipBehavior: Clip.antiAlias,
      elevation: 2,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: selected
            ? BorderSide(
                color: Theme.of(context).colorScheme.primary, width: 2)
            : BorderSide.none,
      ),
      child: InkWell(
        onTap: onTap,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Cover image or placeholder with search button overlay
            Expanded(
              child: Stack(
                children: [
                  Container(
                    width: double.infinity,
                    color: Theme.of(context).colorScheme.surfaceVariant,
                    child: coverIndividualId != null
                        ? Image.network(
                            apiClient.getThumbnailUrl(
                              coverIndividualId,
                              size: 'medium',
                            ),
                            fit: BoxFit.cover,
                            errorBuilder: (context, error, stackTrace) =>
                                _buildPlaceholder(context),
                          )
                        : _buildPlaceholder(context),
                  ),
                  // Search button overlay
                  Positioned(
                    top: 8,
                    right: 8,
                    child: Material(
                      color: Colors.white.withOpacity(0.9),
                      borderRadius: BorderRadius.circular(20),
                      elevation: 2,
                      child: InkWell(
                        borderRadius: BorderRadius.circular(20),
                        onTap: () => _showCameraSearchDialog(context),
                        child: Padding(
                          padding: const EdgeInsets.all(8),
                          child: Icon(
                            Icons.video_camera_front,
                            size: 20,
                            color: Theme.of(context).colorScheme.primary,
                          ),
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
            
            // Group info
            Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    group.name,
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.bold,
                        ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: 4),
                  Text(
                    '${group.memberCount} ${group.memberCount == 1 ? 'member' : 'members'}',
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: Colors.grey[600],
                        ),
                  ),
                  if (group.tags.isNotEmpty) ...[
                    const SizedBox(height: 8),
                    Wrap(
                      spacing: 4,
                      children: group.tags.take(2).map((tag) {
                        return Chip(
                          label: Text(tag),
                          labelStyle: const TextStyle(fontSize: 10),
                          padding: EdgeInsets.zero,
                          materialTapTargetSize:
                              MaterialTapTargetSize.shrinkWrap,
                        );
                      }).toList(),
                    ),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildPlaceholder(BuildContext context) {
    return Center(
      child: Icon(
        Icons.group,
        size: 64,
        color: Theme.of(context).colorScheme.onSurfaceVariant.withOpacity(0.3),
      ),
    );
  }

  void _showCameraSearchDialog(BuildContext context) async {
    final searchParams = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (context) => CameraSearchDialog(
        groupId: group.id,
        groupName: group.name,
        memberCount: group.memberCount,
      ),
    );

    if (searchParams != null && context.mounted) {
      // Handle both single and multiple cameras
      final cameraIds = searchParams['camera_ids'] as List<dynamic>?;
      final cameraUuids = searchParams['camera_uuids'] as List<dynamic>?;
      final cameraNames = searchParams['camera_names'] as List<dynamic>?;
      
      // Format camera names for display
      final displayNames = cameraNames?.join(', ') ?? 'Unknown';
      
      // Navigate to cross-video analysis with camera search context
      final analysisContext = CrossVideoAnalysisContext(
        individualUuids: [], // Will be populated by backend
        sessionUuid: 'camera_search_${group.id}_${DateTime.now().millisecondsSinceEpoch}',
        sessionData: {
          'source': 'individual_group_camera_search',
          'group_id': group.id,
          'group_name': group.name,
          'camera_names': displayNames,  // Display string for UI
          'search_parameters': {
            'camera_ids': cameraIds,    // Collection names — used by group-camera-search API
            'camera_uuids': cameraUuids, // Collection UUIDs — used by routes filtering
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
