// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'media_models.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

MediaItem _$MediaItemFromJson(Map<String, dynamic> json) => MediaItem(
      mediaId: _intToString(json['id']),
      uuid: json['uuid'] as String,
      originalFilename: json['original_filename'] as String,
      mediaType: $enumDecode(_$MediaTypeEnumMap, json['media_type']),
      fileSize: (json['file_size'] as num).toInt(),
      filePath: json['file_path'] as String,
      uploadedAt: DateTime.parse(json['created_at'] as String),
      uploadedBy: json['uploaded_by'] as String?,
      deviceName: json['device_name'] as String?,
      deviceManufacturer: json['device_manufacturer'] as String?,
      deviceModel: json['device_model'] as String?,
      deviceOs: json['device_os'] as String?,
      appName: json['app_name'] as String?,
      appVersion: json['app_version'] as String?,
      isPublic: json['is_public'] as bool,
      isArchived: json['is_archived'] as bool? ?? false,
      tags:
          (json['tags'] as List<dynamic>?)?.map((e) => e as String).toList() ??
              const [],
      description: json['description'] as String?,
      technicalMetadata: json['technical_metadata'] as Map<String, dynamic>?,
      thumbnailUrl: json['thumbnail_url'] as String?,
      url: json['url'] as String?,
      duration: (json['duration'] as num?)?.toInt(),
    );

Map<String, dynamic> _$MediaItemToJson(MediaItem instance) => <String, dynamic>{
      'id': instance.mediaId,
      'uuid': instance.uuid,
      'original_filename': instance.originalFilename,
      'media_type': _$MediaTypeEnumMap[instance.mediaType]!,
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
    };

const _$MediaTypeEnumMap = {
  MediaType.image: 'picture',
  MediaType.video: 'video',
  MediaType.audio: 'audio',
  MediaType.document: 'document',
  MediaType.pdf: 'pdf',
  MediaType.text: 'text',
  MediaType.archive: 'archive',
  MediaType.other: 'other',
};

MediaUploadResponse _$MediaUploadResponseFromJson(Map<String, dynamic> json) =>
    MediaUploadResponse(
      mediaId: json['media_id'] as String,
      filePath: json['file_path'] as String,
      filename: json['filename'] as String,
      thumbnailGenerated: json['thumbnail_generated'] as bool,
      status: json['status'] as String,
      message: json['message'] as String,
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

MediaSearchResponse _$MediaSearchResponseFromJson(Map<String, dynamic> json) =>
    MediaSearchResponse(
      items: (json['items'] as List<dynamic>)
          .map((e) => MediaItem.fromJson(e as Map<String, dynamic>))
          .toList(),
      total: (json['total'] as num).toInt(),
      limit: (json['limit'] as num).toInt(),
      offset: (json['offset'] as num).toInt(),
      hasNext: json['has_next'] as bool,
      hasPrevious: json['has_previous'] as bool,
    );

Map<String, dynamic> _$MediaSearchResponseToJson(
        MediaSearchResponse instance) =>
    <String, dynamic>{
      'items': instance.items,
      'total': instance.total,
      'limit': instance.limit,
      'offset': instance.offset,
      'has_next': instance.hasNext,
      'has_previous': instance.hasPrevious,
    };

MediaSearchFilters _$MediaSearchFiltersFromJson(Map<String, dynamic> json) =>
    MediaSearchFilters(
      query: json['query'] as String?,
      mediaType: $enumDecodeNullable(_$MediaTypeEnumMap, json['media_type']),
      startDate: json['start_date'] == null
          ? null
          : DateTime.parse(json['start_date'] as String),
      endDate: json['end_date'] == null
          ? null
          : DateTime.parse(json['end_date'] as String),
      tags: (json['tags'] as List<dynamic>?)?.map((e) => e as String).toList(),
      collectionId: json['collection_id'] as String?,
      collectionIds: (json['collection_ids'] as List<dynamic>?)
          ?.map((e) => e as String)
          .toList(),
      sortBy: json['sort_by'] as String?,
      sortOrder: json['sort_order'] as String?,
      minFileSize: (json['min_file_size'] as num?)?.toInt(),
      maxFileSize: (json['max_file_size'] as num?)?.toInt(),
      hasThumbnail: json['has_thumbnail'] as bool?,
    );

Map<String, dynamic> _$MediaSearchFiltersToJson(MediaSearchFilters instance) =>
    <String, dynamic>{
      'query': instance.query,
      'media_type': _$MediaTypeEnumMap[instance.mediaType],
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
    };

DeviceAnalytics _$DeviceAnalyticsFromJson(Map<String, dynamic> json) =>
    DeviceAnalytics(
      totalMediaCount: (json['total_media_count'] as num).toInt(),
      totalFiles: (json['total_files'] as num).toInt(),
      totalStorageBytes: (json['total_storage_bytes'] as num).toInt(),
      uploadsToday: (json['uploads_today'] as num).toInt(),
      deviceBreakdown: Map<String, int>.from(json['device_breakdown'] as Map),
      manufacturerBreakdown:
          Map<String, int>.from(json['manufacturer_breakdown'] as Map),
      mediaTypeBreakdown:
          Map<String, int>.from(json['media_type_breakdown'] as Map),
      uploadTrends: Map<String, int>.from(json['upload_trends'] as Map),
      uploadsByDay: Map<String, int>.from(json['uploads_by_day'] as Map),
      storageUsageByDay:
          Map<String, int>.from(json['storage_usage_by_day'] as Map),
      topDevices: (json['top_devices'] as List<dynamic>)
          .map((e) => DeviceStats.fromJson(e as Map<String, dynamic>))
          .toList(),
    );

Map<String, dynamic> _$DeviceAnalyticsToJson(DeviceAnalytics instance) =>
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
      'top_devices': instance.topDevices,
    };

