/// Video List Builder Widget
/// UI for creating and editing video lists from user collections

import 'package:flutter/material.dart';
import 'package:provider/provider.dart' as provider;
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../models/signage_models.dart';
import '../../providers/signage_provider.dart';
import '../../core/models/collection_models.dart';
import '../../services/media_api_client.dart';
import '../../core/api/api_client.dart';

class VideoListBuilder extends ConsumerStatefulWidget {
  final VideoList? videoList;
  final SignageProvider? signageProvider;

  const VideoListBuilder({Key? key, this.videoList, this.signageProvider}) : super(key: key);

  @override
  ConsumerState<VideoListBuilder> createState() => _VideoListBuilderState();
}

class _VideoListBuilderState extends ConsumerState<VideoListBuilder> {
  final _formKey = GlobalKey<FormState>();
  final _nameController = TextEditingController();
  final _descriptionController = TextEditingController();
  
  late final MediaApiClient _mediaApiClient;
  
  List<MediaCollection> _availableCollections = [];
  List<String> _selectedCollectionIds = [];
  Map<String, List<dynamic>> _collectionVideos = {};
  List<VideoOrderItem> _orderedVideos = [];
  
  LoopMode _loopMode = LoopMode.continuous;
  int _transitionDuration = 1000;
  bool _isLoading = false;
  bool _isSaving = false;

  @override
  void initState() {
    super.initState();
    
    // Initialize MediaApiClient with shared authenticated ApiClient from Riverpod
    _mediaApiClient = MediaApiClient(ref.read(apiClientProvider));
    
    if (widget.videoList != null) {
      _nameController.text = widget.videoList!.name;
      _descriptionController.text = widget.videoList!.description ?? '';
      _selectedCollectionIds = List.from(widget.videoList!.collectionIds ?? []);
      _loopMode = widget.videoList!.loopMode ?? LoopMode.continuous;
      _transitionDuration = widget.videoList!.transitionDurationMs ?? 1000;
      _orderedVideos = widget.videoList!.videoItems
          ?.map((item) => VideoOrderItem(
                collectionId: item.collectionId,
                videoId: item.videoId,
                sequence: item.sequenceOrder,
              ))
          .toList() ?? [];
    }
    
    _loadCollections();
  }

  @override
  void dispose() {
    _nameController.dispose();
    _descriptionController.dispose();
    super.dispose();
  }

