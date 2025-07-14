import 'package:dio/dio.dart';
import '../models/api_response.dart';
import '../models/media_models.dart';
import '../core/config/app_config.dart';

/// API client for media operations
class MediaApiClient {
  late final Dio _dio;
  
  MediaApiClient() {
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
    required String filePath,
    required String filename,
    Map<String, dynamic>? metadata,
    String? collectionId,
    Function(int, int)? onProgress,
  }) async {
    try {
      final formData = FormData.fromMap({
        'file': await MultipartFile.fromFile(filePath, filename: filename),
        if (metadata != null) 'metadata': metadata,
        if (collectionId != null) 'collection_id': collectionId,
      });

      final response = await _dio.post(
        '/upload',
        data: formData,
        onSendProgress: onProgress,
      );

      return ApiResponse.success(MediaItem.fromJson(response.data));
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
    required String query,
    MediaSearchFilters? filters,
    int page = 1,
    int limit = 20,
  }) async {
    try {
      final requestData = <String, dynamic>{
        'query': query,
        'page': page,
        'limit': limit,
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
}
