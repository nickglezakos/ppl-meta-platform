import 'dart:io';
import 'package:dio/dio.dart' as dio;
import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:http_parser/http_parser.dart' as http_parser;
import 'package:path_provider/path_provider.dart';
import '../models/api_response.dart';
import '../models/media_models.dart';
import '../core/models/collection_models.dart';
import '../models/device_info.dart';
import '../core/config/app_config.dart';
import '../core/api/api_client.dart';
import '../services/discovery_service_client.dart';
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
        uuid: responseData['uuid']?.toString() ?? responseData['id']?.toString() ?? '',
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

  /// Get media item by UUID (used when navigating from appearance cards)
  Future<MediaItem> getMediaByUuid(String uuid) async {
    try {
      debugPrint('🎬 MediaApiClient: Fetching media details for UUID: $uuid');
      
      // Get current user ID for authentication
      final userId = await _getCurrentUserId();
      
      final response = await _apiClient.get(
        '/api/v1/media/$uuid',
        queryParameters: userId != null ? {'user_id': userId} : null,
      );
      
      debugPrint('🎬 MediaApiClient: Got media response: ${response.statusCode}');
      
      // Parse the response data into a MediaItem
      final data = response.data as Map<String, dynamic>;
      final mediaItem = MediaItem(
        mediaId: data['id']?.toString() ?? data['uuid']?.toString() ?? '',
        uuid: data['uuid']?.toString() ?? uuid,
        originalFilename: data['original_filename'] ?? data['filename'] ?? 'Unknown',
        mediaType: _parseMediaType(data['media_type'] ?? 'video'),
        fileSize: data['file_size'] ?? 0,
        filePath: data['file_path'] ?? '',
        uploadedAt: data['created_at'] != null 
            ? DateTime.parse(data['created_at']) 
            : DateTime.now(),
        uploadedBy: data['uploaded_by'],
        isPublic: data['is_public'] ?? false,
        thumbnailUrl: data['thumbnail_url'],
        url: data['url'],
        tags: (data['tags'] as List?)?.cast<String>() ?? [],
        description: data['description'],
        technicalMetadata: data['technical_metadata'],
      );
      
      debugPrint('🎬 MediaApiClient: Successfully parsed MediaItem: ${mediaItem.originalFilename}');
      return mediaItem;
    } on DioException catch (e) {
      debugPrint('❌ MediaApiClient: Failed to fetch media by UUID: ${_handleDioError(e)}');
      throw Exception('Failed to load media details: ${_handleDioError(e)}');
    } catch (e) {
      debugPrint('❌ MediaApiClient: Unexpected error: $e');
      throw Exception('Unexpected error loading media: $e');
    }
  }

  MediaType _parseMediaType(String type) {
    switch (type.toLowerCase()) {
      case 'video':
        return MediaType.video;
      case 'image':
      case 'picture':
        return MediaType.image;
      case 'audio':
        return MediaType.audio;
      default:
        return MediaType.document;
    }
  }

  /// Get video properties including metadata (fps, frame count, etc.)
  Future<Map<String, dynamic>?> getVideoProperties(String mediaId) async {
    try {
      final response = await _apiClient.get('/api/v1/media/$mediaId/video-properties');
      return response.data as Map<String, dynamic>?;
    } on DioException catch (e) {
      print('❌ Failed to get video properties: ${_handleDioError(e)}');
      return null;
    } catch (e) {
      print('❌ Unexpected error getting video properties: $e');
      return null;
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

  /// Get user's media collections
  /// 
  /// Returns list of collections owned by the authenticated user.
  /// Collections are user-created groups of uploaded videos/images.
  Future<ApiResponse<List<MediaCollection>>> getCollections({
    int skip = 0,
    int limit = 100,
    bool includePublic = false,
    bool excludeCameraCollections = false,
  }) async {
    try {
      debugPrint('📡 Fetching collections from media service...');
      debugPrint('   Parameters: skip=$skip, limit=$limit, includePublic=$includePublic, excludeCameraCollections=$excludeCameraCollections');
      debugPrint('   🔑 ApiClient has token: ${_apiClient.authToken != null ? "YES (${_apiClient.authToken!.length} chars)" : "NO - NOT AUTHENTICATED!"}');
      
      final response = await _apiClient.get(
        '/api/v1/media/collections',
        queryParameters: {
          'skip': skip,
          'limit': limit,
          'include_public': includePublic,
          'exclude_camera_collections': excludeCameraCollections,
        },
      );

      debugPrint('✅ Got ${(response.data as List).length} collections');
      
      final collections = (response.data as List<dynamic>)
          .map((c) => MediaCollection.fromJson(c as Map<String, dynamic>))
          .toList();
      
      return ApiResponse.success(collections);
    } on DioException catch (e) {
      final statusCode = e.response?.statusCode;
      final errorData = e.response?.data;
      
      debugPrint('❌ Get collections failed with status $statusCode');
      debugPrint('   Error: ${e.message}');
      debugPrint('   Response: $errorData');
      
      // Handle specific status codes gracefully
      if (statusCode == 422 || statusCode == 404) {
        // Return empty list instead of error for "no collections found" scenarios
        debugPrint('   Treating as empty collections list');
        return ApiResponse.success(<MediaCollection>[]);
      }
      
      // For auth errors, provide clear message
      if (statusCode == 401 || statusCode == 403) {
        return ApiResponse.error('Authentication failed. Please login again.');
      }
      
      return ApiResponse.error(_handleDioError(e));
    } catch (e, stackTrace) {
      debugPrint('❌ Get collections unexpected error: $e');
      debugPrint('   Stack trace: $stackTrace');
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

  /// Bulk add media items to collection using backend bulk-add endpoint
  Future<ApiResponse<void>> bulkAddToCollection({
    required String collectionId,
    required List<String> mediaIds,
  }) async {
    try {
      final userId = await _getCurrentUserId();
      if (userId == null) {
        return ApiResponse.error('Authentication required. Please login again.');
      }

      print('DEBUG: MediaApiClient bulkAddToCollection - collectionId: $collectionId, mediaIds: $mediaIds, userId: $userId');
      
      final response = await _apiClient.post(
        '/api/v1/media/collections/$collectionId/bulk-add',
        data: {
          'media_ids': mediaIds,
          'collection_id': collectionId,
          'user_id': userId,
        },
      );
      
      print('DEBUG: MediaApiClient bulkAddToCollection - success: ${response.data}');
      return ApiResponse.success(null);
    } on DioException catch (e) {
      print('DEBUG: MediaApiClient bulkAddToCollection - DioException: $e');
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      print('DEBUG: MediaApiClient bulkAddToCollection - Exception: $e');
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
    List<String>? collectionIds,
    String? sortBy,
    String? sortOrder,
    MediaSearchFilters? filters,
    int page = 1,
    int limit = 20,
  }) async {
    try {
      // Use the unified search endpoint that supports collection filtering
      final queryParams = <String, dynamic>{
        'page': page,
        'page_size': limit, // Backend uses page_size instead of limit
        if (query != null && query.isNotEmpty) 'query': query,
        if (mediaType != null) 'media_type': mediaType.apiValue,
        if (startDate != null) 'start_date': startDate.toIso8601String(),
        if (endDate != null) 'end_date': endDate.toIso8601String(),
        if (tags != null && tags.isNotEmpty) 'tags': tags.join(','),
        if (collectionId != null) 'collection_id': collectionId,
        if (collectionIds != null && collectionIds.isNotEmpty) 
          'collection_ids': collectionIds.join(','),
        if (sortBy != null) 'sort_by': sortBy,
        if (sortOrder != null) 'sort_order': sortOrder,
        
        // Support filters object as well
        if (filters != null) ...{
          if (filters.query != null && filters.query!.isNotEmpty) 
            'query': filters.query,
          if (filters.mediaType != null) 
            'media_type': filters.mediaType!.apiValue,
          if (filters.startDate != null) 
            'start_date': filters.startDate!.toIso8601String(),
          if (filters.endDate != null) 
            'end_date': filters.endDate!.toIso8601String(),
          if (filters.tags != null && filters.tags!.isNotEmpty) 
            'tags': filters.tags!.join(','),
          if (filters.collectionId != null) 
            'collection_id': filters.collectionId,
          if (filters.collectionIds != null && filters.collectionIds!.isNotEmpty) 
            'collection_ids': filters.collectionIds!.join(','),
          if (filters.sortBy != null) 
            'sort_by': filters.sortBy,
          if (filters.sortOrder != null) 
            'sort_order': filters.sortOrder,
        },
      };

      // Use ApiClient.get() to ensure proper authorization headers
      final response = await _apiClient.get(
        '/api/v1/media/search',
        queryParameters: queryParams,
      );
      
      // The backend returns a list directly, not wrapped in a response object
      final items = (response.data as List)
          .map((json) => MediaItem.fromJson(json))
          .where((item) => !item.isArchived) // Filter out archived (deleted) items
          .toList();
      
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

  /// Get camera MVR people count with demographics (cached)
  /// 
  /// Fetches the count of unique MVR people detected by a camera with demographic breakdowns.
  /// Results are cached for 10 minutes for optimal performance.
  /// 
  /// Parameters:
  /// - cameraId: Camera device ID
  /// - timeFilter: Time period filter ('today', 'last_hour', 'last_3_hours', 'last_week', 'last_month')
  /// - forceRefresh: Bypass cache and get live data
  /// 
  /// Returns:
  /// - count: Total unique people
  /// - video_count: Number of videos analyzed
  /// - demographics: Gender and age breakdowns
  /// - cached: Whether result came from cache
  Future<ApiResponse<Map<String, dynamic>>> getCameraMVRCountCached({
    required String cameraId,
    String timeFilter = 'today',
    bool forceRefresh = false,
  }) async {
    try {
      debugPrint('📡 Fetching MVR count for camera: $cameraId (timeFilter: $timeFilter, forceRefresh: $forceRefresh)');
      
      final response = await _apiClient.get(
        '/api/v1/cameras/$cameraId/mvr-count',
        queryParameters: {
          'time_filter': timeFilter,
          'force_refresh': forceRefresh,
        },
      );

      debugPrint('✅ Got MVR count: ${response.data['count']} people (cached: ${response.data['cached']})');
      
      return ApiResponse.success(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      debugPrint('❌ Get MVR count failed: ${e.message}');
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      debugPrint('❌ Get MVR count unexpected error: $e');
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  /// Get aggregated analytics summary across all cameras
  /// 
  /// Fetches a summary of analytics data across multiple cameras with aggregate metrics.
  /// This is the primary endpoint for the analytics dashboard Level 1 (Basic Metrics).
  /// 
  /// Parameters:
  /// - timeFilter: Time period filter ('today', 'last_hour', 'last_3_hours', 'last_week', 'last_month')
  /// - cameraIds: Optional list of specific camera IDs to include (null = all cameras)
  /// - forceRefresh: Bypass cache and get live data
  /// 
  /// Returns:
  /// - total_people: Total unique people across all cameras
  /// - active_cameras: Number of cameras with detections
  /// - total_videos: Total videos analyzed
  /// - last_detection: Timestamp of most recent detection
  /// - demographics: Aggregate demographic breakdown
  /// - camera_breakdown: Per-camera analytics
  /// - cached: Whether result came from cache
  Future<ApiResponse<Map<String, dynamic>>> getAnalyticsSummary({
    String timeFilter = 'today',
    List<String>? cameraIds,
    bool forceRefresh = false,
  }) async {
    try {
      debugPrint('📊 Fetching analytics summary (timeFilter: $timeFilter, collections: ${cameraIds?.length ?? "all"})');
      
      final queryParams = <String, dynamic>{
        'time_filter': timeFilter,
        'force_refresh': forceRefresh,
      };
      
      if (cameraIds != null && cameraIds.isNotEmpty) {
        queryParams['collection_ids'] = cameraIds.join(',');
      }
      
      final response = await _apiClient.get(
        '/api/v1/analytics/summary',
        queryParameters: queryParams,
      );

      debugPrint('✅ Got analytics summary: ${response.data['total_people']} total people, ${response.data['active_cameras']} active cameras');
      
      return ApiResponse.success(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      debugPrint('❌ Get analytics summary failed: ${e.message}');
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      debugPrint('❌ Get analytics summary unexpected error: $e');
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  /// Get time-based analytics with trend data
  /// 
  /// Fetches time series data showing people count trends over time.
  /// Used for Level 2 (Time-Based Trends) analytics.
  /// 
  /// Parameters:
  /// - timeFilter: Time period filter ('last_hour', 'last_3_hours', 'today', 'last_week', 'last_month')
  /// - cameraIds: Optional list of specific camera IDs to include
  /// - interval: Time interval for data points ('minute', 'hour', 'day')
  /// 
  /// Returns:
  /// - time_filter: Applied time filter
  /// - data_points: List of time series data points with counts
  /// - peak_count: Highest count in the period
  /// - peak_time: Timestamp of peak count
  /// - average_count: Average count across period
  Future<ApiResponse<Map<String, dynamic>>> getTimeBasedAnalytics({
    String timeFilter = 'today',
    List<String>? cameraIds,
    String interval = 'hour',
  }) async {
    try {
      debugPrint('📈 Fetching time-based analytics (timeFilter: $timeFilter, interval: $interval)');
      
      final queryParams = <String, dynamic>{
        'time_filter': timeFilter,
        'interval': interval,
      };
      
      if (cameraIds != null && cameraIds.isNotEmpty) {
        queryParams['camera_ids'] = cameraIds.join(',');
      }
      
      final response = await _apiClient.get(
        '/api/v1/analytics/time-series',
        queryParameters: queryParams,
      );

      debugPrint('✅ Got time-based analytics: ${(response.data['data_points'] as List).length} data points');
      
      return ApiResponse.success(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      debugPrint('❌ Get time-based analytics failed: ${e.message}');
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      debugPrint('❌ Get time-based analytics unexpected error: $e');
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  /// Get list of all cameras with their basic info
  /// 
  /// Helper method to fetch camera metadata for analytics filtering.
  /// Returns list of cameras with IDs, names, and collection info.
  Future<ApiResponse<List<Map<String, dynamic>>>> getCamerasList() async {
    try {
      debugPrint('📹 Fetching cameras list');
      
      final response = await _apiClient.get('/api/v1/analytics/cameras');

      debugPrint('✅ Got ${(response.data as List).length} cameras');
      
      final cameras = (response.data as List)
          .map((c) => c as Map<String, dynamic>)
          .toList();
      
      return ApiResponse.success(cameras);
    } on DioException catch (e) {
      debugPrint('❌ Get cameras list failed: ${e.message}');
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      debugPrint('❌ Get cameras list unexpected error: $e');
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
      // Get user profile to extract user_id from Gateway service
      final profileData = await _makeGatewayRequest('/api/v1/user/profile');
      final userId = profileData['guid'] as String;
      
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

  /// Real-time face detection for single frame during video playback
  /// Phase 1 of Hybrid Face Detection Architecture (Issue 052)
  Future<SingleFrameFaceDetectionResult> detectFacesAtFrame({
    required String mediaId,
    required int frameNumber,
    double confidenceThreshold = 0.5, // FIXED: Default to 0.5 for better face detection
  }) async {
    try {
      final response = await _apiClient.get(
        '/api/v1/stream/faces/$mediaId/frame/$frameNumber',
        queryParameters: {
          'confidence_threshold': confidenceThreshold,
        },
      );

      return SingleFrameFaceDetectionResult.fromJson(response.data);
    } on DioException catch (e) {
      throw Exception('Real-time face detection failed: ${_handleDioError(e)}');
    }
  }

  /// Bulk face detection workflow for optimized video processing
  /// Uses Media Service workflow with frame rate optimization (3 FPS default)
  Future<BulkFaceDetectionWorkflowResult> startBulkFaceDetectionWorkflow({
    required String mediaId,
    double framesPerSecond = 3.0,
    String method = 'two_stage',
    double confidenceThreshold = 0.5,
    String priority = 'normal',
    bool storeResults = true,
  }) async {
    try {
      final response = await _apiClient.post(
        '/api/v1/workflow/face-detection/bulk-process',
        data: {
          'media_ids': [mediaId],
          'frames_per_second': framesPerSecond,
          'method': method,
          'confidence_threshold': confidenceThreshold,
          'priority': priority,
          'store_results': storeResults,
        },
      );

      return BulkFaceDetectionWorkflowResult.fromJson(response.data);
    } on DioException catch (e) {
      throw Exception('Bulk face detection workflow failed: ${_handleDioError(e)}');
    }
  }

  /// Check bulk face detection workflow status
  Future<BulkFaceDetectionWorkflowResult> getBulkFaceDetectionWorkflowStatus({
    required String workflowId,
  }) async {
    try {
      final response = await _apiClient.get(
        '/api/v1/workflow/face-detection/$workflowId',
      );

      return BulkFaceDetectionWorkflowResult.fromJson(response.data);
    } on DioException catch (e) {
      throw Exception('Get workflow status failed: ${_handleDioError(e)}');
    }
  }
  
  /// Get current user ID from authentication context
  Future<String?> _getCurrentUserId() async {
    try {
      // Call Gateway service for user profile (not media service)
      final gatewayResponse = await _makeGatewayRequest('/api/v1/user/profile');
      if (gatewayResponse['guid'] != null) {
        // Extract user_id from profile response - use 'guid' (UUID) instead of 'id' (integer)
        return gatewayResponse['guid']?.toString();
      }
      return null;
    } on DioException catch (e) {
      if (e.response?.statusCode == 401) {
        print('🔓 MediaApiClient: Authentication required - 401 error');
      } else {
        print('⚠️ MediaApiClient: Failed to get current user ID - Status: ${e.response?.statusCode}');
      }
      return null;
    } catch (e) {
      print('⚠️ MediaApiClient: Network error getting user ID: $e');
      return null;
    }
  }

  /// Helper method to make requests to Gateway service for user-related endpoints
  Future<Map<String, dynamic>> _makeGatewayRequest(String endpoint) async {
    // Use ApiClient.get() to ensure proper authorization headers
    final response = await _apiClient.get(endpoint);
    
    return response.data as Map<String, dynamic>;
  }

  /// Create cross-video individual tracking session with vmeta service
  Future<ApiResponse<Map<String, dynamic>>> createCrossVideoTrackingSession({
    required String collectionName,
    required DateTime startTime,
    required DateTime endTime,
  }) async {
    try {
      final requestBody = {
        'collections': [collectionName],
        'start_time': startTime.toIso8601String(),
        'end_time': endTime.toIso8601String(),
        'background_processing': true,
        'algorithm_config': {
          'max_gap_seconds': 10,
          'iou_threshold': 0.3,
          'min_overlap_confidence': 0.5,
        },
      };

      print('DEBUG: Creating cross-video tracking session with: $requestBody');
      
      final response = await _apiClient.post(
        '/api/v1/cross-video/individuals/tracking/sessions',
        data: requestBody,
      );

      print('DEBUG: Cross-video tracking session created: ${response.data}');
      
      return ApiResponse.success(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      print('ERROR: Failed to create tracking session: ${e.response?.data}');
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      print('ERROR: Unexpected error creating tracking session: $e');
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  /// Get cross-video tracking session status
  Future<ApiResponse<Map<String, dynamic>>> getCrossVideoTrackingSessionStatus({
    required String sessionUuid,
  }) async {
    try {
      print('');
      print('### API CLIENT - GET SESSION STATUS ###');
      print('=' * 80);
      print('REQUEST:');
      print('   Endpoint: /api/v1/cross-video/individuals/tracking/sessions/$sessionUuid');
      
      final response = await _apiClient.get(
        '/api/v1/cross-video/individuals/tracking/sessions/$sessionUuid',
      );

      print('');
      print('RAW HTTP RESPONSE:');
      print('   Status Code: ${response.statusCode}');
      print('   Response Type: ${response.data.runtimeType}');
      print('   Response Data: ${response.data}');
      
      final data = response.data as Map<String, dynamic>;
      print('');
      print('PARSED RESPONSE FIELDS:');
      print('   session_uuid: ${data['session_uuid']}');
      print('   status: ${data['status']}');
      print('   individuals_found: ${data['individuals_found']}');
      print('   unique_mvr_people_count: ${data['unique_mvr_people_count']}');
      print('   cache_hits: ${data['cache_hits']}');
      print('   total_videos: ${data['total_videos']}');
      print('   processed_videos: ${data['processed_videos']}');
      print('=' * 80);
      print('');

      print('DEBUG: Tracking session status: ${response.data}');
      
      return ApiResponse.success(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  /// Get individuals from cross-video tracking session (Phase 5)
  Future<ApiResponse<Map<String, dynamic>>> getCrossVideoIndividuals({
    required String sessionUuid,
  }) async {
    try {
      final response = await _apiClient.get(
        '/api/v1/cross-video/individuals/tracking/sessions/$sessionUuid/individuals',
      );

      print('DEBUG: Cross-video individuals: ${response.data}');
      
      return ApiResponse.success(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  /// Get aggregated individual analysis from vmeta backend (Phase 6)
  /// 
  /// This endpoint returns complete analysis data for an individual including:
  /// - All video appearances across multiple videos
  /// - Temporal analysis (first seen, last seen, duration)
  /// - Aggregated confidence scores
  /// - Person object UUIDs for each appearance
  /// 
  /// Note: Requires session_uuid as query parameter to filter appearances by session
  Future<ApiResponse<Map<String, dynamic>>> getIndividualAggregatedAnalysis({
    required String individualUuid,
    required String sessionUuid,
  }) async {
    try {
      final response = await _apiClient.get(
        '/api/v1/cross-video/individuals/tracking/individuals/$individualUuid/aggregated-analysis?session_uuid=$sessionUuid',
      );

      // Debug logging for name propagation tracking
      debugPrint('═══ VMETA API RESPONSE DEBUG ═══');
      debugPrint('Individual UUID: $individualUuid');
      debugPrint('Name field: ${response.data['name']}');
      debugPrint('Name updated at: ${response.data['name_updated_at']}');
      debugPrint('Name updated by: ${response.data['name_updated_by']}');
      debugPrint('═══════════════════════════════');
      
      return ApiResponse.success(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  /// Get individual analysis without requiring a session UUID
  /// 
  /// This endpoint returns all appearances for an individual across all videos
  /// without filtering by session. Ideal for MVR search results where individuals
  /// may span multiple sessions or have no session association.
  /// 
  /// Optional date filtering:
  /// - startTime: Filter appearances starting after this time
  /// - endTime: Filter appearances ending before this time
  /// 
  /// Returns:
  /// - individual_uuid: UUID of the individual
  /// - total_appearances: Total number of appearances across all videos
  /// - unique_videos: Number of unique videos
  /// - first_seen: Timestamp of first appearance
  /// - last_seen: Timestamp of last appearance
  /// - appearances: List of all video appearances with details
  Future<ApiResponse<Map<String, dynamic>>> getIndividualAnalysisNoSession({
    required String individualUuid,
    DateTime? startTime,
    DateTime? endTime,
  }) async {
    try {
      // Build query parameters
      final queryParams = <String>[];
      if (startTime != null) {
        queryParams.add('start_time=${startTime.toUtc().toIso8601String()}');
      }
      if (endTime != null) {
        queryParams.add('end_time=${endTime.toUtc().toIso8601String()}');
      }
      
      final queryString = queryParams.isNotEmpty ? '?${queryParams.join('&')}' : '';
      
      final response = await _apiClient.get(
        '/api/v1/mvr-people/individuals/$individualUuid/analysis$queryString',
      );

      print('DEBUG: Individual analysis (no session): ${response.data}');
      
      return ApiResponse.success(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  /// Get MVR person analysis (consolidated individual data)
  /// 
  /// This endpoint returns consolidated analysis for an MVR person, which
  /// represents multiple individuals merged into a single identity.
  /// 
  /// Optional date filtering:
  /// - startTime: Filter appearances starting after this time
  /// - endTime: Filter appearances ending before this time
  /// 
  /// Returns:
  /// - mvr_person_uuid: UUID of the MVR person
  /// - individual_uuids: List of constituent individual UUIDs
  /// - total_appearances: Total appearances across all individuals
  /// - unique_videos: Number of unique videos
  /// - first_seen: Timestamp of first appearance
  /// - last_seen: Timestamp of last appearance
  /// - appearances: Consolidated list of all appearances
  Future<ApiResponse<Map<String, dynamic>>> getMVRPersonAnalysis({
    required String mvrPersonUuid,
    DateTime? startTime,
    DateTime? endTime,
  }) async {
    try {
      // Build query parameters
      final queryParams = <String>[];
      if (startTime != null) {
        queryParams.add('start_time=${startTime.toUtc().toIso8601String()}');
      }
      if (endTime != null) {
        queryParams.add('end_time=${endTime.toUtc().toIso8601String()}');
      }
      
      final queryString = queryParams.isNotEmpty ? '?${queryParams.join('&')}' : '';
      
      final response = await _apiClient.get(
        '/api/v1/mvr-people/mvr-person/$mvrPersonUuid/analysis$queryString',
      );

      print('DEBUG: MVR person analysis: ${response.data}');
      
      return ApiResponse.success(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  /// Manually merge selected individuals with embedding validation
  /// 
  /// This endpoint validates face embedding similarity before merging individuals.
  /// Used in the Flutter UI when users manually select individuals to merge.
  /// The backend generates facial embeddings from face crops and validates
  /// similarity against a threshold before executing the merge.
  /// 
  /// Request parameters:
  /// - individual_uuids: List of individual UUIDs to merge (minimum 2)
  /// - session_uuid: Session identifier for filtering
  /// - similarity_threshold: Minimum similarity score (default 0.75)
  /// 
  /// Returns:
  /// - predominant_individual_uuid: The UUID of the predominant individual
  /// - merged_individual_uuids: List of UUIDs that were merged
  /// - similarity_score: Calculated similarity score
  /// - statistics: Merge statistics (appearances transferred, etc.)
  Future<ApiResponse<Map<String, dynamic>>> mergeIndividuals({
    required List<String> individualUuids,
    required String sessionUuid,
    double similarityThreshold = 0.6,
  }) async {
    try {
      final requestBody = {
        'individual_uuids': individualUuids,
        'session_uuid': sessionUuid,
        'similarity_threshold': similarityThreshold,
        'triggered_by': 'flutter_ui_manual_selection',
      };

      print('DEBUG: Merging individuals with: $requestBody');

      final response = await _apiClient.post(
        '/api/v1/cross-video/individuals/tracking/merge',
        data: requestBody,
      );

      print('DEBUG: Individuals merged successfully: ${response.data}');
      
      return ApiResponse.success(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      print('ERROR: Failed to merge individuals: ${e.response?.data}');
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      print('ERROR: Unexpected error merging individuals: $e');
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  /// Batch match and merge individuals using MVR-People matching
  /// 
  /// This endpoint processes a list of individual UUIDs and automatically merges
  /// duplicates based on MVR-People similarity scores. Used for cross-video tracking
  /// to reduce duplicate individuals into unique persons.
  /// 
  /// Returns counters:
  /// - original_count: Number of individuals before merging
  /// - unique_count: Number of unique individuals after merging
  /// - merge_count: Number of duplicates merged
  Future<ApiResponse<Map<String, dynamic>>> batchMatchAndMerge({
    required List<String> individualUuids,
    double threshold = 0.85,
    String triggeredBy = 'cross_video_tracking_session',
    String? sessionUuid,
  }) async {
    try {
      final response = await _apiClient.post(
        '/api/v1/mvr-people/batch-match-and-merge',
        data: {
          'individual_uuids': individualUuids,
          'threshold': threshold,
          'triggered_by': triggeredBy,
          if (sessionUuid != null) 'session_uuid': sessionUuid,
        },
      );

      print('🔄 Batch merge result: ${response.data}');
      
      return ApiResponse.success(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      print('❌ Batch merge failed: ${_handleDioError(e)}');
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      print('❌ Batch merge unexpected error: $e');
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  /// Merge multiple MVR people into one (for hierarchical merges from Individual Groups)
  ///
  /// This method merges multiple MVR people (from Individual Groups) into a single
  /// super-individual by using the hierarchical merge endpoint which calculates
  /// similarity and merges duplicates automatically.
  ///
  /// **Use Case:** When users select multiple members from an Individual Group
  /// and want to merge them into one person in the Cross-Video Analysis screen.
  ///
  /// Returns:
  /// - predominant_individual_uuid: The UUID of the final merged individual
  /// - merged_individual_uuids: List of UUIDs that were merged
  /// - similarity_score: Average similarity score (if available)
  Future<ApiResponse<Map<String, dynamic>>> mergeMVRPeople({
    required List<String> mvrUuids,
    double similarityThreshold = 0.75,
  }) async {
    try {
      if (mvrUuids.length < 2) {
        return ApiResponse.error('At least 2 individuals required for merging');
      }

      print('🔄 Merging ${mvrUuids.length} MVR people hierarchically...');

      final response = await _apiClient.post(
        '/api/v1/mvr-people/merge/hierarchical',
        data: {
          'mvr_uuids': mvrUuids,
          'similarity_threshold': similarityThreshold,
          'min_similarity_check': 0.50,
        },
      );

      print('✅ Hierarchical merge response: ${response.data}');

      // Extract results from hierarchical merge response
      final data = response.data as Map<String, dynamic>;
      final superIndividuals = data['super_individuals'] as List?;
      final statistics = data['statistics'] as Map<String, dynamic>?;

      // Return response in format matching tracking merge
      return ApiResponse.success({
        'predominant_individual_uuid': superIndividuals?.isNotEmpty == true 
            ? superIndividuals![0] 
            : mvrUuids[0],
        'merged_individual_uuids': mvrUuids.sublist(1),
        'similarity_score': similarityThreshold,
        'message': statistics != null
            ? 'Merged ${statistics['merged_mvr']} individuals into ${statistics['super_individuals']} super-individual(s)'
            : 'Successfully merged ${mvrUuids.length} individuals',
        'statistics': statistics,
      });
    } on DioException catch (e) {
      print('❌ MVR merge failed: ${_handleDioError(e)}');
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      print('❌ MVR merge unexpected error: $e');
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  /// Search existing MVR people by collection and date range
  /// 
  /// This endpoint fetches EXISTING MVR people and their linked individuals
  /// that were created within the specified time range for a collection.
  /// It does NOT trigger any merge operations - only retrieves cached data.
  /// 
  /// Use this for the search modal to display existing analysis results
  /// without reprocessing or merging.
  /// 
  /// Returns:
  /// - success: bool
  /// - total_results: int
  /// - mvr_people: List of MVR people with appearances and aggregated data
  /// - search_parameters: Search criteria used
  Future<ApiResponse<Map<String, dynamic>>> searchMVRPeopleByVideos({
    required List<String> videoUuids,
    DateTime? startTime,
    DateTime? endTime,
    int limit = 100,
  }) async {
    try {
      final data = {
        'video_uuids': videoUuids,
        'limit': limit,
      };
      
      if (startTime != null) {
        data['start_time'] = startTime.toIso8601String();
      }
      if (endTime != null) {
        data['end_time'] = endTime.toIso8601String();
      }

      final response = await _apiClient.post(
        '/api/v1/mvr-people/search/by-videos',
        data: data,
      );

      debugPrint('🔍 Search MVR people by videos result: ${response.data}');
      
      return ApiResponse.success(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      debugPrint('❌ Search MVR people by videos failed: ${_handleDioError(e)}');
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      debugPrint('❌ Search MVR people by videos unexpected error: $e');
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  /// Search for existing MVR people by collection (DEPRECATED)
  ///
  /// DEPRECATED: Cannot filter by collection without cross-database queries.
  /// Use searchMVRPeopleByVideos instead.
  @Deprecated('Use searchMVRPeopleByVideos instead')
  Future<ApiResponse<Map<String, dynamic>>> searchMVRPeopleByCollection({
    required String collectionName,
    required DateTime startTime,
    required DateTime endTime,
    int limit = 100,
  }) async {
    try {
      final response = await _apiClient.post(
        '/api/v1/mvr-people/search/by-collection',
        data: {
          'collection_name': collectionName,
          'start_time': startTime.toIso8601String(),
          'end_time': endTime.toIso8601String(),
          'limit': limit,
        },
      );

      print('🔍 Search MVR people result: ${response.data}');
      
      return ApiResponse.success(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      print('❌ Search MVR people failed: ${_handleDioError(e)}');
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      print('❌ Search MVR people unexpected error: $e');
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  /// Get today's MVR people count for a camera
  /// 
  /// Get MVR people count for specific video UUIDs
  /// 
  /// This endpoint queries VMeta's database for unique MVR people
  /// detected across the provided video UUIDs.
  /// 
  /// Returns:
  /// - count: Number of unique MVR people detected
  /// - video_count: Number of videos processed
  Future<ApiResponse<Map<String, dynamic>>> getMVRPeopleCountByVideos({
    required List<String> videoUuids,
  }) async {
    try {
      final response = await _apiClient.post(
        '/api/v1/mvr-people/count-by-videos',
        data: {'video_uuids': videoUuids},
      );

      debugPrint('📊 MVR people count result: ${response.data}');
      
      return ApiResponse.success(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      debugPrint('❌ MVR people count failed: ${_handleDioError(e)}');
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      debugPrint('❌ MVR people count unexpected error: $e');
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  /// Get MVR people count for a camera (DEPRECATED)
  /// 
  /// Returns count of unique MVR people detected today for the specified camera.
  /// Uses the camera's collection and queries appearances within today's timeframe.
  /// 
  /// DEPRECATED: This endpoint has cross-database issues. Use getMVRPeopleCountByVideos instead.
  /// 
  /// Returns:
  /// - camera_id: Camera device ID
  /// - collection_name: Associated collection name
  /// - count: Number of unique MVR people detected today
  /// - date: Date of the count (today)
  /// - start_time: Start of today (00:00:00)
  /// - end_time: End of today (23:59:59)
  @Deprecated('Use getMVRPeopleCountByVideos instead')
  Future<ApiResponse<Map<String, dynamic>>> getCameraMVRPeopleCount({
    required String cameraId,
  }) async {
    try {
      final response = await _apiClient.get(
        '/api/v1/mvr-people/count-by-camera/$cameraId',
      );

      print('📊 Camera MVR people count result: ${response.data}');
      
      return ApiResponse.success(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      print('❌ Camera MVR people count failed: ${_handleDioError(e)}');
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      print('❌ Camera MVR people count unexpected error: $e');
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  /// Get items (videos/images) in a specific collection
  /// 
  /// Returns media items that belong to the specified collection.
  Future<ApiResponse<List<Map<String, dynamic>>>> getCollectionItems({
    required String collectionId,
    int skip = 0,
    int limit = 100,
  }) async {
    try {
      final userId = await _getCurrentUserId();
      if (userId == null) {
        throw Exception('User not authenticated');
      }

      final response = await _apiClient.get(
        '/api/v1/media/collections/$collectionId/items',
        queryParameters: {
          'user_id': userId,
          'skip': skip,
          'limit': limit,
        },
      );

      final items = (response.data as List<dynamic>)
          .map((i) => i as Map<String, dynamic>)
          .toList();
      
      return ApiResponse.success(items);
    } on DioException catch (e) {
      debugPrint('❌ Get collection items failed: ${_handleDioError(e)}');
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      debugPrint('❌ Get collection items unexpected error: $e');
      return ApiResponse.error('Unexpected error: $e');
    }
  }



  /// Invalidate cached MVR count for a camera.
  ///
  /// Use this when you know new detections have been processed
  /// and want to force cache refresh on next request.
  Future<ApiResponse<Map<String, dynamic>>> invalidateCameraMVRCountCache({
    required String cameraId,
    String? date,
  }) async {
    try {
      final queryParams = <String, dynamic>{};
      if (date != null) {
        queryParams['date'] = date;
      }

      final response = await _apiClient.delete(
        '/api/v1/cameras/$cameraId/mvr-count/cache',
        queryParameters: queryParams.isNotEmpty ? queryParams : null,
      );

      debugPrint('🗑️  Camera MVR count cache invalidated: ${response.data}');

      return ApiResponse.success(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      debugPrint('❌ Invalidate cache failed: ${_handleDioError(e)}');
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      debugPrint('❌ Invalidate cache unexpected error: $e');
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  /// Get all cached camera MVR counts for a date.
  ///
  /// Useful for displaying dashboard summaries without
  /// querying each camera individually.
  Future<ApiResponse<Map<String, dynamic>>> getAllCameraMVRCounts({
    String? date,
  }) async {
    try {
      final queryParams = <String, dynamic>{};
      if (date != null) {
        queryParams['date'] = date;
      }

      final response = await _apiClient.get(
        '/api/v1/cameras/mvr-counts/all',
        queryParameters: queryParams.isNotEmpty ? queryParams : null,
      );

      debugPrint('📊 All camera MVR counts result: ${response.data}');

      return ApiResponse.success(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      debugPrint('❌ Get all camera counts failed: ${_handleDioError(e)}');
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      debugPrint('❌ Get all camera counts unexpected error: $e');
      return ApiResponse.error('Unexpected error: $e');
    }
  }
}



/// Single frame face detection result model for real-time detection
class SingleFrameFaceDetectionResult {
  final int frameNumber;
  final List<FaceDetection> faces;
  final double detectionTime;
  final String method;

  SingleFrameFaceDetectionResult({
    required this.frameNumber,
    required this.faces,
    required this.detectionTime,
    required this.method,
  });

  factory SingleFrameFaceDetectionResult.fromJson(Map<String, dynamic> json) {
    return SingleFrameFaceDetectionResult(
      frameNumber: json['frame_number'] ?? 0,
      faces: (json['faces'] as List<dynamic>?)
          ?.map((faceJson) => FaceDetection.fromJson(faceJson))
          .toList() ?? [],
      detectionTime: (json['detection_time'] ?? 0.0).toDouble(),
      method: json['method'] ?? 'real_time_detection',
    );
  }
}

/// Bulk face detection workflow result model for optimized video processing
class BulkFaceDetectionWorkflowResult {
  final String workflowId;
  final String status; // queued, processing, completed, failed
  final int mediaCount;
  final String createdAt;
  final String? estimatedCompletionTime;
  final Map<String, dynamic> processingOptions;
  final String? errorMessage;
  final Map<String, dynamic>? resultsSummary;

  BulkFaceDetectionWorkflowResult({
    required this.workflowId,
    required this.status,
    required this.mediaCount,
    required this.createdAt,
    this.estimatedCompletionTime,
    required this.processingOptions,
    this.errorMessage,
    this.resultsSummary,
  });

  factory BulkFaceDetectionWorkflowResult.fromJson(Map<String, dynamic> json) {
    return BulkFaceDetectionWorkflowResult(
      workflowId: json['workflow_id'] ?? '',
      status: json['status'] ?? 'unknown',
      mediaCount: json['media_count'] ?? 0,
      createdAt: json['created_at'] ?? '',
      estimatedCompletionTime: json['estimated_completion_time'],
      processingOptions: json['processing_options'] ?? {},
      errorMessage: json['error_message'],
      resultsSummary: json['results_summary'],
    );
  }

  bool get isCompleted => status == 'completed';
  bool get isFailed => status == 'failed';
  bool get isProcessing => status == 'processing';
  bool get isQueued => status == 'queued';
}

/// Face detection model for single face result
class FaceDetection {
  final String? id;
  final String? mediaId;
  final FaceBoundingBox boundingBox;
  final double confidence;
  final String method;
  final DateTime? timestamp;
  final Map<String, dynamic>? metadata;

  FaceDetection({
    this.id,
    this.mediaId,
    required this.boundingBox,
    required this.confidence,
    required this.method,
    this.timestamp,
    this.metadata,
  });

  factory FaceDetection.fromJson(Map<String, dynamic> json) {
    return FaceDetection(
      id: json['id'],
      mediaId: json['media_id'],
      boundingBox: FaceBoundingBox.fromJson(json['bbox'] ?? [0, 0, 0, 0]),
      confidence: (json['confidence'] ?? 0.0).toDouble(),
      method: json['method'] ?? 'unknown',
      timestamp: json['timestamp'] != null ? DateTime.parse(json['timestamp']) : null,
      metadata: json['metadata'],
    );
  }
}

/// Bounding box for face detection
class FaceBoundingBox {
  final double left;
  final double top;
  final double width;
  final double height;

  FaceBoundingBox({
    required this.left,
    required this.top,
    required this.width,
    required this.height,
  });

  factory FaceBoundingBox.fromJson(List<dynamic> bbox) {
    if (bbox.length >= 4) {
      // ✅ FIX ISSUE 2: bbox format is [left, top, right, bottom] not [left, top, width, height]
      final left = (bbox[0] ?? 0.0).toDouble();
      final top = (bbox[1] ?? 0.0).toDouble();
      final right = (bbox[2] ?? 0.0).toDouble();
      final bottom = (bbox[3] ?? 0.0).toDouble();
      
      return FaceBoundingBox(
        left: left,
        top: top,
        width: right - left,  // Calculate width from right - left
        height: bottom - top, // Calculate height from bottom - top
      );
    }
    return FaceBoundingBox(left: 0, top: 0, width: 0, height: 0);
  }
}
