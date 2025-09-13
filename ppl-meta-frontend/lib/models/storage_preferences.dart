import 'package:json_annotation/json_annotation.dart';

part 'storage_preferences.g.dart';

/// User storage preferences model
@JsonSerializable()
class UserStoragePreferences {
  @JsonKey(name: 'uuid')
  final String uuid;
  
  @JsonKey(name: 'user_id')
  final String userId;
  
  @JsonKey(name: 'default_collection_size_gb')
  final double defaultCollectionSizeGb;
  
  @JsonKey(name: 'default_live_portion_percentage')
  final double defaultLivePortionPercentage;
  
  @JsonKey(name: 'default_auto_archive_enabled')
  final bool defaultAutoArchiveEnabled;
  
  @JsonKey(name: 'default_min_age_for_archive_days')
  final int defaultMinAgeForArchiveDays;
  
  @JsonKey(name: 'enable_storage_notifications')
  final bool enableStorageNotifications;
  
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
  
  @JsonKey(name: 'auto_increase_quota_enabled')
  final bool autoIncreaseQuotaEnabled;
  
  @JsonKey(name: 'max_auto_quota_increase_gb')
  final double maxAutoQuotaIncreaseGb;
  
  @JsonKey(name: 'preferred_compression_enabled')
  final bool preferredCompressionEnabled;
  
  @JsonKey(name: 'preferred_video_quality')
  final String preferredVideoQuality;
  
  @JsonKey(name: 'enable_redundant_storage')
  final bool enableRedundantStorage;
  
  @JsonKey(name: 'created_at')
  final DateTime? createdAt;
  
  @JsonKey(name: 'updated_at')
  final DateTime? updatedAt;

  const UserStoragePreferences({
    required this.uuid,
    required this.userId,
    required this.defaultCollectionSizeGb,
    required this.defaultLivePortionPercentage,
    required this.defaultAutoArchiveEnabled,
    required this.defaultMinAgeForArchiveDays,
    required this.enableStorageNotifications,
    required this.notificationThresholdPercentage,
    required this.emailNotificationsEnabled,
    required this.pushNotificationsEnabled,
    required this.autoDeleteOldArchivesEnabled,
    required this.autoDeleteAfterDays,
    required this.autoIncreaseQuotaEnabled,
    required this.maxAutoQuotaIncreaseGb,
    required this.preferredCompressionEnabled,
    required this.preferredVideoQuality,
    required this.enableRedundantStorage,
    this.createdAt,
    this.updatedAt,
  });

  factory UserStoragePreferences.fromJson(Map<String, dynamic> json) =>
      _$UserStoragePreferencesFromJson(json);

  Map<String, dynamic> toJson() => _$UserStoragePreferencesToJson(this);
}

/// User storage preferences update model
@JsonSerializable()
class UserStoragePreferencesUpdate {
  @JsonKey(name: 'default_collection_size_gb')
  final double? defaultCollectionSizeGb;
  
  @JsonKey(name: 'default_live_portion_percentage')
  final double? defaultLivePortionPercentage;
  
  @JsonKey(name: 'default_auto_archive_enabled')
  final bool? defaultAutoArchiveEnabled;
  
  @JsonKey(name: 'default_min_age_for_archive_days')
  final int? defaultMinAgeForArchiveDays;
  
  @JsonKey(name: 'enable_storage_notifications')
  final bool? enableStorageNotifications;
  
  @JsonKey(name: 'notification_threshold_percentage')
  final double? notificationThresholdPercentage;
  
  @JsonKey(name: 'email_notifications_enabled')
  final bool? emailNotificationsEnabled;
  
  @JsonKey(name: 'push_notifications_enabled')
  final bool? pushNotificationsEnabled;
  
  @JsonKey(name: 'auto_delete_old_archives_enabled')
  final bool? autoDeleteOldArchivesEnabled;
  
  @JsonKey(name: 'auto_delete_after_days')
  final int? autoDeleteAfterDays;
  
  @JsonKey(name: 'auto_increase_quota_enabled')
  final bool? autoIncreaseQuotaEnabled;
  
  @JsonKey(name: 'max_auto_quota_increase_gb')
  final double? maxAutoQuotaIncreaseGb;
  
  @JsonKey(name: 'preferred_compression_enabled')
  final bool? preferredCompressionEnabled;
  
  @JsonKey(name: 'preferred_video_quality')
  final String? preferredVideoQuality;
  
  @JsonKey(name: 'enable_redundant_storage')
  final bool? enableRedundantStorage;

  const UserStoragePreferencesUpdate({
    this.defaultCollectionSizeGb,
    this.defaultLivePortionPercentage,
    this.defaultAutoArchiveEnabled,
    this.defaultMinAgeForArchiveDays,
    this.enableStorageNotifications,
    this.notificationThresholdPercentage,
    this.emailNotificationsEnabled,
    this.pushNotificationsEnabled,
    this.autoDeleteOldArchivesEnabled,
    this.autoDeleteAfterDays,
    this.autoIncreaseQuotaEnabled,
    this.maxAutoQuotaIncreaseGb,
    this.preferredCompressionEnabled,
    this.preferredVideoQuality,
    this.enableRedundantStorage,
  });

  factory UserStoragePreferencesUpdate.fromJson(Map<String, dynamic> json) =>
      _$UserStoragePreferencesUpdateFromJson(json);

  Map<String, dynamic> toJson() => _$UserStoragePreferencesUpdateToJson(this);
}

/// Storage recommendation model
@JsonSerializable()
class StorageRecommendation {
  final String type;
  final String message;
  final Map<String, dynamic> metadata;

  const StorageRecommendation({
    required this.type,
    required this.message,
    required this.metadata,
  });

  factory StorageRecommendation.fromJson(Map<String, dynamic> json) =>
      _$StorageRecommendationFromJson(json);

  Map<String, dynamic> toJson() => _$StorageRecommendationToJson(this);
}