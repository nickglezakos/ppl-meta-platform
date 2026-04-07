// GENERATED CODE - DO NOT MODIFY BY HAND
// Manual implementation (build_runner has pre-existing errors)

part of 'media_models.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

MediaType _$MediaTypeFromJson(String value) {
  switch (value) {
    case 'picture':
      return MediaType.image;
    case 'video':
      return MediaType.video;
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
    case 'other':
      return MediaType.other;
    default:
      return MediaType.other;
  }
}

String _$MediaTypeToJson(MediaType type) {
  switch (type) {
    case MediaType.image:
      return 'picture';
    case MediaType.video:
      return 'video';
    case MediaType.audio:
      return 'audio';
    case MediaType.document:
      return 'document';
    case MediaType.pdf:
      return 'pdf';
    case MediaType.text:
      return 'text';
    case MediaType.archive:
      return 'archive';
    case MediaType.other:
      return 'other';
  }
}

SharePermission _$SharePermissionFromJson(String value) {
  switch (value) {
    case 'private':
      return SharePermission.private;
    case 'public':
      return SharePermission.public;
    case 'shared':
      return SharePermission.shared;
    case 'restricted':
      return SharePermission.restricted;
    case 'organization':
      return SharePermission.organization;
    case 'view':
      return SharePermission.view;
    case 'comment':
      return SharePermission.comment;
    case 'edit':
      return SharePermission.edit;
    default:
      return SharePermission.private;
  }
}

MediaItem _$MediaItemFromJson(Map<String, dynamic> json) {
  return MediaItem(
    mediaId: _intToString(json['id']),
    uuid: json['uuid'] as String? ?? '',
    originalFilename: json['original_filename'] as String? ?? '',
    mediaType: json['media_type'] == null
        ? MediaType.other
        : _$MediaTypeFromJson(json['media_type'] as String),
    fileSize: (json['file_size'] as num?)?.toInt() ?? 0,
    filePath: json['file_path'] as String? ?? '',
    uploadedAt: json['created_at'] == null
        ? DateTime.now()
        : DateTime.parse(json['created_at'] as String),
    uploadedBy: json['uploaded_by'] as String?,
    deviceName: json['device_name'] as String?,
    deviceManufacturer: json['device_manufacturer'] as String?,
    deviceModel: json['device_model'] as String?,
    deviceOs: json['device_os'] as String?,
    appName: json['app_name'] as String?,
    appVersion: json['app_version'] as String?,
    isPublic: json['is_public'] as bool? ?? false,
    isArchived: json['is_archived'] as bool? ?? false,
    tags: (json['tags'] as List<dynamic>?)
            ?.map((e) => e as String)
            .toList() ??
        const [],
    description: json['description'] as String?,
    technicalMetadata:
        json['technical_metadata'] as Map<String, dynamic>?,
    thumbnailUrl: json['thumbnail_url'] as String?,
    url: json['url'] as String?,
    duration: (json['duration'] as num?)?.toInt(),
    collections: (json['collections'] as List<dynamic>?)
        ?.map((e) => e as Map<String, dynamic>)
        .toList(),
  );
}

Map<String, dynamic> _$MediaItemToJson(MediaItem instance) =>
    <String, dynamic>{
      'id': instance.mediaId,
      'uuid': instance.uuid,
      'original_filename': instance.originalFilename,
      'media_type': _$MediaTypeToJson(instance.mediaType),
      'file_size': instance.fileSize,
      'file_path': instance.filePath,
      'created_at': instance.uploadedAt.toIso8601String(),
      'uploaded_by': instance.uploadedBy,
      'device_name': instance.deviceName,
      'device_manufacturer': instance.deviceManufacturer,
      'device_model': instance.deviceModel,
      'device_os': instance.deviceOs,
      'app_name': instance.appName,
      'app_version': instance.appVersion,
      'is_public': instance.isPublic,
      'is_archived': instance.isArchived,
      'tags': instance.tags,
      'description': instance.description,
      'technical_metadata': instance.technicalMetadata,
      'thumbnail_url': instance.thumbnailUrl,
      'url': instance.url,
      'duration': instance.duration,
      'collections': instance.collections,
    };

MediaUploadResponse _$MediaUploadResponseFromJson(
        Map<String, dynamic> json) =>
    MediaUploadResponse(
      mediaId: json['media_id'] as String? ?? '',
      filePath: json['file_path'] as String? ?? '',
      filename: json['filename'] as String? ?? '',
      thumbnailGenerated:
          json['thumbnail_generated'] as bool? ?? false,
      status: json['status'] as String? ?? '',
      message: json['message'] as String? ?? '',
    );

