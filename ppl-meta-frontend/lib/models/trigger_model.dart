import 'dart:convert';

import 'package:json_annotation/json_annotation.dart';

part 'trigger_model.g.dart';

/// Web-safe JSON normalization for TriggerModel (dart2js Map casts).
Map<String, dynamic> _normalizeTriggerJson(Map<String, dynamic> json) {
  final out = Map<String, dynamic>.from(json);

  Map<String, dynamic>? asStringKeyedMap(dynamic value) {
    if (value == null) return null;
    if (value is Map<String, dynamic>) return value;
    if (value is Map) {
      return value.map((k, v) => MapEntry(k.toString(), v));
    }
    return null;
  }

  List<dynamic>? asList(dynamic value) {
    if (value == null) return null;
    if (value is List) return value;
    if (value is String && value.trim().isNotEmpty) {
      try {
        final parsed = jsonDecode(value);
        if (parsed is List) return parsed;
      } catch (_) {}
    }
    return null;
  }

  final lastMatch = asStringKeyedMap(out['last_match_info']);
  if (out.containsKey('last_match_info')) {
    out['last_match_info'] = lastMatch;
  }

  for (final key in const [
    'demographic_conditions',
    'behavioural_conditions',
    'motion_conditions',
    'action_uuids',
    'action_names',
    'ppl_match_group_ids',
    'camera_device_ids',
    'search_camera_device_ids',
    'left_object_class_allowlist',
    'vehicle_class_allowlist',
    'motion_roi',
    'left_object_roi',
    'vehicle_roi',
  ]) {
    if (!out.containsKey(key)) continue;
    final list = asList(out[key]);
    if (list != null) {
      out[key] = list.map((e) {
        if (e is Map && e is! Map<String, dynamic>) {
          return e.map((k, v) => MapEntry(k.toString(), v));
        }
        return e;
      }).toList();
    } else if (out[key] is String) {
      // Empty / invalid JSON string → null so generated cast does not throw.
      out[key] = null;
    }
  }

  return out;
}

/// Demographic condition for trigger evaluation
@JsonSerializable()
class DemographicCondition {
  final String field;
  final String operator;
  final double value;

  DemographicCondition({
    required this.field,
    required this.operator,
    required this.value,
  });

  factory DemographicCondition.fromJson(Map<String, dynamic> json) =>
      _$DemographicConditionFromJson(json);

  Map<String, dynamic> toJson() => _$DemographicConditionToJson(this);
}

/// Motion condition for motion trigger evaluation (speed / class / ROI).
@JsonSerializable()
class MotionCondition {
  final String field;
  final String operator;
  /// String for speed_band / single value; List for multi-select (in).
  final dynamic value;

  MotionCondition({
    required this.field,
    required this.operator,
    required this.value,
  });

  factory MotionCondition.fromJson(Map<String, dynamic> json) =>
      _$MotionConditionFromJson(json);

  Map<String, dynamic> toJson() => _$MotionConditionToJson(this);
}

@JsonSerializable()
class TriggerModel {
  final int id;
  final String uuid;
  
  @JsonKey(name: 'demographic_conditions')
  final List<DemographicCondition> demographicConditions;
  
  @JsonKey(name: 'time_span')
  final String timeSpan;
  
  @JsonKey(name: 'camera_device_id')
  final String? cameraDeviceId;
  
  @JsonKey(name: 'camera_name')
  final String? cameraName;
  
  @JsonKey(name: 'action_uuid')
  final String? actionUuid;
  
  @JsonKey(name: 'action_name')
  final String? actionName;

  @JsonKey(name: 'action_uuids')
  final List<String>? actionUuids;

  @JsonKey(name: 'action_names')
  final List<String>? actionNames;
  
  @JsonKey(name: 'tracking_duration')
  final String trackingDuration;
  
  @JsonKey(name: 'is_active')
  final bool isActive;
  
  @JsonKey(name: 'cooldown_seconds')
  final int cooldownSeconds;
  
  @JsonKey(name: 'last_fired_at')
  final DateTime? lastFiredAt;

  @JsonKey(name: 'trigger_mode')
  final String triggerMode;

  @JsonKey(name: 'behavioural_lookback_flushes')
  final int? behaviouralLookbackFlushes;

  @JsonKey(name: 'behavioural_conditions')
  final List<DemographicCondition>? behaviouralConditions;

  @JsonKey(name: 'behavioural_condition_logic')
  final String? behaviouralConditionLogic;

