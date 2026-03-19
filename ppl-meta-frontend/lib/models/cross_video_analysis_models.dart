/// Cross-video individual analysis data models
/// 
/// These models support the cross-video tracking feature where individuals
/// are tracked across multiple videos with aggregated analysis data.

import 'package:flutter/foundation.dart';

/// Context for cross-video individual analysis navigation
class CrossVideoAnalysisContext {
  final List<String> individualUuids;
  final String sessionUuid;
  final Map<String, dynamic> sessionData;
  
  CrossVideoAnalysisContext({
    required this.individualUuids,
    required this.sessionUuid,
    required this.sessionData,
  });
  
  /// Get total videos from session data
  int get totalVideos => sessionData['total_videos'] as int? ?? 0;
  
  /// Get individuals count from session data
  int get individualsCount => sessionData['individuals_found'] as int? ?? 0;
  
  /// Get collections from session data
  List<String> get collections => 
      (sessionData['collections'] as List?)?.cast<String>() ?? [];
}

/// Demographics data for an individual
class Demographics {
  final String? gender;
  final double? genderConfidence;
  final int? ageMin;
  final int? ageMax;
  final double? ageMean;
  final double? ageConfidence;

  Demographics({
    this.gender,
    this.genderConfidence,
    this.ageMin,
    this.ageMax,
    this.ageMean,
    this.ageConfidence,
  });

  factory Demographics.fromJson(Map<String, dynamic> json) {
    return Demographics(
      gender: json['gender'] as String?,
      genderConfidence: (json['gender_confidence'] as num?)?.toDouble(),
      ageMin: json['age_min'] as int?,
      ageMax: json['age_max'] as int?,
      ageMean: (json['age_mean'] as num?)?.toDouble(),
      ageConfidence: (json['age_confidence'] as num?)?.toDouble(),
    );
  }
}

/// Gender breakdown statistics
class GenderBreakdown {
  final int male;
  final int female;
  final int unknown;

  GenderBreakdown({
    required this.male,
    required this.female,
    required this.unknown,
  });

  factory GenderBreakdown.fromJson(Map<String, dynamic> json) {
    return GenderBreakdown(
      male: json['male'] as int? ?? 0,
      female: json['female'] as int? ?? 0,
      unknown: json['unknown'] as int? ?? 0,
    );
  }
  
  /// Get total count of individuals with known gender
  int get totalKnown => male + female;
  
  /// Get total count including unknown
  int get total => male + female + unknown;
}

/// Age statistics
class AgeStatistics {
  final double? averageAge;
  final double? minAge;
  final double? maxAge;
  final double? ageRange;

  AgeStatistics({
    this.averageAge,
    this.minAge,
    this.maxAge,
    this.ageRange,
  });

  factory AgeStatistics.fromJson(Map<String, dynamic> json) {
    return AgeStatistics(
      averageAge: (json['average_age'] as num?)?.toDouble(),
      minAge: (json['min_age'] as num?)?.toDouble(),
      maxAge: (json['max_age'] as num?)?.toDouble(),
      ageRange: (json['age_range'] as num?)?.toDouble(),
    );
  }
}

/// Aggregate demographics across all individuals
class AggregateDemographics {
  final int totalIndividuals;
  final GenderBreakdown genderBreakdown;
  final AgeStatistics ageStatistics;

  AggregateDemographics({
    required this.totalIndividuals,
    required this.genderBreakdown,
    required this.ageStatistics,
  });

  factory AggregateDemographics.fromJson(Map<String, dynamic> json) {
    return AggregateDemographics(
      totalIndividuals: json['total_individuals'] as int,
      genderBreakdown: GenderBreakdown.fromJson(json['gender_breakdown'] as Map<String, dynamic>),
      ageStatistics: AgeStatistics.fromJson(json['age_statistics'] as Map<String, dynamic>),
    );
  }
}

