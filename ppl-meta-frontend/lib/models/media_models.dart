import 'package:json_annotation/json_annotation.dart';

part 'media_models.g.dart';

/// Media type enumeration
enum MediaType {
  @JsonValue('image')
  image,
  @JsonValue('video')
  video,
  @JsonValue('audio')
  audio,
  @JsonValue('document')
  document,
  @JsonValue('pdf')
  pdf,
  @JsonValue('text')
  text,
  @JsonValue('archive')
  archive,
  @JsonValue('other')
  other;

  String get displayName {
    switch (this) {
      case MediaType.image:
        return 'Image';
      case MediaType.video:
        return 'Video';
      case MediaType.audio:
        return 'Audio';
      case MediaType.document:
        return 'Document';
      case MediaType.pdf:
        return 'PDF';
      case MediaType.text:
        return 'Text';
      case MediaType.archive:
        return 'Archive';
      case MediaType.other:
        return 'Other';
    }
  }
}

/// Share permission enumeration
enum SharePermission {
  @JsonValue('private')
  private,
  @JsonValue('public')
  public,
  @JsonValue('shared')
  shared,
  @JsonValue('restricted')
  restricted,
  @JsonValue('organization')
  organization,
  @JsonValue('view')
  view,
  @JsonValue('comment')
  comment,
  @JsonValue('edit')
  edit;

  String get displayName {
    switch (this) {
      case SharePermission.private:
        return 'Private';
      case SharePermission.public:
        return 'Public';
      case SharePermission.shared:
        return 'Shared';
      case SharePermission.restricted:
        return 'Restricted';
      case SharePermission.organization:
        return 'Organization';
      case SharePermission.view:
        return 'View Only';
      case SharePermission.comment:
        return 'View & Comment';
      case SharePermission.edit:
        return 'Edit';
    }
  }
}

/// Media item model
@JsonSerializable()
class MediaItem {
  @JsonKey(name: 'media_id')
  final String mediaId;
  
  @JsonKey(name: 'original_filename')
  final String originalFilename;
  
  @JsonKey(name: 'media_type')
  final MediaType mediaType;
  
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
  
  // Additional properties expected by comprehensive frontend
  @JsonKey(name: 'thumbnail_url')
  final String? thumbnailUrl;
  
  @JsonKey(name: 'url')
  final String? url; // Media access URL
  
  @JsonKey(name: 'duration')
  final int? duration; // Duration in seconds for video/audio files
  