  @JsonKey(name: 'ppl_match_group_id')
  final String? pplMatchGroupId;

  @JsonKey(name: 'ppl_match_group_ids')
  final List<String>? pplMatchGroupIds;

  @JsonKey(name: 'camera_device_ids')
  final List<String>? cameraDeviceIds;

  @JsonKey(name: 'ppl_match_similarity_threshold')
  final double pplMatchSimilarityThreshold;

  @JsonKey(name: 'ppl_match_top_k')
  final int pplMatchTopK;

  @JsonKey(name: 'ppl_match_negate')
  final bool pplMatchNegate;

  @JsonKey(name: 'body_posture_target')
  final String? bodyPostureTarget;

  @JsonKey(name: 'body_posture_window_size')
  final int? bodyPostureWindowSize;

  @JsonKey(name: 'body_posture_min_matches')
  final int? bodyPostureMinMatches;

  @JsonKey(name: 'body_posture_min_confidence')
  final double? bodyPostureMinConfidence;

  @JsonKey(name: 'body_posture_iou_threshold')
  final double? bodyPostureIouThreshold;

  @JsonKey(name: 'velocity_scope')
  final String? velocityScope;

  @JsonKey(name: 'velocity_band')
  final String? velocityBand;

  @JsonKey(name: 'motion_scope')
  final String? motionScope;

  @JsonKey(name: 'motion_conditions')
  final List<MotionCondition>? motionConditions;

  @JsonKey(name: 'motion_condition_logic')
  final String? motionConditionLogic;

  @JsonKey(name: 'motion_roi')
  final List<List<double>>? motionRoi;

  @JsonKey(name: 'left_object_class_allowlist')
  final List<String>? leftObjectClassAllowlist;

  @JsonKey(name: 'left_object_roi')
  final List<List<double>>? leftObjectRoi;

  @JsonKey(name: 'left_object_t_stable_seconds')
  final int? leftObjectTStableSeconds;

  @JsonKey(name: 'left_object_t_abandon_seconds')
  final int? leftObjectTAbandonSeconds;

  @JsonKey(name: 'left_object_min_box_area_px')
  final int? leftObjectMinBoxAreaPx;

  @JsonKey(name: 'left_object_require_person_left')
  final bool? leftObjectRequirePersonLeft;

  @JsonKey(name: 'left_object_proximity_px')
  final double? leftObjectProximityPx;

  @JsonKey(name: 'left_object_iou_threshold')
  final double? leftObjectIouThreshold;

  @JsonKey(name: 'vehicle_class_allowlist')
  final List<String>? vehicleClassAllowlist;

  @JsonKey(name: 'vehicle_roi')
  final List<List<double>>? vehicleRoi;

  @JsonKey(name: 'vehicle_t_stable_seconds')
  final int? vehicleTStableSeconds;

  @JsonKey(name: 'vehicle_min_box_area_px')
  final int? vehicleMinBoxAreaPx;

  @JsonKey(name: 'vehicle_plate_ocr_enabled')
  final bool? vehiclePlateOcrEnabled;

  @JsonKey(name: 'vehicle_plate_ocr_every_n_cycles')
  final int? vehiclePlateOcrEveryNCycles;

  @JsonKey(name: 'vehicle_iou_threshold')
  final double? vehicleIouThreshold;

  @JsonKey(name: 'search_camera_device_ids')
  final List<String>? searchCameraDeviceIds;

  @JsonKey(name: 'search_interval_seconds')
  final int? searchIntervalSeconds;

  @JsonKey(name: 'last_match_info')
  final Map<String, dynamic>? lastMatchInfo;

  @JsonKey(name: 'last_matched_at')
  final DateTime? lastMatchedAt;
  
  final String? name;
  final String? description;
  
  @JsonKey(name: 'created_at')
  final DateTime createdAt;
  
  @JsonKey(name: 'updated_at')
  final DateTime? updatedAt;

