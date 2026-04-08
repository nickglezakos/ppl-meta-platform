import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:intl/intl.dart';
import '../../core/theme/app_theme.dart';
import '../../providers/monitoring_providers.dart';

/// Chart section for the monitoring dashboard.
/// Displays detection throughput, success rate, active sessions,
/// processing time distribution, and MVR match trends.
class MonitoringChartsWidget extends ConsumerWidget {
  const MonitoringChartsWidget({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final chartData = ref.watch(monitoringChartDataProvider);

    return chartData.when(
      data: (data) => _buildCharts(context, data),
      loading: () => const Padding(
        padding: EdgeInsets.symmetric(vertical: 32),
        child: Center(child: CircularProgressIndicator()),
      ),
      error: (error, _) => _buildChartError(context, error),
    );
  }

  Widget _buildCharts(BuildContext context, MonitoringChartData data) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Row 1: Throughput + Success Rate
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(child: _DetectionThroughputChart(data: data.detectionThroughput)),
            const SizedBox(width: 16),
            Expanded(child: _SuccessRateTrendChart(data: data.successRateTrend)),
          ],
        ),
        const SizedBox(height: 16),
        // Row 2: Active Sessions + Processing Time
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(child: _ActiveSessionsChart(data: data.activeSessionsTrend)),
            const SizedBox(width: 16),
            Expanded(child: _ProcessingTimeDistributionChart(data: data.processingTimeDistribution)),
          ],
        ),
        const SizedBox(height: 16),
        // Row 3: MVR Match Trend (full width)
        _MvrMatchTrendChart(data: data.mvrMatchTrend),
      ],
    );
  }

  Widget _buildChartError(BuildContext context, Object error) {
    return Card(
      elevation: 1,
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Row(
          children: [
            Icon(Icons.bar_chart, color: AppColors.textSecondary, size: 32),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Charts unavailable',
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      color: AppColors.textSecondary,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    error.toString(),
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: AppColors.textTertiary,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// =============================================================================
// CHART CARD WRAPPER
// =============================================================================

class _ChartCard extends StatelessWidget {
  final String title;
  final IconData icon;
  final Color iconColor;
  final Widget chart;
  final String? emptyMessage;
  final bool isEmpty;

  const _ChartCard({
    required this.title,
    required this.icon,
    required this.iconColor,
    required this.chart,
    this.emptyMessage,
    this.isEmpty = false,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 1,
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(6),
                  decoration: BoxDecoration(
                    color: iconColor.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: Icon(icon, color: iconColor, size: 18),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    title,
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 20),
            SizedBox(
              height: 200,
              child: isEmpty ? _buildEmptyState(context) : chart,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildEmptyState(BuildContext context) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.show_chart, color: AppColors.textTertiary, size: 40),
          const SizedBox(height: 8),
          Text(
            emptyMessage ?? 'No data available yet',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
              color: AppColors.textTertiary,
            ),
          ),
        ],
      ),
    );
  }
}

// =============================================================================
// DETECTION THROUGHPUT (Line Chart)
// =============================================================================

class _DetectionThroughputChart extends StatelessWidget {
  final List<TimeValuePoint> data;
  const _DetectionThroughputChart({required this.data});

  @override
  Widget build(BuildContext context) {
    final spots = data.asMap().entries.map((e) {
      return FlSpot(e.key.toDouble(), e.value.value);
    }).toList();

    return _ChartCard(
      title: 'Detection Throughput (24h)',
      icon: Icons.speed,
      iconColor: AppColors.primary,
      isEmpty: spots.isEmpty,
      emptyMessage: 'No detections in the last 24 hours',
      chart: LineChart(
        LineChartData(
          gridData: FlGridData(
            show: true,
            drawVerticalLine: false,
            horizontalInterval: _calcInterval(spots),
            getDrawingHorizontalLine: (_) => FlLine(
              color: AppColors.border,
              strokeWidth: 1,
            ),
          ),
          titlesData: FlTitlesData(
            topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
            rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
            bottomTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                reservedSize: 28,
                interval: _xLabelInterval(spots.length),
                getTitlesWidget: (value, _) {
                  final idx = value.toInt();
                  if (idx < 0 || idx >= data.length) return const SizedBox.shrink();
                  return Padding(
                    padding: const EdgeInsets.only(top: 6),
                    child: Text(
                      DateFormat('HH:mm').format(data[idx].timestamp),
                      style: const TextStyle(color: AppColors.textTertiary, fontSize: 10),
                    ),
                  );
                },
              ),
            ),
            leftTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                reservedSize: 36,
                interval: _calcInterval(spots),
                getTitlesWidget: (value, _) => Text(
                  value.toInt().toString(),
                  style: const TextStyle(color: AppColors.textTertiary, fontSize: 10),
                ),
              ),
            ),
          ),
          borderData: FlBorderData(show: false),
          lineBarsData: [
            LineChartBarData(
              spots: spots,
              isCurved: true,
              preventCurveOverShooting: true,
              color: AppColors.primary,
              barWidth: 2,
              dotData: const FlDotData(show: false),
              belowBarData: BarAreaData(
                show: true,
                color: AppColors.primary.withOpacity(0.1),
              ),
            ),
          ],
          lineTouchData: LineTouchData(
            touchTooltipData: LineTouchTooltipData(
              getTooltipItems: (touchedSpots) {
                return touchedSpots.map((spot) {
                  final idx = spot.x.toInt();
                  final label = idx >= 0 && idx < data.length
                      ? DateFormat('HH:mm').format(data[idx].timestamp)
                      : '';
                  return LineTooltipItem(
                    '$label\n${spot.y.toInt()} detections',
                    const TextStyle(color: AppColors.textPrimary, fontSize: 12),
                  );
                }).toList();
              },
            ),
          ),
        ),
      ),
    );
  }

  double _calcInterval(List<FlSpot> spots) {
    if (spots.isEmpty) return 1;
    final maxY = spots.map((s) => s.y).reduce((a, b) => a > b ? a : b);
    if (maxY <= 5) return 1;
    return (maxY / 4).ceilToDouble();
  }

  double _xLabelInterval(int count) {
    if (count <= 6) return 1;
    return (count / 6).ceilToDouble();
  }
}

