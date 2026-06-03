// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'signage_models.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

VideoList _$VideoListFromJson(Map<String, dynamic> json) => VideoList(
  databaseId: (json['id'] as num?)?.toInt(),
      id: json['uuid'] as String,
      name: json['name'] as String,
      description: json['description'] as String?,
      userId: json['user_id'] as String?,
      collectionIds: (json['collection_ids'] as List<dynamic>?)
          ?.map((e) => e as String)
          .toList(),
      videoItems: (json['video_items'] as List<dynamic>?)
          ?.map((e) => VideoListItem.fromJson(e as Map<String, dynamic>))
          .toList(),
      loopMode: $enumDecodeNullable(_$LoopModeEnumMap, json['loop_mode']),
      transitionDurationMs: (json['transition_duration_ms'] as num?)?.toInt(),
      isActive: json['is_active'] as bool? ?? true,
      createdAt: DateTime.parse(json['created_at'] as String),
      updatedAt: json['updated_at'] == null
          ? null
          : DateTime.parse(json['updated_at'] as String),
      videoCount: (json['video_count'] as num?)?.toInt(),
      totalDurationMs: (json['total_duration_ms'] as num?)?.toInt(),
    );

Map<String, dynamic> _$VideoListToJson(VideoList instance) => <String, dynamic>{
  'id': instance.databaseId,
      'uuid': instance.id,
      'name': instance.name,
      'description': instance.description,
      'user_id': instance.userId,
      'collection_ids': instance.collectionIds,
      'video_items': instance.videoItems,
      'loop_mode': _$LoopModeEnumMap[instance.loopMode],
      'transition_duration_ms': instance.transitionDurationMs,
      'is_active': instance.isActive,
      'created_at': instance.createdAt.toIso8601String(),
      'updated_at': instance.updatedAt?.toIso8601String(),
      'video_count': instance.videoCount,
      'total_duration_ms': instance.totalDurationMs,
    };

const _$LoopModeEnumMap = {
  LoopMode.once: 'once',
  LoopMode.continuous: 'continuous',
  LoopMode.shuffle: 'shuffle',
};

VideoListItem _$VideoListItemFromJson(Map<String, dynamic> json) =>
    VideoListItem(
      id: json['uuid'] as String,
      videoId: json['video_id'] as String,
      collectionId: json['collection_id'] as String,
      sequenceOrder: (json['sequence_order'] as num).toInt(),
      durationOverride: (json['duration_override'] as num?)?.toInt(),
      metadata: json['metadata'] as Map<String, dynamic>?,
      videoTitle: json['video_title'] as String?,
      videoUrl: json['video_url'] as String?,
      thumbnailUrl: json['thumbnail_url'] as String?,
    );

Map<String, dynamic> _$VideoListItemToJson(VideoListItem instance) =>
    <String, dynamic>{
      'uuid': instance.id,
      'video_id': instance.videoId,
      'collection_id': instance.collectionId,
      'sequence_order': instance.sequenceOrder,
      'duration_override': instance.durationOverride,
      'metadata': instance.metadata,
      'video_title': instance.videoTitle,
      'video_url': instance.videoUrl,
      'thumbnail_url': instance.thumbnailUrl,
    };

CreateVideoListRequest _$CreateVideoListRequestFromJson(
        Map<String, dynamic> json) =>
    CreateVideoListRequest(
      name: json['name'] as String,
      description: json['description'] as String?,
      collectionIds: (json['collection_ids'] as List<dynamic>)
          .map((e) => e as String)
          .toList(),
      videoOrder: (json['video_order'] as List<dynamic>)
          .map((e) => VideoOrderItem.fromJson(e as Map<String, dynamic>))
          .toList(),
      loopMode: $enumDecodeNullable(_$LoopModeEnumMap, json['loop_mode']) ??
          LoopMode.continuous,
      transitionDurationMs:
          (json['transition_duration'] as num?)?.toInt() ?? 1000,
    );

Map<String, dynamic> _$CreateVideoListRequestToJson(
        CreateVideoListRequest instance) =>
    <String, dynamic>{
      'name': instance.name,
      'description': instance.description,
      'collection_ids': instance.collectionIds,
      'video_order': instance.videoOrder,
      'loop_mode': _$LoopModeEnumMap[instance.loopMode]!,
      'transition_duration': instance.transitionDurationMs,
    };

