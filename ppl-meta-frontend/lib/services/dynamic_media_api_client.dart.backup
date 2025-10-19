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
import '../core/api/dynamic_api_client.dart';
import '../utils/download_helper_web.dart' if (dart.library.io) '../utils/download_helper_stub.dart';

/// Enhanced media API client with dynamic service discovery
class DynamicMediaApiClient {
  final DynamicApiClient _apiClient;
  
  DynamicMediaApiClient(this._apiClient);

  /// Upload media file with dynamic service discovery
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
        // Upload from file path (mobile/desktop)
        file = await MultipartFile.fromFile(
          filePath,
          filename: finalFilename,
          contentType: mimeType != null ? http_parser.MediaType.parse(mimeType) : null,
        );
      } else {
        throw ArgumentError('Either filePath or fileBytes must be provided');
      }

      // Create form data
      final formData = FormData();
      formData.files.add(MapEntry('file', file));
      
      // Add metadata
      if (metadata != null) {
        for (final entry in metadata.entries) {
          formData.fields.add(MapEntry(entry.key, entry.value.toString()));
        }
      }
      
      // Add collection ID if provided
      if (collectionId != null) {
        formData.fields.add(MapEntry('collection_id', collectionId));
      }
      
      // Add device info if provided
      if (deviceInfo != null) {
        formData.fields.add(MapEntry('device_info', deviceInfo.toJson().toString()));
      }

      // Make request to media service with progress tracking
      final response = await _apiClient.requestToService<Map<String, dynamic>>(
        'media',
        'POST',
        '/api/v1/media/upload',
        data: formData,
        options: Options(
          headers: {'Content-Type': 'multipart/form-data'},
        ),
      );

      if (response.statusCode == 200 || response.statusCode == 201) {
        final mediaItem = MediaItem.fromJson(response.data!['data']);
        return ApiResponse.success(mediaItem);
      } else {
        return ApiResponse.error(
          'Upload failed with status ${response.statusCode}',
          response.statusCode,
        );
      }
    } catch (e) {
      return ApiResponse.error('Upload failed: $e');
    }
  }

  /// Get media items with pagination and dynamic service discovery
  Future<ApiResponse<PaginatedResponse<MediaItem>>> getMediaItems({
    int page = 1,
    int limit = 20,
    String? collectionId,
    List<String>? tags,
    String? searchQuery,
    String? sortBy,
    String? sortOrder,
    DateTime? startDate,
    DateTime? endDate,
    String? mediaType,
  }) async {
    try {
      final queryParams = <String, dynamic>{
        'page': page,
        'limit': limit,
      };

      if (collectionId != null) queryParams['collection_id'] = collectionId;
      if (tags != null && tags.isNotEmpty) queryParams['tags'] = tags.join(',');
      if (searchQuery != null) queryParams['search'] = searchQuery;
      if (sortBy != null) queryParams['sort_by'] = sortBy;
      if (sortOrder != null) queryParams['sort_order'] = sortOrder;
      if (startDate != null) queryParams['start_date'] = startDate.toIso8601String();
      if (endDate != null) queryParams['end_date'] = endDate.toIso8601String();
      if (mediaType != null) queryParams['media_type'] = mediaType;

      final response = await _apiClient.requestToService<Map<String, dynamic>>(
        'media',
        'GET',
        '/api/v1/media',
        queryParameters: queryParams,
      );

      if (response.statusCode == 200) {
        final data = response.data!['data'];
        final items = (data['items'] as List)
            .map((item) => MediaItem.fromJson(item))
            .toList();
        
        final paginatedResponse = PaginatedResponse<MediaItem>(
          items: items,
          page: data['page'],
          limit: data['limit'],
          totalItems: data['total_items'],
          totalPages: data['total_pages'],
          hasNext: data['has_next'],
          hasPrevious: data['has_previous'],
        );
        
        return ApiResponse.success(paginatedResponse);
      } else {
        return ApiResponse.error(
          'Failed to get media items with status ${response.statusCode}',
          response.statusCode,
        );
      }
    } catch (e) {
      return ApiResponse.error('Failed to get media items: $e');
    }
  }

  /// Get media item by ID with dynamic service discovery
  Future<ApiResponse<MediaItem>> getMediaItem(String mediaId) async {
    try {
      final response = await _apiClient.requestToService<Map<String, dynamic>>(
        'media',
        'GET',
        '/api/v1/media/$mediaId',
      );

      if (response.statusCode == 200) {
        final mediaItem = MediaItem.fromJson(response.data!['data']);
        return ApiResponse.success(mediaItem);
      } else {
        return ApiResponse.error(
          'Failed to get media item with status ${response.statusCode}',
          response.statusCode,
        );
      }
    } catch (e) {
      return ApiResponse.error('Failed to get media item: $e');
    }
  }

  /// Delete media item with dynamic service discovery
  Future<ApiResponse<bool>> deleteMediaItem(String mediaId) async {
    try {
      final response = await _apiClient.requestToService<Map<String, dynamic>>(
        'media',
        'DELETE',
        '/api/v1/media/$mediaId',
      );

      if (response.statusCode == 200 || response.statusCode == 204) {
        return ApiResponse.success(true);
      } else {
        return ApiResponse.error(
          'Failed to delete media item with status ${response.statusCode}',
          response.statusCode,
        );
      }
    } catch (e) {
      return ApiResponse.error('Failed to delete media item: $e');
    }
  }

  /// Get collections with dynamic service discovery
  Future<ApiResponse<List<Collection>>> getCollections() async {
    try {
      final response = await _apiClient.requestToService<Map<String, dynamic>>(
        'media',
        'GET',
        '/api/v1/collections',
      );

      if (response.statusCode == 200) {
        final collections = (response.data!['data'] as List)
            .map((item) => Collection.fromJson(item))
            .toList();
        return ApiResponse.success(collections);
      } else {
        return ApiResponse.error(
          'Failed to get collections with status ${response.statusCode}',
          response.statusCode,
        );
      }
    } catch (e) {
      return ApiResponse.error('Failed to get collections: $e');
    }
  }

  /// Create collection with dynamic service discovery
  Future<ApiResponse<Collection>> createCollection({
    required String name,
    String? description,
    Map<String, dynamic>? metadata,
  }) async {
    try {
      final data = {
        'name': name,
        if (description != null) 'description': description,
        if (metadata != null) 'metadata': metadata,
      };

      final response = await _apiClient.requestToService<Map<String, dynamic>>(
        'media',
        'POST',
        '/api/v1/collections',
        data: data,
      );

      if (response.statusCode == 200 || response.statusCode == 201) {
        final collection = Collection.fromJson(response.data!['data']);
        return ApiResponse.success(collection);
      } else {
        return ApiResponse.error(
          'Failed to create collection with status ${response.statusCode}',
          response.statusCode,
        );
      }
    } catch (e) {
      return ApiResponse.error('Failed to create collection: $e');
    }
  }

  /// Get media service health status
  Future<ApiResponse<Map<String, dynamic>>> getHealthStatus() async {
    try {
      final response = await _apiClient.requestToService<Map<String, dynamic>>(
        'media',
        'GET',
        '/health',
      );

      if (response.statusCode == 200) {
        return ApiResponse.success(response.data!);
      } else {
        return ApiResponse.error(
          'Health check failed with status ${response.statusCode}',
          response.statusCode,
        );
      }
    } catch (e) {
      return ApiResponse.error('Health check failed: $e');
    }
  }

  /// Download media file (platform-specific implementation)
  Future<ApiResponse<String>> downloadMedia(String mediaId, {String? filename}) async {
    try {
      // Get the media service URL dynamically
      final response = await _apiClient.requestToService<List<int>>(
        'media',
        'GET',
        '/api/v1/media/$mediaId/download',
        options: Options(responseType: ResponseType.bytes),
      );

      if (response.statusCode == 200) {
        if (kIsWeb) {
          // Web download using browser
          downloadFileWeb(response.data!, filename ?? 'media_$mediaId');
          return ApiResponse.success('Download started');
        } else {
          // Mobile/Desktop download to file system
          final dir = await getApplicationDocumentsDirectory();
          final file = File('${dir.path}/${filename ?? 'media_$mediaId'}');
          await file.writeAsBytes(response.data!);
          return ApiResponse.success(file.path);
        }
      } else {
        return ApiResponse.error(
          'Download failed with status ${response.statusCode}',
          response.statusCode,
        );
      }
    } catch (e) {
      return ApiResponse.error('Download failed: $e');
    }
  }
}

/// Provider for dynamic media API client
final dynamicMediaApiClientProvider = Provider<DynamicMediaApiClient>((ref) {
  final apiClient = ref.watch(dynamicApiClientProvider);
  return DynamicMediaApiClient(apiClient);
});
