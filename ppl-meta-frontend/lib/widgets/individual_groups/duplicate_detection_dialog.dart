/// Duplicate Detection Dialog
/// Shows potential duplicate members and allows user to merge or add anyway
library;

import 'package:flutter/material.dart';
import '../../models/individual_group_models.dart';
import '../mvr_face_thumbnail.dart';

/// Dialog shown when duplicate members are detected
class DuplicateDetectionDialog extends StatelessWidget {
  final CheckDuplicatesResponse duplicateResponse;
  final String? candidateName;
  final String? candidateThumbnailUrl;
  final VoidCallback onAddAnyway;
  final Function(DuplicateMatch) onMerge;

  const DuplicateDetectionDialog({
    super.key,
    required this.duplicateResponse,
    this.candidateName,
    this.candidateThumbnailUrl,
    required this.onAddAnyway,
    required this.onMerge,
  });

  Color _getConfidenceColor(String confidence) {
    switch (confidence.toLowerCase()) {
      case 'high':
        return Colors.red[700]!;
      case 'medium':
        return Colors.orange[700]!;
      case 'low':
        return Colors.yellow[700]!;
      default:
        return Colors.grey[700]!;
    }
  }

  IconData _getConfidenceIcon(String confidence) {
    switch (confidence.toLowerCase()) {
      case 'high':
        return Icons.warning_rounded;
      case 'medium':
        return Icons.info_outline;
      case 'low':
        return Icons.help_outline;
      default:
        return Icons.circle;
    }
  }

