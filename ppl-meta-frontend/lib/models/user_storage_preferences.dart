// User Storage Preferences Model
// Data model for managing user storage configuration and preferences

import 'package:json_annotation/json_annotation.dart';

part 'user_storage_preferences.g.dart';

@JsonSerializable()
class UserStoragePreferences {
  @JsonKey(name: 'user_uuid')
  final String userUuid;

  @JsonKey(name: 'default_collection_size_gb')
  final double defaultCollectionSizeGb;

  @JsonKey(name: 'default_live_portion_percentage')
  final double defaultLivePortionPercentage;

  @JsonKey(name: 'enable_storage_notifications')
  final bool enableStorageNotifications;

  @JsonKey(name: 'default_auto_archive_enabled')
  final bool defaultAutoArchiveEnabled;

  @JsonKey(name: 'default_min_age_for_archive_days')
  final int defaultMinAgeForArchiveDays;

  @JsonKey(name: 'notification_threshold_percentage')
  final double notificationThresholdPercentage;

  @JsonKey(name: 'email_notifications_enabled')
  final bool emailNotificationsEnabled;

  @JsonKey(name: 'push_notifications_enabled')
  final bool pushNotificationsEnabled;

  @JsonKey(name: 'auto_delete_old_archives_enabled')
  final bool autoDeleteOldArchivesEnabled;

  @JsonKey(name: 'auto_delete_after_days')
  final int autoDeleteAfterDays;

  @JsonKey(name: 'preferred_video_quality')
  final String preferredVideoQuality;

  @JsonKey(name: 'preferred_compression_enabled')
  final bool preferredCompressionEnabled;

  @JsonKey(name: 'created_at')
  final DateTime? createdAt;

  @JsonKey(name: 'updated_at')
  final DateTime? updatedAt;

  const UserStoragePreferences({
    required this.userUuid,
    this.defaultCollectionSizeGb = 50.0,
    this.defaultLivePortionPercentage = 70.0,
    this.enableStorageNotifications = true,
    this.defaultAutoArchiveEnabled = true,
    this.defaultMinAgeForArchiveDays = 7,
    this.notificationThresholdPercentage = 80.0,
    this.emailNotificationsEnabled = true,
    this.pushNotificationsEnabled = true,
    this.autoDeleteOldArchivesEnabled = false,
    this.autoDeleteAfterDays = 365,
    this.preferredVideoQuality = 'medium',
    this.preferredCompressionEnabled = true,
    this.createdAt,
    this.updatedAt,
  });

  factory UserStoragePreferences.fromJson(Map<String, dynamic> json) => 
    _$UserStoragePreferencesFromJson(json);

  Map<String, dynamic> toJson() => _$UserStoragePreferencesToJson(this);

  UserStoragePreferences copyWith({
    String? userUuid,
    double? defaultCollectionSizeGb,
    double? defaultLivePortionPercentage,
    bool? enableStorageNotifications,
    bool? defaultAutoArchiveEnabled,
    int? defaultMinAgeForArchiveDays,
    double? notificationThresholdPercentage,
    bool? emailNotificationsEnabled,
    bool? pushNotificationsEnabled,
    bool? autoDeleteOldArchivesEnabled,
    int? autoDeleteAfterDays,
    String? preferredVideoQuality,
    bool? preferredCompressionEnabled,
    DateTime? createdAt,
    DateTime? updatedAt,
  }) {
    return UserStoragePreferences(
      userUuid: userUuid ?? this.userUuid,
      defaultCollectionSizeGb: defaultCollectionSizeGb ?? this.defaultCollectionSizeGb,
      defaultLivePortionPercentage: defaultLivePortionPercentage ?? this.defaultLivePortionPercentage,
      enableStorageNotifications: enableStorageNotifications ?? this.enableStorageNotifications,
      defaultAutoArchiveEnabled: defaultAutoArchiveEnabled ?? this.defaultAutoArchiveEnabled,
      defaultMinAgeForArchiveDays: defaultMinAgeForArchiveDays ?? this.defaultMinAgeForArchiveDays,
      notificationThresholdPercentage: notificationThresholdPercentage ?? this.notificationThresholdPercentage,
      emailNotificationsEnabled: emailNotificationsEnabled ?? this.emailNotificationsEnabled,
      pushNotificationsEnabled: pushNotificationsEnabled ?? this.pushNotificationsEnabled,
      autoDeleteOldArchivesEnabled: autoDeleteOldArchivesEnabled ?? this.autoDeleteOldArchivesEnabled,
      autoDeleteAfterDays: autoDeleteAfterDays ?? this.autoDeleteAfterDays,
      preferredVideoQuality: preferredVideoQuality ?? this.preferredVideoQuality,
      preferredCompressionEnabled: preferredCompressionEnabled ?? this.preferredCompressionEnabled,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
    );
  }

  /// Calculate the archive portion percentage
  double get archivePortionPercentage => 100.0 - defaultLivePortionPercentage;

  /// Calculate live storage size in GB
  double get liveStorageSizeGb => defaultCollectionSizeGb * (defaultLivePortionPercentage / 100);

  /// Calculate archive storage size in GB
  double get archiveStorageSizeGb => defaultCollectionSizeGb * (archivePortionPercentage / 100);

  /// Check if storage preferences are optimized for efficiency
  bool get isOptimizedForEfficiency {
    return preferredCompressionEnabled && 
           defaultLivePortionPercentage <= 80.0 &&
           defaultAutoArchiveEnabled &&
           defaultMinAgeForArchiveDays <= 14;
  }

