import 'dart:convert';
import 'dart:ui';
import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'media_api_client.dart'; // Import FaceDetection and related models
import '../models/api_response.dart';

/// Vision API client for face detection services
class VisionApiClient {
  final Dio _dio;
  final String baseUrl;

  VisionApiClient({
    String? baseUrl,
    String? authToken,
  }) : baseUrl = baseUrl ?? 'http://localhost:8003',
        _dio = Dio() {
    
    // Configure Dio
    _dio.options.baseUrl = this.baseUrl;
    _dio.options.connectTimeout = const Duration(seconds: 30);
    _dio.options.receiveTimeout = const Duration(seconds: 60);
    
    // Add auth token if provided
    if (authToken != null) {
      _dio.options.headers['Authorization'] = 'Bearer $authToken';
    }
    
    // Add request/response interceptors for debugging
    if (kDebugMode) {
      _dio.interceptors.add(LogInterceptor(
        requestBody: false, // Don't log base64 images
        responseBody: true,
        logPrint: (object) => debugPrint('VisionAPI: $object'),
      ));
    }
  }

  /// Detect faces in an image using base64 encoded data
  Future<FaceDetectionResult> detectFaces({
    required String imageBase64,
    List<String>? methods,
    double? confidenceThreshold,
  }) async {
    try {
      final response = await _dio.post('/detect', data: {
        'image_base64': imageBase64,
        if (methods != null) 'methods': methods,
        if (confidenceThreshold != null) 'confidence_threshold': confidenceThreshold,
      });

      return FaceDetectionResult.fromJson(response.data);
    } on DioException catch (e) {
      throw VisionApiException(
        'Face detection failed: ${e.message}',
        statusCode: e.response?.statusCode,
      );
    }
  }

  /// Detect faces in an image file
  Future<FaceDetectionResult> detectFacesFromFile({
    required Uint8List imageBytes,
    List<String>? methods,
    double? confidenceThreshold,
  }) async {
    try {
      // Convert bytes to base64
      final base64Image = base64Encode(imageBytes);
      
      return await detectFaces(
        imageBase64: base64Image,
        methods: methods,
        confidenceThreshold: confidenceThreshold,
      );
    } catch (e) {
      throw VisionApiException('Failed to process image file: $e');
    }
  }

  /// Get service health status
  Future<Map<String, dynamic>> getHealth() async {
    try {
      final response = await _dio.get('/health');
      return response.data;
    } on DioException catch (e) {
      throw VisionApiException(
        'Health check failed: ${e.message}',
        statusCode: e.response?.statusCode,
      );
    }
  }

  /// Get all stored face detections for a media file
  Future<MediaFaceDetectionsResponse> getAllMediaFaces({
    required String mediaId,
    double? confidenceThreshold,
  }) async {
    try {
      final queryParams = <String, dynamic>{};
      if (confidenceThreshold != null) {
        queryParams['confidence_threshold'] = confidenceThreshold;
      }

      final response = await _dio.get(
        '/faces/media/$mediaId',
        queryParameters: queryParams,
      );

      return MediaFaceDetectionsResponse.fromJson(response.data);
    } on DioException catch (e) {
      throw VisionApiException(
        'Failed to get media faces: ${e.message}',
        statusCode: e.response?.statusCode,
      );
    }
  }

  /// Get face detections for media (simplified for face data provider)
  Future<ApiResponse<List<FaceDetection>>> getMediaFaces(String mediaId) async {
    try {
      final response = await getAllMediaFaces(mediaId: mediaId);
      // Convert facesByFrame to a flat list of FaceDetection
      final List<FaceDetection> allFaces = [];
      response.facesByFrame.forEach((frameNumber, faces) {
        allFaces.addAll(faces);
      });
      return ApiResponse.success(allFaces);
    } catch (e) {
      return ApiResponse.error('Failed to load faces: $e');
    }
  }