Map<String, dynamic> _$MediaUploadResponseToJson(
        MediaUploadResponse instance) =>
    <String, dynamic>{
      'media_id': instance.mediaId,
      'file_path': instance.filePath,
      'filename': instance.filename,
      'thumbnail_generated': instance.thumbnailGenerated,
      'status': instance.status,
      'message': instance.message,
    };

MediaSearchResponse _$MediaSearchResponseFromJson(
        Map<String, dynamic> json) =>
    MediaSearchResponse(
      items: (json['items'] as List<dynamic>?)
              ?.map(
                  (e) => MediaItem.fromJson(e as Map<String, dynamic>))
              .toList() ??
          const [],
      total: (json['total'] as num?)?.toInt() ?? 0,
      limit: (json['limit'] as num?)?.toInt() ?? 20,
      offset: (json['offset'] as num?)?.toInt() ?? 0,
      hasNext: json['has_next'] as bool? ?? false,
      hasPrevious: json['has_previous'] as bool? ?? false,
    );

Map<String, dynamic> _$MediaSearchResponseToJson(
        MediaSearchResponse instance) =>
    <String, dynamic>{
      'items': instance.items.map((e) => e.toJson()).toList(),
      'total': instance.total,
      'limit': instance.limit,
      'offset': instance.offset,
      'has_next': instance.hasNext,
      'has_previous': instance.hasPrevious,
    };

MediaSearchFilters _$MediaSearchFiltersFromJson(
        Map<String, dynamic> json) =>
    MediaSearchFilters(
      query: json['query'] as String?,
      mediaType: json['media_type'] == null
          ? null
          : _$MediaTypeFromJson(json['media_type'] as String),
      startDate: json['start_date'] == null
          ? null
          : DateTime.parse(json['start_date'] as String),
      endDate: json['end_date'] == null
          ? null
          : DateTime.parse(json['end_date'] as String),
      tags: (json['tags'] as List<dynamic>?)
          ?.map((e) => e as String)
          .toList(),
      collectionId: json['collection_id'] as String?,
      collectionIds: (json['collection_ids'] as List<dynamic>?)
          ?.map((e) => e as String)
          .toList(),
      sortBy: json['sort_by'] as String?,
      sortOrder: json['sort_order'] as String?,
      minFileSize: (json['min_file_size'] as num?)?.toInt(),
      maxFileSize: (json['max_file_size'] as num?)?.toInt(),
      hasThumbnail: json['has_thumbnail'] as bool?,
      isArchived: json['is_archived'] as bool?,
    );

Map<String, dynamic> _$MediaSearchFiltersToJson(
        MediaSearchFilters instance) =>
    <String, dynamic>{
      'query': instance.query,
      'media_type': instance.mediaType == null
          ? null
          : _$MediaTypeToJson(instance.mediaType!),
      'start_date': instance.startDate?.toIso8601String(),
      'end_date': instance.endDate?.toIso8601String(),
      'tags': instance.tags,
      'collection_id': instance.collectionId,
      'collection_ids': instance.collectionIds,
      'sort_by': instance.sortBy,
      'sort_order': instance.sortOrder,
      'min_file_size': instance.minFileSize,
      'max_file_size': instance.maxFileSize,
      'has_thumbnail': instance.hasThumbnail,
      'is_archived': instance.isArchived,
    };

