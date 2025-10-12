import 'dart:io';
import 'dart:typed_data';
import 'package:dio/dio.dart';
import 'package:logger/logger.dart';
import '../models/media_models.dart';
import '../models/device_info.dart';
import '../models/api_response.dart';

/// Media Service API Client for PPL Meta Platform
class MediaApiClient {
  late final Dio _dio;
  final Logger _logger = Logger();
  
  static const String _baseUrl = 'http://localhost:8000/api/v1';
  static const Duration _connectTimeout = Duration(seconds: 30);
  static const Duration _receiveTimeout = Duration(minutes: 5);
  
  MediaApiClient() {
    _dio = Dio(BaseOptions(
      baseUrl: _baseUrl,
      connectTimeout: _connectTimeout,
      receiveTimeout: _receiveTimeout,
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    ));
    
    // Add interceptors for logging and error handling
    _dio.interceptors.add(_createLoggingInterceptor());
    _dio.interceptors.add(_createErrorInterceptor());
  }
  
  /// Upload media file with device metadata
  Future<MediaUploadResponse> uploadMedia({
    required File file,
    required DeviceInfo deviceInfo,
    String? userId,
    List<String>? tags,
    bool isPublic = false,
    String? description,
  }) async {
    try {
      _logger.i('Uploading media file: ${file.path}');
      
      // Determine media type from file extension
      final mediaType = _getMediaTypeFromFilename(file.path);
      
      // Get current user ID from authentication if not provided
      final currentUserId = userId ?? await _getCurrentUserId();
      if (currentUserId == null) {
        throw Exception('User not authenticated - please login first');
      }
      
      final formData = FormData.fromMap({
        'file': await MultipartFile.fromFile(
          file.path,
          filename: file.path.split('/').last,
        ),
        'media_type': mediaType,     // Required field for backend validation
        'user_id': currentUserId,    // Required field for backend validation
        'device_name': deviceInfo.deviceName,
        'device_manufacturer': deviceInfo.deviceManufacturer,
        'device_model': deviceInfo.deviceModel,
        'device_os': deviceInfo.deviceOs,
        'app_name': deviceInfo.appName,
        'app_version': deviceInfo.appVersion,
        if (tags != null) 'tags': tags.join(','),
        'is_public': isPublic.toString(),
        if (description != null) 'description': description,
      });
      
      final response = await _dio.post(
        '/media/upload',
        data: formData,
        options: Options(
          headers: {'Content-Type': 'multipart/form-data'},
        ),
      );
      
      _logger.i('Media upload successful: ${response.data['media_id']}');
      return MediaUploadResponse.fromJson(response.data);
      
    } on DioException catch (e) {
      _logger.e('Media upload failed: ${e.message}');
      throw _handleDioError(e);
    }
  }
  
  /// Search media with filters
  Future<MediaSearchResponse> searchMedia({
    String? query,
    List<String>? mediaTypes,
    List<String>? deviceManufacturers,
    List<String>? deviceModels,
    String? uploadedBy,
    DateTime? uploadedAfter,
    DateTime? uploadedBefore,
    List<String>? tags,
    int? limit = 50,
    int? offset = 0,
  }) async {
    try {
      final queryParams = <String, dynamic>{
        if (query != null) 'query': query,
        if (mediaTypes != null) 'media_types': mediaTypes.join(','),
        if (deviceManufacturers != null) 'device_manufacturers': deviceManufacturers.join(','),
        if (deviceModels != null) 'device_models': deviceModels.join(','),
        if (uploadedBy != null) 'uploaded_by': uploadedBy,
        if (uploadedAfter != null) 'uploaded_after': uploadedAfter.toIso8601String(),
        if (uploadedBefore != null) 'uploaded_before': uploadedBefore.toIso8601String(),
        if (tags != null) 'tags': tags.join(','),
        if (limit != null) 'limit': limit,
        if (offset != null) 'offset': offset,
      };
      
      final response = await _dio.get(
        '/media/search',
        queryParameters: queryParams,
      );
      
      return MediaSearchResponse.fromJson(response.data);
      
    } on DioException catch (e) {
      _logger.e('Media search failed: ${e.message}');
      throw _handleDioError(e);
    }
  }
  
  /// Get media by ID
  Future<MediaItem> getMedia(String mediaId, {String? userId}) async {
    try {
      final queryParams = <String, dynamic>{
        if (userId != null) 'user_id': userId,
      };
      
      final response = await _dio.get(
        '/media/$mediaId',
        queryParameters: queryParams,
      );
      
      return MediaItem.fromJson(response.data);
      
    } on DioException catch (e) {
      _logger.e('Get media failed: ${e.message}');
      throw _handleDioError(e);
    }
  }
  
  /// Get device analytics
  Future<DeviceAnalytics> getDeviceAnalytics({String? userId}) async {
    try {
      final queryParams = <String, dynamic>{
        if (userId != null) 'user_id': userId,
      };
      
      final response = await _dio.get(
        '/analytics/device',
        queryParameters: queryParams,
      );
      
      return DeviceAnalytics.fromJson(response.data);
      
    } on DioException catch (e) {
      _logger.e('Get device analytics failed: ${e.message}');
      throw _handleDioError(e);
    }
  }
  
