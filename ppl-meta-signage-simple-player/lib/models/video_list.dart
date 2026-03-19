import 'package:json_annotation/json_annotation.dart';

part 'video_list.g.dart';

/// Represents a video playlist
@JsonSerializable()
class VideoList {
  final String id;
  final String name;
  final String? description;
  @JsonKey(name: 'source_list_id')
  final String sourceListId;
  @JsonKey(name: 'last_synced_at')
  final DateTime? lastSyncedAt;
  @JsonKey(name: 'sync_version')
  final int syncVersion;
  @JsonKey(name: 'is_active')
  final bool isActive;
  @JsonKey(name: 'loop_mode')
  final LoopMode loopMode;
  @JsonKey(name: 'transition_duration_ms')
  final int transitionDurationMs;
  final List<VideoItem> videos;

  VideoList({
    required this.id,
    required this.name,
    this.description,
    required this.sourceListId,
    this.lastSyncedAt,
    this.syncVersion = 1,
    this.isActive = true,
    this.loopMode = LoopMode.continuous,
    this.transitionDurationMs = 0,
    this.videos = const [],
  });

  factory VideoList.fromJson(Map<String, dynamic> json) =>
      _$VideoListFromJson(json);

  Map<String, dynamic> toJson() => _$VideoListToJson(this);

  VideoList copyWith({
    String? id,
    String? name,
    String? description,
    String? sourceListId,
    DateTime? lastSyncedAt,
    int? syncVersion,
    bool? isActive,
    LoopMode? loopMode,
    int? transitionDurationMs,
    List<VideoItem>? videos,
  }) {
    return VideoList(
      id: id ?? this.id,
      name: name ?? this.name,
      description: description ?? this.description,
      sourceListId: sourceListId ?? this.sourceListId,
      lastSyncedAt: lastSyncedAt ?? this.lastSyncedAt,
      syncVersion: syncVersion ?? this.syncVersion,
      isActive: isActive ?? this.isActive,
      loopMode: loopMode ?? this.loopMode,
      transitionDurationMs: transitionDurationMs ?? this.transitionDurationMs,
      videos: videos ?? this.videos,
    );
  }
}

/// Represents a video item in a playlist
@JsonSerializable()
class VideoItem {
  final String id;
  @JsonKey(name: 'video_id')
  final String videoId;
  final String title;
  final String url;
  @JsonKey(name: 'sequence_order')
  final int sequenceOrder;
  @JsonKey(name: 'duration_ms')
  final int durationMs;
  final Map<String, dynamic>? metadata;

  VideoItem({
    required this.id,
    required this.videoId,
    required this.title,
    required this.url,
    required this.sequenceOrder,
    required this.durationMs,
    this.metadata,
  });

  factory VideoItem.fromJson(Map<String, dynamic> json) =>
      _$VideoItemFromJson(json);

  Map<String, dynamic> toJson() => _$VideoItemToJson(this);

  Duration get duration => Duration(milliseconds: durationMs);
}

/// Loop mode for playlist playback
enum LoopMode {
  @JsonValue('continuous')
  continuous,
  @JsonValue('once')
  once,
  @JsonValue('single')
  single;

  String toJson() => name;
}
