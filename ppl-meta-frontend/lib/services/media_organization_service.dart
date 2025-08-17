import 'dart:async';
import 'package:flutter/foundation.dart';
import '../core/models/collection_models.dart';
import '../models/media_models.dart';
import '../core/api/api_client.dart';
import 'media_api_client.dart';

/// Service for organizing media items and collections
/// Handles moving media between collections, bulk operations, and custom collection creation
class MediaOrganizationService extends ChangeNotifier {
  final MediaApiClient _mediaApiClient;
  
  // Progress tracking
  bool _isOperationInProgress = false;
  double _operationProgress = 0.0;
  String? _currentOperationDescription;
  String? _operationError;

  MediaOrganizationService({
    required MediaApiClient mediaApiClient,
  }) : _mediaApiClient = mediaApiClient;

  // Getters for progress tracking
  bool get isOperationInProgress => _isOperationInProgress;
  double get operationProgress => _operationProgress;
  String? get currentOperationDescription => _currentOperationDescription;
  String? get operationError => _operationError;

    /// Move a single media item to a collection
  Future<bool> moveMediaToCollection(String mediaId, String targetCollectionId) async {
    try {
      _setOperationState(true, 0.0, 'Moving media to collection...');
      
      // For now, use a placeholder user GUID - this should be replaced with actual auth
      const userGuid = 'current-user'; // TODO: Get from auth service

      // Remove from current collection (if any) and add to target
      final response = await _mediaApiClient.bulkAddToCollection(
        collectionId: targetCollectionId,
        mediaIds: [mediaId],
      );

      _setOperationState(false, 1.0, null);
      return response.success;
    } catch (e) {
      _setOperationError('Failed to move media: ${e.toString()}');
      return false;
    }
  }

  /// Move multiple media items to a target collection
  Future<bool> bulkMoveMedia(List<String> mediaIds, String targetCollectionId) async {
    try {
      _setOperationState(true, 0.0, 'Moving ${mediaIds.length} items...');
      
      // For now, use a placeholder user GUID - this should be replaced with actual auth
      const userGuid = 'current-user'; // TODO: Get from auth service

      // Process in chunks to avoid overwhelming the API
      const chunkSize = 20;
      final chunks = _chunkList(mediaIds, chunkSize);
      
      for (int i = 0; i < chunks.length; i++) {
        final chunk = chunks[i];
        _setOperationState(true, (i + 1) / chunks.length, 
            'Processing batch ${i + 1} of ${chunks.length}...');
        
        final response = await _mediaApiClient.bulkAddToCollection(
          collectionId: targetCollectionId,
          mediaIds: chunk,
        );
        
        if (!response.success) {
          throw Exception('Failed to process batch ${i + 1}');
        }
      }

      _setOperationState(false, 1.0, null);
      return true;
    } catch (e) {
      _setOperationError('Failed to move media: ${e.toString()}');
      return false;
    }
  }

  /// Create a new collection with specified media items
  Future<bool> createCollectionFromMedia(
    String collectionName, 
    List<String> mediaIds, {
    String? description,
  }) async {
    try {
      _setOperationState(true, 0.0, 'Creating collection...');
      
      // For now, use a placeholder user GUID - this should be replaced with actual auth
      const userGuid = 'current-user'; // TODO: Get from auth service

      // Create the collection first
      _setOperationState(true, 0.3, 'Creating collection "$collectionName"...');
      final response = await _mediaApiClient.createCollection(
        name: collectionName,
        description: description ?? 'Collection created from camera media',
      );

      if (!response.success || response.data == null) {
        throw Exception('Failed to create collection');
      }

      final collection = response.data!;

      // Add media items to the new collection
      if (mediaIds.isNotEmpty) {
        _setOperationState(true, 0.6, 'Adding ${mediaIds.length} items to collection...');
        final success = await bulkMoveMedia(mediaIds, collection.id);
        if (!success) {
          throw Exception('Failed to add media to collection');
        }
      }

      _setOperationState(false, 1.0, null);
      return true;
    } catch (e) {
      _setOperationError('Failed to create collection: ${e.toString()}');
      return false;
    }
  }