  TriggerModel({
    required this.id,
    required this.uuid,
    required this.demographicConditions,
    required this.timeSpan,
    this.cameraDeviceId,
    this.cameraName,
    this.actionUuid,
    this.actionName,
    this.actionUuids,
    this.actionNames,
    this.trackingDuration = '10 minutes',
    required this.isActive,
    this.cooldownSeconds = 60,
    this.lastFiredAt,
    this.triggerMode = 'demographic',
    this.behaviouralLookbackFlushes,
    this.behaviouralConditions,
    this.behaviouralConditionLogic,
    this.pplMatchGroupId,
    this.pplMatchGroupIds,
    this.cameraDeviceIds,
    this.pplMatchSimilarityThreshold = 0.75,
    this.pplMatchTopK = 1,
    this.pplMatchNegate = false,
    this.bodyPostureTarget,
    this.bodyPostureWindowSize,
    this.bodyPostureMinMatches,
    this.bodyPostureMinConfidence,
    this.bodyPostureIouThreshold,
    this.velocityScope,
    this.velocityBand,
    this.motionScope,
    this.motionConditions,
    this.motionConditionLogic,
    this.motionRoi,
    this.leftObjectClassAllowlist,
    this.leftObjectRoi,
    this.leftObjectTStableSeconds,
    this.leftObjectTAbandonSeconds,
    this.leftObjectMinBoxAreaPx,
    this.leftObjectRequirePersonLeft,
    this.leftObjectProximityPx,
    this.leftObjectIouThreshold,
    this.vehicleClassAllowlist,
    this.vehicleRoi,
    this.vehicleTStableSeconds,
    this.vehicleMinBoxAreaPx,
    this.vehiclePlateOcrEnabled,
    this.vehiclePlateOcrEveryNCycles,
    this.vehicleIouThreshold,
    this.searchCameraDeviceIds,
    this.searchIntervalSeconds,
    this.lastMatchInfo,
    this.lastMatchedAt,
    this.name,
    this.description,
    required this.createdAt,
    this.updatedAt,
  });

  factory TriggerModel.fromJson(Map<String, dynamic> json) {
    return _$TriggerModelFromJson(_normalizeTriggerJson(json));
  }

  Map<String, dynamic> toJson() => _$TriggerModelToJson(this);
  
  /// Human-readable display for conditions
  String get conditionsDisplay {
    if (triggerMode == 'vehicle_plate') {
      final cameraCount = cameraDeviceIds?.length ?? 0;
      final classes = (vehicleClassAllowlist ?? const ['car']).join(', ');
      final stable = vehicleTStableSeconds ?? 15;
      final plate = vehiclePlateOcrEnabled == false ? 'OCR off' : 'OCR on';
      return 'Vehicle+plate: $classes, ${stable}s, $plate, $cameraCount camera(s)';
    }
    if (triggerMode == 'left_object') {
      final cameraCount = cameraDeviceIds?.length ?? 0;
      final classes = (leftObjectClassAllowlist ?? const ['backpack']).join(', ');
      final stable = leftObjectTStableSeconds ?? 60;
      final requireLeft = leftObjectRequirePersonLeft == true;
      return requireLeft
          ? 'Left object (person left): $classes, ${stable}s, $cameraCount camera(s)'
          : 'Left object (stable): $classes, ${stable}s, $cameraCount camera(s)';
    }
    if (triggerMode == 'motion' || triggerMode == 'velocity') {
      final cameraCount = cameraDeviceIds?.length ?? 0;
      final scope = motionScope ?? velocityScope ?? 'crowd';
      final logic = (motionConditionLogic ?? 'and').toUpperCase();
      final conds = motionConditions;
      if (conds != null && conds.isNotEmpty) {
        final parts = conds.map((c) => '${c.field}:${c.value}').join(', ');
        return 'Motion ($logic): $parts, $scope, $cameraCount camera(s)';
      }
      final band = velocityBand ?? 'walking';
      return 'Motion: $scope ≥ $band, $cameraCount camera(s)';
    }
    if (triggerMode == 'body_posture') {
      final cameraCount = cameraDeviceIds?.length ?? 0;
      final target = bodyPostureTarget ?? 'horizontal';
      final window = bodyPostureWindowSize ?? 4;
      final minMatches = bodyPostureMinMatches ?? 3;
      return 'Body posture: $target ($minMatches/$window), $cameraCount camera(s)';
    }
    if (triggerMode == 'vprofile_match') {
      final groupCount = pplMatchGroupIds?.length ?? 0;
      final cameraCount = cameraDeviceIds?.length ?? 0;
      return 'VProfile: $groupCount group(s), $cameraCount camera(s)';
    }
    if (triggerMode == 'ppl_match') {
      return 'Group: ${pplMatchGroupId ?? 'Not set'}';
    }
    if (triggerMode == 'search') {
      final cameraCount = searchCameraDeviceIds?.length ?? 0;
      return 'Search: $cameraCount camera(s), every ${searchIntervalSeconds ?? 300}s';
    }
    if (triggerMode == 'search_demographic') {
      final cameraCount = searchCameraDeviceIds?.length ?? 0;
      final condCount = demographicConditions.length;
      return 'Demo Search: $cameraCount cam(s), $condCount cond(s), every ${searchIntervalSeconds ?? 300}s';
    }
    if (triggerMode == 'behavioural') {
      final n = behaviouralLookbackFlushes ?? 6;
      final condCount = behaviouralConditions?.length ?? 0;
      return 'Behavioural: $condCount cond(s), last $n flush(es)';
    }
    if (demographicConditions.isEmpty) return 'No conditions';
    return '${demographicConditions.length} condition(s)';
  }
}