  // Convenience getters for compatibility
  String get id => mediaId;
  String get filename => originalFilename;
  Map<String, dynamic>? get metadata => technicalMetadata;
  DateTime get createdAt => uploadedAt; // Alias for uploadedAt
  
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
    this.thumbnailUrl,
    this.url,
    this.duration,
  });
  
  factory MediaItem.fromJson(Map<String, dynamic> json) => _$MediaItemFromJson(json);
  Map<String, dynamic> toJson() => _$MediaItemToJson(this);
  
  /// Get file extension
  String get fileExtension {
    return originalFilename.split('.').last.toLowerCase();
  }
  
  /// Check if media is an image
  bool get isImage {
    return mediaType == MediaType.image;
  }
  
  /// Check if media is a video
  bool get isVideo {
    return mediaType == MediaType.video;
  }
  
  /// Check if media is audio
  bool get isAudio {
    return mediaType == MediaType.audio;
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
  
  final String filename;
  
  @JsonKey(name: 'thumbnail_generated')
  final bool thumbnailGenerated;
  
  final String status;
  final String message;
  
  const MediaUploadResponse({
    required this.mediaId,
    required this.filePath,
    required this.filename,
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

/// Media search filters for filtering and searching media items
@JsonSerializable()
class MediaSearchFilters {
  @JsonKey(name: 'query')
  final String? query;
  
  @JsonKey(name: 'media_type')
  final MediaType? mediaType;
  
  @JsonKey(name: 'start_date')
  final DateTime? startDate;
  
  @JsonKey(name: 'end_date')
  final DateTime? endDate;
  
  @JsonKey(name: 'tags')
  final List<String>? tags;
  
  @JsonKey(name: 'collection_id')
  final String? collectionId;
  
  @JsonKey(name: 'sort_by')
  final String? sortBy;
  
  @JsonKey(name: 'sort_order')
  final String? sortOrder;
  
  @JsonKey(name: 'min_file_size')
  final int? minFileSize;
  
  @JsonKey(name: 'max_file_size')
  final int? maxFileSize;
  
  @JsonKey(name: 'has_thumbnail')
  final bool? hasThumbnail;

  const MediaSearchFilters({
    this.query,
    this.mediaType,
    this.startDate,
    this.endDate,
    this.tags,
    this.collectionId,
    this.sortBy,
    this.sortOrder,
    this.minFileSize,
    this.maxFileSize,
    this.hasThumbnail,
  });

  factory MediaSearchFilters.fromJson(Map<String, dynamic> json) => _$MediaSearchFiltersFromJson(json);
  Map<String, dynamic> toJson() => _$MediaSearchFiltersToJson(this);

  /// Create a copy with updated properties
  MediaSearchFilters copyWith({
    String? query,
    MediaType? mediaType,
    DateTime? startDate,
    DateTime? endDate,
    List<String>? tags,
    String? collectionId,
    String? sortBy,
    String? sortOrder,
    int? minFileSize,
    int? maxFileSize,
    bool? hasThumbnail,
  }) {
    return MediaSearchFilters(
      query: query ?? this.query,
      mediaType: mediaType ?? this.mediaType,
      startDate: startDate ?? this.startDate,
      endDate: endDate ?? this.endDate,
      tags: tags ?? this.tags,
      collectionId: collectionId ?? this.collectionId,
      sortBy: sortBy ?? this.sortBy,
      sortOrder: sortOrder ?? this.sortOrder,
      minFileSize: minFileSize ?? this.minFileSize,
      maxFileSize: maxFileSize ?? this.maxFileSize,
      hasThumbnail: hasThumbnail ?? this.hasThumbnail,
    );
  }

  /// Check if any filters are applied
  bool get hasFilters {
    return query != null && query!.isNotEmpty ||
           mediaType != null ||
           startDate != null ||
           endDate != null ||
           tags != null && tags!.isNotEmpty ||
           collectionId != null ||
           minFileSize != null ||
           maxFileSize != null ||
           hasThumbnail != null;
  }

  /// Clear all filters
  static MediaSearchFilters empty() => const MediaSearchFilters();
}

/// Device analytics model
@JsonSerializable()
class DeviceAnalytics {
  @JsonKey(name: 'total_media_count')
  final int totalMediaCount;
  
  @JsonKey(name: 'total_files')
  final int totalFiles;
  
  @JsonKey(name: 'total_storage_bytes')
  final int totalStorageBytes;
  
  @JsonKey(name: 'uploads_today')
  final int uploadsToday;
  
  @JsonKey(name: 'device_breakdown')
  final Map<String, int> deviceBreakdown;
  
  @JsonKey(name: 'manufacturer_breakdown')
  final Map<String, int> manufacturerBreakdown;
  
  @JsonKey(name: 'media_type_breakdown')
  final Map<String, int> mediaTypeBreakdown;
  
  @JsonKey(name: 'upload_trends')
  final Map<String, int> uploadTrends;
  
  @JsonKey(name: 'uploads_by_day')
  final Map<String, int> uploadsByDay;
  
  @JsonKey(name: 'storage_usage_by_day')
  final Map<String, int> storageUsageByDay;
  
  @JsonKey(name: 'top_devices')
  final List<DeviceStats> topDevices;
  
  const DeviceAnalytics({
    required this.totalMediaCount,
    required this.totalFiles,
    required this.totalStorageBytes,
    required this.uploadsToday,
    required this.deviceBreakdown,
    required this.manufacturerBreakdown,
    required this.mediaTypeBreakdown,
    required this.uploadTrends,
    required this.uploadsByDay,
    required this.storageUsageByDay,
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
@JsonSerializable()
class MediaCollection {
  @JsonKey(name: 'collection_id')
  final String collectionId;
  
  final String name;
  final String? description;
  
  @JsonKey(name: 'created_at')
  final DateTime createdAt;
  
  @JsonKey(name: 'updated_at')
  final DateTime? updatedAt;
  
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
    this.updatedAt,
    this.createdBy,
    required this.mediaCount,
    this.media = const [],
  });
  
  factory MediaCollection.fromJson(Map<String, dynamic> json) => _$MediaCollectionFromJson(json);
  Map<String, dynamic> toJson() => _$MediaCollectionToJson(this);
  
  // Getter aliases for compatibility
  String get id => collectionId;
  int get itemCount => mediaCount;
  
  /// Create a copy with updated properties
  MediaCollection copyWith({
    String? collectionId,
    String? name,
    String? description,
    DateTime? createdAt,
    DateTime? updatedAt,
    String? createdBy,
    int? mediaCount,
    List<MediaItem>? media,
  }) {
    return MediaCollection(
      collectionId: collectionId ?? this.collectionId,
      name: name ?? this.name,
      description: description ?? this.description,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      createdBy: createdBy ?? this.createdBy,
      mediaCount: mediaCount ?? this.mediaCount,
      media: media ?? this.media,
    );
  }
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

/// Response model for paginated media list
@JsonSerializable()
class MediaListResponse {
  final List<MediaItem> items;
  final int totalCount;
  final int page;
  final int limit;
  final bool hasMore;
  
  const MediaListResponse({
    required this.items,
    required this.totalCount,
    required this.page,
    required this.limit,
    required this.hasMore,
  });
  
  factory MediaListResponse.fromJson(Map<String, dynamic> json) =>
      _$MediaListResponseFromJson(json);
  
  Map<String, dynamic> toJson() => _$MediaListResponseToJson(this);
}

/// Media analytics data model
@JsonSerializable()
class MediaAnalytics {
  final int totalItems;
  final int totalSize;
  final Map<String, int> itemsByType;  // Changed from Map<MediaType, int> to Map<String, int>
  final Map<String, int> uploadsByDay;
  final Map<String, int> accessesByDay;
  final double averageFileSize;
  final MediaItem? mostAccessedItem;
  final List<String> popularTags;
  
  const MediaAnalytics({
    required this.totalItems,
    required this.totalSize,
    required this.itemsByType,
    required this.uploadsByDay,
    required this.accessesByDay,
    required this.averageFileSize,
    this.mostAccessedItem,
    required this.popularTags,
  });
  
  factory MediaAnalytics.fromJson(Map<String, dynamic> json) =>
      _$MediaAnalyticsFromJson(json);
  
  Map<String, dynamic> toJson() => _$MediaAnalyticsToJson(this);
}

/// Share link model for sharing media items
@JsonSerializable()
class ShareLink {
  final String id;
  final String url;
  final List<String> itemIds;
  final DateTime createdAt;
  final DateTime? expiresAt;
  final bool allowDownload;
  final bool hasPassword;
  final int accessCount;
  final bool isActive;
  
  const ShareLink({
    required this.id,
    required this.url,
    required this.itemIds,
    required this.createdAt,
    this.expiresAt,
    required this.allowDownload,
    required this.hasPassword,
    required this.accessCount,
    required this.isActive,
  });
  
  factory ShareLink.fromJson(Map<String, dynamic> json) =>
      _$ShareLinkFromJson(json);
  
  Map<String, dynamic> toJson() => _$ShareLinkToJson(this);
  
  /// Check if the share link is expired
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


