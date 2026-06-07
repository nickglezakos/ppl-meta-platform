class CameraOperationsMeta {
  final DateTime? generatedAt;
  final int? total;

  const CameraOperationsMeta({
    required this.generatedAt,
    required this.total,
  });

  factory CameraOperationsMeta.fromJson(Map<String, dynamic> json) {
    return CameraOperationsMeta(
      generatedAt: DateTime.tryParse(json['generated_at']?.toString() ?? ''),
      total: _asInt(json['total']),
    );
  }
}

class CameraOperationsSummary {
  final Map<String, int> byState;
  final Map<String, int> byCameraType;

  const CameraOperationsSummary({
    required this.byState,
    required this.byCameraType,
  });

  factory CameraOperationsSummary.fromJson(Map<String, dynamic> json) {
    return CameraOperationsSummary(
      byState: _toIntMap(json['by_state']),
      byCameraType: _toIntMap(json['by_camera_type']),
    );
  }
}

class CameraOperationItem {
  final String cameraId;
  final String cameraName;
  final String cameraType;
  final String streamState;
  final int activeViewers;
  final String cameraProfile;
  final String? lastFrameAt;
  final int? frameGapMs;
  final String? lastTransitionReason;
  final String? updatedAt;

  const CameraOperationItem({
    required this.cameraId,
    required this.cameraName,
    required this.cameraType,
    required this.streamState,
    required this.activeViewers,
    required this.cameraProfile,
    required this.lastFrameAt,
    required this.frameGapMs,
    required this.lastTransitionReason,
    required this.updatedAt,
  });

  factory CameraOperationItem.fromJson(Map<String, dynamic> json) {
    return CameraOperationItem(
      cameraId: json['camera_id']?.toString() ?? '',
      cameraName: json['camera_name']?.toString() ?? '',
      cameraType: json['camera_type']?.toString() ?? 'UNKNOWN',
      streamState: json['stream_state']?.toString() ?? 'DISCONNECTED',
      activeViewers: _asInt(json['active_viewers']) ?? 0,
      cameraProfile: json['camera_profile']?.toString() ?? 'usb',
      lastFrameAt: json['last_frame_at']?.toString(),
      frameGapMs: _asInt(json['frame_gap_ms']),
      lastTransitionReason: json['last_transition_reason']?.toString(),
      updatedAt: json['updated_at']?.toString(),
    );
  }
}

class CameraOperationsStatusResponse {
  final CameraOperationsMeta meta;
  final CameraOperationsSummary summary;
  final List<CameraOperationItem> items;

  const CameraOperationsStatusResponse({
    required this.meta,
    required this.summary,
    required this.items,
  });

  factory CameraOperationsStatusResponse.fromJson(Map<String, dynamic> json) {
    final metaJson = Map<String, dynamic>.from((json['meta'] as Map?) ?? const {});
    final summaryJson = Map<String, dynamic>.from((json['summary'] as Map?) ?? const {});
    final rawItems = (json['items'] as List?) ?? const [];

    return CameraOperationsStatusResponse(
      meta: CameraOperationsMeta.fromJson(metaJson),
      summary: CameraOperationsSummary.fromJson(summaryJson),
      items: rawItems
          .whereType<Map>()
          .map((item) => CameraOperationItem.fromJson(Map<String, dynamic>.from(item)))
          .toList(),
    );
  }
}

class ReconcileHealth {
  final bool enabled;
  final int intervalSeconds;
  final bool beatEnabled;
  final String status;
  final int? ageSeconds;
  final String? lastReconcileAt;
  final String? lastPolicyUpdateAt;

  const ReconcileHealth({
    required this.enabled,
    required this.intervalSeconds,
    required this.beatEnabled,
    required this.status,
    required this.ageSeconds,
    required this.lastReconcileAt,
    required this.lastPolicyUpdateAt,
  });

  factory ReconcileHealth.fromJson(Map<String, dynamic> json) {
    return ReconcileHealth(
      enabled: json['enabled'] == true,
      intervalSeconds: _asInt(json['interval_seconds']) ?? 0,
      beatEnabled: json['beat_enabled'] == true,
      status: json['status']?.toString() ?? 'unknown',
      ageSeconds: _asInt(json['age_seconds']),
      lastReconcileAt: json['last_reconcile_at']?.toString(),
      lastPolicyUpdateAt: json['last_policy_update_at']?.toString(),
    );
  }
}

class ReconcileHealthResponse {
  final CameraOperationsMeta meta;
  final ReconcileHealth reconcile;

  const ReconcileHealthResponse({
    required this.meta,
    required this.reconcile,
  });

