// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'playback_history.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

PlaybackHistoryEntry _$PlaybackHistoryEntryFromJson(
  Map<String, dynamic> json,
) => PlaybackHistoryEntry(
  id: json['id'] as String,
  videoId: json['video_id'] as String,
  videoTitle: json['video_title'] as String,
  playlistId: json['playlist_id'] as String,
  playlistName: json['playlist_name'] as String?,
  startedAt: DateTime.parse(json['started_at'] as String),
  completedAt: json['completed_at'] == null
      ? null
      : DateTime.parse(json['completed_at'] as String),
  durationPlayedMs: (json['duration_played_ms'] as num?)?.toInt() ?? 0,
  completionPercent: (json['completion_percent'] as num?)?.toDouble() ?? 0.0,
  playbackQuality: json['playback_quality'] as String?,
  interruptions: (json['interruptions'] as num?)?.toInt() ?? 0,
  errorOccurred: json['error_occurred'] as bool? ?? false,
  errorMessage: json['error_message'] as String?,
  deviceId: json['device_id'] as String,
  createdAt: DateTime.parse(json['created_at'] as String),
);

Map<String, dynamic> _$PlaybackHistoryEntryToJson(
  PlaybackHistoryEntry instance,
) => <String, dynamic>{
  'id': instance.id,
  'video_id': instance.videoId,
  'video_title': instance.videoTitle,
  'playlist_id': instance.playlistId,
  'playlist_name': instance.playlistName,
  'started_at': instance.startedAt.toIso8601String(),
  'completed_at': instance.completedAt?.toIso8601String(),
  'duration_played_ms': instance.durationPlayedMs,
  'completion_percent': instance.completionPercent,
  'playback_quality': instance.playbackQuality,
  'interruptions': instance.interruptions,
  'error_occurred': instance.errorOccurred,
  'error_message': instance.errorMessage,
  'device_id': instance.deviceId,
  'created_at': instance.createdAt.toIso8601String(),
};

HistoryQueryResult _$HistoryQueryResultFromJson(Map<String, dynamic> json) =>
    HistoryQueryResult(
      totalCount: (json['total_count'] as num).toInt(),
      page: (json['page'] as num).toInt(),
      pageSize: (json['page_size'] as num).toInt(),
      results: (json['results'] as List<dynamic>)
          .map((e) => PlaybackHistoryEntry.fromJson(e as Map<String, dynamic>))
          .toList(),
      summary: json['summary'] == null
          ? null
          : PlaybackSummary.fromJson(json['summary'] as Map<String, dynamic>),
    );

Map<String, dynamic> _$HistoryQueryResultToJson(HistoryQueryResult instance) =>
    <String, dynamic>{
      'total_count': instance.totalCount,
      'page': instance.page,
      'page_size': instance.pageSize,
      'results': instance.results,
      'summary': instance.summary,
    };

PlaybackSummary _$PlaybackSummaryFromJson(Map<String, dynamic> json) =>
    PlaybackSummary(
      totalPlaybackTimeMs: (json['total_playback_time_ms'] as num).toInt(),
      uniqueVideosPlayed: (json['unique_videos_played'] as num).toInt(),
      averageCompletionRate: (json['average_completion_rate'] as num)
          .toDouble(),
      mostPlayedVideo: json['most_played_video'] == null
          ? null
          : MostPlayedVideo.fromJson(
              json['most_played_video'] as Map<String, dynamic>,
            ),
    );

Map<String, dynamic> _$PlaybackSummaryToJson(PlaybackSummary instance) =>
    <String, dynamic>{
      'total_playback_time_ms': instance.totalPlaybackTimeMs,
      'unique_videos_played': instance.uniqueVideosPlayed,
      'average_completion_rate': instance.averageCompletionRate,
      'most_played_video': instance.mostPlayedVideo,
    };

MostPlayedVideo _$MostPlayedVideoFromJson(Map<String, dynamic> json) =>
    MostPlayedVideo(
      videoId: json['video_id'] as String,
      playCount: (json['play_count'] as num).toInt(),
      title: json['title'] as String?,
    );

Map<String, dynamic> _$MostPlayedVideoToJson(MostPlayedVideo instance) =>
    <String, dynamic>{
      'video_id': instance.videoId,
      'play_count': instance.playCount,
      'title': instance.title,
    };
