import 'dart:io';
import 'package:dio/dio.dart' as dio;
import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:http_parser/http_parser.dart' as http_parser;
import 'package:path_provider/path_provider.dart';
import '../models/api_response.dart';
import '../models/media_models.dart';
import '../models/device_info.dart';
import '../core/config/app_config.dart';
import '../core/api/api_client.dart';
import '../utils/download_helper_web.dart' if (dart.library.io) '../utils/download_helper_stub.dart';

/// API client for media operations
class MediaApiClient {
  late final ApiClient _apiClient;
  
  MediaApiClient([ApiClient? apiClient]) {
    // Use provided ApiClient or create new one for authentication
    // When used with Provider, the authenticated ApiClient will be passed in
    // When used standalone, creates its own ApiClient (may need manual token setting)
    _apiClient = apiClient ?? ApiClient(AppConfig.instance);
  }

  /// Upload media file
  Future<ApiResponse<MediaItem>> uploadMedia({
    String? filePath,
    String? filename,
    List<int>? fileBytes,
    String? fileName,
    String? mimeType,
    Map<String, dynamic>? metadata,
    String? collectionId,
    DeviceInfo? deviceInfo,
    Function(int, int)? onProgress,
    Function(double)? onProgressPercent,
  }) async {
    try {
      MultipartFile file;
      String finalFilename = filename ?? fileName ?? 'upload';
      
      if (fileBytes != null) {
        // Upload from bytes (web/mobile)
        file = MultipartFile.fromBytes(
          fileBytes,
          filename: finalFilename,
          contentType: mimeType != null ? http_parser.MediaType.parse(mimeType) : null,
        );
      } else if (filePath != null) {
        // Upload from file path (desktop)
        file = await MultipartFile.fromFile(filePath, filename: finalFilename);
      } else {
        throw Exception('Either filePath or fileBytes must be provided');
      }
      
      // Determine media type from file extension
      final mediaType = _getMediaTypeFromFilename(finalFilename);
      
      // Get current user ID from authentication
      final userId = await _getCurrentUserId();
      if (userId == null) {
        throw Exception('User not authenticated - please login first');
      }
      
      final formData = FormData.fromMap({
        'file': file,
        'media_type': mediaType,  // Required field
        'user_id': userId,        // Required field
        if (metadata != null) 'metadata': metadata,
        if (collectionId != null) 'collection_id': collectionId,
        if (deviceInfo != null) 'device_info': deviceInfo.toJson(),
      });

      final response = await _apiClient.post(
        '/api/v1/media/upload',
        data: formData,
      );

      // TODO: Re-implement progress tracking if needed
      // Progress callbacks currently not supported by ApiClient wrapper

      // Create a MediaItem from the response data, mapping backend fields to frontend model
      final responseData = response.data as Map<String, dynamic>;
      final mediaItem = MediaItem(
        mediaId: responseData['id']?.toString() ?? responseData['uuid']?.toString() ?? '',
        originalFilename: responseData['original_filename'] ?? responseData['filename'] ?? finalFilename,
        mediaType: _parseMediaType(responseData['media_type'] ?? 'document'),
        fileSize: responseData['file_size'] ?? 0,
        filePath: responseData['file_path'] ?? '',
        uploadedAt: responseData['created_at'] != null 
            ? DateTime.parse(responseData['created_at']) 
            : DateTime.now(),
        uploadedBy: responseData['uploaded_by'],
        isPublic: responseData['is_public'] ?? false,
        thumbnailUrl: responseData['thumbnail_url'],
        url: responseData['url'],
        tags: (responseData['tags'] as List?)?.cast<String>() ?? [],
        description: responseData['description'],
        technicalMetadata: responseData['technical_metadata'],
      );

      return ApiResponse.success(mediaItem);
    } on DioException catch (e) {
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  /// Get media items with pagination
  Future<ApiResponse<MediaListResponse>> getMediaItems({
    int page = 1,
    int limit = 20,
    MediaType? type,
    String? search,
    String? collectionId,
    DateTime? startDate,
    DateTime? endDate,
  }) async {
    try {
      final queryParams = <String, dynamic>{
        'page': page,
        'limit': limit,
        if (type != null) 'type': type.name,
        if (search != null && search.isNotEmpty) 'search': search,
        if (collectionId != null) 'collection_id': collectionId,
        if (startDate != null) 'start_date': startDate.toIso8601String(),
        if (endDate != null) 'end_date': endDate.toIso8601String(),
      };

      final response = await _apiClient.get('/api/v1/media/items', queryParameters: queryParams);
      return ApiResponse.success(MediaListResponse.fromJson(response.data));
    } on DioException catch (e) {
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  /// Get media item by ID
  Future<ApiResponse<MediaItem>> getMediaItem(String id) async {
    try {
      final response = await _apiClient.get('/api/v1/media/items/$id');
      return ApiResponse.success(MediaItem.fromJson(response.data));
    } on DioException catch (e) {
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  /// Delete media item
  Future<ApiResponse<void>> deleteMedia(String mediaId) async {
    try {
      // Get current user ID for authentication
      final userId = await _getCurrentUserId();
      if (userId == null) {
        return ApiResponse.error('Authentication required. Please login again.');
      }

      // Make DELETE request to backend
      await _apiClient.delete('/api/v1/media/$mediaId', queryParameters: {
        'user_id': userId,
      });

      return ApiResponse.success(null);
    } on DioException catch (e) {
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  /// Download media file
  Future<ApiResponse<void>> downloadMedia(String mediaId, String filename) async {
    try {
      // Get current user ID for authentication
      final userId = await _getCurrentUserId();
      if (userId == null) {
        return ApiResponse.error('Authentication required. Please login again.');
      }

      // Download the file data using authenticated request
      final response = await _apiClient.get('/api/v1/media/download/$mediaId', 
        queryParameters: {
          'user_id': userId,
        },
        options: dio.Options(
          responseType: dio.ResponseType.bytes,
        ),
      );

      if (kIsWeb) {
        // For web: Use web download helper
        final bytes = response.data as List<int>;
        downloadFileWeb(bytes, filename);
        return ApiResponse.success(null);
      } else {
        // For desktop/mobile, save to Downloads folder
        if (!kIsWeb) {
          final directory = await getDownloadsDirectory();
          if (directory != null) {
            final file = File('${directory.path}/$filename');
            await file.writeAsBytes(response.data);
          } else {
            return ApiResponse.error('Could not access downloads directory');
          }
        } else {
          return ApiResponse.error('Platform not supported for file downloads');
        }
        
        return ApiResponse.success(null);
      }
    } on DioException catch (e) {
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  /// Get collections (always include authenticated user's UUID as user_id)
  Future<ApiResponse<List<MediaCollection>>> getCollections() async {
    try {
      final userId = await _getCurrentUserId();
      if (userId == null) {
        throw Exception('User not authenticated - please login first');
      }
      final response = await _apiClient.get(
        '/api/v1/media/collections',
        queryParameters: {'user_id': userId},
      );
      final collections = (response.data as List)
          .map((json) => MediaCollection.fromJson(json))
          .toList();
      return ApiResponse.success(collections);
    } on DioException catch (e) {
      // Handle specific status codes gracefully
      if (e.response?.statusCode == 422 || e.response?.statusCode == 404) {
        // Return empty list instead of error for "no collections found" scenarios
        return ApiResponse.success(<MediaCollection>[]);
      }
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  /// Create collection
  Future<ApiResponse<MediaCollection>> createCollection({
    required String name,
    String? description,
  }) async {
    try {
      // Get current user ID for authentication
      final userId = await _getCurrentUserId();
      if (userId == null) {
        return ApiResponse.error('Authentication required. Please login again.');
      }

      // Use FormData as backend expects Form fields, not JSON
      final formData = FormData.fromMap({
        'name': name,
        'user_id': userId,
        if (description != null && description.isNotEmpty) 'description': description,
        'is_public': 'false',  // Form fields should be strings
      });

      final response = await _apiClient.post(
        '/api/v1/media/collections', 
        data: formData,
        options: Options(
          headers: {'Content-Type': 'multipart/form-data'},
        ),
      );
      return ApiResponse.success(MediaCollection.fromJson(response.data));
    } on DioException catch (e) {
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  /// Add single media item to collection
  Future<ApiResponse<void>> addMediaToCollection({
    required String collectionId,
    required String mediaId,
  }) async {
    try {
      final userId = await _getCurrentUserId();
      if (userId == null) {
        return ApiResponse.error('Authentication required. Please login again.');
      }

      final response = await _apiClient.post(
        '/api/v1/media/collections/$collectionId/add/$mediaId',
        queryParameters: {'user_id': userId},
      );
      
      print('DEBUG: MediaApiClient addMediaToCollection - success: ${response.data}');
      return ApiResponse.success(null);
    } on DioException catch (e) {
      print('DEBUG: MediaApiClient addMediaToCollection - DioException: $e');
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      print('DEBUG: MediaApiClient addMediaToCollection - Exception: $e');
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  /// Add multiple items to collection (bulk operation)
  Future<ApiResponse<void>> addItemsToCollection({
    required String collectionId,
    required List<String> itemIds,
  }) async {
    try {
      await _apiClient.post('/api/v1/media/collections/$collectionId/items', data: {
        'item_ids': itemIds,
      });
      return ApiResponse.success(null);
    } on DioException catch (e) {
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  /// Get analytics data
  Future<ApiResponse<MediaAnalytics>> getAnalytics({
    DateTime? startDate,
    DateTime? endDate,
  }) async {
    try {
      final queryParams = <String, dynamic>{
        if (startDate != null) 'start_date': startDate.toIso8601String(),
        if (endDate != null) 'end_date': endDate.toIso8601String(),
      };

      final response = await _apiClient.get('/api/v1/media/analytics', queryParameters: queryParams);
      return ApiResponse.success(MediaAnalytics.fromJson(response.data));
    } on DioException catch (e) {
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  /// Search media with suggestions
  Future<ApiResponse<MediaListResponse>> searchMedia({
    String? query,
    MediaType? mediaType,
    DateTime? startDate,
    DateTime? endDate,
    List<String>? tags,
    String? collectionId,
    String? sortBy,
    String? sortOrder,
    MediaSearchFilters? filters,
    int page = 1,
    int limit = 20,
  }) async {
    try {
      // If searching within a specific collection, use the collection items endpoint
      if (collectionId != null && collectionId.isNotEmpty) {
        return await _getCollectionItems(
          collectionId: collectionId,
          page: page,
          limit: limit,
        );
      }

      // Otherwise use the general search endpoint
      final queryParams = <String, dynamic>{
        'page': page,
        'page_size': limit, // Backend uses page_size instead of limit
        if (query != null && query.isNotEmpty) 'query': query,
        if (mediaType != null) 'media_types': mediaType.name,
        if (startDate != null) 'start_date': startDate.toIso8601String(),
        if (endDate != null) 'end_date': endDate.toIso8601String(),
        if (tags != null && tags.isNotEmpty) 'tags': tags.join(','),
        if (sortBy != null) 'sort_by': sortBy,
        if (sortOrder != null) 'sort_order': sortOrder,
        // Note: filters parameter not used for now, using individual parameters
      };

      print('DEBUG: MediaApiClient searchMedia - general search queryParams: $queryParams');
      final response = await _apiClient.get('/api/v1/media/search', queryParameters: queryParams);
      print('DEBUG: MediaApiClient searchMedia - response received, status: ${response.statusCode}');
      print('DEBUG: MediaApiClient searchMedia - response data type: ${response.data.runtimeType}');
      print('DEBUG: MediaApiClient searchMedia - first item sample: ${(response.data as List).isNotEmpty ? (response.data as List)[0] : 'empty'}');
      
      // The backend returns a list directly, not wrapped in a response object
      final items = (response.data as List)
          .map((json) {
            print('DEBUG: Parsing MediaItem from: ${json['original_filename']} - deviceName: ${json['device_name']}');
            return MediaItem.fromJson(json);
          })
          .where((item) => !item.isArchived) // Filter out archived (deleted) items
          .toList();
      
      print('DEBUG: MediaApiClient searchMedia - parsed ${items.length} items');
      if (items.isNotEmpty) {
        print('DEBUG: First item after parsing - originalFilename: ${items[0].originalFilename}, deviceName: ${items[0].deviceName}');
      }
      
      // Create MediaListResponse with the items (simplified without JSON serialization)
      final searchResponse = MediaListResponse(
        items: items,
        totalCount: items.length,
        page: page,
        limit: limit,
        hasMore: items.length == limit,
      );
      
      return ApiResponse.success(searchResponse);
    } on DioException catch (e) {
      print('DEBUG: MediaApiClient searchMedia - DioException: $e');
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      print('DEBUG: MediaApiClient searchMedia - Exception: $e');
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  /// Get media items in a specific collection
  Future<ApiResponse<MediaListResponse>> _getCollectionItems({
    required String collectionId,
    int page = 1,
    int limit = 20,
  }) async {
    try {
      final userId = await _getCurrentUserId();
      if (userId == null) {
        return ApiResponse.error('Authentication required. Please login again.');
      }

      final queryParams = <String, dynamic>{
        'user_id': userId,
        'skip': (page - 1) * limit,
        'limit': limit,
      };

      print('DEBUG: MediaApiClient _getCollectionItems - collectionId: $collectionId, queryParams: $queryParams');
      final response = await _apiClient.get('/api/v1/media/collections/$collectionId/items', queryParameters: queryParams);
      print('DEBUG: MediaApiClient _getCollectionItems - response received, status: ${response.statusCode}');
      print('DEBUG: MediaApiClient _getCollectionItems - response data type: ${response.data.runtimeType}');
      
      // The backend returns a list directly, not wrapped in a response object
      final items = (response.data as List)
          .map((json) {
            print('DEBUG: Parsing collection MediaItem from: ${json['original_filename']}');
            return MediaItem.fromJson(json);
          })
          .where((item) => !item.isArchived) // Filter out archived (deleted) items
          .toList();
      
      print('DEBUG: MediaApiClient _getCollectionItems - parsed ${items.length} items for collection $collectionId');
      
      // Create MediaListResponse with the items
      final collectionResponse = MediaListResponse(
        items: items,
        totalCount: items.length,
        page: page,
        limit: limit,
        hasMore: items.length == limit,
      );
      
      return ApiResponse.success(collectionResponse);
    } on DioException catch (e) {
      print('DEBUG: MediaApiClient _getCollectionItems - DioException: $e');
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      print('DEBUG: MediaApiClient _getCollectionItems - Exception: $e');
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  /// Get search suggestions
  Future<ApiResponse<List<String>>> getSearchSuggestions(String query) async {
    try {
      final response = await _apiClient.get('/api/v1/media/search/suggestions', queryParameters: {
        'query': query,
      });
      return ApiResponse.success(List<String>.from(response.data));
    } on DioException catch (e) {
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  /// Generate share link
  Future<ApiResponse<ShareLink>> createShareLink({
    required List<String> itemIds,
    String? password,
    DateTime? expiresAt,
    bool allowDownload = true,
  }) async {
    try {
      final response = await _apiClient.post('/api/v1/media/share', data: {
        'item_ids': itemIds,
        if (password != null) 'password': password,
        if (expiresAt != null) 'expires_at': expiresAt.toIso8601String(),
        'allow_download': allowDownload,
      });
      return ApiResponse.success(ShareLink.fromJson(response.data));
    } on DioException catch (e) {
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  /// Get device analytics
  Future<ApiResponse<DeviceAnalytics>> getDeviceAnalytics({
    DateTime? startDate,
    DateTime? endDate,
  }) async {
    try {
      final queryParams = <String, dynamic>{
        if (startDate != null) 'start_date': startDate.toIso8601String(),
        if (endDate != null) 'end_date': endDate.toIso8601String(),
      };

      final response = await _apiClient.get('/api/v1/media/device-analytics', queryParameters: queryParams);
      return ApiResponse.success(DeviceAnalytics.fromJson(response.data));
    } on DioException catch (e) {
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  /// Delete collection
  Future<ApiResponse<void>> deleteCollection(String collectionId) async {
    try {
      await _apiClient.delete('/api/v1/media/collections/$collectionId');
      return ApiResponse.success(null);
    } on DioException catch (e) {
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  /// Update collection
  Future<ApiResponse<MediaCollection>> updateCollection({
    required String collectionId,
    String? name,
    String? description,
  }) async {
    try {
      // Get user profile to extract user_id
      final profileResponse = await _apiClient.get('/api/v1/user/profile');
      final userId = profileResponse.data['guid'] as String;
      
      final response = await _apiClient.put('/api/v1/media/collections/$collectionId?user_id=$userId', data: {
        if (name != null) 'name': name,
        if (description != null) 'description': description,
      });
      return ApiResponse.success(MediaCollection.fromJson(response.data));
    } on DioException catch (e) {
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  /// Share media by email
  Future<ApiResponse<void>> shareByEmail({
    required List<String> itemIds,
    required String email,
    String? message,
  }) async {
    try {
      await _apiClient.post('/api/v1/media/share/email', data: {
        'item_ids': itemIds,
        'email': email,
        if (message != null) 'message': message,
      });
      return ApiResponse.success(null);
    } on DioException catch (e) {
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  /// Handle Dio errors and convert to user-friendly messages
  String _handleDioError(DioException error) {
    switch (error.type) {
      case DioExceptionType.connectionTimeout:
        return 'Connection timeout. Please check your internet connection.';
      case DioExceptionType.sendTimeout:
        return 'Request timeout. Please try again.';
      case DioExceptionType.receiveTimeout:
        return 'Response timeout. Please try again.';
      case DioExceptionType.badResponse:
        final statusCode = error.response?.statusCode;
        switch (statusCode) {
          case 400:
            return 'Bad request. Please check your input.';
          case 401:
            return 'Authentication required. Please login again.';
          case 403:
            return 'Access forbidden. You don\'t have permission.';
          case 404:
            return 'Resource not found.';
          case 422:
            return error.response?.data?['detail'] ?? 'Validation error.';
          case 500:
            return 'Server error. Please try again later.';
          default:
            return 'HTTP error: $statusCode';
        }
      case DioExceptionType.cancel:
        return 'Request cancelled.';
      case DioExceptionType.unknown:
        if (error.error.toString().contains('SocketException')) {
          return 'Network error. Please check your connection.';
        }
        return 'Unknown error occurred.';
      default:
        return 'Unexpected error: ${error.message}';
    }
  }
  
  /// Get MediaType from filename extension
  String _getMediaTypeFromFilename(String filename) {
    final extension = filename.split('.').last.toLowerCase();
    
    switch (extension) {
      // Video formats
      case 'mp4':
      case 'mov':
      case 'avi':
      case 'mkv':
      case 'webm':
      case 'flv':
        return 'video';
      
      // Picture/Image formats  
      case 'jpg':
      case 'jpeg':
      case 'png':
      case 'gif':
      case 'bmp':
      case 'webp':
      case 'tiff':
      case 'svg':
        return 'picture';
      
      // Sound/Audio formats
      case 'mp3':
      case 'wav':
      case 'aac':
      case 'flac':
      case 'ogg':
      case 'm4a':
        return 'sound';
      
      // Document formats
      case 'pdf':
      case 'doc':
      case 'docx':
      case 'txt':
      case 'rtf':
      case 'xls':
      case 'xlsx':
      case 'ppt':
      case 'pptx':
        return 'document';
      
      // Default to document for unknown extensions
      default:
        return 'document';
    }
  }
  
  /// Parse MediaType from backend string to frontend enum
  MediaType _parseMediaType(String mediaTypeString) {
    switch (mediaTypeString.toLowerCase()) {
      case 'picture':
      case 'image':
        return MediaType.image;
      case 'video':
        return MediaType.video;
      case 'sound':
      case 'audio':
        return MediaType.audio;
      case 'document':
        return MediaType.document;
      case 'pdf':
        return MediaType.pdf;
      case 'text':
        return MediaType.text;
      case 'archive':
        return MediaType.archive;
      default:
        return MediaType.other;
    }
  }
  
  /// Get current user ID from authentication context
  Future<String?> _getCurrentUserId() async {
    try {
      // Use internal ApiClient for authentication
      final response = await _apiClient.get('/api/v1/user/profile');
      if (response.data != null) {
        // Extract user_id from profile response - use 'guid' (UUID) instead of 'id' (integer)
        return response.data['guid']?.toString();
      }
      return null;
    } catch (e) {
      print('Failed to get current user ID: $e');
    }
    return null;
  }
}
