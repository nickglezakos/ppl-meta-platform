import 'package:json_annotation/json_annotation.dart';

part 'media_models.g.dart';

/// Media item model
@JsonSerializable()
class MediaItem {
  @JsonKey(name: 'media_id')
  final String mediaId;
  
  @JsonKey(name: 'original_filename')
  final String originalFilename;
  
  @JsonKey(name: 'media_type')
  final String mediaType;
  
  @JsonKey(name: 'file_size')
  final int fileSize;
  
  @JsonKey(name: 'file_path')
  final String filePath;
  
  @JsonKey(name: 'uploaded_at')
  final DateTime uploadedAt;
  
  @JsonKey(name: 'uploaded_by')
  final String? uploadedBy;
  
  @JsonKey(name: 'device_name')
  final String? deviceName;
  
  @JsonKey(name: 'device_manufacturer')
  final String? deviceManufacturer;
  
  @JsonKey(name: 'device_model')
  final String? deviceModel;
  
  @JsonKey(name: 'device_os')
  final String? deviceOs;
  
  @JsonKey(name: 'app_name')
  final String? appName;
  
  @JsonKey(name: 'app_version')
  final String? appVersion;
  
  @JsonKey(name: 'is_public')
  final bool isPublic;
  
  final List<String> tags;
  final String? description;
  
  @JsonKey(name: 'technical_metadata')
  final Map<String, dynamic>? technicalMetadata;
  
  const MediaItem({
    required this.mediaId,
    required this.originalFilename,
    required this.mediaType,
    required this.fileSize,
    required this.filePath,
    required this.uploadedAt,
    this.uploadedBy,
    this.deviceName,
    this.deviceManufacturer,
    this.deviceModel,
    this.deviceOs,
    this.appName,
    this.appVersion,
    required this.isPublic,
    this.tags = const [],
    this.description,
    this.technicalMetadata,
  });
  
  factory MediaItem.fromJson(Map<String, dynamic> json) => _$MediaItemFromJson(json);
  Map<String, dynamic> toJson() => _$MediaItemToJson(this);
  
  /// Get file extension
  String get fileExtension {
    return originalFilename.split('.').last.toLowerCase();
  }
  
  /// Check if media is an image
  bool get isImage {
    return mediaType.startsWith('image/');
  }
  
  /// Check if media is a video
  bool get isVideo {
    return mediaType.startsWith('video/');
  }
  
  /// Check if media is audio
  bool get isAudio {
    return mediaType.startsWith('audio/');
  }
  
  /// Get formatted file size
  String get formattedFileSize {
    if (fileSize < 1024) return '${fileSize}B';
    if (fileSize < 1024 * 1024) return '${(fileSize / 1024).toStringAsFixed(1)}KB';
    if (fileSize < 1024 * 1024 * 1024) return '${(fileSize / (1024 * 1024)).toStringAsFixed(1)}MB';
    return '${(fileSize / (1024 * 1024 * 1024)).toStringAsFixed(1)}GB';
  }
  
  /// Get device display name
  String get deviceDisplayName {
    if (deviceManufacturer != null && deviceModel != null) {
      return '$deviceManufacturer $deviceModel';
    }
    return deviceName ?? 'Unknown Device';
  }
}

/// Media upload response
@JsonSerializable()
class MediaUploadResponse {
  @JsonKey(name: 'media_id')
  final String mediaId;
  
  @JsonKey(name: 'file_path')
  final String filePath;
  
  @JsonKey(name: 'thumbnail_generated')
  final bool thumbnailGenerated;
  
  final String status;
  final String message;
  
  const MediaUploadResponse({
    required this.mediaId,
    required this.filePath,
    required this.thumbnailGenerated,
    required this.status,
    required this.message,
  });
  
  factory MediaUploadResponse.fromJson(Map<String, dynamic> json) => _$MediaUploadResponseFromJson(json);
  Map<String, dynamic> toJson() => _$MediaUploadResponseToJson(this);
}

/// Media search response
@JsonSerializable()
class MediaSearchResponse {
  final List<MediaItem> items;
  final int total;
  final int limit;
  final int offset;
  
  @JsonKey(name: 'has_next')
  final bool hasNext;
  
  @JsonKey(name: 'has_previous')
  final bool hasPrevious;
  
  const MediaSearchResponse({
    required this.items,
    required this.total,
    required this.limit,
    required this.offset,
    required this.hasNext,
    required this.hasPrevious,
  });
  
  factory MediaSearchResponse.fromJson(Map<String, dynamic> json) => _$MediaSearchResponseFromJson(json);
  Map<String, dynamic> toJson() => _$MediaSearchResponseToJson(this);
}

