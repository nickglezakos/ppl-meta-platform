/// Individual Group Detail Screen
/// Shows group details and member grid with thumbnails
library;

import 'dart:ui' as ui;
import 'dart:async';
import 'dart:typed_data';
import 'dart:math' as math;
import 'package:dio/dio.dart' as dio;
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:uuid/uuid.dart';
import '../core/config/app_config.dart';
import '../core/config.dart';
import '../models/individual_group_models.dart';
import '../services/individual_groups_api_client.dart';
import '../core/api/api_client.dart';
import '../widgets/individual_groups/edit_group_dialog.dart';
import '../widgets/individual_groups/add_members_dialog.dart';
import '../widgets/individual_groups/cover_image_selector.dart';
import '../widgets/people_profile_picker.dart';
import '../services/presence_api_client.dart';
import '../widgets/custom_app_bar.dart';
import '../models/cross_video_analysis_models.dart';
import '../models/mvr_best_image.dart';
import '../services/mvr_image_service.dart';
import '../providers/mvr_image_service_provider.dart';
import 'person_objects_detail_screen.dart';

class IndividualGroupDetailScreen extends ConsumerStatefulWidget {
  final String groupId;

  const IndividualGroupDetailScreen({
    super.key,
    required this.groupId,
  });

  @override
  ConsumerState<IndividualGroupDetailScreen> createState() =>
      _IndividualGroupDetailScreenState();
}