DeviceStats _$DeviceStatsFromJson(Map<String, dynamic> json) => DeviceStats(
      deviceName: json['device_name'] as String,
      deviceManufacturer: json['device_manufacturer'] as String,
      deviceModel: json['device_model'] as String,
      mediaCount: (json['media_count'] as num).toInt(),
      totalSize: (json['total_size'] as num).toInt(),
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
      shareId: json['share_id'] as String,
      shareToken: json['share_token'] as String,
      shareUrl: json['share_url'] as String,
      mediaId: json['media_id'] as String,
      permissions: (json['permissions'] as List<dynamic>)
          .map((e) => e as String)
          .toList(),
      expiresAt: json['expires_at'] == null
          ? null
          : DateTime.parse(json['expires_at'] as String),
      createdAt: DateTime.parse(json['created_at'] as String),
    );

Map<String, dynamic> _$ShareResponseToJson(ShareResponse instance) =>
    <String, dynamic>{
      'share_id': instance.shareId,
      'share_token': instance.shareToken,
      'share_url': instance.shareUrl,
      'media_id': instance.mediaId,
      'permissions': instance.permissions,
      'expires_at': instance.expiresAt?.toIso8601String(),
      'created_at': instance.createdAt.toIso8601String(),
    };

MediaListResponse _$MediaListResponseFromJson(Map<String, dynamic> json) =>
    MediaListResponse(
      items: (json['items'] as List<dynamic>)
          .map((e) => MediaItem.fromJson(e as Map<String, dynamic>))
          .toList(),
      totalCount: (json['totalCount'] as num).toInt(),
      page: (json['page'] as num).toInt(),
      limit: (json['limit'] as num).toInt(),
      hasMore: json['hasMore'] as bool,
    );

Map<String, dynamic> _$MediaListResponseToJson(MediaListResponse instance) =>
    <String, dynamic>{
      'items': instance.items,
      'totalCount': instance.totalCount,
      'page': instance.page,
      'limit': instance.limit,
      'hasMore': instance.hasMore,
    };

ShareLink _$ShareLinkFromJson(Map<String, dynamic> json) => ShareLink(
      id: json['id'] as String,
      url: json['url'] as String,
      itemIds:
          (json['itemIds'] as List<dynamic>).map((e) => e as String).toList(),
      createdAt: DateTime.parse(json['createdAt'] as String),
      expiresAt: json['expiresAt'] == null
          ? null
          : DateTime.parse(json['expiresAt'] as String),
      allowDownload: json['allowDownload'] as bool,
      hasPassword: json['hasPassword'] as bool,
      accessCount: (json['accessCount'] as num).toInt(),
      isActive: json['isActive'] as bool,
    );

Map<String, dynamic> _$ShareLinkToJson(ShareLink instance) => <String, dynamic>{
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

MostAccessedItem _$MostAccessedItemFromJson(Map<String, dynamic> json) =>
    MostAccessedItem(
      id: (json['id'] as num).toInt(),
      uuid: json['uuid'] as String,
      originalFilename: json['original_filename'] as String,
      mediaType: json['media_type'] as String,
      fileSize: (json['file_size'] as num).toInt(),
      createdAt: json['created_at'] as String,
      accessCount: (json['access_count'] as num).toInt(),
    );

Map<String, dynamic> _$MostAccessedItemToJson(MostAccessedItem instance) =>
    <String, dynamic>{
      'id': instance.id,
      'uuid': instance.uuid,
      'original_filename': instance.originalFilename,
      'media_type': instance.mediaType,
      'file_size': instance.fileSize,
      'created_at': instance.createdAt,
      'access_count': instance.accessCount,
    };

MediaAnalytics _$MediaAnalyticsFromJson(Map<String, dynamic> json) =>
    MediaAnalytics(
      totalItems: (json['totalItems'] as num).toInt(),
      totalSize: (json['totalSize'] as num).toInt(),
      averageFileSize: (json['averageFileSize'] as num).toDouble(),
      itemsByType: Map<String, int>.from(json['itemsByType'] as Map),
      uploadsByDay: Map<String, int>.from(json['uploadsByDay'] as Map),
      accessesByDay: Map<String, int>.from(json['accessesByDay'] as Map),
      popularTags: (json['popularTags'] as List<dynamic>)
          .map((e) => e as String)
          .toList(),
      mostAccessedItem: json['mostAccessedItem'] == null
          ? null
          : MostAccessedItem.fromJson(
              json['mostAccessedItem'] as Map<String, dynamic>),
    );

Map<String, dynamic> _$MediaAnalyticsToJson(MediaAnalytics instance) =>
    <String, dynamic>{
      'totalItems': instance.totalItems,
      'totalSize': instance.totalSize,
      'averageFileSize': instance.averageFileSize,
      'itemsByType': instance.itemsByType,
      'uploadsByDay': instance.uploadsByDay,
      'accessesByDay': instance.accessesByDay,
      'popularTags': instance.popularTags,
      'mostAccessedItem': instance.mostAccessedItem,
    };
