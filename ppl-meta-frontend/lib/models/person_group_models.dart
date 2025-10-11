/// PPL Meta Frontend - Person Group Drill-Down Models
/// 
/// This file contains the detailed data models for person group analytics
/// and drill-down views, supporting comprehensive person object analysis.

import 'package:flutter/material.dart';

// =============================================================================
// PERSON GROUP ANALYTICS MODELS
// =============================================================================

/// Represents a complete person group with all analytics data
class PersonObjectGroup {
  final String personUuid;
  final String personId;
  final int faceCount;
  final List<RepresentativeFace> representativeFaces;
  final List<String> allFaceIds;
  final double averageConfidence;
  final SpatialBounds spatialBounds;
  final TemporalSpan temporalSpan;
  final MovementTracking movementTracking;
  final QualityMetrics qualityMetrics;

  const PersonObjectGroup({
    required this.personUuid,
    required this.personId,
    required this.faceCount,
    required this.representativeFaces,
    required this.allFaceIds,
    required this.averageConfidence,
    required this.spatialBounds,
    required this.temporalSpan,
    required this.movementTracking,
    required this.qualityMetrics,
  });

  factory PersonObjectGroup.fromJson(Map<String, dynamic> json) {
    return PersonObjectGroup(
      personUuid: json['person_uuid'] ?? '',
      personId: json['person_id'] ?? '',
      faceCount: json['face_count'] ?? 0,
      representativeFaces: (json['representative_faces'] as List?)
          ?.map((face) => RepresentativeFace.fromJson(face))
          .toList() ?? [],
      allFaceIds: List<String>.from(json['all_face_ids'] ?? []),
      averageConfidence: (json['average_confidence'] ?? 0.0).toDouble(),
      spatialBounds: SpatialBounds.fromJson(json['spatial_bounds'] ?? {}),
      temporalSpan: TemporalSpan.fromJson(json['temporal_span'] ?? {}),
      movementTracking: MovementTracking.fromJson(json['movement_tracking'] ?? {}),
      qualityMetrics: QualityMetrics.fromJson(json['quality_metrics'] ?? {}),
    );
  }

  /// Get the closest distance from representative faces
  double get closestDistance {
    if (representativeFaces.isEmpty) return 100.0;
    return representativeFaces
        .map((face) => face.faceData['distance_from_camera'] as double? ?? 100.0)
        .reduce((a, b) => a < b ? a : b);
  }

  /// Get distance-based color for this person group
  Color get distanceColor {
    final distance = closestDistance;
    if (distance < 10) return const Color(0xFFE53E3E); // Red - Very close
    if (distance < 20) return const Color(0xFFFF8C00); // Orange - Close  
    if (distance < 30) return const Color(0xFFFFD700); // Yellow - Medium
    if (distance < 50) return const Color(0xFF38A169); // Green - Far
    return const Color(0xFF3182CE); // Blue - Very far
  }
}

/// Representative face with quality scoring and selection metadata
class RepresentativeFace {
  final Map<String, dynamic> faceData;
  final double qualityScore;
  final int selectionRank;
  final SelectionCriteria selectionCriteria;

  const RepresentativeFace({
    required this.faceData,
    required this.qualityScore,
    required this.selectionRank,
    required this.selectionCriteria,
  });

  factory RepresentativeFace.fromJson(Map<String, dynamic> json) {
    return RepresentativeFace(
      faceData: json['face_data'] ?? {},
      qualityScore: (json['quality_score'] ?? 0.0).toDouble(),
      selectionRank: json['selection_rank'] ?? 0,
      selectionCriteria: SelectionCriteria.fromJson(json['selection_criteria'] ?? {}),
    );
  }

  /// Get distance from camera for this face
  double get distance => (faceData['distance_from_camera'] as double?) ?? 100.0;

  /// Get confidence score for this face
  double get confidence => (faceData['confidence'] as double?) ?? 0.0;

  /// Get face area for this face
  double get faceArea => (faceData['face_area'] as double?) ?? 0.0;

  /// Get bounding box as List<double>
  List<double> get bbox {
    final bboxData = faceData['bbox'] as List?;
    if (bboxData == null) return [0, 0, 0, 0];
    return bboxData.map((e) => (e as num).toDouble()).toList();
  }
}

/// Face selection criteria with weighting factors
class SelectionCriteria {
  final double distanceWeight;
  final double confidenceWeight;
  final double areaWeight;
  final double positionWeight;

  const SelectionCriteria({
    required this.distanceWeight,
    required this.confidenceWeight,
    required this.areaWeight,
    required this.positionWeight,
  });