/// Device analytics model
@JsonSerializable()
class DeviceAnalytics {
  @JsonKey(name: 'total_media_count')
  final int totalMediaCount;
  
  @JsonKey(name: 'device_breakdown')
  final Map<String, int> deviceBreakdown;
  
  @JsonKey(name: 'manufacturer_breakdown')
  final Map<String, int> manufacturerBreakdown;
  
  @JsonKey(name: 'media_type_breakdown')
  final Map<String, int> mediaTypeBreakdown;
  
  @JsonKey(name: 'upload_trends')
  final Map<String, int> uploadTrends;
  
  @JsonKey(name: 'top_devices')
  final List<DeviceStats> topDevices;
  
  const DeviceAnalytics({
    required this.totalMediaCount,
    required this.deviceBreakdown,
    required this.manufacturerBreakdown,
    required this.mediaTypeBreakdown,
    required this.uploadTrends,
    required this.topDevices,
  });
  
  factory DeviceAnalytics.fromJson(Map<String, dynamic> json) => _$DeviceAnalyticsFromJson(json);
  Map<String, dynamic> toJson() => _$DeviceAnalyticsToJson(this);
}

/// Device statistics
@JsonSerializable()
class DeviceStats {
  @JsonKey(name: 'device_name')
  final String deviceName;
  
  @JsonKey(name: 'device_manufacturer')
  final String deviceManufacturer;
  
  @JsonKey(name: 'device_model')
  final String deviceModel;
  
  @JsonKey(name: 'media_count')
  final int mediaCount;
  
  @JsonKey(name: 'total_size')
  final int totalSize;
  
  const DeviceStats({
    required this.deviceName,
    required this.deviceManufacturer,
    required this.deviceModel,
    required this.mediaCount,
    required this.totalSize,
  });
  
  factory DeviceStats.fromJson(Map<String, dynamic> json) => _$DeviceStatsFromJson(json);
  Map<String, dynamic> toJson() => _$DeviceStatsToJson(this);
  
  /// Get formatted total size
  String get formattedTotalSize {
    if (totalSize < 1024) return '${totalSize}B';
    if (totalSize < 1024 * 1024) return '${(totalSize / 1024).toStringAsFixed(1)}KB';
    if (totalSize < 1024 * 1024 * 1024) return '${(totalSize / (1024 * 1024)).toStringAsFixed(1)}MB';
    return '${(totalSize / (1024 * 1024 * 1024)).toStringAsFixed(1)}GB';
  }
}

/// Media collection model
@JsonSerializable()
class MediaCollection {
  @JsonKey(name: 'collection_id')
  final String collectionId;
  
  final String name;
  final String? description;
  
  @JsonKey(name: 'created_at')
  final DateTime createdAt;
  
  @JsonKey(name: 'created_by')
  final String? createdBy;
  
  @JsonKey(name: 'media_count')
  final int mediaCount;
  
  final List<MediaItem> media;
  
  const MediaCollection({
    required this.collectionId,
    required this.name,
    this.description,
    required this.createdAt,
    this.createdBy,
    required this.mediaCount,
    this.media = const [],
  });
  
  factory MediaCollection.fromJson(Map<String, dynamic> json) => _$MediaCollectionFromJson(json);
  Map<String, dynamic> toJson() => _$MediaCollectionToJson(this);
}

/// Share response model
@JsonSerializable()
class ShareResponse {
  @JsonKey(name: 'share_id')
  final String shareId;
  
  @JsonKey(name: 'share_token')
  final String shareToken;
  
  @JsonKey(name: 'share_url')
  final String shareUrl;
  
  @JsonKey(name: 'media_id')
  final String mediaId;
  
  final List<String> permissions;
  
  @JsonKey(name: 'expires_at')
  final DateTime? expiresAt;
  
  @JsonKey(name: 'created_at')
  final DateTime createdAt;
  
  const ShareResponse({
    required this.shareId,
    required this.shareToken,
    required this.shareUrl,
    required this.mediaId,
    required this.permissions,
    this.expiresAt,
    required this.createdAt,
  });
  
  factory ShareResponse.fromJson(Map<String, dynamic> json) => _$ShareResponseFromJson(json);
  Map<String, dynamic> toJson() => _$ShareResponseToJson(this);
  
  /// Check if share has expired
  bool get isExpired {
    if (expiresAt == null) return false;
    return DateTime.now().isAfter(expiresAt!);
  }
}

/// API error model
class ApiError implements Exception {
  final String code;
  final String message;
  final int statusCode;
  
  const ApiError({
    required this.code,
    required this.message,
    required this.statusCode,
  });
  
  @override
  String toString() {
    return 'ApiError(code: $code, message: $message, statusCode: $statusCode)';
  }
}
