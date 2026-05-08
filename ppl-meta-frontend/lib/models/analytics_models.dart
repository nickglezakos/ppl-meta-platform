// MVR Analytics Data Models
// Models for analytics dashboard data structures

/// Demographics breakdown for people detection
class Demographics {
  final int maleCount;
  final int femaleCount;
  final int youngCount;
  final int adultCount;
  final int elderlyCount;
  final double malePercentage;
  final double femalePercentage;
  final double youngPercentage;
  final double adultPercentage;
  final double elderlyPercentage;

  Demographics({
    required this.maleCount,
    required this.femaleCount,
    required this.youngCount,
    required this.adultCount,
    required this.elderlyCount,
    required this.malePercentage,
    required this.femalePercentage,
    required this.youngPercentage,
    required this.adultPercentage,
    required this.elderlyPercentage,
  });

  factory Demographics.fromJson(Map<String, dynamic> json) {
    final gender = json['gender'] as Map<String, dynamic>? ?? {};
    final age = json['age'] as Map<String, dynamic>? ?? {};

    return Demographics(
      maleCount: gender['male'] as int? ?? 0,
      femaleCount: gender['female'] as int? ?? 0,
      youngCount: age['young'] as int? ?? 0,
      adultCount: age['adult'] as int? ?? 0,
      elderlyCount: age['elderly'] as int? ?? 0,
      malePercentage: (gender['male_percentage'] as num?)?.toDouble() ?? 0.0,
      femalePercentage: (gender['female_percentage'] as num?)?.toDouble() ?? 0.0,
      youngPercentage: (age['young_percentage'] as num?)?.toDouble() ?? 0.0,
      adultPercentage: (age['adult_percentage'] as num?)?.toDouble() ?? 0.0,
      elderlyPercentage: (age['elderly_percentage'] as num?)?.toDouble() ?? 0.0,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'gender': {
        'male': maleCount,
        'female': femaleCount,
        'male_percentage': malePercentage,
        'female_percentage': femalePercentage,
      },
      'age': {
        'young': youngCount,
        'adult': adultCount,
        'elderly': elderlyCount,
        'young_percentage': youngPercentage,
        'adult_percentage': adultPercentage,
        'elderly_percentage': elderlyPercentage,
      },
    };
  }

  int get totalCount => maleCount + femaleCount;
  
  bool get isEmpty => totalCount == 0;
}

/// Per-camera analytics data
class CameraAnalytics {
  final String cameraId;
  final String? cameraName;
  final int peopleCount;
  final int videoCount;
  final Demographics? demographics;
  final DateTime? lastDetection;
  final bool cached;

  CameraAnalytics({
    required this.cameraId,
    this.cameraName,
    required this.peopleCount,
    required this.videoCount,
    this.demographics,
    this.lastDetection,
    required this.cached,
  });

  factory CameraAnalytics.fromJson(Map<String, dynamic> json) {
    return CameraAnalytics(
      cameraId: json['camera_id'] as String,
      cameraName: json['camera_name'] as String?,
      peopleCount: json['count'] as int? ?? 0,
      videoCount: json['video_count'] as int? ?? 0,
      demographics: json['demographics'] != null
          ? Demographics.fromJson(json['demographics'] as Map<String, dynamic>)
          : null,
      lastDetection: json['last_detection'] != null
          ? DateTime.parse(json['last_detection'] as String)
          : null,
      cached: json['cached'] as bool? ?? false,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'camera_id': cameraId,
      if (cameraName != null) 'camera_name': cameraName,
      'count': peopleCount,
      'video_count': videoCount,
      if (demographics != null) 'demographics': demographics!.toJson(),
      if (lastDetection != null) 'last_detection': lastDetection!.toIso8601String(),
      'cached': cached,
    };
  }
}

/// Top-level analytics summary
class AnalyticsSummary {
  final int totalPeople;
  final int activeCameras;
  final int totalVideos;
  final DateTime? lastDetection;
  final String timeFilter;
  final Demographics? demographics;
  final List<CameraAnalytics> cameraBreakdown;
  final DateTime generatedAt;
  final bool cached;

  AnalyticsSummary({
    required this.totalPeople,
    required this.activeCameras,
    required this.totalVideos,
    this.lastDetection,
    required this.timeFilter,
    this.demographics,
    this.cameraBreakdown = const [],
    required this.generatedAt,
    required this.cached,
  });