/// Aggregated individual analysis data from vmeta backend (Phase 6)
/// 
/// This model represents the complete analysis of an individual across
/// multiple videos with all appearances and temporal metrics.
class AggregatedIndividualAnalysis {
  final String individualUuid;
  final String individualId;
  final String sessionUuid;
  final int totalAppearances;
  final int uniqueVideos;
  final DateTime firstSeen;
  final DateTime lastSeen;
  final double totalDurationSeconds;
  final double averageConfidence;
  final double? averageRouteVelocity;
  final Demographics? demographics;
  final AggregateDemographics? aggregateDemographics;
  final List<IndividualAppearance> appearances;
  final List<String> personObjectUuids;
  final DateTime analysisTimestamp;
  
  // Hierarchical merge fields (v2.19.84)
  final bool isSuperIndividual;
  final int mergedMVRCount;
  final List<MergedMVRPerson> mergedMVRPeople;
  final String? bestFaceThumbnail;
  
  // Individual naming (v2.21.0)
  final String? name;
  final DateTime? nameUpdatedAt;
  final String? nameUpdatedBy;
  
  AggregatedIndividualAnalysis({
    required this.individualUuid,
    required this.individualId,
    required this.sessionUuid,
    required this.totalAppearances,
    required this.uniqueVideos,
    required this.firstSeen,
    required this.lastSeen,
    required this.totalDurationSeconds,
    required this.averageConfidence,
    this.averageRouteVelocity,
    this.demographics,
    this.aggregateDemographics,
    required this.appearances,
    required this.personObjectUuids,
    required this.analysisTimestamp,
    this.isSuperIndividual = false,
    this.mergedMVRCount = 1,
    this.mergedMVRPeople = const [],
    this.bestFaceThumbnail,
    this.name,
    this.nameUpdatedAt,
    this.nameUpdatedBy,
  });
  
  factory AggregatedIndividualAnalysis.fromJson(Map<String, dynamic> json) {
    // Debug logging for name field parsing
    debugPrint('═══ MODEL PARSING DEBUG ═══');
    debugPrint('Parsing UUID: ${json['individual_uuid']}');
    debugPrint('Name from JSON: ${json['name']}');
    debugPrint('Name updated: ${json['name_updated_at']}');
    debugPrint('Updated by: ${json['name_updated_by']}');
    debugPrint('═══════════════════════════');
    
    return AggregatedIndividualAnalysis(
      individualUuid: json['individual_uuid'] as String,
      individualId: json['individual_id'] as String,
      sessionUuid: json['session_uuid'] as String,
      totalAppearances: json['total_appearances'] as int,
      uniqueVideos: json['unique_videos'] as int,
      firstSeen: DateTime.parse(json['first_seen'] as String),
      lastSeen: DateTime.parse(json['last_seen'] as String),
      totalDurationSeconds: (json['total_duration_seconds'] as num).toDouble(),
      averageConfidence: (json['average_confidence'] as num).toDouble(),
      averageRouteVelocity: (json['average_route_velocity'] as num?)?.toDouble(),
      demographics: json['demographics'] != null 
          ? Demographics.fromJson(json['demographics'] as Map<String, dynamic>)
          : null,
      aggregateDemographics: json['aggregate_demographics'] != null
          ? AggregateDemographics.fromJson(json['aggregate_demographics'] as Map<String, dynamic>)
          : null,
      appearances: (json['appearances'] as List)
          .map((app) => IndividualAppearance.fromJson(app as Map<String, dynamic>))
          .toList(),
      personObjectUuids: (json['person_object_uuids'] as List)
          .map((uuid) => uuid as String)
          .toList(),
      analysisTimestamp: DateTime.parse(json['analysis_timestamp'] as String),
      isSuperIndividual: json['is_super_individual'] as bool? ?? false,
      mergedMVRCount: json['merged_mvr_count'] as int? ?? 1,
      mergedMVRPeople: (json['merged_mvr_people'] as List?)
          ?.map((mvr) => MergedMVRPerson.fromJson(mvr as Map<String, dynamic>))
          .toList() ?? [],
      bestFaceThumbnail: json['best_face_thumbnail'] as String?,
      name: json['name'] as String?,
      nameUpdatedAt: json['name_updated_at'] != null 
          ? DateTime.parse(json['name_updated_at'] as String)
          : null,
      nameUpdatedBy: json['name_updated_by'] as String?,
    );
  }
  
