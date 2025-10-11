/// PPL Meta Frontend - Enhanced Person Objects Models with Distance Support
/// 
/// This file contains the enhanced data models for the distance-based color 
/// coding feature. These models support the new PPL Thread endpoint that 
/// includes distance calculations, representative faces, and quality scoring.

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

// =============================================================================
// ENHANCED PERSON OBJECTS MODELS FOR DISTANCE-BASED COLOR CODING
// =============================================================================

/// Enhanced person object group with distance information and representative faces
class EnhancedPersonObjectGroup {
  final String personUuid;
  final String personId;
  final int faceCount;
  final List<RepresentativeFace> representativeFaces;
  final List<String> allFaceIds;
  final double averageConfidence;
  final EnhancedSpatialBounds spatialBounds;
  final EnhancedTemporalSpan temporalSpan;
  final EnhancedMovementTracking movementTracking;
  final EnhancedQualityMetrics qualityMetrics;

  const EnhancedPersonObjectGroup({
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

  factory EnhancedPersonObjectGroup.fromJson(Map<String, dynamic> json) {
    return EnhancedPersonObjectGroup(
      personUuid: json['person_uuid'] ?? '',
      personId: json['person_id'] ?? '',
      faceCount: json['face_count'] ?? 0,
      representativeFaces: (json['representative_faces'] as List?)
          ?.map((e) => RepresentativeFace.fromJson(e))
          .toList() ?? [],
      allFaceIds: List<String>.from(json['all_face_ids'] ?? []),
      averageConfidence: (json['average_confidence'] ?? 0.0).toDouble(),
      spatialBounds: EnhancedSpatialBounds.fromJson(json['spatial_bounds'] ?? {}),
      temporalSpan: EnhancedTemporalSpan.fromJson(json['temporal_span'] ?? {}),
      movementTracking: EnhancedMovementTracking.fromJson(json['movement_tracking'] ?? {}),
      qualityMetrics: EnhancedQualityMetrics.fromJson(json['quality_metrics'] ?? {}),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'person_uuid': personUuid,
      'person_id': personId,
      'face_count': faceCount,
      'representative_faces': representativeFaces.map((e) => e.toJson()).toList(),
      'all_face_ids': allFaceIds,
      'average_confidence': averageConfidence,
      'spatial_bounds': spatialBounds.toJson(),
      'temporal_span': temporalSpan.toJson(),
      'movement_tracking': movementTracking.toJson(),
      'quality_metrics': qualityMetrics.toJson(),
    };
  }

  /// Get the closest distance from all representative faces
  double get closestDistance {
    if (representativeFaces.isEmpty) return 100.0; // Default far distance
    
    return representativeFaces
        .map((face) => face.faceData.distanceFromCamera)
        .reduce((a, b) => a < b ? a : b);
  }

  /// Get the best quality representative face (rank 1)
  RepresentativeFace? get bestFace {
    return representativeFaces.isEmpty 
        ? null 
        : representativeFaces.firstWhere(
            (face) => face.selectionRank == 1,
            orElse: () => representativeFaces.first,
          );
  }

  /// Get distance-based color for UI display
  Color get distanceColor {
    final distance = closestDistance;
    if (distance < 10) return const Color(0xFFE53E3E); // Red - Very close
    if (distance < 20) return const Color(0xFFFF8C00); // Orange - Close  
    if (distance < 30) return const Color(0xFFFFD700); // Yellow - Medium
    if (distance < 50) return const Color(0xFF38A169); // Green - Far
    return const Color(0xFF3182CE); // Blue - Very far
  }

  @override
  String toString() => 'EnhancedPersonObjectGroup(id: $personId, faces: $faceCount, distance: ${closestDistance.toStringAsFixed(1)}m)';
}

/// Representative face with quality scoring and selection criteria
class RepresentativeFace {
  final EnhancedFaceData faceData;
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
      faceData: EnhancedFaceData.fromJson(json['face_data'] ?? {}),
      qualityScore: (json['quality_score'] ?? 0.0).toDouble(),
      selectionRank: json['selection_rank'] ?? 0,
      selectionCriteria: SelectionCriteria.fromJson(json['selection_criteria'] ?? {}),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'face_data': faceData.toJson(),
      'quality_score': qualityScore,
      'selection_rank': selectionRank,
      'selection_criteria': selectionCriteria.toJson(),
    };
  }

  @override
  String toString() => 'RepresentativeFace(rank: $selectionRank, quality: ${qualityScore.toStringAsFixed(1)}, distance: ${faceData.distanceFromCamera.toStringAsFixed(1)}m)';
}

/// Enhanced face data with distance and center coordinates
class EnhancedFaceData {
  final List<double> bbox;
  final double confidence;
  final String method;
  final double timestamp;
  final int frameNumber;
  final double distanceFromCamera;
  final double centerX;
  final double centerY;
  final double faceWidth;
  final double faceHeight;
  final double faceArea;