  String _getConfidenceDescription(String confidence) {
    switch (confidence.toLowerCase()) {
      case 'high':
        return 'Very likely the same person';
      case 'medium':
        return 'Possibly the same person';
      case 'low':
        return 'May be the same person';
      default:
        return 'Unknown confidence';
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final matches = duplicateResponse.matches;

    return Dialog(
      child: Container(
        width: 650,
        constraints: const BoxConstraints(maxHeight: 700),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Header
            Container(
              padding: const EdgeInsets.all(24),
              decoration: BoxDecoration(
                color: Colors.orange[50],
                border: Border(
                  bottom: BorderSide(color: Colors.orange[200]!),
                ),
              ),
              child: Row(
                children: [
                  Icon(
                    Icons.warning_rounded,
                    color: Colors.orange[700],
                    size: 28,
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Potential Duplicate Detected',
                          style: theme.textTheme.titleLarge?.copyWith(
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          'This person looks similar to ${matches.length} existing member${matches.length > 1 ? 's' : ''}',
                          style: theme.textTheme.bodyMedium?.copyWith(
                            color: Colors.grey[700],
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),

            // Candidate section
            Padding(
              padding: const EdgeInsets.all(24),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Adding:',
                    style: theme.textTheme.titleSmall?.copyWith(
                      color: Colors.grey[600],
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      MVRFaceThumbnail(
                        imageUrl: candidateThumbnailUrl,
                        radius: 40,
                        showQualityBadge: false,
                      ),
                      const SizedBox(width: 16),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              candidateName ?? 'Unnamed Individual',
                              style: theme.textTheme.titleMedium?.copyWith(
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              'ID: ${duplicateResponse.candidateId.substring(0, 8)}...',
                              style: theme.textTheme.bodySmall?.copyWith(
                                color: Colors.grey[600],
                                fontFamily: 'monospace',
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),

            const Divider(height: 1),

            // Matches list
            Flexible(
              child: ListView.separated(
                shrinkWrap: true,
                padding: const EdgeInsets.all(24),
                itemCount: matches.length,
                separatorBuilder: (context, index) => const SizedBox(height: 16),
                itemBuilder: (context, index) {
                  final match = matches[index];
                  return _buildMatchCard(context, match);
                },
              ),
            ),

            // Footer with actions
            Container(
              padding: const EdgeInsets.all(24),
              decoration: BoxDecoration(
                color: Colors.grey[50],
                border: Border(
                  top: BorderSide(color: Colors.grey[200]!),
                ),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  TextButton(
                    onPressed: () => Navigator.of(context).pop(),
                    child: const Text('Cancel'),
                  ),
                  const SizedBox(width: 12),
                  OutlinedButton.icon(
                    onPressed: () {
                      Navigator.of(context).pop();
                      onAddAnyway();
                    },
                    icon: const Icon(Icons.person_add),
                    label: const Text('Add Anyway'),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildMatchCard(BuildContext context, DuplicateMatch match) {
    final theme = Theme.of(context);
    final confidenceColor = _getConfidenceColor(match.confidence);
    final confidenceIcon = _getConfidenceIcon(match.confidence);
    final confidenceDesc = _getConfidenceDescription(match.confidence);

    return Container(
      decoration: BoxDecoration(
        border: Border.all(color: confidenceColor.withOpacity(0.3)),
        borderRadius: BorderRadius.circular(12),
        color: confidenceColor.withOpacity(0.05),
      ),
      child: Column(
        children: [
          // Match info
          Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              children: [
                // Thumbnail
                MVRFaceThumbnail(
                  imageUrl: match.thumbnailUrl,
                  radius: 40,
                  showQualityBadge: false,
                ),
                const SizedBox(width: 16),

                // Details
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Expanded(
                            child: Text(
                              match.memberName ?? 'Unnamed Member',
                              style: theme.textTheme.titleMedium?.copyWith(
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ),
                          // Confidence badge
                          Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 10,
                              vertical: 4,
                            ),
                            decoration: BoxDecoration(
                              color: confidenceColor.withOpacity(0.15),
                              borderRadius: BorderRadius.circular(12),
                              border: Border.all(
                                color: confidenceColor.withOpacity(0.3),
                              ),
                            ),
                            child: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Icon(
                                  confidenceIcon,
                                  size: 14,
                                  color: confidenceColor,
                                ),
                                const SizedBox(width: 4),
                                Text(
                                  '${match.confidence.toUpperCase()}',
                                  style: theme.textTheme.labelSmall?.copyWith(
                                    color: confidenceColor,
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 6),
                      Text(
                        confidenceDesc,
                        style: theme.textTheme.bodySmall?.copyWith(
                          color: Colors.grey[600],
                        ),
                      ),
                      const SizedBox(height: 8),
                      Row(
                        children: [
                          Icon(
                            Icons.percent,
                            size: 14,
                            color: Colors.grey[600],
                          ),
                          const SizedBox(width: 4),
                          Text(
                            'Similarity: ${(match.similarity * 100).toStringAsFixed(1)}%',
                            style: theme.textTheme.bodySmall?.copyWith(
                              color: Colors.grey[700],
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                          const SizedBox(width: 16),
                          Icon(
                            Icons.badge,
                            size: 14,
                            color: Colors.grey[600],
                          ),
                          const SizedBox(width: 4),
                          Expanded(
                            child: Text(
                              'ID: ${match.memberId.substring(0, 8)}...',
                              style: theme.textTheme.bodySmall?.copyWith(
                                color: Colors.grey[600],
                                fontFamily: 'monospace',
                              ),
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),

          // Merge button
          Container(
            decoration: BoxDecoration(
              border: Border(
                top: BorderSide(color: confidenceColor.withOpacity(0.2)),
              ),
              color: Colors.white,
              borderRadius: const BorderRadius.only(
                bottomLeft: Radius.circular(12),
                bottomRight: Radius.circular(12),
              ),
            ),
            child: Material(
              color: Colors.transparent,
              child: InkWell(
                borderRadius: const BorderRadius.only(
                  bottomLeft: Radius.circular(12),
                  bottomRight: Radius.circular(12),
                ),
                onTap: () {
                  Navigator.of(context).pop();
                  onMerge(match);
                },
                child: Padding(
                  padding: const EdgeInsets.symmetric(vertical: 12),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(
                        Icons.merge_type,
                        size: 18,
                        color: confidenceColor,
                      ),
                      const SizedBox(width: 8),
                      Text(
                        'Merge with this member',
                        style: theme.textTheme.labelLarge?.copyWith(
                          color: confidenceColor,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
