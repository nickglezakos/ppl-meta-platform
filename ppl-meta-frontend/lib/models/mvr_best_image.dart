// MVR Best Image Response Models
// Data models for best face and frame images

class BestFaceData {
  final String imageUrl;
  final double qualityScore;
  final String personObjectUuid;
  final String videoUuid;
  final String timestamp;
  final String sourceMvrUuid;
  final List<dynamic>? bbox;  // Changed from Map to List to match backend format [x1, y1, x2, y2]
  final Map<String, dynamic>? faceData;

  BestFaceData({
    required this.imageUrl,
    required this.qualityScore,
    required this.personObjectUuid,
    required this.videoUuid,
    required this.timestamp,
    required this.sourceMvrUuid,
    this.bbox,
    this.faceData,
  });

  factory BestFaceData.fromJson(Map<String, dynamic> json) {
    return BestFaceData(
      imageUrl: json['image_url'] as String,
      qualityScore: (json['quality_score'] as num).toDouble(),
      personObjectUuid: json['person_object_uuid'] as String,
      videoUuid: json['video_uuid'] as String,
      timestamp: json['timestamp'] as String,
      sourceMvrUuid: json['source_mvr_uuid'] as String,
      bbox: json['bbox'] as List<dynamic>?,  // Parse as List, not Map
      faceData: json['face_data'] as Map<String, dynamic>?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'image_url': imageUrl,
      'quality_score': qualityScore,
      'person_object_uuid': personObjectUuid,
      'video_uuid': videoUuid,
      'timestamp': timestamp,
      'source_mvr_uuid': sourceMvrUuid,
      if (bbox != null) 'bbox': bbox,
      if (faceData != null) 'face_data': faceData,
    };
  }
}

class FrameImageData {
  final String imageUrl;
  final String personObjectUuid;
  final String videoUuid;
  final String timestamp;

  FrameImageData({
    required this.imageUrl,
    required this.personObjectUuid,
    required this.videoUuid,
    required this.timestamp,
  });

  factory FrameImageData.fromJson(Map<String, dynamic> json) {
    return FrameImageData(
      imageUrl: json['image_url'] as String,
      personObjectUuid: json['person_object_uuid'] as String,
      videoUuid: json['video_uuid'] as String,
      timestamp: json['timestamp'] as String,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'image_url': imageUrl,
      'person_object_uuid': personObjectUuid,
      'video_uuid': videoUuid,
      'timestamp': timestamp,
    };
  }
}

class BestImageMetadata {
  final int totalAppearancesChecked;
  final int totalMvrChecked;
  final bool cacheHit;
  final int processingTimeMs;
  final List<String> fallbackImageUrls;

  BestImageMetadata({
    required this.totalAppearancesChecked,
    required this.totalMvrChecked,
    required this.cacheHit,
    required this.processingTimeMs,
    this.fallbackImageUrls = const [],
  });

  factory BestImageMetadata.fromJson(Map<String, dynamic> json) {
    return BestImageMetadata(
      totalAppearancesChecked: json['total_appearances_checked'] as int,
      totalMvrChecked: json['total_mvr_checked'] as int,
      cacheHit: json['cache_hit'] as bool,
      processingTimeMs: json['processing_time_ms'] as int,
      fallbackImageUrls: (json['fallback_image_urls'] as List<dynamic>?)
              ?.map((item) => item.toString())
              .where((item) => item.isNotEmpty)
              .toList() ??
          const [],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'total_appearances_checked': totalAppearancesChecked,
      'total_mvr_checked': totalMvrChecked,
      'cache_hit': cacheHit,
      'processing_time_ms': processingTimeMs,
      if (fallbackImageUrls.isNotEmpty) 'fallback_image_urls': fallbackImageUrls,
    };
  }
}

class BestImageResponse {
  final String mvrPeopleUuid;
  final bool isSuperIndividual;
  final BestFaceData? bestFace;
  final FrameImageData? frameImage;
  final BestImageMetadata metadata;

  BestImageResponse({
    required this.mvrPeopleUuid,
    required this.isSuperIndividual,
    this.bestFace,
    this.frameImage,
    required this.metadata,
  });

  factory BestImageResponse.fromJson(Map<String, dynamic> json) {
    return BestImageResponse(
      mvrPeopleUuid: json['mvr_people_uuid'] as String,
      isSuperIndividual: json['is_super_individual'] as bool,
      bestFace: json['best_face'] != null
          ? BestFaceData.fromJson(json['best_face'] as Map<String, dynamic>)
          : null,
      frameImage: json['frame_image'] != null
          ? FrameImageData.fromJson(json['frame_image'] as Map<String, dynamic>)
          : null,
      metadata: BestImageMetadata.fromJson(json['metadata'] as Map<String, dynamic>),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'mvr_people_uuid': mvrPeopleUuid,
      'is_super_individual': isSuperIndividual,
      'best_face': bestFace?.toJson(),
      'frame_image': frameImage?.toJson(),
      'metadata': metadata.toJson(),
    };
  }
}