  /// Get face detections for a specific video frame
  /// Get faces for specific video frame - Phase 2 Enhanced
  Future<FrameFaceDetectionResult> getVideoFrameFaces({
    required String mediaId,
    required int frameNumber,
    String? method = 'two_stage',
    double? confidenceThreshold = 0.5,
  }) async {
    try {
      final response = await _dio.get('/faces/media/$mediaId/frame/$frameNumber', 
        queryParameters: {
          'method': method,
          'confidence_threshold': confidenceThreshold,
        }
      );

      return FrameFaceDetectionResult.fromJson(response.data);
    } on DioException catch (e) {
      throw VisionApiException(
        'Frame face detection failed: ${e.message}',
        statusCode: e.response?.statusCode,
      );
    }
  }

  /// Bulk process video for face detection - Phase 2 Enhanced for Hybrid Architecture
  Future<BulkVideoProcessingResult> bulkProcessVideo({
    required String mediaId,
    String? method = 'two_stage',
    double? confidenceThreshold = 0.5, // FIXED: Default to 0.5 for better face detection
    int? frameInterval = 1,
    int? maxFrames, // Issue 052: Limit frames for progressive pre-loading
    String? description,
    bool storeToDatabase = false, // New parameter for Phase 2 complete analysis
  }) async {
    try {
      final queryParams = <String, dynamic>{};
      if (frameInterval != null) queryParams['frame_interval'] = frameInterval;
      if (maxFrames != null) queryParams['max_frames'] = maxFrames;
      
      final response = await _dio.post(
        '/faces/media/$mediaId/bulk-process',
        queryParameters: queryParams,
        data: {
          'method': method,
          'confidence_threshold': confidenceThreshold,
          'store_to_database': storeToDatabase, // Enable database storage for Phase 2
          if (description != null) 'description': description,
        },
      );

      return BulkVideoProcessingResult.fromJson(response.data);
    } on DioException catch (e) {
      throw VisionApiException(
        'Bulk video processing failed: ${e.message}',
        statusCode: e.response?.statusCode,
      );
    }
  }

  /// Store multiple face detections for a media file (bulk storage)
  Future<BulkFaceStorageResponse> storeBulkFaces({
    required String mediaId,
    required Map<String, dynamic> facesData,
  }) async {
    try {
      final response = await _dio.post(
        '/faces/media/$mediaId/bulk',
        data: facesData,
      );

      return BulkFaceStorageResponse.fromJson(response.data);
    } on DioException catch (e) {
      throw VisionApiException(
        'Failed to store bulk faces: ${e.message}',
        statusCode: e.response?.statusCode,
      );
    }
  }

  /// Get available detection methods
  Future<List<String>> getAvailableMethods() async {
    try {
      final health = await getHealth();
      return List<String>.from(health['available_methods'] ?? []);
    } catch (e) {
      // Fallback to default methods
      return ['haar', 'dlib', 'mtcnn'];
    }
  }

  /// Get system information and health status
  Future<Map<String, dynamic>> getSystemInfo() async {
    try {
      final response = await _dio.get('/system/info');
      return response.data;
    } on DioException catch (e) {
      throw VisionApiException(
        'Failed to get system info: ${e.message}',
        statusCode: e.response?.statusCode,
      );
    }
  }
}

/// Face detection result model
class FaceDetectionResult {
  final bool success;
  final String? message;
  final List<FaceDetection> detections;
  final double processingTime;
  final DateTime timestamp;

  FaceDetectionResult({
    required this.success,
    this.message,
    required this.detections,
    required this.processingTime,
    required this.timestamp,
  });

  factory FaceDetectionResult.fromJson(Map<String, dynamic> json) {
    return FaceDetectionResult(
      success: json['success'] ?? false,
      message: json['message'],
      detections: (json['detections'] as List<dynamic>?)
          ?.map((d) => FaceDetection.fromJson(d))
          .toList() ?? [],
      processingTime: (json['processing_time'] ?? 0.0).toDouble(),
      timestamp: DateTime.parse(json['timestamp'] ?? DateTime.now().toIso8601String()),
    );
  }
}

