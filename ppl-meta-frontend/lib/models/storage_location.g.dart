// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'storage_location.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

StorageLocation _$StorageLocationFromJson(Map<String, dynamic> json) =>
    StorageLocation(
      uuid: json['uuid'] as String,
      userId: json['user_id'] as String,
      name: json['name'] as String,
      locationType: json['location_type'] as String,
      basePath: json['base_path'] as String,
      tier: json['tier'] as String,
      isActive: json['is_active'] as bool,
      isDefault: json['is_default'] as bool,
      totalCapacityBytes: (json['total_capacity_bytes'] as num?)?.toInt(),
      usedBytes: (json['used_bytes'] as num?)?.toInt() ?? 0,
      fileCount: (json['file_count'] as num?)?.toInt() ?? 0,
      usagePercentage: (json['usage_percentage'] as num?)?.toDouble() ?? 0.0,
      usedGb: (json['used_gb'] as num?)?.toDouble() ?? 0.0,
      totalCapacityGb: (json['total_capacity_gb'] as num?)?.toDouble(),
      freeGb: (json['free_gb'] as num?)?.toDouble(),
      mountVerified: json['mount_verified'] as bool? ?? false,
      lastVerifiedAt: json['last_verified_at'] as String?,
      createdAt: json['created_at'] as String?,
      updatedAt: json['updated_at'] as String?,
    );

Map<String, dynamic> _$StorageLocationToJson(StorageLocation instance) =>
    <String, dynamic>{
      'uuid': instance.uuid,
      'user_id': instance.userId,
      'name': instance.name,
      'location_type': instance.locationType,
      'base_path': instance.basePath,
      'tier': instance.tier,
      'is_active': instance.isActive,
      'is_default': instance.isDefault,
      'total_capacity_bytes': instance.totalCapacityBytes,
      'used_bytes': instance.usedBytes,
      'file_count': instance.fileCount,
      'usage_percentage': instance.usagePercentage,
      'used_gb': instance.usedGb,
      'total_capacity_gb': instance.totalCapacityGb,
      'free_gb': instance.freeGb,
      'mount_verified': instance.mountVerified,
      'last_verified_at': instance.lastVerifiedAt,
      'created_at': instance.createdAt,
      'updated_at': instance.updatedAt,
    };

StorageDashboard _$StorageDashboardFromJson(Map<String, dynamic> json) =>
    StorageDashboard(
      totalCapacityBytes: (json['total_capacity_bytes'] as num?)?.toInt(),
      totalUsedBytes: (json['total_used_bytes'] as num?)?.toInt() ?? 0,
      totalFiles: (json['total_files'] as num?)?.toInt() ?? 0,
      usagePercentage: (json['usage_percentage'] as num?)?.toDouble() ?? 0.0,
      activeUsedBytes: (json['active_used_bytes'] as num?)?.toInt() ?? 0,
      activeFiles: (json['active_files'] as num?)?.toInt() ?? 0,
      archiveUsedBytes: (json['archive_used_bytes'] as num?)?.toInt() ?? 0,
      archiveFiles: (json['archive_files'] as num?)?.toInt() ?? 0,
      totalCapacityGb: (json['total_capacity_gb'] as num?)?.toDouble(),
      totalUsedGb: (json['total_used_gb'] as num?)?.toDouble() ?? 0.0,
      freeGb: (json['free_gb'] as num?)?.toDouble(),
      locationCount: (json['location_count'] as num?)?.toInt() ?? 0,
      locations: json['locations'] as List<dynamic>? ?? const [],
      alerts: json['alerts'] as List<dynamic>? ?? const [],
      mediaRealUsedBytes: (json['media_real_used_bytes'] as num?)?.toInt() ?? 0,
      mediaRealFiles: (json['media_real_files'] as num?)?.toInt() ?? 0,
      mediaRealUsedGb: (json['media_real_used_gb'] as num?)?.toDouble() ?? 0.0,
      defaultActiveLocation:
          json['default_active_location'] as Map<String, dynamic>?,
    );

Map<String, dynamic> _$StorageDashboardToJson(StorageDashboard instance) =>
    <String, dynamic>{
      'total_capacity_bytes': instance.totalCapacityBytes,
      'total_used_bytes': instance.totalUsedBytes,
      'total_files': instance.totalFiles,
      'usage_percentage': instance.usagePercentage,
      'active_used_bytes': instance.activeUsedBytes,
      'active_files': instance.activeFiles,
      'archive_used_bytes': instance.archiveUsedBytes,
      'archive_files': instance.archiveFiles,
      'total_capacity_gb': instance.totalCapacityGb,
      'total_used_gb': instance.totalUsedGb,
      'free_gb': instance.freeGb,
      'location_count': instance.locationCount,
      'locations': instance.locations,
      'alerts': instance.alerts,
      'media_real_used_bytes': instance.mediaRealUsedBytes,
      'media_real_files': instance.mediaRealFiles,
      'media_real_used_gb': instance.mediaRealUsedGb,
      'default_active_location': instance.defaultActiveLocation,
    };
