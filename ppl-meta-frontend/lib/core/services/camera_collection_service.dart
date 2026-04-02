import 'package:dio/dio.dart';
import 'package:logger/logger.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'dart:convert';
import '../models/camera.dart';
import '../models/collection_models.dart';
import '../api/api_client.dart';

/// Service for managing camera-owned collections
class CameraCollectionService {
  final ApiClient _apiClient;
  final Logger _logger = Logger();

  CameraCollectionService(this._apiClient);

  /// Get camera collection ID
  Future<String?> getCameraCollectionId(String cameraId) async {
    // First check local mapping
    final mapping = await getCameraCollectionMapping(cameraId);
    if (mapping != null) {
      return mapping.collectionId;
    }
    
    // If no local mapping, try to find existing collection
    final found = await _findAndMapExistingCollection(cameraId);
    if (found) {
      // Try again to get the mapping after finding
      final newMapping = await getCameraCollectionMapping(cameraId);
      return newMapping?.collectionId;
    }
    
    return null;
  }

  /// Get camera collection ID with camera name for better matching (NEW for RTSP cameras)
  Future<String?> getCameraCollectionIdWithName(String cameraId, String cameraName) async {
    // First check local mapping
    final mapping = await getCameraCollectionMapping(cameraId);
    if (mapping != null) {
      return mapping.collectionId;
    }
    
    // If no local mapping, try to find existing collection with camera name
    final found = await _findAndMapExistingCollectionWithName(cameraId, cameraName);
    if (found) {
      // Try again to get the mapping after finding
      final newMapping = await getCameraCollectionMapping(cameraId);
      return newMapping?.collectionId;
    }
    
    return null;
  }

  /// Check if camera has a collection mapping
  Future<bool> hasCameraCollection(String cameraId) async {
    final mapping = await getCameraCollectionMapping(cameraId);
    if (mapping != null) {
      return true;
    }
    
    // Try to find existing collection
    return await _findAndMapExistingCollection(cameraId);
  }

  /// Check if camera has a collection using camera name for better matching (NEW for RTSP cameras)
  Future<bool> hasCameraCollectionWithName(String cameraId, String cameraName) async {
    final mapping = await getCameraCollectionMapping(cameraId);
    if (mapping != null) {
      return true;
    }
    
    // Try to find existing collection with camera name
    return await _findAndMapExistingCollectionWithName(cameraId, cameraName);
  }

  /// Create a collection for a camera
  Future<MediaCollection> createCameraCollection(String cameraId, String cameraName) async {
    try {
      // Check if collection already exists
      final existingMapping = await getCameraCollectionMapping(cameraId);
      if (existingMapping != null) {
        throw CameraCollectionException('Collection already exists for camera $cameraId');
      }

      // Get current user UUID
      final userId = await _getCurrentUserId();
      if (userId == null) {
        throw CameraCollectionException('User not authenticated');
      }

      _logger.i('Creating collection for camera $cameraId: $cameraName Collection');

      // Prepare form data for the API (backend expects form data, not JSON)
      final formData = FormData.fromMap({
        'name': '$cameraName Collection',
        'description': 'Collection for camera: $cameraName',
        'user_id': userId,
        'is_public': 'false',
      });

      // Make API call to create collection using form data
      final response = await _apiClient.post(
        '/api/v1/media/collections',
        data: formData,
      );

      if (response.statusCode == 200 || response.statusCode == 201) {
        final collection = MediaCollection.fromJson(response.data);
        
        // Store mapping locally
        final mapping = CameraCollectionMapping(
          cameraId: cameraId,
          collectionId: collection.id,
          cameraName: cameraName,
          collectionName: collection.name,
          createdAt: DateTime.now(),
          lastUsed: DateTime.now(),
        );
        
        await storeCameraCollectionMapping(mapping);
        
        _logger.i('Successfully created collection ${collection.id} for camera $cameraId');
        return collection;
      } else {
        throw Exception('Failed to create collection: ${response.statusCode}');
      }
    } on DioException catch (e) {
      _logger.e('Failed to create camera collection: ${e.message}');
      if (e.response?.data != null) {
        _logger.e('Error response: ${e.response?.data}');
      }
      throw CameraCollectionException('Failed to create collection for camera $cameraName: ${e.message}');
    } catch (e) {
      _logger.e('Unexpected error creating camera collection: $e');
      throw CameraCollectionException('Unexpected error creating collection for camera $cameraName: $e');
    }
  }

  /// Get collection by ID
  Future<MediaCollection> getCollectionById(String collectionId) async {
    try {
      final userId = await _getCurrentUserId();
      if (userId == null) {
        throw CameraCollectionException('User not authenticated');
      }
      
      final response = await _apiClient.get('/api/v1/media/collections/$collectionId', queryParameters: {
        'user_id': userId,
      });
      
      if (response.statusCode == 200) {
        return MediaCollection.fromJson(response.data);
      } else {
        throw Exception('Collection not found: $collectionId');
      }
    } on DioException catch (e) {
      throw CameraCollectionException('Failed to get collection $collectionId: ${e.message}');
    }
  }