@JsonSerializable(includeIfNull: false)
class TriggerCreateRequest {
  @JsonKey(name: 'demographic_conditions')
  final List<DemographicCondition> demographicConditions;
  
  @JsonKey(name: 'time_span')
  final String timeSpan;
  
  @JsonKey(name: 'camera_device_id')
  final String? cameraDeviceId;
  
  @JsonKey(name: 'camera_name')
  final String? cameraName;
  
  @JsonKey(name: 'action_uuid')
  final String? actionUuid;

  @JsonKey(name: 'action_uuids')
  final List<String>? actionUuids;
  
  @JsonKey(name: 'tracking_duration')
  final String trackingDuration;
  
  @JsonKey(name: 'is_active')
  final bool isActive;
  
  @JsonKey(name: 'cooldown_seconds')
  final int cooldownSeconds;

  @JsonKey(name: 'trigger_mode')
  final String triggerMode;

  @JsonKey(name: 'behavioural_lookback_flushes')
  final int? behaviouralLookbackFlushes;

  @JsonKey(name: 'behavioural_conditions')
  final List<DemographicCondition>? behaviouralConditions;

  @JsonKey(name: 'behavioural_condition_logic')
  final String? behaviouralConditionLogic;

  @JsonKey(name: 'ppl_match_group_id')
  final String? pplMatchGroupId;

  @JsonKey(name: 'ppl_match_group_ids')
  final List<String>? pplMatchGroupIds;

  @JsonKey(name: 'camera_device_ids')
  final List<String>? cameraDeviceIds;

  @JsonKey(name: 'ppl_match_similarity_threshold')
  final double? pplMatchSimilarityThreshold;

  @JsonKey(name: 'ppl_match_top_k')
  final int? pplMatchTopK;

  @JsonKey(name: 'ppl_match_negate')
  final bool? pplMatchNegate;

  @JsonKey(name: 'body_posture_target')
  final String? bodyPostureTarget;

  @JsonKey(name: 'body_posture_window_size')
  final int? bodyPostureWindowSize;

  @JsonKey(name: 'body_posture_min_matches')
  final int? bodyPostureMinMatches;

  @JsonKey(name: 'body_posture_min_confidence')
  final double? bodyPostureMinConfidence;

  @JsonKey(name: 'body_posture_iou_threshold')
  final double? bodyPostureIouThreshold;

  @JsonKey(name: 'velocity_scope')
  final String? velocityScope;

  @JsonKey(name: 'velocity_band')
  final String? velocityBand;

  @JsonKey(name: 'motion_scope')
  final String? motionScope;

  @JsonKey(name: 'motion_conditions')
  final List<MotionCondition>? motionConditions;

  @JsonKey(name: 'motion_condition_logic')
  final String? motionConditionLogic;

  @JsonKey(name: 'motion_roi')
  final List<List<double>>? motionRoi;

  @JsonKey(name: 'left_object_class_allowlist')
  final List<String>? leftObjectClassAllowlist;

  @JsonKey(name: 'left_object_roi')
  final List<List<double>>? leftObjectRoi;

  @JsonKey(name: 'left_object_t_stable_seconds')
  final int? leftObjectTStableSeconds;

  @JsonKey(name: 'left_object_t_abandon_seconds')
  final int? leftObjectTAbandonSeconds;

  @JsonKey(name: 'left_object_min_box_area_px')
  final int? leftObjectMinBoxAreaPx;

  @JsonKey(name: 'left_object_require_person_left')
  final bool? leftObjectRequirePersonLeft;

  @JsonKey(name: 'left_object_proximity_px')
  final double? leftObjectProximityPx;

  @JsonKey(name: 'left_object_iou_threshold')
  final double? leftObjectIouThreshold;

