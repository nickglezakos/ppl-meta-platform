import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../core/theme/theme_kit.dart';
import '../utils/offline_fonts.dart';

/// Shared analytics intents: Counting, Occupancy, Heatmap (FOV), Path (FOV).
/// Used only on AnalyticsScreen (Cameras pane + /analytics) for Instant and Recording.
class AnalyticsIntentsPanel extends StatelessWidget {
  const AnalyticsIntentsPanel({
    super.key,
    required this.metrics,
    required this.dataSource,
    this.isNormalised = false,
    this.occupancyThreshold = 3,
    this.heatmapGridSize = 8,
  });

  /// Precomputed metrics (from Instant logs/spans or Recording APIs).
  final AnalyticsIntentMetrics metrics;

  /// `'instant_detection'` or `'recording'`.
  final String dataSource;

  final bool isNormalised;
  final int occupancyThreshold;
  final int heatmapGridSize;

  bool get _isInstant => dataSource == 'instant_detection';

  @override
  Widget build(BuildContext context) {
    final subtitle = _isInstant
        ? (isNormalised
            ? 'Instant Detection · normalised spans + route points'
            : 'Instant Detection · flush logs + route points')
        : 'Recording · summary / time-series + FOV routes';

    final cards = [
      _CountingCard(metrics: metrics, isInstant: _isInstant),
      _OccupancyCard(
        metrics: metrics,
        threshold: occupancyThreshold,
        isInstant: _isInstant,
      ),
      _HeatmapCard(
        metrics: metrics,
        gridSize: heatmapGridSize,
        isInstant: _isInstant,
      ),
      _PathCard(metrics: metrics, isInstant: _isInstant),
    ];

    // Same section chrome as LEVEL 1 / LEVEL 2 — not a drawer.
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(
                color: Colors.teal.withOpacity(0.12),
                borderRadius: BorderRadius.circular(4),
              ),
              child: const Text(
                'INTENTS',
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.bold,
                  color: Colors.teal,
                ),
              ),
            ),
            const SizedBox(width: 8),
            const Text(
              'Analytics Intents',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        Text(
          subtitle,
          style: TextStyle(
            fontSize: 13,
            color: Colors.grey.shade600,
          ),
        ),
        const SizedBox(height: 16),
        LayoutBuilder(
          builder: (context, constraints) {
            final wide = constraints.maxWidth > 900;
            if (wide) {
              return Column(
                children: [
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(child: cards[0]),
                      const SizedBox(width: 12),
                      Expanded(child: cards[1]),
                    ],
                  ),
                  const SizedBox(height: 12),
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(child: cards[2]),
                      const SizedBox(width: 12),
                      Expanded(child: cards[3]),
                    ],
                  ),
                ],
              );
            }
            return Column(
              children: [
                for (var i = 0; i < cards.length; i++) ...[
                  if (i > 0) const SizedBox(height: 12),
                  cards[i],
                ],
              ],
            );
          },
        ),
      ],
    );
  }
}

/// Public metrics DTO for Counting / Occupancy / Heatmap / Path cards.
class AnalyticsIntentMetrics {
  const AnalyticsIntentMetrics({
    required this.rowCount,
    required this.peakPeople,
    required this.totalPeopleSum,
    required this.avgPeople,
    required this.spansAboveThreshold,
    required this.occupancySeries,
    required this.heatmap,
    required this.pathCount,
    required this.avgVelocity,
    required this.avgTimeInFrame,
    required this.samplePaths,
  });

  final int rowCount;
  final int peakPeople;
  final int totalPeopleSum;
  final double avgPeople;
  final int spansAboveThreshold;
  final List<int> occupancySeries;
  final List<List<int>> heatmap;
  final int pathCount;
  final double avgVelocity;
  final double avgTimeInFrame;
  final List<List<Offset>> samplePaths;

  factory AnalyticsIntentMetrics.empty({int gridSize = 8}) {
    return AnalyticsIntentMetrics(
      rowCount: 0,
      peakPeople: 0,
      totalPeopleSum: 0,
      avgPeople: 0,
      spansAboveThreshold: 0,
      occupancySeries: const [],
      heatmap: List.generate(gridSize, (_) => List.filled(gridSize, 0)),
      pathCount: 0,
      avgVelocity: 0,
      avgTimeInFrame: 0,
      samplePaths: const [],
    );
  }

