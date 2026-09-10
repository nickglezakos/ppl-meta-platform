import 'package:json_annotation/json_annotation.dart';

part 'trigger_model.g.dart';

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
    return _$TriggerModelFromJson(json);
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
    if (triggerMode == 'velocity') {
      final cameraCount = cameraDeviceIds?.length ?? 0;
      final scope = velocityScope ?? 'crowd';
      final band = velocityBand ?? 'walking';
      const floors = {
        'walking': '1.25',
        'light_running': '2.2',
        'running': '3.3',
        'fast_running': '5.0',
      };
      final floor = floors[band] ?? '?';
      return 'Velocity: $scope ≥ $band ($floor m/s), $cameraCount camera(s)';
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

  factory TriggerListResponse.fromJson(Map<String, dynamic> json) =>
      _$TriggerListResponseFromJson(json);

  Map<String, dynamic> toJson() => _$TriggerListResponseToJson(this);
}
