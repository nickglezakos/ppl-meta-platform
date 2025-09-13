// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'user_storage_preferences.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

UserStoragePreferences _$UserStoragePreferencesFromJson(
        Map<String, dynamic> json) =>
    UserStoragePreferences(
      userUuid: json['user_uuid'] as String,
      defaultCollectionSizeGb:
          (json['default_collection_size_gb'] as num?)?.toDouble() ?? 50.0,
      defaultLivePortionPercentage:
          (json['default_live_portion_percentage'] as num?)?.toDouble() ?? 70.0,
      enableStorageNotifications:
          json['enable_storage_notifications'] as bool? ?? true,
      defaultAutoArchiveEnabled:
          json['default_auto_archive_enabled'] as bool? ?? true,
      defaultMinAgeForArchiveDays:
          (json['default_min_age_for_archive_days'] as num?)?.toInt() ?? 7,
      notificationThresholdPercentage:
          (json['notification_threshold_percentage'] as num?)?.toDouble() ??
              80.0,
      emailNotificationsEnabled:
          json['email_notifications_enabled'] as bool? ?? true,
      pushNotificationsEnabled:
          json['push_notifications_enabled'] as bool? ?? true,
      autoDeleteOldArchivesEnabled:
          json['auto_delete_old_archives_enabled'] as bool? ?? false,
      autoDeleteAfterDays:
          (json['auto_delete_after_days'] as num?)?.toInt() ?? 365,
      preferredVideoQuality:
          json['preferred_video_quality'] as String? ?? 'medium',
      preferredCompressionEnabled:
          json['preferred_compression_enabled'] as bool? ?? true,
      createdAt: json['created_at'] == null
          ? null
          : DateTime.parse(json['created_at'] as String),
      updatedAt: json['updated_at'] == null
          ? null
          : DateTime.parse(json['updated_at'] as String),
    );

Map<String, dynamic> _$UserStoragePreferencesToJson(
        UserStoragePreferences instance) =>
    <String, dynamic>{
      'user_uuid': instance.userUuid,
      'default_collection_size_gb': instance.defaultCollectionSizeGb,
      'default_live_portion_percentage': instance.defaultLivePortionPercentage,
      'enable_storage_notifications': instance.enableStorageNotifications,
      'default_auto_archive_enabled': instance.defaultAutoArchiveEnabled,
      'default_min_age_for_archive_days': instance.defaultMinAgeForArchiveDays,
      'notification_threshold_percentage':
          instance.notificationThresholdPercentage,
      'email_notifications_enabled': instance.emailNotificationsEnabled,
      'push_notifications_enabled': instance.pushNotificationsEnabled,
      'auto_delete_old_archives_enabled': instance.autoDeleteOldArchivesEnabled,
      'auto_delete_after_days': instance.autoDeleteAfterDays,
      'preferred_video_quality': instance.preferredVideoQuality,
      'preferred_compression_enabled': instance.preferredCompressionEnabled,
      'created_at': instance.createdAt?.toIso8601String(),
      'updated_at': instance.updatedAt?.toIso8601String(),
    };

StorageUsageSummary _$StorageUsageSummaryFromJson(Map<String, dynamic> json) =>
    StorageUsageSummary(
      totalCollections: (json['total_collections'] as num).toInt(),
      totalUsedGb: (json['total_used_gb'] as num).toDouble(),
      totalAllocatedGb: (json['total_allocated_gb'] as num).toDouble(),
      usagePercentage: (json['usage_percentage'] as num).toDouble(),
      collectionsNearCapacity:
          (json['collections_near_capacity'] as num).toInt(),
      liveStorageUsedGb: (json['live_storage_used_gb'] as num).toDouble(),
      archiveStorageUsedGb: (json['archive_storage_used_gb'] as num).toDouble(),
      lastUpdated: DateTime.parse(json['last_updated'] as String),
    );

Map<String, dynamic> _$StorageUsageSummaryToJson(
        StorageUsageSummary instance) =>
    <String, dynamic>{
      'total_collections': instance.totalCollections,
      'total_used_gb': instance.totalUsedGb,
      'total_allocated_gb': instance.totalAllocatedGb,
      'usage_percentage': instance.usagePercentage,
      'collections_near_capacity': instance.collectionsNearCapacity,
      'live_storage_used_gb': instance.liveStorageUsedGb,
      'archive_storage_used_gb': instance.archiveStorageUsedGb,
      'last_updated': instance.lastUpdated.toIso8601String(),
    };
