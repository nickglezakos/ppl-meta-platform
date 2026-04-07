import 'package:json_annotation/json_annotation.dart';

part 'storage_location.g.dart';

/// Storage location model
@JsonSerializable()
class StorageLocation {
  @JsonKey(name: 'uuid')
  final String uuid;

  @JsonKey(name: 'user_id')
  final String userId;

  @JsonKey(name: 'name')
  final String name;

  @JsonKey(name: 'location_type')
  final String locationType;

  @JsonKey(name: 'base_path')
  final String basePath;

  @JsonKey(name: 'tier')
  final String tier;

  @JsonKey(name: 'is_active')
  final bool isActive;

  @JsonKey(name: 'is_default')
  final bool isDefault;

  @JsonKey(name: 'total_capacity_bytes')
  final int? totalCapacityBytes;

  @JsonKey(name: 'used_bytes')
  final int usedBytes;

  @JsonKey(name: 'file_count')
  final int fileCount;

  @JsonKey(name: 'usage_percentage')
  final double usagePercentage;

  @JsonKey(name: 'used_gb')
  final double usedGb;

  @JsonKey(name: 'total_capacity_gb')
  final double? totalCapacityGb;

  @JsonKey(name: 'free_gb')
  final double? freeGb;

  @JsonKey(name: 'mount_verified')
  final bool mountVerified;

  @JsonKey(name: 'last_verified_at')
  final String? lastVerifiedAt;

  @JsonKey(name: 'created_at')
  final String? createdAt;

  @JsonKey(name: 'updated_at')
  final String? updatedAt;

  StorageLocation({
    required this.uuid,
    required this.userId,
    required this.name,
    required this.locationType,
    required this.basePath,
    required this.tier,
    required this.isActive,
    required this.isDefault,
    this.totalCapacityBytes,
    this.usedBytes = 0,
    this.fileCount = 0,
    this.usagePercentage = 0.0,
    this.usedGb = 0.0,
    this.totalCapacityGb,
    this.freeGb,
    this.mountVerified = false,
    this.lastVerifiedAt,
    this.createdAt,
    this.updatedAt,
  });

  factory StorageLocation.fromJson(Map<String, dynamic> json) =>
      _$StorageLocationFromJson(json);
  Map<String, dynamic> toJson() => _$StorageLocationToJson(this);

  bool get isCloud =>
      locationType == 'cloud_s3' ||
      locationType == 'cloud_azure' ||
      locationType == 'cloud_gcp';

  bool get isUnlimited => totalCapacityBytes == null;

  String get typeLabel {
    switch (locationType) {
      case 'local_disk':
        return 'Local Disk';
      case 'external_drive':
        return 'External Drive';
      case 'cloud_s3':
        return 'AWS S3';
      case 'cloud_azure':
        return 'Azure Blob';
      case 'cloud_gcp':
        return 'Google Cloud';
      default:
        return locationType;
    }
  }

  String get typeIcon {
    switch (locationType) {
      case 'local_disk':
        return '💾';
      case 'external_drive':
        return '🔌';
      case 'cloud_s3':
      case 'cloud_azure':
      case 'cloud_gcp':
        return '☁️';
      default:
        return '📁';
    }
  }
}

/// Storage dashboard summary model
@JsonSerializable()
class StorageDashboard {
  @JsonKey(name: 'total_capacity_bytes')
  final int? totalCapacityBytes;

  @JsonKey(name: 'total_used_bytes')
  final int totalUsedBytes;

  @JsonKey(name: 'total_files')
  final int totalFiles;

  @JsonKey(name: 'usage_percentage')
  final double usagePercentage;

  @JsonKey(name: 'active_used_bytes')
  final int activeUsedBytes;

  @JsonKey(name: 'active_files')
  final int activeFiles;

  @JsonKey(name: 'archive_used_bytes')
  final int archiveUsedBytes;

  @JsonKey(name: 'archive_files')
  final int archiveFiles;

  @JsonKey(name: 'total_capacity_gb')
  final double? totalCapacityGb;

  @JsonKey(name: 'total_used_gb')
  final double totalUsedGb;

  @JsonKey(name: 'free_gb')
  final double? freeGb;

  @JsonKey(name: 'location_count')
  final int locationCount;

  @JsonKey(name: 'locations')
  final List<dynamic> locations;

  @JsonKey(name: 'alerts')
  final List<dynamic> alerts;

  @JsonKey(name: 'media_real_used_bytes')
  final int mediaRealUsedBytes;

  @JsonKey(name: 'media_real_files')
  final int mediaRealFiles;

  @JsonKey(name: 'media_real_used_gb')
  final double mediaRealUsedGb;

  @JsonKey(name: 'default_active_location')
  final Map<String, dynamic>? defaultActiveLocation;

  StorageDashboard({
    this.totalCapacityBytes,
    this.totalUsedBytes = 0,
    this.totalFiles = 0,
    this.usagePercentage = 0.0,
    this.activeUsedBytes = 0,
    this.activeFiles = 0,
    this.archiveUsedBytes = 0,
    this.archiveFiles = 0,
    this.totalCapacityGb,
    this.totalUsedGb = 0.0,
    this.freeGb,
    this.locationCount = 0,
    this.locations = const [],
    this.alerts = const [],
    this.mediaRealUsedBytes = 0,
    this.mediaRealFiles = 0,
    this.mediaRealUsedGb = 0.0,
    this.defaultActiveLocation,
  });

  factory StorageDashboard.fromJson(Map<String, dynamic> json) =>
      _$StorageDashboardFromJson(json);
  Map<String, dynamic> toJson() => _$StorageDashboardToJson(this);
}

/// Storage location create/update request
class StorageLocationRequest {
  final String name;
  final String locationType;
  final String basePath;
  final String tier;
  final bool isDefault;
  final Map<String, dynamic>? cloudConfig;

  StorageLocationRequest({
    required this.name,
    required this.locationType,
    required this.basePath,
    this.tier = 'active',
    this.isDefault = false,
    this.cloudConfig,
  });

  Map<String, dynamic> toJson() => {
        'name': name,
        'location_type': locationType,
        'base_path': basePath,
        'tier': tier,
        'is_default': isDefault,
        if (cloudConfig != null) 'cloud_config': cloudConfig,
      };
}