  /// Instant Detection: compute-on-read from flush/span rows + payload routes.
  factory AnalyticsIntentMetrics.fromLogs(
    List<Map<String, dynamic>> logs, {
    required int occupancyThreshold,
    int gridSize = 8,
  }) {
    final series = <int>[];
    var peak = 0;
    var sum = 0;
    var above = 0;
    final grid = List.generate(gridSize, (_) => List.filled(gridSize, 0));
    final paths = <List<Offset>>[];
    var pathCount = 0;
    var velSum = 0.0;
    var velN = 0;
    var tifSum = 0.0;
    var tifN = 0;

    for (final log in logs) {
      final people = (log['people_count'] as num?)?.toInt() ?? 0;
      series.add(people);
      sum += people;
      if (people > peak) peak = people;
      if (people >= occupancyThreshold) above++;

      final payload = _asMap(log['payload_json']);
      final individuals = _collectIndividuals(payload);
      for (final person in individuals) {
        final tracking = _asMap(person['movement_tracking']);
        final routePoints = (tracking?['route_points'] as List?) ??
            (person['route_points'] as List?) ??
            const [];
        if (routePoints.isEmpty) continue;
        pathCount++;
        final path = <Offset>[];
        for (final raw in routePoints) {
          final pt = _asMap(raw);
          if (pt == null) continue;
          final x = (pt['center_x'] as num?)?.toDouble();
          final y = (pt['center_y'] as num?)?.toDouble();
          if (x == null || y == null) continue;
          path.add(Offset(x, y));
          final nx =
              x > 1.5 ? (x / 1920.0).clamp(0.0, 0.999) : x.clamp(0.0, 0.999);
          final ny =
              y > 1.5 ? (y / 1080.0).clamp(0.0, 0.999) : y.clamp(0.0, 0.999);
          final cx = (nx * gridSize).floor().clamp(0, gridSize - 1);
          final cy = (ny * gridSize).floor().clamp(0, gridSize - 1);
          grid[cy][cx] = grid[cy][cx] + 1;
        }
        if (path.length >= 2 && paths.length < 12) {
          paths.add(path);
        }
        final avgVel = (person['average_route_velocity'] as num?)?.toDouble() ??
            (tracking?['average_route_velocity'] as num?)?.toDouble() ??
            (_asMap(tracking?['movement_statistics'])?['average_velocity']
                    as num?)
                ?.toDouble();
        if (avgVel != null && avgVel > 0) {
          velSum += avgVel;
          velN++;
        }
        final tif = (_asMap(tracking?['movement_statistics'])
                ?['time_in_frame_seconds'] as num?)
            ?.toDouble();
        if (tif != null && tif > 0) {
          tifSum += tif;
          tifN++;
        }
      }
    }

    return AnalyticsIntentMetrics(
      rowCount: logs.length,
      peakPeople: peak,
      totalPeopleSum: sum,
      avgPeople: logs.isEmpty ? 0 : sum / logs.length,
      spansAboveThreshold: above,
      occupancySeries: series.reversed.take(24).toList().reversed.toList(),
      heatmap: grid,
      pathCount: pathCount,
      avgVelocity: velN == 0 ? 0 : velSum / velN,
      avgTimeInFrame: tifN == 0 ? 0 : tifSum / tifN,
      samplePaths: paths,
    );
  }

  /// Recording: Counting/Occupancy from summary + time-series; FOV from route-fov.
  factory AnalyticsIntentMetrics.fromRecording({
    required int totalPeople,
    required List<int> occupancySeries,
    required int occupancyThreshold,
    List<List<int>>? heatmap,
    int pathCount = 0,
    double avgVelocity = 0,
    double avgTimeInFrame = 0,
    List<List<Offset>> samplePaths = const [],
    int gridSize = 8,
  }) {
    final series = occupancySeries;
    final peak = series.isEmpty ? totalPeople : series.reduce(math.max);
    final above = series.where((c) => c >= occupancyThreshold).length;
    final sum = series.isEmpty ? totalPeople : series.fold<int>(0, (a, b) => a + b);
    final avg = series.isEmpty
        ? (totalPeople > 0 ? totalPeople.toDouble() : 0.0)
        : sum / series.length;
    return AnalyticsIntentMetrics(
      rowCount: series.isEmpty ? (totalPeople > 0 ? 1 : 0) : series.length,
      peakPeople: peak,
      totalPeopleSum: totalPeople > 0 ? totalPeople : sum,
      avgPeople: avg,
      spansAboveThreshold: above,
      occupancySeries: series.length > 24
          ? series.sublist(series.length - 24)
          : series,
      heatmap: heatmap ??
          List.generate(gridSize, (_) => List.filled(gridSize, 0)),
      pathCount: pathCount,
      avgVelocity: avgVelocity,
      avgTimeInFrame: avgTimeInFrame,
      samplePaths: samplePaths,
    );
  }

