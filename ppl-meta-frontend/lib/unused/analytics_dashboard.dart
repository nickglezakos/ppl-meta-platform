import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:fl_chart/fl_chart.dart';
import '../../providers/analytics_providers.dart';

/// Analytics dashboard for face detection results and performance metrics
/// Provides comprehensive visualization of detection data, trends, and insights
class AnalyticsDashboard extends ConsumerStatefulWidget {
  const AnalyticsDashboard({Key? key}) : super(key: key);

  @override
  ConsumerState<AnalyticsDashboard> createState() => _AnalyticsDashboardState();
}

class _AnalyticsDashboardState extends ConsumerState<AnalyticsDashboard>
    with TickerProviderStateMixin {
  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 4, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Analytics Dashboard'),
        bottom: TabBar(
          controller: _tabController,
          tabs: const [
            Tab(icon: Icon(Icons.dashboard), text: 'Overview'),
            Tab(icon: Icon(Icons.face), text: 'Detections'),
            Tab(icon: Icon(Icons.speed), text: 'Performance'),
            Tab(icon: Icon(Icons.insights), text: 'Insights'),
          ],
        ),
        actions: [
          IconButton(
            onPressed: () => _showDateRangePicker(),
            icon: const Icon(Icons.date_range),
            tooltip: 'Select Date Range',
          ),
          IconButton(
            onPressed: () => _exportAnalytics(),
            icon: const Icon(Icons.file_download),
            tooltip: 'Export Data',
          ),
          IconButton(
            onPressed: () => _refreshData(),
            icon: const Icon(Icons.refresh),
            tooltip: 'Refresh',
          ),
        ],
      ),
      body: TabBarView(
        controller: _tabController,
        children: [
          _buildOverviewTab(),
          _buildDetectionsTab(),
          _buildPerformanceTab(),
          _buildInsightsTab(),
        ],
      ),
    );
  }

  Widget _buildOverviewTab() {
    final overviewStats = ref.watch(analyticsOverviewProvider);
    final timeRange = ref.watch(analyticsTimeRangeProvider);

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Time Range Selector
          _buildTimeRangeSelector(timeRange),
          const SizedBox(height: 24),

          // Key Metrics Cards
          overviewStats.when(
            data: (stats) => Column(
              children: [
                Row(
                  children: [
                    Expanded(
                      child: _buildMetricCard(
                        title: 'Total Detections',
                        value: '${stats.totalDetections}',
                        icon: Icons.face,
                        color: Colors.blue,
                        trend: stats.detectionsTrend,
                      ),
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: _buildMetricCard(
                        title: 'Unique Faces',
                        value: '${stats.uniqueFaces}',
                        icon: Icons.people,
                        color: Colors.green,
                        trend: stats.uniqueFacesTrend,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                Row(
                  children: [
                    Expanded(
                      child: _buildMetricCard(
                        title: 'Active Cameras',
                        value: '${stats.activeCameras}',
                        icon: Icons.videocam,
                        color: Colors.orange,
                        trend: stats.activeCamerasTrend,
                      ),
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: _buildMetricCard(
                        title: 'Avg Confidence',
                        value: '${stats.averageConfidence.toStringAsFixed(1)}%',
                        icon: Icons.verified,
                        color: Colors.purple,
                        trend: stats.confidenceTrend,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 24),

                // Detection Trends Chart
                _buildDetectionTrendsChart(stats.detectionTrends),
                const SizedBox(height: 24),

                // Camera Activity Chart
                _buildCameraActivityChart(stats.cameraActivity),
                const SizedBox(height: 24),

                // Recent Activity Feed
                _buildRecentActivityFeed(stats.recentActivity),
              ],
            ),
            loading: () => const Center(
              child: Padding(
                padding: EdgeInsets.all(64),
                child: CircularProgressIndicator(),
              ),
            ),
            error: (error, stack) => Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Icon(Icons.error, size: 64, color: Colors.red),
                  const SizedBox(height: 16),
                  Text('Error loading analytics: $error'),
                  const SizedBox(height: 16),
                  ElevatedButton(
                    onPressed: () => ref.refresh(analyticsOverviewProvider),
                    child: const Text('Retry'),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDetectionsTab() {
    final detectionsData = ref.watch(detectionsAnalyticsProvider);

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Detections Filter Controls
          _buildDetectionsFilters(),
          const SizedBox(height: 24),

          detectionsData.when(
            data: (data) => Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Detection Heatmap
                _buildDetectionHeatmap(data.heatmapData),
                const SizedBox(height: 24),

                // Face Recognition Accuracy
                _buildRecognitionAccuracyChart(data.recognitionAccuracy),
                const SizedBox(height: 24),

                // Detection Confidence Distribution
                _buildConfidenceDistributionChart(data.confidenceDistribution),
                const SizedBox(height: 24),

                // Top Detected Faces
                _buildTopDetectedFaces(data.topDetectedFaces),
                const SizedBox(height: 24),

                // Detection Timeline
                _buildDetectionTimeline(data.detectionTimeline),
              ],
            ),
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (error, stack) => Center(
              child: Text('Error loading detection data: $error'),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPerformanceTab() {
    final performanceData = ref.watch(performanceAnalyticsProvider);

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          performanceData.when(
            data: (data) => Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // System Performance Overview
                _buildSystemPerformanceOverview(data.systemMetrics),
                const SizedBox(height: 24),

                // Processing Speed Chart
                _buildProcessingSpeedChart(data.processingSpeed),
                const SizedBox(height: 24),

                // Camera Performance Comparison
                _buildCameraPerformanceComparison(data.cameraPerformance),
                const SizedBox(height: 24),

                // Resource Usage Charts
                _buildResourceUsageCharts(data.resourceUsage),
                const SizedBox(height: 24),

                // Error Rate Analysis
                _buildErrorRateAnalysis(data.errorRates),
              ],
            ),
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (error, stack) => Center(
              child: Text('Error loading performance data: $error'),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildInsightsTab() {
    final insightsData = ref.watch(insightsAnalyticsProvider);

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          insightsData.when(
            data: (data) => Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Key Insights Cards
                _buildKeyInsights(data.keyInsights),
                const SizedBox(height: 24),

                // Peak Activity Analysis
                _buildPeakActivityAnalysis(data.peakActivity),
                const SizedBox(height: 24),

                // Face Recognition Patterns
                _buildRecognitionPatterns(data.recognitionPatterns),
                const SizedBox(height: 24),

                // Recommendations
                _buildRecommendations(data.recommendations),
                const SizedBox(height: 24),

                // Anomaly Detection
                _buildAnomalyDetection(data.anomalies),
              ],
            ),
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (error, stack) => Center(
              child: Text('Error loading insights: $error'),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTimeRangeSelector(AnalyticsTimeRange timeRange) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            const Icon(Icons.date_range),
            const SizedBox(width: 8),
            Text(
              'Time Range:',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Wrap(
                spacing: 8,
                children: AnalyticsTimeRange.values.map((range) {
                  final isSelected = timeRange == range;
                  return FilterChip(
                    label: Text(range.displayName),
                    selected: isSelected,
                    onSelected: (selected) {
                      if (selected) {
                        ref.read(analyticsTimeRangeProvider.notifier).setTimeRange(range);
                      }
                    },
                  );
                }).toList(),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildMetricCard({
    required String title,
    required String value,
    required IconData icon,
    required Color color,
    required double trend,
  }) {
    final trendIcon = trend > 0 
        ? Icons.trending_up 
        : trend < 0 
            ? Icons.trending_down 
            : Icons.trending_flat;
    final trendColor = trend > 0 
        ? Colors.green 
        : trend < 0 
            ? Colors.red 
            : Colors.grey;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(icon, color: color),
                const SizedBox(width: 8),
                Text(
                  title,
                  style: Theme.of(context).textTheme.titleSmall,
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              value,
              style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                color: color,
                fontWeight: FontWeight.bold,
              ),
            ),
            Row(
              children: [
                Icon(
                  trendIcon,
                  size: 16,
                  color: trendColor,
                ),
                const SizedBox(width: 4),
                Text(
                  '${trend.abs().toStringAsFixed(1)}%',
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: trendColor,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDetectionTrendsChart(List<DetectionTrendData> trends) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Detection Trends',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 16),
            SizedBox(
              height: 200,
              child: LineChart(
                LineChartData(
                  gridData: FlGridData(show: true),
                  titlesData: FlTitlesData(
                    leftTitles: AxisTitles(
                      sideTitles: SideTitles(showTitles: true),
                    ),
                    bottomTitles: AxisTitles(
                      sideTitles: SideTitles(
                        showTitles: true,
                        getTitlesWidget: (value, meta) {
                          // Format timestamp to readable date
                          final date = DateTime.fromMillisecondsSinceEpoch(value.toInt());
                          return Text(
                            '${date.month}/${date.day}',
                            style: Theme.of(context).textTheme.bodySmall,
                          );
                        },
                      ),
                    ),
                    topTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
                    rightTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
                  ),
                  borderData: FlBorderData(show: true),
                  lineBarsData: [
                    LineChartBarData(
                      spots: trends.map((data) => FlSpot(
                        data.timestamp.millisecondsSinceEpoch.toDouble(),
                        data.count.toDouble(),
                      )).toList(),
                      isCurved: true,
                      color: Colors.blue,
                      barWidth: 3,
                      dotData: FlDotData(show: false),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildCameraActivityChart(List<CameraActivityData> activity) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Camera Activity',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 16),
            SizedBox(
              height: 200,
              child: BarChart(
                BarChartData(
                  alignment: BarChartAlignment.spaceAround,
                  maxY: activity.isNotEmpty 
                      ? activity.map((d) => d.detectionCount).reduce((a, b) => a > b ? a : b).toDouble() * 1.2
                      : 100,
                  barTouchData: BarTouchData(enabled: true),
                  titlesData: FlTitlesData(
                    leftTitles: AxisTitles(
                      sideTitles: SideTitles(showTitles: true),
                    ),
                    bottomTitles: AxisTitles(
                      sideTitles: SideTitles(
                        showTitles: true,
                        getTitlesWidget: (value, meta) {
                          if (value.toInt() < activity.length) {
                            return Text(
                              activity[value.toInt()].cameraName,
                              style: Theme.of(context).textTheme.bodySmall,
                            );
                          }
                          return const Text('');
                        },
                      ),
                    ),
                    topTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
                    rightTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
                  ),
                  borderData: FlBorderData(show: false),
                  barGroups: activity.asMap().entries.map((entry) {
                    return BarChartGroupData(
                      x: entry.key,
                      barRods: [
                        BarChartRodData(
                          toY: entry.value.detectionCount.toDouble(),
                          color: Colors.blue,
                          width: 20,
                        ),
                      ],
                    );
                  }).toList(),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildRecentActivityFeed(List<RecentActivityItem> activity) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  'Recent Activity',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                TextButton(
                  onPressed: () => _tabController.animateTo(1),
                  child: const Text('View All'),
                ),
              ],
            ),
            const SizedBox(height: 16),
            ...activity.take(5).map((item) {
              return ListTile(
                leading: CircleAvatar(
                  backgroundColor: _getActivityColor(item.type),
                  child: Icon(
                    _getActivityIcon(item.type),
                    color: Colors.white,
                  ),
                ),
                title: Text(item.description),
                subtitle: Text(_formatRelativeTime(item.timestamp)),
                trailing: item.confidence != null
                    ? Text('${item.confidence!.toStringAsFixed(1)}%')
                    : null,
              );
            }).toList(),
          ],
        ),
      ),
    );
  }

  Widget _buildDetectionsFilters() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Filter Detections',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: DropdownButtonFormField<String?>(
                    decoration: const InputDecoration(
                      labelText: 'Camera',
                      border: OutlineInputBorder(),
                    ),
                    value: ref.watch(detectionsFilterProvider).selectedCamera,
                    items: const [
                      DropdownMenuItem(value: null, child: Text('All Cameras')),
                      // Add camera options dynamically
                    ],
                    onChanged: (camera) {
                      ref.read(detectionsFilterProvider.notifier).setCamera(camera);
                    },
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: DropdownButtonFormField<double?>(
                    decoration: const InputDecoration(
                      labelText: 'Min Confidence',
                      border: OutlineInputBorder(),
                    ),
                    value: ref.watch(detectionsFilterProvider).minConfidence,
                    items: const [
                      DropdownMenuItem(value: null, child: Text('Any')),
                      DropdownMenuItem(value: 0.5, child: Text('50%')),
                      DropdownMenuItem(value: 0.7, child: Text('70%')),
                      DropdownMenuItem(value: 0.9, child: Text('90%')),
                    ],
                    onChanged: (confidence) {
                      ref.read(detectionsFilterProvider.notifier).setMinConfidence(confidence);
                    },
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDetectionHeatmap(List<HeatmapData> heatmapData) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Detection Heatmap (24 Hours)',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 16),
            SizedBox(
              height: 150,
              child: GridView.builder(
                gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                  crossAxisCount: 24,
                  childAspectRatio: 1,
                ),
                itemCount: 24,
                itemBuilder: (context, index) {
                  final intensity = heatmapData.isNotEmpty && index < heatmapData.length
                      ? heatmapData[index].intensity
                      : 0.0;
                  return Container(
                    margin: const EdgeInsets.all(1),
                    decoration: BoxDecoration(
                      color: Colors.blue.withOpacity(intensity),
                      borderRadius: BorderRadius.circular(2),
                    ),
                    child: Center(
                      child: Text(
                        '$index',
                        style: TextStyle(
                          fontSize: 8,
                          color: intensity > 0.5 ? Colors.white : Colors.black,
                        ),
                      ),
                    ),
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildRecognitionAccuracyChart(List<AccuracyData> accuracyData) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Recognition Accuracy',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 16),
            SizedBox(
              height: 200,
              child: PieChart(
                PieChartData(
                  sections: accuracyData.map((data) {
                    return PieChartSectionData(
                      value: data.percentage,
                      title: '${data.percentage.toStringAsFixed(1)}%',
                      color: data.color,
                      radius: 50,
                    );
                  }).toList(),
                  centerSpaceRadius: 40,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildConfidenceDistributionChart(List<ConfidenceDistributionData> distribution) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Confidence Distribution',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 16),
            SizedBox(
              height: 200,
              child: BarChart(
                BarChartData(
                  alignment: BarChartAlignment.spaceAround,
                  barGroups: distribution.asMap().entries.map((entry) {
                    return BarChartGroupData(
                      x: entry.key,
                      barRods: [
                        BarChartRodData(
                          toY: entry.value.count.toDouble(),
                          color: Colors.green,
                          width: 20,
                        ),
                      ],
                    );
                  }).toList(),
                  titlesData: FlTitlesData(
                    bottomTitles: AxisTitles(
                      sideTitles: SideTitles(
                        showTitles: true,
                        getTitlesWidget: (value, meta) {
                          if (value.toInt() < distribution.length) {
                            return Text(
                              '${distribution[value.toInt()].confidenceRange}%',
                              style: Theme.of(context).textTheme.bodySmall,
                            );
                          }
                          return const Text('');
                        },
                      ),
                    ),
                    leftTitles: AxisTitles(
                      sideTitles: SideTitles(showTitles: true),
                    ),
                    topTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
                    rightTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTopDetectedFaces(List<TopDetectedFace> topFaces) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Most Detected Faces',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 16),
            ...topFaces.take(5).map((face) {
              return ListTile(
                leading: CircleAvatar(
                  backgroundImage: face.thumbnailUrl != null
                      ? NetworkImage(face.thumbnailUrl!)
                      : null,
                  child: face.thumbnailUrl == null
                      ? const Icon(Icons.person)
                      : null,
                ),
                title: Text(face.name ?? 'Unknown'),
                subtitle: Text('${face.detectionCount} detections'),
                trailing: Text('${face.averageConfidence.toStringAsFixed(1)}%'),
              );
            }).toList(),
          ],
        ),
      ),
    );
  }

  Widget _buildDetectionTimeline(List<DetectionTimelineItem> timeline) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Detection Timeline',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 16),
            SizedBox(
              height: 300,
              child: ListView.builder(
                itemCount: timeline.length,
                itemBuilder: (context, index) {
                  final item = timeline[index];
                  return ListTile(
                    leading: CircleAvatar(
                      child: Text('${item.detectionCount}'),
                    ),
                    title: Text(item.cameraName),
                    subtitle: Text(_formatDateTime(item.timestamp)),
                    trailing: Text('${item.confidence.toStringAsFixed(1)}%'),
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSystemPerformanceOverview(SystemMetrics metrics) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'System Performance',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: _buildPerformanceMetric(
                    'CPU Usage',
                    '${metrics.cpuUsage.toStringAsFixed(1)}%',
                    metrics.cpuUsage / 100,
                    Colors.blue,
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: _buildPerformanceMetric(
                    'Memory Usage',
                    '${metrics.memoryUsage.toStringAsFixed(1)}%',
                    metrics.memoryUsage / 100,
                    Colors.green,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: _buildPerformanceMetric(
                    'Processing Speed',
                    '${metrics.avgProcessingTime.toStringAsFixed(0)}ms',
                    metrics.avgProcessingTime / 1000,
                    Colors.orange,
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: _buildPerformanceMetric(
                    'Queue Length',
                    '${metrics.queueLength}',
                    metrics.queueLength / 100,
                    Colors.purple,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildPerformanceMetric(String title, String value, double progress, Color color) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(title, style: Theme.of(context).textTheme.titleSmall),
        const SizedBox(height: 4),
        Text(
          value,
          style: Theme.of(context).textTheme.headlineSmall?.copyWith(
            color: color,
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: 8),
        LinearProgressIndicator(
          value: progress.clamp(0.0, 1.0),
          backgroundColor: Colors.grey[300],
          valueColor: AlwaysStoppedAnimation<Color>(color),
        ),
      ],
    );
  }

  Widget _buildProcessingSpeedChart(List<ProcessingSpeedData> speedData) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Processing Speed Over Time',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 16),
            SizedBox(
              height: 200,
              child: LineChart(
                LineChartData(
                  lineBarsData: [
                    LineChartBarData(
                      spots: speedData.map((data) => FlSpot(
                        data.timestamp.millisecondsSinceEpoch.toDouble(),
                        data.processingTimeMs.toDouble(),
                      )).toList(),
                      isCurved: true,
                      color: Colors.orange,
                      barWidth: 3,
                    ),
                  ],
                  titlesData: FlTitlesData(
                    bottomTitles: AxisTitles(
                      sideTitles: SideTitles(
                        showTitles: true,
                        getTitlesWidget: (value, meta) {
                          final date = DateTime.fromMillisecondsSinceEpoch(value.toInt());
                          return Text(
                            '${date.hour}:${date.minute.toString().padLeft(2, '0')}',
                            style: Theme.of(context).textTheme.bodySmall,
                          );
                        },
                      ),
                    ),
                    leftTitles: AxisTitles(
                      sideTitles: SideTitles(
                        showTitles: true,
                        getTitlesWidget: (value, meta) {
                          return Text(
                            '${value.toInt()}ms',
                            style: Theme.of(context).textTheme.bodySmall,
                          );
                        },
                      ),
                    ),
                    topTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
                    rightTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildCameraPerformanceComparison(List<CameraPerformanceData> performance) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Camera Performance Comparison',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 16),
            ...performance.map((camera) {
              return Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(camera.cameraName),
                        Text('${camera.avgProcessingTime.toStringAsFixed(0)}ms'),
                      ],
                    ),
                    const SizedBox(height: 4),
                    LinearProgressIndicator(
                      value: camera.avgProcessingTime / 1000,
                      backgroundColor: Colors.grey[300],
                      valueColor: AlwaysStoppedAnimation<Color>(
                        camera.avgProcessingTime < 500 ? Colors.green : 
                        camera.avgProcessingTime < 1000 ? Colors.orange : Colors.red,
                      ),
                    ),
                  ],
                ),
              );
            }).toList(),
          ],
        ),
      ),
    );
  }

  Widget _buildResourceUsageCharts(ResourceUsageData usage) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Resource Usage',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 16),
            SizedBox(
              height: 200,
              child: LineChart(
                LineChartData(
                  lineBarsData: [
                    LineChartBarData(
                      spots: usage.cpuHistory.asMap().entries.map((entry) => 
                          FlSpot(entry.key.toDouble(), entry.value)).toList(),
                      isCurved: true,
                      color: Colors.blue,
                      barWidth: 2,
                    ),
                    LineChartBarData(
                      spots: usage.memoryHistory.asMap().entries.map((entry) => 
                          FlSpot(entry.key.toDouble(), entry.value)).toList(),
                      isCurved: true,
                      color: Colors.green,
                      barWidth: 2,
                    ),
                  ],
                  titlesData: FlTitlesData(
                    leftTitles: AxisTitles(
                      sideTitles: SideTitles(
                        showTitles: true,
                        getTitlesWidget: (value, meta) {
                          return Text('${value.toInt()}%');
                        },
                      ),
                    ),
                    bottomTitles: AxisTitles(
                      sideTitles: SideTitles(showTitles: false),
                    ),
                    topTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
                    rightTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildErrorRateAnalysis(List<ErrorRateData> errorRates) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Error Rate Analysis',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 16),
            ...errorRates.map((error) {
              return ListTile(
                leading: Icon(
                  Icons.error_outline,
                  color: error.rate > 5 ? Colors.red : Colors.orange,
                ),
                title: Text(error.errorType),
                subtitle: Text('${error.occurrences} occurrences'),
                trailing: Text('${error.rate.toStringAsFixed(1)}%'),
              );
            }).toList(),
          ],
        ),
      ),
    );
  }

  Widget _buildKeyInsights(List<KeyInsight> insights) {
    return Column(
      children: insights.map((insight) {
        return Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              children: [
                Icon(
                  _getInsightIcon(insight.type),
                  color: _getInsightColor(insight.type),
                  size: 32,
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        insight.title,
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 4),
                      Text(
                        insight.description,
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        );
      }).toList(),
    );
  }

  Widget _buildPeakActivityAnalysis(PeakActivityData peakActivity) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Peak Activity Analysis',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 16),
            ListTile(
              leading: const Icon(Icons.schedule, color: Colors.blue),
              title: const Text('Peak Hour'),
              subtitle: Text('${peakActivity.peakHour}:00 - ${peakActivity.peakHour + 1}:00'),
              trailing: Text('${peakActivity.peakHourDetections} detections'),
            ),
            ListTile(
              leading: const Icon(Icons.calendar_today, color: Colors.green),
              title: const Text('Peak Day'),
              subtitle: Text(peakActivity.peakDay),
              trailing: Text('${peakActivity.peakDayDetections} detections'),
            ),
            ListTile(
              leading: const Icon(Icons.videocam, color: Colors.orange),
              title: const Text('Most Active Camera'),
              subtitle: Text(peakActivity.mostActiveCameraName),
              trailing: Text('${peakActivity.mostActiveCameraDetections} detections'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildRecognitionPatterns(List<RecognitionPattern> patterns) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Recognition Patterns',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 16),
            ...patterns.map((pattern) {
              return ListTile(
                leading: Icon(
                  _getPatternIcon(pattern.type),
                  color: _getPatternColor(pattern.type),
                ),
                title: Text(pattern.description),
                subtitle: Text('Confidence: ${pattern.confidence.toStringAsFixed(1)}%'),
                trailing: Text('${pattern.frequency}x'),
              );
            }).toList(),
          ],
        ),
      ),
    );
  }

  Widget _buildRecommendations(List<Recommendation> recommendations) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Recommendations',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 16),
            ...recommendations.map((recommendation) {
              return Card(
                color: Theme.of(context).colorScheme.surfaceVariant,
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Icon(
                            _getRecommendationIcon(recommendation.priority),
                            color: _getRecommendationColor(recommendation.priority),
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              recommendation.title,
                              style: Theme.of(context).textTheme.titleSmall,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      Text(
                        recommendation.description,
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                      if (recommendation.impact != null) ...[
                        const SizedBox(height: 8),
                        Text(
                          'Expected Impact: ${recommendation.impact}',
                          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: Theme.of(context).colorScheme.primary,
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              );
            }).toList(),
          ],
        ),
      ),
    );
  }

  Widget _buildAnomalyDetection(List<Anomaly> anomalies) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Anomaly Detection',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 16),
            if (anomalies.isEmpty)
              Center(
                child: Column(
                  children: [
                    Icon(
                      Icons.check_circle_outline,
                      size: 48,
                      color: Colors.green,
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'No anomalies detected',
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        color: Colors.green,
                      ),
                    ),
                  ],
                ),
              )
            else
              ...anomalies.map((anomaly) {
                return ListTile(
                  leading: Icon(
                    Icons.warning,
                    color: _getAnomalySeverityColor(anomaly.severity),
                  ),
                  title: Text(anomaly.description),
                  subtitle: Text(_formatDateTime(anomaly.detectedAt)),
                  trailing: Text(anomaly.severity.displayName),
                );
              }).toList(),
          ],
        ),
      ),
    );
  }

  // Helper methods for formatting and icons
  String _formatRelativeTime(DateTime dateTime) {
    final now = DateTime.now();
    final difference = now.difference(dateTime);

    if (difference.inMinutes < 1) {
      return 'Just now';
    } else if (difference.inHours < 1) {
      return '${difference.inMinutes}m ago';
    } else if (difference.inDays < 1) {
      return '${difference.inHours}h ago';
    } else {
      return '${difference.inDays}d ago';
    }
  }

  String _formatDateTime(DateTime dateTime) {
    return '${dateTime.day}/${dateTime.month} ${dateTime.hour}:${dateTime.minute.toString().padLeft(2, '0')}';
  }

  Color _getActivityColor(ActivityType type) {
    switch (type) {
      case ActivityType.faceDetected:
        return Colors.blue;
      case ActivityType.faceRecognized:
        return Colors.green;
      case ActivityType.errorOccurred:
        return Colors.red;
      case ActivityType.cameraConnected:
        return Colors.orange;
    }
  }

  IconData _getActivityIcon(ActivityType type) {
    switch (type) {
      case ActivityType.faceDetected:
        return Icons.face;
      case ActivityType.faceRecognized:
        return Icons.verified_user;
      case ActivityType.errorOccurred:
        return Icons.error;
      case ActivityType.cameraConnected:
        return Icons.videocam;
    }
  }

  IconData _getInsightIcon(InsightType type) {
    switch (type) {
      case InsightType.performance:
        return Icons.speed;
      case InsightType.usage:
        return Icons.bar_chart;
      case InsightType.trend:
        return Icons.trending_up;
      case InsightType.alert:
        return Icons.warning;
    }
  }

  Color _getInsightColor(InsightType type) {
    switch (type) {
      case InsightType.performance:
        return Colors.blue;
      case InsightType.usage:
        return Colors.green;
      case InsightType.trend:
        return Colors.purple;
      case InsightType.alert:
        return Colors.orange;
    }
  }

  IconData _getPatternIcon(PatternType type) {
    switch (type) {
      case PatternType.recurring:
        return Icons.repeat;
      case PatternType.peak:
        return Icons.trending_up;
      case PatternType.unusual:
        return Icons.warning;
    }
  }

  Color _getPatternColor(PatternType type) {
    switch (type) {
      case PatternType.recurring:
        return Colors.blue;
      case PatternType.peak:
        return Colors.green;
      case PatternType.unusual:
        return Colors.orange;
    }
  }

  IconData _getRecommendationIcon(RecommendationPriority priority) {
    switch (priority) {
      case RecommendationPriority.low:
        return Icons.info;
      case RecommendationPriority.medium:
        return Icons.lightbulb;
      case RecommendationPriority.high:
        return Icons.priority_high;
    }
  }

  Color _getRecommendationColor(RecommendationPriority priority) {
    switch (priority) {
      case RecommendationPriority.low:
        return Colors.blue;
      case RecommendationPriority.medium:
        return Colors.orange;
      case RecommendationPriority.high:
        return Colors.red;
    }
  }

  Color _getAnomalySeverityColor(AnomalySeverity severity) {
    switch (severity) {
      case AnomalySeverity.low:
        return Colors.yellow;
      case AnomalySeverity.medium:
        return Colors.orange;
      case AnomalySeverity.high:
        return Colors.red;
    }
  }

  void _showDateRangePicker() {
    showDateRangePicker(
      context: context,
      firstDate: DateTime.now().subtract(const Duration(days: 365)),
      lastDate: DateTime.now(),
      initialDateRange: DateTimeRange(
        start: DateTime.now().subtract(const Duration(days: 7)),
        end: DateTime.now(),
      ),
    ).then((dateRange) {
      if (dateRange != null) {
        ref.read(analyticsDateRangeProvider.notifier).setDateRange(dateRange);
      }
    });
  }

  void _exportAnalytics() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Export Analytics'),
        content: const Text('Choose export format and data range'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () {
              Navigator.of(context).pop();
              // Implement export functionality
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(
                  content: Text('Exporting analytics data...'),
                ),
              );
            },
            child: const Text('Export'),
          ),
        ],
      ),
    );
  }

  void _refreshData() {
    ref.refresh(analyticsOverviewProvider);
    ref.refresh(detectionsAnalyticsProvider);
    ref.refresh(performanceAnalyticsProvider);
    ref.refresh(insightsAnalyticsProvider);
  }
}

// Data classes and enums would be defined in separate files
// This includes all the analytics data structures, time ranges, filters, etc.