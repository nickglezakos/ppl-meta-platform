import 'package:json_annotation/json_annotation.dart';

part 'collection_models_new.g.dart';

/// Media collection model for the Media Service API
@JsonSerializable()
class MediaCollection {
  final String id;
  final String name;
  final String? description;
  final DateTime createdAt;
  final DateTime updatedAt;
  final int itemCount;
  final String? createdBy;
  final Map<String, dynamic>? metadata;
  final bool isPublic;

  const MediaCollection({
    required this.id,
    required this.name,
    this.description,
    required this.createdAt,
    required this.updatedAt,
    required this.itemCount,
    this.createdBy,
    this.metadata,
    this.isPublic = false,
  });

  factory MediaCollection.fromJson(Map<String, dynamic> json) => _$MediaCollectionFromJson(json);
  Map<String, dynamic> toJson() => _$MediaCollectionToJson(this);

  @override
  String toString() => 'MediaCollection(id: $id, name: $name, itemCount: $itemCount)';
}

/// Request model for creating a new collection
@JsonSerializable()
class CreateCollectionRequest {
  final String name;
  final String? description;
  final bool isPublic;
  final List<String> tags;
  final Map<String, dynamic>? metadata;

  const CreateCollectionRequest({
    required this.name,
    this.description,
    this.isPublic = false,
    this.tags = const [],
    this.metadata,
  });

  factory CreateCollectionRequest.fromJson(Map<String, dynamic> json) => _$CreateCollectionRequestFromJson(json);
  Map<String, dynamic> toJson() => _$CreateCollectionRequestToJson(this);

  /// Create a camera-specific collection request
  factory CreateCollectionRequest.forCamera({
    required String cameraId,
    required String cameraName,
    String? description,
    bool isPublic = false,
  }) {
    return CreateCollectionRequest(
      name: 'Camera $cameraName Snapshots',
      description: description ?? 'Auto-created collection for camera $cameraName snapshots',
      isPublic: isPublic,
      tags: ['camera', 'snapshots', cameraId],
      metadata: {
        'camera_id': cameraId,
        'camera_name': cameraName,
        'collection_type': 'camera_snapshots',
        'auto_created': true,
        'created_at': DateTime.now().toIso8601String(),
      },
    );
  }

  @override
  String toString() => 'CreateCollectionRequest(name: $name, isPublic: $isPublic)';
}

/// Request model for updating an existing collection
@JsonSerializable()
class UpdateCollectionRequest {
  final String? name;
  final String? description;
  final bool? isPublic;
  final List<String>? tags;
  final Map<String, dynamic>? metadata;

  const UpdateCollectionRequest({
    this.name,
    this.description,
    this.isPublic,
    this.tags,
    this.metadata,
  });

  factory UpdateCollectionRequest.fromJson(Map<String, dynamic> json) => _$UpdateCollectionRequestFromJson(json);
  Map<String, dynamic> toJson() => _$UpdateCollectionRequestToJson(this);

  @override
  String toString() => 'UpdateCollectionRequest(name: $name, isPublic: $isPublic)';
}

/// Collection response wrapper
@JsonSerializable()
class CollectionResponse {
  final bool success;
  final MediaCollection? collection;
  final String? message;
  final String? error;

  const CollectionResponse({
    required this.success,
    this.collection,
    this.message,
    this.error,
  });

  factory CollectionResponse.fromJson(Map<String, dynamic> json) => _$CollectionResponseFromJson(json);
  Map<String, dynamic> toJson() => _$CollectionResponseToJson(this);

  @override
  String toString() => 'CollectionResponse(success: $success, collection: $collection)';
}

/// Camera to collection mapping for local storage
@JsonSerializable()
class CameraCollectionMapping {
  final String cameraId;
  final String cameraName;
  final String collectionId;
  final String collectionName;
  final DateTime createdAt;
  final DateTime lastUsed;
  final bool autoCreated;

  const CameraCollectionMapping({
    required this.cameraId,
    required this.cameraName,
    required this.collectionId,
    required this.collectionName,
    required this.createdAt,
    required this.lastUsed,
    this.autoCreated = false,
  });

  factory CameraCollectionMapping.fromJson(Map<String, dynamic> json) => _$CameraCollectionMappingFromJson(json);
  Map<String, dynamic> toJson() => _$CameraCollectionMappingToJson(this);

  /// Create a new mapping for auto-created collection
  factory CameraCollectionMapping.forCamera({
    required String cameraId,
    required String cameraName,
    required String collectionId,
    required String collectionName,
  }) {
    final now = DateTime.now();
    return CameraCollectionMapping(
      cameraId: cameraId,
      cameraName: cameraName,
      collectionId: collectionId,
      collectionName: collectionName,
      createdAt: now,
      lastUsed: now,
      autoCreated: true,
    );
  }

  /// Update last used timestamp
  CameraCollectionMapping updateLastUsed() {
    return CameraCollectionMapping(
      cameraId: cameraId,
      cameraName: cameraName,
      collectionId: collectionId,
      collectionName: collectionName,
      createdAt: createdAt,
      lastUsed: DateTime.now(),
      autoCreated: autoCreated,
    );
  }

  @override
  String toString() => 'CameraCollectionMapping(cameraId: $cameraId, collectionId: $collectionId)';
}

/// Collection search and filter parameters
@JsonSerializable()
class CollectionSearchParams {
  final String? query;
  final List<String>? tags;
  final String? createdBy;
  final bool? isPublic;
  final DateTime? createdAfter;
  final DateTime? createdBefore;
  final int? minItems;
  final int? maxItems;
  final String? sortBy;
  final String? sortOrder;
  final int? limit;
  final int? offset;

  const CollectionSearchParams({
    this.query,
    this.tags,
    this.createdBy,
    this.isPublic,
    this.createdAfter,
    this.createdBefore,
    this.minItems,
    this.maxItems,
    this.sortBy,
    this.sortOrder,
    this.limit,
    this.offset,
  });

  factory CollectionSearchParams.fromJson(Map<String, dynamic> json) => _$CollectionSearchParamsFromJson(json);
  Map<String, dynamic> toJson() => _$CollectionSearchParamsToJson(this);

  @override
  String toString() => 'CollectionSearchParams(query: $query, tags: $tags)';
}
