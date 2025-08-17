import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/phase2_providers.dart';
import '../services/phase2_services.dart';
import '../widgets/custom_app_bar.dart';

/// Camera Media Sync - Centralized snapshot management hub
/// 
/// This screen provides oversight and control for camera snapshot syncing:
/// - Multi-camera sync status monitoring
/// - Cross-camera gallery with hybrid display  
/// - Camera collection management
/// - System-wide sync settings and statistics
class CameraMediaSyncScreen extends ConsumerStatefulWidget {
  const CameraMediaSyncScreen({super.key});

  @override
  ConsumerState<CameraMediaSyncScreen> createState() => _CameraMediaSyncScreenState();
}

class _CameraMediaSyncScreenState extends ConsumerState<CameraMediaSyncScreen>
    with SingleTickerProviderStateMixin {
  
  late TabController _tabController;
  
  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 4, vsync: this);
  }
  
  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: const CustomAppBar(
        title: 'Camera Media Sync',
      ),
      body: Column(
        children: [
          // TabBar as separate widget below CustomAppBar
          Material(
            color: Theme.of(context).primaryColor,
            child: TabBar(
              controller: _tabController,
              indicatorColor: Colors.white,
              labelColor: Colors.white,
              unselectedLabelColor: Colors.white70,
              tabs: const [
                Tab(icon: Icon(Icons.sync), text: 'Sync Status'),
                Tab(icon: Icon(Icons.photo_library), text: 'Gallery'),
                Tab(icon: Icon(Icons.folder), text: 'Collections'),
                Tab(icon: Icon(Icons.settings), text: 'Settings'),
              ],
            ),
          ),
          // TabBarView takes remaining space
          Expanded(
            child: TabBarView(
              controller: _tabController,
              children: [
                _buildSyncStatusTab(),
                _buildGalleryTab(),
                _buildCollectionsTab(),
                _buildSettingsTab(),
              ],
            ),
          ),
        ],
      ),
    );
  }
  
  Widget _buildSyncStatusTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Sync Status Dashboard',
            style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 16),
          
          // Sync status panel
          Consumer(
            builder: (context, ref, child) {
              final syncStatusAsync = ref.watch(syncStatusProvider);
              
              return syncStatusAsync.when(
                data: (status) => Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Icon(
                              _getSyncStatusIcon(status),
                              color: _getSyncStatusColor(status),
                            ),
                            const SizedBox(width: 8),
                            Text(
                              'Sync Status: ${status.name}',
                              style: const TextStyle(fontWeight: FontWeight.bold),
                            ),
                          ],
                        ),
                        const SizedBox(height: 8),
                        Text(_getSyncStatusDescription(status)),
                      ],
                    ),
                  ),
                ),
                loading: () => const Card(
                  child: Padding(
                    padding: EdgeInsets.all(16),
                    child: Row(
                      children: [
                        CircularProgressIndicator(),
                        SizedBox(width: 16),
                        Text('Loading sync status...'),
                      ],
                    ),
                  ),
                ),
                error: (error, stack) => Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Row(
                          children: [
                            Icon(Icons.error, color: Colors.red),
                            SizedBox(width: 8),
                            Text('Sync Status Error'),
                          ],
                        ),
                        const SizedBox(height: 8),
                        Text(error.toString()),
                      ],
                    ),
                  ),
                ),
              );
            },
          ),
          
          const SizedBox(height: 24),
          
          // Upload queue status
          const Text(
            'Upload Queue',
            style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 8),
          
          Consumer(
            builder: (context, ref, child) {
              final uploadQueueAsync = ref.watch(uploadQueueProvider);
              
              return uploadQueueAsync.when(
                data: (uploadTasks) {
                  if (uploadTasks.isEmpty) {
                    return const Card(
                      child: Padding(
                        padding: EdgeInsets.all(16),
                        child: Row(
                          children: [
                            Icon(Icons.check_circle, color: Colors.green),
                            SizedBox(width: 8),
                            Text('Upload queue is empty'),
                          ],
                        ),
                      ),
                    );
                  }
                  
                  return Column(
                    children: uploadTasks.map((task) => Card(
                      child: ListTile(
                        leading: const Icon(Icons.cloud_upload),
                        title: Text('Uploading: ${task.snapshotId}'),
                        subtitle: LinearProgressIndicator(
                          value: task.progress,
                        ),
                        trailing: Text('${(task.progress * 100).toInt()}%'),
                      ),
                    )).toList(),
                  );
                },
                loading: () => const Card(
                  child: Padding(
                    padding: EdgeInsets.all(16),
                    child: Row(
                      children: [
                        CircularProgressIndicator(),
                        SizedBox(width: 16),
                        Text('Loading upload queue...'),
                      ],
                    ),
                  ),
                ),
                error: (error, stack) => Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Text('Error: $error'),
                  ),
                ),
              );
            },
          ),
          
          const SizedBox(height: 24),
          
          // Manual sync controls
          const Text(
            'Manual Controls',
            style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 8),
          
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                children: [
                  ElevatedButton.icon(
                    onPressed: () async {
                      final syncService = await ref.read(snapshotSyncServiceProvider.future);
                      await syncService.syncAll();
                      
                      if (mounted) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(content: Text('Manual sync started')),
                        );
                      }
                    },
                    icon: const Icon(Icons.sync),
                    label: const Text('Start Manual Sync'),
                  ),
                  const SizedBox(height: 8),
                  ElevatedButton.icon(
                    onPressed: () async {
                      final syncService = await ref.read(snapshotSyncServiceProvider.future);
                      await syncService.pauseSync();
                      
                      if (mounted) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(content: Text('Sync paused')),
                        );
                      }
                    },
                    icon: const Icon(Icons.pause),
                    label: const Text('Pause Sync'),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
  
  Widget _buildGalleryTab() {
    return Column(
      children: [
        // Gallery mode selector
        Consumer(
          builder: (context, ref, child) {
            final currentMode = ref.watch(galleryModeProvider);
            
            return Padding(
              padding: const EdgeInsets.all(16),
              child: SegmentedButton<GalleryMode>(
                segments: const [
                  ButtonSegment(
                    value: GalleryMode.local,
                    label: Text('Local'),
                    icon: Icon(Icons.storage),
                  ),
                  ButtonSegment(
                    value: GalleryMode.cloud,
                    label: Text('Cloud'),
                    icon: Icon(Icons.cloud),
                  ),
                  ButtonSegment(
                    value: GalleryMode.both,
                    label: Text('Both'),
                    icon: Icon(Icons.sync),
                  ),
                ],
                selected: {currentMode},
                onSelectionChanged: (Set<GalleryMode> selection) {
                  ref.read(galleryModeProvider.notifier).state = selection.first;
                },
              ),
            );
          },
        ),
        
        // Enhanced gallery widget
        Expanded(
          child: Consumer(
            builder: (context, ref, child) {
              final galleryFilter = ref.watch(galleryFilterProvider);
              final galleryItemsAsync = ref.watch(galleryItemsProvider(galleryFilter));
              
              return galleryItemsAsync.when(
                data: (items) {
                  if (items.isEmpty) {
                    return const Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.photo_library_outlined, size: 64, color: Colors.grey),
                          SizedBox(height: 16),
                          Text('No snapshots yet', style: TextStyle(fontSize: 18)),
                          Text('Start capturing to see them here'),
                        ],
                      ),
                    );
                  }
                  
                  return GridView.builder(
                    padding: const EdgeInsets.all(16),
                    gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                      crossAxisCount: 3,
                      crossAxisSpacing: 8,
                      mainAxisSpacing: 8,
                    ),
                    itemCount: items.length,
                    itemBuilder: (context, index) {
                      final item = items[index];
                      return Card(
                        child: InkWell(
                          onTap: () => _showSnapshotPreview(context, item),
                          onLongPress: () => _showSnapshotOptions(context, item),
                          child: Column(
                            children: [
                              Expanded(
                                child: Container(
                                  width: double.infinity,
                                  decoration: BoxDecoration(
                                    color: Colors.grey[300],
                                    borderRadius: const BorderRadius.vertical(
                                      top: Radius.circular(12),
                                    ),
                                  ),
                                  child: Icon(
                                    item.source == 'cloud' ? Icons.cloud : Icons.storage,
                                    size: 32,
                                    color: item.source == 'cloud' ? Colors.blue : Colors.green,
                                  ),
                                ),
                              ),
                              Padding(
                                padding: const EdgeInsets.all(4),
                                child: Text(
                                  item.id,
                                  style: const TextStyle(fontSize: 10),
                                  overflow: TextOverflow.ellipsis,
                                ),
                              ),
                            ],
                          ),
                        ),
                      );
                    },
                  );
                },
                loading: () => const Center(child: CircularProgressIndicator()),
                error: (error, stack) => Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(Icons.error, size: 64, color: Colors.red),
                      const SizedBox(height: 16),
                      const Text('Failed to load gallery'),
                      Text(error.toString()),
                    ],
                  ),
                ),
              );
            },
          ),
        ),
      ],
    );
  }
  
  Widget _buildCollectionsTab() {
    return Consumer(
      builder: (context, ref, child) {
        final collectionsAsync = ref.watch(collectionsProvider);
        
        return collectionsAsync.when(
          data: (collections) {
            if (collections.isEmpty) {
              return const Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(Icons.folder_open, size: 64, color: Colors.grey),
                    SizedBox(height: 16),
                    Text(
                      'No collections yet',
                      style: TextStyle(fontSize: 18, color: Colors.grey),
                    ),
                    SizedBox(height: 8),
                    Text(
                      'Collections will appear as you organize snapshots',
                      style: TextStyle(color: Colors.grey),
                    ),
                  ],
                ),
              );
            }
            
            return ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: collections.length,
              itemBuilder: (context, index) {
                final collection = collections[index];
                return Card(
                  child: ListTile(
                    leading: const Icon(Icons.folder),
                    title: Text(collection.name),
                    subtitle: Text('${collection.snapshotCount} snapshots'),
                    trailing: const Icon(Icons.arrow_forward_ios),
                    onTap: () {
                      // Select collection for filtering
                      ref.read(selectedCollectionProvider.notifier).state = collection;
                      _tabController.animateTo(1); // Switch to gallery tab
                    },
                  ),
                );
              },
            );
          },
          loading: () => const Center(
            child: CircularProgressIndicator(),
          ),
          error: (error, stack) => Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Icon(Icons.error, size: 64, color: Colors.red),
                const SizedBox(height: 16),
                const Text('Failed to load collections'),
                const SizedBox(height: 8),
                Text(error.toString()),
                const SizedBox(height: 16),
                ElevatedButton(
                  onPressed: () => ref.refresh(collectionsProvider),
                  child: const Text('Retry'),
                ),
              ],
            ),
          ),
        );
      },
    );
  }
  
  Widget _buildSettingsTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Camera Media Sync Settings',
            style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 16),
          
          // Background sync toggle
          Consumer(
            builder: (context, ref, child) {
              final backgroundSyncEnabled = ref.watch(backgroundSyncEnabledProvider);
              
              return Card(
                child: SwitchListTile(
                  title: const Text('Background Sync'),
                  subtitle: const Text('Automatically upload snapshots to cloud'),
                  value: backgroundSyncEnabled,
                  onChanged: (value) {
                    ref.read(backgroundSyncEnabledProvider.notifier).state = value;
                  },
                ),
              );
            },
          ),
          
          // Auto-upload settings
          Consumer(
            builder: (context, ref, child) {
              final autoUploadSettings = ref.watch(autoUploadSettingsProvider);
              
              return Card(
                child: Column(
                  children: [
                    SwitchListTile(
                      title: const Text('Auto Upload'),
                      subtitle: const Text('Upload snapshots immediately after capture'),
                      value: autoUploadSettings.enabled,
                      onChanged: (value) {
                        ref.read(autoUploadSettingsProvider.notifier).state = 
                            autoUploadSettings.copyWith(enabled: value);
                      },
                    ),
                    SwitchListTile(
                      title: const Text('WiFi Only'),
                      subtitle: const Text('Only upload when connected to WiFi'),
                      value: autoUploadSettings.wifiOnly,
                      onChanged: (value) {
                        ref.read(autoUploadSettingsProvider.notifier).state = 
                            autoUploadSettings.copyWith(wifiOnly: value);
                      },
                    ),
                  ],
                ),
              );
            },
          ),
          
          // Gallery stats
          Consumer(
            builder: (context, ref, child) {
              final galleryStatsAsync = ref.watch(galleryStatsProvider);
              
              return galleryStatsAsync.when(
                data: (stats) => Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'Gallery Statistics',
                          style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                        ),
                        const SizedBox(height: 8),
                        Text('Total snapshots: ${stats.totalSnapshots}'),
                        Text('Local snapshots: ${stats.localSnapshots}'),
                        Text('Cloud snapshots: ${stats.cloudSnapshots}'),
                        Text('Pending uploads: ${stats.pendingUploads}'),
                        Text('Total size: ${stats.totalSizeMB.toStringAsFixed(1)} MB'),
                      ],
                    ),
                  ),
                ),
                loading: () => const Card(
                  child: Padding(
                    padding: EdgeInsets.all(16),
                    child: Row(
                      children: [
                        CircularProgressIndicator(),
                        SizedBox(width: 16),
                        Text('Loading statistics...'),
                      ],
                    ),
                  ),
                ),
                error: (error, stack) => Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Text('Error loading stats: $error'),
                  ),
                ),
              );
            },
          ),
        ],
      ),
    );
  }
  
  // Helper methods for sync status display
  IconData _getSyncStatusIcon(SyncStatus status) {
    switch (status) {
      case SyncStatus.idle:
        return Icons.check_circle;
      case SyncStatus.syncing:
        return Icons.sync;
      case SyncStatus.error:
        return Icons.error;
      case SyncStatus.paused:
        return Icons.pause_circle;
      case SyncStatus.completed:
        return Icons.check_circle;
    }
  }
  
  Color _getSyncStatusColor(SyncStatus status) {
    switch (status) {
      case SyncStatus.idle:
        return Colors.grey;
      case SyncStatus.syncing:
        return Colors.blue;
      case SyncStatus.error:
        return Colors.red;
      case SyncStatus.paused:
        return Colors.orange;
      case SyncStatus.completed:
        return Colors.green;
    }
  }
  
  String _getSyncStatusDescription(SyncStatus status) {
    switch (status) {
      case SyncStatus.idle:
        return 'All snapshots are synced';
      case SyncStatus.syncing:
        return 'Syncing snapshots to cloud...';
      case SyncStatus.error:
        return 'Sync failed - check connection';
      case SyncStatus.paused:
        return 'Sync is paused';
      case SyncStatus.completed:
        return 'Sync completed successfully';
    }
  }
  
  void _showSnapshotPreview(BuildContext context, GalleryItem galleryItem) {
    // TODO: Implement enhanced snapshot preview
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Snapshot Preview'),
        content: Text('Showing preview for: ${galleryItem.id}'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Close'),
          ),
        ],
      ),
    );
  }
  
  void _showSnapshotOptions(BuildContext context, GalleryItem galleryItem) {
    showModalBottomSheet(
      context: context,
      builder: (context) => Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          ListTile(
            leading: const Icon(Icons.share),
            title: const Text('Share'),
            onTap: () {
              Navigator.of(context).pop();
              // TODO: Implement sharing
            },
          ),
          ListTile(
            leading: const Icon(Icons.download),
            title: const Text('Download'),
            onTap: () {
              Navigator.of(context).pop();
              // TODO: Implement download
            },
          ),
          ListTile(
            leading: const Icon(Icons.folder_open),
            title: const Text('Add to Collection'),
            onTap: () {
              Navigator.of(context).pop();
              // TODO: Implement collection assignment
            },
          ),
          ListTile(
            leading: const Icon(Icons.delete, color: Colors.red),
            title: const Text('Delete', style: TextStyle(color: Colors.red)),
            onTap: () {
              Navigator.of(context).pop();
              // TODO: Implement deletion
            },
          ),
        ],
      ),
    );
  }
}

// Extension for AutoUploadSettings copyWith method
extension AutoUploadSettingsExtension on AutoUploadSettings {
  AutoUploadSettings copyWith({
    bool? enabled,
    bool? wifiOnly,
    double? qualityThreshold,
  }) {
    return AutoUploadSettings(
      enabled: enabled ?? this.enabled,
      wifiOnly: wifiOnly ?? this.wifiOnly,
      qualityThreshold: qualityThreshold ?? this.qualityThreshold,
    );
  }
}