class _IndividualGroupDetailScreenState
    extends ConsumerState<IndividualGroupDetailScreen> {
  IndividualGroup? _group;
  List<IndividualSummary> _members = [];
  Map<String, BestImageResponse?> _bestImages = {};
  bool _isLoading = true;
  String? _errorMessage;
  final Set<String> _debuggedFaces = {}; // Track which faces we've logged
  final Set<String> _failedThumbnailUrls = {};
  final Map<String, String> _workingThumbnailUrlByMember = {};
  final Set<String> _selectedMembers = {};
  bool _isSelectionMode = false;

  String _formatGroupMemberLabel(IndividualSummary member, int index) {
    final number = member.groupMemberNumber ?? (index + 1);
    return 'Group Member ${number.toString().padLeft(2, '0')}';
  }

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _loadGroupData();
    });
  }

  IndividualGroupsApiClient get _apiClient {
    final apiClient = ref.read(apiClientProvider);
    return IndividualGroupsApiClient(apiClient);
  }

  Future<void> _loadGroupData() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    // Load group details
    final groupResponse = await _apiClient.getGroup(widget.groupId);
    debugPrint(
      '[IG-DEBUG][UI] getGroup groupId=${widget.groupId} success=${groupResponse.success} '
      'error=${groupResponse.error}',
    );
    
    if (!groupResponse.success) {
      setState(() {
        _errorMessage = groupResponse.error;
        _isLoading = false;
      });
      return;
    }

    // Load all members
    final membersResponse = await _apiClient.getGroupMembers(
      widget.groupId,
      limit: 200, // Backend max limit
    );
    debugPrint(
      '[IG-DEBUG][UI] getGroupMembers groupId=${widget.groupId} success=${membersResponse.success} '
      'count=${membersResponse.data?.members.length ?? 0} error=${membersResponse.error}',
    );

    setState(() {
      _group = groupResponse.data!.group;
      // Defensive: drop any member without a resolvable MVR identity. Such
      // "shell" memberships carry no analysable UUID and cannot be rendered.
      _members = (membersResponse.data?.members ?? [])
          .where((member) => member.mvrPersonUuid != null)
          .toList();
      _isLoading = false;
    });

    // Debug: Check if members have names
    print('📝 Loaded ${_members.length} members');
    for (var member in _members) {
      print(
        '[IG-DEBUG][UI] member id=${member.id} mvr=${member.mvrPersonUuid} '
        'num=${member.groupMemberNumber} name="${member.name}"',
      );
    }

    // Load best images for all members
    if (_members.isNotEmpty) {
      _loadBestImages();
    }
  }

  Future<void> _loadBestImages() async {
    final imageService = ref.read(mvrImageServiceProvider);
    final lookupByMemberId = {
      for (final member in _members)
        if (member.mvrPersonUuid != null) member.id: member.mvrPersonUuid!,
    };
    final imageLookupIds = lookupByMemberId.values.toSet().toList();

    debugPrint(
      '[IG-DEBUG][UI] best-image lookup map size=${lookupByMemberId.length} '
      'members=${_members.length} uniqueLookupIds=${imageLookupIds.length}',
    );
    lookupByMemberId.forEach((memberId, lookupId) {
      debugPrint('[IG-DEBUG][UI] best-image map memberId=$memberId -> lookupId=$lookupId');
    });

    if (imageLookupIds.isEmpty) {
      if (mounted) {
        setState(() {
          _bestImages = {};
        });
      }
      return;
    }

    try {
      final imagesByLookupId = await imageService.getBestImagesForMultiple(
        imageLookupIds,
        includeMerged: true,
      );
      imagesByLookupId.forEach((lookupId, bestImage) {
        debugPrint(
          '[IG-DEBUG][UI] best-image response lookupId=$lookupId '
          'hasBestFace=${bestImage?.bestFace != null} '
          'quality=${bestImage?.bestFace?.qualityScore} '
          'video=${bestImage?.bestFace?.videoUuid}',
        );
      });
      final imagesByMemberId = {
        for (final member in _members)
          member.id: member.mvrPersonUuid != null
              ? imagesByLookupId[member.mvrPersonUuid]
              : null,
      };
      imagesByMemberId.forEach((memberId, bestImage) {
        final resolvedLookupId = lookupByMemberId[memberId] ?? 'none';
        debugPrint(
          '[IG-DEBUG][UI] member image memberId=$memberId '
          'hasBestFace=${bestImage?.bestFace != null} '
          'resolvedLookupId=$resolvedLookupId',
        );
      });
      
      if (mounted) {
        setState(() {
          _bestImages = imagesByMemberId;
        });
      }
    } catch (e, stack) {
      print('Error loading best images: $e');
    }
  }

  void _toggleSelection(String individualId) {
    setState(() {
      if (_selectedMembers.contains(individualId)) {
        _selectedMembers.remove(individualId);
        if (_selectedMembers.isEmpty) {
          _isSelectionMode = false;
        }
      } else {
        _selectedMembers.add(individualId);
        _isSelectionMode = true;
      }
    });
  }

  void _showMemberDetail(IndividualSummary member) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Member Details'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'People Profile:',
              style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12),
            ),
            const SizedBox(height: 8),
            if (member.mvrPersonUuid != null)
              PeopleProfilePicker(
                groupId: widget.groupId,
                individualId: member.mvrPersonUuid!,
                apiClient: PresenceApiClient(ref.read(apiClientProvider)),
                onChanged: () {
                  _loadGroupData();
                },
              )
            else
              const Text(
                'No MVR UUID available for this member',
                style: TextStyle(color: Colors.grey),
              ),
            const SizedBox(height: 16),
            Text(
              'ID: ${member.id}',
              style: const TextStyle(fontSize: 12),
            ),
            const SizedBox(height: 8),
            Text(
              'Appearances: ${member.totalAppearances}',
              style: const TextStyle(fontSize: 12),
            ),
            if (member.lastSeen != null) ...[
              const SizedBox(height: 8),
              Text(
                'Last seen: ${member.lastSeen}',
                style: const TextStyle(fontSize: 12),
              ),
            ],
          ],
        ),
        actions: [
          TextButton(
            onPressed: () {
              if (member.mvrPersonUuid == null) {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                    content: Text('Cannot analyse member without an MVR UUID'),
                  ),
                );
                return;
              }
              Navigator.pop(context);
              final analysisUuid = member.mvrPersonUuid!;
              
              // Generate a proper UUID for the session
              const uuid = Uuid();
              final sessionUuid = uuid.v4();
              
              // Navigate to Cross-Video Analysis for this individual
              final analysisContext = CrossVideoAnalysisContext(
                individualUuids: [analysisUuid],
                sessionUuid: sessionUuid,
                sessionData: {
                  'source': 'individual_group_member',
                  'group_id': widget.groupId,
                  'group_name': _group?.name ?? 'Unknown Group',
                  'member_name': member.name ?? 'Unnamed',
                  'individuals_found': 1,
                  'total_videos': 0,
                  'hierarchical_merge_applied': true,
                  'search_results': [], // Indicates this is MVR people, not individuals
                },
              );
              
              Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (ctx) => PersonObjectsDetailScreen(
                    crossVideoContext: analysisContext,
                  ),
                ),
              );
            },
            child: const Text('Analyse'),
          ),
          TextButton(
            onPressed: () async {
              Navigator.pop(context);
              await _removeSingleMember(member);
            },
            style: TextButton.styleFrom(foregroundColor: Colors.red),
            child: const Text('Remove'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Close'),
          ),
        ],
      ),
    );
  }

  void _selectAll() {
    setState(() {
      _selectedMembers.addAll(_members.map((m) => m.id));
      _isSelectionMode = true;
    });
  }

  void _clearSelection() {
    setState(() {
      _selectedMembers.clear();
      _isSelectionMode = false;
    });
  }

  void _navigateToCrossVideoAnalysis() {
    if (_selectedMembers.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Please select at least one member'),
        ),
      );
      return;
    }

    final analysisUuids = _members
        .where((member) => _selectedMembers.contains(member.id))
        .map((member) => member.mvrPersonUuid)
        .whereType<String>()
        .toSet()
        .toList();

    if (analysisUuids.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Selected members do not have analysis identifiers'),
        ),
      );
      return;
    }

    // Generate a proper UUID for the session
    const uuid = Uuid();
    final sessionUuid = uuid.v4();

    // Create context for cross-video analysis with selected individuals
    final analysisContext = CrossVideoAnalysisContext(
      individualUuids: analysisUuids,
      sessionUuid: sessionUuid, // Use proper UUID
      sessionData: {
        'source': 'individual_group_multi_select',
        'group_id': widget.groupId,
        'group_name': _group?.name ?? 'Unknown Group',
        'individuals_found': analysisUuids.length,
        'total_videos': 0, // No specific videos - analyzing across all appearances
        'hierarchical_merge_applied': true, // Critical: Use hierarchy endpoint
        'search_results': [], // Indicates this is MVR people, not individuals
      },
    );

    // Navigate to cross-video analysis screen
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (ctx) => PersonObjectsDetailScreen(
          crossVideoContext: analysisContext,
        ),
      ),
    );
  }

  Future<void> _removeSingleMember(IndividualSummary member) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Remove Member'),
        content: Text(
          'Remove ${member.name ?? 'this member'} from this group?',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            style: TextButton.styleFrom(foregroundColor: Colors.red),
            child: const Text('Remove'),
          ),
        ],
      ),
    );

    if (confirmed == true && mounted) {
      final response = await _apiClient.removeMembers(
        widget.groupId,
        RemoveMembersRequest(individualIds: [member.id]),
      );

      if (response.success && mounted) {
        setState(() {
          _group = response.data!.group;
          _members.removeWhere((m) => m.id == member.id);
        });

        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('${member.name ?? 'Member'} removed successfully'),
          ),
        );
      } else if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(response.error ?? 'Failed to remove member'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  void _removeSelectedMembers() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Remove Members'),
        content: Text(
          'Remove ${_selectedMembers.length} members from this group?',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            style: TextButton.styleFrom(foregroundColor: Colors.red),
            child: const Text('Remove'),
          ),
        ],
      ),
    );

    if (confirmed == true && mounted) {
      final response = await _apiClient.removeMembers(
        widget.groupId,
        RemoveMembersRequest(individualIds: _selectedMembers.toList()),
      );

      if (response.success && mounted) {
        // Update UI immediately with the new group data
        setState(() {
          _group = response.data!.group;
          _members.removeWhere((m) => _selectedMembers.contains(m.id));
        });
        
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              '${response.data!.removedCount} member(s) removed successfully',
            ),
          ),
        );
        _clearSelection();
      } else if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(response.error ?? 'Failed to remove members'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  Future<void> _showEditDialog() async {
    if (_group == null) return;

    final request = await showDialog<UpdateGroupRequest>(
      context: context,
      builder: (context) => EditGroupDialog(group: _group!),
    );

    if (request != null && mounted) {
      final response = await _apiClient.updateGroup(widget.groupId, request);
      
      if (response.success && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Group updated successfully')),
        );
        _loadGroupData();
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

  Future<void> _showCoverImageSelector() async {
    final selectedId = await showDialog<String>(
      context: context,
      builder: (context) => CoverImageSelector(
        groupId: widget.groupId,
        members: _members,
        apiClient: _apiClient,
        currentCoverIndividualId: _group?.metadata?['cover_individual_id'] as String?,
      ),
    );

    if (selectedId != null && mounted) {
      // Update group with cover image
      final request = UpdateGroupRequest(
        name: _group!.name,
        description: _group!.description,
        visibility: _group!.visibility,
        tags: _group!.tags,
        coverIndividualId: selectedId,
      );

      final response = await _apiClient.updateGroup(widget.groupId, request);
      
      if (response.success && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Cover image updated')),
        );
        _loadGroupData();
      }
    }
  }

  Future<void> _showAddMembersDialog() async {
    final individualIds = await showDialog<List<String>>(
      context: context,
      builder: (context) => AddMembersDialog(
        groupId: widget.groupId,
        apiClient: _apiClient,
      ),
    );

    if (individualIds != null && individualIds.isNotEmpty && mounted) {
      final response = await _apiClient.addMembers(
        widget.groupId,
        AddMembersRequest(
          individualIds: individualIds,
          addedBy: 'current_user', // TODO: Get from auth provider
        ),
      );
      
      if (response.success && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Added ${response.data!.addedCount} members'),
          ),
        );
        _loadGroupData();
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

  Future<void> _showDeleteDialog() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Group'),
        content: Text(
          'Are you sure you want to delete "${_group?.name}"?\n\n'
          'This action cannot be undone.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            style: TextButton.styleFrom(foregroundColor: Colors.red),
            child: const Text('Delete'),
          ),
        ],
      ),
    );

    if (confirmed == true && mounted) {
      final response = await _apiClient.deleteGroup(
        widget.groupId,
        removeMembers: false,
      );

      if (response.success && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Group deleted successfully')),
        );
        Navigator.of(context).pop();
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
      appBar: _isSelectionMode
          ? AppBar(
              title: Text('${_selectedMembers.length} selected'),
              leading: IconButton(
                icon: const Icon(Icons.close),
                onPressed: _clearSelection,
              ),
              actions: [
                IconButton(
                  icon: const Icon(Icons.select_all),
                  onPressed: _selectAll,
                  tooltip: 'Select All',
                ),
              ],
            )
          : CustomAppBar(
              title: _group?.name ?? 'Loading...',
              showBackButton: true,
              showHomeButton: true,
              actions: [
                PopupMenuButton(
                  itemBuilder: (context) => [
                    const PopupMenuItem(
                      value: 'edit',
                      child: Text('Edit Group'),
                    ),
                    const PopupMenuItem(
                      value: 'cover',
                      child: Text('Set Cover Image'),
                    ),
                    const PopupMenuItem(
                      value: 'add_members',
                      child: Text('Add Members'),
                    ),
                    const PopupMenuItem(
                      value: 'delete',
                      child: Text('Delete Group'),
              ),
            ],
            onSelected: (value) async {
              switch (value) {
                case 'edit':
                  _showEditDialog();
                  break;
                case 'cover':
                  _showCoverImageSelector();
                  break;
                case 'add_members':
                  _showAddMembersDialog();
                  break;
                case 'delete':
                  _showDeleteDialog();
                  break;
              }
            },
          ),
        ],
      ),
      body: _buildBody(),
      bottomNavigationBar: _isSelectionMode
          ? _buildSelectionToolbar()
          : null,
    );
  }

  Widget _buildBody() {
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
              onPressed: _loadGroupData,
              child: const Text('Retry'),
            ),
          ],
        ),
      );
    }

    return Column(
      children: [
        // Group info header
        _buildGroupHeader(),
        
        // Members grid
        Expanded(
          child: _members.isEmpty
              ? _buildEmptyState()
              : _buildMembersGrid(),
        ),
      ],
    );
  }

  Widget _buildGroupHeader() {
    if (_group == null) return const SizedBox.shrink();

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceVariant,
        border: Border(
          bottom: BorderSide(
            color: Theme.of(context).dividerColor,
          ),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (_group!.description != null) ...[
            Text(
              _group!.description!,
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            const SizedBox(height: 12),
          ],
          Row(
            children: [
              _buildInfoChip(
                icon: Icons.people,
                label: '${_group!.memberCount} members',
              ),
              const SizedBox(width: 8),
              _buildVisibilityChip(_group!.visibility),
              if (_group!.tags.isNotEmpty) ...[
                const SizedBox(width: 8),
                ...(_group!.tags.map((tag) => Padding(
                      padding: const EdgeInsets.only(right: 8),
                      child: Chip(
                        label: Text(tag),
                        labelStyle: const TextStyle(fontSize: 12),
                      ),
                    ))),
              ],
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildInfoChip({required IconData icon, required String label}) {
    return Chip(
      avatar: Icon(icon, size: 16),
      label: Text(label, style: const TextStyle(fontSize: 12)),
      padding: EdgeInsets.zero,
      materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
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
      materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.person_add_outlined,
            size: 96,
            color: Colors.grey[400],
          ),
          const SizedBox(height: 16),
          Text(
            'No members yet',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 8),
          Text(
            'Add individuals to this group',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: Colors.grey[600],
                ),
          ),
          const SizedBox(height: 24),
          ElevatedButton.icon(
            onPressed: () {
              // TODO: Add members dialog
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('Add members - Coming soon')),
              );
            },
            icon: const Icon(Icons.add),
            label: const Text('Add Members'),
          ),
        ],
      ),
    );
  }

  Widget _buildMembersGrid() {
    return GridView.builder(
      padding: const EdgeInsets.all(16),
      gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
        maxCrossAxisExtent: 150,
        childAspectRatio: 0.75,
        crossAxisSpacing: 12,
        mainAxisSpacing: 12,
      ),
      itemCount: _members.length,
      itemBuilder: (context, index) {
        final member = _members[index];
        final isSelected = _selectedMembers.contains(member.id);
        
        return GestureDetector(
          onTap: () {
            if (_isSelectionMode) {
              _toggleSelection(member.id);
            } else {
              _showMemberDetail(member);
            }
          },
          onLongPress: () => _toggleSelection(member.id),
          child: Container(
            decoration: BoxDecoration(
              border: Border.all(
                color: isSelected
                    ? Theme.of(context).colorScheme.primary
                    : Colors.transparent,
                width: 3,
              ),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Card(
              clipBehavior: Clip.antiAlias,
              margin: EdgeInsets.zero,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // Thumbnail - using best-image endpoint
                  Expanded(
                    child: Stack(
                      fit: StackFit.expand,
                      children: [
                        _buildMemberThumbnail(member.id),
                        
                        // Selection checkbox (always visible in top-right corner)
                        Positioned(
                          top: 4,
                          right: 4,
                          child: Container(
                            decoration: BoxDecoration(
                              color: Colors.black.withOpacity(0.5),
                              shape: BoxShape.circle,
                            ),
                            child: Icon(
                              isSelected
                                  ? Icons.check_circle
                                  : Icons.circle_outlined,
                              color: isSelected
                                  ? Theme.of(context).colorScheme.primary
                                  : Colors.white,
                              size: 24,
                            ),
                          ),
                        ),
                        
                        // Selection overlay
                        if (isSelected)
                          Container(
                            color: Theme.of(context)
                                .colorScheme
                                .primary
                                .withOpacity(0.3),
                          ),
                      ],
                    ),
                  ),
                  
                  // Info
                  Padding(
                    padding: const EdgeInsets.all(8),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          _formatGroupMemberLabel(member, index),
                          style: const TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.bold,
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                        if (member.name != null)
                          Text(
                            member.name!,
                            style: TextStyle(
                              fontSize: 9,
                              color: Colors.grey[700],
                            ),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          )
                        else
                          Text(
                            'ID: ${member.id.substring(0, 8)}...',
                            style: TextStyle(
                              fontSize: 9,
                              color: Colors.grey[700],
                            ),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                        Text(
                          '${member.totalAppearances} appearances',
                          style: TextStyle(
                            fontSize: 9,
                            color: Colors.grey[600],
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
      },
    );
  }

  Widget _buildMemberThumbnail(String memberId) {
    final bestImage = _bestImages[memberId];
    
    if (bestImage == null || bestImage.bestFace == null) {
      debugPrint('[IG-DEBUG][UI] thumbnail memberId=$memberId bestImage/bestFace missing');
      return _buildThumbnailPlaceholder();
    }

    final bestFaceImageUrl = bestImage.bestFace!.imageUrl;
    if (bestFaceImageUrl.isEmpty) {
      debugPrint('[IG-DEBUG][UI] thumbnail memberId=$memberId bestFace imageUrl empty');
      return _buildThumbnailPlaceholder();
    }

    final fallbackFrameImageUrl = bestImage.frameImage?.imageUrl;
    final fallbackVideoThumbnailUrl = '/api/v1/media/thumbnail/${bestImage.bestFace!.videoUuid}';
    final metadataFallbackUrls = bestImage.metadata.fallbackImageUrls;

    debugPrint('[IG-DEBUG][UI] thumbnail memberId=$memberId rendering direct bestFace.imageUrl');
    return _buildDirectFaceThumbnail(
      memberId,
      bestFaceImageUrl,
      fallbackImageUrls: [
        fallbackVideoThumbnailUrl,
        if (fallbackFrameImageUrl != null) fallbackFrameImageUrl,
        ...metadataFallbackUrls,
      ],
    );
  }

  Widget _buildDirectFaceThumbnail(
    String memberId,
    String imageUrl, {
    List<String> fallbackImageUrls = const [],
  }) {
    final candidates = <String>[];
    final seen = <String>{};

    void addCandidate(String? rawUrl) {
      if (rawUrl == null || rawUrl.isEmpty) {
        return;
      }
      final resolved = _resolveBestFaceImageUrl(rawUrl);
      if (seen.add(resolved)) {
        candidates.add(resolved);
      }
    }

    final workingUrl = _workingThumbnailUrlByMember[memberId];
    addCandidate(workingUrl);
    addCandidate(imageUrl);
    for (final url in fallbackImageUrls) {
      addCandidate(url);
    }

    final filteredCandidates = candidates.where((url) => !_failedThumbnailUrls.contains(url)).toList();
    final uncappedCandidates = filteredCandidates.isNotEmpty ? filteredCandidates : candidates;
    final effectiveCandidates = uncappedCandidates.take(6).toList();

    if (effectiveCandidates.isEmpty) {
      return _buildThumbnailPlaceholder();
    }

    debugPrint('[IG-DEBUG][UI] direct thumbnail candidates=${effectiveCandidates.length} first=${effectiveCandidates.first}');
    return _buildNetworkImageWithFallback(memberId, effectiveCandidates, 0);
  }

  Widget _buildNetworkImageWithFallback(String memberId, List<String> candidates, int index) {
    final apiClient = ref.read(apiClientProvider);
    if (index >= candidates.length) {
      debugPrint('[IG-DEBUG][UI] all thumbnail candidates exhausted');
      return _buildThumbnailPlaceholder();
    }

    final url = candidates[index];
    return Image.network(
      url,
      fit: BoxFit.cover,
      headers: apiClient.authToken != null
          ? {'Authorization': 'Bearer ${apiClient.authToken}'}
          : const {},
      frameBuilder: (context, child, frame, wasSynchronouslyLoaded) {
        if (frame != null && _workingThumbnailUrlByMember[memberId] != url) {
          WidgetsBinding.instance.addPostFrameCallback((_) {
            if (!mounted) return;
            setState(() {
              _workingThumbnailUrlByMember[memberId] = url;
            });
          });
        }
        return child;
      },
      loadingBuilder: (context, child, loadingProgress) {
        if (loadingProgress == null) {
          return child;
        }
        return Container(
          color: Colors.grey[300],
          child: Center(
            child: SizedBox(
              width: 20,
              height: 20,
              child: CircularProgressIndicator(strokeWidth: 2),
            ),
          ),
        );
      },
      errorBuilder: (context, error, stackTrace) {
        _failedThumbnailUrls.add(url);
        if (index == 0) {
          debugPrint('[IG-DEBUG][UI] thumbnail primary candidate failed memberId=$memberId url=$url error=$error');
        }
        return _buildNetworkImageWithFallback(memberId, candidates, index + 1);
      },
    );
  }

  String _resolveBestFaceImageUrl(String imageUrl) {
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

  /// Build cropped face image asynchronously - EXACT copy from preview screen
  Future<Widget> _buildCroppedFaceImageAsync(Map<String, dynamic> faceData, String videoUuid) async {
    try {
      final frameNumber = faceData['frame_number'] ?? 0;
      final bbox = faceData['bbox'] as List<dynamic>?;
      
      // Create unique cache key to avoid repeated calculations
      final cacheKey = 'frame_${frameNumber}_bbox_${bbox?.join('_')}';
      
      // Only print debug info once per unique face
      final shouldDebug = !_debuggedFaces.contains(cacheKey);
      if (shouldDebug) {
        _debuggedFaces.add(cacheKey);
      }
      
      // Check if bbox is available and valid
      if (bbox == null || bbox.length < 4) {
        // Fallback to showing the full frame image
        final frameUrl = '${Config.gatewayServiceUrl}/api/v1/media/$videoUuid/frame/$frameNumber?format=jpeg';
        return _buildAuthenticatedFrameImageWidget(
          frameUrl,
          fit: BoxFit.cover,
        );
      }
      
      // Extract bounding box coordinates
      final x = bbox[0].toDouble();
      final y = bbox[1].toDouble();
      final x2 = bbox[2].toDouble();
      final y2 = bbox[3].toDouble();
      final width = x2 - x;
      final height = y2 - y;
      
      // Expand the crop area to get 250x250 from original 100x100
      final areaMultiplier = 6.25; // 250x250 = 62,500 px² vs 100x100 = 10,000 px²
      final scaleFactor = math.sqrt(areaMultiplier); // Scale factor for dimensions
      final expandedWidth = width * scaleFactor;
      final expandedHeight = height * scaleFactor;
      
      final widthExpansion = expandedWidth - width;
      final heightExpansion = expandedHeight - height;
      
      final expandedX = x - (widthExpansion / 2);
      final expandedY = y - (heightExpansion / 2);
      
      // Validate expanded bounding box dimensions
      if (expandedWidth <= 0 || expandedHeight <= 0) {
        final frameUrl = '${Config.gatewayServiceUrl}/api/v1/media/$videoUuid/frame/$frameNumber?format=jpeg';
        return _buildAuthenticatedFrameImageWidget(
          frameUrl,
          fit: BoxFit.cover,
        );
      }
      
      // Get the full frame image first
      final frameUrl = '${Config.gatewayServiceUrl}/api/v1/media/$videoUuid/frame/$frameNumber?format=jpeg';
      
      // For now, return the full frame and crop it in Flutter since backend doesn't support cropping
      return FutureBuilder<ui.Image>(
        future: _loadNetworkImage(frameUrl),
        builder: (context, snapshot) {
          if (snapshot.hasData && snapshot.data != null) {
            return SizedBox(
              width: expandedWidth,
              height: expandedHeight,
              child: CustomPaint(
                painter: CroppedImagePainter(
                  image: snapshot.data!,
                  cropRect: Rect.fromLTWH(expandedX, expandedY, expandedWidth, expandedHeight),
                ),
                size: Size(expandedWidth, expandedHeight),
              ),
            );
          } else if (snapshot.hasError) {
            return _buildAuthenticatedFrameImageWidget(
              frameUrl,
              fit: BoxFit.cover,
            );
          } else {
            return Container(
              color: Colors.grey[300],
              child: Center(
                child: CircularProgressIndicator(strokeWidth: 2),
              ),
            );
          }
        },
      );
    } catch (e) {
      return Container(
        color: Colors.grey[300],
        child: Icon(Icons.error, size: 24, color: Colors.red),
      );
    }
  }

  /// Load network image and return ui.Image for cropping
  Future<ui.Image> _loadNetworkImage(String url) async {
    try {
      final bytes = await _fetchAuthenticatedFrameBytes(url);
      if (bytes == null || bytes.isEmpty) {
        throw Exception('Empty frame bytes');
      }

      final codec = await ui.instantiateImageCodec(bytes);
      final frame = await codec.getNextFrame();
      return frame.image;
    } catch (e) {
      throw Exception('Failed to load image: $e');
    }
  }

  Future<Uint8List?> _fetchAuthenticatedFrameBytes(String url) async {
    try {
      final apiClient = ref.read(apiClientProvider);
      final headers = <String, String>{};
      if (apiClient.authToken != null && apiClient.authToken!.isNotEmpty) {
        headers['Authorization'] = 'Bearer ${apiClient.authToken}';
      }

      final response = await apiClient.dio.get<List<int>>(
        url,
        options: dio.Options(
          responseType: dio.ResponseType.bytes,
          headers: headers,
        ),
      );

      final bytes = response.data;
      if (bytes == null || bytes.isEmpty) {
        return null;
      }
      return Uint8List.fromList(bytes);
    } catch (e) {
      debugPrint('[IG-DEBUG][UI] authenticated frame fetch failed url=$url error=$e');
      return null;
    }
  }

  Widget _buildAuthenticatedFrameImageWidget(
    String frameUrl, {
    BoxFit fit = BoxFit.cover,
  }) {
    return FutureBuilder<Uint8List?>(
      future: _fetchAuthenticatedFrameBytes(frameUrl),
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return Container(
            color: Colors.grey[300],
            child: Center(
              child: SizedBox(
                width: 20,
                height: 20,
                child: CircularProgressIndicator(strokeWidth: 2),
              ),
            ),
          );
        }

        final bytes = snapshot.data;
        if (bytes == null || bytes.isEmpty) {
          return Container(
            color: Colors.grey[300],
            child: Icon(Icons.broken_image, size: 24, color: Colors.grey[600]),
          );
        }

        return Image.memory(
          bytes,
          fit: fit,
          gaplessPlayback: true,
        );
      },
    );
  }

  Widget _buildThumbnailPlaceholder() {
    return Container(
      color: Colors.grey[300],
      child: const Center(
        child: Icon(Icons.person, size: 48, color: Colors.grey),
      ),
    );
  }

  Widget _buildSelectionToolbar() {
    return BottomAppBar(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        child: Row(
          children: [
            Text(
              '${_selectedMembers.length} selected',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const Spacer(),
            TextButton.icon(
              onPressed: _removeSelectedMembers,
              icon: const Icon(Icons.remove_circle_outline, color: Colors.red),
              label: const Text('Remove', style: TextStyle(color: Colors.red)),
            ),
            const SizedBox(width: 8),
            ElevatedButton.icon(
              onPressed: _navigateToCrossVideoAnalysis,
              icon: const Icon(Icons.analytics),
              label: const Text('Analyze'),
            ),
          ],
        ),
      ),
    );
  }
}

/// Custom painter to crop image to face bounding box - EXACT copy from preview screen
class CroppedImagePainter extends CustomPainter {
  final ui.Image image;
  final Rect cropRect;
  static String? _lastDebugInfo; // Static variable to reduce debug spam
  static Size? _lastSignificantSize; // Track significant canvas size changes

  CroppedImagePainter({required this.image, required this.cropRect});

  @override
  void paint(Canvas canvas, Size size) {
    final Paint paint = Paint();
    
    // Much more aggressive debug reduction - only print for significant canvas size changes
    final isSignificantChange = _lastSignificantSize == null || 
        (size.width - _lastSignificantSize!.width).abs() > 20 ||
        (size.height - _lastSignificantSize!.height).abs() > 20;
        
      if (isSignificantChange) {
        _lastSignificantSize = size;
      }
    
    // MAINTAIN ASPECT RATIO: Don't stretch the square crop into different canvas proportions
    final cropAspectRatio = cropRect.width / cropRect.height;
    final canvasAspectRatio = size.width / size.height;
    
    late Rect destRect;
    
    if (cropAspectRatio > canvasAspectRatio) {
      // Crop is wider than canvas - fit width, center vertically
      final destHeight = size.width / cropAspectRatio;
      final offsetY = (size.height - destHeight) / 2;
      destRect = Rect.fromLTWH(0, offsetY, size.width, destHeight);
    } else {
      // Crop is taller than canvas - fit height, center horizontally  
      final destWidth = size.height * cropAspectRatio;
      final offsetX = (size.width - destWidth) / 2;
      destRect = Rect.fromLTWH(offsetX, 0, destWidth, size.height);
    }
    
    // Draw with proper aspect ratio (no stretching)
    canvas.drawImageRect(
      image,
      cropRect, // Source: expanded face area
      destRect,  // Destination: properly scaled to fit canvas without stretching
      paint,
    );
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
