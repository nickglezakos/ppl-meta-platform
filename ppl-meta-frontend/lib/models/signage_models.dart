/// Data models for Signage Simple Player management
/// Includes video lists, devices, playback status, and sync history

import 'package:json_annotation/json_annotation.dart';

part 'signage_models.g.dart';

/// Loop mode for playlist playback
enum LoopMode {
  @JsonValue('once')
  once,
  @JsonValue('continuous')
  continuous,
  @JsonValue('shuffle')
  shuffle,
}

/// Sync mode for ETL operations
enum SyncMode {
  @JsonValue('full')
  full,
  @JsonValue('incremental')
  incremental,
}

/// Sync status
enum SyncStatus {
  @JsonValue('pending')
  pending,
  @JsonValue('in_progress')
  inProgress,
  @JsonValue('completed')
  completed,
  @JsonValue('partial')
  partial,
  @JsonValue('failed')
  failed,
}

/// Playback command
enum PlaybackCommand {
  @JsonValue('start')
  start,
  @JsonValue('pause')
  pause,
  @JsonValue('resume')
  resume,
  @JsonValue('stop')
  stop,
  @JsonValue('next')
  next,
  @JsonValue('previous')
  previous,
}

/// Playback state
enum PlaybackState {
  @JsonValue('playing')
  playing,
  @JsonValue('paused')
  paused,
  @JsonValue('stopped')
  stopped,
  @JsonValue('loading')
  loading,
  @JsonValue('buffering')
  buffering,
  @JsonValue('error')
  error,
}

/// Video List model
@JsonSerializable()
class VideoList {
  @JsonKey(name: 'id')
  final int? databaseId;
  @JsonKey(name: 'uuid')
  final String id;
  final String name;
  final String? description;
  @JsonKey(name: 'user_id')
  final String? userId;
  @JsonKey(name: 'collection_ids')
  final List<String>? collectionIds;
  @JsonKey(name: 'video_items')
  final List<VideoListItem>? videoItems;
  @JsonKey(name: 'loop_mode')
  final LoopMode? loopMode;
  @JsonKey(name: 'transition_duration_ms')
  final int? transitionDurationMs;
  @JsonKey(name: 'is_active')
  final bool isActive;
  @JsonKey(name: 'created_at')
  final DateTime createdAt;
  @JsonKey(name: 'updated_at')
  final DateTime? updatedAt;
  @JsonKey(name: 'video_count')
  final int? videoCount;
  @JsonKey(name: 'total_duration_ms')
  final int? totalDurationMs;

  VideoList({
    this.databaseId,
    required this.id,
    required this.name,
    this.description,
    this.userId,
    this.collectionIds,
    this.videoItems,
    this.loopMode,
    this.transitionDurationMs,
    this.isActive = true,
    required this.createdAt,
    this.updatedAt,
    this.videoCount,
    this.totalDurationMs,
  });

  factory VideoList.fromJson(Map<String, dynamic> json) => _$VideoListFromJson(json);
  Map<String, dynamic> toJson() => _$VideoListToJson(this);

  VideoList copyWith({
    int? databaseId,
    String? id,
    String? name,
    String? description,
    String? userId,
    List<String>? collectionIds,
    List<VideoListItem>? videoItems,
    LoopMode? loopMode,
    int? transitionDurationMs,
    bool? isActive,
    DateTime? createdAt,
    DateTime? updatedAt,
    int? videoCount,
    int? totalDurationMs,
  }) {
    return VideoList(
      databaseId: databaseId ?? this.databaseId,
      id: id ?? this.id,
      name: name ?? this.name,
      description: description ?? this.description,
      userId: userId ?? this.userId,
      collectionIds: collectionIds ?? this.collectionIds,
      videoItems: videoItems ?? this.videoItems,
      loopMode: loopMode ?? this.loopMode,
      transitionDurationMs: transitionDurationMs ?? this.transitionDurationMs,
      isActive: isActive ?? this.isActive,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      videoCount: videoCount ?? this.videoCount,
      totalDurationMs: totalDurationMs ?? this.totalDurationMs,
    );
  }
}

/// Video List Item model
@JsonSerializable()
class VideoListItem {
  @JsonKey(name: 'uuid')
  final String id;
  @JsonKey(name: 'video_id')
  final String videoId;
  @JsonKey(name: 'collection_id')
  final String collectionId;
  @JsonKey(name: 'sequence_order')
  final int sequenceOrder;
  @JsonKey(name: 'duration_override')
  final int? durationOverride;
  final Map<String, dynamic>? metadata;
  
  // Additional fields for UI display
  @JsonKey(name: 'video_title')
  final String? videoTitle;
  @JsonKey(name: 'video_url')
  final String? videoUrl;
  @JsonKey(name: 'thumbnail_url')
  final String? thumbnailUrl;