// =============================================================================
// SUCCESS RATE TREND (Line Chart)
// =============================================================================

class _SuccessRateTrendChart extends StatelessWidget {
  final List<SuccessRatePoint> data;
  const _SuccessRateTrendChart({required this.data});

  @override
  Widget build(BuildContext context) {
    final spots = data.asMap().entries.map((e) {
      return FlSpot(e.key.toDouble(), e.value.rate);
    }).toList();

    return _ChartCard(
      title: 'Success Rate Trend (7d)',
      icon: Icons.trending_up,
      iconColor: AppColors.success,
      isEmpty: spots.isEmpty,
      emptyMessage: 'No workflow data in the last 7 days',
      chart: LineChart(
        LineChartData(
          minY: 0,
          maxY: 100,
          gridData: FlGridData(
            show: true,
            drawVerticalLine: false,
            horizontalInterval: 25,
            getDrawingHorizontalLine: (_) => FlLine(
              color: AppColors.border,
              strokeWidth: 1,
            ),
          ),
          titlesData: FlTitlesData(
            topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
            rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
            bottomTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                reservedSize: 28,
                getTitlesWidget: (value, _) {
                  final idx = value.toInt();
                  if (idx < 0 || idx >= data.length) return const SizedBox.shrink();
                  return Padding(
                    padding: const EdgeInsets.only(top: 6),
                    child: Text(
                      DateFormat('MM/dd').format(data[idx].date),
                      style: const TextStyle(color: AppColors.textTertiary, fontSize: 10),
                    ),
                  );
                },
              ),
            ),
            leftTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                reservedSize: 36,
                interval: 25,
                getTitlesWidget: (value, _) => Text(
                  '${value.toInt()}%',
                  style: const TextStyle(color: AppColors.textTertiary, fontSize: 10),
                ),
              ),
            ),
          ),
          borderData: FlBorderData(show: false),
          lineBarsData: [
            LineChartBarData(
              spots: spots,
              isCurved: true,
              preventCurveOverShooting: true,
              color: AppColors.success,
              barWidth: 2,
              dotData: FlDotData(
                show: true,
                getDotPainter: (_, __, ___, ____) => FlDotCirclePainter(
                  radius: 3,
                  color: AppColors.success,
                  strokeColor: AppColors.surface,
                  strokeWidth: 1,
                ),
              ),
              belowBarData: BarAreaData(
                show: true,
                color: AppColors.success.withOpacity(0.08),
              ),
            ),
          ],
          lineTouchData: LineTouchData(
            touchTooltipData: LineTouchTooltipData(
              getTooltipItems: (touchedSpots) {
                return touchedSpots.map((spot) {
                  final idx = spot.x.toInt();
                  if (idx < 0 || idx >= data.length) {
                    return LineTooltipItem('', const TextStyle());
                  }
                  final pt = data[idx];
                  return LineTooltipItem(
                    '${DateFormat('MM/dd').format(pt.date)}\n${pt.rate}% (${pt.completed}/${pt.completed + pt.failed})',
                    const TextStyle(color: AppColors.textPrimary, fontSize: 12),
                  );
                }).toList();
              },
            ),
          ),
        ),
      ),
    );
  }
}