VideoOrderItem _$VideoOrderItemFromJson(Map<String, dynamic> json) =>
    VideoOrderItem(
      collectionId: json['collection_id'] as String,
      videoId: json['video_id'] as String,
      sequence: (json['sequence'] as num).toInt(),
    );

Map<String, dynamic> _$VideoOrderItemToJson(VideoOrderItem instance) =>
    <String, dynamic>{
      'collection_id': instance.collectionId,
      'video_id': instance.videoId,
      'sequence': instance.sequence,
    };

SignageDevice _$SignageDeviceFromJson(Map<String, dynamic> json) =>
    SignageDevice(
      id: json['uuid'] as String,
      name: json['name'] as String,
      deviceId: json['device_id'] as String,
      serviceType: json['service_type'] as String,
      host: json['host'] as String,
      port: (json['port'] as num).toInt(),
      status: json['status'] as String,
      metadata: json['metadata'] as Map<String, dynamic>?,
      lastHeartbeat: json['last_heartbeat'] == null
          ? null
          : DateTime.parse(json['last_heartbeat'] as String),
      registeredAt: json['registered_at'] == null
          ? null
          : DateTime.parse(json['registered_at'] as String),
    );

Map<String, dynamic> _$SignageDeviceToJson(SignageDevice instance) =>
    <String, dynamic>{
      'uuid': instance.id,
      'name': instance.name,
      'device_id': instance.deviceId,
      'service_type': instance.serviceType,
      'host': instance.host,
      'port': instance.port,
      'status': instance.status,
      'metadata': instance.metadata,
      'last_heartbeat': instance.lastHeartbeat?.toIso8601String(),
      'registered_at': instance.registeredAt?.toIso8601String(),
    };

DatabaseSignageDevice _$DatabaseSignageDeviceFromJson(
        Map<String, dynamic> json) =>
    DatabaseSignageDevice(
      id: json['uuid'] as String,
      name: json['device_name'] as String,
      deviceId: json['device_id'] as String,
      hostname: json['device_hostname'] as String?,
      ipAddress: json['ip_address'] as String?,
      port: (json['port'] as num?)?.toInt(),
      location: json['location'] as String?,
      notes: json['notes'] as String?,
      isActive: json['is_active'] as bool,
      isOnline: json['is_online'] as bool,
      lastSeen: json['last_seen'] == null
          ? null
          : DateTime.parse(json['last_seen'] as String),
      lastHeartbeat: json['last_heartbeat'] == null
          ? null
          : DateTime.parse(json['last_heartbeat'] as String),
      currentVideoListId: (json['current_video_list_id'] as num?)?.toInt(),
      playbackState: json['playback_state'] as String?,
      appVersion: json['app_version'] as String?,
      screenResolution: json['screen_resolution'] as String?,
      createdAt: json['created_at'] == null
          ? null
          : DateTime.parse(json['created_at'] as String),
      updatedAt: json['updated_at'] == null
          ? null
          : DateTime.parse(json['updated_at'] as String),
    );

Map<String, dynamic> _$DatabaseSignageDeviceToJson(
        DatabaseSignageDevice instance) =>
    <String, dynamic>{
      'uuid': instance.id,
      'device_name': instance.name,
      'device_id': instance.deviceId,
      'device_hostname': instance.hostname,
      'ip_address': instance.ipAddress,
      'port': instance.port,
      'location': instance.location,
      'notes': instance.notes,
      'is_active': instance.isActive,
      'is_online': instance.isOnline,
      'last_seen': instance.lastSeen?.toIso8601String(),
      'last_heartbeat': instance.lastHeartbeat?.toIso8601String(),
      'current_video_list_id': instance.currentVideoListId,
      'playback_state': instance.playbackState,
      'app_version': instance.appVersion,
      'screen_resolution': instance.screenResolution,
      'created_at': instance.createdAt?.toIso8601String(),
      'updated_at': instance.updatedAt?.toIso8601String(),
    };

SyncRequest _$SyncRequestFromJson(Map<String, dynamic> json) => SyncRequest(
      videoListId: json['video_list_id'] as String,
      targetDevices: (json['target_devices'] as List<dynamic>)
          .map((e) => e as String)
          .toList(),
      syncMode: $enumDecodeNullable(_$SyncModeEnumMap, json['sync_mode']) ??
          SyncMode.incremental,
      forceUpdate: json['force_update'] as bool? ?? false,
      notifyOnComplete: json['notify_on_complete'] as bool? ?? true,
    );