  VideoListItem({
    required this.id,
    required this.videoId,
    required this.collectionId,
    required this.sequenceOrder,
    this.durationOverride,
    this.metadata,
    this.videoTitle,
    this.videoUrl,
    this.thumbnailUrl,
  });

  factory VideoListItem.fromJson(Map<String, dynamic> json) => _$VideoListItemFromJson(json);
  Map<String, dynamic> toJson() => _$VideoListItemToJson(this);

  VideoListItem copyWith({
    String? id,
    String? videoId,
    String? collectionId,
    int? sequenceOrder,
    int? durationOverride,
    Map<String, dynamic>? metadata,
    String? videoTitle,
    String? videoUrl,
    String? thumbnailUrl,
  }) {
    return VideoListItem(
      id: id ?? this.id,
      videoId: videoId ?? this.videoId,
      collectionId: collectionId ?? this.collectionId,
      sequenceOrder: sequenceOrder ?? this.sequenceOrder,
      durationOverride: durationOverride ?? this.durationOverride,
      metadata: metadata ?? this.metadata,
      videoTitle: videoTitle ?? this.videoTitle,
      videoUrl: videoUrl ?? this.videoUrl,
      thumbnailUrl: thumbnailUrl ?? this.thumbnailUrl,
    );
  }
}

/// Create Video List Request
@JsonSerializable()
class CreateVideoListRequest {
  final String name;
  final String? description;
  @JsonKey(name: 'collection_ids')
  final List<String> collectionIds;
  @JsonKey(name: 'video_order')
  final List<VideoOrderItem> videoOrder;
  @JsonKey(name: 'loop_mode')
  final LoopMode loopMode;
  @JsonKey(name: 'transition_duration')
  final int transitionDurationMs;

  CreateVideoListRequest({
    required this.name,
    this.description,
    required this.collectionIds,
    required this.videoOrder,
    this.loopMode = LoopMode.continuous,
    this.transitionDurationMs = 1000,
  });

  // Manually implemented toJson since build_runner isn't generating it
  Map<String, dynamic> toJson() {
    return {
      'name': name,
      if (description != null) 'description': description,
      'collection_ids': collectionIds,
      'video_order': videoOrder.map((v) => v.toJson()).toList(),
      'loop_mode': loopMode.name,
      'transition_duration': transitionDurationMs,
    };
  }

  factory CreateVideoListRequest.fromJson(Map<String, dynamic> json) {
    return CreateVideoListRequest(
      name: json['name'] as String,
      description: json['description'] as String?,
      collectionIds: (json['collection_ids'] as List<dynamic>).cast<String>(),
      videoOrder: (json['video_order'] as List<dynamic>)
          .map((e) => VideoOrderItem.fromJson(e as Map<String, dynamic>))
          .toList(),
      loopMode: LoopMode.values.firstWhere((e) => e.name == json['loop_mode']),
      transitionDurationMs: json['transition_duration'] as int? ?? 1000,
    );
  }
}

/// Video order item for creating/updating playlists
@JsonSerializable()
class VideoOrderItem {
  @JsonKey(name: 'collection_id')
  final String collectionId;
  @JsonKey(name: 'video_id')
  final String videoId;
  final int sequence;

  VideoOrderItem({
    required this.collectionId,
    required this.videoId,
    required this.sequence,
  });

  // Manually implemented since build_runner isn't generating it
  Map<String, dynamic> toJson() {
    return {
      'collection_id': collectionId,
      'video_id': videoId,
      'sequence': sequence,
    };
  }

  factory VideoOrderItem.fromJson(Map<String, dynamic> json) {
    return VideoOrderItem(
      collectionId: json['collection_id'] as String,
      videoId: json['video_id'] as String,
      sequence: json['sequence'] as int,
    );
  }
}

/// Signage Device model (from service discovery)
@JsonSerializable()
class SignageDevice {
  @JsonKey(name: 'uuid')
  final String id;
  final String name;
  @JsonKey(name: 'device_id')
  final String deviceId;
  @JsonKey(name: 'service_type')
  final String serviceType;
  final String host;
  final int port;
  final String status;
  final Map<String, dynamic>? metadata;
  @JsonKey(name: 'last_heartbeat')
  final DateTime? lastHeartbeat;
  @JsonKey(name: 'registered_at')
  final DateTime? registeredAt;

  SignageDevice({
    required this.id,
    required this.name,
    required this.deviceId,
    required this.serviceType,
    required this.host,
    required this.port,
    required this.status,
    this.metadata,
    this.lastHeartbeat,
    this.registeredAt,
  });

