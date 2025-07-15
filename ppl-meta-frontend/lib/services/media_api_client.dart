import 'package:dio/dio.dart';
import 'package:http_parser/http_parser.dart' as http_parser;
import '../models/api_response.dart';
import '../models/media_models.dart';
import '../models/device_info.dart';
import '../core/config/app_config.dart';
import '../core/api/api_client.dart';

/// API client for media operations
class MediaApiClient {
  late final Dio _dio;
  final ApiClient? _apiClient;
  
  MediaApiClient({ApiClient? apiClient}) : _apiClient = apiClient {
    _dio = Dio(BaseOptions(
      baseUrl: AppConfig.instance.mediaEndpoint,
      connectTimeout: const Duration(seconds: 30),
      receiveTimeout: const Duration(seconds: 30),
      headers: {
        'Content-Type': 'application/json',
      },
    ));
    
    // Add interceptors for logging and authentication
    if (AppConfig.instance.isDevelopment) {
      _dio.interceptors.add(LogInterceptor(
        requestBody: true,
        responseBody: true,
        logPrint: (o) => print(o),
      ));
    }
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

      final response = await _dio.post(
        '/upload',
        data: formData,
        onSendProgress: (sent, total) {
          if (onProgress != null) onProgress(sent, total);
          if (onProgressPercent != null && total > 0) {
            onProgressPercent(sent / total);
          }
        },
      );

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

      final response = await _dio.get('/items', queryParameters: queryParams);
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
      final response = await _dio.get('/items/$id');
      return ApiResponse.success(MediaItem.fromJson(response.data));
    } on DioException catch (e) {
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  /// Delete media item
  Future<ApiResponse<void>> deleteMediaItem(String id) async {
    try {
      await _dio.delete('/items/$id');
      return ApiResponse.success(null);
    } on DioException catch (e) {
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  /// Get collections
  Future<ApiResponse<List<MediaCollection>>> getCollections() async {
    try {
      final response = await _dio.get('/collections');
      final collections = (response.data as List)
          .map((json) => MediaCollection.fromJson(json))
          .toList();
      return ApiResponse.success(collections);
    } on DioException catch (e) {
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
      final response = await _dio.post('/collections', data: {
        'name': name,
        if (description != null) 'description': description,
      });
      return ApiResponse.success(MediaCollection.fromJson(response.data));
    } on DioException catch (e) {
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  /// Add items to collection
  Future<ApiResponse<void>> addItemsToCollection({
    required String collectionId,
    required List<String> itemIds,
  }) async {
    try {
      await _dio.post('/collections/$collectionId/items', data: {
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

      final response = await _dio.get('/analytics', queryParameters: queryParams);
      return ApiResponse.success(MediaAnalytics.fromJson(response.data));
    } on DioException catch (e) {
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  /// Search media with suggestions
  Future<ApiResponse<MediaSearchResponse>> searchMedia({
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
      final requestData = <String, dynamic>{
        'page': page,
        'limit': limit,
        if (query != null && query.isNotEmpty) 'query': query,
        if (mediaType != null) 'media_type': mediaType.name,
        if (startDate != null) 'start_date': startDate.toIso8601String(),
        if (endDate != null) 'end_date': endDate.toIso8601String(),
        if (tags != null && tags.isNotEmpty) 'tags': tags,
        if (collectionId != null) 'collection_id': collectionId,
        if (sortBy != null) 'sort_by': sortBy,
        if (sortOrder != null) 'sort_order': sortOrder,
        if (filters != null) ...filters.toJson(),
      };

      final response = await _dio.post('/search', data: requestData);
      return ApiResponse.success(MediaSearchResponse.fromJson(response.data));
    } on DioException catch (e) {
      return ApiResponse.error(_handleDioError(e));
    } catch (e) {
      return ApiResponse.error('Unexpected error: $e');
    }
  }

  /// Get search suggestions
  Future<ApiResponse<List<String>>> getSearchSuggestions(String query) async {
    try {
      final response = await _dio.get('/search/suggestions', queryParameters: {
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
      final response = await _dio.post('/share', data: {
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

      final response = await _dio.get('/device-analytics', queryParameters: queryParams);
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
      await _dio.delete('/collections/$collectionId');
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
      final response = await _dio.put('/collections/$collectionId', data: {
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
      await _dio.post('/share/email', data: {
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
      case DioExceptionType.receiveTimeout:
        return 'Server response timeout. Please try again.';
      case DioExceptionType.badResponse:
        final statusCode = error.response?.statusCode;
        switch (statusCode) {
          case 400:
            return 'Invalid request. Please check your input.';
          case 401:
            return 'Authentication required. Please login again.';
          case 403:
            return 'Access denied. You don\'t have permission for this action.';
          case 404:
            return 'Resource not found.';
          case 413:
            return 'File too large. Please choose a smaller file.';
          case 429:
            return 'Too many requests. Please wait and try again.';
          case 500:
            return 'Server error. Please try again later.';
          default:
            return 'Request failed with status: $statusCode';
        }
      case DioExceptionType.cancel:
        return 'Request was cancelled.';
      case DioExceptionType.unknown:
        return 'Network error. Please check your connection.';
      default:
        return 'An unexpected error occurred.';
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
      // Use ApiClient if available (has authentication) or fallback to direct call
      if (_apiClient != null) {
        final response = await _apiClient!.get('/api/v1/user/profile');
        if (response.data != null) {
          // Extract user_id from profile response - use 'guid' (UUID) instead of 'id' (integer)
          return response.data['guid']?.toString();
        }
      } else {
        // Fallback: create a temporary dio client that uses Gateway service 
        final userDio = Dio(BaseOptions(
          baseUrl: 'http://localhost:8080/api/v1',
          connectTimeout: const Duration(seconds: 10),
          receiveTimeout: const Duration(seconds: 10),
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
          },
        ));
        
        // Copy authentication headers from main client
        final authHeader = _dio.options.headers['Authorization'];
        if (authHeader != null) {
          userDio.options.headers['Authorization'] = authHeader;
        }
        
        // Get user profile to extract user ID
        final response = await userDio.get('/users/profile');
        if (response.data != null) {
          // Extract user_id from profile response - use 'guid' (UUID) instead of 'id' (integer)
          return response.data['guid']?.toString();
        }
      }
    } catch (e) {
      print('Failed to get current user ID: $e');
    }
    return null;
  }
}
