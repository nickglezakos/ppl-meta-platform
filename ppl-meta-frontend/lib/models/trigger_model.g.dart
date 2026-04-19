// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'trigger_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

DemographicCondition _$DemographicConditionFromJson(
        Map<String, dynamic> json) =>
    DemographicCondition(
      field: json['field'] as String,
      operator: json['operator'] as String,
      value: (json['value'] as num).toDouble(),
    );

Map<String, dynamic> _$DemographicConditionToJson(
        DemographicCondition instance) =>
    <String, dynamic>{
      'field': instance.field,
      'operator': instance.operator,
      'value': instance.value,
    };

TriggerModel _$TriggerModelFromJson(Map<String, dynamic> json) => TriggerModel(
      id: (json['id'] as num).toInt(),
      uuid: json['uuid'] as String,
      demographicConditions: (json['demographic_conditions'] as List<dynamic>)
          .map((e) => DemographicCondition.fromJson(e as Map<String, dynamic>))
          .toList(),
      timeSpan: json['time_span'] as String,
      cameraDeviceId: json['camera_device_id'] as String?,
      cameraName: json['camera_name'] as String?,
      actionUuid: json['action_uuid'] as String?,
      actionName: json['action_name'] as String?,
      actionUuids: (json['action_uuids'] as List<dynamic>?)
          ?.map((e) => e as String)
          .toList(),
      actionNames: (json['action_names'] as List<dynamic>?)
          ?.map((e) => e as String)
          .toList(),
      trackingDuration: json['tracking_duration'] as String? ?? '10 minutes',
      isActive: json['is_active'] as bool,
      cooldownSeconds: (json['cooldown_seconds'] as num?)?.toInt() ?? 60,
      lastFiredAt: json['last_fired_at'] == null
          ? null
          : DateTime.parse(json['last_fired_at'] as String),
      triggerMode: json['trigger_mode'] as String? ?? 'demographic',
      pplMatchGroupId: json['ppl_match_group_id'] as String?,
      pplMatchSimilarityThreshold:
          (json['ppl_match_similarity_threshold'] as num?)?.toDouble() ?? 0.75,
      pplMatchTopK: (json['ppl_match_top_k'] as num?)?.toInt() ?? 1,
      searchCameraDeviceIds:
          (json['search_camera_device_ids'] as List<dynamic>?)
              ?.map((e) => e as String)
              .toList(),
      searchIntervalSeconds: (json['search_interval_seconds'] as num?)?.toInt(),
      lastMatchInfo: json['last_match_info'] as Map<String, dynamic>?,
      lastMatchedAt: json['last_matched_at'] == null
          ? null
          : DateTime.parse(json['last_matched_at'] as String),
      name: json['name'] as String?,
      description: json['description'] as String?,
      createdAt: DateTime.parse(json['created_at'] as String),
      updatedAt: json['updated_at'] == null
          ? null
          : DateTime.parse(json['updated_at'] as String),
    );

Map<String, dynamic> _$TriggerModelToJson(TriggerModel instance) =>
    <String, dynamic>{
      'id': instance.id,
      'uuid': instance.uuid,
      'demographic_conditions': instance.demographicConditions,
      'time_span': instance.timeSpan,
      'camera_device_id': instance.cameraDeviceId,
      'camera_name': instance.cameraName,
      'action_uuid': instance.actionUuid,
      'action_name': instance.actionName,
      'action_uuids': instance.actionUuids,
      'action_names': instance.actionNames,
      'tracking_duration': instance.trackingDuration,
      'is_active': instance.isActive,
      'cooldown_seconds': instance.cooldownSeconds,
      'last_fired_at': instance.lastFiredAt?.toIso8601String(),
      'trigger_mode': instance.triggerMode,
      'ppl_match_group_id': instance.pplMatchGroupId,
      'ppl_match_similarity_threshold': instance.pplMatchSimilarityThreshold,
      'ppl_match_top_k': instance.pplMatchTopK,
      'search_camera_device_ids': instance.searchCameraDeviceIds,
      'search_interval_seconds': instance.searchIntervalSeconds,
      'last_match_info': instance.lastMatchInfo,
      'last_matched_at': instance.lastMatchedAt?.toIso8601String(),
      'name': instance.name,
      'description': instance.description,
      'created_at': instance.createdAt.toIso8601String(),
      'updated_at': instance.updatedAt?.toIso8601String(),
    };