  factory SignageDevice.fromJson(Map<String, dynamic> json) => 
      _$SignageDeviceFromJson(json);
  Map<String, dynamic> toJson() => _$SignageDeviceToJson(this);

  bool get isOnline => status == 'healthy' && lastHeartbeat != null &&
      DateTime.now().toUtc().difference(lastHeartbeat!).inMinutes < 2;
}

/// Database Signage Device model (from media service API)
@JsonSerializable()
class DatabaseSignageDevice {
  @JsonKey(name: 'uuid')
  final String id;
  @JsonKey(name: 'device_name')
  final String name;
  @JsonKey(name: 'device_id')
  final String deviceId;
  @JsonKey(name: 'device_hostname')
  final String? hostname;
  @JsonKey(name: 'ip_address')
  final String? ipAddress;
  final int? port;
  final String? location;
  final String? notes;
  @JsonKey(name: 'is_active')
  final bool isActive;
  @JsonKey(name: 'is_online')
  final bool isOnline;
  @JsonKey(name: 'last_seen')
  final DateTime? lastSeen;
  @JsonKey(name: 'last_heartbeat')
  final DateTime? lastHeartbeat;
  @JsonKey(name: 'current_video_list_id')
  final int? currentVideoListId;
  @JsonKey(name: 'playback_state')
  final String? playbackState;
  @JsonKey(name: 'app_version')
  final String? appVersion;
  @JsonKey(name: 'screen_resolution')
  final String? screenResolution;
  @JsonKey(name: 'created_at')
  final DateTime? createdAt;
  @JsonKey(name: 'updated_at')
  final DateTime? updatedAt;

  DatabaseSignageDevice({
    required this.id,
    required this.name,
    required this.deviceId,
    this.hostname,
    this.ipAddress,
    this.port,
    this.location,
    this.notes,
    required this.isActive,
    required this.isOnline,
    this.lastSeen,
    this.lastHeartbeat,
    this.currentVideoListId,
    this.playbackState,
    this.appVersion,
    this.screenResolution,
    this.createdAt,
    this.updatedAt,
  });

  factory DatabaseSignageDevice.fromJson(Map<String, dynamic> json) => 
      _$DatabaseSignageDeviceFromJson(json);
  Map<String, dynamic> toJson() => _$DatabaseSignageDeviceToJson(this);
}

/// Sync Request model
@JsonSerializable()
class SyncRequest {
  @JsonKey(name: 'video_list_id')
  final String videoListId;
  @JsonKey(name: 'target_devices')
  final List<String> targetDevices;
  @JsonKey(name: 'sync_mode')
  final SyncMode syncMode;
  @JsonKey(name: 'force_update')
  final bool forceUpdate;
  @JsonKey(name: 'notify_on_complete')
  final bool notifyOnComplete;

  SyncRequest({
    required this.videoListId,
    required this.targetDevices,
    this.syncMode = SyncMode.incremental,
    this.forceUpdate = false,
    this.notifyOnComplete = true,
  });

  factory SyncRequest.fromJson(Map<String, dynamic> json) => 
      _$SyncRequestFromJson(json);
  Map<String, dynamic> toJson() => _$SyncRequestToJson(this);
}

/// Sync Result model
@JsonSerializable()
class SyncResult {
  @JsonKey(name: 'sync_job_id')
  final String syncJobId;
  final SyncStatus status;
  @JsonKey(name: 'target_device_count')
  final int targetDeviceCount;
  @JsonKey(name: 'estimated_completion_at')
  final DateTime? estimatedCompletionAt;
  @JsonKey(name: 'videos_synced')
  final int? videosSynced;
  @JsonKey(name: 'videos_failed')
  final int? videosFailed;
  @JsonKey(name: 'sync_duration_ms')
  final int? syncDurationMs;
  @JsonKey(name: 'error_message')
  final String? errorMessage;

  SyncResult({
    required this.syncJobId,
    required this.status,
    required this.targetDeviceCount,
    this.estimatedCompletionAt,
    this.videosSynced,
    this.videosFailed,
    this.syncDurationMs,
    this.errorMessage,
  });

  factory SyncResult.fromJson(Map<String, dynamic> json) => 
      _$SyncResultFromJson(json);
  Map<String, dynamic> toJson() => _$SyncResultToJson(this);
}

/// Playback Control Request model
@JsonSerializable()
class PlaybackControlRequest {
  @JsonKey(name: 'device_ids')
  final List<String> deviceIds;
  final PlaybackCommand command;
  @JsonKey(name: 'video_list_id')
  final String? videoListId;
  final PlaybackParameters? parameters;

  PlaybackControlRequest({
    required this.deviceIds,
    required this.command,
    this.videoListId,
    this.parameters,
  });