  /// Factory constructor for super-individual hierarchy response (v2.19.85)
  /// 
  /// Creates an AggregatedIndividualAnalysis from the hierarchical merge endpoint
  /// response. This represents a merged super-individual with constituent MVR people.
  /// 
  /// Parameters:
  /// - superIndividualUuid: UUID of the super-individual
  /// - hierarchyData: Response from GET /super-individual/{uuid}/hierarchy
  /// - sessionUuid: Session UUID for this analysis
  /// - startTime: Optional start time filter
  /// - endTime: Optional end time filter
  factory AggregatedIndividualAnalysis.fromSuperIndividual({
    required String superIndividualUuid,
    required Map<String, dynamic> hierarchyData,
    required String sessionUuid,
    DateTime? startTime,
    DateTime? endTime,
  }) {
    final superIndividual = hierarchyData['super_individual'] as Map<String, dynamic>;
    final mergedMVR = (hierarchyData['merged_mvr_people'] as List?)
        ?.map((mvr) => MergedMVRPerson.fromJson(mvr as Map<String, dynamic>))
        .toList() ?? [];
    final allIndividuals = hierarchyData['all_individuals'] as List;
    
    // Filter individuals by date range if provided
    var filteredIndividuals = allIndividuals;
    if (startTime != null || endTime != null) {
      filteredIndividuals = allIndividuals.where((ind) {
        final indData = ind as Map<String, dynamic>;
        if (startTime != null && indData['first_seen_timestamp'] != null) {
          final firstSeen = DateTime.parse(indData['first_seen_timestamp'] as String);
          if (firstSeen.isBefore(startTime)) return false;
        }
        if (endTime != null && indData['last_seen_timestamp'] != null) {
          final lastSeen = DateTime.parse(indData['last_seen_timestamp'] as String);
          if (lastSeen.isAfter(endTime)) return false;
        }
        return true;
      }).toList();
    }
    
    // Convert individuals to appearances
    final appearances = filteredIndividuals
        .map((ind) => IndividualAppearance.fromIndividual(ind as Map<String, dynamic>))
        .toList();
    
    // Extract unique video UUIDs from all individuals
    final uniqueVideoUuids = filteredIndividuals
        .map((ind) => (ind as Map<String, dynamic>)['video_uuid'] as String?)
        .where((uuid) => uuid != null)
        .toSet()
        .length;
    
    // Extract demographics from super-individual
    // Always create demographics object to ensure we have the data if it exists
    Demographics? demographics;
    final hasAnyDemographics = superIndividual['gender'] != null || 
                               superIndividual['age_min'] != null ||
                               superIndividual['age_max'] != null;
    
    if (hasAnyDemographics) {
      demographics = Demographics(
        gender: superIndividual['gender'] as String?,
        genderConfidence: (superIndividual['gender_confidence'] as num?)?.toDouble(),
        ageMin: superIndividual['age_min'] as int?,
        ageMax: superIndividual['age_max'] as int?,
        ageMean: superIndividual['age_mean'] != null 
            ? (superIndividual['age_mean'] as num?)?.toDouble()
            : (superIndividual['age_min'] != null && superIndividual['age_max'] != null)
                ? ((superIndividual['age_min']! + superIndividual['age_max']!) / 2.0)
                : null,
        ageConfidence: (superIndividual['age_confidence'] as num?)?.toDouble(),
      );
    }
    
    // Calculate first/last seen from filtered individuals
    DateTime? firstSeen;
    DateTime? lastSeen;
    for (final ind in filteredIndividuals) {
      final indData = ind as Map<String, dynamic>;
      if (indData['first_seen_timestamp'] != null) {
        final ts = DateTime.parse(indData['first_seen_timestamp'] as String);
        if (firstSeen == null || ts.isBefore(firstSeen)) {
          firstSeen = ts;
        }
      }
      if (indData['last_seen_timestamp'] != null) {
        final ts = DateTime.parse(indData['last_seen_timestamp'] as String);
        if (lastSeen == null || ts.isAfter(lastSeen)) {
          lastSeen = ts;
        }
      }
    }
    
    return AggregatedIndividualAnalysis(
      individualUuid: superIndividualUuid,
      individualId: superIndividualUuid,
      sessionUuid: sessionUuid,
      totalAppearances: filteredIndividuals.length,
      uniqueVideos: uniqueVideoUuids,
      firstSeen: firstSeen ?? DateTime.parse(superIndividual['created_at'] as String),
      lastSeen: lastSeen ?? DateTime.now(),
      totalDurationSeconds: 0.0, // Calculate from appearances if needed
      averageConfidence: (superIndividual['confidence_score'] as num?)?.toDouble() ?? 0.0,
      demographics: demographics,
      appearances: appearances,
      personObjectUuids: filteredIndividuals
          .map((ind) => (ind as Map<String, dynamic>)['individual_uuid'] as String)
          .toList(),
      analysisTimestamp: DateTime.now(),
      isSuperIndividual: mergedMVR.isNotEmpty,
      mergedMVRCount: (hierarchyData['mvr_count'] as int?) ?? 1,
      mergedMVRPeople: mergedMVR,
      bestFaceThumbnail: superIndividual['featured_person_object_uuid'] as String?,
      name: superIndividual['name'] as String?,
      nameUpdatedAt: superIndividual['name_updated_at'] != null
          ? DateTime.parse(superIndividual['name_updated_at'] as String)
          : null,
      nameUpdatedBy: superIndividual['name_updated_by'] as String?,
    );
  }
  