  /// Merge FOV fields from a route-fov API response into recording metrics.
  AnalyticsIntentMetrics withRouteFov(Map<String, dynamic> fov) {
    final gridRaw = fov['heatmap'];
    List<List<int>>? grid;
    if (gridRaw is List) {
      grid = gridRaw
          .map(
            (row) => row is List
                ? row.map((v) => (v as num?)?.toInt() ?? 0).toList()
                : <int>[],
          )
          .toList();
    }
    final pathsRaw = fov['sample_paths'];
    final paths = <List<Offset>>[];
    if (pathsRaw is List) {
      for (final rawPath in pathsRaw) {
        if (rawPath is! List) continue;
        final path = <Offset>[];
        for (final pt in rawPath) {
          if (pt is Map) {
            final x = (pt['x'] as num?)?.toDouble() ??
                (pt['center_x'] as num?)?.toDouble();
            final y = (pt['y'] as num?)?.toDouble() ??
                (pt['center_y'] as num?)?.toDouble();
            if (x != null && y != null) path.add(Offset(x, y));
          } else if (pt is List && pt.length >= 2) {
            path.add(Offset(
              (pt[0] as num).toDouble(),
              (pt[1] as num).toDouble(),
            ));
          }
        }
        if (path.length >= 2) paths.add(path);
        if (paths.length >= 12) break;
      }
    }
    return AnalyticsIntentMetrics(
      rowCount: rowCount,
      peakPeople: peakPeople,
      totalPeopleSum: totalPeopleSum,
      avgPeople: avgPeople,
      spansAboveThreshold: spansAboveThreshold,
      occupancySeries: occupancySeries,
      heatmap: grid ?? heatmap,
      pathCount: (fov['path_count'] as num?)?.toInt() ?? pathCount,
      avgVelocity:
          (fov['avg_velocity'] as num?)?.toDouble() ?? avgVelocity,
      avgTimeInFrame:
          (fov['avg_time_in_frame'] as num?)?.toDouble() ?? avgTimeInFrame,
      samplePaths: paths.isNotEmpty ? paths : samplePaths,
    );
  }

  static Map<String, dynamic>? _asMap(dynamic v) {
    if (v is Map<String, dynamic>) return v;
    if (v is Map) return Map<String, dynamic>.from(v);
    return null;
  }

  static List<Map<String, dynamic>> _collectIndividuals(
    Map<String, dynamic>? payload,
  ) {
    final out = <Map<String, dynamic>>[];
    if (payload == null) return out;

    void addAll(List? list) {
      if (list == null) return;
      for (final item in list) {
        final m = _asMap(item);
        if (m != null) out.add(m);
      }
    }

    final merge = _asMap(payload['hierarchical_merge']);
    addAll(merge?['merge_groups'] as List?);
    addAll(payload['person_groups'] as List?);
    addAll(payload['instant_mvrs'] as List?);
    addAll(payload['people'] as List?);
    addAll(payload['individuals'] as List?);
    if (out.isEmpty) {
      addAll(payload['flush_individuals'] as List?);
    }
    return out;
  }
}

class _CountingCard extends StatelessWidget {
  const _CountingCard({required this.metrics, required this.isInstant});
  final AnalyticsIntentMetrics metrics;
  final bool isInstant;

  @override
  Widget build(BuildContext context) {
    return _IntentCard(
      title: 'People Counting',
      icon: Icons.people_outline,
      child: metrics.rowCount == 0
          ? _EmptyHint(
              isInstant
                  ? 'No flush/span rows in range.'
                  : 'No recording people in range. Adjust filters or process videos.',
            )
          : Wrap(
              spacing: 16,
              runSpacing: 8,
              children: [
                _StatChip(
                  label: isInstant ? 'Rows' : 'Buckets',
                  value: '${metrics.rowCount}',
                ),
                _StatChip(label: 'Peak', value: '${metrics.peakPeople}'),
                _StatChip(
                  label: isInstant ? 'Avg / row' : 'Avg / bucket',
                  value: metrics.avgPeople.toStringAsFixed(1),
                ),
                _StatChip(
                  label: isInstant ? 'Sum people' : 'Total people',
                  value: '${metrics.totalPeopleSum}',
                ),
              ],
            ),
    );
  }
}

