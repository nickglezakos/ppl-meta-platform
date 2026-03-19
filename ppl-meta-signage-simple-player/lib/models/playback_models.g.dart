// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'playback_models.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

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
);

Map<String, dynamic> _$PlaylistInfoToJson(PlaylistInfo instance) =>
    <String, dynamic>{
      'id': instance.id,
      'name': instance.name,
      'total_videos': instance.totalVideos,
      'current_index': instance.currentIndex,
    };

PlaybackStatus _$PlaybackStatusFromJson(Map<String, dynamic> json) =>
    PlaybackStatus(
      deviceId: json['device_id'] as String,
      currentVideo: json['current_video'] == null
          ? null
          : CurrentVideoInfo.fromJson(
              json['current_video'] as Map<String, dynamic>,
            ),
      playlist: json['playlist'] == null
          ? null
          : PlaylistInfo.fromJson(json['playlist'] as Map<String, dynamic>),
      playbackState: $enumDecode(
        _$PlaybackStateEnumMap,
        json['playback_state'],
      ),
      recentlyPlayed:
          (json['recently_played'] as List<dynamic>?)
              ?.map((e) => VideoHistoryItem.fromJson(e as Map<String, dynamic>))
              .toList() ??
          const [],
      upcomingVideos:
          (json['upcoming_videos'] as List<dynamic>?)
              ?.map((e) => VideoHistoryItem.fromJson(e as Map<String, dynamic>))
              .toList() ??
          const [],
      historyCount: (json['history_count'] as num?)?.toInt() ?? 0,
      upcomingCount: (json['upcoming_count'] as num?)?.toInt() ?? 0,
    );

Map<String, dynamic> _$PlaybackStatusToJson(PlaybackStatus instance) =>
    <String, dynamic>{
      'device_id': instance.deviceId,
      'current_video': instance.currentVideo,
      'playlist': instance.playlist,
      'playback_state': instance.playbackState,
      'recently_played': instance.recentlyPlayed,
      'upcoming_videos': instance.upcomingVideos,
      'history_count': instance.historyCount,
      'upcoming_count': instance.upcomingCount,
    };

const _$PlaybackStateEnumMap = {
  PlaybackState.stopped: 'stopped',
  PlaybackState.playing: 'playing',
  PlaybackState.paused: 'paused',
  PlaybackState.loading: 'loading',
  PlaybackState.error: 'error',
};

VideoHistoryItem _$VideoHistoryItemFromJson(Map<String, dynamic> json) =>
    VideoHistoryItem(
      videoId: json['video_id'] as String,
      title: json['title'] as String,
      completedAt: json['completed_at'] == null
          ? null
          : DateTime.parse(json['completed_at'] as String),
      sequenceOrder: (json['sequence_order'] as num?)?.toInt(),
    );

Map<String, dynamic> _$VideoHistoryItemToJson(VideoHistoryItem instance) =>
    <String, dynamic>{
      'video_id': instance.videoId,
      'title': instance.title,
      'completed_at': instance.completedAt?.toIso8601String(),
      'sequence_order': instance.sequenceOrder,
    };