  /// Check if this is a standalone individual (not merged)
  bool get isStandalone => !isSuperIndividual && mergedMVRCount == 1;
  
  /// Get total duration in a human-readable format
  String get formattedDuration {
    final days = (totalDurationSeconds / 86400).floor();
    final hours = ((totalDurationSeconds % 86400) / 3600).floor();
    final minutes = ((totalDurationSeconds % 3600) / 60).floor();
    
    if (days > 0) {
      return '$days days, $hours hours';
    } else if (hours > 0) {
      return '$hours hours, $minutes minutes';
    } else {
      return '$minutes minutes';
    }
  }
  
  /// Legacy compatibility: map to totalVideos
  int get totalVideos => uniqueVideos;
  
  /// Legacy compatibility: map to confidenceScore
  double get confidenceScore => averageConfidence;
}

/// Individual appearance in a single video (from Phase 6 response)
class IndividualAppearance {
  final String individualUuid;
  final String videoUuid;
  final String personObjectUuid;
  final DateTime startTimestamp;
  final DateTime endTimestamp;
  final List<double>? entryBbox;
  final List<double>? exitBbox;
  final double confidenceScore;
  final String? cameraId;  // Camera/collection ID
  final String? cameraName;  // Camera/collection name
  
  IndividualAppearance({
    required this.individualUuid,
    required this.videoUuid,
    required this.personObjectUuid,
    required this.startTimestamp,
    required this.endTimestamp,
    this.entryBbox,
    this.exitBbox,
    required this.confidenceScore,
    this.cameraId,
    this.cameraName,
  });
  