class _OccupancyCard extends StatelessWidget {
  const _OccupancyCard({
    required this.metrics,
    required this.threshold,
    required this.isInstant,
  });
  final AnalyticsIntentMetrics metrics;
  final int threshold;
  final bool isInstant;

  @override
  Widget build(BuildContext context) {
    final pct = metrics.rowCount == 0
        ? 0.0
        : 100.0 * metrics.spansAboveThreshold / metrics.rowCount;
    return _IntentCard(
      title: 'Occupancy Monitoring',
      icon: Icons.groups_2_outlined,
      child: metrics.rowCount == 0
          ? _EmptyHint(
              isInstant
                  ? 'Enable normalisation for span occupancy, or wait for flush logs.'
                  : 'No time-series people counts in range.',
            )
          : Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (!isInstant)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 6),
                    child: Text(
                      'Unique people per time bucket (not concurrent frame occupancy).',
                      style: OfflineFonts.inter(
                        fontSize: 11,
                        color: AppColors.textSecondary,
                      ),
                    ),
                  ),
                Wrap(
                  spacing: 16,
                  runSpacing: 8,
                  children: [
                    _StatChip(
                      label: 'Peak occupancy',
                      value: '${metrics.peakPeople}',
                    ),
                    _StatChip(
                      label: 'Above ≥$threshold',
                      value:
                          '${metrics.spansAboveThreshold} (${pct.toStringAsFixed(0)}%)',
                    ),
                  ],
                ),
                if (metrics.occupancySeries.isNotEmpty) ...[
                  const SizedBox(height: 8),
                  SizedBox(
                    height: 36,
                    child: CustomPaint(
                      painter: _SparklinePainter(metrics.occupancySeries),
                      child: const SizedBox.expand(),
                    ),
                  ),
                ],
              ],
            ),
    );
  }
}

class _HeatmapCard extends StatelessWidget {
  const _HeatmapCard({
    required this.metrics,
    required this.gridSize,
    required this.isInstant,
  });
  final AnalyticsIntentMetrics metrics;
  final int gridSize;
  final bool isInstant;

  @override
  Widget build(BuildContext context) {
    var maxCell = 0;
    for (final row in metrics.heatmap) {
      for (final v in row) {
        if (v > maxCell) maxCell = v;
      }
    }
    return _IntentCard(
      title: 'Heatmap (FOV)',
      icon: Icons.grid_on_outlined,
      child: maxCell == 0
          ? _EmptyHint(
              isInstant
                  ? 'No route_points in payloads yet. Run Instant Detection with movement tracking.'
                  : 'No recording route_points in range. Process videos with movement tracking.',
            )
          : SizedBox(
              height: 120,
              width: double.infinity,
              child: CustomPaint(
                painter: _HeatmapPainter(metrics.heatmap, maxCell),
                child: const SizedBox.expand(),
              ),
            ),
    );
  }
}

class _PathCard extends StatelessWidget {
  const _PathCard({required this.metrics, required this.isInstant});
  final AnalyticsIntentMetrics metrics;
  final bool isInstant;

  @override
  Widget build(BuildContext context) {
    return _IntentCard(
      title: 'Path Analysis (FOV)',
      icon: Icons.route_outlined,
      child: metrics.pathCount == 0
          ? _EmptyHint(
              isInstant
                  ? 'No movement_tracking routes in this range.'
                  : 'No recording movement routes in this range.',
            )
          : Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Wrap(
                  spacing: 16,
                  runSpacing: 8,
                  children: [
                    _StatChip(label: 'Paths', value: '${metrics.pathCount}'),
                    _StatChip(
                      label: 'Avg velocity',
                      value: metrics.avgVelocity <= 0
                          ? '--'
                          : '${metrics.avgVelocity.toStringAsFixed(1)} px/s',
                    ),
                    _StatChip(
                      label: 'Avg time in frame',
                      value: metrics.avgTimeInFrame <= 0
                          ? '--'
                          : '${metrics.avgTimeInFrame.toStringAsFixed(1)} s',
                    ),
                  ],
                ),
                if (metrics.samplePaths.isNotEmpty) ...[
                  const SizedBox(height: 8),
                  SizedBox(
                    height: 120,
                    width: double.infinity,
                    child: CustomPaint(
                      painter: _PathsPainter(metrics.samplePaths),
                      child: const SizedBox.expand(),
                    ),
                  ),
                ],
              ],
            ),
    );
  }
}

class _IntentCard extends StatelessWidget {
  const _IntentCard({
    required this.title,
    required this.icon,
    required this.child,
  });

