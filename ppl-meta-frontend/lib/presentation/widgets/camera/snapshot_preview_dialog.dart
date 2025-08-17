import 'package:flutter/material.dart';
import '../../../core/models/snapshot_result.dart';
import 'dart:convert';
import 'dart:typed_data';

/// Preview dialog for captured snapshots - Phase 1
class SnapshotPreviewDialog extends StatelessWidget {
  final SnapshotResult snapshot;
  final VoidCallback? onDelete;
  final VoidCallback? onShare;

  const SnapshotPreviewDialog({
    super.key,
    required this.snapshot,
    this.onDelete,
    this.onShare,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    
    return Dialog(
      backgroundColor: Colors.transparent,
      child: Container(
        constraints: const BoxConstraints(
          maxWidth: 600,
          maxHeight: 700,
        ),
        decoration: BoxDecoration(
          color: theme.cardColor,
          borderRadius: BorderRadius.circular(16),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.2),
              blurRadius: 20,
              spreadRadius: 5,
            ),
          ],
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Header with title and actions
            _buildHeader(context, theme),
            
            // Image display
            Expanded(
              child: _buildImageDisplay(context),
            ),
            
            // Metadata and actions
            _buildFooter(context, theme),
          ],
        ),
      ),
    );
  }

  Widget _buildHeader(BuildContext context, ThemeData theme) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: theme.primaryColor.withOpacity(0.1),
        borderRadius: const BorderRadius.only(
          topLeft: Radius.circular(16),
          topRight: Radius.circular(16),
        ),
      ),
      child: Row(
        children: [
          Icon(
            Icons.photo_camera,
            color: theme.primaryColor,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  snapshot.filename ?? 'Snapshot',
                  style: theme.textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                Text(
                  'Camera: ${snapshot.deviceId}',
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: theme.textTheme.bodySmall?.color?.withOpacity(0.7),
                  ),
                ),
              ],
            ),
          ),
          IconButton(
            icon: const Icon(Icons.close),
            onPressed: () => Navigator.of(context).pop(),
            tooltip: 'Close',
          ),
        ],
      ),
    );
  }

  Widget _buildImageDisplay(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(8),
        child: Image.memory(
          _getImageBytes(),
          fit: BoxFit.contain,
          errorBuilder: (context, error, stackTrace) {
            return Container(
              height: 200,
              decoration: BoxDecoration(
                color: Colors.grey.shade200,
                borderRadius: BorderRadius.circular(8),
              ),
              child: const Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(
                      Icons.broken_image,
                      size: 48,
                      color: Colors.grey,
                    ),
                    SizedBox(height: 8),
                    Text(
                      'Failed to load image',
                      style: TextStyle(color: Colors.grey),
                    ),
                  ],
                ),
              ),
            );
          },
        ),
      ),
    );
  }

  Widget _buildFooter(BuildContext context, ThemeData theme) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: theme.cardColor,
        borderRadius: const BorderRadius.only(
          bottomLeft: Radius.circular(16),
          bottomRight: Radius.circular(16),
        ),
      ),
      child: Column(
        children: [
          // Metadata grid
          Row(
            children: [
              Expanded(
                child: _buildMetadataItem(
                  'Captured',
                  snapshot.formattedCaptureTime,
                  Icons.access_time,
                ),
              ),
              Expanded(
                child: _buildMetadataItem(
                  'Size',
                  snapshot.formattedFileSize,
                  Icons.storage,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          
          // Additional metadata if available
          if (snapshot.metadata != null && snapshot.metadata!.isNotEmpty)
            Row(
              children: [
                if (snapshot.metadata!['resolution'] != null)
                  Expanded(
                    child: _buildMetadataItem(
                      'Resolution',
                      snapshot.metadata!['resolution'].toString(),
                      Icons.photo_size_select_actual,
                    ),
                  ),
                if (snapshot.metadata!['format'] != null)
                  Expanded(
                    child: _buildMetadataItem(
                      'Format',
                      snapshot.metadata!['format'].toString(),
                      Icons.image,
                    ),
                  ),
              ],
            ),
          
          const SizedBox(height: 16),
          
          // Action buttons
          Row(
            children: [
              if (onDelete != null)
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: () {
                      _showDeleteConfirmation(context);
                    },
                    icon: const Icon(Icons.delete_outline),
                    label: const Text('Delete'),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: Colors.red,
                      side: const BorderSide(color: Colors.red),
                    ),
                  ),
                ),
              
              if (onDelete != null && onShare != null)
                const SizedBox(width: 8),
              
              if (onShare != null)
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: onShare,
                    icon: const Icon(Icons.share),
                    label: const Text('Share'),
                  ),
                ),
              
              const SizedBox(width: 8),
              
              // Download/Save button
              Expanded(
                child: ElevatedButton.icon(
                  onPressed: () {
                    _downloadSnapshot(context);
                  },
                  icon: const Icon(Icons.download),
                  label: const Text('Download'),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildMetadataItem(String label, String value, IconData icon) {
    return Row(
      children: [
        Icon(
          icon,
          size: 16,
          color: Colors.grey.shade600,
        ),
        const SizedBox(width: 8),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                label,
                style: TextStyle(
                  fontSize: 12,
                  color: Colors.grey.shade600,
                  fontWeight: FontWeight.w500,
                ),
              ),
              Text(
                value,
                style: const TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                ),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ],
          ),
        ),
      ],
    );
  }

  void _showDeleteConfirmation(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Snapshot'),
        content: const Text(
          'Are you sure you want to delete this snapshot? This action cannot be undone.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () {
              Navigator.of(context).pop(); // Close confirmation
              Navigator.of(context).pop(); // Close preview
              onDelete?.call();
            },
            style: TextButton.styleFrom(
              foregroundColor: Colors.red,
            ),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
  }

  void _downloadSnapshot(BuildContext context) {
    // For Phase 1, show info about download functionality
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Download functionality will be available in Phase 2'),
        backgroundColor: Colors.orange,
      ),
    );
  }

  Uint8List _getImageBytes() {
    return snapshot.imageBytes;
  }
}