  /// Create media collection
  Future<MediaCollection> createCollection({
    required String name,
    String? description,
    required List<String> mediaIds,
    String? userId,
  }) async {
    try {
      final formData = FormData.fromMap({
        'name': name,
        if (description != null) 'description': description,
        'media_ids': mediaIds.join(','),
        if (userId != null) 'user_id': userId,
      });
      
      final response = await _dio.post(
        '/collections',
        data: formData,
        options: Options(
          headers: {'Content-Type': 'multipart/form-data'},
        ),
      );
      
      return MediaCollection.fromJson(response.data);
      
    } on DioException catch (e) {
      _logger.e('Create collection failed: ${e.message}');
      throw _handleDioError(e);
    }
  }
  
  /// Share media
  Future<ShareResponse> shareMedia({
    required String mediaId,
    required List<String> permissions,
    DateTime? expiresAt,
    String? userId,
  }) async {
    try {
      final requestData = {
        'media_id': mediaId,
        'permissions': permissions,
        if (expiresAt != null) 'expires_at': expiresAt.toIso8601String(),
        if (userId != null) 'user_id': userId,
      };
      
      final response = await _dio.post(
        '/shares',
        data: requestData,
      );
      
      return ShareResponse.fromJson(response.data);
      
    } on DioException catch (e) {
      _logger.e('Share media failed: ${e.message}');
      throw _handleDioError(e);
    }
  }
  
  /// Get thumbnail URL
  String getThumbnailUrl(String mediaId, {String size = 'medium'}) {
    return '$_baseUrl/media/thumbnail/$mediaId?size=$size';
  }
  
  /// Get download URL
  String getDownloadUrl(String mediaId) {
    return '$_baseUrl/media/download/$mediaId';
  }
  
  /// Get streaming URL
  String getStreamingUrl(String mediaId) {
    return '$_baseUrl/media/stream/$mediaId';
  }
  
  /// Create logging interceptor
  Interceptor _createLoggingInterceptor() {
    return InterceptorsWrapper(
      onRequest: (options, handler) {
        _logger.d('Request: ${options.method} ${options.path}');
        _logger.d('Headers: ${options.headers}');
        if (options.data != null && options.data is! FormData) {
          _logger.d('Data: ${options.data}');
        }
        handler.next(options);
      },
      onResponse: (response, handler) {
        _logger.d('Response: ${response.statusCode} ${response.requestOptions.path}');
        handler.next(response);
      },
      onError: (error, handler) {
        _logger.e('Error: ${error.requestOptions.path} - ${error.message}');
        handler.next(error);
      },
    );
  }
  
  /// Create error handling interceptor
  Interceptor _createErrorInterceptor() {
    return InterceptorsWrapper(
      onError: (error, handler) {
        final apiError = _handleDioError(error);
        handler.reject(DioException(
          requestOptions: error.requestOptions,
          error: apiError,
          type: error.type,
        ));
      },
    );
  }
  
  /// Handle Dio errors and convert to API errors
  ApiError _handleDioError(DioException error) {
    switch (error.type) {
      case DioExceptionType.connectionTimeout:
      case DioExceptionType.sendTimeout:
      case DioExceptionType.receiveTimeout:
        return ApiError(
          code: 'TIMEOUT',
          message: 'Request timeout. Please check your connection.',
          statusCode: 408,
        );
      
      case DioExceptionType.badResponse:
        final statusCode = error.response?.statusCode ?? 500;
        final data = error.response?.data;
        
        if (data is Map<String, dynamic> && data.containsKey('detail')) {
          return ApiError(
            code: 'API_ERROR',
            message: data['detail'].toString(),
            statusCode: statusCode,
          );
        }
        
        return ApiError(
          code: 'HTTP_ERROR',
          message: 'Server error: $statusCode',
          statusCode: statusCode,
        );
      
      case DioExceptionType.cancel:
        return ApiError(
          code: 'CANCELLED',
          message: 'Request was cancelled',
          statusCode: 0,
        );
      
      case DioExceptionType.connectionError:
        return ApiError(
          code: 'CONNECTION_ERROR',
          message: 'Connection failed. Please check your internet connection.',
          statusCode: 0,
        );
      
      default:
        return ApiError(
          code: 'UNKNOWN_ERROR',
          message: error.message ?? 'An unknown error occurred',
          statusCode: 0,
        );
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
  
  /// Get current user ID from authentication context
  Future<String?> _getCurrentUserId() async {
    try {
      // Call Gateway service for user profile (not media service)
      final gatewayDio = Dio(BaseOptions(
        baseUrl: 'http://localhost:8080',
        connectTimeout: _connectTimeout,
        receiveTimeout: _receiveTimeout,
        headers: _dio.options.headers,
      ));
      
      final response = await gatewayDio.get('/api/v1/user/profile');
      if (response.data != null) {
        // Extract user_id from profile response - use 'guid' (UUID)
        return response.data['guid']?.toString();
      }
    } catch (e) {
      _logger.w('Failed to get current user ID: $e');
    }
    return null;
  }
}
