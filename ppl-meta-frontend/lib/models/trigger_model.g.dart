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
      pplMatchGroupIds: (json['ppl_match_group_ids'] as List<dynamic>?)
          ?.map((e) => e as String)
          .toList(),
      cameraDeviceIds: (json['camera_device_ids'] as List<dynamic>?)
          ?.map((e) => e as String)
          .toList(),
      pplMatchSimilarityThreshold:
          (json['ppl_match_similarity_threshold'] as num?)?.toDouble() ?? 0.75,
      pplMatchTopK: (json['ppl_match_top_k'] as num?)?.toInt() ?? 1,
      pplMatchNegate: json['ppl_match_negate'] as bool? ?? false,
      bodyPostureTarget: json['body_posture_target'] as String?,
      bodyPostureWindowSize:
          (json['body_posture_window_size'] as num?)?.toInt(),
      bodyPostureMinMatches:
          (json['body_posture_min_matches'] as num?)?.toInt(),
      bodyPostureMinConfidence:
          (json['body_posture_min_confidence'] as num?)?.toDouble(),
      bodyPostureIouThreshold:
          (json['body_posture_iou_threshold'] as num?)?.toDouble(),
      velocityScope: json['velocity_scope'] as String?,
      velocityBand: json['velocity_band'] as String?,
      leftObjectClassAllowlist:
          (json['left_object_class_allowlist'] as List<dynamic>?)
              ?.map((e) => e as String)
              .toList(),
      leftObjectRoi: (json['left_object_roi'] as List<dynamic>?)
          ?.map((e) => (e as List<dynamic>).map((v) => (v as num).toDouble()).toList())
          .toList(),
      leftObjectTStableSeconds:
          (json['left_object_t_stable_seconds'] as num?)?.toInt(),
      leftObjectTAbandonSeconds:
          (json['left_object_t_abandon_seconds'] as num?)?.toInt(),
      leftObjectMinBoxAreaPx:
          (json['left_object_min_box_area_px'] as num?)?.toInt(),
      leftObjectRequirePersonLeft:
          json['left_object_require_person_left'] as bool?,
      leftObjectProximityPx:
          (json['left_object_proximity_px'] as num?)?.toDouble(),
      leftObjectIouThreshold:
          (json['left_object_iou_threshold'] as num?)?.toDouble(),
      vehicleClassAllowlist:
          (json['vehicle_class_allowlist'] as List<dynamic>?)
              ?.map((e) => e as String)
              .toList(),
      vehicleRoi: (json['vehicle_roi'] as List<dynamic>?)
          ?.map((e) => (e as List<dynamic>).map((v) => (v as num).toDouble()).toList())
          .toList(),
      vehicleTStableSeconds:
          (json['vehicle_t_stable_seconds'] as num?)?.toInt(),
      vehicleMinBoxAreaPx:
          (json['vehicle_min_box_area_px'] as num?)?.toInt(),
      vehiclePlateOcrEnabled: json['vehicle_plate_ocr_enabled'] as bool?,
      vehiclePlateOcrEveryNCycles:
          (json['vehicle_plate_ocr_every_n_cycles'] as num?)?.toInt(),
      vehicleIouThreshold:
          (json['vehicle_iou_threshold'] as num?)?.toDouble(),
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
      'ppl_match_group_ids': instance.pplMatchGroupIds,
      'camera_device_ids': instance.cameraDeviceIds,
      'ppl_match_similarity_threshold': instance.pplMatchSimilarityThreshold,
      'ppl_match_top_k': instance.pplMatchTopK,
      'ppl_match_negate': instance.pplMatchNegate,
      'body_posture_target': instance.bodyPostureTarget,
      'body_posture_window_size': instance.bodyPostureWindowSize,
      'body_posture_min_matches': instance.bodyPostureMinMatches,
      'body_posture_min_confidence': instance.bodyPostureMinConfidence,
      'body_posture_iou_threshold': instance.bodyPostureIouThreshold,
      'velocity_scope': instance.velocityScope,
      'velocity_band': instance.velocityBand,
      'left_object_class_allowlist': instance.leftObjectClassAllowlist,
      'left_object_roi': instance.leftObjectRoi,
      'left_object_t_stable_seconds': instance.leftObjectTStableSeconds,
      'left_object_t_abandon_seconds': instance.leftObjectTAbandonSeconds,
      'left_object_min_box_area_px': instance.leftObjectMinBoxAreaPx,
      'left_object_require_person_left': instance.leftObjectRequirePersonLeft,
      'left_object_proximity_px': instance.leftObjectProximityPx,
      'left_object_iou_threshold': instance.leftObjectIouThreshold,
      'vehicle_class_allowlist': instance.vehicleClassAllowlist,
      'vehicle_roi': instance.vehicleRoi,
      'vehicle_t_stable_seconds': instance.vehicleTStableSeconds,
      'vehicle_min_box_area_px': instance.vehicleMinBoxAreaPx,
      'vehicle_plate_ocr_enabled': instance.vehiclePlateOcrEnabled,
      'vehicle_plate_ocr_every_n_cycles': instance.vehiclePlateOcrEveryNCycles,
      'vehicle_iou_threshold': instance.vehicleIouThreshold,
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
      pplMatchGroupIds: (json['ppl_match_group_ids'] as List<dynamic>?)
          ?.map((e) => e as String)
          .toList(),
      cameraDeviceIds: (json['camera_device_ids'] as List<dynamic>?)
          ?.map((e) => e as String)
          .toList(),
      pplMatchSimilarityThreshold:
          (json['ppl_match_similarity_threshold'] as num?)?.toDouble(),
      pplMatchTopK: (json['ppl_match_top_k'] as num?)?.toInt(),
      pplMatchNegate: json['ppl_match_negate'] as bool?,
      bodyPostureTarget: json['body_posture_target'] as String?,
      bodyPostureWindowSize:
          (json['body_posture_window_size'] as num?)?.toInt(),
      bodyPostureMinMatches:
          (json['body_posture_min_matches'] as num?)?.toInt(),
      bodyPostureMinConfidence:
          (json['body_posture_min_confidence'] as num?)?.toDouble(),
      bodyPostureIouThreshold:
          (json['body_posture_iou_threshold'] as num?)?.toDouble(),
      velocityScope: json['velocity_scope'] as String?,
      velocityBand: json['velocity_band'] as String?,
      leftObjectClassAllowlist:
          (json['left_object_class_allowlist'] as List<dynamic>?)
              ?.map((e) => e as String)
              .toList(),
      leftObjectRoi: (json['left_object_roi'] as List<dynamic>?)
          ?.map((e) => (e as List<dynamic>).map((v) => (v as num).toDouble()).toList())
          .toList(),
      leftObjectTStableSeconds:
          (json['left_object_t_stable_seconds'] as num?)?.toInt(),
      leftObjectTAbandonSeconds:
          (json['left_object_t_abandon_seconds'] as num?)?.toInt(),
      leftObjectMinBoxAreaPx:
          (json['left_object_min_box_area_px'] as num?)?.toInt(),
      leftObjectRequirePersonLeft:
          json['left_object_require_person_left'] as bool?,
      leftObjectProximityPx:
          (json['left_object_proximity_px'] as num?)?.toDouble(),
      leftObjectIouThreshold:
          (json['left_object_iou_threshold'] as num?)?.toDouble(),
      vehicleClassAllowlist:
          (json['vehicle_class_allowlist'] as List<dynamic>?)
              ?.map((e) => e as String)
              .toList(),
      vehicleRoi: (json['vehicle_roi'] as List<dynamic>?)
          ?.map((e) => (e as List<dynamic>).map((v) => (v as num).toDouble()).toList())
          .toList(),
      vehicleTStableSeconds:
          (json['vehicle_t_stable_seconds'] as num?)?.toInt(),
      vehicleMinBoxAreaPx:
          (json['vehicle_min_box_area_px'] as num?)?.toInt(),
      vehiclePlateOcrEnabled: json['vehicle_plate_ocr_enabled'] as bool?,
      vehiclePlateOcrEveryNCycles:
          (json['vehicle_plate_ocr_every_n_cycles'] as num?)?.toInt(),
      vehicleIouThreshold:
          (json['vehicle_iou_threshold'] as num?)?.toDouble(),
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
      if (instance.pplMatchGroupIds case final value?)
        'ppl_match_group_ids': value,
      if (instance.cameraDeviceIds case final value?)
        'camera_device_ids': value,
      if (instance.pplMatchSimilarityThreshold case final value?)
        'ppl_match_similarity_threshold': value,
      if (instance.pplMatchTopK case final value?) 'ppl_match_top_k': value,
      if (instance.pplMatchNegate case final value?) 'ppl_match_negate': value,
      if (instance.bodyPostureTarget case final value?)
        'body_posture_target': value,
      if (instance.bodyPostureWindowSize case final value?)
        'body_posture_window_size': value,
      if (instance.bodyPostureMinMatches case final value?)
        'body_posture_min_matches': value,
      if (instance.bodyPostureMinConfidence case final value?)
        'body_posture_min_confidence': value,
      if (instance.bodyPostureIouThreshold case final value?)
        'body_posture_iou_threshold': value,
      if (instance.velocityScope case final value?) 'velocity_scope': value,
      if (instance.velocityBand case final value?) 'velocity_band': value,
      if (instance.leftObjectClassAllowlist case final value?)
        'left_object_class_allowlist': value,
      if (instance.leftObjectRoi case final value?) 'left_object_roi': value,
      if (instance.leftObjectTStableSeconds case final value?)
        'left_object_t_stable_seconds': value,
      if (instance.leftObjectTAbandonSeconds case final value?)
        'left_object_t_abandon_seconds': value,
      if (instance.leftObjectMinBoxAreaPx case final value?)
        'left_object_min_box_area_px': value,
      if (instance.leftObjectRequirePersonLeft case final value?)
        'left_object_require_person_left': value,
      if (instance.leftObjectProximityPx case final value?)
        'left_object_proximity_px': value,
      if (instance.leftObjectIouThreshold case final value?)
        'left_object_iou_threshold': value,
      if (instance.vehicleClassAllowlist case final value?)
        'vehicle_class_allowlist': value,
      if (instance.vehicleRoi case final value?) 'vehicle_roi': value,
      if (instance.vehicleTStableSeconds case final value?)
        'vehicle_t_stable_seconds': value,
      if (instance.vehicleMinBoxAreaPx case final value?)
        'vehicle_min_box_area_px': value,
      if (instance.vehiclePlateOcrEnabled case final value?)
        'vehicle_plate_ocr_enabled': value,
      if (instance.vehiclePlateOcrEveryNCycles case final value?)
        'vehicle_plate_ocr_every_n_cycles': value,
      if (instance.vehicleIouThreshold case final value?)
        'vehicle_iou_threshold': value,
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