  factory IndividualAppearance.fromJson(Map<String, dynamic> json) {
    return IndividualAppearance(
      individualUuid: json['individual_uuid'] as String,
      videoUuid: json['video_uuid'] as String,
      personObjectUuid: json['person_object_uuid'] as String,
      startTimestamp: DateTime.parse(json['start_timestamp'] as String),
      endTimestamp: DateTime.parse(json['end_timestamp'] as String),
      entryBbox: (json['entry_bbox'] as List?)?.map((e) => (e as num).toDouble()).toList(),
      exitBbox: (json['exit_bbox'] as List?)?.map((e) => (e as num).toDouble()).toList(),
      confidenceScore: (json['confidence_score'] as num).toDouble(),
      cameraId: json['camera_id'] as String?,
      cameraName: json['camera_name'] as String?,
    );
  }
  
  /// Factory constructor from individual data (for super-individual hierarchy)
  factory IndividualAppearance.fromIndividual(Map<String, dynamic> json) {
    return IndividualAppearance(
      individualUuid: json['individual_uuid'] as String,
      videoUuid: json['video_uuid'] as String? ?? '',
      personObjectUuid: json['individual_uuid'] as String, // Use individual_uuid if person_object not available
      startTimestamp: json['first_seen_timestamp'] != null 
          ? DateTime.parse(json['first_seen_timestamp'] as String)
          : DateTime.now(),
      endTimestamp: json['last_seen_timestamp'] != null
          ? DateTime.parse(json['last_seen_timestamp'] as String)
          : DateTime.now(),
      confidenceScore: 0.0, // Not available in this format
    );
  }
  
  /// Get duration of this appearance in seconds
  double get durationSeconds => endTimestamp.difference(startTimestamp).inSeconds.toDouble();
  
  /// Get formatted duration
  String get formattedDuration {
    final seconds = durationSeconds.toInt();
    if (seconds < 60) {
      return '$seconds seconds';
    } else {
      final minutes = (seconds / 60).floor();
      final remainingSeconds = seconds % 60;
      return '$minutes min ${remainingSeconds}s';
    }
  }
}

/// Person object data from a single video appearance
class PersonObjectData {
  final String personUuid;
  final String videoUuid;
  final String personId;
  final int faceCount;
  final List<FaceData> faces;
  final List<RoutePoint> routes;
  final Map<String, dynamic> qualityMetrics;
  final DateTime timestamp;
  
  PersonObjectData({
    required this.personUuid,
    required this.videoUuid,
    required this.personId,
    required this.faceCount,
    required this.faces,
    required this.routes,
    required this.qualityMetrics,
    required this.timestamp,
  });
  
  factory PersonObjectData.fromJson(Map<String, dynamic> json) {
    return PersonObjectData(
      personUuid: json['person_uuid'] as String,
      videoUuid: json['video_uuid'] as String,
      personId: json['person_id'] as String,
      faceCount: json['face_count'] as int,
      faces: (json['faces'] as List)
          .map((face) => FaceData.fromJson(face as Map<String, dynamic>))
          .toList(),
      routes: (json['routes'] as List)
          .map((route) => RoutePoint.fromJson(route as Map<String, dynamic>))
          .toList(),
      qualityMetrics: json['quality_metrics'] as Map<String, dynamic>,
      timestamp: DateTime.parse(json['timestamp'] as String),
    );
  }
  
  /// Get average sharpness from quality metrics
  double get averageSharpness => 
      (qualityMetrics['average_sharpness'] as num?)?.toDouble() ?? 0.0;
  
  /// Get average brightness from quality metrics
  double get averageBrightness => 
      (qualityMetrics['average_brightness'] as num?)?.toDouble() ?? 0.0;
  
  /// Get average confidence from quality metrics
  double get averageConfidence => 
      (qualityMetrics['average_confidence'] as num?)?.toDouble() ?? 0.0;
  
  /// Calculate overall quality score (matches backend algorithm)
  double get qualityScore {
    return (averageSharpness * 0.4) + 
           (averageBrightness * 0.3) + 
           (averageConfidence * 0.3);
  }
  