DeviceAnalytics _$DeviceAnalyticsFromJson(
        Map<String, dynamic> json) =>
    DeviceAnalytics(
      totalMediaCount:
          (json['total_media_count'] as num?)?.toInt() ?? 0,
      totalFiles: (json['total_files'] as num?)?.toInt() ?? 0,
      totalStorageBytes:
          (json['total_storage_bytes'] as num?)?.toInt() ?? 0,
      uploadsToday:
          (json['uploads_today'] as num?)?.toInt() ?? 0,
      deviceBreakdown:
          (json['device_breakdown'] as Map<String, dynamic>?)
                  ?.map((k, v) => MapEntry(k, (v as num).toInt())) ??
              const {},
      manufacturerBreakdown:
          (json['manufacturer_breakdown'] as Map<String, dynamic>?)
                  ?.map((k, v) => MapEntry(k, (v as num).toInt())) ??
              const {},
      mediaTypeBreakdown:
          (json['media_type_breakdown'] as Map<String, dynamic>?)
                  ?.map((k, v) => MapEntry(k, (v as num).toInt())) ??
              const {},
      uploadTrends:
          (json['upload_trends'] as Map<String, dynamic>?)
                  ?.map((k, v) => MapEntry(k, (v as num).toInt())) ??
              const {},
      uploadsByDay:
          (json['uploads_by_day'] as Map<String, dynamic>?)
                  ?.map((k, v) => MapEntry(k, (v as num).toInt())) ??
              const {},
      storageUsageByDay:
          (json['storage_usage_by_day'] as Map<String, dynamic>?)
                  ?.map((k, v) => MapEntry(k, (v as num).toInt())) ??
              const {},
      topDevices: (json['top_devices'] as List<dynamic>?)
              ?.map((e) =>
                  DeviceStats.fromJson(e as Map<String, dynamic>))
              .toList() ??
          const [],
    );

Map<String, dynamic> _$DeviceAnalyticsToJson(
        DeviceAnalytics instance) =>
    <String, dynamic>{
      'total_media_count': instance.totalMediaCount,
      'total_files': instance.totalFiles,
      'total_storage_bytes': instance.totalStorageBytes,
      'uploads_today': instance.uploadsToday,
      'device_breakdown': instance.deviceBreakdown,
      'manufacturer_breakdown': instance.manufacturerBreakdown,
      'media_type_breakdown': instance.mediaTypeBreakdown,
      'upload_trends': instance.uploadTrends,
      'uploads_by_day': instance.uploadsByDay,
      'storage_usage_by_day': instance.storageUsageByDay,
      'top_devices':
          instance.topDevices.map((e) => e.toJson()).toList(),
    };

DeviceStats _$DeviceStatsFromJson(Map<String, dynamic> json) =>
    DeviceStats(
      deviceName: json['device_name'] as String? ?? '',
      deviceManufacturer:
          json['device_manufacturer'] as String? ?? '',
      deviceModel: json['device_model'] as String? ?? '',
      mediaCount: (json['media_count'] as num?)?.toInt() ?? 0,
      totalSize: (json['total_size'] as num?)?.toInt() ?? 0,
    );

Map<String, dynamic> _$DeviceStatsToJson(DeviceStats instance) =>
    <String, dynamic>{
      'device_name': instance.deviceName,
      'device_manufacturer': instance.deviceManufacturer,
      'device_model': instance.deviceModel,
      'media_count': instance.mediaCount,
      'total_size': instance.totalSize,
    };

ShareResponse _$ShareResponseFromJson(Map<String, dynamic> json) =>
    ShareResponse(
      shareId: json['share_id'] as String? ?? '',
      shareToken: json['share_token'] as String? ?? '',
      shareUrl: json['share_url'] as String? ?? '',
      mediaId: json['media_id'] as String? ?? '',
      permissions: (json['permissions'] as List<dynamic>?)
              ?.map((e) => e as String)
              .toList() ??
          const [],
      expiresAt: json['expires_at'] == null
          ? null
          : DateTime.parse(json['expires_at'] as String),
      createdAt: json['created_at'] == null
          ? DateTime.now()
          : DateTime.parse(json['created_at'] as String),
    );

Map<String, dynamic> _$ShareResponseToJson(
        ShareResponse instance) =>
    <String, dynamic>{
      'share_id': instance.shareId,
      'share_token': instance.shareToken,
      'share_url': instance.shareUrl,
      'media_id': instance.mediaId,
      'permissions': instance.permissions,
      'expires_at': instance.expiresAt?.toIso8601String(),
      'created_at': instance.createdAt.toIso8601String(),
    };

MediaListResponse _$MediaListResponseFromJson(
        Map<String, dynamic> json) =>
    MediaListResponse(
      items: (json['items'] as List<dynamic>?)
              ?.map(
                  (e) => MediaItem.fromJson(e as Map<String, dynamic>))
              .toList() ??
          const [],
      totalCount: (json['totalCount'] as num?)?.toInt() ?? 0,
      page: (json['page'] as num?)?.toInt() ?? 1,
      limit: (json['limit'] as num?)?.toInt() ?? 20,
      hasMore: json['hasMore'] as bool? ?? false,
    );

