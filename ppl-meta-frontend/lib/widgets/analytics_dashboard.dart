import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:fl_chart/fl_chart.dart';
import '../core/theme/app_theme.dart';
import '../core/models/api_response.dart';
import '../core/api/api_client.dart';
import '../models/media_models.dart';
import '../services/media_api_client.dart';

/// Analytics dashboard showing usage metrics and insights
class AnalyticsDashboard extends ConsumerStatefulWidget {
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
  ConsumerState<AnalyticsDashboard> createState() => _AnalyticsDashboardState();
}

class _AnalyticsDashboardState extends ConsumerState<AnalyticsDashboard>
    with TickerProviderStateMixin {
  
  late TabController _tabController;
  MediaAnalytics? _analytics;
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
      // Get authenticated ApiClient from Riverpod
      final apiClient = ref.read(apiClientProvider);
      final mediaApiClient = MediaApiClient(apiClient);
      
      final response = await mediaApiClient.getAnalytics(
        startDate: widget.startDate,
        endDate: widget.endDate,
      );

      if (response.success) {
        setState(() {
          _analytics = response.data;
          _isLoading = false;
          _prepareChartData();
        });
        // Debug output to check the data
        // print('✅ Analytics loaded successfully!');
        // print('📊 Items by type: ${_analytics!.itemsByType}');
        // print('🎯 Filtered entries: ${_analytics!.itemsByType.entries.where((entry) => entry.value > 0).map((e) => '${e.key}: ${e.value}').toList()}');
      } else {
        setState(() {
          _error = response.error ?? 'Failed to load analytics';
          _isLoading = false;
        });
      }
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
              DateTime.parse(entry.key).millisecondsSinceEpoch.toDouble(),
              entry.value.toDouble(),
            ))
        .toList();

    // Media type distribution - handle string keys from JSON
    _mediaTypeData = _analytics!.itemsByType.entries
        .where((entry) => entry.value > 0) // Only include types with data
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

    // Device usage data - use access data as placeholder since device breakdown not available
    _deviceUsageData = _analytics!.accessesByDay.entries
        .take(10) // Limit to 10 entries for readability
        .toList()
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

    // Storage usage trend - cumulative storage growth over time
    _storageUsageData = [];
    if (_analytics!.uploadsByDay.isNotEmpty) {
      // Sort upload days chronologically
      final sortedEntries = _analytics!.uploadsByDay.entries.toList()
        ..sort((a, b) => DateTime.parse(a.key).compareTo(DateTime.parse(b.key)));
      
      // Calculate cumulative storage growth
      double cumulativeStorageBytes = 0.0;
      final avgFileSize = _analytics!.totalItems > 0 
          ? _analytics!.totalSize.toDouble() / _analytics!.totalItems.toDouble()
          : 0.0;
      
      for (final entry in sortedEntries) {
        // Add storage for files uploaded on this day
        final dailyStorageAdded = entry.value.toDouble() * avgFileSize;
        cumulativeStorageBytes += dailyStorageAdded;
        
        // Convert to MB for better readability (most users have files in MB range)
        final cumulativeStorageMB = cumulativeStorageBytes / (1024 * 1024);
        
        _storageUsageData.add(FlSpot(
          DateTime.parse(entry.key).millisecondsSinceEpoch.toDouble(),
          cumulativeStorageMB,
        ));
      }
    }
  }

  /// Format file size in human readable format
  String _formatFileSize(int bytes) {
    if (bytes < 1024) {
      return '$bytes B';
    } else if (bytes < 1024 * 1024) {
      return '${(bytes / 1024).toStringAsFixed(1)} KB';
    } else if (bytes < 1024 * 1024 * 1024) {
      return '${(bytes / (1024 * 1024)).toStringAsFixed(1)} MB';
    } else {
      return '${(bytes / (1024 * 1024 * 1024)).toStringAsFixed(1)} GB';
    }
  }

  /// Get color for media type
  Color _getMediaTypeColor(String mediaType) {
    switch (mediaType.toLowerCase()) {
      case 'image':
        return AppColors.primary;
      case 'video':
        return AppColors.secondary;
      case 'audio':
        return AppColors.accent;
      case 'document':
        return AppColors.success;
      case 'pdf':
        return AppColors.warning;
      case 'text':
        return AppColors.info;
      case 'archive':
        return AppColors.gray600;
      case 'other':
      default:
        return AppColors.gray400;
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
            Tab(text: 'Access Activity'),
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
                value: _analytics!.totalItems.toString(),
                icon: Icons.inventory,
                color: AppColors.primary,
                width: isWide ? (constraints.maxWidth - AppSpacing.md) / 2 : null,
              ),
              _SummaryCard(
                title: 'Storage Used',
                value: _analytics!.formattedTotalSize,
                icon: Icons.storage,
                color: AppColors.secondary,
                width: isWide ? (constraints.maxWidth - AppSpacing.md) / 2 : null,
              ),
              _SummaryCard(
                title: 'Avg File Size',
                value: _analytics!.formattedAverageSize,
                icon: Icons.upload,
                color: AppColors.success,
                width: isWide ? (constraints.maxWidth - AppSpacing.md) / 2 : null,
              ),
              _SummaryCard(
                title: 'Popular Tags',
                value: _analytics!.popularTags.length.toString(),
                icon: Icons.tag,
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
                      child: _uploadTrendData.isEmpty
                          ? Center(
                              child: Column(
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  Icon(
                                    Icons.timeline,
                                    size: 64,
                                    color: AppColors.gray400,
                                  ),
                                  const SizedBox(height: AppSpacing.md),
                                  Text(
                                    'No upload trend data available',
                                    style: AppTextStyles.bodyMedium.copyWith(
                                      color: AppColors.textSecondary,
                                    ),
                                  ),
                                  const SizedBox(height: AppSpacing.sm),
                                  Text(
                                    'Upload more files to see trends over time',
                                    style: AppTextStyles.caption.copyWith(
                                      color: AppColors.textSecondary,
                                    ),
                                  ),
                                ],
                              ),
                            )
                          : LineChart(
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
                      child: Container(
                        padding: const EdgeInsets.all(AppSpacing.sm),
                        decoration: BoxDecoration(
                          border: Border.all(color: AppColors.border),
                          borderRadius: BorderRadius.circular(AppRadius.sm),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          mainAxisAlignment: MainAxisAlignment.center,
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Text(
                              'Legend',
                              style: AppTextStyles.labelMedium.copyWith(
                                fontWeight: FontWeight.bold,
                                color: AppColors.textSecondary,
                              ),
                            ),
                            const SizedBox(height: AppSpacing.sm),
                            ...() {
                              final legendItems = _analytics!.itemsByType.entries
                                  .where((entry) => entry.value > 0) // Only show types with data
                                  .map((entry) {
                                    // print('🏷️ Creating legend item: ${entry.key.toUpperCase()} = ${entry.value}');
                                    return _LegendItem(
                                      color: _getMediaTypeColor(entry.key),
                                      label: entry.key.toUpperCase(),
                                      count: entry.value,
                                    );
                                  })
                                  .toList();
                              // print('📝 Total legend items created: ${legendItems.length}');
                              return legendItems;
                            }(),
                          ],
                        ),
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
                'Access Activity by Day',
                style: AppTextStyles.h6,
              ),
              const SizedBox(height: AppSpacing.md),
              Expanded(
                child: _analytics!.accessesByDay.isEmpty
                    ? Center(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(
                              Icons.bar_chart,
                              size: 64,
                              color: AppColors.gray400,
                            ),
                            const SizedBox(height: AppSpacing.md),
                            Text(
                              'No access activity data available',
                              style: AppTextStyles.bodyMedium.copyWith(
                                color: AppColors.textSecondary,
                              ),
                            ),
                            const SizedBox(height: AppSpacing.sm),
                            Text(
                              'Activity tracking will show here as you use the platform',
                              style: AppTextStyles.caption.copyWith(
                                color: AppColors.textSecondary,
                              ),
                            ),
                          ],
                        ),
                      )
                    : BarChart(
                        BarChartData(
                          alignment: BarChartAlignment.spaceAround,
                          maxY: _analytics!.accessesByDay.values.isNotEmpty
                              ? _analytics!.accessesByDay.values
                                  .map((e) => e.toDouble())
                                  .reduce((a, b) => a > b ? a : b) * 1.2
                              : 10.0, // Default maxY when no data
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
                            final accessDays = _analytics!.accessesByDay.keys.toList();
                            if (value.toInt() < accessDays.length) {
                              return Padding(
                                padding: const EdgeInsets.only(top: 8),
                                child: Text(
                                  accessDays[value.toInt()].substring(5), // Show MM-DD format
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
                'Cumulative Storage Growth',
                style: AppTextStyles.h6,
              ),
              const SizedBox(height: AppSpacing.sm),
              Text(
                'Shows how your storage usage has grown over time',
                style: AppTextStyles.caption.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
              const SizedBox(height: AppSpacing.md),
              Expanded(
                child: _storageUsageData.isEmpty
                    ? Center(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(
                              Icons.storage,
                              size: 64,
                              color: AppColors.gray400,
                            ),
                            const SizedBox(height: AppSpacing.md),
                            Text(
                              'No storage growth data available',
                              style: AppTextStyles.bodyMedium.copyWith(
                                color: AppColors.textSecondary,
                              ),
                            ),
                            const SizedBox(height: AppSpacing.sm),
                            Text(
                              'Upload some files to see your storage growth over time',
                              style: AppTextStyles.caption.copyWith(
                                color: AppColors.textSecondary,
                              ),
                            ),
                            const SizedBox(height: AppSpacing.sm),
                            Text(
                              'Total storage used: ${_analytics!.formattedTotalSize}',
                              style: AppTextStyles.caption.copyWith(
                                color: AppColors.textSecondary,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ],
                        ),
                      )
                    : LineChart(
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
    return Container(
      margin: const EdgeInsets.only(bottom: AppSpacing.sm),
      padding: const EdgeInsets.all(AppSpacing.xs),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(AppRadius.sm),
        border: Border.all(color: AppColors.border.withOpacity(0.5)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.max,
        children: [
          Container(
            width: 20,
            height: 20,
            decoration: BoxDecoration(
              color: color,
              borderRadius: BorderRadius.circular(AppRadius.xs),
              border: Border.all(color: AppColors.border),
            ),
          ),
          const SizedBox(width: AppSpacing.sm),
          Expanded(
            child: Text(
              label,
              style: AppTextStyles.bodyMedium.copyWith(
                fontWeight: FontWeight.w500,
                color: AppColors.textPrimary,
              ),
              overflow: TextOverflow.ellipsis,
            ),
          ),
          const SizedBox(width: AppSpacing.xs),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(
              color: AppColors.primary.withOpacity(0.1),
              borderRadius: BorderRadius.circular(AppRadius.sm),
            ),
            child: Text(
              count.toString(),
              style: AppTextStyles.labelMedium.copyWith(
                fontWeight: FontWeight.bold,
                color: AppColors.primary,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
