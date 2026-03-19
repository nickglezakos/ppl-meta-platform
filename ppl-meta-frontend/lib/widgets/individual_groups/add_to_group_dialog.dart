/// Dialog for adding an individual to a group
/// Used in cross-video analysis screen
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../models/individual_group_models.dart';
import '../../services/individual_groups_api_client.dart';
import '../../core/api/api_client.dart';
import 'duplicate_detection_dialog.dart';

/// Dialog to select a group and add an individual to it
class AddToGroupDialog extends ConsumerStatefulWidget {
  final String individualId;
  final String? individualName;
  final String? thumbnailUrl;

  const AddToGroupDialog({
    super.key,
    required this.individualId,
    this.individualName,
    this.thumbnailUrl,
  });

  @override
  ConsumerState<AddToGroupDialog> createState() => _AddToGroupDialogState();
}

class _AddToGroupDialogState extends ConsumerState<AddToGroupDialog> {
  List<IndividualGroup> _groups = [];
  String? _selectedGroupId;
  bool _isLoading = true;
  String? _errorMessage;
  bool _isAdding = false;

  @override
  void initState() {
    super.initState();
    _loadGroups();
  }

  Future<void> _loadGroups() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    final apiClient = IndividualGroupsApiClient();
    final response = await apiClient.listGroups(limit: 100);

    if (response.success && response.data != null) {
      setState(() {
        _groups = response.data!.groups;
        _isLoading = false;
        if (_groups.isEmpty) {
          _errorMessage = 'No groups available. Create a group first.';
        }
      });
    } else {
      setState(() {
        _isLoading = false;
        _errorMessage = response.error ?? 'Failed to load groups';
      });
    }
  }

  Future<void> _addToGroup() async {
    if (_selectedGroupId == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please select a group')),
      );
      return;
    }

    setState(() => _isAdding = true);

    final apiClient = IndividualGroupsApiClient();
    
    // First, check for duplicates
    final checkResponse = await apiClient.checkDuplicates(
      _selectedGroupId!,
      CheckDuplicatesRequest(
        candidateMvrUuid: widget.individualId,
        similarityThreshold: 0.75, // Default threshold
      ),
    );

    setState(() => _isAdding = false);

    if (!checkResponse.success) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(checkResponse.error ?? 'Failed to check for duplicates'),
            backgroundColor: Colors.red,
          ),
        );
      }
      // Don't add if duplicate check failed
      return;
    }

    // If duplicates found, show dialog
    if (checkResponse.data!.hasDuplicates && checkResponse.data!.matches.isNotEmpty) {
      if (mounted) {
        Navigator.of(context).pop(); // Close add-to-group dialog
        showDialog(
          context: context,
          builder: (context) => DuplicateDetectionDialog(
            duplicateResponse: checkResponse.data!,
            candidateName: widget.individualName,
            candidateThumbnailUrl: widget.thumbnailUrl,
            onAddAnyway: () => _performAdd(),
            onMerge: (match) => _performMerge(match),
          ),
        );
      }
    } else {
      // No duplicates, proceed with add
      await _performAdd();
    }
  }

  Future<void> _performAdd() async {
    setState(() => _isAdding = true);

    final apiClient = IndividualGroupsApiClient();
    final response = await apiClient.addMembers(
      _selectedGroupId!,
      AddMembersRequest(
        individualIds: [widget.individualId],
        addedBy: 'current_user',
      ),
    );

    setState(() => _isAdding = false);

    if (response.success) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              'Added ${widget.individualName ?? "individual"} to group',
            ),
          ),
        );
        Navigator.of(context).pop(true); // Return true to indicate success
      }
    } else {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(response.error ?? 'Failed to add to group'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  Future<void> _performMerge(DuplicateMatch match) async {
    setState(() => _isAdding = true);

    final apiClient = IndividualGroupsApiClient();
    final response = await apiClient.mergeMembers(
      _selectedGroupId!,
      MergeMembersRequest(
        sourceMvrUuid: widget.individualId, // New candidate
        targetMvrUuid: match.memberId, // Existing member
        userConfirmed: true,
      ),
    );

    setState(() => _isAdding = false);

    if (response.success) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              'Merged ${widget.individualName ?? "individual"} with ${match.memberName ?? "existing member"}',
            ),
            backgroundColor: Colors.green,
          ),
        );
        Navigator.of(context).pop(true); // Return true to indicate success
      }
    } else {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(response.error ?? 'Failed to merge members'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text(
        'Add ${widget.individualName ?? "Individual"} to Group',
      ),
      content: SizedBox(
        width: double.maxFinite,
        child: _isLoading
            ? const Center(
                child: Padding(
                  padding: EdgeInsets.all(32.0),
                  child: CircularProgressIndicator(),
                ),
              )
            : _errorMessage != null
                ? Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(
                        Icons.error_outline,
                        size: 48,
                        color: Theme.of(context).colorScheme.error,
                      ),
                      const SizedBox(height: 16),
                      Text(
                        _errorMessage!,
                        textAlign: TextAlign.center,
                      ),
                    ],
                  )
                : _groups.isEmpty
                    ? Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(
                            Icons.folder_off_outlined,
                            size: 48,
                            color: Theme.of(context).colorScheme.secondary,
                          ),
                          const SizedBox(height: 16),
                          const Text(
                            'No groups available',
                            textAlign: TextAlign.center,
                          ),
                          const SizedBox(height: 8),
                          const Text(
                            'Create a group first in the Individual Groups screen',
                            textAlign: TextAlign.center,
                            style: TextStyle(fontSize: 12),
                          ),
                        ],
                      )
                    : Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const Text('Select a group:'),
                          const SizedBox(height: 16),
                          Flexible(
                            child: ListView.builder(
                              shrinkWrap: true,
                              itemCount: _groups.length,
                              itemBuilder: (context, index) {
                                final group = _groups[index];
                                return RadioListTile<String>(
                                  value: group.id,
                                  groupValue: _selectedGroupId,
                                  onChanged: (value) {
                                    setState(() => _selectedGroupId = value);
                                  },
                                  title: Text(group.name),
                                  subtitle: group.description != null
                                      ? Text(
                                          group.description!,
                                          maxLines: 1,
                                          overflow: TextOverflow.ellipsis,
                                        )
                                      : null,
                                  secondary: Column(
                                    mainAxisAlignment: MainAxisAlignment.center,
                                    children: [
                                      Icon(
                                        group.visibility == GroupVisibility.private
                                            ? Icons.lock_outline
                                            : group.visibility == GroupVisibility.shared
                                                ? Icons.people_outline
                                                : Icons.public,
                                        size: 20,
                                      ),
                                      const SizedBox(height: 4),
                                      Text(
                                        '${group.memberCount}',
                                        style: const TextStyle(fontSize: 12),
                                      ),
                                    ],
                                  ),
                                );
                              },
                            ),
                          ),
                        ],
                      ),
      ),
      actions: [
        TextButton(
          onPressed: _isAdding ? null : () => Navigator.of(context).pop(),
          child: const Text('Cancel'),
        ),
        if (_errorMessage == null && _groups.isNotEmpty)
          FilledButton(
            onPressed: _isAdding ? null : _addToGroup,
            child: _isAdding
                ? const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Text('Add'),
          ),
      ],
    );
  }
}
