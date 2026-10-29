import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/providers/camera_providers.dart';
import '../../../core/theme/theme_kit.dart';
import '../../../models/cross_video_analysis_models.dart';
import '../../../providers/settings_providers.dart';
import '../../../screens/person_objects_detail_screen.dart';
import '../../../utils/offline_fonts.dart';
import '../../../widgets/collections_search_dialog.dart';

/// Camera content-pane view of Instant Detection flush logs
/// (Media `instant_detection_logs` — separate from Automation action logs).
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

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
      _expandedId = null;
    });
    try {
      final client = ref.read(mediaApiClientProvider);
      final rows = await client.listInstantDetectionLogs(
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

  String _fmt(dynamic value) {
    if (value == null) return '—';
    final s = value.toString();
    if (s.length >= 19 && s.contains('T')) {
      return s.substring(0, 19).replaceFirst('T', ' ');
    }
    return s;
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
    if (tracking == null) return;
    record['movement_tracking'] = {
      'route_points':
          List<dynamic>.from(tracking['route_points'] as List? ?? const []),
      'movement_statistics': Map<String, dynamic>.from(
        tracking['movement_statistics'] as Map? ?? const {},
      ),
    };
    record['route_points'] =
        List<dynamic>.from(tracking['route_points'] as List? ?? const []);
    if (tracking['average_route_velocity'] != null) {
      record['average_route_velocity'] = tracking['average_route_velocity'];
    } else {
      final stats = tracking['movement_statistics'];
      if (stats is Map && stats['average_velocity'] != null) {
        record['average_route_velocity'] = stats['average_velocity'];
      }
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
      final logs = await client.listInstantDetectionLogs(
        cameraDeviceId: widget.cameraDeviceId,
        startTime: startTime,
        endTime: endTime,
        limit: 500,
      );

      if (logs.isEmpty) {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('No Instant Detection logs in that date range'),
          ),
        );
        return;
      }

      // People-level individuals from each flush (hierarchical winners),
      // not raw per-cycle InstantMvrs.
      final flushIndividuals = _collectFlushIndividuals(logs);
      if (flushIndividuals.isEmpty) {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('No individuals found in matching logs'),
          ),
        );
        return;
      }

      final generalSettings = ref.read(generalSettingsProvider).valueOrNull;
      final mergeRule = generalSettings?.mergeIndividualsRule ?? 'none';
      final mergeThreshold =
          generalSettings?.mergeIndividualsThreshold ?? 0.70;
      // Match Collections recording search: only `auto` merges at search time.
      // `semi` is treated like `none` (no semi-auto interactive merge here).
      final autoMerge = mergeRule == 'auto';

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
        },
        'hierarchical_merge_applied': autoMerge,
        'merge_rule_applied': mergeRule,
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
                'Could not load Instant Detection logs',
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
    if (_logs.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                Icons.receipt_long_outlined,
                size: 48,
                color: AppColors.textSecondary.withOpacity(0.5),
              ),
              const SizedBox(height: 12),
              Text(
                'No Instant Detection flush logs yet',
                style: OfflineFonts.inter(
                  fontSize: 15,
                  fontWeight: FontWeight.w600,
                  color: AppColors.textPrimary,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                'Logs appear after Y-cycle flush (re-group + merge). '
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
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 4),
          child: Row(
            children: [
              Expanded(
                child: Text(
                  'Instant Detection logs',
                  style: OfflineFonts.inter(
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                    color: AppColors.textPrimary,
                  ),
                ),
              ),
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
        ),
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
              }

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
                                _fmt(log['flush_started_at']),
                                style: OfflineFonts.inter(
                                  fontSize: 13,
                                  fontWeight: FontWeight.w600,
                                  color: AppColors.textPrimary,
                                ),
                              ),
                            ),
                            Text(
                              '$people people · $cycles cycles',
                              style: OfflineFonts.inter(
                                fontSize: 12,
                                color: AppColors.textSecondary,
                              ),
                            ),
                          ],
                        ),
                        if (expanded) ...[
                          const SizedBox(height: 10),
                          Text(
                            'Ended ${_fmt(log['flush_ended_at'])}'
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
                              'People groups: ${_personGroupCount(payloadMap)}'
                              ' · InstantMvrs: '
                              '${(payloadMap['instant_mvrs'] is List ? (payloadMap['instant_mvrs'] as List).length : '—')}'
                              ' · people_count: ${log['people_count'] ?? '—'}',
                              style: OfflineFonts.inter(
                                fontSize: 12,
                                color: AppColors.textPrimary,
                              ),
                            ),
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
