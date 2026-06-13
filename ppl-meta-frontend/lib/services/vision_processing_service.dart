import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import '../core/config.dart';

/// Service for processing media with Vision AI (VMeta Single-Media MVR endpoint)
class VisionProcessingService extends ChangeNotifier {
  final Dio _dio;
  final String? _authToken;
  
  // State
  bool _isProcessing = false;
  int _currentProgress = 0;
  int _totalItems = 0;
  String? _currentMediaId;
  
  // Getters
  bool get isProcessing => _isProcessing;
  int get currentProgress => _currentProgress;
  int get totalItems => _totalItems;
  String? get currentMediaId => _currentMediaId;
  double get progressPercent => 
      _totalItems > 0 ? _currentProgress / _totalItems : 0.0;
  
  VisionProcessingService({Dio? dio, String? authToken}) 
      : _dio = dio ?? Dio(),
        _authToken = authToken;
  
  /// Process selected media with Vision AI
  Future<VisionProcessingResult> processSelectedMedia({
    required List<String> mediaIds,
    double? similarityThreshold,
    double? minFaceQuality,
    bool includeDemographics = true,
    bool includeRouteData = true,
    String? authToken,
  }) async {
    _isProcessing = true;
    _currentProgress = 0;
    _totalItems = mediaIds.length;
    notifyListeners();
    
    try {
      // Use token from parameter if provided, otherwise use stored token
      final token = authToken ?? _authToken ?? '';
      
      print('🔍 Vision Processing Service: Starting processing...');
      print('   Media IDs count: ${mediaIds.length}');
      print('   Media IDs: $mediaIds');
      print('   Endpoint: ${Config.vmetaServiceUrl}/api/v1/mvr-people/process-media');
      
      // Call VMeta Single-Media MVR endpoint
      final response = await _dio.post(
        '${Config.vmetaServiceUrl}/api/v1/mvr-people/process-media',
        options: Options(
          headers: {
            'Authorization': 'Bearer $token',
            'Content-Type': 'application/json',
          },
          receiveTimeout: const Duration(seconds: 300), // 5 minutes timeout
          sendTimeout: const Duration(seconds: 60),
        ),
        data: {
          'media_uuids': mediaIds,
          'processing_options': {
            'similarity_threshold': similarityThreshold ?? 0.8,
            'min_face_quality': minFaceQuality ?? 0.20,
            'include_demographics': includeDemographics,
            'include_route_data': includeRouteData,
          },
        },
      );
      
      print('✅ Vision Processing Service: Received response');
      print('   Status code: ${response.statusCode}');
      
      // Parse response
      final data = response.data;
      print('📦 Response data type: ${data.runtimeType}');
      print('📦 Response keys: ${data is Map ? data.keys.toList() : "not a map"}');
      
      // Update progress to 100%
      _currentProgress = _totalItems;
      notifyListeners();
      
      // Create result object
      final result = VisionProcessingResult.fromJson(data);
      
      print('📊 Vision Processing Result:');
      print('   Success: ${result.success}');
      print('   Processed: ${result.processedMedia}/${_totalItems}');
      print('   Failed: ${result.failedMedia}');
      print('   MVR People Created: ${result.mvrPeopleCount}');
      
      // Log any errors from failed media
      if (result.failedMedia > 0) {
        print('⚠️ Failed media details:');
        for (final mediaResult in result.results.where((r) => r.isFailed)) {
          print('   • ${mediaResult.mediaUuid}: ${mediaResult.error}');
        }
      }
      
      return result;
      
    } on DioException catch (e) {
      print('❌ Vision Processing Service: DioException');
      print('   Type: ${e.type}');
      print('   Message: ${e.message}');
      print('   Response: ${e.response?.data}');
      
      throw VisionProcessingException(
        message: _parseDioError(e),
        originalError: e,
      );
    } catch (e) {
      print('❌ Vision Processing Service: Unexpected error');
      print('   Error: $e');
      
      throw VisionProcessingException(
        message: 'Unexpected error: ${e.toString()}',
        originalError: e,
      );
    } finally {
      _isProcessing = false;
      _currentProgress = 0;
      _totalItems = 0;
      _currentMediaId = null;
      notifyListeners();
    }
  }
  
