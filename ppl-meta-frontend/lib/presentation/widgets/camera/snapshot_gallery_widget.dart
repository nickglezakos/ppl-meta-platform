import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/models/snapshot_result.dart';
import '../../../core/services/snapshot_storage_service.dart';
import 'snapshot_preview_dialog.dart';
import 'dart:convert';
import 'dart:typed_data';

/// Local snapshot gallery widget for Phase 1
class SnapshotGalleryWidget extends ConsumerStatefulWidget {
  final String? cameraId; // Filter by camera if provided
  final bool showLocalOnly; // Phase 1 vs Phase 2 flag
  final int maxDisplayCount; // Limit for performance
  final bool showTitle;

  const SnapshotGalleryWidget({
    super.key,
    this.cameraId,
    this.showLocalOnly = true, // Phase 1 default
    this.maxDisplayCount = 50,
    this.showTitle = true,
  });

  @override
  ConsumerState<SnapshotGalleryWidget> createState() => _SnapshotGalleryWidgetState();
}

class _SnapshotGalleryWidgetState extends ConsumerState<SnapshotGalleryWidget> {
  final SnapshotStorageService _storageService = SnapshotStorageService();
  List<SnapshotResult> _snapshots = [];
  bool _isLoading = true;
  String _searchQuery = '';
  TextEditingController _searchController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _loadSnapshots();
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> loadSnapshots() async {
    setState(() {
      _isLoading = true;
    });

    try {
      List<SnapshotResult> snapshots;
      
      if (_searchQuery.isNotEmpty) {
        snapshots = await _storageService.searchSnapshots(_searchQuery);
        debugPrint('🔍 Loaded ${snapshots.length} snapshots for search: $_searchQuery');
      } else if (widget.cameraId != null) {
        snapshots = await _storageService.getSnapshotsByCamera(widget.cameraId!);
        debugPrint('📷 Loaded ${snapshots.length} snapshots for camera: ${widget.cameraId}');
      } else {
        snapshots = await _storageService.getSnapshots();
        debugPrint('📸 Loaded ${snapshots.length} total snapshots');
      }

      // Limit display count for performance
      if (snapshots.length > widget.maxDisplayCount) {
        snapshots = snapshots.take(widget.maxDisplayCount).toList();
        debugPrint('📊 Limited to ${snapshots.length} snapshots for display');
      }

      setState(() {
        _snapshots = snapshots;
        _isLoading = false;
      });
      
      debugPrint('✅ Snapshot loading complete. Showing ${_snapshots.length} snapshots');
    } catch (e) {
      debugPrint('❌ Error loading snapshots: $e');
      setState(() {
        _isLoading = false;
      });
    }
  }

  Future<void> _loadSnapshots() async {
    return loadSnapshots();
  }