/// Media face detections response model
class MediaFaceDetectionsResponse {
  final bool success;
  final String mediaId;
  final bool hasStoredFaces;
  final int totalFaces;
  final Map<String, List<FaceDetection>> facesByFrame;
  final String message;

  MediaFaceDetectionsResponse({
    required this.success,
    required this.mediaId,
    required this.hasStoredFaces,
    required this.totalFaces,
    required this.facesByFrame,
    required this.message,
  });

  factory MediaFaceDetectionsResponse.fromJson(Map<String, dynamic> json) {
    final facesByFrameJson = json['faces_by_frame'] as Map<String, dynamic>? ?? {};
    final facesByFrame = <String, List<FaceDetection>>{};
    
    facesByFrameJson.forEach((frameNumber, faces) {
      final facesList = (faces as List<dynamic>)
          .map((face) => FaceDetection.fromJson(face))
          .toList();
      facesByFrame[frameNumber] = facesList;
    });

    return MediaFaceDetectionsResponse(
      success: json['success'] ?? false,
      mediaId: json['media_id'] ?? '',
      hasStoredFaces: json['has_stored_faces'] ?? false,
      totalFaces: json['total_faces'] ?? 0,
      facesByFrame: facesByFrame,
      message: json['message'] ?? '',
    );
  }
}

/// Bulk face storage response model
class BulkFaceStorageResponse {
  final bool success;
  final String mediaId;
  final int storedFaces;
  final int totalFrames;
  final String message;

  BulkFaceStorageResponse({
    required this.success,
    required this.mediaId,
    required this.storedFaces,
    required this.totalFrames,
    required this.message,
  });

  factory BulkFaceStorageResponse.fromJson(Map<String, dynamic> json) {
    return BulkFaceStorageResponse(
      success: json['success'] ?? false,
      mediaId: json['media_id'] ?? '',
      storedFaces: json['stored_faces'] ?? 0,
      totalFrames: json['total_frames'] ?? 0,
      message: json['message'] ?? '',
    );
  }
}

/// Bulk video processing response model
class BulkVideoProcessingResponse {
  final bool success;
  final String mediaId;
  final VideoInfo videoInfo;
  final Map<String, List<FaceDetection>> facesByFrame;
  final int totalFaces;
  final double processingTime;
  final double confidenceThreshold;
  final String message;

  BulkVideoProcessingResponse({
    required this.success,
    required this.mediaId,
    required this.videoInfo,
    required this.facesByFrame,
    required this.totalFaces,
    required this.processingTime,
    required this.confidenceThreshold,
    required this.message,
  });

  factory BulkVideoProcessingResponse.fromJson(Map<String, dynamic> json) {
    final facesByFrameJson = json['faces_by_frame'] as Map<String, dynamic>? ?? {};
    final facesByFrame = <String, List<FaceDetection>>{};
    
    facesByFrameJson.forEach((frameNumber, faces) {
      final facesList = (faces as List<dynamic>)
          .map((face) => FaceDetection.fromJson(face))
          .toList();
      facesByFrame[frameNumber] = facesList;
    });

    return BulkVideoProcessingResponse(
      success: json['success'] ?? false,
      mediaId: json['media_id'] ?? '',
      videoInfo: VideoInfo.fromJson(json['video_info'] ?? {}),
      facesByFrame: facesByFrame,
      totalFaces: json['total_faces'] ?? 0,
      processingTime: (json['processing_time'] ?? 0.0).toDouble(),
      confidenceThreshold: (json['confidence_threshold'] ?? 0.5).toDouble(),
      message: json['message'] ?? '',
    );
  }
}

/// Video information model
class VideoInfo {
  final int totalFrames;
  final double fps;
  final double duration;
  final int processedFrames;
  final int frameInterval;

  VideoInfo({
    required this.totalFrames,
    required this.fps,
    required this.duration,
    required this.processedFrames,
    required this.frameInterval,
  });

  factory VideoInfo.fromJson(Map<String, dynamic> json) {
    return VideoInfo(
      totalFrames: json['total_frames'] ?? 0,
      fps: (json['fps'] ?? 30.0).toDouble(),
      duration: (json['duration'] ?? 0.0).toDouble(),
      processedFrames: json['processed_frames'] ?? 0,
      frameInterval: json['frame_interval'] ?? 30,
    );
  }
}