  /// Setup camera with collection (creates if needed)
  Future<MediaCollection> setupCameraWithCollection(Camera camera) async {
    try {
      // First, try to get existing collection using camera name for better matching
      final existingCollectionId = await getCameraCollectionIdWithName(camera.id, camera.name);
      if (existingCollectionId != null) {
        _logger.d('Using existing collection $existingCollectionId for camera ${camera.id}');
        return await getCollectionById(existingCollectionId);
      }

      // If no existing collection, create a new one
      _logger.i('Creating new collection for camera ${camera.id} (${camera.name})');
      final collection = await createCameraCollection(camera.id, camera.name);
      return collection;
    } catch (e) {
      _logger.e('Failed to setup camera collection for ${camera.id}: $e');
      rethrow;
    }
  }

  /// Get camera collection mapping from local storage
  Future<CameraCollectionMapping?> getCameraCollectionMapping(String cameraId) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final key = 'camera_collection_$cameraId';
      final mappingJson = prefs.getString(key);
      
      if (mappingJson != null) {
        final mappingData = json.decode(mappingJson);
        return CameraCollectionMapping.fromJson(mappingData);
      }
      
      return null;
    } catch (e) {
      _logger.e('Error getting camera collection mapping for $cameraId: $e');
      return null;
    }
  }

  /// Store camera collection mapping locally
  Future<void> storeCameraCollectionMapping(CameraCollectionMapping mapping) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final key = 'camera_collection_${mapping.cameraId}';
      final mappingJson = json.encode(mapping.toJson());
      
      await prefs.setString(key, mappingJson);
      _logger.d('Stored camera collection mapping: ${mapping.cameraId} -> ${mapping.collectionId}');
    } catch (e) {
      _logger.e('Error storing camera collection mapping: $e');
    }
  }

  /// Get all camera collection mappings
  Future<List<CameraCollectionMapping>> getAllCameraMappings() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final keys = prefs.getKeys();
      final mappings = <CameraCollectionMapping>[];
      
      for (final key in keys) {
        if (key.startsWith('camera_collection_')) {
          final mappingJson = prefs.getString(key);
          if (mappingJson != null) {
            try {
              final mappingData = json.decode(mappingJson);
              final mapping = CameraCollectionMapping.fromJson(mappingData);
              mappings.add(mapping);
            } catch (e) {
              _logger.w('Failed to parse camera collection mapping for key $key: $e');
            }
          }
        }
      }
      
      return mappings;
    } catch (e) {
      _logger.e('Error getting all camera collection mappings: $e');
      return [];
    }
  }

  /// Find and map existing collection to camera
  Future<bool> _findAndMapExistingCollection(String cameraId) async {
    try {
      if (_apiClient.authToken == null) {
        _logger.w('Cannot find existing collections: No authentication token available');
        return false;
      }

      // Generate expected collection name based on camera ID
      final expectedCollectionName = _generateExpectedCollectionName(cameraId);
      
      _logger.i('Looking for collection with name: $expectedCollectionName for camera $cameraId');
      
      // Get all collections and look for matches
      final allCollections = await getAllCollections();
      
      for (final collection in allCollections) {
        if (_isCollectionForCamera(collection, cameraId, expectedCollectionName)) {
          // Found matching collection! Store the mapping
          final mapping = CameraCollectionMapping(
            cameraId: cameraId,
            collectionId: collection.id,
            cameraName: cameraId, // Use camera ID as name if not available
            collectionName: collection.name,
            createdAt: collection.createdAt ?? DateTime.now(),
            lastUsed: DateTime.now(),
            autoCreated: true, // Assume it was auto-created since we found it
          );
          
          await storeCameraCollectionMapping(mapping);
          
          _logger.i('Found and mapped existing collection for camera $cameraId: ${collection.id} (${collection.name})');
          return true;
        }
      }
      
      return false;
    } catch (e) {
      _logger.e('Error finding existing collection for camera $cameraId: $e');
      return false;
    }
  }

  /// Find and map existing collection using actual camera name for better matching (NEW for RTSP cameras)
  Future<bool> _findAndMapExistingCollectionWithName(String cameraId, String cameraName) async {
    try {
      // Check authentication first
      if (_apiClient.authToken == null) {
        _logger.w('Cannot find existing collections: No authentication token available');
        return false;
      }

      // Generate expected collection name using the actual camera name
      final expectedCollectionName = '$cameraName Collection';
      
      _logger.i('Looking for collection with name: $expectedCollectionName for camera $cameraId');
      
      // Get all collections and look for name matches
      final allCollections = await getAllCollections();
      
      for (final collection in allCollections) {
        if (_isCollectionForCameraWithName(collection, cameraId, cameraName, expectedCollectionName)) {
          // Found matching collection! Store the mapping
          final mapping = CameraCollectionMapping(
            cameraId: cameraId,
            collectionId: collection.id,
            cameraName: cameraName,
            collectionName: collection.name,
            createdAt: collection.createdAt ?? DateTime.now(),
            lastUsed: DateTime.now(),
            autoCreated: true,
          );
          
          await storeCameraCollectionMapping(mapping);
          
          _logger.i('Found and mapped existing collection for camera $cameraId: ${collection.id} (${collection.name})');
          return true;
        }
      }
      
      _logger.w('No collection found for camera $cameraId with expected name: $expectedCollectionName');
      return false;
    } catch (e) {
      _logger.e('Error finding existing collection for camera $cameraId: $e');
      return false;
    }
  }

  /// Generate expected collection name for a camera
  String _generateExpectedCollectionName(String cameraId) {
    // Convert camera_id to expected collection name
    // e.g., "usb_camera_0" -> "USB Camera 0 Collection"
    if (cameraId == 'usb_camera_0') {
      return 'USB Camera 0 Collection';
    }
    
    // For RTSP cameras like "rtsp_192.168.1.75_554", we can't predict the name
    // without the actual camera name, so this will likely fail
    // This is why _findAndMapExistingCollectionWithName is preferred
    if (cameraId.startsWith('rtsp_')) {
      // Extract IP for basic name
      final parts = cameraId.split('_');
      if (parts.length >= 3) {
        final ip = parts[1];
        return 'RTSP Camera $ip Collection';
      }
      return 'RTSP Camera Collection';
    }
    
    // Default fallback
    return '${cameraId.replaceAll('_', ' ').toUpperCase()} Collection';
  }

  /// Check if collection is for a specific camera
  bool _isCollectionForCamera(MediaCollection collection, String cameraId, String expectedName) {
    // Check exact name match
    if (collection.name == expectedName) {
      return true;
    }
    
    // Check if collection description mentions the camera
    if (collection.description?.contains(cameraId) == true) {
      return true;
    }
    
    // Check metadata if available
    if (collection.metadata?['camera_id'] == cameraId) {
      return true;
    }
    
    return false;
  }

  /// Check if collection is for a specific camera using actual camera name (NEW for RTSP cameras)
  bool _isCollectionForCameraWithName(MediaCollection collection, String cameraId, String cameraName, String expectedName) {
    // Check exact name match with expected collection name
    if (collection.name == expectedName) {
      return true;
    }
    
    // Check if collection name matches the camera name pattern
    if (collection.name == '$cameraName Collection') {
      return true;
    }
    
    // Check if collection description mentions the camera
    if (collection.description?.contains(cameraId) == true ||
        collection.description?.contains(cameraName) == true) {
      return true;
    }
    
    // Check metadata if available
    if (collection.metadata?['camera_id'] == cameraId) {
      return true;
    }
    
    return false;
  }

  /// Get all collections (including camera collections)
  Future<List<MediaCollection>> getAllCollections() async {
    try {
      if (_apiClient.authToken == null) {
        _logger.w('No auth token available for getAllCollections');
        return [];
      }

      // Backend uses JWT from Authorization header (set by ApiClient interceptor)
      // Do NOT pass user_id as query parameter - backend extracts user from JWT
      final response = await _apiClient.get('/api/v1/media/collections');

      if (response.statusCode == 200) {
        final data = response.data;
        if (data is List) {
          return data.map<MediaCollection>((item) => MediaCollection.fromJson(item)).toList();
        } else if (data is Map && data.containsKey('collections')) {
          final collections = data['collections'] as List;
          return collections.map<MediaCollection>((item) => MediaCollection.fromJson(item)).toList();
        } else {
          _logger.w('Unexpected response format for collections');
          return [];
        }
      } else if (response.statusCode == 401) {
        _logger.w('Authentication failed when fetching collections: ${response.statusCode}');
        return [];
      } else {
        throw Exception('Failed to get collections: ${response.statusCode}');
      }
    } on DioException catch (e) {
      _logger.e('Failed to get collections: ${e.message}');
      if (e.response?.statusCode == 401) {
        _logger.w('Authentication error fetching collections, returning empty list');
        return [];
      }
      rethrow;
    } catch (e) {
      _logger.e('Error getting all collections: $e');
      rethrow;
    }
  }

  /// Retry collection detection after authentication
  Future<void> retryCollectionDetectionAfterAuth() async {
    _logger.i('Retrying collection detection after authentication...');
    try {
      // This method can be called by providers to retry detection
      // The actual retry will happen when cameras try to access collections again
      _logger.d('Collection detection retry completed - UI will refresh automatically');
    } catch (e) {
      _logger.e('Error during collection detection retry: $e');
    }
  }

  /// Get current user UUID (needed for collection operations)
  Future<String?> _getCurrentUserId() async {
    try {
      if (_apiClient.authToken == null) {
        _logger.d('No auth token available for _getCurrentUserId');
        return null;
      }

      // Use the correct profile endpoint that works
      final response = await _apiClient.get('/api/v1/user/profile');
      
      if (response.statusCode == 200) {
        return response.data['guid']?.toString();
      } else {
        _logger.w('Failed to get user info: ${response.statusCode}');
        return null;
      }
    } catch (e) {
      _logger.w('Failed to get current user UUID: $e');
      return null;
    }
  }
}

/// Exception for camera collection operations
class CameraCollectionException implements Exception {
  final String message;
  
  CameraCollectionException(this.message);
  
  @override
  String toString() => 'CameraCollectionException: $message';
}