  /// Create a custom collection (without media items)
  Future<MediaCollection?> createCustomCollection(
    String name, 
    String description, {
    bool isPublic = false,
  }) async {
    try {
      _setOperationState(true, 0.0, 'Creating collection...');
      
      final response = await _mediaApiClient.createCollection(
        name: name,
        description: description,
      );

      _setOperationState(false, 1.0, null);
      return response.success ? response.data : null;
    } catch (e) {
      _setOperationError('Failed to create collection: ${e.toString()}');
      return null;
    }
  }

  /// Copy media items to another collection (without removing from original)
  Future<bool> copyMediaToCollection(List<String> mediaIds, String targetCollectionId) async {
    try {
      _setOperationState(true, 0.0, 'Copying ${mediaIds.length} items...');
      
      final response = await _mediaApiClient.bulkAddToCollection(
        collectionId: targetCollectionId,
        mediaIds: mediaIds,
      );

      _setOperationState(false, 1.0, null);
      return response.success;
    } catch (e) {
      _setOperationError('Failed to copy media: ${e.toString()}');
      return false;
    }
  }

  /// Remove media items from a collection
  Future<bool> removeFromCollection(List<String> mediaIds, String collectionId) async {
    try {
      _setOperationState(true, 0.0, 'Removing ${mediaIds.length} items...');
      
      // Note: This would require a remove API endpoint
      // For now, we'll throw an informative error
      throw UnimplementedError('Remove from collection API not yet implemented');
      
      // TODO: Implement when backend supports removal
      // final response = await _mediaApiClient.bulkRemoveFromCollection(
      //   collectionId: collectionId,
      //   mediaIds: mediaIds,
      // );

      // _setOperationState(false, 1.0, null);
      // return response.success;
    } catch (e) {
      _setOperationError('Failed to remove media: ${e.toString()}');
      return false;
    }
  }

    /// Get all available collections for organization
  Future<List<MediaCollection>> getAvailableCollections() async {
    try {
      final response = await _mediaApiClient.getCollections();
      return response.success ? response.data ?? [] : [];
    } catch (e) {
      print('Error getting collections: $e');
      return [];
    }
  }

  /// Create a "Security Event" collection from multiple camera snapshots
  Future<MediaCollection?> createSecurityEventCollection(
    List<String> mediaIds, {
    String? eventName,
    String? eventDescription,
    DateTime? eventTime,
  }) async {
    final time = eventTime ?? DateTime.now();
    final name = eventName ?? 'Security Event - ${_formatDateTime(time)}';
    final description = eventDescription ?? 
        'Security event collection created from ${mediaIds.length} camera captures on ${_formatDateTime(time)}';

    final success = await createCollectionFromMedia(name, mediaIds, description: description);
    if (success) {
      // Try to fetch the created collection from the available collections
      final collections = await getAvailableCollections();
      return collections.firstWhere(
        (collection) => collection.name == name,
        orElse: () => MediaCollection(
          id: 'temp-id',
          name: name,
          description: description,
          createdAt: time,
          itemCount: mediaIds.length,
          isPublic: false,
        ),
      );
    }
    return null;
  }

  /// Clear any operation errors
  void clearError() {
    _operationError = null;
    notifyListeners();
  }

  // Private helper methods

  void _setOperationState(bool inProgress, double progress, String? description) {
    _isOperationInProgress = inProgress;
    _operationProgress = progress;
    _currentOperationDescription = description;
    _operationError = null;
    notifyListeners();
  }

  void _setOperationError(String error) {
    _isOperationInProgress = false;
    _operationProgress = 0.0;
    _currentOperationDescription = null;
    _operationError = error;
    notifyListeners();
  }

  List<List<T>> _chunkList<T>(List<T> list, int chunkSize) {
    final chunks = <List<T>>[];
    for (int i = 0; i < list.length; i += chunkSize) {
      chunks.add(list.sublist(i, (i + chunkSize).clamp(0, list.length)));
    }
    return chunks;
  }

  String _formatDateTime(DateTime dateTime) {
    return '${dateTime.day}/${dateTime.month}/${dateTime.year} ${dateTime.hour}:${dateTime.minute.toString().padLeft(2, '0')}';
  }
}
