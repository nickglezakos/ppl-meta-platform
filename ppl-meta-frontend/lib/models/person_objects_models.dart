/// PPL Meta Frontend - Person Objects Data Models
/// 
/// Data models for PPL Thread (Person Objects) functionality that match
/// the PPL Meta Mini output structure exactly. These models provide type-safe
/// access to person objects data from the Vision Service PPL Thread workflow.
/// 
/// Key Features:
/// - Exact compatibility with PPL Meta Mini FaceGroupingEngine output
/// - Type-safe JSON serialization/deserialization
/// - Comprehensive person tracking and quality analysis support
/// - Age detection and best face quality integration

import 'package:flutter/foundation.dart';

/// Person objects data model matching PPL Meta Mini output structure
class PersonObjectsData {
  final String workflowId;
  final String sessionUuid;
  final bool success;
  final int originalGroups;
  final int mergedGroups;
  final int totalPersons;
  final List<PersonGroup> groupTracking;
  final PersonObjectsStatistics statistics;
  final Map<String, BestQualityFace> bestQualityFaces;
  final List<ClassifiedFace> classifiedFaces;
  final String processingTimestamp;
  final String workflowType;

  const PersonObjectsData({
    required this.workflowId,
    required this.sessionUuid,
    required this.success,
    required this.originalGroups,
    required this.mergedGroups,
    required this.totalPersons,
    required this.groupTracking,
    required this.statistics,
    required this.bestQualityFaces,
    required this.classifiedFaces,
    required this.processingTimestamp,
    required this.workflowType,
  });

  factory PersonObjectsData.fromJson(Map<String, dynamic> json) {
    return PersonObjectsData(
      workflowId: json['workflow_id'] ?? json['media_id'] ?? '',
      sessionUuid: json['session_uuid'] ?? '',
      success: json['success'] ?? false,
      originalGroups: json['original_groups'] ?? json['total_faces'] ?? 0,
      mergedGroups: json['merged_groups'] ?? json['total_persons'] ?? 0,
      totalPersons: json['total_persons'] ?? json['merged_groups'] ?? 0,  // Use total_persons from Orchestrator response
      groupTracking: (json['group_tracking'] as List? ?? [])
          .map((item) => PersonGroup.fromJson(item))
          .toList(),
      statistics: PersonObjectsStatistics.fromJson(json['statistics'] ?? {}),
      bestQualityFaces: (json['best_quality_faces'] as Map<String, dynamic>? ?? {})
          .map((key, value) => MapEntry(key, BestQualityFace.fromJson(value))),
      classifiedFaces: (json['classified_faces'] as List? ?? [])
          .map((item) => ClassifiedFace.fromJson(item))
          .toList(),
      processingTimestamp: json['processing_timestamp'] ?? '',
      workflowType: json['workflow_type'] ?? '',
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'workflow_id': workflowId,
      'session_uuid': sessionUuid,
      'success': success,
      'original_groups': originalGroups,
      'merged_groups': mergedGroups,
      'group_tracking': groupTracking.map((g) => g.toJson()).toList(),
      'statistics': statistics.toJson(),
      'best_quality_faces': bestQualityFaces.map((k, v) => MapEntry(k, v.toJson())),
      'classified_faces': classifiedFaces.map((f) => f.toJson()).toList(),
      'processing_timestamp': processingTimestamp,
      'workflow_type': workflowType,
    };
  }

  /// Get summary statistics for UI display
  PersonObjectsSummary get summary => PersonObjectsSummary(
    totalPersons: totalPersons,
    totalFaces: originalGroups,
    averageFacesPerPerson: totalPersons > 0 ? (originalGroups / totalPersons).round() : 0,
    qualityAnalysisCount: bestQualityFaces.length,
    framesProcessed: statistics.framesProcessed,
    groupingAlgorithm: statistics.groupingAlgorithm,
    tolerancePercent: statistics.tolerancePercent,
  );

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is PersonObjectsData &&
          runtimeType == other.runtimeType &&
          workflowId == other.workflowId &&
          sessionUuid == other.sessionUuid;

  @override
  int get hashCode => workflowId.hashCode ^ sessionUuid.hashCode;
}

/// Person group tracking data (matches PPL Mini format exactly)
class PersonGroup {
  final String mergedGroupId;
  final List<String> originalGroupIds;
  final int faceCount;
  final PersonPosition averagePosition;
  final bool yCoordinateBased;
  final bool trackingBased;
  final double tolerancePercent;
  final List<dynamic> mergeHistory;

  const PersonGroup({
    required this.mergedGroupId,
    required this.originalGroupIds,
    required this.faceCount,
    required this.averagePosition,
    required this.yCoordinateBased,
    required this.trackingBased,
    required this.tolerancePercent,
    required this.mergeHistory,
  });