Map<String, dynamic> _$SyncRequestToJson(SyncRequest instance) =>
    <String, dynamic>{
      'video_list_id': instance.videoListId,
      'target_devices': instance.targetDevices,
      'sync_mode': _$SyncModeEnumMap[instance.syncMode]!,
      'force_update': instance.forceUpdate,
      'notify_on_complete': instance.notifyOnComplete,
    };

const _$SyncModeEnumMap = {
  SyncMode.full: 'full',
  SyncMode.incremental: 'incremental',
};

SyncResult _$SyncResultFromJson(Map<String, dynamic> json) => SyncResult(
      syncJobId: json['sync_job_id'] as String,
      status: $enumDecode(_$SyncStatusEnumMap, json['status']),
      targetDeviceCount: (json['target_device_count'] as num).toInt(),
      estimatedCompletionAt: json['estimated_completion_at'] == null
          ? null
          : DateTime.parse(json['estimated_completion_at'] as String),
      videosSynced: (json['videos_synced'] as num?)?.toInt(),
      videosFailed: (json['videos_failed'] as num?)?.toInt(),
      syncDurationMs: (json['sync_duration_ms'] as num?)?.toInt(),
      errorMessage: json['error_message'] as String?,
    );

Map<String, dynamic> _$SyncResultToJson(SyncResult instance) =>
    <String, dynamic>{
      'sync_job_id': instance.syncJobId,
      'status': _$SyncStatusEnumMap[instance.status]!,
      'target_device_count': instance.targetDeviceCount,
      'estimated_completion_at':
          instance.estimatedCompletionAt?.toIso8601String(),
      'videos_synced': instance.videosSynced,
      'videos_failed': instance.videosFailed,
      'sync_duration_ms': instance.syncDurationMs,
      'error_message': instance.errorMessage,
    };

const _$SyncStatusEnumMap = {
  SyncStatus.pending: 'pending',
  SyncStatus.inProgress: 'in_progress',
  SyncStatus.completed: 'completed',
  SyncStatus.partial: 'partial',
  SyncStatus.failed: 'failed',
};

PlaybackControlRequest _$PlaybackControlRequestFromJson(
        Map<String, dynamic> json) =>
    PlaybackControlRequest(
      deviceIds: (json['device_ids'] as List<dynamic>)
          .map((e) => e as String)
          .toList(),
      command: $enumDecode(_$PlaybackCommandEnumMap, json['command']),
      videoListId: json['video_list_id'] as String?,
      parameters: json['parameters'] == null
          ? null
          : PlaybackParameters.fromJson(
              json['parameters'] as Map<String, dynamic>),
    );

Map<String, dynamic> _$PlaybackControlRequestToJson(
        PlaybackControlRequest instance) =>
    <String, dynamic>{
      'device_ids': instance.deviceIds,
      'command': _$PlaybackCommandEnumMap[instance.command]!,
      'video_list_id': instance.videoListId,
      'parameters': instance.parameters,
    };

const _$PlaybackCommandEnumMap = {
  PlaybackCommand.start: 'start',
  PlaybackCommand.pause: 'pause',
  PlaybackCommand.resume: 'resume',
  PlaybackCommand.stop: 'stop',
  PlaybackCommand.next: 'next',
  PlaybackCommand.previous: 'previous',
};

PlaybackParameters _$PlaybackParametersFromJson(Map<String, dynamic> json) =>
    PlaybackParameters(
      startIndex: (json['start_index'] as num?)?.toInt() ?? 0,
      volume: (json['volume'] as num?)?.toInt() ?? 80,
      speed: (json['speed'] as num?)?.toDouble() ?? 1.0,
    );

Map<String, dynamic> _$PlaybackParametersToJson(PlaybackParameters instance) =>
    <String, dynamic>{
      'start_index': instance.startIndex,
      'volume': instance.volume,
      'speed': instance.speed,
    };

