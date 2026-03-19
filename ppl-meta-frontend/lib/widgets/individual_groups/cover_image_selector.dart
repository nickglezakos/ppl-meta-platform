/// Cover Image Selector Widget
/// Allows selecting a cover image for a group from member thumbnails
library;

import 'package:flutter/material.dart';
import '../../models/individual_group_models.dart';
import '../../services/individual_groups_api_client.dart';

class CoverImageSelector extends StatefulWidget {
  final String groupId;
  final List<IndividualSummary> members;
  final IndividualGroupsApiClient apiClient;
  final String? currentCoverIndividualId;

  const CoverImageSelector({
    super.key,
    required this.groupId,
    required this.members,
    required this.apiClient,
    this.currentCoverIndividualId,
  });

  @override
  State<CoverImageSelector> createState() => _CoverImageSelectorState();
}

class _CoverImageSelectorState extends State<CoverImageSelector> {
  String? _selectedIndividualId;

  @override
  void initState() {
    super.initState();
    _selectedIndividualId = widget.currentCoverIndividualId;
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      child: Container(
        width: 600,
        height: 700,
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header
            Row(
              children: [
                const Icon(Icons.image, size: 28),
                const SizedBox(width: 12),
                Text(
                  'Select Cover Image',
                  style: Theme.of(context).textTheme.headlineSmall,
                ),
                const Spacer(),
                IconButton(
                  icon: const Icon(Icons.close),
                  onPressed: () => Navigator.of(context).pop(),
                ),
              ],
            ),
            const SizedBox(height: 16),

            Text(
              'Choose a member thumbnail as the group cover',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            const SizedBox(height: 16),

            // Members grid
            Expanded(
              child: widget.members.isEmpty
                  ? _buildEmptyState()
                  : _buildMembersGrid(),
            ),

            // Action buttons
            const SizedBox(height: 16),
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                if (_selectedIndividualId != null) ...[
                  TextButton(
                    onPressed: () {
                      setState(() => _selectedIndividualId = null);
                    },
                    child: const Text('Clear'),
                  ),
                  const SizedBox(width: 12),
                ],
                TextButton(
                  onPressed: () => Navigator.of(context).pop(),
                  child: const Text('Cancel'),
                ),
                const SizedBox(width: 12),
                FilledButton(
                  onPressed: () => Navigator.of(context).pop(_selectedIndividualId),
                  child: const Text('Save'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Icons.person_off_outlined, size: 64),
          const SizedBox(height: 16),
          Text(
            'No members available',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 8),
          Text(
            'Add members to select a cover image',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
        ],
      ),
    );
  }

  Widget _buildMembersGrid() {
    return GridView.builder(
      gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
        maxCrossAxisExtent: 150,
        childAspectRatio: 0.8,
        crossAxisSpacing: 12,
        mainAxisSpacing: 12,
      ),
      itemCount: widget.members.length,
      itemBuilder: (context, index) {
        final member = widget.members[index];
        final isSelected = _selectedIndividualId == member.id;

        return GestureDetector(
          onTap: () {
            setState(() {
              _selectedIndividualId = member.id;
            });
          },
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
                  // Thumbnail
                  Expanded(
                    child: Stack(
                      fit: StackFit.expand,
                      children: [
                        member.thumbnailUrl != null
                            ? Image.network(
                                widget.apiClient.getThumbnailUrl(
                                  member.id,
                                  size: 'medium',
                                ),
                                fit: BoxFit.cover,
                                errorBuilder: (context, error, stackTrace) =>
                                    _buildPlaceholder(),
                              )
                            : _buildPlaceholder(),
                        
                        // Selection indicator
                        if (isSelected)
                          Positioned(
                            top: 8,
                            right: 8,
                            child: Container(
                              padding: const EdgeInsets.all(4),
                              decoration: BoxDecoration(
                                color: Theme.of(context).colorScheme.primary,
                                shape: BoxShape.circle,
                              ),
                              child: const Icon(
                                Icons.check,
                                color: Colors.white,
                                size: 20,
                              ),
                            ),
                          ),
                      ],
                    ),
                  ),
                  
                  // Info
                  Padding(
                    padding: const EdgeInsets.all(8),
                    child: Text(
                      '${member.totalAppearances} appearances',
                      style: const TextStyle(fontSize: 10),
                      textAlign: TextAlign.center,
                      maxLines: 1,
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

  Widget _buildPlaceholder() {
    return Container(
      color: Colors.grey[300],
      child: const Center(
        child: Icon(Icons.person, size: 48, color: Colors.grey),
      ),
    );
  }
}