Map<String, dynamic> _$MediaListResponseToJson(
        MediaListResponse instance) =>
    <String, dynamic>{
      'items': instance.items.map((e) => e.toJson()).toList(),
      'totalCount': instance.totalCount,
      'page': instance.page,
      'limit': instance.limit,
      'hasMore': instance.hasMore,
    };

ShareLink _$ShareLinkFromJson(Map<String, dynamic> json) =>
    ShareLink(
      id: json['id'] as String? ?? '',
      url: json['url'] as String? ?? '',
      itemIds: (json['itemIds'] as List<dynamic>?)
              ?.map((e) => e as String)
              .toList() ??
          const [],
      createdAt: json['createdAt'] == null
          ? DateTime.now()
          : DateTime.parse(json['createdAt'] as String),
      expiresAt: json['expiresAt'] == null
          ? null
          : DateTime.parse(json['expiresAt'] as String),
      allowDownload: json['allowDownload'] as bool? ?? false,
      hasPassword: json['hasPassword'] as bool? ?? false,
      accessCount: (json['accessCount'] as num?)?.toInt() ?? 0,
      isActive: json['isActive'] as bool? ?? true,
    );

Map<String, dynamic> _$ShareLinkToJson(ShareLink instance) =>
    <String, dynamic>{
      'id': instance.id,
      'url': instance.url,
      'itemIds': instance.itemIds,
      'createdAt': instance.createdAt.toIso8601String(),
      'expiresAt': instance.expiresAt?.toIso8601String(),
      'allowDownload': instance.allowDownload,
      'hasPassword': instance.hasPassword,
      'accessCount': instance.accessCount,
      'isActive': instance.isActive,
    };

MostAccessedItem _$MostAccessedItemFromJson(
        Map<String, dynamic> json) =>
    MostAccessedItem(
      id: (json['id'] as num?)?.toInt() ?? 0,
      uuid: json['uuid'] as String? ?? '',
      originalFilename:
          json['original_filename'] as String? ?? '',
      mediaType: json['media_type'] as String? ?? 'other',
      fileSize: (json['file_size'] as num?)?.toInt() ?? 0,
      createdAt: json['created_at'] as String? ?? '',
      accessCount: (json['access_count'] as num?)?.toInt() ?? 0,
    );

Map<String, dynamic> _$MostAccessedItemToJson(
        MostAccessedItem instance) =>
    <String, dynamic>{
      'id': instance.id,
      'uuid': instance.uuid,
      'original_filename': instance.originalFilename,
      'media_type': instance.mediaType,
      'file_size': instance.fileSize,
      'created_at': instance.createdAt,
      'access_count': instance.accessCount,
    };

MediaAnalytics _$MediaAnalyticsFromJson(
        Map<String, dynamic> json) =>
    MediaAnalytics(
      totalItems: (json['totalItems'] as num?)?.toInt() ?? 0,
      totalSize: (json['totalSize'] as num?)?.toInt() ?? 0,
      averageFileSize:
          (json['averageFileSize'] as num?)?.toDouble() ?? 0.0,
      itemsByType:
          (json['itemsByType'] as Map<String, dynamic>?)
                  ?.map((k, v) => MapEntry(k, (v as num).toInt())) ??
              const {},
      uploadsByDay:
          (json['uploadsByDay'] as Map<String, dynamic>?)
                  ?.map((k, v) => MapEntry(k, (v as num).toInt())) ??
              const {},
      accessesByDay:
          (json['accessesByDay'] as Map<String, dynamic>?)
                  ?.map((k, v) => MapEntry(k, (v as num).toInt())) ??
              const {},
      popularTags: (json['popularTags'] as List<dynamic>?)
              ?.map((e) => e as String)
              .toList() ??
          const [],
      mostAccessedItem: json['mostAccessedItem'] == null
          ? null
          : MostAccessedItem.fromJson(
              json['mostAccessedItem'] as Map<String, dynamic>),
    );

Map<String, dynamic> _$MediaAnalyticsToJson(
        MediaAnalytics instance) =>
    <String, dynamic>{
      'totalItems': instance.totalItems,
      'totalSize': instance.totalSize,
      'averageFileSize': instance.averageFileSize,
      'itemsByType': instance.itemsByType,
      'uploadsByDay': instance.uploadsByDay,
      'accessesByDay': instance.accessesByDay,
      'popularTags': instance.popularTags,
      'mostAccessedItem': instance.mostAccessedItem?.toJson(),
    };
