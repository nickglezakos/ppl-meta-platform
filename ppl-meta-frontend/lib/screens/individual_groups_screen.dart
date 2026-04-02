/// Individual Groups List Screen
/// Displays all individual groups with search and filtering
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:cached_network_image/cached_network_image.dart';
import '../models/individual_group_models.dart';
import '../services/individual_groups_api_client.dart';
import '../services/mvr_image_service.dart';
import '../providers/mvr_image_service_provider.dart';
import '../models/mvr_best_image.dart';
import '../core/api/api_client.dart';
import '../core/config/app_config.dart';
import 'individual_group_detail_screen.dart';
import 'person_objects_detail_screen.dart';
import '../widgets/individual_groups/create_group_dialog.dart';
import '../widgets/individual_groups/camera_search_dialog.dart';
import '../widgets/custom_app_bar.dart';
import '../models/cross_video_analysis_models.dart';

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
      body: Column(
        children: [
          // Search bar
          Padding(
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
          ),
          
          // Content
          Expanded(
            child: _buildContent(),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _showCreateGroupDialog,
        icon: const Icon(Icons.add),
        label: const Text('New Group'),
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
        return _GroupCard(
          group: group,
          apiClient: _apiClient,
          onTap: () => _navigateToGroupDetail(group),
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
        return Card(
          margin: const EdgeInsets.only(bottom: 12),
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
                const SizedBox(height: 8),
                _MemberFaceThumbnails(
                  groupId: group.id,
                  maxFaces: 5,
                ),
              ],
            ),
            trailing: _buildVisibilityChip(group.visibility),
            onTap: () => _navigateToGroupDetail(group),
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
  });

  @override
  Widget build(BuildContext context) {
    final coverIndividualId = group.metadata?['cover_individual_id'] as String?;
    
    return Card(
      clipBehavior: Clip.antiAlias,
      elevation: 2,
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
                  const SizedBox(height: 8),
                  _MemberFaceThumbnails(
                    groupId: group.id,
                    maxFaces: 3,
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

/// Widget to display member face thumbnails for a group
class _MemberFaceThumbnails extends ConsumerStatefulWidget {
  final String groupId;
  final int maxFaces;

  const _MemberFaceThumbnails({
    required this.groupId,
    required this.maxFaces,
  });

  @override
  ConsumerState<_MemberFaceThumbnails> createState() =>
      _MemberFaceThumbnailsState();
}

class _MemberFaceThumbnailsState extends ConsumerState<_MemberFaceThumbnails> {
  List<String>? _memberMvrUuids;
  Map<String, BestImageResponse?> _faceImages = {};
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadMemberFaces();
  }

  Future<void> _loadMemberFaces() async {
    try {
      // Get group members
      final apiClient = ref.read(apiClientProvider);
      final groupsClient = IndividualGroupsApiClient(apiClient);
      final response = await groupsClient.getGroupMembers(widget.groupId);

      if (!mounted) return;

      // Check if response is successful and has data
      if (!response.success || response.data == null) {
        setState(() {
          _isLoading = false;
        });
        return;
      }

      // Get top N member MVR UUIDs
      final mvrUuids = response.data!.members
          .take(widget.maxFaces)
          .map((m) => m.id)
          .toList();

      setState(() {
        _memberMvrUuids = mvrUuids;
      });

      // Fetch face images for all members in parallel
      if (mvrUuids.isNotEmpty) {
        final imageService = ref.read(mvrImageServiceProvider);
        final images = await imageService.getBestImagesForMultiple(
          mvrUuids,
          includeMerged: false,
        );

        if (!mounted) return;

        setState(() {
          _faceImages = images;
          _isLoading = false;
        });
      } else {
        setState(() {
          _isLoading = false;
        });
      }
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const SizedBox(
        height: 32,
        child: Center(
          child: SizedBox(
            width: 16,
            height: 16,
            child: CircularProgressIndicator(strokeWidth: 2),
          ),
        ),
      );
    }

    if (_memberMvrUuids == null || _memberMvrUuids!.isEmpty) {
      return const SizedBox.shrink();
    }

    return SizedBox(
      height: 32,
      child: Row(
        children: _memberMvrUuids!.map((mvrUuid) {
          final imageData = _faceImages[mvrUuid];
          final imageUrl = imageData?.bestFace?.imageUrl;

          return Padding(
            padding: const EdgeInsets.only(right: 4),
            child: CircleAvatar(
              radius: 16,
              backgroundColor: Colors.grey[300],
              child: imageUrl != null
                  ? ClipOval(
                      child: CachedNetworkImage(
                        imageUrl: imageUrl,
                        width: 32,
                        height: 32,
                        fit: BoxFit.cover,
                        placeholder: (context, url) => const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(strokeWidth: 1),
                        ),
                        errorWidget: (context, url, error) => Icon(
                          Icons.person,
                          size: 16,
                          color: Colors.grey[600],
                        ),
                      ),
                    )
                  : Icon(
                      Icons.person,
                      size: 16,
                      color: Colors.grey[600],
                    ),
            ),
          );
        }).toList(),
      ),
    );
  }
}
