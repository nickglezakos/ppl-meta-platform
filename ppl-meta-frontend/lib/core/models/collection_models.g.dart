// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'collection_models.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

MediaCollection _$MediaCollectionFromJson(Map<String, dynamic> json) =>
    MediaCollection(
      id: json['id'] as String,
      name: json['name'] as String,
      description: json['description'] as String?,
      createdAt: json['created_at'] == null
          ? null
          : DateTime.parse(json['created_at'] as String),
      updatedAt: json['updated_at'] == null
          ? null
          : DateTime.parse(json['updated_at'] as String),
      itemCount: (json['itemCount'] as num?)?.toInt() ?? 0,
      createdBy: json['created_by'] as String?,
      cameraDeviceId: json['camera_device_id'] as String?,
      metadata: json['metadata'] as Map<String, dynamic>?,
      isPublic: json['is_public'] as bool? ?? false,
      uuid: json['uuid'] as String?,
    );

Map<String, dynamic> _$MediaCollectionToJson(MediaCollection instance) =>
    <String, dynamic>{
      'id': instance.id,
      'name': instance.name,
      'description': instance.description,
      'created_at': instance.createdAt?.toIso8601String(),
      'updated_at': instance.updatedAt?.toIso8601String(),
      'itemCount': instance.itemCount,
      'created_by': instance.createdBy,
      'camera_device_id': instance.cameraDeviceId,
      'metadata': instance.metadata,
      'is_public': instance.isPublic,
      'uuid': instance.uuid,
    };

CreateCollectionRequest _$CreateCollectionRequestFromJson(
        Map<String, dynamic> json) =>
    CreateCollectionRequest(
      name: json['name'] as String,
      description: json['description'] as String?,
      isPublic: json['isPublic'] as bool? ?? false,
      tags:
          (json['tags'] as List<dynamic>?)?.map((e) => e as String).toList() ??
              const [],
      metadata: json['metadata'] as Map<String, dynamic>?,
    );

Map<String, dynamic> _$CreateCollectionRequestToJson(
        CreateCollectionRequest instance) =>
    <String, dynamic>{
      'name': instance.name,
      'description': instance.description,
      'isPublic': instance.isPublic,
      'tags': instance.tags,
      'metadata': instance.metadata,
    };

UpdateCollectionRequest _$UpdateCollectionRequestFromJson(
        Map<String, dynamic> json) =>
    UpdateCollectionRequest(
      name: json['name'] as String?,
      description: json['description'] as String?,
      isPublic: json['isPublic'] as bool?,
      tags: (json['tags'] as List<dynamic>?)?.map((e) => e as String).toList(),
      metadata: json['metadata'] as Map<String, dynamic>?,
    );

Map<String, dynamic> _$UpdateCollectionRequestToJson(
        UpdateCollectionRequest instance) =>
    <String, dynamic>{
      'name': instance.name,
      'description': instance.description,
      'isPublic': instance.isPublic,
      'tags': instance.tags,
      'metadata': instance.metadata,
    };

CollectionResponse _$CollectionResponseFromJson(Map<String, dynamic> json) =>
    CollectionResponse(
      success: json['success'] as bool,
      collection: json['collection'] == null
          ? null
          : MediaCollection.fromJson(
              json['collection'] as Map<String, dynamic>),
      message: json['message'] as String?,
      error: json['error'] as String?,
    );

Map<String, dynamic> _$CollectionResponseToJson(CollectionResponse instance) =>
    <String, dynamic>{
      'success': instance.success,
      'collection': instance.collection,
      'message': instance.message,
      'error': instance.error,
    };

CameraCollectionMapping _$CameraCollectionMappingFromJson(
        Map<String, dynamic> json) =>
    CameraCollectionMapping(
      cameraId: json['cameraId'] as String,
      cameraName: json['cameraName'] as String,
      collectionId: json['collectionId'] as String,
      collectionName: json['collectionName'] as String,
      createdAt: DateTime.parse(json['createdAt'] as String),
      lastUsed: DateTime.parse(json['lastUsed'] as String),
      autoCreated: json['autoCreated'] as bool? ?? false,
    );

Map<String, dynamic> _$CameraCollectionMappingToJson(
        CameraCollectionMapping instance) =>
    <String, dynamic>{
      'cameraId': instance.cameraId,
      'cameraName': instance.cameraName,
      'collectionId': instance.collectionId,
      'collectionName': instance.collectionName,
      'createdAt': instance.createdAt.toIso8601String(),
      'lastUsed': instance.lastUsed.toIso8601String(),
      'autoCreated': instance.autoCreated,
    };

CollectionSearchParams _$CollectionSearchParamsFromJson(
        Map<String, dynamic> json) =>
    CollectionSearchParams(
      query: json['query'] as String?,
      tags: (json['tags'] as List<dynamic>?)?.map((e) => e as String).toList(),
      createdBy: json['createdBy'] as String?,
      isPublic: json['isPublic'] as bool?,
      createdAfter: json['createdAfter'] == null
          ? null
          : DateTime.parse(json['createdAfter'] as String),
      createdBefore: json['createdBefore'] == null
          ? null
          : DateTime.parse(json['createdBefore'] as String),
      minItems: (json['minItems'] as num?)?.toInt(),
      maxItems: (json['maxItems'] as num?)?.toInt(),
      sortBy: json['sortBy'] as String?,
      sortOrder: json['sortOrder'] as String?,
      limit: (json['limit'] as num?)?.toInt(),
      offset: (json['offset'] as num?)?.toInt(),
    );

Map<String, dynamic> _$CollectionSearchParamsToJson(
        CollectionSearchParams instance) =>
    <String, dynamic>{
      'query': instance.query,
      'tags': instance.tags,
      'createdBy': instance.createdBy,
      'isPublic': instance.isPublic,
      'createdAfter': instance.createdAfter?.toIso8601String(),
      'createdBefore': instance.createdBefore?.toIso8601String(),
      'minItems': instance.minItems,
      'maxItems': instance.maxItems,
      'sortBy': instance.sortBy,
      'sortOrder': instance.sortOrder,
      'limit': instance.limit,
      'offset': instance.offset,
    };