  factory AnalyticsSummary.fromJson(Map<String, dynamic> json) {
    return AnalyticsSummary(
      totalPeople: json['total_people'] as int? ?? 0,
      activeCameras: json['active_cameras'] as int? ?? 0,
      totalVideos: json['total_videos'] as int? ?? 0,
      lastDetection: json['last_detection'] != null
          ? DateTime.parse(json['last_detection'] as String)
          : null,
      timeFilter: json['time_filter'] as String? ?? 'today',
      demographics: json['demographics'] != null
          ? Demographics.fromJson(json['demographics'] as Map<String, dynamic>)
          : null,
      cameraBreakdown: json['camera_breakdown'] != null
          ? (json['camera_breakdown'] as List)
              .map((c) => CameraAnalytics.fromJson(c as Map<String, dynamic>))
              .toList()
          : [],
      generatedAt: json['generated_at'] != null
          ? DateTime.parse(json['generated_at'] as String)
          : DateTime.now(),
      cached: json['cached'] as bool? ?? false,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'total_people': totalPeople,
      'active_cameras': activeCameras,
      'total_videos': totalVideos,
      if (lastDetection != null) 'last_detection': lastDetection!.toIso8601String(),
      'time_filter': timeFilter,
      if (demographics != null) 'demographics': demographics!.toJson(),
      'camera_breakdown': cameraBreakdown.map((c) => c.toJson()).toList(),
      'generated_at': generatedAt.toIso8601String(),
      'cached': cached,
    };
  }
}

/// MVR Quality Metrics Model
/// Represents quality metrics from the MVR tracking system
class MvrQualityMetrics {
  final String timeFilter;
  final String? collectionName;
  final int trackingSessionsCount;
  final int totalIndividuals;
  final int totalMvrPeople;
  final int totalVideosProcessed;
  final int mvrWithQuality;
  final int mvrWithoutQuality;
  final double? averageQuality;
  final double? minQuality;
  final double? maxQuality;
  final double? qualityStdDev;
  final String? qualityGrade;
  final DataCompleteness dataCompleteness;
  final DateTime queryStartTime;
  final DateTime queryEndTime;
  final DateTime queriedAt;

  MvrQualityMetrics({
    required this.timeFilter,
    this.collectionName,
    required this.trackingSessionsCount,
    required this.totalIndividuals,
    required this.totalMvrPeople,
    required this.totalVideosProcessed,
    required this.mvrWithQuality,
    required this.mvrWithoutQuality,
    this.averageQuality,
    this.minQuality,
    this.maxQuality,
    this.qualityStdDev,
    this.qualityGrade,
    required this.dataCompleteness,
    required this.queryStartTime,
    required this.queryEndTime,
    required this.queriedAt,
  });

  factory MvrQualityMetrics.fromJson(Map<String, dynamic> json) {
    return MvrQualityMetrics(
      timeFilter: json['time_filter'] as String,
      collectionName: json['collection_name'] as String?,
      trackingSessionsCount: json['tracking_sessions_count'] as int? ?? 0,
      totalIndividuals: json['total_individuals'] as int? ?? 0,
      totalMvrPeople: json['total_mvr_people'] as int? ?? 0,
      totalVideosProcessed: json['total_videos_processed'] as int? ?? 0,
      mvrWithQuality: json['mvr_with_quality'] as int? ?? 0,
      mvrWithoutQuality: json['mvr_without_quality'] as int? ?? 0,
      averageQuality: (json['average_quality'] as num?)?.toDouble(),
      minQuality: (json['min_quality'] as num?)?.toDouble(),
      maxQuality: (json['max_quality'] as num?)?.toDouble(),
      qualityStdDev: (json['quality_std_dev'] as num?)?.toDouble(),
      qualityGrade: json['quality_grade'] as String?,
      dataCompleteness: DataCompleteness.fromJson(
        json['data_completeness'] as Map<String, dynamic>,
      ),
      // Backend returns 'start_time', 'end_time', 'generated_at' not 'query_*' or 'queried_at'
      queryStartTime: DateTime.parse(json['start_time'] as String),
      queryEndTime: DateTime.parse(json['end_time'] as String),
      queriedAt: DateTime.parse(json['generated_at'] as String),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'time_filter': timeFilter,
      if (collectionName != null) 'collection_name': collectionName,
      'tracking_sessions_count': trackingSessionsCount,
      'total_individuals': totalIndividuals,
      'total_mvr_people': totalMvrPeople,
      'total_videos_processed': totalVideosProcessed,
      'mvr_with_quality': mvrWithQuality,
      'mvr_without_quality': mvrWithoutQuality,
      if (averageQuality != null) 'average_quality': averageQuality,
      if (minQuality != null) 'min_quality': minQuality,
      if (maxQuality != null) 'max_quality': maxQuality,
      if (qualityStdDev != null) 'quality_std_dev': qualityStdDev,
      if (qualityGrade != null) 'quality_grade': qualityGrade,
      'data_completeness': dataCompleteness.toJson(),
      'query_start_time': queryStartTime.toIso8601String(),
      'query_end_time': queryEndTime.toIso8601String(),
      'queried_at': queriedAt.toIso8601String(),
    };
  }