  String _parseDioError(DioException e) {
    if (e.type == DioExceptionType.connectionTimeout ||
        e.type == DioExceptionType.receiveTimeout) {
      return 'Request timed out. Processing may take longer for many media items.';
    } else if (e.type == DioExceptionType.connectionError) {
      return 'Unable to connect to Vision service. Check your connection.';
    } else if (e.response != null) {
      final statusCode = e.response!.statusCode;
      if (statusCode == 401) {
        return 'Authentication failed. Please log in again.';
      } else if (statusCode == 403) {
        return 'Permission denied. You do not have access to this feature.';
      } else if (statusCode == 400) {
        final message = e.response!.data['message'] ?? 
                       e.response!.data['detail'] ?? 
                       'Invalid request';
        return message;
      } else if (statusCode! >= 500) {
        return 'Server error. Please try again later.';
      }
    }
    return 'An unexpected error occurred: ${e.message}';
  }
}

/// Result of vision processing operation
class VisionProcessingResult {
  final bool success;
  final int totalMedia;
  final int processedMedia;
  final int failedMedia;
  final int mvrPeopleCount;
  final double processingTimeSeconds;
  final List<MediaProcessingResult> results;
  final Map<String, dynamic> aggregateStatistics;
  
  VisionProcessingResult({
    required this.success,
    required this.totalMedia,
    required this.processedMedia,
    required this.failedMedia,
    required this.mvrPeopleCount,
    required this.processingTimeSeconds,
    required this.results,
    required this.aggregateStatistics,
  });
  
  factory VisionProcessingResult.fromJson(Map<String, dynamic> json) {
    // Calculate MVR people count from aggregate_statistics or results
    int mvrCount = 0;
    
    // First try aggregate_statistics.total_mvr_people_created (Single-Media MVR endpoint)
    final aggStats = json['aggregate_statistics'] as Map<String, dynamic>?;
    if (aggStats != null && aggStats.containsKey('total_mvr_people_created')) {
      mvrCount = aggStats['total_mvr_people_created'] ?? 0;
    } else {
      // Fallback: Calculate from results array
      final resultsList = json['results'] as List?;
      if (resultsList != null) {
        for (final result in resultsList) {
          final mvrPeople = result['mvr_people'] as List?;
          if (mvrPeople != null) {
            mvrCount += mvrPeople.length;
          }
        }
      }
    }
    
    return VisionProcessingResult(
      success: json['success'] ?? false,
      totalMedia: json['total_media'] ?? 0,
      processedMedia: json['processed_media'] ?? 0,
      failedMedia: json['failed_media'] ?? 0,
      mvrPeopleCount: mvrCount,
      processingTimeSeconds: (json['processing_time_seconds'] ?? 0).toDouble(),
      results: (json['results'] as List?)
          ?.map((r) => MediaProcessingResult.fromJson(r))
          .toList() ?? [],
      aggregateStatistics: json['aggregate_statistics'] ?? {},
    );
  }
}

/// Result for individual media item
class MediaProcessingResult {
  final String mediaUuid;
  final String mediaType;
  final String status;
  final int mvrPeopleCount;
  final int totalFacesDetected;
  final double? processingTimeMs;
  final String? error;
  final List<Map<String, dynamic>> mvrPeople; // Full MVR people data
  
  MediaProcessingResult({
    required this.mediaUuid,
    required this.mediaType,
    required this.status,
    required this.mvrPeopleCount,
    required this.totalFacesDetected,
    this.processingTimeMs,
    this.error,
    this.mvrPeople = const [],
  });
  
  factory MediaProcessingResult.fromJson(Map<String, dynamic> json) {
    // Handle error field which can be a String or an object
    String? errorMessage;
    final errorField = json['error'];
    if (errorField != null) {
      if (errorField is String) {
        errorMessage = errorField;
      } else if (errorField is Map) {
        // If error is a map, try to extract message or detail
        errorMessage = errorField['message']?.toString() ?? 
                      errorField['detail']?.toString() ?? 
                      errorField.toString();
      } else {
        errorMessage = errorField.toString();
      }
    }
    
    return MediaProcessingResult(
      mediaUuid: json['media_uuid'] ?? '',
      mediaType: json['media_type'] ?? 'unknown',
      status: json['status'] ?? 'unknown',
      mvrPeopleCount: json['mvr_people_count'] ?? 0,
      totalFacesDetected: json['total_faces_detected'] ?? 0,
      processingTimeMs: json['processing_time_ms']?.toDouble(),
      error: errorMessage,
      mvrPeople: (json['mvr_people'] as List?)?.cast<Map<String, dynamic>>() ?? [],
    );
  }
  
  bool get isSuccess => status == 'completed';
  bool get isFailed => status == 'failed';
}

/// Exception thrown during vision processing
class VisionProcessingException implements Exception {
  final String message;
  final dynamic originalError;
  
  VisionProcessingException({
    required this.message,
    this.originalError,
  });
  
  @override
  String toString() => message;
}