  Future<void> _deleteSnapshot(SnapshotResult snapshot) async {
    final success = await _storageService.deleteSnapshot(snapshot);
    
    if (success) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Snapshot deleted successfully'),
          backgroundColor: Colors.green,
        ),
      );
      _loadSnapshots(); // Refresh the list
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Failed to delete snapshot'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  void _showSnapshotPreview(SnapshotResult snapshot) {
    showDialog(
      context: context,
      barrierDismissible: true,
      builder: (context) => SnapshotPreviewDialog(
        snapshot: snapshot,
        onDelete: () => _deleteSnapshot(snapshot),
        onShare: () {
          // Phase 2 functionality
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Share functionality coming in Phase 2'),
              backgroundColor: Colors.orange,
            ),
          );
        },
      ),
    );
  }

  Future<void> _clearAllSnapshots() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Clear All Snapshots'),
        content: Text(
          widget.cameraId != null
              ? 'Delete all snapshots for this camera?'
              : 'Delete all snapshots? This cannot be undone.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.of(context).pop(true),
            style: TextButton.styleFrom(foregroundColor: Colors.red),
            child: const Text('Delete All'),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      bool success;
      if (widget.cameraId != null) {
        success = await _storageService.deleteSnapshotsForCamera(widget.cameraId!);
      } else {
        success = await _storageService.clearAllSnapshots();
      }

      if (success) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Snapshots cleared successfully'),
            backgroundColor: Colors.green,
          ),
        );
        _loadSnapshots();
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Failed to clear snapshots'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Title and controls
        if (widget.showTitle) _buildHeader(theme),

        // Content
        Expanded(
          child: _isLoading ? _buildLoadingState() : _buildGalleryContent(theme),
        ),
      ],
    );
  }

  Widget _buildHeader(ThemeData theme) {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                Icons.photo_library,
                color: theme.primaryColor,
              ),
              const SizedBox(width: 8),
              Text(
                widget.cameraId != null 
                    ? 'Camera Snapshots' 
                    : 'Snapshot Gallery',
                style: theme.textTheme.headlineSmall?.copyWith(
                  fontWeight: FontWeight.w600,
                ),
              ),
              const Spacer(),
              if (_snapshots.isNotEmpty)
                PopupMenuButton<String>(
                  icon: const Icon(Icons.more_vert),
                  onSelected: (value) {
                    switch (value) {
                      case 'clear':
                        _clearAllSnapshots();
                        break;
                      case 'refresh':
                        _loadSnapshots();
                        break;
                    }
                  },
                  itemBuilder: (context) => [
                    const PopupMenuItem(
                      value: 'refresh',
                      child: Row(
                        children: [
                          Icon(Icons.refresh),
                          SizedBox(width: 8),
                          Text('Refresh'),
                        ],
                      ),
                    ),
                    const PopupMenuItem(
                      value: 'clear',
                      child: Row(
                        children: [
                          Icon(Icons.clear_all, color: Colors.red),
                          SizedBox(width: 8),
                          Text('Clear All'),
                        ],
                      ),
                    ),
                  ],
                ),
            ],
          ),
          
          // Search bar
          const SizedBox(height: 12),
          TextField(
            controller: _searchController,
            decoration: InputDecoration(
              hintText: 'Search snapshots...',
              prefixIcon: const Icon(Icons.search),
              suffixIcon: _searchQuery.isNotEmpty
                  ? IconButton(
                      icon: const Icon(Icons.clear),
                      onPressed: () {
                        _searchController.clear();
                        setState(() {
                          _searchQuery = '';
                        });
                        _loadSnapshots();
                      },
                    )
                  : null,
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(12),
              ),
              contentPadding: const EdgeInsets.symmetric(
                horizontal: 16,
                vertical: 12,
              ),
            ),
            onChanged: (value) {
              setState(() {
                _searchQuery = value;
              });
              _loadSnapshots();
            },
          ),
        ],
      ),
    );
  }

  Widget _buildLoadingState() {
    return const Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          CircularProgressIndicator(),
          SizedBox(height: 16),
          Text('Loading snapshots...'),
        ],
      ),
    );
  }

  Widget _buildGalleryContent(ThemeData theme) {
    if (_snapshots.isEmpty) {
      return _buildEmptyState(theme);
    }

    return RefreshIndicator(
      onRefresh: _loadSnapshots,
      child: GridView.builder(
        padding: const EdgeInsets.all(16),
        gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
          crossAxisCount: 3,
          crossAxisSpacing: 8,
          mainAxisSpacing: 8,
          childAspectRatio: 1.0,
        ),
        itemCount: _snapshots.length,
        itemBuilder: (context, index) {
          final snapshot = _snapshots[index];
          return _buildSnapshotTile(snapshot, theme);
        },
      ),
    );
  }

  Widget _buildEmptyState(ThemeData theme) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.photo_library_outlined,
            size: 64,
            color: Colors.grey.shade400,
          ),
          const SizedBox(height: 16),
          Text(
            widget.cameraId != null
                ? 'No snapshots for this camera'
                : 'No snapshots yet',
            style: theme.textTheme.titleMedium?.copyWith(
              color: Colors.grey.shade600,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'Start capturing snapshots to see them here',
            style: theme.textTheme.bodyMedium?.copyWith(
              color: Colors.grey.shade500,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 24),
          ElevatedButton.icon(
            onPressed: _loadSnapshots,
            icon: const Icon(Icons.refresh),
            label: const Text('Refresh'),
          ),
        ],
      ),
    );
  }

  Widget _buildSnapshotTile(SnapshotResult snapshot, ThemeData theme) {
    return GestureDetector(
      onTap: () => _showSnapshotPreview(snapshot),
      child: Container(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: Colors.grey.shade300),
        ),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(8),
          child: Stack(
            children: [
              // Snapshot image
              Container(
                width: double.infinity,
                height: double.infinity,
                child: Image.memory(
                  _getSnapshotThumbnail(snapshot),
                  fit: BoxFit.cover,
                  errorBuilder: (context, error, stackTrace) {
                    return Container(
                      color: Colors.grey.shade200,
                      child: const Center(
                        child: Icon(
                          Icons.broken_image,
                          color: Colors.grey,
                        ),
                      ),
                    );
                  },
                ),
              ),
              
              // Overlay with metadata
              Positioned(
                bottom: 0,
                left: 0,
                right: 0,
                child: Container(
                  padding: const EdgeInsets.all(6),
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      begin: Alignment.bottomCenter,
                      end: Alignment.topCenter,
                      colors: [
                        Colors.black.withOpacity(0.8),
                        Colors.transparent,
                      ],
                    ),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        snapshot.formattedCaptureTime,
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 10,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                      Text(
                        snapshot.formattedFileSize,
                        style: const TextStyle(
                          color: Colors.white70,
                          fontSize: 9,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              
              // Camera indicator for multi-camera view
              if (widget.cameraId == null)
                Positioned(
                  top: 4,
                  right: 4,
                  child: Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 4,
                      vertical: 2,
                    ),
                    decoration: BoxDecoration(
                      color: Colors.black54,
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text(
                      snapshot.deviceId.length > 8 
                          ? '${snapshot.deviceId.substring(0, 8)}...'
                          : snapshot.deviceId,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 8,
                      ),
                    ),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }

  Uint8List _getSnapshotThumbnail(SnapshotResult snapshot) {
    try {
      // Use the imageBytes getter which handles data URL extraction
      return snapshot.imageBytes;
    } catch (e) {
      debugPrint('Error decoding snapshot thumbnail: $e');
      return Uint8List(0);
    }
  }
}
