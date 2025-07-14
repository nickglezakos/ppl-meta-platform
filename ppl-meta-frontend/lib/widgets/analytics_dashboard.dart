import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import '../core/theme/app_theme.dart';
import '../core/models/api_response.dart';
import '../models/media_models.dart';
import '../services/media_api_client.dart';

/// Analytics dashboard showing usage metrics and insights
class AnalyticsDashboard extends StatefulWidget {
  final String? userId;
  final String? collectionId;
  final DateTime? startDate;
  final DateTime? endDate;

  const AnalyticsDashboard({
    super.key,
    this.userId,
    this.collectionId,
    this.startDate,
    this.endDate,
  });

  @override
  State<AnalyticsDashboard> createState() => _AnalyticsDashboardState();
}

class _AnalyticsDashboardState extends State<AnalyticsDashboard>
    with TickerProviderStateMixin {
  final MediaApiClient _apiClient = MediaApiClient();
  
  late TabController _tabController;
  DeviceAnalytics? _analytics;
  bool _isLoading = false;
  String? _error;
  
  // Chart data
  List<FlSpot> _uploadTrendData = [];
  List<PieChartSectionData> _mediaTypeData = [];
  List<BarChartGroupData> _deviceUsageData = [];
  List<FlSpot> _storageUsageData = [];

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 4, vsync: this);
    _loadAnalytics();
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  void didUpdateWidget(AnalyticsDashboard oldWidget) {
    super.didUpdateWidget(oldWidget);
    
    if (widget.userId != oldWidget.userId ||
        widget.collectionId != oldWidget.collectionId ||
        widget.startDate != oldWidget.startDate ||
        widget.endDate != oldWidget.endDate) {
      _loadAnalytics();
    }
  }

  /// Load analytics data
  Future<void> _loadAnalytics() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final analytics = await _apiClient.getDeviceAnalytics(
        userId: widget.userId,
        collectionId: widget.collectionId,
        startDate: widget.startDate,
        endDate: widget.endDate,
      );

      setState(() {
        _analytics = analytics;
        _isLoading = false;
        _prepareChartData();
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _isLoading = false;
      });
    }
  }

  /// Prepare chart data from analytics
  void _prepareChartData() {
    if (_analytics == null) return;

    // Upload trend data (last 30 days)
    _uploadTrendData = _analytics!.uploadsByDay.entries
        .map((entry) => FlSpot(
              entry.key.millisecondsSinceEpoch.toDouble(),
              entry.value.toDouble(),
            ))
        .toList();

    // Media type distribution
    _mediaTypeData = _analytics!.mediaTypeBreakdown.entries
        .map((entry) => PieChartSectionData(
              color: _getMediaTypeColor(entry.key),
              value: entry.value.toDouble(),
              title: '${entry.value}',
              radius: 60,
              titleStyle: AppTextStyles.labelSmall.copyWith(
                color: AppColors.white,
                fontWeight: FontWeight.bold,
              ),
            ))
        .toList();

    // Device usage data
    _deviceUsageData = _analytics!.deviceBreakdown.entries
        .asMap()
        .entries
        .map((entry) => BarChartGroupData(
              x: entry.key,
              barRods: [
                BarChartRodData(
                  toY: entry.value.value.toDouble(),
                  color: AppColors.primary,
                  width: 20,
                  borderRadius: BorderRadius.circular(4),
                ),
              ],
            ))
        .toList();

    // Storage usage trend
    _storageUsageData = _analytics!.storageUsageByDay.entries
        .map((entry) => FlSpot(
              entry.key.millisecondsSinceEpoch.toDouble(),
              entry.value.toDouble() / (1024 * 1024 * 1024), // Convert to GB
            ))
        .toList();
  }

  /// Get color for media type
  Color _getMediaTypeColor(String mediaType) {
    switch (mediaType.toLowerCase()) {
      case 'image':
        return AppColors.imageColor;
      case 'video':
        return AppColors.videoColor;
      case 'audio':
        return AppColors.audioColor;
      case 'document':
        return AppColors.documentColor;
      default:
        return AppColors.gray500;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        // Header with refresh button
        Padding(
          padding: const EdgeInsets.all(AppSpacing.md),
          child: Row(
            children: [
              Text(
                'Analytics Dashboard',
                style: AppTextStyles.h4,
              ),
              const Spacer(),
              IconButton(
                onPressed: _isLoading ? null : _loadAnalytics,
                icon: _isLoading
                    ? const SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.refresh),
                tooltip: 'Refresh data',
              ),
            ],
          ),
        ),

        // Content
        Expanded(
          child: _buildContent(),
        ),
      ],
    );
  }

  /// Build main content
  Widget _buildContent() {
    if (_isLoading && _analytics == null) {
      return const Center(
        child: CircularProgressIndicator(),
      );
    }

    if (_error != null) {
      return _buildErrorState();
    }

    if (_analytics == null) {
      return _buildEmptyState();
    }

    return Column(
      children: [
        // Summary cards
        _buildSummaryCards(),
        
        const SizedBox(height: AppSpacing.lg),
        
        // Tab bar
        TabBar(
          controller: _tabController,
          labelColor: AppColors.primary,
          unselectedLabelColor: AppColors.textSecondary,
          indicatorColor: AppColors.primary,
          tabs: const [
            Tab(text: 'Overview'),
            Tab(text: 'Media Types'),
            Tab(text: 'Devices'),
            Tab(text: 'Storage'),
          ],
        ),
        
        // Tab content
        Expanded(
          child: TabBarView(
            controller: _tabController,
            children: [
              _buildOverviewTab(),
              _buildMediaTypesTab(),
              _buildDevicesTab(),
              _buildStorageTab(),
            ],
          ),
        ),
      ],
    );
  }

  /// Build summary cards
  Widget _buildSummaryCards() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
      child: LayoutBuilder(
        builder: (context, constraints) {
          final isWide = constraints.maxWidth > 600;
          
          return Wrap(
            spacing: AppSpacing.md,
            runSpacing: AppSpacing.md,
            children: [
              _SummaryCard(
                title: 'Total Files',
                value: _analytics!.totalFiles.toString(),
                icon: Icons.inventory,
                color: AppColors.primary,
                width: isWide ? (constraints.maxWidth - AppSpacing.md) / 2 : null,
              ),
              _SummaryCard(
                title: 'Storage Used',
                value: '${(_analytics!.totalStorageBytes / (1024 * 1024 * 1024)).toStringAsFixed(1)} GB',
                icon: Icons.storage,
                color: AppColors.secondary,
                width: isWide ? (constraints.maxWidth - AppSpacing.md) / 2 : null,
              ),
              _SummaryCard(
                title: 'Uploads Today',
                value: _analytics!.uploadsToday.toString(),
                icon: Icons.upload,
                color: AppColors.success,
                width: isWide ? (constraints.maxWidth - AppSpacing.md) / 2 : null,
              ),
              _SummaryCard(
                title: 'Active Devices',
                value: _analytics!.deviceBreakdown.length.toString(),
                icon: Icons.devices,
                color: AppColors.accent,
                width: isWide ? (constraints.maxWidth - AppSpacing.md) / 2 : null,
              ),
            ],
          );
        },
      ),
    );
  }

  /// Build overview tab
  Widget _buildOverviewTab() {
    return Padding(
      padding: const EdgeInsets.all(AppSpacing.md),
      child: Column(
        children: [
          // Upload trend chart
          Expanded(
            child: Card(
              child: Padding(
                padding: const EdgeInsets.all(AppSpacing.md),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Upload Trend (Last 30 Days)',
                      style: AppTextStyles.h6,
                    ),
                    const SizedBox(height: AppSpacing.md),
                    Expanded(
                      child: LineChart(
                        LineChartData(
                          gridData: const FlGridData(show: true),
                          titlesData: FlTitlesData(
                            leftTitles: AxisTitles(
                              sideTitles: SideTitles(
                                showTitles: true,
                                reservedSize: 40,
                                getTitlesWidget: (value, meta) {
                                  return Text(
                                    value.toInt().toString(),
                                    style: AppTextStyles.caption,
                                  );
                                },
                              ),
                            ),
                            bottomTitles: AxisTitles(
                              sideTitles: SideTitles(
                                showTitles: true,
                                reservedSize: 30,
                                getTitlesWidget: (value, meta) {
                                  final date = DateTime.fromMillisecondsSinceEpoch(
                                    value.toInt(),
                                  );
                                  return Text(
                                    '${date.month}/${date.day}',
                                    style: AppTextStyles.caption,
                                  );
                                },
                              ),
                            ),
                            topTitles: const AxisTitles(
                              sideTitles: SideTitles(showTitles: false),
                            ),
                            rightTitles: const AxisTitles(
                              sideTitles: SideTitles(showTitles: false),
                            ),
                          ),
                          borderData: FlBorderData(
                            show: true,
                            border: const Border(
                              bottom: BorderSide(color: AppColors.border),
                              left: BorderSide(color: AppColors.border),
                            ),
                          ),
                          lineBarsData: [
                            LineChartBarData(
                              spots: _uploadTrendData,
                              isCurved: true,
                              color: AppColors.primary,
                              barWidth: 3,
                              dotData: const FlDotData(show: false),
                              belowBarData: BarAreaData(
                                show: true,
                                color: AppColors.primary.withOpacity(0.1),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  /// Build media types tab
  Widget _buildMediaTypesTab() {
    return Padding(
      padding: const EdgeInsets.all(AppSpacing.md),
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(AppSpacing.md),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Media Type Distribution',
                style: AppTextStyles.h6,
              ),
              const SizedBox(height: AppSpacing.md),
              Expanded(
                child: Row(
                  children: [
                    // Pie chart
                    Expanded(
                      flex: 2,
                      child: PieChart(
                        PieChartData(
                          sections: _mediaTypeData,
                          centerSpaceRadius: 50,
                          sectionsSpace: 2,
                        ),
                      ),
                    ),
                    
                    const SizedBox(width: AppSpacing.lg),
                    
                    // Legend
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: _analytics!.mediaTypeBreakdown.entries
                            .map((entry) => _LegendItem(
                                  color: _getMediaTypeColor(entry.key),
                                  label: entry.key.toUpperCase(),
                                  count: entry.value,
                                ))
                            .toList(),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  /// Build devices tab
  Widget _buildDevicesTab() {
    return Padding(
      padding: const EdgeInsets.all(AppSpacing.md),
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(AppSpacing.md),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Device Usage',
                style: AppTextStyles.h6,
              ),
              const SizedBox(height: AppSpacing.md),
              Expanded(
                child: BarChart(
                  BarChartData(
                    alignment: BarChartAlignment.spaceAround,
                    maxY: _analytics!.deviceBreakdown.values
                        .map((e) => e.toDouble())
                        .reduce((a, b) => a > b ? a : b) * 1.2,
                    barTouchData: BarTouchData(enabled: true),
                    titlesData: FlTitlesData(
                      leftTitles: AxisTitles(
                        sideTitles: SideTitles(
                          showTitles: true,
                          reservedSize: 40,
                          getTitlesWidget: (value, meta) {
                            return Text(
                              value.toInt().toString(),
                              style: AppTextStyles.caption,
                            );
                          },
                        ),
                      ),
                      bottomTitles: AxisTitles(
                        sideTitles: SideTitles(
                          showTitles: true,
                          reservedSize: 40,
                          getTitlesWidget: (value, meta) {
                            final devices = _analytics!.deviceBreakdown.keys.toList();
                            if (value.toInt() < devices.length) {
                              return Padding(
                                padding: const EdgeInsets.only(top: 8),
                                child: Text(
                                  devices[value.toInt()],
                                  style: AppTextStyles.caption,
                                  maxLines: 2,
                                  textAlign: TextAlign.center,
                                ),
                              );
                            }
                            return const Text('');
                          },
                        ),
                      ),
                      topTitles: const AxisTitles(
                        sideTitles: SideTitles(showTitles: false),
                      ),
                      rightTitles: const AxisTitles(
                        sideTitles: SideTitles(showTitles: false),
                      ),
                    ),
                    borderData: FlBorderData(
                      show: true,
                      border: const Border(
                        bottom: BorderSide(color: AppColors.border),
                        left: BorderSide(color: AppColors.border),
                      ),
                    ),
                    barGroups: _deviceUsageData,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  /// Build storage tab
  Widget _buildStorageTab() {
    return Padding(
      padding: const EdgeInsets.all(AppSpacing.md),
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(AppSpacing.md),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Storage Usage (GB)',
                style: AppTextStyles.h6,
              ),
              const SizedBox(height: AppSpacing.md),
              Expanded(
                child: LineChart(
                  LineChartData(
                    gridData: const FlGridData(show: true),
                    titlesData: FlTitlesData(
                      leftTitles: AxisTitles(
                        sideTitles: SideTitles(
                          showTitles: true,
                          reservedSize: 50,
                          getTitlesWidget: (value, meta) {
                            return Text(
                              '${value.toStringAsFixed(1)} GB',
                              style: AppTextStyles.caption,
                            );
                          },
                        ),
                      ),
                      bottomTitles: AxisTitles(
                        sideTitles: SideTitles(
                          showTitles: true,
                          reservedSize: 30,
                          getTitlesWidget: (value, meta) {
                            final date = DateTime.fromMillisecondsSinceEpoch(
                              value.toInt(),
                            );
                            return Text(
                              '${date.month}/${date.day}',
                              style: AppTextStyles.caption,
                            );
                          },
                        ),
                      ),
                      topTitles: const AxisTitles(
                        sideTitles: SideTitles(showTitles: false),
                      ),
                      rightTitles: const AxisTitles(
                        sideTitles: SideTitles(showTitles: false),
                      ),
                    ),
                    borderData: FlBorderData(
                      show: true,
                      border: const Border(
                        bottom: BorderSide(color: AppColors.border),
                        left: BorderSide(color: AppColors.border),
                      ),
                    ),
                    lineBarsData: [
                      LineChartBarData(
                        spots: _storageUsageData,
                        isCurved: true,
                        color: AppColors.secondary,
                        barWidth: 3,
                        dotData: const FlDotData(show: false),
                        belowBarData: BarAreaData(
                          show: true,
                          color: AppColors.secondary.withOpacity(0.1),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  /// Build error state
  Widget _buildErrorState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.error_outline,
            size: 64,
            color: AppColors.error,
          ),
          const SizedBox(height: AppSpacing.md),
          Text(
            'Failed to load analytics',
            style: AppTextStyles.h5,
          ),
          const SizedBox(height: AppSpacing.sm),
          Text(
            _error!,
            style: AppTextStyles.bodyMedium.copyWith(
              color: AppColors.textSecondary,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: AppSpacing.lg),
          ElevatedButton(
            onPressed: _loadAnalytics,
            child: const Text('Retry'),
          ),
        ],
      ),
    );
  }

  /// Build empty state
  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.analytics_outlined,
            size: 64,
            color: AppColors.textTertiary,
          ),
          const SizedBox(height: AppSpacing.md),
          Text(
            'No analytics data available',
            style: AppTextStyles.h5.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
          const SizedBox(height: AppSpacing.sm),
          Text(
            'Upload some media to see analytics',
            style: AppTextStyles.bodyMedium.copyWith(
              color: AppColors.textTertiary,
            ),
          ),
        ],
      ),
    );
  }
}

/// Summary card widget
class _SummaryCard extends StatelessWidget {
  final String title;
  final String value;
  final IconData icon;
  final Color color;
  final double? width;

  const _SummaryCard({
    required this.title,
    required this.value,
    required this.icon,
    required this.color,
    this.width,
  });

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: width,
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(AppSpacing.md),
          child: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(AppSpacing.sm),
                decoration: BoxDecoration(
                  color: color.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(AppRadius.sm),
                ),
                child: Icon(
                  icon,
                  color: color,
                  size: 24,
                ),
              ),
              const SizedBox(width: AppSpacing.md),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: AppTextStyles.labelMedium.copyWith(
                        color: AppColors.textSecondary,
                      ),
                    ),
                    const SizedBox(height: AppSpacing.xs),
                    Text(
                      value,
                      style: AppTextStyles.h5.copyWith(
                        color: color,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Legend item for pie chart
class _LegendItem extends StatelessWidget {
  final Color color;
  final String label;
  final int count;

  const _LegendItem({
    required this.color,
    required this.label,
    required this.count,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.sm),
      child: Row(
        children: [
          Container(
            width: 16,
            height: 16,
            decoration: BoxDecoration(
              color: color,
              borderRadius: BorderRadius.circular(AppRadius.xs),
            ),
          ),
          const SizedBox(width: AppSpacing.sm),
          Expanded(
            child: Text(
              label,
              style: AppTextStyles.bodyMedium,
            ),
          ),
          Text(
            count.toString(),
            style: AppTextStyles.labelMedium.copyWith(
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
      ),
    );
  }
}
