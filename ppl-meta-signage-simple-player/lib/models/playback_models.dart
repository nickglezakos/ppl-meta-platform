import 'package:json_annotation/json_annotation.dart';

part 'playback_models.g.dart';

/// Playback state enum
enum PlaybackState {
  @JsonValue('stopped')
  stopped,
  @JsonValue('playing')
  playing,
  @JsonValue('paused')
  paused,
  @JsonValue('loading')
  loading,
  @JsonValue('error')
  error;

  String toJson() => name;
}

/// Playback command enum
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
  @JsonValue('seek')
  seek;

  String toJson() => name;
}

/// Current video playback information
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

/// Playlist information
@JsonSerializable()
class PlaylistInfo {
  final String id;
  final String name;
  @JsonKey(name: 'total_videos')
  final int totalVideos;
  @JsonKey(name: 'current_index')
  final int currentIndex;

  PlaylistInfo({
    required this.id,
    required this.name,
    required this.totalVideos,
    required this.currentIndex,
  });

  factory PlaylistInfo.fromJson(Map<String, dynamic> json) =>
      _$PlaylistInfoFromJson(json);

  Map<String, dynamic> toJson() => _$PlaylistInfoToJson(this);
}

/// Complete playback status
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
  final List<VideoHistoryItem> upcomingVideos;
  @JsonKey(name: 'history_count')
  final int historyCount;
  @JsonKey(name: 'upcoming_count')
  final int upcomingCount;

  PlaybackStatus({
    required this.deviceId,
    this.currentVideo,
    this.playlist,
    required this.playbackState,
    this.recentlyPlayed = const [],
    this.upcomingVideos = const [],
    this.historyCount = 0,
    this.upcomingCount = 0,
  });

  factory PlaybackStatus.fromJson(Map<String, dynamic> json) =>
      _$PlaybackStatusFromJson(json);

  Map<String, dynamic> toJson() => _$PlaybackStatusToJson(this);
}

/// Video history item
@JsonSerializable()
class VideoHistoryItem {
  @JsonKey(name: 'video_id')
  final String videoId;
  final String title;
  @JsonKey(name: 'completed_at')
  final DateTime? completedAt;
  @JsonKey(name: 'sequence_order')
  final int? sequenceOrder;

  VideoHistoryItem({
    required this.videoId,
    required this.title,
    this.completedAt,
    this.sequenceOrder,
  });

  factory VideoHistoryItem.fromJson(Map<String, dynamic> json) =>
      _$VideoHistoryItemFromJson(json);

  Map<String, dynamic> toJson() => _$VideoHistoryItemToJson(this);
}