TriggerCreateRequest _$TriggerCreateRequestFromJson(
        Map<String, dynamic> json) =>
    TriggerCreateRequest(
      demographicConditions: (json['demographic_conditions'] as List<dynamic>)
          .map((e) => DemographicCondition.fromJson(e as Map<String, dynamic>))
          .toList(),
      timeSpan: json['time_span'] as String,
      cameraDeviceId: json['camera_device_id'] as String?,
      cameraName: json['camera_name'] as String?,
      actionUuid: json['action_uuid'] as String?,
      actionUuids: (json['action_uuids'] as List<dynamic>?)
          ?.map((e) => e as String)
          .toList(),
      trackingDuration: json['tracking_duration'] as String? ?? '10 minutes',
      isActive: json['is_active'] as bool? ?? true,
      cooldownSeconds: (json['cooldown_seconds'] as num?)?.toInt() ?? 60,
      triggerMode: json['trigger_mode'] as String? ?? 'demographic',
      pplMatchGroupId: json['ppl_match_group_id'] as String?,
      pplMatchSimilarityThreshold:
          (json['ppl_match_similarity_threshold'] as num?)?.toDouble(),
      pplMatchTopK: (json['ppl_match_top_k'] as num?)?.toInt(),
      searchCameraDeviceIds:
          (json['search_camera_device_ids'] as List<dynamic>?)
              ?.map((e) => e as String)
              .toList(),
      searchIntervalSeconds: (json['search_interval_seconds'] as num?)?.toInt(),
      name: json['name'] as String?,
      description: json['description'] as String?,
    );

Map<String, dynamic> _$TriggerCreateRequestToJson(
        TriggerCreateRequest instance) =>
    <String, dynamic>{
      'demographic_conditions': instance.demographicConditions,
      'time_span': instance.timeSpan,
      if (instance.cameraDeviceId case final value?) 'camera_device_id': value,
      if (instance.cameraName case final value?) 'camera_name': value,
      if (instance.actionUuid case final value?) 'action_uuid': value,
      if (instance.actionUuids case final value?) 'action_uuids': value,
      'tracking_duration': instance.trackingDuration,
      'is_active': instance.isActive,
      'cooldown_seconds': instance.cooldownSeconds,
      'trigger_mode': instance.triggerMode,
      if (instance.pplMatchGroupId case final value?)
        'ppl_match_group_id': value,
      if (instance.pplMatchSimilarityThreshold case final value?)
        'ppl_match_similarity_threshold': value,
      if (instance.pplMatchTopK case final value?) 'ppl_match_top_k': value,
      if (instance.searchCameraDeviceIds case final value?)
        'search_camera_device_ids': value,
      if (instance.searchIntervalSeconds case final value?)
        'search_interval_seconds': value,
      if (instance.name case final value?) 'name': value,
      if (instance.description case final value?) 'description': value,
    };

TriggerListResponse _$TriggerListResponseFromJson(Map<String, dynamic> json) =>
    TriggerListResponse(
      triggers: (json['triggers'] as List<dynamic>)
          .map((e) => TriggerModel.fromJson(e as Map<String, dynamic>))
          .toList(),
      total: (json['total'] as num).toInt(),
      page: (json['page'] as num).toInt(),
      pageSize: (json['page_size'] as num).toInt(),
      totalPages: (json['total_pages'] as num).toInt(),
    );

Map<String, dynamic> _$TriggerListResponseToJson(
        TriggerListResponse instance) =>
    <String, dynamic>{
      'triggers': instance.triggers,
      'total': instance.total,
      'page': instance.page,
      'page_size': instance.pageSize,
      'total_pages': instance.totalPages,
    };