  const EnhancedFaceData({
    required this.bbox,
    required this.confidence,
    required this.method,
    required this.timestamp,
    required this.frameNumber,
    required this.distanceFromCamera,
    required this.centerX,
    required this.centerY,
    required this.faceWidth,
    required this.faceHeight,
    required this.faceArea,
  });

  factory EnhancedFaceData.fromJson(Map<String, dynamic> json) {
    return EnhancedFaceData(
      bbox: List<double>.from(json['bbox'] ?? []),
      confidence: (json['confidence'] ?? 0.0).toDouble(),
      method: json['method'] ?? '',
      timestamp: (json['timestamp'] ?? 0.0).toDouble(),
      frameNumber: json['frame_number'] ?? 0,
      distanceFromCamera: (json['distance_from_camera'] ?? 0.0).toDouble(),
      centerX: (json['center_x'] ?? 0.0).toDouble(),
      centerY: (json['center_y'] ?? 0.0).toDouble(),
      faceWidth: (json['face_width'] ?? 0.0).toDouble(),
      faceHeight: (json['face_height'] ?? 0.0).toDouble(),
      faceArea: (json['face_area'] ?? 0.0).toDouble(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'bbox': bbox,
      'confidence': confidence,
      'method': method,
      'timestamp': timestamp,
      'frame_number': frameNumber,
      'distance_from_camera': distanceFromCamera,
      'center_x': centerX,
      'center_y': centerY,
      'face_width': faceWidth,
      'face_height': faceHeight,
      'face_area': faceArea,
    };
  }

  @override
  String toString() => 'EnhancedFaceData(frame: $frameNumber, distance: ${distanceFromCamera.toStringAsFixed(1)}m, conf: ${(confidence * 100).toInt()}%)';
}

/// Face selection criteria weights
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

  Map<String, dynamic> toJson() {
    return {
      'distance_weight': distanceWeight,
      'confidence_weight': confidenceWeight,
      'area_weight': areaWeight,
      'position_weight': positionWeight,
    };
  }
}

/// Enhanced spatial bounds with center coordinates
class EnhancedSpatialBounds {
  final double minX;
  final double maxX;
  final double minY;
  final double maxY;
  final double centerX;
  final double centerY;

  const EnhancedSpatialBounds({
    required this.minX,
    required this.maxX,
    required this.minY,
    required this.maxY,
    required this.centerX,
    required this.centerY,
  });

  factory EnhancedSpatialBounds.fromJson(Map<String, dynamic> json) {
    return EnhancedSpatialBounds(
      minX: (json['min_x'] ?? 0.0).toDouble(),
      maxX: (json['max_x'] ?? 0.0).toDouble(),
      minY: (json['min_y'] ?? 0.0).toDouble(),
      maxY: (json['max_y'] ?? 0.0).toDouble(),
      centerX: (json['center_x'] ?? 0.0).toDouble(),
      centerY: (json['center_y'] ?? 0.0).toDouble(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'min_x': minX,
      'max_x': maxX,
      'min_y': minY,
      'max_y': maxY,
      'center_x': centerX,
      'center_y': centerY,
    };
  }

  double get width => maxX - minX;
  double get height => maxY - minY;
}

/// Enhanced temporal span information
class EnhancedTemporalSpan {
  final int startFrame;
  final int endFrame;
  final double durationSeconds;
  final int frameCount;

  const EnhancedTemporalSpan({
    required this.startFrame,
    required this.endFrame,
    required this.durationSeconds,
    required this.frameCount,
  });

  factory EnhancedTemporalSpan.fromJson(Map<String, dynamic> json) {
    return EnhancedTemporalSpan(
      startFrame: json['start_frame'] ?? 0,
      endFrame: json['end_frame'] ?? 0,
      durationSeconds: (json['duration_seconds'] ?? 0.0).toDouble(),
      frameCount: json['frame_count'] ?? 0,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'start_frame': startFrame,
      'end_frame': endFrame,
      'duration_seconds': durationSeconds,
      'frame_count': frameCount,
    };
  }
}

/// Enhanced movement tracking (for future route visualization)
class EnhancedMovementTracking {
  final List<RoutePoint> routePoints;
  final MovementStatistics movementStatistics;

  const EnhancedMovementTracking({
    required this.routePoints,
    required this.movementStatistics,
  });

  factory EnhancedMovementTracking.fromJson(Map<String, dynamic> json) {
    return EnhancedMovementTracking(
      routePoints: (json['route_points'] as List?)
          ?.map((e) => RoutePoint.fromJson(e))
          .toList() ?? [],
      movementStatistics: MovementStatistics.fromJson(json['movement_statistics'] ?? {}),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'route_points': routePoints.map((e) => e.toJson()).toList(),
      'movement_statistics': movementStatistics.toJson(),
    };
  }
}

/// Route point for movement tracking
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
      distanceFromCamera: json['distance_from_camera']?.toDouble(),
      velocityX: (json['velocity_x'] ?? 0.0).toDouble(),
      velocityY: (json['velocity_y'] ?? 0.0).toDouble(),
      velocityMagnitude: (json['velocity_magnitude'] ?? 0.0).toDouble(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'sequence_number': sequenceNumber,
      'frame_number': frameNumber,
      'timestamp': timestamp,
      'center_x': centerX,
      'center_y': centerY,
      'distance_from_camera': distanceFromCamera,
      'velocity_x': velocityX,
      'velocity_y': velocityY,
      'velocity_magnitude': velocityMagnitude,
    };
  }
}