PlaybackStatus _$PlaybackStatusFromJson(Map<String, dynamic> json) =>
    PlaybackStatus(
      deviceId: json['device_id'] as String,
      currentVideo: json['current_video'] == null
          ? null
          : CurrentVideoInfo.fromJson(
              json['current_video'] as Map<String, dynamic>),
      playlist: json['playlist'] == null
          ? null
          : PlaylistInfo.fromJson(json['playlist'] as Map<String, dynamic>),
      playbackState:
          $enumDecode(_$PlaybackStateEnumMap, json['playback_state']),
      recentlyPlayed: (json['recently_played'] as List<dynamic>)
          .map((e) => VideoHistoryItem.fromJson(e as Map<String, dynamic>))
          .toList(),
      upcomingVideos: (json['upcoming_videos'] as List<dynamic>)
          .map((e) => VideoListItem.fromJson(e as Map<String, dynamic>))
          .toList(),
      historyCount: (json['history_count'] as num).toInt(),
      upcomingCount: (json['upcoming_count'] as num).toInt(),
    );

Map<String, dynamic> _$PlaybackStatusToJson(PlaybackStatus instance) =>
    <String, dynamic>{
      'device_id': instance.deviceId,
      'current_video': instance.currentVideo,
      'playlist': instance.playlist,
      'playback_state': _$PlaybackStateEnumMap[instance.playbackState]!,
      'recently_played': instance.recentlyPlayed,
      'upcoming_videos': instance.upcomingVideos,
      'history_count': instance.historyCount,
      'upcoming_count': instance.upcomingCount,
    };

const _$PlaybackStateEnumMap = {
  PlaybackState.playing: 'playing',
  PlaybackState.paused: 'paused',
  PlaybackState.stopped: 'stopped',
  PlaybackState.loading: 'loading',
  PlaybackState.buffering: 'buffering',
  PlaybackState.error: 'error',
};

CurrentVideoInfo _$CurrentVideoInfoFromJson(Map<String, dynamic> json) =>
    CurrentVideoInfo(
      videoId: json['video_id'] as String,
      title: json['title'] as String,
      positionMs: (json['position_ms'] as num).toInt(),
      durationMs: (json['duration_ms'] as num).toInt(),
      progressPercent: (json['progress_percent'] as num).toDouble(),
    );

Map<String, dynamic> _$CurrentVideoInfoToJson(CurrentVideoInfo instance) =>
    <String, dynamic>{
      'video_id': instance.videoId,
      'title': instance.title,
      'position_ms': instance.positionMs,
      'duration_ms': instance.durationMs,
      'progress_percent': instance.progressPercent,
    };

PlaylistInfo _$PlaylistInfoFromJson(Map<String, dynamic> json) => PlaylistInfo(
      id: json['id'] as String,
      name: json['name'] as String,
      totalVideos: (json['total_videos'] as num).toInt(),
      currentIndex: (json['current_index'] as num).toInt(),
      loopMode: json['loop_mode'] as String?,
      videoListId: json['video_list_id'] as String?,
    );

Map<String, dynamic> _$PlaylistInfoToJson(PlaylistInfo instance) =>
    <String, dynamic>{
      'id': instance.id,
      'name': instance.name,
      'total_videos': instance.totalVideos,
      'current_index': instance.currentIndex,
      'loop_mode': instance.loopMode,
      'video_list_id': instance.videoListId,
    };

VideoHistoryItem _$VideoHistoryItemFromJson(Map<String, dynamic> json) =>
    VideoHistoryItem(
      videoId: json['video_id'] as String,
      title: json['title'] as String,
      completedAt: DateTime.parse(json['completed_at'] as String),
    );

Map<String, dynamic> _$VideoHistoryItemToJson(VideoHistoryItem instance) =>
    <String, dynamic>{
      'video_id': instance.videoId,
      'title': instance.title,
      'completed_at': instance.completedAt.toIso8601String(),
    };

VideoListsResponse _$VideoListsResponseFromJson(Map<String, dynamic> json) =>
    VideoListsResponse(
      totalCount: (json['total_count'] as num).toInt(),
      page: (json['page'] as num).toInt(),
      pageSize: (json['page_size'] as num).toInt(),
      results: (json['results'] as List<dynamic>)
          .map((e) => VideoList.fromJson(e as Map<String, dynamic>))
          .toList(),
    );

Map<String, dynamic> _$VideoListsResponseToJson(VideoListsResponse instance) =>
    <String, dynamic>{
      'total_count': instance.totalCount,
      'page': instance.page,
      'page_size': instance.pageSize,
      'results': instance.results,
    };