  Future<void> _loadCollections() async {
    setState(() => _isLoading = true);
    
    try {
      final response = await _mediaApiClient.getCollections(
        limit: 100,
        excludeCameraCollections: true, // Only load user-created collections for video lists
      );
      
      if (response.success && response.data != null) {
        // Client-side filter: exclude camera collections
        // Checks camera_device_id AND description/name patterns for
        // collections whose camera was removed (camera_device_id cleared)
        final userCreatedOnly = response.data!.where((c) {
          // Exclude if camera_device_id is set
          if (c.cameraDeviceId != null && c.cameraDeviceId!.isNotEmpty) {
            return false;
          }
          // Exclude if description matches auto-created camera pattern
          final desc = c.description ?? '';
          if (desc.startsWith('Collection for camera:')) {
            return false;
          }
          // Exclude if name matches typical camera collection pattern
          // e.g. "Home Camera Collection", "RTSP Camera 01 Collection"
          final name = c.name;
          if (RegExp(r'.+Camera.*Collection$', caseSensitive: false).hasMatch(name)) {
            return false;
          }
          return true;
        }).toList();
        setState(() {
          _availableCollections = userCreatedOnly;
          _isLoading = false;
        });
        
        // Load videos for selected collections
        for (final collectionId in _selectedCollectionIds) {
          await _loadCollectionVideos(collectionId);
        }
      } else {
        throw Exception(response.error ?? 'Failed to load collections');
      }
    } catch (e, stackTrace) {
      setState(() => _isLoading = false);
      debugPrint('❌ Error loading collections: $e');
      debugPrint('   Stack trace: $stackTrace');
      
      if (mounted) {
        // Use addPostFrameCallback to show SnackBar after initState completes
        WidgetsBinding.instance.addPostFrameCallback((_) {
          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                content: Text('Failed to load collections: $e'),
                duration: const Duration(seconds: 5),
                action: SnackBarAction(
                  label: 'Retry',
                  onPressed: _loadCollections,
                ),
              ),
            );
          }
        });
      }
    }
  }

  Future<void> _loadCollectionVideos(String collectionId) async {
    try {
      final response = await _mediaApiClient.getCollectionItems(
        collectionId: collectionId,
      );
      
      if (response.success && response.data != null) {
        setState(() {
          _collectionVideos[collectionId] = response.data!;
        });
      } else {
        throw Exception(response.error ?? 'Failed to load collection items');
      }
    } catch (e) {
      print('Failed to load videos for collection $collectionId: $e');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      child: Container(
        width: MediaQuery.of(context).size.width * 0.8,
        height: MediaQuery.of(context).size.height * 0.8,
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header
            Row(
              children: [
                Icon(
                  widget.videoList == null ? Icons.add : Icons.edit,
                  size: 32,
                ),
                const SizedBox(width: 16),
                Text(
                  widget.videoList == null
                      ? 'Create Video Playlist'
                      : 'Edit Video Playlist',
                  style: Theme.of(context).textTheme.headlineSmall,
                ),
                const Spacer(),
                IconButton(
                  icon: const Icon(Icons.close),
                  onPressed: () => Navigator.pop(context),
                ),
              ],
            ),
            const Divider(height: 32),
            
            // Content
            Expanded(
              child: _isLoading
                  ? const Center(child: CircularProgressIndicator())
                  : _buildForm(),
            ),
            
            // Actions
            const Divider(height: 32),
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                TextButton(
                  onPressed: () => Navigator.pop(context),
                  child: const Text('Cancel'),
                ),
                const SizedBox(width: 16),
                ElevatedButton(
                  onPressed: _isSaving ? null : _savePlaylist,
                  child: _isSaving
                      ? const SizedBox(
                          width: 20,
                          height: 20,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : Text(widget.videoList == null ? 'Create' : 'Save'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildForm() {
    return Form(
      key: _formKey,
      child: ListView(
        children: [
          // Name field
          TextFormField(
            controller: _nameController,
            decoration: const InputDecoration(
              labelText: 'Playlist Name *',
              hintText: 'e.g., Morning Display',
              border: OutlineInputBorder(),
            ),
            validator: (value) {
              if (value == null || value.isEmpty) {
                return 'Please enter a playlist name';
              }
              return null;
            },
          ),
          const SizedBox(height: 16),
          
          // Description field
          TextFormField(
            controller: _descriptionController,
            decoration: const InputDecoration(
              labelText: 'Description',
              hintText: 'Optional description',
              border: OutlineInputBorder(),
            ),
            maxLines: 3,
          ),
          const SizedBox(height: 24),
          
          // Loop mode selector
          Row(
            children: [
              Expanded(
                child: DropdownButtonFormField<LoopMode>(
                  value: _loopMode,
                  decoration: const InputDecoration(
                    labelText: 'Loop Mode',
                    border: OutlineInputBorder(),
                  ),
                  items: const [
                    DropdownMenuItem(
                      value: LoopMode.once,
                      child: Text('Play Once'),
                    ),
                    DropdownMenuItem(
                      value: LoopMode.continuous,
                      child: Text('Continuous Loop'),
                    ),
                    DropdownMenuItem(
                      value: LoopMode.shuffle,
                      child: Text('Shuffle'),
                    ),
                  ],
                  onChanged: (value) {
                    if (value != null) {
                      setState(() => _loopMode = value);
                    }
                  },
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: TextFormField(
                  initialValue: (_transitionDuration ~/ 1000).toString(),
                  decoration: const InputDecoration(
                    labelText: 'Transition (seconds)',
                    border: OutlineInputBorder(),
                  ),
                  keyboardType: TextInputType.number,
                  onChanged: (value) {
                    final seconds = int.tryParse(value) ?? 1;
                    _transitionDuration = seconds * 1000;
                  },
                ),
              ),
            ],
          ),
          const SizedBox(height: 24),
          
          // Collection selector
          Text(
            'Select Collections',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 8),
          Text(
            'Choose collections containing videos for this playlist',
            style: Theme.of(context).textTheme.bodySmall,
          ),
          const SizedBox(height: 16),
          
          Container(
            constraints: const BoxConstraints(maxHeight: 200),
            decoration: BoxDecoration(
              border: Border.all(color: Colors.grey[300]!),
              borderRadius: BorderRadius.circular(8),
            ),
            child: ListView.builder(
              shrinkWrap: true,
              itemCount: _availableCollections.length,
              itemBuilder: (context, index) {
                final collection = _availableCollections[index];
                final isSelected = _selectedCollectionIds.contains(collection.id);
                
                return CheckboxListTile(
                  title: Text(collection.name),
                  subtitle: Text('${collection.itemCount ?? 0} videos'),
                  value: isSelected,
                  onChanged: (value) async {
                    setState(() {
                      if (value == true) {
                        _selectedCollectionIds.add(collection.id);
                      } else {
                        _selectedCollectionIds.remove(collection.id);
                        _collectionVideos.remove(collection.id);
                        _orderedVideos.removeWhere(
                          (v) => v.collectionId == collection.id,
                        );
                      }
                    });
                    
                    if (value == true) {
                      await _loadCollectionVideos(collection.id);
                    }
                  },
                );
              },
            ),
          ),
          const SizedBox(height: 24),
          
          // Video order section
          if (_selectedCollectionIds.isNotEmpty) ...[
            Row(
              children: [
                Text(
                  'Video Order',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const Spacer(),
                TextButton.icon(
                  onPressed: _autoOrderVideos,
                  icon: const Icon(Icons.sort),
                  label: const Text('Auto-order'),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              'Drag to reorder videos',
              style: Theme.of(context).textTheme.bodySmall,
            ),
            const SizedBox(height: 16),
            
            Container(
              constraints: const BoxConstraints(maxHeight: 300),
              decoration: BoxDecoration(
                border: Border.all(color: Colors.grey[300]!),
                borderRadius: BorderRadius.circular(8),
              ),
              child: _buildVideoOrderList(),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildVideoOrderList() {
    if (_orderedVideos.isEmpty && _collectionVideos.isNotEmpty) {
      _autoOrderVideos();
    }
    
    return ReorderableListView.builder(
      shrinkWrap: true,
      itemCount: _orderedVideos.length,
      onReorder: (oldIndex, newIndex) {
        setState(() {
          if (newIndex > oldIndex) {
            newIndex -= 1;
          }
          final item = _orderedVideos.removeAt(oldIndex);
          _orderedVideos.insert(newIndex, item);
          
          // Update sequence numbers
          for (var i = 0; i < _orderedVideos.length; i++) {
            _orderedVideos[i] = VideoOrderItem(
              collectionId: _orderedVideos[i].collectionId,
              videoId: _orderedVideos[i].videoId,
              sequence: i,
            );
          }
        });
      },
      itemBuilder: (context, index) {
        final videoOrder = _orderedVideos[index];
        final video = _getVideoDetails(videoOrder.collectionId, videoOrder.videoId);
        
        return ListTile(
          key: ValueKey(videoOrder.videoId),
          leading: CircleAvatar(
            child: Text('${index + 1}'),
          ),
          title: Text(video?['original_filename'] ?? 'Video ${videoOrder.videoId}'),
          subtitle: Text(_getCollectionName(videoOrder.collectionId)),
          trailing: IconButton(
            icon: const Icon(Icons.delete),
            onPressed: () {
              setState(() {
                _orderedVideos.removeAt(index);
                // Update sequence numbers
                for (var i = 0; i < _orderedVideos.length; i++) {
                  _orderedVideos[i] = VideoOrderItem(
                    collectionId: _orderedVideos[i].collectionId,
                    videoId: _orderedVideos[i].videoId,
                    sequence: i,
                  );
                }
              });
            },
          ),
        );
      },
    );
  }

  void _autoOrderVideos() {
    final allVideos = <VideoOrderItem>[];
    var sequence = 0;
    
    for (final collectionId in _selectedCollectionIds) {
      final videos = _collectionVideos[collectionId] ?? [];
      for (final video in videos) {
        allVideos.add(VideoOrderItem(
          collectionId: collectionId,
          videoId: video['uuid']?.toString() ?? '',
          sequence: sequence++,
        ));
      }
    }
    
    setState(() {
      _orderedVideos = allVideos;
    });
  }

  Map<String, dynamic>? _getVideoDetails(String collectionId, String videoId) {
    final videos = _collectionVideos[collectionId] ?? [];
    try {
      return videos.firstWhere(
        (v) => v['uuid']?.toString() == videoId,
      );
    } catch (e) {
      return null;
    }
  }

  String _getCollectionName(String collectionId) {
    try {
      return _availableCollections
          .firstWhere((c) => c.id == collectionId)
          .name;
    } catch (e) {
      return 'Unknown Collection';
    }
  }

  Future<void> _savePlaylist() async {
    if (!_formKey.currentState!.validate()) {
      return;
    }
    
    if (_selectedCollectionIds.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please select at least one collection')),
      );
      return;
    }
    
    if (_orderedVideos.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('No videos to add to playlist')),
      );
      return;
    }

    setState(() => _isSaving = true);

    try {
      debugPrint('💾 Saving video list...');
      debugPrint('   Widget: VideoListBuilder (${widget.videoList == null ? "CREATE" : "EDIT"})');
      debugPrint('   Context widget: ${context.widget.runtimeType}');
      
      final request = CreateVideoListRequest(
        name: _nameController.text.trim(),
        description: _descriptionController.text.trim().isEmpty
            ? null
            : _descriptionController.text.trim(),
        collectionIds: _selectedCollectionIds,
        videoOrder: _orderedVideos,
        loopMode: _loopMode,
        transitionDurationMs: _transitionDuration,
      );

      debugPrint('   Request: ${request.name} with ${_selectedCollectionIds.length} collections');
      debugPrint('   Request JSON: ${request.toJson()}');
      
      // Use passed provider or look it up from context
      final SignageProvider signageProvider;
      if (widget.signageProvider != null) {
        debugPrint('   ✅ Using passed SignageProvider');
        signageProvider = widget.signageProvider!;
      } else {
        debugPrint('   🔍 Looking for SignageProvider in context tree...');
        signageProvider = provider.Provider.of<SignageProvider>(context, listen: false);
        debugPrint('   ✅ SignageProvider found!');
      }
      
      // Perform async operation
      final bool success;
      if (widget.videoList == null) {
        final result = await signageProvider.createVideoList(request);
        success = result != null;
      } else {
        success = await signageProvider.updateVideoList(widget.videoList!.id, request);
      }

      if (mounted) {
        if (success) {
          Navigator.pop(context, true);
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(widget.videoList == null
                  ? 'Playlist created successfully'
                  : 'Playlist updated successfully'),
            ),
          );
        } else {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(widget.videoList == null
                  ? 'Failed to create playlist'
                  : 'Failed to update playlist'),
            ),
          );
        }
      }
    } catch (e, stackTrace) {
      debugPrint('❌ Error saving video list: $e');
      debugPrint('   Stack trace: $stackTrace');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: $e')),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isSaving = false);
      }
    }
  }
}
