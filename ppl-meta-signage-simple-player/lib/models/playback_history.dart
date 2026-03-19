import 'package:json_annotation/json_annotation.dart';

part 'playback_history.g.dart';

/// Playback history entry
@JsonSerializable()
class PlaybackHistoryEntry {
  final String id;
  @JsonKey(name: 'video_id')
  final String videoId;
  @JsonKey(name: 'video_title')
  final String videoTitle;
  @JsonKey(name: 'playlist_id')
  final String playlistId;
  @JsonKey(name: 'playlist_name')
  final String? playlistName;
  @JsonKey(name: 'started_at')
  final DateTime startedAt;
  @JsonKey(name: 'completed_at')
  final DateTime? completedAt;
  @JsonKey(name: 'duration_played_ms')
  final int durationPlayedMs;
  @JsonKey(name: 'completion_percent')
  final double completionPercent;
  @JsonKey(name: 'playback_quality')
  final String? playbackQuality;
  final int interruptions;
  @JsonKey(name: 'error_occurred')
  final bool errorOccurred;
  @JsonKey(name: 'error_message')
  final String? errorMessage;
  @JsonKey(name: 'device_id')
  final String deviceId;
  @JsonKey(name: 'created_at')
  final DateTime createdAt;

  PlaybackHistoryEntry({
    required this.id,
    required this.videoId,
    required this.videoTitle,
    required this.playlistId,
    this.playlistName,
    required this.startedAt,
    this.completedAt,
    this.durationPlayedMs = 0,
    this.completionPercent = 0.0,
    this.playbackQuality,
    this.interruptions = 0,
    this.errorOccurred = false,
    this.errorMessage,
    required this.deviceId,
    required this.createdAt,
  });

  factory PlaybackHistoryEntry.fromJson(Map<String, dynamic> json) =>
      _$PlaybackHistoryEntryFromJson(json);

  Map<String, dynamic> toJson() => _$PlaybackHistoryEntryToJson(this);

  Duration get durationPlayed => Duration(milliseconds: durationPlayedMs);

  bool get isCompleted => completedAt != null;
}

/// History query result
@JsonSerializable()
class HistoryQueryResult {
  @JsonKey(name: 'total_count')
  final int totalCount;
  final int page;
  @JsonKey(name: 'page_size')
  final int pageSize;
  final List<PlaybackHistoryEntry> results;
  final PlaybackSummary? summary;

  HistoryQueryResult({
    required this.totalCount,
    required this.page,
    required this.pageSize,
    required this.results,
    this.summary,
  });

  int get totalPages => (totalCount / pageSize).ceil();

  factory HistoryQueryResult.fromJson(Map<String, dynamic> json) =>
      _$HistoryQueryResultFromJson(json);

  Map<String, dynamic> toJson() => _$HistoryQueryResultToJson(this);
}

/// Playback summary statistics
@JsonSerializable()
class PlaybackSummary {
  @JsonKey(name: 'total_playback_time_ms')
  final int totalPlaybackTimeMs;
  @JsonKey(name: 'unique_videos_played')
  final int uniqueVideosPlayed;
  @JsonKey(name: 'average_completion_rate')
  final double averageCompletionRate;
  @JsonKey(name: 'most_played_video')
  final MostPlayedVideo? mostPlayedVideo;

  PlaybackSummary({
    required this.totalPlaybackTimeMs,
    required this.uniqueVideosPlayed,
    required this.averageCompletionRate,
    this.mostPlayedVideo,
  });

  Duration get totalPlaybackTime => Duration(milliseconds: totalPlaybackTimeMs);

  factory PlaybackSummary.fromJson(Map<String, dynamic> json) =>
      _$PlaybackSummaryFromJson(json);

  Map<String, dynamic> toJson() => _$PlaybackSummaryToJson(this);
}

/// Most played video information
@JsonSerializable()
class MostPlayedVideo {
  @JsonKey(name: 'video_id')
  final String videoId;
  @JsonKey(name: 'play_count')
  final int playCount;
  final String? title;

  MostPlayedVideo({
    required this.videoId,
    required this.playCount,
    this.title,
  });

  factory MostPlayedVideo.fromJson(Map<String, dynamic> json) =>
      _$MostPlayedVideoFromJson(json);

  Map<String, dynamic> toJson() => _$MostPlayedVideoToJson(this);
}
