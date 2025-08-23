import 'package:flutter/foundation.dart';
import '../../shared/models/media_item.dart';
import '../services/gallery_service.dart';

/// Provider for managing gallery state and operations
class GalleryProvider extends ChangeNotifier {
  final GalleryService _galleryService = GalleryService.instance;

  List<MediaItem> _allMedia = [];
  bool _isLoading = false;
  String? _error;

  // Getters
  List<MediaItem> get allMedia => _allMedia;
  List<MediaItem> get photos => _allMedia.where((item) => item.type == MediaType.photo).toList();
  List<MediaItem> get videos => _allMedia.where((item) => item.type == MediaType.video).toList();
  bool get isLoading => _isLoading;
  String? get error => _error;

  /// Load all media from storage
  Future<void> loadMedia() async {
    try {
      _setLoading(true);
      _clearError();
      
      _allMedia = await _galleryService.getAllMedia();
      notifyListeners();
    } catch (e) {
      _setError('Failed to load media: $e');
    } finally {
      _setLoading(false);
    }
  }

  /// Load media with filters
  Future<void> loadMediaWithFilter({
    MediaType? filterType,
    DateTime? startDate,
    DateTime? endDate,
  }) async {
    try {
      _setLoading(true);
      _clearError();
      
      _allMedia = await _galleryService.getAllMedia(
        filterType: filterType,
        startDate: startDate,
        endDate: endDate,
      );
      notifyListeners();
    } catch (e) {
      _setError('Failed to load filtered media: $e');
    } finally {
      _setLoading(false);
    }
  }

  /// Add a new media item
  Future<void> addMedia(MediaItem item) async {
    try {
      await _galleryService.addMediaItem(item.path);
      _allMedia.insert(0, item); // Add to beginning for most recent first
      notifyListeners();
    } catch (e) {
      _setError('Failed to add media: $e');
    }
  }

  /// Delete media items by IDs
  Future<void> deleteMedia(List<String> mediaIds) async {
    try {
      for (String id in mediaIds) {
        await _galleryService.deleteMediaItem(id);
        _allMedia.removeWhere((item) => item.id == id);
      }
      notifyListeners();
    } catch (e) {
      _setError('Failed to delete media: $e');
      rethrow;
    }
  }

  /// Get media by ID
  MediaItem? getMediaById(String id) {
    try {
      return _allMedia.firstWhere((item) => item.id == id);
    } catch (e) {
      return null;
    }
  }

  /// Clear all media from gallery
  Future<void> clearAllMedia() async {
    try {
      _setLoading(true);
      await _galleryService.clearGallery();
      _allMedia.clear();
      notifyListeners();
    } catch (e) {
      _setError('Failed to clear media: $e');
    } finally {
      _setLoading(false);
    }
  }

  /// Refresh gallery by reloading from storage
  Future<void> refresh() async {
    await loadMedia();
  }

  /// Get storage statistics
  Future<Map<String, dynamic>> getStorageStats() async {
    try {
      return await _galleryService.getGalleryStats();
    } catch (e) {
      _setError('Failed to get storage stats: $e');
      return {};
    }
  }

  void _setLoading(bool loading) {
    _isLoading = loading;
    notifyListeners();
  }

  void _setError(String error) {
    _error = error;
    notifyListeners();
  }

  void _clearError() {
    _error = null;
    notifyListeners();
  }

  @override
  void dispose() {
    super.dispose();
  }
}