// =============================================================================
// ACTIVE SESSIONS OVER TIME (Area Chart)
// =============================================================================

class _ActiveSessionsChart extends StatelessWidget {
  final List<TimeValuePoint> data;
  const _ActiveSessionsChart({required this.data});

  @override
  Widget build(BuildContext context) {
    final spots = data.asMap().entries.map((e) {
      return FlSpot(e.key.toDouble(), e.value.value);
    }).toList();

    return _ChartCard(
      title: 'Active Sessions (24h)',
      icon: Icons.people,
      iconColor: AppColors.info,
      isEmpty: spots.isEmpty,
      emptyMessage: 'No sessions in the last 24 hours',
      chart: LineChart(
        LineChartData(
          gridData: FlGridData(
            show: true,
            drawVerticalLine: false,
            horizontalInterval: _calcInterval(spots),
            getDrawingHorizontalLine: (_) => FlLine(
              color: AppColors.border,
              strokeWidth: 1,
            ),
          ),
          titlesData: FlTitlesData(
            topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
            rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
            bottomTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                reservedSize: 28,
                interval: _xLabelInterval(spots.length),
                getTitlesWidget: (value, _) {
                  final idx = value.toInt();
                  if (idx < 0 || idx >= data.length) return const SizedBox.shrink();
                  return Padding(
                    padding: const EdgeInsets.only(top: 6),
                    child: Text(
                      DateFormat('HH:mm').format(data[idx].timestamp),
                      style: const TextStyle(color: AppColors.textTertiary, fontSize: 10),
                    ),
                  );
                },
              ),
            ),
            leftTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                reservedSize: 36,
                interval: _calcInterval(spots),
                getTitlesWidget: (value, _) => Text(
                  value.toInt().toString(),
                  style: const TextStyle(color: AppColors.textTertiary, fontSize: 10),
                ),
              ),
            ),
          ),
          borderData: FlBorderData(show: false),
          lineBarsData: [
            LineChartBarData(
              spots: spots,
              isCurved: true,
              preventCurveOverShooting: true,
              color: AppColors.info,
              barWidth: 2,
              dotData: const FlDotData(show: false),
              belowBarData: BarAreaData(
                show: true,
                color: AppColors.info.withOpacity(0.12),
              ),
            ),
          ],
          lineTouchData: LineTouchData(
            touchTooltipData: LineTouchTooltipData(
              getTooltipItems: (touchedSpots) {
                return touchedSpots.map((spot) {
                  final idx = spot.x.toInt();
                  final label = idx >= 0 && idx < data.length
                      ? DateFormat('HH:mm').format(data[idx].timestamp)
                      : '';
                  return LineTooltipItem(
                    '$label\n${spot.y.toInt()} sessions',
                    const TextStyle(color: AppColors.textPrimary, fontSize: 12),
                  );
                }).toList();
              },
            ),
          ),
        ),
      ),
    );
  }

  double _calcInterval(List<FlSpot> spots) {
    if (spots.isEmpty) return 1;
    final maxY = spots.map((s) => s.y).reduce((a, b) => a > b ? a : b);
    if (maxY <= 5) return 1;
    return (maxY / 4).ceilToDouble();
  }

  double _xLabelInterval(int count) {
    if (count <= 6) return 1;
    return (count / 6).ceilToDouble();
  }
}

// =============================================================================
// PROCESSING TIME DISTRIBUTION (Bar Chart)
// =============================================================================

class _ProcessingTimeDistributionChart extends StatelessWidget {
  final List<ProcessingTimeBucket> data;
  const _ProcessingTimeDistributionChart({required this.data});