  factory PlaybackControlRequest.fromJson(Map<String, dynamic> json) => 
      _$PlaybackControlRequestFromJson(json);
  Map<String, dynamic> toJson() => _$PlaybackControlRequestToJson(this);
}

/// Playback Parameters model
@JsonSerializable()
class PlaybackParameters {
  @JsonKey(name: 'start_index')
  final int startIndex;
  final int volume;
  final double speed;

  PlaybackParameters({
    this.startIndex = 0,
    this.volume = 80,
    this.speed = 1.0,
  });

  factory PlaybackParameters.fromJson(Map<String, dynamic> json) => 
      _$PlaybackParametersFromJson(json);
  Map<String, dynamic> toJson() => _$PlaybackParametersToJson(this);
}

/// Playback Status model
@JsonSerializable()
class PlaybackStatus {
  @JsonKey(name: 'device_id')
  final String deviceId;
  @JsonKey(name: 'current_video')
  final CurrentVideoInfo? currentVideo;
  final PlaylistInfo? playlist;
  @JsonKey(name: 'playback_state')
  final PlaybackState playbackState;
  @JsonKey(name: 'recently_played')
  final List<VideoHistoryItem> recentlyPlayed;
  @JsonKey(name: 'upcoming_videos')
  final List<VideoListItem> upcomingVideos;
  @JsonKey(name: 'history_count')
  final int historyCount;
  @JsonKey(name: 'upcoming_count')
  final int upcomingCount;

  PlaybackStatus({
    required this.deviceId,
    this.currentVideo,
    this.playlist,
    required this.playbackState,
    required this.recentlyPlayed,
    required this.upcomingVideos,
    required this.historyCount,
    required this.upcomingCount,
  });

  factory PlaybackStatus.fromJson(Map<String, dynamic> json) => 
      _$PlaybackStatusFromJson(json);
  Map<String, dynamic> toJson() => _$PlaybackStatusToJson(this);
}

/// Current Video Info model
@JsonSerializable()
class CurrentVideoInfo {
  @JsonKey(name: 'video_id')
  final String videoId;
  final String title;
  @JsonKey(name: 'position_ms')
  final int positionMs;
  @JsonKey(name: 'duration_ms')
  final int durationMs;
  @JsonKey(name: 'progress_percent')
  final double progressPercent;

  // Helper getters for compatibility
  int get currentPosition => positionMs;
  int get duration => durationMs;

  CurrentVideoInfo({
    required this.videoId,
    required this.title,
    required this.positionMs,
    required this.durationMs,
    required this.progressPercent,
  });

  factory CurrentVideoInfo.fromJson(Map<String, dynamic> json) => 
      _$CurrentVideoInfoFromJson(json);
  Map<String, dynamic> toJson() => _$CurrentVideoInfoToJson(this);
}

/// Playlist Info model
@JsonSerializable()
class PlaylistInfo {
  final String id;
  final String name;
  @JsonKey(name: 'total_videos')
  final int totalVideos;
  @JsonKey(name: 'current_index')
  final int currentIndex;
  @JsonKey(name: 'loop_mode')
  final String? loopMode;
  @JsonKey(name: 'video_list_id')
  final String? videoListId;

  PlaylistInfo({
    required this.id,
    required this.name,
    required this.totalVideos,
    required this.currentIndex,
    this.loopMode,
    this.videoListId,
  });

  factory PlaylistInfo.fromJson(Map<String, dynamic> json) => 
      _$PlaylistInfoFromJson(json);
  Map<String, dynamic> toJson() => _$PlaylistInfoToJson(this);
}

/// Video History Item model
@JsonSerializable()
class VideoHistoryItem {
  @JsonKey(name: 'video_id')
  final String videoId;
  final String title;
  @JsonKey(name: 'completed_at')
  final DateTime completedAt;

  VideoHistoryItem({
    required this.videoId,
    required this.title,
    required this.completedAt,
  });

  factory VideoHistoryItem.fromJson(Map<String, dynamic> json) => 
      _$VideoHistoryItemFromJson(json);
  Map<String, dynamic> toJson() => _$VideoHistoryItemToJson(this);
}

/// Video Lists Response model
@JsonSerializable()
class VideoListsResponse {
  @JsonKey(name: 'total_count')
  final int totalCount;
  final int page;
  @JsonKey(name: 'page_size')
  final int pageSize;
  final List<VideoList> results;

  VideoListsResponse({
    required this.totalCount,
    required this.page,
    required this.pageSize,
    required this.results,
  });

  factory VideoListsResponse.fromJson(Map<String, dynamic> json) => 
      _$VideoListsResponseFromJson(json);
  Map<String, dynamic> toJson() => _$VideoListsResponseToJson(this);
}