  /// Get best quality face from this person object
  FaceData? get bestQualityFace {
    if (faces.isEmpty) return null;
    
    var bestFace = faces.first;
    var bestScore = _calculateFaceQualityScore(bestFace);
    
    for (var face in faces.skip(1)) {
      final score = _calculateFaceQualityScore(face);
      if (score > bestScore) {
        bestScore = score;
        bestFace = face;
      }
    }
    
    return bestFace;
  }
  
  /// Calculate quality score for a face (matches backend algorithm)
  double _calculateFaceQualityScore(FaceData face) {
    final quality = face.qualityMetrics;
    var score = 0.0;
    
    // Sharpness (40%)
    if (quality['sharpness'] != null) {
      score += (quality['sharpness'] as num).toDouble() * 0.4;
    }
    
    // Brightness (20%)
    if (quality['brightness'] != null) {
      score += (quality['brightness'] as num).toDouble() * 0.2;
    }
    
    // Face size (30%)
    if (face.bbox.length >= 4) {
      final width = face.bbox[2] - face.bbox[0];
      final height = face.bbox[3] - face.bbox[1];
      final area = width * height;
      final normalizedSize = (area / (1920.0 * 1080.0)).clamp(0.0, 1.0);
      score += normalizedSize * 0.3;
    }
    
    // Confidence (10%)
    score += face.confidence * 0.1;
    
    return score;
  }
}

/// Route point data with video context
class RoutePoint {
  final double x;
  final double y;
  final String timestamp;
  final String videoUuid;
  final double confidence;
  
  RoutePoint({
    required this.x,
    required this.y,
    required this.timestamp,
    required this.videoUuid,
    this.confidence = 1.0,
  });
  
  factory RoutePoint.fromJson(Map<String, dynamic> json) {
    return RoutePoint(
      x: (json['x'] as num).toDouble(),
      y: (json['y'] as num).toDouble(),
      timestamp: json['timestamp'] as String,
      videoUuid: json['video_uuid'] as String,
      confidence: (json['confidence'] as num?)?.toDouble() ?? 1.0,
    );
  }
  
  /// Get DateTime from timestamp string
  DateTime get dateTime => DateTime.parse(timestamp);
  
  /// Convert to JSON
  Map<String, dynamic> toJson() {
    return {
      'x': x,
      'y': y,
      'timestamp': timestamp,
      'video_uuid': videoUuid,
      'confidence': confidence,
    };
  }
}

/// Face data model for cross-video analysis
class FaceData {
  final String faceId;
  final List<double> bbox;
  final double confidence;
  final Map<String, dynamic> qualityMetrics;
  final String? imageUrl;
  
  FaceData({
    required this.faceId,
    required this.bbox,
    required this.confidence,
    required this.qualityMetrics,
    this.imageUrl,
  });
  
  factory FaceData.fromJson(Map<String, dynamic> json) {
    return FaceData(
      faceId: json['face_id'] as String,
      bbox: (json['bbox'] as List).map((v) => (v as num).toDouble()).toList(),
      confidence: (json['confidence'] as num).toDouble(),
      qualityMetrics: json['quality_metrics'] as Map<String, dynamic>,
      imageUrl: json['image_url'] as String?,
    );
  }
  
  /// Get sharpness from quality metrics
  double get sharpness => 
      (qualityMetrics['sharpness'] as num?)?.toDouble() ?? 0.0;
  
  /// Get brightness from quality metrics
  double get brightness => 
      (qualityMetrics['brightness'] as num?)?.toDouble() ?? 0.0;
  
  /// Get face width
  double get width => bbox.length >= 4 ? bbox[2] - bbox[0] : 0.0;
  
  /// Get face height
  double get height => bbox.length >= 4 ? bbox[3] - bbox[1] : 0.0;
  
  /// Get face area
  double get area => width * height;
  