  @override
  Widget build(BuildContext context) {
    final hasData = data.any((b) => b.count > 0);
    final groups = data.asMap().entries.map((e) {
      return BarChartGroupData(
        x: e.key,
        barRods: [
          BarChartRodData(
            toY: e.value.count.toDouble(),
            color: _barColor(e.key),
            width: 24,
            borderRadius: const BorderRadius.vertical(top: Radius.circular(4)),
          ),
        ],
      );
    }).toList();

    return _ChartCard(
      title: 'Processing Time Distribution',
      icon: Icons.timer,
      iconColor: AppColors.warning,
      isEmpty: !hasData,
      emptyMessage: 'No processing data available',
      chart: BarChart(
        BarChartData(
          gridData: FlGridData(
            show: true,
            drawVerticalLine: false,
            getDrawingHorizontalLine: (_) => FlLine(
              color: AppColors.border,
              strokeWidth: 1,
            ),
          ),
          titlesData: FlTitlesData(
            topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
            rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
            bottomTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                reservedSize: 28,
                getTitlesWidget: (value, _) {
                  final idx = value.toInt();
                  if (idx < 0 || idx >= data.length) return const SizedBox.shrink();
                  return Padding(
                    padding: const EdgeInsets.only(top: 6),
                    child: Text(
                      data[idx].bucket,
                      style: const TextStyle(color: AppColors.textTertiary, fontSize: 9),
                    ),
                  );
                },
              ),
            ),
            leftTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                reservedSize: 32,
                getTitlesWidget: (value, _) => Text(
                  value.toInt().toString(),
                  style: const TextStyle(color: AppColors.textTertiary, fontSize: 10),
                ),
              ),
            ),
          ),
          borderData: FlBorderData(show: false),
          barGroups: groups,
          barTouchData: BarTouchData(
            touchTooltipData: BarTouchTooltipData(
              getTooltipItem: (group, groupIndex, rod, rodIndex) {
                final bucket = groupIndex < data.length ? data[groupIndex].bucket : '';
                return BarTooltipItem(
                  '$bucket\n${rod.toY.toInt()} workflows',
                  const TextStyle(color: AppColors.textPrimary, fontSize: 12),
                );
              },
            ),
          ),
        ),
      ),
    );
  }

  Color _barColor(int index) {
    const colors = [
      AppColors.success,    // <1s  - green (fast)
      Color(0xFF66BB6A),    // 1-5s - light green
      AppColors.info,       // 5-15s - blue
      AppColors.warning,    // 15-30s - yellow
      Color(0xFFFF9800),    // 30-60s - orange
      AppColors.error,      // >60s - red (slow)
    ];
    return index < colors.length ? colors[index] : AppColors.textSecondary;
  }
}

// =============================================================================
// MVR MATCH TREND (Bar Chart)
// =============================================================================

class _MvrMatchTrendChart extends StatelessWidget {
  final List<MvrMatchPoint> data;
  const _MvrMatchTrendChart({required this.data});

  @override
  Widget build(BuildContext context) {
    final hasData = data.any((d) => d.matches > 0 || d.mvrCreated > 0);
    final groups = data.asMap().entries.map((e) {
      final d = e.value;
      return BarChartGroupData(
        x: e.key,
        barRods: [
          BarChartRodData(
            toY: d.merges.toDouble() + d.mappings.toDouble(),
            color: AppColors.secondary,
            width: 14,
            borderRadius: const BorderRadius.vertical(top: Radius.circular(4)),
          ),
          BarChartRodData(
            toY: d.mvrCreated.toDouble(),
            color: AppColors.primary,
            width: 14,
            borderRadius: const BorderRadius.vertical(top: Radius.circular(4)),
          ),
        ],
        barsSpace: 2,
      );
    }).toList();

    return _ChartCard(
      title: 'MVR Activity (7d)',
      icon: Icons.compare_arrows,
      iconColor: AppColors.secondary,
      isEmpty: !hasData,
      emptyMessage: 'No MVR activity in the last 7 days',
      chart: BarChart(
        BarChartData(
          gridData: FlGridData(
            show: true,
            drawVerticalLine: false,
            getDrawingHorizontalLine: (_) => FlLine(
              color: AppColors.border,
              strokeWidth: 1,
            ),
          ),
          titlesData: FlTitlesData(
            topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
            rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
            bottomTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                reservedSize: 28,
                getTitlesWidget: (value, _) {
                  final idx = value.toInt();
                  if (idx < 0 || idx >= data.length) return const SizedBox.shrink();
                  return Padding(
                    padding: const EdgeInsets.only(top: 6),
                    child: Text(
                      DateFormat('MM/dd').format(data[idx].date),
                      style: const TextStyle(color: AppColors.textTertiary, fontSize: 10),
                    ),
                  );
                },
              ),
            ),
            leftTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                reservedSize: 32,
                getTitlesWidget: (value, _) => Text(
                  value.toInt().toString(),
                  style: const TextStyle(color: AppColors.textTertiary, fontSize: 10),
                ),
              ),
            ),
          ),
          borderData: FlBorderData(show: false),
          barGroups: groups,
          barTouchData: BarTouchData(
            touchTooltipData: BarTouchTooltipData(
              getTooltipItem: (group, groupIndex, rod, rodIndex) {
                final label = groupIndex < data.length
                    ? DateFormat('MM/dd').format(data[groupIndex].date)
                    : '';
                if (groupIndex >= data.length) {
                  return BarTooltipItem('', const TextStyle());
                }
                final d = data[groupIndex];
                final text = rodIndex == 0
                    ? '$label\n${d.merges} merges + ${d.mappings} links'
                    : '$label\n${d.mvrCreated} MVR created';
                return BarTooltipItem(
                  text,
                  const TextStyle(color: AppColors.textPrimary, fontSize: 12),
                );
              },
            ),
          ),
        ),
      ),
    );
  }
}
