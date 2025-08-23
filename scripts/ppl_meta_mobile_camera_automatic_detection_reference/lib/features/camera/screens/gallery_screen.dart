import 'dart:io';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../../core/providers/gallery_provider.dart';
import '../../../shared/models/media_item.dart';

/// Gallery screen for viewing and managing captured photos and videos
class GalleryScreen extends StatefulWidget {
  const GalleryScreen({Key? key}) : super(key: key);

  @override
  State<GalleryScreen> createState() => _GalleryScreenState();
}

class _GalleryScreenState extends State<GalleryScreen>
    with TickerProviderStateMixin {
  late TabController _tabController;
  bool _isSelectionMode = false;
  Set<String> _selectedItems = {};

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<GalleryProvider>().loadMedia();
    });
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      body: SafeArea(
        child: Column(
          children: [
            _buildAppBar(),
            _buildTabBar(),
            Expanded(
              child: TabBarView(
                controller: _tabController,
                children: [
                  _buildAllMediaTab(),
                  _buildPhotosTab(),
                  _buildVideosTab(),
                ],
              ),
            ),
          ],
        ),
      ),
      bottomNavigationBar: _isSelectionMode ? _buildSelectionActions() : null,
    );
  }

  Widget _buildAppBar() {
    return Container(
      padding: const EdgeInsets.all(16),
      child: Row(
        children: [
          IconButton(
            onPressed: () => Navigator.of(context).pop(),
            icon: const Icon(
              Icons.arrow_back,
              color: Colors.white,
            ),
          ),
          const SizedBox(width: 8),
          const Text(
            'Gallery',
            style: TextStyle(
              color: Colors.white,
              fontSize: 20,
              fontWeight: FontWeight.w600,
            ),
          ),
          const Spacer(),
          if (_isSelectionMode) ...[
            Text(
              '${_selectedItems.length} selected',
              style: const TextStyle(
                color: Colors.white70,
                fontSize: 14,
              ),
            ),
            const SizedBox(width: 16),
            TextButton(
              onPressed: _exitSelectionMode,
              child: const Text(
                'Cancel',
                style: TextStyle(
                  color: Colors.blue,
                  fontSize: 14,
                ),
              ),
            ),
          ] else ...[
            IconButton(
              onPressed: _enterSelectionMode,
              icon: const Icon(
                Icons.select_all,
                color: Colors.white,
              ),
            ),
            IconButton(
              onPressed: () {
                context.read<GalleryProvider>().loadMedia();
              },
              icon: const Icon(
                Icons.refresh,
                color: Colors.white,
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildTabBar() {
    return Container(
      decoration: BoxDecoration(
        border: Border(
          bottom: BorderSide(
            color: Colors.white.withOpacity(0.1),
            width: 1,
          ),
        ),
      ),
      child: TabBar(
        controller: _tabController,
        indicatorColor: Colors.blue,
        indicatorWeight: 2,
        labelColor: Colors.white,
        unselectedLabelColor: Colors.white54,
        tabs: const [
          Tab(text: 'All'),
          Tab(text: 'Photos'),
          Tab(text: 'Videos'),
        ],
      ),
    );
  }

  Widget _buildAllMediaTab() {
    return Consumer<GalleryProvider>(
      builder: (context, galleryProvider, child) {
        if (galleryProvider.isLoading) {
          return const Center(
            child: CircularProgressIndicator(),
          );
        }

        if (galleryProvider.error != null) {
          return _buildErrorState(galleryProvider.error!);
        }

        final allMedia = galleryProvider.allMedia;
        if (allMedia.isEmpty) {
          return _buildEmptyState('No media found', 'Start capturing photos and videos');
        }

        return _buildMediaGrid(allMedia);
      },
    );
  }

  Widget _buildPhotosTab() {
    return Consumer<GalleryProvider>(
      builder: (context, galleryProvider, child) {
        if (galleryProvider.isLoading) {
          return const Center(
            child: CircularProgressIndicator(),
          );
        }

        final photos = galleryProvider.photos;
        if (photos.isEmpty) {
          return _buildEmptyState('No photos found', 'Capture your first photo');
        }

        return _buildMediaGrid(photos);
      },
    );
  }

  Widget _buildVideosTab() {
    return Consumer<GalleryProvider>(
      builder: (context, galleryProvider, child) {
        if (galleryProvider.isLoading) {
          return const Center(
            child: CircularProgressIndicator(),
          );
        }

        final videos = galleryProvider.videos;
        if (videos.isEmpty) {
          return _buildEmptyState('No videos found', 'Record your first video');
        }

        return _buildMediaGrid(videos);
      },
    );
  }

  Widget _buildMediaGrid(List<MediaItem> items) {
    return GridView.builder(
      padding: const EdgeInsets.all(8),
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 3,
        crossAxisSpacing: 4,
        mainAxisSpacing: 4,
        childAspectRatio: 1,
      ),
      itemCount: items.length,
      itemBuilder: (context, index) {
        final item = items[index];
        return _buildMediaTile(item);
      },
    );
  }

  Widget _buildMediaTile(MediaItem item) {
    final isSelected = _selectedItems.contains(item.id);

    return GestureDetector(
      onTap: () => _handleTileTap(item),
      onLongPress: () => _handleTileLongPress(item),
      child: Stack(
        children: [
          Container(
            decoration: BoxDecoration(
              color: Colors.grey[900],
              borderRadius: BorderRadius.circular(8),
              border: isSelected
                  ? Border.all(color: Colors.blue, width: 3)
                  : null,
            ),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(8),
              child: Stack(
                fit: StackFit.expand,
                children: [
                  // Thumbnail - Use local file for captured photos
                  _buildThumbnailImage(item),

                  // Video duration overlay
                  if (item.type == MediaType.video)
                    Positioned(
                      bottom: 4,
                      right: 4,
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 6,
                          vertical: 2,
                        ),
                        decoration: BoxDecoration(
                          color: Colors.black.withOpacity(0.7),
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: Text(
                          _formatDuration(item.duration ?? 0),
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 10,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ),
                    ),

                  // Selection overlay
                  if (_isSelectionMode)
                    Container(
                      decoration: BoxDecoration(
                        color: isSelected
                            ? Colors.blue.withOpacity(0.3)
                            : Colors.black.withOpacity(0.3),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Center(
                        child: Icon(
                          isSelected
                              ? Icons.check_circle
                              : Icons.radio_button_unchecked,
                          color: isSelected ? Colors.blue : Colors.white,
                          size: 30,
                        ),
                      ),
                    ),
                ],
              ),
            ),
          ),

          // Video indicator
          if (item.type == MediaType.video && !_isSelectionMode)
            const Positioned(
              top: 4,
              left: 4,
              child: Icon(
                Icons.play_circle_filled,
                color: Colors.white,
                size: 20,
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildThumbnailImage(MediaItem item) {
    // For local files (captured photos), use File instead of network
    final file = File(item.path);
    
    if (file.existsSync()) {
      return Image.file(
        file,
        fit: BoxFit.cover,
        errorBuilder: (context, error, stackTrace) {
          print('❌ Error loading image from ${item.path}: $error');
          return _buildThumbnailPlaceholder(item);
        },
      );
    } else {
      // Fallback to network image if thumbnailPath is provided
      if (item.thumbnailPath != null) {
        return Image.network(
          item.thumbnailPath!,
          fit: BoxFit.cover,
          errorBuilder: (context, error, stackTrace) {
            print('❌ Error loading thumbnail from ${item.thumbnailPath}: $error');
            return _buildThumbnailPlaceholder(item);
          },
        );
      } else {
        print('❌ No file found at ${item.path} and no thumbnailPath available');
        return _buildThumbnailPlaceholder(item);
      }
    }
  }

  Widget _buildThumbnailPlaceholder(MediaItem item) {
    return Container(
      color: Colors.grey[800],
      child: Icon(
        item.type == MediaType.video ? Icons.videocam : Icons.image,
        color: Colors.white54,
        size: 40,
      ),
    );
  }

  Widget _buildEmptyState(String title, String subtitle) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.photo_library_outlined,
            size: 80,
            color: Colors.white.withOpacity(0.3),
          ),
          const SizedBox(height: 16),
          Text(
            title,
            style: TextStyle(
              color: Colors.white.withOpacity(0.8),
              fontSize: 18,
              fontWeight: FontWeight.w500,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            subtitle,
            style: TextStyle(
              color: Colors.white.withOpacity(0.5),
              fontSize: 14,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildErrorState(String error) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(
            Icons.error_outline,
            size: 80,
            color: Colors.red,
          ),
          const SizedBox(height: 16),
          Text(
            'Error loading media',
            style: TextStyle(
              color: Colors.white.withOpacity(0.8),
              fontSize: 18,
              fontWeight: FontWeight.w500,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            error,
            style: TextStyle(
              color: Colors.white.withOpacity(0.5),
              fontSize: 14,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 16),
          ElevatedButton(
            onPressed: () {
              context.read<GalleryProvider>().loadMedia();
            },
            child: const Text('Retry'),
          ),
        ],
      ),
    );
  }

  Widget _buildSelectionActions() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.black.withOpacity(0.9),
        border: Border(
          top: BorderSide(
            color: Colors.white.withOpacity(0.1),
            width: 1,
          ),
        ),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceEvenly,
        children: [
          _buildActionButton(
            icon: Icons.share,
            label: 'Share',
            onPressed: _shareSelectedItems,
          ),
          _buildActionButton(
            icon: Icons.download,
            label: 'Download',
            onPressed: _downloadSelectedItems,
          ),
          _buildActionButton(
            icon: Icons.delete,
            label: 'Delete',
            onPressed: _deleteSelectedItems,
            isDestructive: true,
          ),
        ],
      ),
    );
  }

  Widget _buildActionButton({
    required IconData icon,
    required String label,
    required VoidCallback onPressed,
    bool isDestructive = false,
  }) {
    return GestureDetector(
      onTap: onPressed,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            icon,
            color: isDestructive ? Colors.red : Colors.white,
            size: 24,
          ),
          const SizedBox(height: 4),
          Text(
            label,
            style: TextStyle(
              color: isDestructive ? Colors.red : Colors.white,
              fontSize: 12,
            ),
          ),
        ],
      ),
    );
  }

  void _handleTileTap(MediaItem item) {
    if (_isSelectionMode) {
      _toggleSelection(item);
    } else {
      _openMediaViewer(item);
    }
  }

  void _handleTileLongPress(MediaItem item) {
    if (!_isSelectionMode) {
      _enterSelectionMode();
      _toggleSelection(item);
    }
  }

  void _enterSelectionMode() {
    setState(() {
      _isSelectionMode = true;
      _selectedItems.clear();
    });
  }

  void _exitSelectionMode() {
    setState(() {
      _isSelectionMode = false;
      _selectedItems.clear();
    });
  }

  void _toggleSelection(MediaItem item) {
    setState(() {
      if (_selectedItems.contains(item.id)) {
        _selectedItems.remove(item.id);
      } else {
        _selectedItems.add(item.id);
      }
    });
  }

  void _openMediaViewer(MediaItem item) {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => _MediaViewerScreen(item: item),
      ),
    );
  }

  void _shareSelectedItems() async {
    if (_selectedItems.isEmpty) return;

    // TODO: Implement sharing functionality
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('Sharing ${_selectedItems.length} items...'),
        backgroundColor: Colors.blue,
      ),
    );

    _exitSelectionMode();
  }

  void _downloadSelectedItems() async {
    if (_selectedItems.isEmpty) return;

    // TODO: Implement download functionality
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('Downloading ${_selectedItems.length} items...'),
        backgroundColor: Colors.green,
      ),
    );

    _exitSelectionMode();
  }

  void _deleteSelectedItems() async {
    if (_selectedItems.isEmpty) return;

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Items'),
        content: Text(
          'Are you sure you want to delete ${_selectedItems.length} item(s)? This action cannot be undone.',
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

    if (confirmed == true) {
      try {
        await context.read<GalleryProvider>().deleteMedia(_selectedItems.toList());
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Deleted ${_selectedItems.length} items'),
            backgroundColor: Colors.red,
          ),
        );
      } catch (e) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to delete items: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }

    _exitSelectionMode();
  }

  String _formatDuration(int seconds) {
    final minutes = seconds ~/ 60;
    final remainingSeconds = seconds % 60;
    return '${minutes.toString().padLeft(2, '0')}:${remainingSeconds.toString().padLeft(2, '0')}';
  }
}

