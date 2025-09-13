// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'storage_preferences.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

UserStoragePreferences _$UserStoragePreferencesFromJson(
        Map<String, dynamic> json) =>
    UserStoragePreferences(
      uuid: json['uuid'] as String,
      userId: json['user_id'] as String,
      defaultCollectionSizeGb:
          (json['default_collection_size_gb'] as num).toDouble(),
      defaultLivePortionPercentage:
          (json['default_live_portion_percentage'] as num).toDouble(),
      defaultAutoArchiveEnabled: json['default_auto_archive_enabled'] as bool,
      defaultMinAgeForArchiveDays:
          (json['default_min_age_for_archive_days'] as num).toInt(),
      enableStorageNotifications: json['enable_storage_notifications'] as bool,
      notificationThresholdPercentage:
          (json['notification_threshold_percentage'] as num).toDouble(),
      emailNotificationsEnabled: json['email_notifications_enabled'] as bool,
      pushNotificationsEnabled: json['push_notifications_enabled'] as bool,
      autoDeleteOldArchivesEnabled:
          json['auto_delete_old_archives_enabled'] as bool,
      autoDeleteAfterDays: (json['auto_delete_after_days'] as num).toInt(),
      autoIncreaseQuotaEnabled: json['auto_increase_quota_enabled'] as bool,
      maxAutoQuotaIncreaseGb:
          (json['max_auto_quota_increase_gb'] as num).toDouble(),
      preferredCompressionEnabled:
          json['preferred_compression_enabled'] as bool,
      preferredVideoQuality: json['preferred_video_quality'] as String,
      enableRedundantStorage: json['enable_redundant_storage'] as bool,
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
      'uuid': instance.uuid,
      'user_id': instance.userId,
      'default_collection_size_gb': instance.defaultCollectionSizeGb,
      'default_live_portion_percentage': instance.defaultLivePortionPercentage,
      'default_auto_archive_enabled': instance.defaultAutoArchiveEnabled,
      'default_min_age_for_archive_days': instance.defaultMinAgeForArchiveDays,
      'enable_storage_notifications': instance.enableStorageNotifications,
      'notification_threshold_percentage':
          instance.notificationThresholdPercentage,
      'email_notifications_enabled': instance.emailNotificationsEnabled,
      'push_notifications_enabled': instance.pushNotificationsEnabled,
      'auto_delete_old_archives_enabled': instance.autoDeleteOldArchivesEnabled,
      'auto_delete_after_days': instance.autoDeleteAfterDays,
      'auto_increase_quota_enabled': instance.autoIncreaseQuotaEnabled,
      'max_auto_quota_increase_gb': instance.maxAutoQuotaIncreaseGb,
      'preferred_compression_enabled': instance.preferredCompressionEnabled,
      'preferred_video_quality': instance.preferredVideoQuality,
      'enable_redundant_storage': instance.enableRedundantStorage,
      'created_at': instance.createdAt?.toIso8601String(),
      'updated_at': instance.updatedAt?.toIso8601String(),
    };

UserStoragePreferencesUpdate _$UserStoragePreferencesUpdateFromJson(
        Map<String, dynamic> json) =>
    UserStoragePreferencesUpdate(
      defaultCollectionSizeGb:
          (json['default_collection_size_gb'] as num?)?.toDouble(),
      defaultLivePortionPercentage:
          (json['default_live_portion_percentage'] as num?)?.toDouble(),
      defaultAutoArchiveEnabled: json['default_auto_archive_enabled'] as bool?,
      defaultMinAgeForArchiveDays:
          (json['default_min_age_for_archive_days'] as num?)?.toInt(),
      enableStorageNotifications: json['enable_storage_notifications'] as bool?,
      notificationThresholdPercentage:
          (json['notification_threshold_percentage'] as num?)?.toDouble(),
      emailNotificationsEnabled: json['email_notifications_enabled'] as bool?,
      pushNotificationsEnabled: json['push_notifications_enabled'] as bool?,
      autoDeleteOldArchivesEnabled:
          json['auto_delete_old_archives_enabled'] as bool?,
      autoDeleteAfterDays: (json['auto_delete_after_days'] as num?)?.toInt(),
      autoIncreaseQuotaEnabled: json['auto_increase_quota_enabled'] as bool?,
      maxAutoQuotaIncreaseGb:
          (json['max_auto_quota_increase_gb'] as num?)?.toDouble(),
      preferredCompressionEnabled:
          json['preferred_compression_enabled'] as bool?,
      preferredVideoQuality: json['preferred_video_quality'] as String?,
      enableRedundantStorage: json['enable_redundant_storage'] as bool?,
    );

Map<String, dynamic> _$UserStoragePreferencesUpdateToJson(
        UserStoragePreferencesUpdate instance) =>
    <String, dynamic>{
      'default_collection_size_gb': instance.defaultCollectionSizeGb,
      'default_live_portion_percentage': instance.defaultLivePortionPercentage,
      'default_auto_archive_enabled': instance.defaultAutoArchiveEnabled,
      'default_min_age_for_archive_days': instance.defaultMinAgeForArchiveDays,
      'enable_storage_notifications': instance.enableStorageNotifications,
      'notification_threshold_percentage':
          instance.notificationThresholdPercentage,
      'email_notifications_enabled': instance.emailNotificationsEnabled,
      'push_notifications_enabled': instance.pushNotificationsEnabled,
      'auto_delete_old_archives_enabled': instance.autoDeleteOldArchivesEnabled,
      'auto_delete_after_days': instance.autoDeleteAfterDays,
      'auto_increase_quota_enabled': instance.autoIncreaseQuotaEnabled,
      'max_auto_quota_increase_gb': instance.maxAutoQuotaIncreaseGb,
      'preferred_compression_enabled': instance.preferredCompressionEnabled,
      'preferred_video_quality': instance.preferredVideoQuality,
      'enable_redundant_storage': instance.enableRedundantStorage,
    };

StorageRecommendation _$StorageRecommendationFromJson(
        Map<String, dynamic> json) =>
    StorageRecommendation(
      type: json['type'] as String,
      message: json['message'] as String,
      metadata: json['metadata'] as Map<String, dynamic>,
    );

Map<String, dynamic> _$StorageRecommendationToJson(
        StorageRecommendation instance) =>
    <String, dynamic>{
      'type': instance.type,
      'message': instance.message,
      'metadata': instance.metadata,
    };