  @JsonKey(name: 'vehicle_class_allowlist')
  final List<String>? vehicleClassAllowlist;

  @JsonKey(name: 'vehicle_roi')
  final List<List<double>>? vehicleRoi;

  @JsonKey(name: 'vehicle_t_stable_seconds')
  final int? vehicleTStableSeconds;

  @JsonKey(name: 'vehicle_min_box_area_px')
  final int? vehicleMinBoxAreaPx;

  @JsonKey(name: 'vehicle_plate_ocr_enabled')
  final bool? vehiclePlateOcrEnabled;

  @JsonKey(name: 'vehicle_plate_ocr_every_n_cycles')
  final int? vehiclePlateOcrEveryNCycles;

  @JsonKey(name: 'vehicle_iou_threshold')
  final double? vehicleIouThreshold;

  @JsonKey(name: 'search_camera_device_ids')
  final List<String>? searchCameraDeviceIds;

  @JsonKey(name: 'search_interval_seconds')
  final int? searchIntervalSeconds;
  
  final String? name;
  final String? description;

  TriggerCreateRequest({
    required this.demographicConditions,
    required this.timeSpan,
    this.cameraDeviceId,
    this.cameraName,
    this.actionUuid,
    this.actionUuids,
    this.trackingDuration = '10 minutes',
    this.isActive = true,
    this.cooldownSeconds = 60,
    this.triggerMode = 'demographic',
    this.behaviouralLookbackFlushes,
    this.behaviouralConditions,
    this.behaviouralConditionLogic,
    this.pplMatchGroupId,
    this.pplMatchGroupIds,
    this.cameraDeviceIds,
    this.pplMatchSimilarityThreshold,
    this.pplMatchTopK,
    this.pplMatchNegate,
    this.bodyPostureTarget,
    this.bodyPostureWindowSize,
    this.bodyPostureMinMatches,
    this.bodyPostureMinConfidence,
    this.bodyPostureIouThreshold,
    this.velocityScope,
    this.velocityBand,
    this.motionScope,
    this.motionConditions,
    this.motionConditionLogic,
    this.motionRoi,
    this.leftObjectClassAllowlist,
    this.leftObjectRoi,
    this.leftObjectTStableSeconds,
    this.leftObjectTAbandonSeconds,
    this.leftObjectMinBoxAreaPx,
    this.leftObjectRequirePersonLeft,
    this.leftObjectProximityPx,
    this.leftObjectIouThreshold,
    this.vehicleClassAllowlist,
    this.vehicleRoi,
    this.vehicleTStableSeconds,
    this.vehicleMinBoxAreaPx,
    this.vehiclePlateOcrEnabled,
    this.vehiclePlateOcrEveryNCycles,
    this.vehicleIouThreshold,
    this.searchCameraDeviceIds,
    this.searchIntervalSeconds,
    this.name,
    this.description,
  });

  factory TriggerCreateRequest.fromJson(Map<String, dynamic> json) =>
      _$TriggerCreateRequestFromJson(json);

  Map<String, dynamic> toJson() => _$TriggerCreateRequestToJson(this);
}

@JsonSerializable()
class TriggerListResponse {
  final List<TriggerModel> triggers;
  final int total;
  final int page;
  @JsonKey(name: 'page_size')
  final int pageSize;
  @JsonKey(name: 'total_pages')
  final int totalPages;

  TriggerListResponse({
    required this.triggers,
    required this.total,
    required this.page,
    required this.pageSize,
    required this.totalPages,
  });

  factory TriggerListResponse.fromJson(Map<String, dynamic> json) {
    final triggersRaw = json['triggers'];
    final triggers = <TriggerModel>[];
    if (triggersRaw is List) {
      for (final item in triggersRaw) {
        if (item is Map) {
          triggers.add(
            TriggerModel.fromJson(
              item is Map<String, dynamic>
                  ? item
                  : item.map((k, v) => MapEntry(k.toString(), v)),
            ),
          );
        }
      }
    }
    return TriggerListResponse(
      triggers: triggers,
      total: (json['total'] as num?)?.toInt() ?? triggers.length,
      page: (json['page'] as num?)?.toInt() ?? 1,
      pageSize: (json['page_size'] as num?)?.toInt() ?? triggers.length,
      totalPages: (json['total_pages'] as num?)?.toInt() ?? 1,
    );
  }

  Map<String, dynamic> toJson() => _$TriggerListResponseToJson(this);
}