  factory SelectionCriteria.fromJson(Map<String, dynamic> json) {
    return SelectionCriteria(
      distanceWeight: (json['distance_weight'] ?? 0.0).toDouble(),
      confidenceWeight: (json['confidence_weight'] ?? 0.0).toDouble(),
      areaWeight: (json['area_weight'] ?? 0.0).toDouble(),
      positionWeight: (json['position_weight'] ?? 0.0).toDouble(),
    );
  }
}

/// Spatial bounds and positioning data
class SpatialBounds {
  final double minX;
  final double maxX;
  final double minY;
  final double maxY;
  final double centerX;
  final double centerY;

  const SpatialBounds({
    required this.minX,
    required this.maxX,
    required this.minY,
    required this.maxY,
    required this.centerX,
    required this.centerY,
  });

  factory SpatialBounds.fromJson(Map<String, dynamic> json) {
    return SpatialBounds(
      minX: (json['min_x'] ?? 0.0).toDouble(),
      maxX: (json['max_x'] ?? 0.0).toDouble(),
      minY: (json['min_y'] ?? 0.0).toDouble(),
      maxY: (json['max_y'] ?? 0.0).toDouble(),
      centerX: (json['center_x'] ?? 0.0).toDouble(),
      centerY: (json['center_y'] ?? 0.0).toDouble(),
    );
  }

  /// Calculate width of movement area
  double get width => maxX - minX;

  /// Calculate height of movement area
  double get height => maxY - minY;

  /// Calculate area of movement bounds
  double get area => width * height;
}

/// Temporal span and timing information
class TemporalSpan {
  final int startFrame;
  final int endFrame;
  final double durationSeconds;
  final int frameCount;

  const TemporalSpan({
    required this.startFrame,
    required this.endFrame,
    required this.durationSeconds,
    required this.frameCount,
  });

  factory TemporalSpan.fromJson(Map<String, dynamic> json) {
    return TemporalSpan(
      startFrame: json['start_frame'] ?? 0,
      endFrame: json['end_frame'] ?? 0,
      durationSeconds: (json['duration_seconds'] ?? 0.0).toDouble(),
      frameCount: json['frame_count'] ?? 0,
    );
  }

  /// Get frames per second rate
  double get framesPerSecond {
    if (durationSeconds <= 0) return 0.0;
    return frameCount / durationSeconds;
  }
}

/// Movement tracking with route points and statistics
class MovementTracking {
  final List<RoutePoint> routePoints;
  final MovementStatistics movementStatistics;

  const MovementTracking({
    required this.routePoints,
    required this.movementStatistics,
  });

  factory MovementTracking.fromJson(Map<String, dynamic> json) {
    return MovementTracking(
      routePoints: (json['route_points'] as List?)
          ?.map((point) => RoutePoint.fromJson(point))
          .toList() ?? [],
      movementStatistics: MovementStatistics.fromJson(json['movement_statistics'] ?? {}),
    );
  }
}

/// Individual route point with position and velocity
class RoutePoint {
  final int sequenceNumber;
  final int frameNumber;
  final double timestamp;
  final double centerX;
  final double centerY;
  final double? distanceFromCamera;
  final double velocityX;
  final double velocityY;
  final double velocityMagnitude;

  const RoutePoint({
    required this.sequenceNumber,
    required this.frameNumber,
    required this.timestamp,
    required this.centerX,
    required this.centerY,
    this.distanceFromCamera,
    required this.velocityX,
    required this.velocityY,
    required this.velocityMagnitude,
  });

  factory RoutePoint.fromJson(Map<String, dynamic> json) {
    return RoutePoint(
      sequenceNumber: json['sequence_number'] ?? 0,
      frameNumber: json['frame_number'] ?? 0,
      timestamp: (json['timestamp'] ?? 0.0).toDouble(),
      centerX: (json['center_x'] ?? 0.0).toDouble(),
      centerY: (json['center_y'] ?? 0.0).toDouble(),
      distanceFromCamera: (json['distance_from_camera'] as double?),
      velocityX: (json['velocity_x'] ?? 0.0).toDouble(),
      velocityY: (json['velocity_y'] ?? 0.0).toDouble(),
      velocityMagnitude: (json['velocity_magnitude'] ?? 0.0).toDouble(),
    );
  }
}

/// Movement statistics and analytics
class MovementStatistics {
  final int totalRoutePoints;
  final double totalDistancePixels;
  final double averageVelocity;
  final double maxVelocity;
  final double timeInFrameSeconds;