  bool get hasQualityData => mvrWithQuality > 0;
  
  double get qualityCompleteness => dataCompleteness.percentage;
}

/// Data completeness metrics
class DataCompleteness {
  final int total;
  final int withData;
  final int withoutData;
  final double percentage;

  DataCompleteness({
    required this.total,
    required this.withData,
    required this.withoutData,
    required this.percentage,
  });

  factory DataCompleteness.fromJson(Map<String, dynamic> json) {
    final total =
        (json['total'] as num?)?.toInt() ??
        (json['total_mvr_people'] as num?)?.toInt() ??
        0;
    final withData =
        (json['with_data'] as num?)?.toInt() ??
        (json['mvr_with_quality'] as num?)?.toInt() ??
        (json['mvr_with_quality_scores'] as num?)?.toInt() ??
        0;
    final withoutData =
        (json['without_data'] as num?)?.toInt() ??
        (json['mvr_without_quality'] as num?)?.toInt() ??
        (total - withData).clamp(0, total);

    return DataCompleteness(
      total: total,
      withData: withData,
      withoutData: withoutData,
      percentage: (json['percentage'] as num?)?.toDouble() ?? 0.0,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'total': total,
      'with_data': withData,
      'without_data': withoutData,
      'percentage': percentage,
    };
  }
}

/// Time series data point for trends
class TimeSeriesDataPoint {
  final DateTime timestamp;
  final int count;
  final Demographics? demographics;

  TimeSeriesDataPoint({
    required this.timestamp,
    required this.count,
    this.demographics,
  });

  factory TimeSeriesDataPoint.fromJson(Map<String, dynamic> json) {
    return TimeSeriesDataPoint(
      timestamp: DateTime.parse(json['timestamp'] as String),
      count: json['count'] as int,
      demographics: json['demographics'] != null
          ? Demographics.fromJson(json['demographics'] as Map<String, dynamic>)
          : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'timestamp': timestamp.toIso8601String(),
      'count': count,
      if (demographics != null) 'demographics': demographics!.toJson(),
    };
  }
}

/// Time-based analytics with trend data
class TimeBasedAnalytics {
  final String timeFilter;
  final List<TimeSeriesDataPoint> dataPoints;
  final int peakCount;
  final DateTime? peakTime;
  final double averageCount;
  final DateTime generatedAt;

  TimeBasedAnalytics({
    required this.timeFilter,
    required this.dataPoints,
    required this.peakCount,
    this.peakTime,
    required this.averageCount,
    required this.generatedAt,
  });

  factory TimeBasedAnalytics.fromJson(Map<String, dynamic> json) {
    return TimeBasedAnalytics(
      timeFilter: json['time_filter'] as String,
      dataPoints: (json['data_points'] as List)
          .map((d) => TimeSeriesDataPoint.fromJson(d as Map<String, dynamic>))
          .toList(),
      peakCount: json['peak_count'] as int,
      peakTime: json['peak_time'] != null
          ? DateTime.parse(json['peak_time'] as String)
          : null,
      averageCount: (json['average_count'] as num).toDouble(),
      generatedAt: DateTime.parse(json['generated_at'] as String),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'time_filter': timeFilter,
      'data_points': dataPoints.map((d) => d.toJson()).toList(),
      'peak_count': peakCount,
      if (peakTime != null) 'peak_time': peakTime!.toIso8601String(),
      'average_count': averageCount,
      'generated_at': generatedAt.toIso8601String(),
    };
  }
}

/// Export analytics data for Excel
class AnalyticsExportData {
  final AnalyticsSummary summary;
  final TimeBasedAnalytics? timeBasedData;
  final String exportLevel;
  final DateTime exportedAt;

  AnalyticsExportData({
    required this.summary,
    this.timeBasedData,
    required this.exportLevel,
    required this.exportedAt,
  });

  Map<String, dynamic> toJson() {
    return {
      'summary': summary.toJson(),
      if (timeBasedData != null) 'time_based_data': timeBasedData!.toJson(),
      'export_level': exportLevel,
      'exported_at': exportedAt.toIso8601String(),
    };
  }
}