  /// Check if storage preferences are optimized for quality
  bool get isOptimizedForQuality {
    return !preferredCompressionEnabled ||
           preferredVideoQuality == 'high' ||
           preferredVideoQuality == 'ultra';
  }

  /// Get storage configuration summary
  String get configurationSummary {
    final liveSize = liveStorageSizeGb.toStringAsFixed(1);
    final archiveSize = archiveStorageSizeGb.toStringAsFixed(1);
    return '$liveSize GB live, $archiveSize GB archive';
  }

  /// Get notification settings summary
  String get notificationSummary {
    if (!enableStorageNotifications) return 'Disabled';
    
    final methods = <String>[];
    if (emailNotificationsEnabled) methods.add('Email');
    if (pushNotificationsEnabled) methods.add('Push');
    
    return '${methods.join(' + ')} at ${notificationThresholdPercentage.round()}%';
  }

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    
    return other is UserStoragePreferences &&
      other.userUuid == userUuid &&
      other.defaultCollectionSizeGb == defaultCollectionSizeGb &&
      other.defaultLivePortionPercentage == defaultLivePortionPercentage &&
      other.enableStorageNotifications == enableStorageNotifications &&
      other.defaultAutoArchiveEnabled == defaultAutoArchiveEnabled &&
      other.defaultMinAgeForArchiveDays == defaultMinAgeForArchiveDays &&
      other.notificationThresholdPercentage == notificationThresholdPercentage &&
      other.emailNotificationsEnabled == emailNotificationsEnabled &&
      other.pushNotificationsEnabled == pushNotificationsEnabled &&
      other.autoDeleteOldArchivesEnabled == autoDeleteOldArchivesEnabled &&
      other.autoDeleteAfterDays == autoDeleteAfterDays &&
      other.preferredVideoQuality == preferredVideoQuality &&
      other.preferredCompressionEnabled == preferredCompressionEnabled;
  }

  @override
  int get hashCode {
    return Object.hash(
      userUuid,
      defaultCollectionSizeGb,
      defaultLivePortionPercentage,
      enableStorageNotifications,
      defaultAutoArchiveEnabled,
      defaultMinAgeForArchiveDays,
      notificationThresholdPercentage,
      emailNotificationsEnabled,
      pushNotificationsEnabled,
      autoDeleteOldArchivesEnabled,
      autoDeleteAfterDays,
      preferredVideoQuality,
      preferredCompressionEnabled,
    );
  }

  @override
  String toString() {
    return 'UserStoragePreferences{userUuid: $userUuid, size: ${defaultCollectionSizeGb}GB, live: ${defaultLivePortionPercentage}%, notifications: $enableStorageNotifications}';
  }
}

@JsonSerializable()
class StorageUsageSummary {
  @JsonKey(name: 'total_collections')
  final int totalCollections;

  @JsonKey(name: 'total_used_gb')
  final double totalUsedGb;

  @JsonKey(name: 'total_allocated_gb')
  final double totalAllocatedGb;

  @JsonKey(name: 'usage_percentage')
  final double usagePercentage;

  @JsonKey(name: 'collections_near_capacity')
  final int collectionsNearCapacity;

  @JsonKey(name: 'live_storage_used_gb')
  final double liveStorageUsedGb;

  @JsonKey(name: 'archive_storage_used_gb')
  final double archiveStorageUsedGb;

  @JsonKey(name: 'last_updated')
  final DateTime lastUpdated;

  const StorageUsageSummary({
    required this.totalCollections,
    required this.totalUsedGb,
    required this.totalAllocatedGb,
    required this.usagePercentage,
    required this.collectionsNearCapacity,
    required this.liveStorageUsedGb,
    required this.archiveStorageUsedGb,
    required this.lastUpdated,
  });

  factory StorageUsageSummary.fromJson(Map<String, dynamic> json) => 
    _$StorageUsageSummaryFromJson(json);

  Map<String, dynamic> toJson() => _$StorageUsageSummaryToJson(this);

  /// Get available storage in GB
  double get availableStorageGb => totalAllocatedGb - totalUsedGb;

  /// Check if overall usage is critical
  bool get isCriticalUsage => usagePercentage >= 90.0;

  /// Check if overall usage is warning level
  bool get isWarningUsage => usagePercentage >= 80.0 && usagePercentage < 90.0;

  /// Get storage health status
  StorageHealthStatus get healthStatus {
    if (isCriticalUsage) return StorageHealthStatus.critical;
    if (isWarningUsage) return StorageHealthStatus.warning;
    return StorageHealthStatus.healthy;
  }
}

enum StorageHealthStatus {
  healthy,
  warning,
  critical,
}

extension StorageHealthStatusExtension on StorageHealthStatus {
  String get displayName {
    switch (this) {
      case StorageHealthStatus.healthy:
        return 'Healthy';
      case StorageHealthStatus.warning:
        return 'Warning';
      case StorageHealthStatus.critical:
        return 'Critical';
    }
  }

  Color get color {
    switch (this) {
      case StorageHealthStatus.healthy:
        return Colors.green;
      case StorageHealthStatus.warning:
        return Colors.orange;
      case StorageHealthStatus.critical:
        return Colors.red;
    }
  }

  IconData get icon {
    switch (this) {
      case StorageHealthStatus.healthy:
        return Icons.check_circle;
      case StorageHealthStatus.warning:
        return Icons.warning;
      case StorageHealthStatus.critical:
        return Icons.error;
    }
  }
}