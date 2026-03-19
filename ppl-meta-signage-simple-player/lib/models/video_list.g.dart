// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'video_list.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

VideoList _$VideoListFromJson(Map<String, dynamic> json) => VideoList(
  id: json['id'] as String,
  name: json['name'] as String,
  description: json['description'] as String?,
  sourceListId: json['source_list_id'] as String,
  lastSyncedAt: json['last_synced_at'] == null
      ? null
      : DateTime.parse(json['last_synced_at'] as String),
  syncVersion: (json['sync_version'] as num?)?.toInt() ?? 1,
  isActive: json['is_active'] as bool? ?? true,
  loopMode:
      $enumDecodeNullable(_$LoopModeEnumMap, json['loop_mode']) ??
      LoopMode.continuous,
  transitionDurationMs: (json['transition_duration_ms'] as num?)?.toInt() ?? 0,
  videos:
      (json['videos'] as List<dynamic>?)
          ?.map((e) => VideoItem.fromJson(e as Map<String, dynamic>))
          .toList() ??
      const [],
);

Map<String, dynamic> _$VideoListToJson(VideoList instance) => <String, dynamic>{
  'id': instance.id,
  'name': instance.name,
  'description': instance.description,
  'source_list_id': instance.sourceListId,
  'last_synced_at': instance.lastSyncedAt?.toIso8601String(),
  'sync_version': instance.syncVersion,
  'is_active': instance.isActive,
  'loop_mode': instance.loopMode,
  'transition_duration_ms': instance.transitionDurationMs,
  'videos': instance.videos,
};

const _$LoopModeEnumMap = {
  LoopMode.continuous: 'continuous',
  LoopMode.once: 'once',
  LoopMode.single: 'single',
};

VideoItem _$VideoItemFromJson(Map<String, dynamic> json) => VideoItem(
  id: json['id'] as String,
  videoId: json['video_id'] as String,
  title: json['title'] as String,
  url: json['url'] as String,
  sequenceOrder: (json['sequence_order'] as num).toInt(),
  durationMs: (json['duration_ms'] as num).toInt(),
  metadata: json['metadata'] as Map<String, dynamic>?,
);

Map<String, dynamic> _$VideoItemToJson(VideoItem instance) => <String, dynamic>{
  'id': instance.id,
  'video_id': instance.videoId,
  'title': instance.title,
  'url': instance.url,
  'sequence_order': instance.sequenceOrder,
  'duration_ms': instance.durationMs,
  'metadata': instance.metadata,
};