  final String title;
  final IconData icon;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.grey.shade300),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, size: 18, color: AppColors.primary),
              const SizedBox(width: 8),
              Text(
                title,
                style: OfflineFonts.inter(
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                  color: AppColors.textPrimary,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          child,
        ],
      ),
    );
  }
}

class _StatChip extends StatelessWidget {
  const _StatChip({required this.label, required this.value});
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: OfflineFonts.inter(fontSize: 10, color: AppColors.textSecondary),
        ),
        Text(
          value,
          style: OfflineFonts.inter(
            fontSize: 14,
            fontWeight: FontWeight.w600,
            color: AppColors.textPrimary,
          ),
        ),
      ],
    );
  }
}

class _EmptyHint extends StatelessWidget {
  const _EmptyHint(this.text);
  final String text;

  @override
  Widget build(BuildContext context) {
    return Text(
      text,
      style: OfflineFonts.inter(fontSize: 12, color: AppColors.textSecondary),
    );
  }
}

class _SparklinePainter extends CustomPainter {
  _SparklinePainter(this.values);
  final List<int> values;

  @override
  void paint(Canvas canvas, Size size) {
    if (values.isEmpty) return;
    final maxV = values.reduce(math.max).clamp(1, 1 << 30);
    final paint = Paint()
      ..color = AppColors.primary
      ..strokeWidth = 2
      ..style = PaintingStyle.stroke;
    final path = Path();
    for (var i = 0; i < values.length; i++) {
      final x = values.length == 1
          ? size.width / 2
          : size.width * i / (values.length - 1);
      final y = size.height - (values[i] / maxV) * (size.height - 4) - 2;
      if (i == 0) {
        path.moveTo(x, y);
      } else {
        path.lineTo(x, y);
      }
    }
    canvas.drawPath(path, paint);
  }

  @override
  bool shouldRepaint(covariant _SparklinePainter oldDelegate) =>
      oldDelegate.values != values;
}

class _HeatmapPainter extends CustomPainter {
  _HeatmapPainter(this.grid, this.maxCell);
  final List<List<int>> grid;
  final int maxCell;

  @override
  void paint(Canvas canvas, Size size) {
    if (grid.isEmpty || maxCell <= 0) return;
    final rows = grid.length;
    final cols = grid[0].length;
    final cw = size.width / cols;
    final ch = size.height / rows;
    for (var r = 0; r < rows; r++) {
      for (var c = 0; c < cols; c++) {
        final v = grid[r][c];
        if (v <= 0) continue;
        final t = (v / maxCell).clamp(0.0, 1.0);
        final paint = Paint()
          ..color = Color.lerp(
            Colors.blue.shade100.withOpacity(0.35),
            Colors.red.shade700.withOpacity(0.85),
            t,
          )!;
        canvas.drawRect(Rect.fromLTWH(c * cw, r * ch, cw, ch), paint);
      }
    }
  }

  @override
  bool shouldRepaint(covariant _HeatmapPainter oldDelegate) =>
      oldDelegate.grid != grid || oldDelegate.maxCell != maxCell;
}

class _PathsPainter extends CustomPainter {
  _PathsPainter(this.paths);
  final List<List<Offset>> paths;

  @override
  void paint(Canvas canvas, Size size) {
    if (paths.isEmpty) return;
    double maxX = 1;
    double maxY = 1;
    for (final p in paths) {
      for (final o in p) {
        if (o.dx > maxX) maxX = o.dx;
        if (o.dy > maxY) maxY = o.dy;
      }
    }
    final norm = maxX <= 1.5 && maxY <= 1.5;
    final paint = Paint()
      ..strokeWidth = 1.5
      ..style = PaintingStyle.stroke
      ..color = AppColors.primary.withOpacity(0.7);

    for (final pts in paths) {
      if (pts.length < 2) continue;
      final path = Path();
      for (var i = 0; i < pts.length; i++) {
        final nx = norm
            ? pts[i].dx.clamp(0.0, 1.0)
            : (pts[i].dx / maxX).clamp(0.0, 1.0);
        final ny = norm
            ? pts[i].dy.clamp(0.0, 1.0)
            : (pts[i].dy / maxY).clamp(0.0, 1.0);
        final x = nx * size.width;
        final y = ny * size.height;
        if (i == 0) {
          path.moveTo(x, y);
        } else {
          path.lineTo(x, y);
        }
      }
      canvas.drawPath(path, paint);
    }
  }

  @override
  bool shouldRepaint(covariant _PathsPainter oldDelegate) =>
      oldDelegate.paths != paths;
}