  factory PersonGroup.fromJson(Map<String, dynamic> json) {
    return PersonGroup(
      mergedGroupId: json['Merged_Group_ID'] ?? '',
      originalGroupIds: List<String>.from(json['Original_Group_IDs'] ?? []),
      faceCount: json['Face_Count'] ?? 0,
      averagePosition: PersonPosition.fromJson(json['Average_Position'] ?? {}),
      yCoordinateBased: json['Y_Coordinate_Based'] ?? false,
      trackingBased: json['Tracking_Based'] ?? false,
      tolerancePercent: (json['Tolerance_Percent'] ?? 0).toDouble(),
      mergeHistory: json['Merge_History'] ?? [],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'Merged_Group_ID': mergedGroupId,
      'Original_Group_IDs': originalGroupIds,
      'Face_Count': faceCount,
      'Average_Position': averagePosition.toJson(),
      'Y_Coordinate_Based': yCoordinateBased,
      'Tracking_Based': trackingBased,
      'Tolerance_Percent': tolerancePercent,
      'Merge_History': mergeHistory,
    };
  }

  @override
  String toString() => 'PersonGroup(id: $mergedGroupId, faces: $faceCount, pos: $averagePosition)';
}

/// Person position coordinates
class PersonPosition {
  final double x;
  final double y;

  const PersonPosition({required this.x, required this.y});

  factory PersonPosition.fromJson(Map<String, dynamic> json) {
    return PersonPosition(
      x: (json['x'] ?? 0).toDouble(),
      y: (json['y'] ?? 0).toDouble(),
    );
  }

  Map<String, dynamic> toJson() {
    return {'x': x, 'y': y};
  }

  @override
  String toString() => 'PersonPosition(x: ${x.toStringAsFixed(1)}, y: ${y.toStringAsFixed(1)})';

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is PersonPosition &&
          runtimeType == other.runtimeType &&
          x == other.x &&
          y == other.y;

  @override
  int get hashCode => x.hashCode ^ y.hashCode;
}

/// Best quality face for a person
class BestQualityFace {
  final String faceId;
  final int frameNumber;
  final double qualityScore;
  final List<int> bbox;
  final AgeDetection ageDetection;
  final double distance;

  const BestQualityFace({
    required this.faceId,
    required this.frameNumber,
    required this.qualityScore,
    required this.bbox,
    required this.ageDetection,
    required this.distance,
  });

  factory BestQualityFace.fromJson(Map<String, dynamic> json) {
    return BestQualityFace(
      faceId: json['face_id'] ?? '',
      frameNumber: json['frame_number'] ?? 0,
      qualityScore: (json['quality_score'] ?? 0).toDouble(),
      bbox: List<int>.from(json['bbox'] ?? []),
      ageDetection: AgeDetection.fromJson(json['age_detection'] ?? {}),
      distance: (json['distance'] ?? 0).toDouble(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'face_id': faceId,
      'frame_number': frameNumber,
      'quality_score': qualityScore,
      'bbox': bbox,
      'age_detection': ageDetection.toJson(),
      'distance': distance,
    };
  }

  /// Get quality score as percentage for UI display
  String get qualityPercentage => '${(qualityScore * 100).toStringAsFixed(1)}%';

  /// Get distance in user-friendly format
  String get distanceFormatted => '${distance.toStringAsFixed(1)} units';

  @override
  String toString() => 'BestQualityFace(id: $faceId, frame: $frameNumber, quality: $qualityPercentage)';
}

/// Age detection result
class AgeDetection {
  final dynamic estimatedAge;  // Can be int or "Unknown"

  const AgeDetection({required this.estimatedAge});

  factory AgeDetection.fromJson(Map<String, dynamic> json) {
    return AgeDetection(
      estimatedAge: json['estimated_age'] ?? 'Unknown',
    );
  }

  Map<String, dynamic> toJson() {
    return {'estimated_age': estimatedAge};
  }
  
  String get displayAge {
    if (estimatedAge is int) {
      return '$estimatedAge years';
    }
    return estimatedAge.toString();
  }

  bool get hasValidAge => estimatedAge is int && estimatedAge > 0;

  @override
  String toString() => 'AgeDetection($displayAge)';
}

/// Person objects processing statistics
class PersonObjectsStatistics {
  final int totalGroups;
  final int originalUniqueFaces;
  final int mergedGroupsCount;
  final int totalDetections;
  final int framesProcessed;
  final String groupingAlgorithm;
  final double tolerancePercent;
  final int trackedFaces;
  final int newFaces;
  final int mergeIterations;

  const PersonObjectsStatistics({
    required this.totalGroups,
    required this.originalUniqueFaces,
    required this.mergedGroupsCount,
    required this.totalDetections,
    required this.framesProcessed,
    required this.groupingAlgorithm,
    required this.tolerancePercent,
    required this.trackedFaces,
    required this.newFaces,
    required this.mergeIterations,
  });