  factory ReconcileHealthResponse.fromJson(Map<String, dynamic> json) {
    final metaJson = Map<String, dynamic>.from((json['meta'] as Map?) ?? const {});
    final reconcileJson = Map<String, dynamic>.from((json['reconcile'] as Map?) ?? const {});

    return ReconcileHealthResponse(
      meta: CameraOperationsMeta.fromJson(metaJson),
      reconcile: ReconcileHealth.fromJson(reconcileJson),
    );
  }
}

class CameraOperationsAggregateRow {
  final String group;
  final double frameGapP95Ms;
  final double activeViewersAvg;
  final double effectiveFpsAvg;
  final int staleEvents;

  const CameraOperationsAggregateRow({
    required this.group,
    required this.frameGapP95Ms,
    required this.activeViewersAvg,
    required this.effectiveFpsAvg,
    required this.staleEvents,
  });

  factory CameraOperationsAggregateRow.fromJson(Map<String, dynamic> json) {
    return CameraOperationsAggregateRow(
      group: json['group']?.toString() ?? 'unknown',
      frameGapP95Ms: _asDouble(json['frame_gap_p95_ms']) ?? 0.0,
      activeViewersAvg: _asDouble(json['active_viewers_avg']) ?? 0.0,
      effectiveFpsAvg: _asDouble(json['effective_fps_avg']) ?? 0.0,
      staleEvents: _asInt(json['stale_events']) ?? 0,
    );
  }
}

class CameraOperationsAggregatesResponse {
  final CameraOperationsMeta meta;
  final List<CameraOperationsAggregateRow> rows;

  const CameraOperationsAggregatesResponse({
    required this.meta,
    required this.rows,
  });

  factory CameraOperationsAggregatesResponse.fromJson(Map<String, dynamic> json) {
    final metaJson = Map<String, dynamic>.from((json['meta'] as Map?) ?? const {});
    final rawRows = (json['rows'] as List?) ?? const [];

    return CameraOperationsAggregatesResponse(
      meta: CameraOperationsMeta.fromJson(metaJson),
      rows: rawRows
          .whereType<Map>()
          .map((row) => CameraOperationsAggregateRow.fromJson(Map<String, dynamic>.from(row)))
          .toList(),
    );
  }
}

class ReconcileTriggerResult {
  final String scope;
  final String? cameraId;
  final String? taskId;
  final String? taskName;
  final String? status;
  final int? total;
  final int? updated;

  const ReconcileTriggerResult({
    required this.scope,
    required this.cameraId,
    required this.taskId,
    required this.taskName,
    required this.status,
    required this.total,
    required this.updated,
  });

  factory ReconcileTriggerResult.fromJson(Map<String, dynamic> json) {
    return ReconcileTriggerResult(
      scope: json['scope']?.toString() ?? 'all',
      cameraId: json['camera_id']?.toString(),
      taskId: json['task_id']?.toString(),
      taskName: json['task_name']?.toString(),
      status: json['status']?.toString(),
      total: _asInt(json['total']),
      updated: _asInt(json['updated']),
    );
  }
}

class ReconcileTriggerResponse {
  final ReconcileTriggerMeta meta;
  final ReconcileTriggerResult result;

  const ReconcileTriggerResponse({
    required this.meta,
    required this.result,
  });

  factory ReconcileTriggerResponse.fromJson(Map<String, dynamic> json) {
    final metaJson = Map<String, dynamic>.from((json['meta'] as Map?) ?? const {});
    final resultJson = Map<String, dynamic>.from((json['result'] as Map?) ?? const {});

    return ReconcileTriggerResponse(
      meta: ReconcileTriggerMeta.fromJson(metaJson),
      result: ReconcileTriggerResult.fromJson(resultJson),
    );
  }
}

class ReconcileTriggerMeta {
  final DateTime? generatedAt;
  final String? triggeredBy;
  final String? mode;

  const ReconcileTriggerMeta({
    required this.generatedAt,
    required this.triggeredBy,
    required this.mode,
  });

  factory ReconcileTriggerMeta.fromJson(Map<String, dynamic> json) {
    return ReconcileTriggerMeta(
      generatedAt: DateTime.tryParse(json['generated_at']?.toString() ?? ''),
      triggeredBy: json['triggered_by']?.toString(),
      mode: json['mode']?.toString(),
    );
  }
}

Map<String, int> _toIntMap(dynamic value) {
  if (value is! Map) {
    return const {};
  }

  final result = <String, int>{};
  value.forEach((key, val) {
    final parsed = _asInt(val);
    if (key != null && parsed != null) {
      result[key.toString()] = parsed;
    }
  });
  return result;
}

int? _asInt(dynamic value) {
  if (value is int) {
    return value;
  }
  if (value is double) {
    return value.toInt();
  }
  if (value is String) {
    return int.tryParse(value);
  }
  return null;
}

double? _asDouble(dynamic value) {
  if (value is double) {
    return value;
  }
  if (value is int) {
    return value.toDouble();
  }
  if (value is String) {
    return double.tryParse(value);
  }
  return null;
}