  /// Calculate quality score for this face (matches backend algorithm)
  double get qualityScore {
    var score = 0.0;
    
    // Sharpness (40%)
    score += sharpness * 0.4;
    
    // Brightness (20%)
    score += brightness * 0.2;
    
    // Face size (30%)
    final normalizedSize = (area / (1920.0 * 1080.0)).clamp(0.0, 1.0);
    score += normalizedSize * 0.3;
    
    // Confidence (10%)
    score += confidence * 0.1;
    
    return score;
  }
  
  /// Convert to JSON
  Map<String, dynamic> toJson() {
    return {
      'face_id': faceId,
      'bbox': bbox,
      'confidence': confidence,
      'quality_metrics': qualityMetrics,
      if (imageUrl != null) 'image_url': imageUrl,
    };
  }
}
/// Merged MVR person data (v2.19.84)
/// 
/// Represents an MVR person that was merged into a super-individual,
/// with similarity scores and merge metadata.
class MergedMVRPerson {
  final String mvrPeopleUuid;
  final String featuredIndividualUuid;
  final double qualityScore;
  final double confidenceScore;
  final String? gender;
  final int? ageMin;
  final int? ageMax;
  final DateTime? orphanedAt;
  final String? mergedIntoMvrUuid;
  final double similarityToFeatured;
  
  // Individual naming (v2.21.0)
  final String? name;
  final DateTime? nameUpdatedAt;
  final String? nameUpdatedBy;
  
  MergedMVRPerson({
    required this.mvrPeopleUuid,
    required this.featuredIndividualUuid,
    required this.qualityScore,
    required this.confidenceScore,
    this.gender,
    this.ageMin,
    this.ageMax,
    this.orphanedAt,
    this.mergedIntoMvrUuid,
    this.similarityToFeatured = 0.0,
    this.name,
    this.nameUpdatedAt,
    this.nameUpdatedBy,
  });
  
  factory MergedMVRPerson.fromJson(Map<String, dynamic> json) {
    return MergedMVRPerson(
      mvrPeopleUuid: json['mvr_people_uuid'] as String,
      featuredIndividualUuid: json['featured_individual_uuid'] as String,
      qualityScore: (json['quality_score'] as num?)?.toDouble() ?? 0.0,
      confidenceScore: (json['confidence_score'] as num?)?.toDouble() ?? 0.0,
      gender: json['gender'] as String?,
      ageMin: json['age_min'] as int?,
      ageMax: json['age_max'] as int?,
      orphanedAt: json['orphaned_at'] != null 
          ? DateTime.parse(json['orphaned_at'] as String)
          : null,
      mergedIntoMvrUuid: json['merged_into_mvr_uuid'] as String?,
      similarityToFeatured: (json['similarity_to_featured'] as num?)?.toDouble() ?? 0.0,
      name: json['name'] as String?,
      nameUpdatedAt: json['name_updated_at'] != null
          ? DateTime.parse(json['name_updated_at'] as String)
          : null,
      nameUpdatedBy: json['name_updated_by'] as String?,
    );
  }
  
  /// Get age range as string
  String get ageRange {
    if (ageMin == null || ageMax == null) return 'Unknown';
    return '$ageMin-$ageMax';
  }
  
  /// Get formatted similarity percentage
  String get formattedSimilarity {
    return '${(similarityToFeatured * 100).toStringAsFixed(1)}%';
  }
  
  /// Convert to JSON
  Map<String, dynamic> toJson() {
    return {
      'mvr_people_uuid': mvrPeopleUuid,
      'featured_individual_uuid': featuredIndividualUuid,
      'quality_score': qualityScore,
      'confidence_score': confidenceScore,
      if (gender != null) 'gender': gender,
      if (ageMin != null) 'age_min': ageMin,
      if (ageMax != null) 'age_max': ageMax,
      if (orphanedAt != null) 'orphaned_at': orphanedAt!.toIso8601String(),
      if (mergedIntoMvrUuid != null) 'merged_into_mvr_uuid': mergedIntoMvrUuid,
      'similarity_to_featured': similarityToFeatured,
    };
  }
}