/// Full-screen media viewer for photos and videos
class _MediaViewerScreen extends StatelessWidget {
  final MediaItem item;

  const _MediaViewerScreen({required this.item});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        backgroundColor: Colors.black,
        foregroundColor: Colors.white,
        title: Text(
          item.name,
          style: const TextStyle(fontSize: 16),
        ),
        actions: [
          IconButton(
            onPressed: () => _shareItem(context),
            icon: const Icon(Icons.share),
          ),
          IconButton(
            onPressed: () => _showItemInfo(context),
            icon: const Icon(Icons.info_outline),
          ),
        ],
      ),
      body: Center(
        child: InteractiveViewer(
          panEnabled: true,
          boundaryMargin: const EdgeInsets.all(20),
          minScale: 0.5,
          maxScale: 4.0,
          child: _buildMediaContent(),
        ),
      ),
    );
  }

  Widget _buildMediaContent() {
    final file = File(item.path);
    
    if (item.type == MediaType.photo) {
      if (file.existsSync()) {
        print('📸 Loading image from local file: ${item.path}');
        return Image.file(
          file,
          fit: BoxFit.contain,
          errorBuilder: (context, error, stackTrace) {
            print('❌ Error loading image: $error');
            return _buildErrorWidget();
          },
        );
      } else {
        print('❌ File not found: ${item.path}');
        return _buildErrorWidget();
      }
    } else if (item.type == MediaType.video) {
      // TODO: Implement video player
      return Container(
        padding: const EdgeInsets.all(20),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(
              Icons.play_circle_outline,
              size: 80,
              color: Colors.white54,
            ),
            const SizedBox(height: 16),
            Text(
              'Video Player Coming Soon',
              style: TextStyle(
                color: Colors.white.withOpacity(0.7),
                fontSize: 18,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              item.name,
              style: TextStyle(
                color: Colors.white.withOpacity(0.5),
                fontSize: 14,
              ),
            ),
          ],
        ),
      );
    } else {
      return _buildErrorWidget();
    }
  }

  Widget _buildErrorWidget() {
    return Container(
      padding: const EdgeInsets.all(20),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(
            Icons.error_outline,
            size: 80,
            color: Colors.red,
          ),
          const SizedBox(height: 16),
          const Text(
            'Unable to load media',
            style: TextStyle(
              color: Colors.white,
              fontSize: 18,
              fontWeight: FontWeight.w500,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'File: ${item.name}',
            style: TextStyle(
              color: Colors.white.withOpacity(0.7),
              fontSize: 14,
            ),
          ),
          Text(
            'Path: ${item.path}',
            style: TextStyle(
              color: Colors.white.withOpacity(0.5),
              fontSize: 12,
            ),
          ),
        ],
      ),
    );
  }

  void _shareItem(BuildContext context) {
    // TODO: Implement sharing
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Sharing coming soon...'),
        backgroundColor: Colors.blue,
      ),
    );
  }

  void _showItemInfo(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: Colors.grey[900],
        title: const Text(
          'Media Info',
          style: TextStyle(color: Colors.white),
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildInfoRow('Name', item.name),
            _buildInfoRow('Type', item.type.name.toUpperCase()),
            _buildInfoRow('Size', _formatFileSize(item.fileSize ?? 0)),
            _buildInfoRow('Created', _formatDateTime(item.createdAt)),
            _buildInfoRow('Path', item.path),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text(
              'Close',
              style: TextStyle(color: Colors.blue),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildInfoRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 60,
            child: Text(
              '$label:',
              style: TextStyle(
                color: Colors.white.withOpacity(0.7),
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: const TextStyle(color: Colors.white),
            ),
          ),
        ],
      ),
    );
  }

  String _formatFileSize(int bytes) {
    if (bytes < 1024) return '$bytes B';
    if (bytes < 1024 * 1024) return '${(bytes / 1024).toStringAsFixed(1)} KB';
    return '${(bytes / (1024 * 1024)).toStringAsFixed(1)} MB';
  }

  String _formatDateTime(DateTime dateTime) {
    return '${dateTime.day}/${dateTime.month}/${dateTime.year} ${dateTime.hour.toString().padLeft(2, '0')}:${dateTime.minute.toString().padLeft(2, '0')}';
  }
}