/// Bulk video processing result - Phase 2 Enhanced
class BulkVideoProcessingResult {
  final bool success;
  final String? message;
  final String? jobId;
  final List<FrameFaceDetectionResult> frames;
  final VideoInfo? videoInfo;
  final double processingTime;
  final DateTime timestamp;
  final String method;
  final double confidenceThreshold;

  BulkVideoProcessingResult({
    required this.success,
    this.message,
    this.jobId,
    required this.frames,
    this.videoInfo,
    required this.processingTime,
    required this.timestamp,
    required this.method,
    required this.confidenceThreshold,
  });

  factory BulkVideoProcessingResult.fromJson(Map<String, dynamic> json) {
    // Convert faces_by_frame object to frames list
    List<FrameFaceDetectionResult> framesList = [];
    if (json['faces_by_frame'] != null) {
      final facesByFrame = json['faces_by_frame'] as Map<String, dynamic>;
      facesByFrame.forEach((frameNumberStr, faces) {
        final frameNumber = int.tryParse(frameNumberStr) ?? 0;
        final facesList = (faces as List<dynamic>?)
            ?.map((face) => FaceDetection.fromJson(face))
            .toList() ?? [];
        
        framesList.add(FrameFaceDetectionResult(
          success: true,
          mediaId: json['media_id'] ?? '',
          frameNumber: frameNumber,
          faces: facesList,
          processingTime: (json['processing_time'] ?? 0.0).toDouble(),
        ));
      });
    }

    return BulkVideoProcessingResult(
      success: json['success'] ?? false,
      message: json['message'],
      jobId: json['job_id'],
      frames: framesList,
      videoInfo: json['video_info'] != null 
          ? VideoInfo.fromJson(json['video_info']) 
          : null,
      processingTime: (json['processing_time'] ?? 0.0).toDouble(),
      timestamp: DateTime.parse(json['timestamp'] ?? DateTime.now().toIso8601String()),
      method: json['method'] ?? 'two_stage',
      confidenceThreshold: (json['confidence_threshold'] ?? 0.5).toDouble(),
    );
  }
}

/// Face detection response model
class FaceDetectionResponse {
  final List<FaceDetection> detections;
  final DateTime timestamp;

  FaceDetectionResponse({
    required this.detections,
    required this.timestamp,
  });

  factory FaceDetectionResponse.fromJson(Map<String, dynamic> json) {
    final detections = (json['faces'] as List<dynamic>? ?? [])
        .map((face) => FaceDetection.fromJson(face))
        .toList();
    
    return FaceDetectionResponse(
      detections: detections,
      timestamp: DateTime.now(),
    );
  }
}

/// Vision API exception
class VisionApiException implements Exception {
  final String message;
  final int? statusCode;

  VisionApiException(this.message, {this.statusCode});

  @override
  String toString() => 'VisionApiException: $message${statusCode != null ? ' (Status: $statusCode)' : ''}';
}

/// Frame-specific face detection result - Phase 2 Enhanced
class FrameFaceDetectionResult {
  final bool success;
  final String mediaId;
  final int frameNumber;
  final List<FaceDetection> faces;
  final double processingTime;
  final String? message;

  FrameFaceDetectionResult({
    required this.success,
    required this.mediaId,
    required this.frameNumber,
    required this.faces,
    required this.processingTime,
    this.message,
  });

  factory FrameFaceDetectionResult.fromJson(Map<String, dynamic> json) {
    return FrameFaceDetectionResult(
      success: json['success'] ?? false,
      mediaId: json['media_id'] ?? '',
      frameNumber: json['frame_number'] ?? 0,
      faces: (json['faces'] as List<dynamic>?)
          ?.map((face) => FaceDetection.fromJson(face))
          .toList() ?? [],
      processingTime: (json['processing_time'] ?? 0.0).toDouble(),
      message: json['message'],
    );
  }
}
