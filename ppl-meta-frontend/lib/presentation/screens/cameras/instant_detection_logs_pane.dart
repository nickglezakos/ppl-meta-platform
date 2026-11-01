import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/providers/camera_providers.dart';
import '../../../core/theme/theme_kit.dart';
import '../../../models/cross_video_analysis_models.dart';
import '../../../providers/instant_analytics_view_mode_provider.dart';
import '../../../providers/settings_providers.dart';
import '../../../screens/person_objects_detail_screen.dart';
import '../../../utils/offline_fonts.dart';
import '../../../widgets/collections_search_dialog.dart';

/// Camera content-pane view of Instant Detection flush logs
/// (Media `instant_detection_logs` — separate from Automation action logs).
/// Analytics intents live on AnalyticsScreen, not here.
class InstantDetectionLogsPane extends ConsumerStatefulWidget {
  const InstantDetectionLogsPane({
    super.key,
    required this.cameraDeviceId,
  });

  final String cameraDeviceId;

  @override
  ConsumerState<InstantDetectionLogsPane> createState() =>
      _InstantDetectionLogsPaneState();
}

class _InstantDetectionLogsPaneState
    extends ConsumerState<InstantDetectionLogsPane> {
  bool _loading = true;
  bool _searching = false;
  String? _error;
  List<Map<String, dynamic>> _logs = const [];
  int? _expandedId;
  InstantAnalyticsViewMode? _loadedMode;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _load());
  }

  @override
  void didUpdateWidget(covariant InstantDetectionLogsPane oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.cameraDeviceId != widget.cameraDeviceId) {
      _load();
    }
  }

  bool get _isNormalised =>
      ref.read(instantAnalyticsViewModeProvider).isNormalised;

  Future<void> _load() async {
    final mode = ref.read(instantAnalyticsViewModeProvider);
    setState(() {
      _loading = true;
      _error = null;
      _expandedId = null;
      _loadedMode = mode;
    });
    try {
      final client = ref.read(mediaApiClientProvider);
      final rows = mode.isNormalised
          ? await client.listInstantDetectionNormalisedSpans(
              cameraDeviceId: widget.cameraDeviceId,
              limit: 50,
            )
          : await client.listInstantDetectionLogs(
              cameraDeviceId: widget.cameraDeviceId,
              limit: 50,
            );
      if (!mounted) return;
      setState(() {
        _logs = rows;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  List<Map<String, dynamic>> _collectNormalisedIndividuals(
    List<Map<String, dynamic>> spans,
  ) {
    final collected = <Map<String, dynamic>>[];
    final seen = <String>{};
    for (final span in spans) {
      final payload = span['payload_json'];
      if (payload is! Map) continue;
      final individuals = payload['individuals'];
      if (individuals is! List) continue;
      for (final raw in individuals) {
        if (raw is! Map) continue;
        final person = Map<String, dynamic>.from(raw);
        final uid = person['instant_mvr_uuid']?.toString() ??
            person['mvr_people_uuid']?.toString() ??
            person['super_individual_uuid']?.toString();
        if (uid == null || uid.isEmpty || !seen.add(uid)) continue;
        person['instant_mvr_uuid'] = uid;
        person['mvr_people_uuid'] = person['mvr_people_uuid'] ?? uid;
        person['camera_id'] =
            person['camera_id'] ?? span['camera_device_id'] ?? widget.cameraDeviceId;
        person['camera_device_id'] =
            span['camera_device_id'] ?? widget.cameraDeviceId;
        person['source'] = 'normalised_individual';
        person['normalised_span_id'] = span['id'];
        person['flush_started_at'] =
            person['flush_started_at'] ?? span['span_start'];
        person['flush_ended_at'] =
            person['flush_ended_at'] ?? span['span_end'];
        collected.add(person);
      }
    }
    return collected;
  }

  String _fmt(dynamic value) {
    if (value == null) return '—';
    final s = value.toString();
    if (s.length >= 19 && s.contains('T')) {
      return s.substring(0, 19).replaceFirst('T', ' ');
    }
    return s;
  }

  String _formatGaitBandLabel(String band) {
    switch (band.trim().toLowerCase()) {
      case 'walking':
        return 'Walking';
      case 'light_running':
        return 'Light running';
      case 'running':
        return 'Running';
      case 'fast_running':
        return 'Fast running';
      default:
        return band.replaceAll('_', ' ');
    }
  }

  String _formatMotionClassLabel(String motionClass) {
    switch (motionClass.trim().toLowerCase()) {
      case 'stationary':
        return 'Stationary';
      case 'directed_transit':
        return 'Directed transit';
      case 'loitering':
        return 'Loitering';
      case 'pacing':
        return 'Pacing';
      case 'erratic':
        return 'Erratic';
      default:
        return motionClass.replaceAll('_', ' ');
    }
  }

  List<Map<String, dynamic>> _flushMotionEntities(Map<String, dynamic> payload) {
    final merge = payload['hierarchical_merge'];
    if (merge is Map) {
      final groups = merge['merge_groups'];
      if (groups is List && groups.isNotEmpty) {
        return groups.whereType<Map>().map((e) => Map<String, dynamic>.from(e)).toList();
      }
    }
    final mvrs = payload['instant_mvrs'];
    if (mvrs is List && mvrs.isNotEmpty) {
      return mvrs.whereType<Map>().map((e) => Map<String, dynamic>.from(e)).toList();
    }
    final groups = payload['person_groups'];
    if (groups is List && groups.isNotEmpty) {
      return groups.whereType<Map>().map((e) => Map<String, dynamic>.from(e)).toList();
    }
    return const [];
  }

  double? _entitySpeedMps(Map<String, dynamic> entity) {
    final direct = entity['speed_mps'] ?? entity['average_speed_mps'];
    if (direct is num && direct > 0) return direct.toDouble();
    final tracking = entity['movement_tracking'];
    if (tracking is Map) {
      final stats = tracking['movement_statistics'];
      if (stats is Map) {
        final nested = stats['average_speed_mps'] ?? stats['speed_mps'];
        if (nested is num && nested > 0) return nested.toDouble();
      }
    }
    return null;
  }

  String? _entityGait(Map<String, dynamic> entity) {
    final gait = entity['gait_band'];
    if (gait is String && gait.isNotEmpty) return gait;
    final tracking = entity['movement_tracking'];
    if (tracking is Map) {
      final stats = tracking['movement_statistics'];
      if (stats is Map) {
        final nested = stats['gait_band'];
        if (nested is String && nested.isNotEmpty) return nested;
      }
    }
    return null;
  }

  String? _entityMotionClass(Map<String, dynamic> entity) {
    final cls = entity['motion_class'];
    if (cls is String && cls.isNotEmpty && cls.toLowerCase() != 'unknown') {
      return cls;
    }
    final tracking = entity['movement_tracking'];
    if (tracking is Map) {
      final stats = tracking['movement_statistics'];
      if (stats is Map) {
        final nested = stats['motion_class'];
        if (nested is String &&
            nested.isNotEmpty &&
            nested.toLowerCase() != 'unknown') {
          return nested;
        }
      }
    }
    return null;
  }

  Widget _motionChip(String label, String value) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: AppColors.info.withOpacity(0.1),
        borderRadius: BorderRadius.circular(AppRadius.chipBadge),
        border: Border.all(color: AppColors.info.withOpacity(0.25)),
      ),
      child: Text(
        '$label $value',
        style: OfflineFonts.inter(
          fontSize: 11,
          fontWeight: FontWeight.w500,
          color: AppColors.textPrimary,
        ),
      ),
    );
  }

  Widget _buildFlushMotionSummary(Map<String, dynamic> payload) {
    final entities = _flushMotionEntities(payload);
    final speeds = <double>[];
    final gaitCounts = <String, int>{};
    final motionCounts = <String, int>{};
    for (final entity in entities) {
      final speed = _entitySpeedMps(entity);
      if (speed != null) speeds.add(speed);
      final gait = _entityGait(entity);
      if (gait != null) {
        gaitCounts[gait] = (gaitCounts[gait] ?? 0) + 1;
      }
      final motion = _entityMotionClass(entity);
      if (motion != null) {
        motionCounts[motion] = (motionCounts[motion] ?? 0) + 1;
      }
    }
    if (speeds.isEmpty && gaitCounts.isEmpty && motionCounts.isEmpty) {
      return const SizedBox.shrink();
    }
    String? dominant(Map<String, int> counts) {
      if (counts.isEmpty) return null;
      return counts.entries.reduce((a, b) => a.value >= b.value ? a : b).key;
    }
    final avg = speeds.isEmpty
        ? null
        : speeds.reduce((a, b) => a + b) / speeds.length;
    final gait = dominant(gaitCounts);
    final motion = dominant(motionCounts);
    return Wrap(
      spacing: 6,
      runSpacing: 4,
      children: [
        if (avg != null) _motionChip('Avg', '${avg.toStringAsFixed(2)} m/s'),
        if (gait != null) _motionChip('Gait', _formatGaitBandLabel(gait)),
        if (motion != null)
          _motionChip('Motion', _formatMotionClassLabel(motion)),
      ],
    );
  }

  Widget _buildFlushMotionDetail(Map<String, dynamic> payload) {
    final entities = _flushMotionEntities(payload);
    if (entities.isEmpty) return const SizedBox.shrink();
    final rows = <Widget>[];
    for (var i = 0; i < entities.length && i < 8; i++) {
      final entity = entities[i];
      final speed = _entitySpeedMps(entity);
      final gait = _entityGait(entity);
      final motion = _entityMotionClass(entity);
      if (speed == null && gait == null && motion == null) continue;
      final id = entity['person_object_uuid'] ??
          entity['instant_mvr_uuid'] ??
          entity['group_id'] ??
          entity['super_individual_uuid'] ??
          '#${i + 1}';
      final parts = <String>[];
      if (speed != null) parts.add('${speed.toStringAsFixed(2)} m/s');
      if (gait != null) parts.add(_formatGaitBandLabel(gait));
      if (motion != null) parts.add(_formatMotionClassLabel(motion));
      rows.add(
        Padding(
          padding: const EdgeInsets.only(bottom: 4),
          child: Text(
            '${id.toString().length > 12 ? '${id.toString().substring(0, 12)}…' : id}: ${parts.join(' · ')}',
            style: OfflineFonts.inter(
              fontSize: 11,
              color: AppColors.textSecondary,
            ),
          ),
        ),
      );
    }
    if (rows.isEmpty) return const SizedBox.shrink();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Motion per person',
          style: OfflineFonts.inter(
            fontSize: 12,
            fontWeight: FontWeight.w600,
            color: AppColors.textPrimary,
          ),
        ),
        const SizedBox(height: 4),
        ...rows,
      ],
    );
  }

  /// Prefer Vision person_groups; fall back to hierarchical merge / InstantMvrs.
  int _personGroupCount(Map<String, dynamic>? payload) {
    if (payload == null) return 0;
    final groups = payload['person_groups'];
    if (groups is List && groups.isNotEmpty) return groups.length;

    final merge = payload['hierarchical_merge'];
    if (merge is Map) {
      final supers = merge['super_individuals'];
      if (supers is List && supers.isNotEmpty) return supers.length;
      final stats = merge['statistics'];
      if (stats is Map) {
        final n = stats['super_individuals'];
        if (n is int) return n;
        if (n is num) return n.toInt();
      }
    }

    final mvrs = payload['instant_mvrs'];
    if (mvrs is List && mvrs.isNotEmpty) {
      // Distinct InstantMvr ids when merge payload is incomplete.
      final ids = <String>{};
      for (final m in mvrs) {
        if (m is! Map) continue;
        final id = m['instant_mvr_uuid'] ?? m['mvr_people_uuid'];
        if (id != null) ids.add(id.toString());
      }
      return ids.isNotEmpty ? ids.length : mvrs.length;
    }
    return groups is List ? groups.length : 0;
  }

  String? _mvrUid(dynamic raw) {
    if (raw is Map) {
      final uid = raw['instant_mvr_uuid'] ?? raw['mvr_people_uuid'];
      return uid?.toString();
    }
    if (raw == null) return null;
    final s = raw.toString();
    return s.isEmpty ? null : s;
  }

  /// Build recording-shaped movement_tracking from Vision faces (legacy logs).
  Map<String, dynamic> _movementTrackingFromFaces(List<dynamic> faces) {
    final enriched = <Map<String, dynamic>>[];
    for (var i = 0; i < faces.length; i++) {
      final raw = faces[i];
      if (raw is! Map) continue;
      final face = Map<String, dynamic>.from(raw);
      double cx = 0;
      double cy = 0;
      if (face['center_x'] != null && face['center_y'] != null) {
        cx = (face['center_x'] as num).toDouble();
        cy = (face['center_y'] as num).toDouble();
      } else {
        final bbox = face['bbox'];
        if (bbox is List && bbox.length >= 4) {
          cx = ((bbox[0] as num) + (bbox[2] as num)) / 2.0;
          cy = ((bbox[1] as num) + (bbox[3] as num)) / 2.0;
        } else if (face['bbox_x1'] != null && face['bbox_x2'] != null) {
          cx = ((face['bbox_x1'] as num) + (face['bbox_x2'] as num)) / 2.0;
          cy = ((face['bbox_y1'] as num) + (face['bbox_y2'] as num)) / 2.0;
        }
      }
      double ts = i.toDouble();
      final rawTs = face['timestamp'] ?? face['created_at'];
      if (rawTs is num) {
        ts = rawTs.toDouble();
      } else if (rawTs != null) {
        final parsed = DateTime.tryParse(rawTs.toString());
        if (parsed != null) {
          ts = parsed.millisecondsSinceEpoch / 1000.0;
        }
      }
      face['center_x'] = cx;
      face['center_y'] = cy;
      face['timestamp'] = ts;
      face['_frame'] = face['frame_number'] ?? face['frame_index'] ?? i;
      enriched.add(face);
    }
    enriched.sort((a, b) {
      final byTs = (a['timestamp'] as num).compareTo(b['timestamp'] as num);
      if (byTs != 0) return byTs;
      return (a['_frame'] as num).compareTo(b['_frame'] as num);
    });

    final routePoints = <Map<String, dynamic>>[];
    final velocities = <double>[];
    for (var i = 0; i < enriched.length; i++) {
      final face = enriched[i];
      var vx = 0.0;
      var vy = 0.0;
      var magnitude = 0.0;
      if (i > 0) {
        final prev = enriched[i - 1];
        final dt =
            (face['timestamp'] as num).toDouble() -
            (prev['timestamp'] as num).toDouble();
        if (dt > 0) {
          vx = ((face['center_x'] as num) - (prev['center_x'] as num)) / dt;
          vy = ((face['center_y'] as num) - (prev['center_y'] as num)) / dt;
          magnitude = math.sqrt(vx * vx + vy * vy);
        }
      }
      routePoints.add({
        'sequence_number': i + 1,
        'frame_number': face['frame_number'] ?? face['frame_index'],
        'timestamp': face['timestamp'],
        'center_x': face['center_x'],
        'center_y': face['center_y'],
        'velocity_x': double.parse(vx.toStringAsFixed(2)),
        'velocity_y': double.parse(vy.toStringAsFixed(2)),
        'velocity_magnitude': double.parse(magnitude.toStringAsFixed(2)),
        'confidence': face['confidence'],
        if (face['bbox'] != null) 'bbox': face['bbox'],
      });
      if (magnitude > 0) velocities.add(magnitude);
    }

    var totalDistance = 0.0;
    for (var i = 1; i < routePoints.length; i++) {
      final dx = (routePoints[i]['center_x'] as num) -
          (routePoints[i - 1]['center_x'] as num);
      final dy = (routePoints[i]['center_y'] as num) -
          (routePoints[i - 1]['center_y'] as num);
      totalDistance += math.sqrt(
        dx.toDouble() * dx.toDouble() + dy.toDouble() * dy.toDouble(),
      );
    }
    final avg = velocities.isEmpty
        ? 0.0
        : velocities.reduce((a, b) => a + b) / velocities.length;
    final maxV = velocities.isEmpty
        ? 0.0
        : velocities.reduce((a, b) => a > b ? a : b);
    final timeInFrame = routePoints.length > 1
        ? ((routePoints.last['timestamp'] as num) -
                (routePoints.first['timestamp'] as num))
            .toDouble()
        : 0.0;
    return {
      'route_points': routePoints,
      'movement_statistics': {
        'total_route_points': routePoints.length,
        'total_distance_pixels': double.parse(totalDistance.toStringAsFixed(2)),
        'average_velocity': double.parse(avg.toStringAsFixed(2)),
        'max_velocity': double.parse(maxV.toStringAsFixed(2)),
        'time_in_frame_seconds': double.parse(timeInFrame.toStringAsFixed(2)),
      },
      'average_route_velocity': double.parse(avg.toStringAsFixed(2)),
    };
  }

  void _applyMovementTracking(
    Map<String, dynamic> record,
    Map<String, dynamic>? tracking,
  ) {
    if (tracking == null) {
      _preserveSpeedFields(record);
      _preserveMotionFields(record);
      return;
    }
    final stats = Map<String, dynamic>.from(
      tracking['movement_statistics'] as Map? ?? const {},
    );
    // Keep ground-speed fields from record or tracking stats (do not invent m/s).
    final speed = record['speed_mps'] ??
        tracking['speed_mps'] ??
        stats['average_speed_mps'];
    final gait = record['gait_band'] ??
        tracking['gait_band'] ??
        stats['gait_band'];
    if (speed != null) {
      stats['average_speed_mps'] = speed;
    }
    if (gait != null) {
      stats['gait_band'] = gait;
    }
    record['movement_tracking'] = {
      'route_points':
          List<dynamic>.from(tracking['route_points'] as List? ?? const []),
      'movement_statistics': stats,
    };
    record['route_points'] =
        List<dynamic>.from(tracking['route_points'] as List? ?? const []);
    if (tracking['average_route_velocity'] != null) {
      record['average_route_velocity'] = tracking['average_route_velocity'];
    } else {
      if (stats['average_velocity'] != null) {
        record['average_route_velocity'] = stats['average_velocity'];
      }
    }
    _preserveSpeedFields(record, preferredSpeed: speed, preferredGait: gait);
    _preserveMotionFields(record);
  }

  /// Preserve motion_class fields on a flush search record.
  void _preserveMotionFields(
    Map<String, dynamic> record, {
    dynamic preferredClass,
    dynamic preferredConfidence,
  }) {
    final tracking = record['movement_tracking'];
    final stats = (tracking is Map)
        ? Map<String, dynamic>.from(
            (tracking['movement_statistics'] as Map?) ?? const {},
          )
        : <String, dynamic>{};
    final motionClass = preferredClass ??
        record['motion_class'] ??
        stats['motion_class'];
    final confidence = preferredConfidence ??
        record['motion_confidence'] ??
        stats['motion_confidence'];
    if (motionClass != null &&
        motionClass.toString().isNotEmpty &&
        motionClass.toString().toLowerCase() != 'unknown') {
      record['motion_class'] = motionClass.toString();
      stats['motion_class'] = motionClass.toString();
    }
    if (confidence is num) {
      record['motion_confidence'] = confidence.toDouble();
      stats['motion_confidence'] = confidence.toDouble();
    }
    if (record['motion_features'] == null && stats['motion_features'] != null) {
      record['motion_features'] = stats['motion_features'];
    }
    if (tracking is Map || stats.isNotEmpty) {
      record['movement_tracking'] = {
        ...(tracking is Map ? Map<String, dynamic>.from(tracking) : {}),
        'movement_statistics': stats,
      };
    }
  }

  /// Preserve / normalize speed_mps + gait_band on a flush search record.
  void _preserveSpeedFields(
    Map<String, dynamic> record, {
    Object? preferredSpeed,
    Object? preferredGait,
  }) {
    final stats = (record['movement_tracking'] is Map)
        ? Map<String, dynamic>.from(
            (record['movement_tracking'] as Map)['movement_statistics']
                    as Map? ??
                const {},
          )
        : <String, dynamic>{};
    final speed = preferredSpeed ??
        record['speed_mps'] ??
        stats['average_speed_mps'];
    final gait = preferredGait ?? record['gait_band'] ?? stats['gait_band'];
    if (speed != null) {
      record['speed_mps'] = speed;
      stats['average_speed_mps'] = speed;
    }
    if (gait != null) {
      record['gait_band'] = gait;
      stats['gait_band'] = gait;
    }
    if (stats.isNotEmpty) {
      final tracking = record['movement_tracking'] is Map
          ? Map<String, dynamic>.from(record['movement_tracking'] as Map)
          : <String, dynamic>{
              'route_points': record['route_points'] ?? const [],
            };
      tracking['movement_statistics'] = stats;
      record['movement_tracking'] = tracking;
    }
  }

  Map<String, dynamic>? _resolveMovementTracking({
    required Map<String, dynamic> group,
    required Map<String, dynamic> winnerRecord,
    required Map payload,
  }) {
    final groupTracking = group['movement_tracking'];
    if (groupTracking is Map &&
        (groupTracking['route_points'] as List?)?.isNotEmpty == true) {
      return Map<String, dynamic>.from(groupTracking);
    }
    if (group['route_points'] is List &&
        (group['route_points'] as List).isNotEmpty) {
      return _movementTrackingFromFaces(group['route_points'] as List);
    }
    final winnerTracking = winnerRecord['movement_tracking'];
    if (winnerTracking is Map &&
        (winnerTracking['route_points'] as List?)?.isNotEmpty == true) {
      return Map<String, dynamic>.from(winnerTracking);
    }
    if (winnerRecord['route_points'] is List &&
        (winnerRecord['route_points'] as List).isNotEmpty) {
      return _movementTrackingFromFaces(winnerRecord['route_points'] as List);
    }

    // Legacy logs: reconstruct from Vision person_groups.faces.
    final personGroups = payload['person_groups'];
    if (personGroups is List) {
      final pou = winnerRecord['person_object_uuid']?.toString();
      for (final raw in personGroups) {
        if (raw is! Map) continue;
        final g = Map<String, dynamic>.from(raw);
        final gPou = g['person_object_uuid']?.toString() ?? g['person_id']?.toString();
        if (pou != null && gPou != pou) continue;
        final faces = g['faces'];
        if (faces is List && faces.isNotEmpty) {
          return _movementTrackingFromFaces(faces);
        }
      }
      // If no pou match, try first group with faces (single-person flushes).
      if (personGroups.length == 1 && personGroups.first is Map) {
        final faces = (personGroups.first as Map)['faces'];
        if (faces is List && faces.isNotEmpty) {
          return _movementTrackingFromFaces(faces);
        }
      }
    }
    return null;
  }

  Map<String, Map<String, dynamic>> _indexInstantMvrs(List<dynamic>? mvrs) {
    final byId = <String, Map<String, dynamic>>{};
    for (final raw in mvrs ?? const []) {
      if (raw is! Map) continue;
      final mvr = Map<String, dynamic>.from(raw);
      final uid = _mvrUid(mvr);
      if (uid == null) continue;
      mvr['instant_mvr_uuid'] = uid;
      mvr['mvr_people_uuid'] = uid;
      byId[uid] = mvr;
    }
    return byId;
  }

  Map<String, dynamic> _annotateFlushRecord(
    Map<String, dynamic> record,
    Map<String, dynamic> log, {
    required String uid,
    List<String> memberUuids = const [],
  }) {
    final out = Map<String, dynamic>.from(record);
    out['instant_mvr_uuid'] = uid;
    out['mvr_people_uuid'] = uid;
    out['log_id'] = log['id'];
    out['flush_started_at'] = log['flush_started_at'];
    out['flush_ended_at'] = log['flush_ended_at'];
    out['camera_id'] =
        out['camera_id'] ?? log['camera_device_id'] ?? widget.cameraDeviceId;
    out['camera_device_id'] =
        log['camera_device_id'] ?? widget.cameraDeviceId;
    out['source'] = 'flush_individual';
    if (memberUuids.isNotEmpty) {
      out['flush_member_uuids'] = memberUuids;
    }
    return out;
  }

  /// One search individual per flush person (hierarchical merge winners),
  /// not one per raw cycle InstantMvr.
  List<Map<String, dynamic>> _collectFlushIndividuals(
    List<Map<String, dynamic>> logs,
  ) {
    final collected = <Map<String, dynamic>>[];
    final seen = <String>{};

    for (final log in logs) {
      final payload = log['payload_json'];
      if (payload is! Map) continue;
      final mvrById = _indexInstantMvrs(
        payload['instant_mvrs'] is List
            ? payload['instant_mvrs'] as List
            : null,
      );

      final merge = payload['hierarchical_merge'];
      final mergeGroups = merge is Map ? merge['merge_groups'] : null;
      if (mergeGroups is List && mergeGroups.isNotEmpty) {
        for (final rawGroup in mergeGroups) {
          if (rawGroup is! Map) continue;
          final group = Map<String, dynamic>.from(rawGroup);
          final superUid = group['super_individual_uuid']?.toString();
          if (superUid == null || superUid.isEmpty || seen.contains(superUid)) {
            continue;
          }

          final memberUuids = <String>[];
          Map<String, dynamic>? winner;
          final members = group['members'];
          if (members is List) {
            for (final member in members) {
              final uid = _mvrUid(member);
              if (uid == null) continue;
              memberUuids.add(uid);
              if (member is Map && uid == superUid) {
                winner = Map<String, dynamic>.from(member);
              }
            }
          }
          for (final uid in (group['merged_mvr_uuids'] as List? ?? const [])) {
            final s = uid?.toString();
            if (s != null && s.isNotEmpty && !memberUuids.contains(s)) {
              memberUuids.add(s);
            }
          }
          if (!memberUuids.contains(superUid)) {
            memberUuids.insert(0, superUid);
          }

          winner ??= mvrById[superUid];
          if (winner == null && members is List) {
            for (final member in members) {
              if (member is! Map) continue;
              if (member['face_embedding'] != null) {
                winner = Map<String, dynamic>.from(member);
                break;
              }
            }
          }
          winner ??= mvrById.values.isNotEmpty
              ? Map<String, dynamic>.from(mvrById.values.first)
              : <String, dynamic>{'instant_mvr_uuid': superUid};

          // Local non-null copy for analyzer (winner may be reassigned above).
          var winnerRecord = Map<String, dynamic>.from(winner!);

          // Prefer highest-quality member embedding when winner lacks one.
          if (winnerRecord['face_embedding'] == null && members is List) {
            double bestQ = -1;
            for (final member in members) {
              if (member is! Map || member['face_embedding'] == null) continue;
              final q = (member['quality_score'] as num?)?.toDouble() ??
                  (member['face_quality'] as num?)?.toDouble() ??
                  0.0;
              if (q > bestQ) {
                bestQ = q;
                winnerRecord = Map<String, dynamic>.from(member);
              }
            }
          }

          final demographics = group['demographics'];
          if (demographics is Map && winnerRecord['age_gender'] == null) {
            winnerRecord['age_gender'] =
                Map<String, dynamic>.from(demographics);
          }
          if (group['winner_quality'] != null &&
              winnerRecord['quality_score'] == null) {
            winnerRecord['quality_score'] = group['winner_quality'];
          }

          _applyMovementTracking(
            winnerRecord,
            _resolveMovementTracking(
              group: group,
              winnerRecord: winnerRecord,
              payload: payload,
            ),
          );
          if (group['average_route_velocity'] != null &&
              winnerRecord['average_route_velocity'] == null) {
            winnerRecord['average_route_velocity'] =
                group['average_route_velocity'];
          }
          _preserveSpeedFields(
            winnerRecord,
            preferredSpeed: winnerRecord['speed_mps'] ?? group['speed_mps'],
            preferredGait: winnerRecord['gait_band'] ?? group['gait_band'],
          );
          // Merge cycle speed history from group + every member InstantMvr.
          final mergedSamples = <Map<String, dynamic>>[];
          final seenSampleKeys = <String>{};
          void addSamples(dynamic raw) {
            if (raw is! List) return;
            for (final sample in raw.whereType<Map>()) {
              final map = Map<String, dynamic>.from(sample);
              final key =
                  '${map['cycle_id']}|${map['timestamp']}|${map['speed_mps']}';
              if (!seenSampleKeys.add(key)) continue;
              mergedSamples.add(map);
            }
          }

          addSamples(group['speed_samples']);
          addSamples(winnerRecord['speed_samples']);
          for (final memberUid in memberUuids) {
            final member = mvrById[memberUid];
            if (member == null) continue;
            addSamples(member['speed_samples']);
            final memberSpeed = (member['speed_mps'] as num?)?.toDouble();
            if (memberSpeed != null && memberSpeed > 0) {
              addSamples([
                {
                  'timestamp': member['timestamp'] ??
                      log['flush_started_at'] ??
                      winnerRecord['flush_started_at'],
                  'speed_mps': memberSpeed,
                  'gait_band': member['gait_band'],
                  'instant_mvr_uuid': memberUid,
                },
              ]);
            }
          }
          if (mergedSamples.isNotEmpty) {
            winnerRecord['speed_samples'] = mergedSamples;
            final positive = mergedSamples
                .map((s) => (s['speed_mps'] as num?)?.toDouble())
                .whereType<double>()
                .where((s) => s > 0)
                .toList();
            if (positive.isNotEmpty) {
              final current =
                  (winnerRecord['speed_mps'] as num?)?.toDouble() ?? 0;
              if (current <= 0) {
                final mean =
                    positive.reduce((a, b) => a + b) / positive.length;
                _preserveSpeedFields(
                  winnerRecord,
                  preferredSpeed: mean,
                  preferredGait: winnerRecord['gait_band'] ?? group['gait_band'],
                );
              }
            }
          }
          _preserveMotionFields(
            winnerRecord,
            preferredClass:
                winnerRecord['motion_class'] ?? group['motion_class'],
            preferredConfidence: winnerRecord['motion_confidence'] ??
                group['motion_confidence'],
          );

          seen.add(superUid);
          collected.add(
            _annotateFlushRecord(
              winnerRecord,
              log,
              uid: superUid,
              memberUuids: memberUuids,
            ),
          );
        }
        continue;
      }

      // Fallback: Vision person_groups (already people-level when present).
      final personGroups = payload['person_groups'];
      if (personGroups is List && personGroups.isNotEmpty) {
        for (final rawGroup in personGroups) {
          if (rawGroup is! Map) continue;
          final group = Map<String, dynamic>.from(rawGroup);
          final linked = <String>[];
          final rawLinks = group['instant_mvr_uuids'];
          if (rawLinks is List) {
            for (final link in rawLinks) {
              final uid = _mvrUid(link);
              if (uid != null) linked.add(uid);
            }
          }

          String? uid = group['person_object_uuid']?.toString() ??
              group['person_id']?.toString();
          Map<String, dynamic>? record;
          if (linked.isNotEmpty) {
            uid = linked.first;
            record = mvrById[uid];
            for (final linkUid in linked) {
              final candidate = mvrById[linkUid];
              if (candidate == null) continue;
              if (record == null ||
                  ((candidate['quality_score'] as num?)?.toDouble() ?? 0) >
                      ((record['quality_score'] as num?)?.toDouble() ?? 0)) {
                record = candidate;
                uid = linkUid;
              }
            }
          }
          if (uid == null || uid.isEmpty || seen.contains(uid)) continue;

          record ??= <String, dynamic>{
            'instant_mvr_uuid': uid,
            'mvr_people_uuid': uid,
            'person_object_uuid': group['person_object_uuid'],
            'age_gender': group['age_gender'],
            'face_quality': group['avg_confidence'],
            'quality_score': group['avg_confidence'],
          };
          final bestFace = group['best_face'];
          if (bestFace is Map && record['face_embedding'] == null) {
            final emb = bestFace['face_embedding'];
            if (emb != null) record['face_embedding'] = emb;
            if (bestFace['bbox'] != null) record['bbox'] = bestFace['bbox'];
          }
          _applyMovementTracking(
            record,
            _resolveMovementTracking(
              group: group,
              winnerRecord: record,
              payload: payload,
            ),
          );
          if (group['average_route_velocity'] != null &&
              record['average_route_velocity'] == null) {
            record['average_route_velocity'] = group['average_route_velocity'];
          }
          _preserveSpeedFields(
            record,
            preferredSpeed: record['speed_mps'] ?? group['speed_mps'],
            preferredGait: record['gait_band'] ?? group['gait_band'],
          );
          final groupSamples = group['speed_samples'] ?? record['speed_samples'];
          if (groupSamples is List && groupSamples.isNotEmpty) {
            record['speed_samples'] = groupSamples
                .whereType<Map>()
                .map((e) => Map<String, dynamic>.from(e))
                .toList();
          }
          _preserveMotionFields(
            record,
            preferredClass: record['motion_class'] ?? group['motion_class'],
            preferredConfidence:
                record['motion_confidence'] ?? group['motion_confidence'],
          );

          seen.add(uid);
          collected.add(
            _annotateFlushRecord(
              record,
              log,
              uid: uid,
              memberUuids: linked.isNotEmpty ? linked : [uid],
            ),
          );
        }
        continue;
      }

      // Last resort: raw InstantMvrs (pre-merge cycle embeds).
      for (final mvr in mvrById.values) {
        final uid = _mvrUid(mvr);
        if (uid == null || seen.contains(uid)) continue;
        seen.add(uid);
        _preserveSpeedFields(mvr);
        _preserveMotionFields(mvr);
        collected.add(_annotateFlushRecord(mvr, log, uid: uid));
      }
    }
    return collected;
  }

  Future<void> _showSearchDialog() async {
    await showDialog<void>(
      context: context,
      builder: (context) => CollectionsSearchDialog(
        onApply: (start, end) {
          // Dialog pops itself on Apply; kick off search after close.
          _runSearchAndNavigate(start, end);
        },
      ),
    );
  }

  Future<void> _runSearchAndNavigate(
    DateTime? startTime,
    DateTime? endTime,
  ) async {
    if (startTime == null || endTime == null) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Select both start and end times')),
      );
      return;
    }

    setState(() => _searching = true);
    try {
      final client = ref.read(mediaApiClientProvider);
      final useNormalised = _isNormalised;
      final logs = useNormalised
          ? await client.listInstantDetectionNormalisedSpans(
              cameraDeviceId: widget.cameraDeviceId,
              startTime: startTime,
              endTime: endTime,
              limit: 500,
            )
          : await client.listInstantDetectionLogs(
              cameraDeviceId: widget.cameraDeviceId,
              startTime: startTime,
              endTime: endTime,
              limit: 500,
            );

      if (logs.isEmpty) {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              useNormalised
                  ? 'No normalised spans in that date range'
                  : 'No Instant Detection logs in that date range',
            ),
          ),
        );
        return;
      }

      // Raw: people-level flush winners. Normalised: worker-merged individuals.
      final flushIndividuals = useNormalised
          ? _collectNormalisedIndividuals(logs)
          : _collectFlushIndividuals(logs);
      if (flushIndividuals.isEmpty) {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              useNormalised
                  ? 'No individuals found in normalised spans'
                  : 'No individuals found in matching logs',
            ),
          ),
        );
        return;
      }

      final generalSettings = ref.read(generalSettingsProvider).valueOrNull;
      final mergeRule = generalSettings?.mergeIndividualsRule ?? 'none';
      final mergeThreshold =
          generalSettings?.mergeIndividualsThreshold ?? 0.70;
      // Match Collections recording search: only `auto` merges at search time.
      // Normalised spans are already worker-merged — skip a second cross-flush merge.
      final autoMerge = !useNormalised && mergeRule == 'auto';

      final searchResponse = await client.searchMVRPeopleByInstantLogs(
        cameraDeviceId: widget.cameraDeviceId,
        instantMvrs: flushIndividuals,
        startTime: startTime,
        endTime: endTime,
        autoMerge: autoMerge,
        similarityThreshold: mergeThreshold,
        limit: 500,
      );

      if (!searchResponse.success || searchResponse.data == null) {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              searchResponse.error ?? 'Instant Detection search failed',
            ),
            backgroundColor: Colors.red,
          ),
        );
        return;
      }

      final payload = searchResponse.data!;
      final mvrPeople =
          (payload['mvr_people'] as List<dynamic>? ?? const [])
              .whereType<Map>()
              .map((e) => Map<String, dynamic>.from(e))
              .toList();

      if (mvrPeople.isEmpty) {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('No individuals found in search')),
        );
        return;
      }

      final mvrUuids = mvrPeople
          .map((mvr) => mvr['mvr_people_uuid']?.toString())
          .whereType<String>()
          .where((uuid) => uuid.isNotEmpty)
          .toList();
      final logIds = logs
          .map((log) => log['id'])
          .where((id) => id != null)
          .toList();
      final sessionUuid =
          'instant_search_${DateTime.now().millisecondsSinceEpoch}';

      final sessionData = <String, dynamic>{
        'source': 'instant_detection_log_search',
        'search_results': mvrPeople,
        'instant_mvrs': flushIndividuals,
        'search_parameters': {
          'camera_device_id': widget.cameraDeviceId,
          'camera_uuids': [widget.cameraDeviceId],
          'start_time': startTime.toUtc().toIso8601String(),
          'end_time': endTime.toUtc().toIso8601String(),
          'log_ids': logIds,
          'auto_merge': autoMerge,
          'similarity_threshold': autoMerge ? mergeThreshold : null,
          'flush_individual_count': flushIndividuals.length,
          'normalised': useNormalised,
        },
        'hierarchical_merge_applied': autoMerge,
        'normalised_view': useNormalised,
        'merge_rule_applied': useNormalised ? 'normalised_worker' : mergeRule,
        'pre_merge_count': flushIndividuals.length,
        'post_merge_count': mvrUuids.length,
        'merge_statistics': {
          'total_mvr': flushIndividuals.length,
          'super_individuals': mvrUuids.length,
          'merges_performed':
              autoMerge ? (flushIndividuals.length - mvrUuids.length) : 0,
          'standalone_individuals': mvrUuids.length,
        },
        'individuals_found': mvrUuids.length,
      };

      if (!mounted) return;
      await Navigator.of(context).push(
        MaterialPageRoute(
          builder: (ctx) => PersonObjectsDetailScreen(
            crossVideoContext: CrossVideoAnalysisContext(
              individualUuids: mvrUuids,
              sessionUuid: sessionUuid,
              sessionData: sessionData,
            ),
          ),
        ),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Search failed: $e'),
          backgroundColor: Colors.red,
        ),
      );
    } finally {
      if (mounted) setState(() => _searching = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final viewMode = ref.watch(instantAnalyticsViewModeProvider);
    ref.listen<InstantAnalyticsViewMode>(instantAnalyticsViewModeProvider,
        (previous, next) {
      if (previous != next && _loadedMode != next) {
        _load();
      }
    });
    final normalised = viewMode.isNormalised;

    if (_searching) {
      return const Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            CircularProgressIndicator(),
            SizedBox(height: 16),
            Text('Searching Instant Detection logs…'),
          ],
        ),
      );
    }
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_error != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                normalised
                    ? 'Could not load normalised spans'
                    : 'Could not load Instant Detection logs',
                style: OfflineFonts.inter(
                  fontSize: 15,
                  fontWeight: FontWeight.w600,
                  color: AppColors.textPrimary,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                _error!,
                textAlign: TextAlign.center,
                style: OfflineFonts.inter(
                  fontSize: 12,
                  color: AppColors.textSecondary,
                ),
              ),
              const SizedBox(height: 16),
              TextButton.icon(
                onPressed: _load,
                icon: const Icon(Icons.refresh),
                label: const Text('Retry'),
              ),
            ],
          ),
        ),
      );
    }
    Widget headerRow() {
      return Padding(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 4),
        child: Row(
          children: [
            Expanded(
              child: Text(
                normalised
                    ? 'Instant Detection normalised'
                    : 'Instant Detection logs',
                style: OfflineFonts.inter(
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                  color: AppColors.textPrimary,
                ),
              ),
            ),
            const InstantAnalyticsViewModeToggle(),
            IconButton(
              tooltip: 'Search logs → MVR analysis',
              onPressed: _showSearchDialog,
              icon: const Icon(Icons.search, size: 20),
            ),
            IconButton(
              tooltip: 'Refresh',
              onPressed: _load,
              icon: const Icon(Icons.refresh, size: 20),
            ),
          ],
        ),
      );
    }

    if (_logs.isEmpty) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          headerRow(),
          Expanded(
            child: Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(
                      normalised
                          ? Icons.merge_type
                          : Icons.receipt_long_outlined,
                      size: 48,
                      color: AppColors.textSecondary.withOpacity(0.5),
                    ),
                    const SizedBox(height: 12),
                    Text(
                      normalised
                          ? 'No normalised spans yet'
                          : 'No Instant Detection flush logs yet',
                      style: OfflineFonts.inter(
                        fontSize: 15,
                        fontWeight: FontWeight.w600,
                        color: AppColors.textPrimary,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      normalised
                          ? 'Normalised spans appear after the worker merges people '
                              'across fixed 5-minute windows. Raw flush logs stay untouched.'
                          : 'Logs appear after Y-cycle flush (re-group + merge). '
                              'They are separate from Automation action logs.',
                      textAlign: TextAlign.center,
                      style: OfflineFonts.inter(
                        fontSize: 13,
                        color: AppColors.textSecondary,
                      ),
                    ),
                    const SizedBox(height: 16),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      alignment: WrapAlignment.center,
                      children: [
                        TextButton.icon(
                          onPressed: _showSearchDialog,
                          icon: const Icon(Icons.search),
                          label: const Text('Search'),
                        ),
                        TextButton.icon(
                          onPressed: _load,
                          icon: const Icon(Icons.refresh),
                          label: const Text('Refresh'),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          ),
        ],
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        headerRow(),
        Expanded(
          child: ListView.separated(
            padding: const EdgeInsets.fromLTRB(12, 0, 12, 16),
            itemCount: _logs.length,
            separatorBuilder: (_, __) => const SizedBox(height: 8),
            itemBuilder: (context, index) {
              final log = _logs[index];
              final id = log['id'] as int?;
              final expanded = id != null && id == _expandedId;
              final people = log['people_count'] ?? 0;
              final cycles = log['cycle_count'] ?? 0;
              final threshold = log['merge_threshold'];
              final payload = log['payload_json'];
              Map<String, dynamic>? payloadMap;
              if (payload is Map<String, dynamic>) {
                payloadMap = payload;
              } else if (payload is Map) {
                payloadMap = Map<String, dynamic>.from(payload);
              }
              final titleTs = normalised
                  ? log['span_start']
                  : log['flush_started_at'];
              final endTs =
                  normalised ? log['span_end'] : log['flush_ended_at'];
              final sourceLogCount = normalised
                  ? ((payloadMap?['source_log_count'] as num?)?.toInt() ??
                      (log['source_log_ids'] is List
                          ? (log['source_log_ids'] as List).length
                          : 0))
                  : cycles;
              final subtitleRight = normalised
                  ? '$people people · $sourceLogCount logs'
                  : '$people people · $cycles cycles';

              // For normalised spans, reuse flush motion helpers by adapting payload.
              final motionPayload = normalised && payloadMap != null
                  ? <String, dynamic>{
                      'hierarchical_merge': payloadMap['hierarchical_merge'],
                      'instant_mvrs': payloadMap['individuals'] ?? const [],
                      'person_groups': const [],
                    }
                  : payloadMap;

              return Material(
                color: AppColors.surface,
                borderRadius: BorderRadius.circular(AppRadius.md),
                child: InkWell(
                  borderRadius: BorderRadius.circular(AppRadius.md),
                  onTap: () {
                    if (id == null) return;
                    setState(() {
                      _expandedId = expanded ? null : id;
                    });
                  },
                  child: Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(AppRadius.md),
                      border: Border.all(
                        color: AppColors.border.withOpacity(0.6),
                      ),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Icon(
                              expanded
                                  ? Icons.expand_less
                                  : Icons.expand_more,
                              size: 20,
                              color: AppColors.textSecondary,
                            ),
                            const SizedBox(width: 6),
                            Expanded(
                              child: Text(
                                _fmt(titleTs),
                                style: OfflineFonts.inter(
                                  fontSize: 13,
                                  fontWeight: FontWeight.w600,
                                  color: AppColors.textPrimary,
                                ),
                              ),
                            ),
                            Text(
                              subtitleRight,
                              style: OfflineFonts.inter(
                                fontSize: 12,
                                color: AppColors.textSecondary,
                              ),
                            ),
                          ],
                        ),
                        if (motionPayload != null) ...[
                          const SizedBox(height: 6),
                          _buildFlushMotionSummary(motionPayload),
                        ],
                        if (expanded) ...[
                          const SizedBox(height: 10),
                          Text(
                            normalised
                                ? 'Span ends ${_fmt(endTs)}'
                                    '${threshold != null ? ' · merge ≥ $threshold' : ''}'
                                    ' · ${log['span_seconds'] ?? 300}s bucket'
                                : 'Ended ${_fmt(endTs)}'
                                    '${threshold != null ? ' · merge ≥ $threshold' : ''}'
                                    ' · frames/cycle ${log['frames_per_cycle'] ?? '—'}',
                            style: OfflineFonts.inter(
                              fontSize: 12,
                              color: AppColors.textSecondary,
                            ),
                          ),
                          if (payloadMap != null) ...[
                            const SizedBox(height: 8),
                            Text(
                              normalised
                                  ? 'Individuals: '
                                      '${(payloadMap['individuals'] is List ? (payloadMap['individuals'] as List).length : '—')}'
                                      ' · source logs: $sourceLogCount'
                                      ' · people_count: ${log['people_count'] ?? '—'}'
                                  : 'People groups: ${_personGroupCount(payloadMap)}'
                                      ' · InstantMvrs: '
                                      '${(payloadMap['instant_mvrs'] is List ? (payloadMap['instant_mvrs'] as List).length : '—')}'
                                      ' · people_count: ${log['people_count'] ?? '—'}',
                              style: OfflineFonts.inter(
                                fontSize: 12,
                                color: AppColors.textPrimary,
                              ),
                            ),
                            const SizedBox(height: 8),
                            if (motionPayload != null)
                              _buildFlushMotionDetail(motionPayload),
                          ],
                        ],
                      ],
                    ),
                  ),
                ),
              );
            },
          ),
        ),
      ],
    );
  }
}