  const MovementStatistics({
    required this.totalRoutePoints,
    required this.totalDistancePixels,
    required this.averageVelocity,
    required this.maxVelocity,
    required this.timeInFrameSeconds,
  });

  factory MovementStatistics.fromJson(Map<String, dynamic> json) {
    return MovementStatistics(
      totalRoutePoints: json['total_route_points'] ?? 0,
      totalDistancePixels: (json['total_distance_pixels'] ?? 0.0).toDouble(),
      averageVelocity: (json['average_velocity'] ?? 0.0).toDouble(),
      maxVelocity: (json['max_velocity'] ?? 0.0).toDouble(),
      timeInFrameSeconds: (json['time_in_frame_seconds'] ?? 0.0).toDouble(),
    );
  }
}

/// Quality metrics and scoring information
class QualityMetrics {
  final double averageQuality;
  final double maxQuality;
  final double minQuality;
  final double qualityVariance;

  const QualityMetrics({
    required this.averageQuality,
    required this.maxQuality,
    required this.minQuality,
    required this.qualityVariance,
  });

  factory QualityMetrics.fromJson(Map<String, dynamic> json) {
    // Calculate quality metrics from representative faces if not provided
    return QualityMetrics(
      averageQuality: (json['average_quality'] ?? 75.0).toDouble(),
      maxQuality: (json['max_quality'] ?? 85.0).toDouble(),
      minQuality: (json['min_quality'] ?? 65.0).toDouble(),
      qualityVariance: (json['quality_variance'] ?? 10.0).toDouble(),
    );
  }

  /// Get quality consistency percentage (100% - variance)
  double get qualityConsistency => 100.0 - qualityVariance;
}

/// Response model for PPL Thread endpoint with person groups
class PPLThreadWorkflowResponse {
  final bool success;
  final String mediaId;
  final int totalPersons;
  final int totalFaces;
  final String status;
  final String message;
  final List<PersonObjectGroup> personGroups;
  final String groupingAlgorithm;
  final double iouThreshold;
  final double processingTimeMs;
  final String sessionUuid;

  const PPLThreadWorkflowResponse({
    required this.success,
    required this.mediaId,
    required this.totalPersons,
    required this.totalFaces,
    required this.status,
    required this.message,
    required this.personGroups,
    required this.groupingAlgorithm,
    required this.iouThreshold,
    required this.processingTimeMs,
    required this.sessionUuid,
  });

  factory PPLThreadWorkflowResponse.fromJson(Map<String, dynamic> json) {
    return PPLThreadWorkflowResponse(
      success: json['success'] ?? false,
      mediaId: json['media_id'] ?? '',
      totalPersons: json['total_persons'] ?? 0,
      totalFaces: json['total_faces'] ?? 0,
      status: json['status'] ?? '',
      message: json['message'] ?? '',
      personGroups: (json['person_groups'] as List?)
          ?.map((group) => PersonObjectGroup.fromJson(group))
          .toList() ?? [],
      groupingAlgorithm: json['grouping_algorithm'] ?? '',
      iouThreshold: (json['iou_threshold'] ?? 0.0).toDouble(),
      processingTimeMs: (json['processing_time_ms'] ?? 0.0).toDouble(),
      sessionUuid: json['session_uuid'] ?? '',
    );
  }
}

// =============================================================================
// UTILITY FUNCTIONS
// =============================================================================

/// Get distance-based color for any distance value
Color getDistanceColor(double distance) {
  if (distance < 10) return const Color(0xFFE53E3E); // Red - Very close (< 10m)
  if (distance < 20) return const Color(0xFFFF8C00); // Orange - Close (10-20m) 
  if (distance < 30) return const Color(0xFFFFD700); // Yellow - Medium (20-30m)
  if (distance < 50) return const Color(0xFF38A169); // Green - Far (30-50m)
  return const Color(0xFF3182CE); // Blue - Very far (> 50m)
}

/// Get distance category name for UI display
String getDistanceCategoryName(double distance) {
  if (distance < 10) return 'Very Close';
  if (distance < 20) return 'Close';
  if (distance < 30) return 'Medium';
  if (distance < 50) return 'Far';
  return 'Very Far';
}

/// Get quality level name based on score
String getQualityLevelName(double qualityScore) {
  if (qualityScore >= 90) return 'Excellent';
  if (qualityScore >= 80) return 'Very Good';
  if (qualityScore >= 70) return 'Good';
  if (qualityScore >= 60) return 'Fair';
  return 'Poor';
}