  factory PersonObjectsStatistics.fromJson(Map<String, dynamic> json) {
    return PersonObjectsStatistics(
      totalGroups: json['total_groups'] ?? 0,
      originalUniqueFaces: json['original_unique_faces'] ?? 0,
      mergedGroupsCount: json['merged_groups_count'] ?? 0,
      totalDetections: json['total_detections'] ?? 0,
      framesProcessed: json['frames_processed'] ?? 0,
      groupingAlgorithm: json['grouping_algorithm'] ?? '',
      tolerancePercent: (json['tolerance_percent'] ?? 0).toDouble(),
      trackedFaces: json['tracked_faces'] ?? 0,
      newFaces: json['new_faces'] ?? 0,
      mergeIterations: json['merge_iterations'] ?? 0,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'total_groups': totalGroups,
      'original_unique_faces': originalUniqueFaces,
      'merged_groups_count': mergedGroupsCount,
      'total_detections': totalDetections,
      'frames_processed': framesProcessed,
      'grouping_algorithm': groupingAlgorithm,
      'tolerance_percent': tolerancePercent,
      'tracked_faces': trackedFaces,
      'new_faces': newFaces,
      'merge_iterations': mergeIterations,
    };
  }

  /// Calculate grouping efficiency percentage
  double get groupingEfficiency {
    if (originalUniqueFaces == 0) return 0.0;
    return ((originalUniqueFaces - totalGroups) / originalUniqueFaces) * 100;
  }

  /// Calculate average faces per person
  double get averageFacesPerPerson {
    if (totalGroups == 0) return 0.0;
    return originalUniqueFaces / totalGroups;
  }

  @override
  String toString() => 'PersonObjectsStatistics(groups: $totalGroups, faces: $originalUniqueFaces, efficiency: ${groupingEfficiency.toStringAsFixed(1)}%)';
}

/// Classified face mapping
class ClassifiedFace {
  final String personId;
  final String faceDetectionId;
  final String matchType;
  final double matchDistance;
  final int frameNumber;
  final double positionX;
  final double positionY;

  const ClassifiedFace({
    required this.personId,
    required this.faceDetectionId,
    required this.matchType,
    required this.matchDistance,
    required this.frameNumber,
    required this.positionX,
    required this.positionY,
  });

  factory ClassifiedFace.fromJson(Map<String, dynamic> json) {
    return ClassifiedFace(
      personId: json['person_id'] ?? '',
      faceDetectionId: json['face_detection_id'] ?? '',
      matchType: json['match_type'] ?? '',
      matchDistance: (json['match_distance'] ?? 0).toDouble(),
      frameNumber: json['frame_number'] ?? 0,
      positionX: (json['position_x'] ?? 0).toDouble(),
      positionY: (json['position_y'] ?? 0).toDouble(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'person_id': personId,
      'face_detection_id': faceDetectionId,
      'match_type': matchType,
      'match_distance': matchDistance,
      'frame_number': frameNumber,
      'position_x': positionX,
      'position_y': positionY,
    };
  }

  PersonPosition get position => PersonPosition(x: positionX, y: positionY);

  bool get isNewTrack => matchType == 'new_track';
  bool get isTrackedFace => matchType == 'tracked';

  @override
  String toString() => 'ClassifiedFace(person: $personId, face: $faceDetectionId, type: $matchType, frame: $frameNumber)';
}

/// Summary data for UI display
class PersonObjectsSummary {
  final int totalPersons;
  final int totalFaces;
  final int averageFacesPerPerson;
  final int qualityAnalysisCount;
  final int framesProcessed;
  final String groupingAlgorithm;
  final double tolerancePercent;

  const PersonObjectsSummary({
    required this.totalPersons,
    required this.totalFaces,
    required this.averageFacesPerPerson,
    required this.qualityAnalysisCount,
    required this.framesProcessed,
    required this.groupingAlgorithm,
    required this.tolerancePercent,
  });

  /// Get grouping efficiency as percentage string
  String get groupingEfficiencyText {
    if (totalFaces == 0) return '0%';
    final efficiency = ((totalFaces - totalPersons) / totalFaces) * 100;
    return '${efficiency.toStringAsFixed(1)}%';
  }

  /// Get summary text for compact display
  String get compactSummary => '$totalPersons persons from $totalFaces faces';

  /// Get detailed summary text
  String get detailedSummary => 
      '$totalPersons persons grouped from $totalFaces faces ($groupingEfficiencyText efficiency)';

  @override
  String toString() => 'PersonObjectsSummary($compactSummary, efficiency: $groupingEfficiencyText)';
}