/// Movement statistics for person tracking
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

  Map<String, dynamic> toJson() {
    return {
      'total_route_points': totalRoutePoints,
      'total_distance_pixels': totalDistancePixels,
      'average_velocity': averageVelocity,
      'max_velocity': maxVelocity,
      'time_in_frame_seconds': timeInFrameSeconds,
    };
  }
}

/// Enhanced quality metrics for person group analysis
class EnhancedQualityMetrics {
  final double averageQuality;
  final double maxQuality;
  final double minQuality;
  final double qualityVariance;

  const EnhancedQualityMetrics({
    required this.averageQuality,
    required this.maxQuality,
    required this.minQuality,
    required this.qualityVariance,
  });

  factory EnhancedQualityMetrics.fromJson(Map<String, dynamic> json) {
    return EnhancedQualityMetrics(
      averageQuality: (json['average_quality'] ?? 0.0).toDouble(),
      maxQuality: (json['max_quality'] ?? 0.0).toDouble(),
      minQuality: (json['min_quality'] ?? 0.0).toDouble(),
      qualityVariance: (json['quality_variance'] ?? 0.0).toDouble(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'average_quality': averageQuality,
      'max_quality': maxQuality,
      'min_quality': minQuality,
      'quality_variance': qualityVariance,
    };
  }
}

// =============================================================================
// ENHANCED PPL THREAD RESPONSE MODEL
// =============================================================================

/// Enhanced PPL Thread response with detailed person groups
class EnhancedPPLThreadResponse {
  final bool success;
  final String mediaId;
  final int totalPersons;
  final int totalFaces;
  final String status;
  final String message;
  final List<EnhancedPersonObjectGroup> personGroups;
  final String groupingAlgorithm;
  final double iouThreshold;
  final double processingTimeMs;
  final String sessionUuid;

  const EnhancedPPLThreadResponse({
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

  factory EnhancedPPLThreadResponse.fromJson(Map<String, dynamic> json) {
    return EnhancedPPLThreadResponse(
      success: json['success'] ?? false,
      mediaId: json['media_id'] ?? '',
      totalPersons: json['total_persons'] ?? 0,
      totalFaces: json['total_faces'] ?? 0,
      status: json['status'] ?? '',
      message: json['message'] ?? '',
      personGroups: (json['person_groups'] as List?)
          ?.map((e) => EnhancedPersonObjectGroup.fromJson(e))
          .toList() ?? [],
      groupingAlgorithm: json['grouping_algorithm'] ?? '',
      iouThreshold: (json['iou_threshold'] ?? 0.0).toDouble(),
      processingTimeMs: (json['processing_time_ms'] ?? 0.0).toDouble(),
      sessionUuid: json['session_uuid'] ?? '',
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'success': success,
      'media_id': mediaId,
      'total_persons': totalPersons,
      'total_faces': totalFaces,
      'status': status,
      'message': message,
      'person_groups': personGroups.map((e) => e.toJson()).toList(),
      'grouping_algorithm': groupingAlgorithm,
      'iou_threshold': iouThreshold,
      'processing_time_ms': processingTimeMs,
      'session_uuid': sessionUuid,
    };
  }

  @override
  String toString() => 'EnhancedPPLThreadResponse(persons: $totalPersons, faces: $totalFaces, status: $status)';
}

// =============================================================================
// DISTANCE-BASED COLOR CODING UTILITY
// =============================================================================

/// Utility class for distance-based color coding
class DistanceColorCoding {
  /// Get color based on distance using the PPL Meta standard color scheme
  static Color getDistanceColor(double distance) {
    if (distance < 10) return const Color(0xFFE53E3E); // Red - Very close (< 10m)
    if (distance < 20) return const Color(0xFFFF8C00); // Orange - Close (10-20m) 
    if (distance < 30) return const Color(0xFFFFD700); // Yellow - Medium (20-30m)
    if (distance < 50) return const Color(0xFF38A169); // Green - Far (30-50m)
    return const Color(0xFF3182CE); // Blue - Very far (> 50m)
  }

  /// Get color description for accessibility
  static String getDistanceDescription(double distance) {
    if (distance < 10) return 'Very Close';
    if (distance < 20) return 'Close';
    if (distance < 30) return 'Medium';
    if (distance < 50) return 'Far';
    return 'Very Far';
  }

  /// Get color name for UI display
  static String getColorName(double distance) {
    if (distance < 10) return 'Red';
    if (distance < 20) return 'Orange';
    if (distance < 30) return 'Yellow';
    if (distance < 50) return 'Green';
    return 'Blue';
  }
}