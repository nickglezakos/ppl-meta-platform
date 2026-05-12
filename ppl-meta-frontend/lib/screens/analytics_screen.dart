import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'dart:io';
import 'package:excel/excel.dart' as excel;
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';
import 'package:fl_chart/fl_chart.dart';
import '../core/theme/app_theme.dart';
import '../widgets/custom_app_bar.dart';
import '../models/analytics_models.dart';
import '../services/media_api_client.dart';
import '../core/providers/camera_providers.dart';
import '../utils/platform_file_download.dart';
import '../widgets/people_counters_tile.dart';

/// MVR Analytics Dashboard - showing people detection insights from camera collections
/// Based on MVRsearch cached results from camera cards endpoint
class AnalyticsScreen extends ConsumerStatefulWidget {
  const AnalyticsScreen({super.key});

  @override
  ConsumerState<AnalyticsScreen> createState() => _AnalyticsScreenState();
}

class _AnalyticsScreenState extends ConsumerState<AnalyticsScreen> {
  static const String _dataSourcePreferenceKey = 'analytics_data_source';

  // Filter state
  String _timeFilter = 'today'; // today, last_hour, last_3_hours, last_week, last_month, custom
  List<String> _selectedCollectionIds = []; // empty = all collections
  List<String> _selectedGenders = []; // empty = all genders (male, female)
  List<String> _selectedAgeGroups = []; // empty = all ages (young, adult, elderly)
  String _dataSource = 'recording'; // 'recording' or 'instant_detection'
  bool _autoRefresh = false;
  DateTime? _startDate;
  DateTime? _endDate;
  
  // Loading and error state
  bool _isLoading = false;
  String? _error;
  
  // Analytics data
  AnalyticsSummary? _analyticsSummary;
  MvrQualityMetrics? _mvrQualityMetrics;  // NEW: MVR quality data
  Map<String, dynamic>? _timeSeriesData;
  Map<String, dynamic>? _demographicsData;
  Map<String, dynamic>? _behavioralData;
  List<Map<String, dynamic>> _cameras = [];
  Future<(DateTime, DateTime)> _getEffectiveAnalyticsRange() async {
    final now = DateTime.now().toUtc();

    switch (_timeFilter) {
      case 'custom':
        return ((_startDate ?? now), (_endDate ?? now));
      case 'today':
        return (DateTime.utc(now.year, now.month, now.day), now);
      case 'last_hour':
        return (now.subtract(const Duration(hours: 1)), now);
      case 'last_3_hours':
        return (now.subtract(const Duration(hours: 3)), now);
      case 'last_week':
        return (now.subtract(const Duration(days: 7)), now);
      case 'last_month':
        return (now.subtract(const Duration(days: 30)), now);
      default:
        return (DateTime.utc(now.year, now.month, now.day), now);
    }
  }

  Future<List<String>?> _resolveAnalyticsVideoUuids(MediaApiClient apiClient) async {
    if (_dataSource != 'recording') {
      return null;
    }

    if (_cameras.isEmpty) {
      return null;
    }

    final selectedCameraIds = _selectedCollectionIds.isNotEmpty
        ? _selectedCollectionIds
        : _cameras
            .map((camera) => (camera['id'] as String?)?.trim())
            .whereType<String>()
            .where((value) => value.isNotEmpty)
            .toList();

    if (selectedCameraIds.isEmpty) {
      return null;
    }

    final (effectiveStartDate, effectiveEndDate) = await _getEffectiveAnalyticsRange();
    final videoUuids = <String>[];
    final seenVideoUuids = <String>{};

    for (final selectedCameraId in selectedCameraIds) {
      final matchingCamera = _cameras.cast<Map<String, dynamic>?>().firstWhere(
        (camera) => camera?['id'] == selectedCameraId,
        orElse: () => null,
      );
      final collectionUuid = (matchingCamera?['uuid'] as String?)?.trim();
      final collectionId = collectionUuid != null && collectionUuid.isNotEmpty
          ? collectionUuid
          : selectedCameraId;

      final mediaResponse = await apiClient.searchMedia(
        collectionId: collectionId,
        startDate: effectiveStartDate,
        endDate: effectiveEndDate,
        limit: 500,
      );

      if (!mediaResponse.success || mediaResponse.data == null) {
        continue;
      }

      for (final media in mediaResponse.data!.items) {
        if (seenVideoUuids.add(media.uuid)) {
          videoUuids.add(media.uuid);
        }
      }
    }

    return videoUuids;
  }

  @override
  void initState() {
    super.initState();
    _restorePreferencesAndLoadAnalytics();
  }

  Future<void> _restorePreferencesAndLoadAnalytics() async {
    final prefs = await SharedPreferences.getInstance();
    final storedDataSource = prefs.getString(_dataSourcePreferenceKey);
    if (!mounted) {
      return;
    }

    if (storedDataSource == 'instant_detection' || storedDataSource == 'recording') {
      setState(() {
        _dataSource = storedDataSource!;
      });
    }

    await _loadAnalytics();
  }

  Future<void> _persistDataSourcePreference() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_dataSourcePreferenceKey, _dataSource);
  }

  Future<void> _loadAnalytics() async {
    setState(() {
      _isLoading = true;
      _error = null;
      _mvrQualityMetrics = null;
    });

    try {
      // Get MediaApiClient from provider
      final apiClient = ref.read(mediaApiClientProvider);
      
      // Load cameras list if empty (for filter dropdown)
      if (_cameras.isEmpty) {
        final camerasResponse = await apiClient.getCamerasList();
        if (camerasResponse.success && camerasResponse.data != null) {
          _cameras = camerasResponse.data!;
        }
      }

      final explicitVideoUuids = await _resolveAnalyticsVideoUuids(apiClient);
      
      // Load analytics summary from backend endpoint
      final response = await apiClient.getAnalyticsSummary(
        timeFilter: _timeFilter,
        cameraIds: _selectedCollectionIds.isNotEmpty ? _selectedCollectionIds : null,
        videoUuids: explicitVideoUuids,
        forceRefresh: false,
        startDate: _startDate,
        endDate: _endDate,
        genders: _selectedGenders.isNotEmpty ? _selectedGenders : null,
        ageGroups: _selectedAgeGroups.isNotEmpty ? _selectedAgeGroups : null,
        dataSource: _dataSource,
      );
      
      if (response.success && response.data != null) {
        if (mounted) {
          setState(() {
            _analyticsSummary = AnalyticsSummary.fromJson(response.data!);
            _isLoading = false;
          });
        }
      } else {
        throw Exception(response.error ?? 'Failed to load analytics');
      }
      
      // Load MVR quality metrics (NEW)
      try {
        debugPrint('🔍 Analytics: Attempting to load MVR quality metrics...');
        final analyticsApiClient = ref.read(analyticsApiClientProvider);
        debugPrint('🔍 Analytics: Got analyticsApiClient: ${analyticsApiClient.runtimeType}');

        final filteredQualityResponse = await analyticsApiClient.getMvrQualityMetrics(
          timeFilter: _timeFilter,
          collectionName: null, // null = all collections
          cameraIds: _selectedCollectionIds.isNotEmpty ? _selectedCollectionIds : null,
          videoUuids: explicitVideoUuids,
          startDate: _startDate,
          endDate: _endDate,
          genders: _selectedGenders.isNotEmpty ? _selectedGenders : null,
          ageGroups: _selectedAgeGroups.isNotEmpty ? _selectedAgeGroups : null,
          dataSource: _dataSource,
        );

        final qualityResponse = await analyticsApiClient.getMvrQualityMetrics(
          timeFilter: _timeFilter,
          collectionName: null, // null = all collections
          cameraIds: _selectedCollectionIds.isNotEmpty ? _selectedCollectionIds : null,
          startDate: _startDate,
          endDate: _endDate,
          genders: _selectedGenders.isNotEmpty ? _selectedGenders : null,
          ageGroups: _selectedAgeGroups.isNotEmpty ? _selectedAgeGroups : null,
          dataSource: _dataSource,
        );
        
        debugPrint('🔍 Analytics: Quality response success: ${qualityResponse.success}');
        if (qualityResponse.data != null) {
          debugPrint('🔍 Analytics: Quality data keys: ${qualityResponse.data!.keys}');
          debugPrint('🔍 Analytics: Average quality: ${qualityResponse.data!['average_quality']}');
          debugPrint('🔍 Analytics: Quality grade: ${qualityResponse.data!['quality_grade']}');
        } else {
          debugPrint('⚠️  Analytics: Quality response data is null');
        }
        
        if (mounted && qualityResponse.success && qualityResponse.data != null) {
          final qualityMetrics = MvrQualityMetrics.fromJson(qualityResponse.data!);
          final overviewMetrics = filteredQualityResponse.success && filteredQualityResponse.data != null
              ? MvrQualityMetrics.fromJson(filteredQualityResponse.data!)
              : qualityMetrics;
          final metrics = MvrQualityMetrics(
            timeFilter: qualityMetrics.timeFilter,
            collectionName: qualityMetrics.collectionName,
            trackingSessionsCount: overviewMetrics.trackingSessionsCount,
            totalIndividuals: overviewMetrics.totalIndividuals,
            totalMvrPeople: overviewMetrics.totalMvrPeople,
            totalVideosProcessed: overviewMetrics.totalVideosProcessed,
            mvrWithQuality: qualityMetrics.mvrWithQuality,
            mvrWithoutQuality: qualityMetrics.mvrWithoutQuality,
            averageQuality: qualityMetrics.averageQuality,
            minQuality: qualityMetrics.minQuality,
            maxQuality: qualityMetrics.maxQuality,
            qualityStdDev: qualityMetrics.qualityStdDev,
            qualityGrade: qualityMetrics.qualityGrade,
            dataCompleteness: qualityMetrics.dataCompleteness,
            queryStartTime: qualityMetrics.queryStartTime,
            queryEndTime: qualityMetrics.queryEndTime,
            queriedAt: qualityMetrics.queriedAt,
          );
          debugPrint('✅ Analytics: Successfully parsed MvrQualityMetrics');
          debugPrint('   - Overview sessions: ${metrics.trackingSessionsCount}');
          debugPrint('   - Overview computed: ${metrics.totalIndividuals}');
          debugPrint('   - Overview detected: ${metrics.totalMvrPeople}');
          debugPrint('   - Has quality data: ${metrics.hasQualityData}');
          debugPrint('   - Average quality: ${metrics.averageQuality}');
          debugPrint('   - Quality grade: ${metrics.qualityGrade}');
          
          setState(() {
            _mvrQualityMetrics = metrics;
          });
          debugPrint('✅ Analytics: State updated with MVR quality metrics');
        } else {
          debugPrint('⚠️  Analytics: Quality response not successful or data null');
          if (!qualityResponse.success) {
            debugPrint('   - Error: ${qualityResponse.error}');
          }
          if (mounted) {
            setState(() {
              _mvrQualityMetrics = null;
            });
          }
        }
      } catch (e, stackTrace) {
        debugPrint('❌ Analytics: Failed to load MVR quality metrics: $e');
        debugPrint('   Stack trace: $stackTrace');
        if (mounted) {
          setState(() {
            _mvrQualityMetrics = null;
          });
        }
        // Don't fail the whole page if quality metrics fails
      }
      
      // Load time-series data for Level 2 analytics
      try {
        final timeSeriesResponse = await apiClient.getTimeBasedAnalytics(
          timeFilter: _timeFilter,
          cameraIds: _selectedCollectionIds.isNotEmpty ? _selectedCollectionIds : null,
          videoUuids: explicitVideoUuids,
          interval: _timeFilter == 'today' || _timeFilter == 'last_hour' || _timeFilter == 'last_3_hours' 
              ? 'hour' 
              : 'day',
          startDate: _startDate,
          endDate: _endDate,
          dataSource: _dataSource,
        );
        
        if (mounted && timeSeriesResponse.success && timeSeriesResponse.data != null) {
          setState(() {
            _timeSeriesData = timeSeriesResponse.data!;
          });
        }
      } catch (e) {
        debugPrint('⚠️  Failed to load time-series data: $e');
        // Don't fail the whole page if time-series fails
      }
      
      // Load demographics data for Level 3 analytics
      try {
        final demographicsResponse = await apiClient.getDemographicsBreakdown(
          timeFilter: _timeFilter,
          cameraIds: _selectedCollectionIds.isNotEmpty ? _selectedCollectionIds : null,
          videoUuids: explicitVideoUuids,
          startDate: _startDate,
          endDate: _endDate,
          genders: _selectedGenders.isNotEmpty ? _selectedGenders : null,
          ageGroups: _selectedAgeGroups.isNotEmpty ? _selectedAgeGroups : null,
          dataSource: _dataSource,
        );
        
        if (mounted && demographicsResponse.success && demographicsResponse.data != null) {
          setState(() {
            _demographicsData = demographicsResponse.data!;
          });
        }
      } catch (e) {
        debugPrint('⚠️  Failed to load demographics data: $e');
        // Don't fail the whole page if demographics fails
      }
      
      // Load behavioral analytics data for Level 4 analytics
      try {
        final behavioralResponse = await apiClient.getBehavioralAnalytics(
          timeFilter: _timeFilter,
          cameraIds: _selectedCollectionIds.isNotEmpty ? _selectedCollectionIds : null,
          videoUuids: explicitVideoUuids,
          startDate: _startDate,
          endDate: _endDate,
          genders: _selectedGenders.isNotEmpty ? _selectedGenders : null,
          ageGroups: _selectedAgeGroups.isNotEmpty ? _selectedAgeGroups : null,
          dataSource: _dataSource,
        );
        
        if (mounted && behavioralResponse.success && behavioralResponse.data != null) {
          setState(() {
            _behavioralData = behavioralResponse.data!;
          });
        }
      } catch (e) {
        debugPrint('⚠️  Failed to load behavioral data: $e');
        // Don't fail the whole page if behavioral fails
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = e.toString();
          _isLoading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: CustomAppBar(
        title: 'MVR Analytics',
        actions: [
          // Refresh button
          IconButton(
            onPressed: _isLoading ? null : _loadAnalytics,
            icon: const Icon(Icons.refresh),
            tooltip: 'Refresh',
          ),
          // Filter button
          IconButton(
            onPressed: _showFilterDialog,
            icon: const Icon(Icons.filter_list),
            tooltip: 'Filters',
          ),
        ],
      ),
      body: Column(
        children: [
          // Filter summary bar
          _buildFilterBar(),
          
          // Main content
          Expanded(
            child: _isLoading
                ? _buildLoadingState()
                : _error != null
                    ? _buildErrorState()
                    : _buildAnalyticsDashboard(),
          ),
        ],
      ),
    );
  }

  /// Build filter bar showing current filters
  Widget _buildFilterBar() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      decoration: BoxDecoration(
        color: AppColors.surface,
        border: Border(
          bottom: BorderSide(color: Colors.grey.shade300),
        ),
      ),
      child: Row(
        children: [
          Icon(Icons.filter_list, size: 16, color: Colors.grey.shade600),
          const SizedBox(width: 8),
          Text(
            'Time: ${_getTimeFilterLabel()}',
            style: TextStyle(
              fontSize: 14,
              color: Colors.grey.shade700,
              fontWeight: FontWeight.w500,
            ),
          ),
          if (_selectedCollectionIds.isNotEmpty) ...[
            const SizedBox(width: 16),
            Text(
              'Collections: ${_selectedCollectionIds.length} selected',
              style: TextStyle(
                fontSize: 14,
                color: Colors.grey.shade700,
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
          if (_selectedGenders.isNotEmpty || _selectedAgeGroups.isNotEmpty) ...[
            const SizedBox(width: 16),
            Text(
              'Demographics: ${[..._selectedGenders, ..._selectedAgeGroups].join(", ")}',
              style: TextStyle(
                fontSize: 14,
                color: Colors.grey.shade700,
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
          if (_dataSource == 'instant_detection') ...[
            const SizedBox(width: 12),
            Chip(
              label: const Text('Instant Detection'),
              avatar: const Icon(Icons.visibility, size: 16),
              backgroundColor: Colors.orange.shade100,
              deleteIcon: const Icon(Icons.close, size: 16),
              onDeleted: () {
                setState(() => _dataSource = 'recording');
                _loadAnalytics();
              },
              materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
              visualDensity: VisualDensity.compact,
            ),
          ],
          const Spacer(),
          if (_autoRefresh)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(
                color: Colors.green.shade50,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: Colors.green.shade300),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.sync, size: 12, color: Colors.green.shade700),
                  const SizedBox(width: 4),
                  Text(
                    'Auto-refresh',
                    style: TextStyle(
                      fontSize: 12,
                      color: Colors.green.shade700,
                    ),
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }

  String _getTimeFilterLabel() {
    switch (_timeFilter) {
      case 'today':
        return 'Today';
      case 'last_hour':
        return 'Last Hour';
      case 'last_3_hours':
        return 'Last 3 Hours';
      case 'last_week':
        return 'Last Week';
      case 'last_month':
        return 'Last Month';
      case 'custom':
        if (_startDate != null && _endDate != null) {
          final fmt = DateFormat('MMM d, HH:mm');
          return '${fmt.format(_startDate!)} - ${fmt.format(_endDate!)}';
        }
        return 'Custom Range';
      default:
        return 'Today';
    }
  }

  /// Format datetime to relative time string (e.g., "2 hours ago")
  String _formatRelativeTime(DateTime dateTime) {
    final now = DateTime.now();
    final difference = now.difference(dateTime);

    if (difference.inSeconds < 60) {
      return '${difference.inSeconds}s ago';
    } else if (difference.inMinutes < 60) {
      return '${difference.inMinutes}m ago';
    } else if (difference.inHours < 24) {
      return '${difference.inHours}h ago';
    } else if (difference.inDays < 7) {
      return '${difference.inDays}d ago';
    } else if (difference.inDays < 30) {
      final weeks = (difference.inDays / 7).floor();
      return '${weeks}w ago';
    } else {
      final months = (difference.inDays / 30).floor();
      return '${months}mo ago';
    }
  }

  /// Build loading state
  Widget _buildLoadingState() {
    return const Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          CircularProgressIndicator(),
          SizedBox(height: 16),
          Text('Loading analytics...'),
        ],
      ),
    );
  }

  /// Build error state
  Widget _buildErrorState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.error_outline, size: 64, color: Colors.red.shade300),
          const SizedBox(height: 16),
          Text(
            'Failed to load analytics',
            style: TextStyle(
              fontSize: 18,
              color: Colors.grey.shade700,
              fontWeight: FontWeight.w500,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            _error ?? 'Unknown error',
            style: TextStyle(
              fontSize: 14,
              color: Colors.grey.shade600,
            ),
          ),
          const SizedBox(height: 24),
          ElevatedButton.icon(
            onPressed: _loadAnalytics,
            icon: const Icon(Icons.refresh),
            label: const Text('Retry'),
          ),
        ],
      ),
    );
  }

  /// Build main analytics dashboard
  Widget _buildAnalyticsDashboard() {
    return RefreshIndicator(
      onRefresh: _loadAnalytics,
      child: SingleChildScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // People Counters automation tile (admin-only)
            const PeopleCountersTile(),
            const SizedBox(height: 8),
            // Section header
            LayoutBuilder(
              builder: (context, constraints) {
                final isCompact = constraints.maxWidth < 520;

                final titleRow = Row(
                  children: const [
                    Icon(Icons.analytics, color: AppColors.primary),
                    SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        'MVR People Detection Analytics',
                        style: TextStyle(
                          fontSize: 20,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                  ],
                );

                final exportButton = OutlinedButton.icon(
                  onPressed: _showExportDialog,
                  icon: const Icon(Icons.download, size: 18),
                  label: const Text('Export'),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: AppColors.primary,
                  ),
                );

                if (isCompact) {
                  return Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      titleRow,
                      const SizedBox(height: 12),
                      exportButton,
                    ],
                  );
                }

                return Row(
                  children: [
                    Expanded(child: titleRow),
                    const SizedBox(width: 16),
                    exportButton,
                  ],
                );
              },
            ),
            const SizedBox(height: 8),
            Text(
              'Real-time insights from camera collection MVR search results',
              style: TextStyle(
                fontSize: 14,
                color: Colors.grey.shade600,
              ),
            ),
            
            const SizedBox(height: 24),
            
            // Level 1: Basic Metrics
            _buildBasicMetricsSection(),
            
            const SizedBox(height: 24),
            
            // NEW: MVR Quality Metrics Section
            if (_mvrQualityMetrics != null) ...[
              _buildMvrQualitySection(),
              const SizedBox(height: 24),
            ],
            
            // Level 2: Time-Based Trends
            if (_timeSeriesData != null) ...[
              _buildTimeBasedTrendsSection(),
              const SizedBox(height: 24),
            ],
            
            // Level 3: Demographics
            if (_demographicsData != null) ...[
              _buildDemographicsSection(),
              const SizedBox(height: 24),
            ],
            
            // Level 4: Behavioral Insights
            if (_behavioralData != null) ...[
              _buildBehavioralSection(),
              const SizedBox(height: 24),
            ],
          ],
        ),
      ),
    );
  }

  /// Build Level 1: Basic metrics section
  Widget _buildBasicMetricsSection() {
    debugPrint('🎨 Analytics: Building basic metrics section');
    debugPrint('   - _mvrQualityMetrics: ${_mvrQualityMetrics != null ? "LOADED" : "NULL"}');
    if (_mvrQualityMetrics != null) {
      debugPrint('   - hasQualityData: ${_mvrQualityMetrics!.hasQualityData}');
      debugPrint('   - averageQuality: ${_mvrQualityMetrics!.averageQuality}');
      debugPrint('   - qualityGrade: ${_mvrQualityMetrics!.qualityGrade}');
    }
    
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(
                color: AppColors.primary.withOpacity(0.1),
                borderRadius: BorderRadius.circular(4),
              ),
              child: const Text(
                'LEVEL 1',
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.bold,
                  color: AppColors.primary,
                ),
              ),
            ),
            const SizedBox(width: 8),
            const Text(
              'Basic Metrics',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),
          ],
        ),
        const SizedBox(height: 16),
        
        // Summary cards grid
        LayoutBuilder(
          builder: (context, constraints) {
            final isWide = constraints.maxWidth > 1000;
            final isTablet = constraints.maxWidth > 600 && constraints.maxWidth <= 1000;
            final crossAxisCount = isWide ? 4 : 2;

            final gridDelegate = SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: crossAxisCount,
              mainAxisSpacing: 16,
              crossAxisSpacing: 16,
              childAspectRatio: isWide
                  ? 1.6
                  : isTablet
                      ? 1.45
                      : 1.15,
              mainAxisExtent: isWide
                  ? null
                  : isTablet
                      ? 142
                      : 156,
            );

            return GridView(
              gridDelegate: gridDelegate,
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              children: [
                _buildMetricCard(
                  title: 'Total People',
                  value: _analyticsSummary?.totalPeople.toString() ?? '--',
                  icon: Icons.people,
                  color: Colors.blue,
                  subtitle: 'Unique individuals',
                ),
                _buildMetricCard(
                  title: 'Active Collections',
                  value: _analyticsSummary?.activeCameras.toString() ?? '--',
                  icon: Icons.videocam,
                  color: Colors.green,
                  subtitle: 'With detections',
                ),
                _buildMetricCard(
                  title: _dataSource == 'instant_detection' ? 'Sessions' : 'Videos Analyzed',
                  value: _dataSource == 'instant_detection'
                      ? '${_mvrQualityMetrics?.trackingSessionsCount ?? 0}'
                      : _analyticsSummary?.totalVideos.toString() ?? '--',
                  icon: _dataSource == 'instant_detection' ? Icons.visibility : Icons.movie,
                  color: Colors.orange,
                  subtitle: _dataSource == 'instant_detection' ? 'Detection sessions' : 'In time range',
                ),
                // NEW: Show Image Quality as main metric
                if (_mvrQualityMetrics != null && _mvrQualityMetrics!.hasQualityData)
                  _buildMetricCard(
                    title: 'Image Quality',
                    value: _mvrQualityMetrics!.averageQuality?.toStringAsFixed(2) ?? '--',
                    icon: Icons.high_quality,
                    color: _getQualityGradeColor(_mvrQualityMetrics!.qualityGrade ?? 'Unknown'),
                    subtitle: _mvrQualityMetrics!.qualityGrade ?? 'No grade',
                  )
                else
                  _buildMetricCard(
                    title: 'Last Detection',
                    value: _analyticsSummary?.lastDetection != null
                        ? _formatRelativeTime(_analyticsSummary!.lastDetection!)
                        : '--',
                    icon: Icons.access_time,
                    color: Colors.purple,
                    subtitle: 'Most recent',
                  ),
              ],
            );
          },
        ),
      ],
    );
  }

  /// Build metric card widget
  Widget _buildMetricCard({
    required String title,
    required String value,
    required IconData icon,
    required Color color,
    String? subtitle,
  }) {
    return Card(
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          mainAxisSize: MainAxisSize.min,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: color.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Icon(icon, color: color, size: 20),
                ),
                const Spacer(),
                Icon(Icons.trending_up, size: 16, color: Colors.grey.shade400),
              ],
            ),
            const SizedBox(height: 8),
            Flexible(
              child: Text(
                value,
                style: const TextStyle(
                  fontSize: 26,
                  fontWeight: FontWeight.bold,
                ),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ),
            const SizedBox(height: 2),
            Text(
              title,
              style: TextStyle(
                fontSize: 13,
                color: Colors.grey.shade700,
                fontWeight: FontWeight.w500,
              ),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
            if (subtitle != null)
              Text(
                subtitle,
                style: TextStyle(
                  fontSize: 11,
                  color: Colors.grey.shade500,
                ),
              ),
          ],
        ),
      ),
    );
  }

  /// Build Level 2: Time-Based Trends section
  Widget _buildTimeBasedTrendsSection() {
    if (_timeSeriesData == null) return const SizedBox.shrink();
    
    final dataPoints = (_timeSeriesData!['data_points'] as List?) ?? [];
    final interval = _timeSeriesData!['interval'] as String? ?? 'hour';
    final peakCount = _timeSeriesData!['peak_count'] as int? ?? 0;
    final averageCount = (_timeSeriesData!['average_count'] as num?)?.toDouble() ?? 0.0;
    final totalCount = _timeSeriesData!['total_count'] as int? ?? 0;
    
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(
                color: Colors.orange.withOpacity(0.1),
                borderRadius: BorderRadius.circular(4),
              ),
              child: const Text(
                'LEVEL 2',
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.bold,
                  color: Colors.orange,
                ),
              ),
            ),
            const SizedBox(width: 8),
            const Text(
              'Time-Based Trends',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),
          ],
        ),
        const SizedBox(height: 16),
        
        // Summary stats cards
        Row(
          children: [
            Expanded(
              child: _buildTrendStatCard(
                title: 'Total',
                value: totalCount.toString(),
                icon: Icons.people,
                color: Colors.blue,
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: _buildTrendStatCard(
                title: 'Peak',
                value: peakCount.toString(),
                icon: Icons.trending_up,
                color: Colors.green,
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: _buildTrendStatCard(
                title: 'Average',
                value: averageCount.toStringAsFixed(1),
                icon: Icons.show_chart,
                color: Colors.purple,
              ),
            ),
          ],
        ),
        
        const SizedBox(height: 24),
        
        // Time-series chart
        if (dataPoints.isNotEmpty) ...[
          Card(
            elevation: 2,
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Icon(Icons.timeline, size: 20, color: Colors.grey.shade700),
                      const SizedBox(width: 8),
                      Text(
                        'Activity Over Time',
                        style: TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.w600,
                          color: Colors.grey.shade800,
                        ),
                      ),
                      const Spacer(),
                      Chip(
                        label: Text(
                          interval == 'hour' ? 'Hourly' : 'Daily',
                          style: const TextStyle(fontSize: 12),
                        ),
                        backgroundColor: Colors.blue.shade50,
                        side: BorderSide(color: Colors.blue.shade200),
                      ),
                    ],
                  ),
                  const SizedBox(height: 24),
                  SizedBox(
                    height: 250,
                    child: _buildTimeSeriesChart(dataPoints, interval),
                  ),
                ],
              ),
            ),
          ),
        ] else ...[
          Card(
            elevation: 1,
            child: Padding(
              padding: const EdgeInsets.all(32),
              child: Center(
                child: Column(
                  children: [
                    Icon(Icons.info_outline, size: 48, color: Colors.grey.shade400),
                    const SizedBox(height: 16),
                    Text(
                      'No time-series data available for this period',
                      style: TextStyle(
                        fontSize: 14,
                        color: Colors.grey.shade600,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ],
      ],
    );
  }

  /// Build trend stat card
  Widget _buildTrendStatCard({
    required String title,
    required String value,
    required IconData icon,
    required Color color,
  }) {
    return Card(
      elevation: 1,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(6),
                  decoration: BoxDecoration(
                    color: color.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: Icon(icon, color: color, size: 16),
                ),
                const Spacer(),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              value,
              style: const TextStyle(
                fontSize: 24,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              title,
              style: TextStyle(
                fontSize: 12,
                color: Colors.grey.shade600,
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// Build time-series line chart using fl_chart
  Widget _buildTimeSeriesChart(List<dynamic> dataPoints, String interval) {
    if (dataPoints.isEmpty) {
      return const Center(child: Text('No data available'));
    }

    return LineChart(
      LineChartData(
        gridData: const FlGridData(show: false),
        titlesData: FlTitlesData(
          show: true,
          rightTitles: const AxisTitles(
            sideTitles: SideTitles(showTitles: false),
          ),
          topTitles: const AxisTitles(
            sideTitles: SideTitles(showTitles: false),
          ),
          bottomTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              reservedSize: 30,
              interval: dataPoints.length > 12 ? (dataPoints.length / 6).ceilToDouble() : 2,
              getTitlesWidget: (value, meta) {
                final index = value.toInt();
                if (index < 0 || index >= dataPoints.length) return const Text('');
                
                final point = dataPoints[index] as Map<String, dynamic>;
                final timestamp = DateTime.parse(point['timestamp'] as String);
                
                String label;
                if (interval == 'hour') {
                  label = DateFormat('HH:mm').format(timestamp);
                } else {
                  label = DateFormat('MM/dd').format(timestamp);
                }
                
                return Text(
                  label,
                  style: TextStyle(
                    fontSize: 10,
                    color: Colors.grey.shade600,
                  ),
                );
              },
            ),
          ),
          leftTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              reservedSize: 40,
              getTitlesWidget: (value, meta) {
                return Text(
                  value.toInt().toString(),
                  style: TextStyle(
                    fontSize: 10,
                    color: Colors.grey.shade600,
                  ),
                );
              },
            ),
          ),
        ),
        borderData: FlBorderData(
          show: true,
          border: Border(
            bottom: BorderSide(color: Colors.grey.shade300),
            left: BorderSide(color: Colors.grey.shade300),
          ),
        ),
        minX: 0,
        maxX: (dataPoints.length - 1).toDouble(),
        minY: 0,
        maxY: (_timeSeriesData!['peak_count'] as int? ?? 10).toDouble() * 1.2,
        lineBarsData: [
          LineChartBarData(
            spots: dataPoints.asMap().entries.map((entry) {
              final index = entry.key;
              final point = entry.value as Map<String, dynamic>;
              final count = (point['count'] as int? ?? 0).toDouble();
              return FlSpot(index.toDouble(), count);
            }).toList(),
            isCurved: true,
            color: AppColors.primary,
            barWidth: 3,
            isStrokeCapRound: true,
            dotData: FlDotData(
              show: dataPoints.length <= 24,
              getDotPainter: (spot, percent, barData, index) {
                return FlDotCirclePainter(
                  radius: 4,
                  color: Colors.white,
                  strokeWidth: 2,
                  strokeColor: AppColors.primary,
                );
              },
            ),
            belowBarData: BarAreaData(
              show: true,
              color: AppColors.primary.withOpacity(0.1),
            ),
          ),
        ],
        lineTouchData: LineTouchData(
          enabled: true,
          touchTooltipData: LineTouchTooltipData(
            getTooltipItems: (touchedSpots) {
              return touchedSpots.map((spot) {
                final index = spot.x.toInt();
                if (index < 0 || index >= dataPoints.length) return null;
                
                final point = dataPoints[index] as Map<String, dynamic>;
                final timestamp = DateTime.parse(point['timestamp'] as String);
                final count = point['count'] as int? ?? 0;
                
                String timeLabel;
                if (interval == 'hour') {
                  timeLabel = DateFormat('HH:mm').format(timestamp);
                } else {
                  timeLabel = DateFormat('MMM dd').format(timestamp);
                }
                
                return LineTooltipItem(
                  '$timeLabel\n$count people',
                  const TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.bold,
                    fontSize: 12,
                  ),
                );
              }).toList();
            },
          ),
        ),
      ),
    );
  }

  /// Build Level 3: Demographics section with pie charts
  Widget _buildDemographicsSection() {
    if (_demographicsData == null) return const SizedBox.shrink();
    
    final genderData = _demographicsData!['gender_distribution'] as Map<String, dynamic>?;
    final ageData = _demographicsData!['age_distribution'] as Map<String, dynamic>?;
    final totalPeople = _demographicsData!['total_people'] as int? ?? 0;
    
    if (totalPeople == 0) {
      return const SizedBox.shrink();
    }
    
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(
                color: Colors.purple.shade50,
                borderRadius: BorderRadius.circular(4),
                border: Border.all(color: Colors.purple.shade200),
              ),
              child: Row(
                children: [
                  Icon(Icons.auto_awesome, size: 14, color: Colors.purple.shade700),
                  const SizedBox(width: 4),
                  Text(
                    'Level 3',
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                      color: Colors.purple.shade700,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 12),
            const Icon(Icons.people, color: AppColors.primary, size: 20),
            const SizedBox(width: 8),
            const Text(
              'Demographics Distribution',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
        const SizedBox(height: 16),
        
        // Total people summary
        Card(
          elevation: 1,
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              children: [
                Icon(Icons.groups, color: AppColors.primary, size: 32),
                const SizedBox(width: 16),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '$totalPeople',
                      style: const TextStyle(
                        fontSize: 28,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    Text(
                      'Total People Analyzed',
                      style: TextStyle(
                        fontSize: 14,
                        color: Colors.grey.shade600,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 16),
        
        // Gender and Age pie charts - responsive layout
        LayoutBuilder(
          builder: (context, constraints) {
            // Use vertical layout for mobile (width < 600px)
            final isMobile = constraints.maxWidth < 600;
            
            if (isMobile) {
              return Column(
                children: [
                  _buildGenderPieChart(genderData),
                  const SizedBox(height: 16),
                  _buildAgePieChart(ageData),
                ],
              );
            } else {
              return Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Gender distribution
                  Expanded(
                    child: _buildGenderPieChart(genderData),
                  ),
                  const SizedBox(width: 16),
                  // Age distribution
                  Expanded(
                    child: _buildAgePieChart(ageData),
                  ),
                ],
              );
            }
          },
        ),
      ],
    );
  }

  /// Build gender distribution pie chart
  Widget _buildGenderPieChart(Map<String, dynamic>? genderData) {
    if (genderData == null) return const SizedBox.shrink();
    
    final male = genderData['male'] as int? ?? 0;
    final female = genderData['female'] as int? ?? 0;
    final unknown = genderData['unknown'] as int? ?? 0;
    final total = male + female + unknown;
    
    if (total == 0) return const SizedBox.shrink();
    
    return Card(
      elevation: 1,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.wc, color: Colors.blue.shade600, size: 20),
                const SizedBox(width: 8),
                const Text(
                  'Gender Distribution',
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 24),
            SizedBox(
              height: 200,
              child: PieChart(
                PieChartData(
                  sections: [
                    if (male > 0)
                      PieChartSectionData(
                        value: male.toDouble(),
                        title: '${(male / total * 100).toStringAsFixed(1)}%',
                        color: Colors.blue.shade600,
                        radius: 80,
                        titleStyle: const TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.bold,
                          color: Colors.white,
                        ),
                      ),
                    if (female > 0)
                      PieChartSectionData(
                        value: female.toDouble(),
                        title: '${(female / total * 100).toStringAsFixed(1)}%',
                        color: Colors.pink.shade400,
                        radius: 80,
                        titleStyle: const TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.bold,
                          color: Colors.white,
                        ),
                      ),
                    if (unknown > 0)
                      PieChartSectionData(
                        value: unknown.toDouble(),
                        title: '${(unknown / total * 100).toStringAsFixed(1)}%',
                        color: Colors.grey.shade400,
                        radius: 80,
                        titleStyle: const TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.bold,
                          color: Colors.white,
                        ),
                      ),
                  ],
                  sectionsSpace: 2,
                  centerSpaceRadius: 40,
                ),
              ),
            ),
            const SizedBox(height: 16),
            // Legend
            Wrap(
              spacing: 16,
              runSpacing: 8,
              children: [
                if (male > 0) _buildLegendItem('Male', Colors.blue.shade600, male),
                if (female > 0) _buildLegendItem('Female', Colors.pink.shade400, female),
                if (unknown > 0) _buildLegendItem('Unknown', Colors.grey.shade400, unknown),
              ],
            ),
          ],
        ),
      ),
    );
  }

  /// Build age distribution pie chart
  Widget _buildAgePieChart(Map<String, dynamic>? ageData) {
    if (ageData == null) return const SizedBox.shrink();
    
    final young = ageData['young'] as int? ?? 0;
    final adult = ageData['adult'] as int? ?? 0;
    final middleAged = ageData['middle_aged'] as int? ?? 0;
    final elderly = ageData['elderly'] as int? ?? 0;
    final unknown = ageData['unknown'] as int? ?? 0;
    final total = young + adult + middleAged + elderly + unknown;
    
    if (total == 0) return const SizedBox.shrink();
    
    return Card(
      elevation: 1,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.cake, color: Colors.orange.shade600, size: 20),
                const SizedBox(width: 8),
                const Text(
                  'Age Distribution',
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 24),
            SizedBox(
              height: 200,
              child: PieChart(
                PieChartData(
                  sections: [
                    if (young > 0)
                      PieChartSectionData(
                        value: young.toDouble(),
                        title: '${(young / total * 100).toStringAsFixed(1)}%',
                        color: Colors.green.shade400,
                        radius: 80,
                        titleStyle: const TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.bold,
                          color: Colors.white,
                        ),
                      ),
                    if (adult > 0)
                      PieChartSectionData(
                        value: adult.toDouble(),
                        title: '${(adult / total * 100).toStringAsFixed(1)}%',
                        color: Colors.blue.shade400,
                        radius: 80,
                        titleStyle: const TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.bold,
                          color: Colors.white,
                        ),
                      ),
                    if (middleAged > 0)
                      PieChartSectionData(
                        value: middleAged.toDouble(),
                        title: '${(middleAged / total * 100).toStringAsFixed(1)}%',
                        color: Colors.orange.shade400,
                        radius: 80,
                        titleStyle: const TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.bold,
                          color: Colors.white,
                        ),
                      ),
                    if (elderly > 0)
                      PieChartSectionData(
                        value: elderly.toDouble(),
                        title: '${(elderly / total * 100).toStringAsFixed(1)}%',
                        color: Colors.purple.shade400,
                        radius: 80,
                        titleStyle: const TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.bold,
                          color: Colors.white,
                        ),
                      ),
                    if (unknown > 0)
                      PieChartSectionData(
                        value: unknown.toDouble(),
                        title: '${(unknown / total * 100).toStringAsFixed(1)}%',
                        color: Colors.grey.shade400,
                        radius: 80,
                        titleStyle: const TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.bold,
                          color: Colors.white,
                        ),
                      ),
                  ],
                  sectionsSpace: 2,
                  centerSpaceRadius: 40,
                ),
              ),
            ),
            const SizedBox(height: 16),
            // Legend
            Wrap(
              spacing: 16,
              runSpacing: 8,
              children: [
                if (young > 0) _buildLegendItem('Young', Colors.green.shade400, young),
                if (adult > 0) _buildLegendItem('Adult', Colors.blue.shade400, adult),
                if (middleAged > 0) _buildLegendItem('Middle Aged', Colors.orange.shade400, middleAged),
                if (elderly > 0) _buildLegendItem('Elderly', Colors.purple.shade400, elderly),
                if (unknown > 0) _buildLegendItem('Unknown', Colors.grey.shade400, unknown),
              ],
            ),
          ],
        ),
      ),
    );
  }

  /// Build legend item for pie charts
  Widget _buildLegendItem(String label, Color color, int count) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 12,
          height: 12,
          decoration: BoxDecoration(
            color: color,
            shape: BoxShape.circle,
          ),
        ),
        const SizedBox(width: 6),
        Text(
          '$label ($count)',
          style: const TextStyle(fontSize: 12),
        ),
      ],
    );
  }

  /// Build Level 4: Behavioral Insights section
  Widget _buildBehavioralSection() {
    if (_behavioralData == null) return const SizedBox.shrink();
    
    final totalDetections = _behavioralData!['total_detections'] as int? ?? 0;
    final weeklyHeatmap = _behavioralData!['weekly_heatmap'] as Map<String, dynamic>? ?? {};
    
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(
                color: Colors.orange.shade50,
                borderRadius: BorderRadius.circular(4),
                border: Border.all(color: Colors.orange.shade200),
              ),
              child: Row(
                children: [
                  Icon(Icons.psychology, size: 14, color: Colors.orange.shade700),
                  const SizedBox(width: 4),
                  Text(
                    'Level 4',
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                      color: Colors.orange.shade700,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 12),
            const Icon(Icons.show_chart, color: AppColors.primary, size: 20),
            const SizedBox(width: 8),
            const Text(
              'Behavioral Insights',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
        const SizedBox(height: 16),
        
        // Show message if no data
        if (totalDetections == 0)
          Card(
            child: Padding(
              padding: const EdgeInsets.all(24.0),
              child: Center(
                child: Column(
                  children: [
                    Icon(Icons.info_outline, size: 48, color: Colors.grey.shade400),
                    const SizedBox(height: 16),
                    Text(
                      'No behavioral data available',
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.w500,
                        color: Colors.grey.shade700,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Try selecting a different time period or camera',
                      style: TextStyle(
                        fontSize: 14,
                        color: Colors.grey.shade600,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          )
        else ...[
          // Weekly heatmap
          _buildWeeklyHeatmap(),
          
          const SizedBox(height: 16),
          
          // Peak times and detection occurrence
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Peak times
              Expanded(
                child: _buildPeakTimesCard(),
              ),
              const SizedBox(width: 16),
              // Detection occurrence / visit frequency
              Expanded(
                child: _buildDetectionOccurrenceCard(),
              ),
            ],
          ),
          
          const SizedBox(height: 16),
          
          // Camera comparison
          _buildCameraComparisonChart(),
        ],
      ],
    );
  }

  /// Build weekly activity heatmap
  Widget _buildWeeklyHeatmap() {
    final heatmapData = _behavioralData!['weekly_heatmap'] as Map<String, dynamic>?;
    if (heatmapData == null) return const SizedBox.shrink();
    
    final days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
    
    // Find max value for color scaling
    int maxValue = 0;
    for (var dayData in heatmapData.values) {
      if (dayData is Map<String, dynamic>) {
        for (var hourValue in dayData.values) {
          if (hourValue is int && hourValue > maxValue) {
            maxValue = hourValue;
          }
        }
      }
    }
    
    return Card(
      elevation: 1,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.grid_on, color: Colors.blue.shade600, size: 20),
                const SizedBox(width: 8),
                const Text(
                  'Weekly Activity Heatmap',
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            // Heatmap grid
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Hour labels
                  Row(
                    children: [
                      const SizedBox(width: 80), // Space for day labels
                      ...List.generate(24, (hour) {
                        return Container(
                          width: 30,
                          alignment: Alignment.center,
                          child: Text(
                            '${hour.toString().padLeft(2, '0')}',
                            style: TextStyle(
                              fontSize: 10,
                              color: Colors.grey.shade400,
                            ),
                          ),
                        );
                      }),
                    ],
                  ),
                  const SizedBox(height: 4),
                  // Heatmap rows
                  ...days.map((day) {
                    final dayData = heatmapData[day] as Map<String, dynamic>? ?? {};
                    return Padding(
                      padding: const EdgeInsets.only(bottom: 2),
                      child: Row(
                        children: [
                          // Day label
                          SizedBox(
                            width: 80,
                            child: Text(
                              day.substring(0, 3),
                              style: TextStyle(
                                fontSize: 12, 
                                fontWeight: FontWeight.w500,
                                color: Colors.grey.shade300,
                              ),
                            ),
                          ),
                          // Hour cells
                          ...List.generate(24, (hour) {
                            final value = dayData[hour.toString()] as int? ?? 0;
                            return Container(
                              width: 30,
                              height: 30,
                              margin: const EdgeInsets.only(right: 2),
                              decoration: BoxDecoration(
                                color: Colors.grey.shade800,
                                borderRadius: BorderRadius.circular(4),
                                border: value > 0 
                                    ? Border.all(color: AppColors.primary, width: 1.5)
                                    : Border.all(color: Colors.grey.shade700, width: 0.5),
                              ),
                              alignment: Alignment.center,
                              child: value > 0
                                  ? Text(
                                      '$value',
                                      style: const TextStyle(
                                        fontSize: 9,
                                        fontWeight: FontWeight.w600,
                                        color: Colors.white,
                                      ),
                                    )
                                  : null,
                            );
                          }),
                        ],
                      ),
                    );
                  }),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// Build peak times card
  Widget _buildPeakTimesCard() {
    final peakHours = _behavioralData!['peak_hours'] as List? ?? [];
    final peakDays = _behavioralData!['peak_days'] as List? ?? [];
    
    return Card(
      elevation: 1,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.schedule, color: Colors.green.shade600, size: 20),
                const SizedBox(width: 8),
                const Text(
                  'Peak Activity Times',
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            if (peakHours.isNotEmpty) ...[
              const Text(
                'Top Hours',
                style: TextStyle(fontSize: 12, fontWeight: FontWeight.w500),
              ),
              const SizedBox(height: 8),
              ...peakHours.take(3).map((peak) {
                final timeLabel = peak['time_label'] as String? ?? '';
                final count = peak['count'] as int? ?? 0;
                return Padding(
                  padding: const EdgeInsets.only(bottom: 4),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(timeLabel, style: const TextStyle(fontSize: 12)),
                      Text('$count', style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
                    ],
                  ),
                );
              }),
            ],
            if (peakDays.isNotEmpty) ...[
              const SizedBox(height: 16),
              const Text(
                'Top Days',
                style: TextStyle(fontSize: 12, fontWeight: FontWeight.w500),
              ),
              const SizedBox(height: 8),
              ...peakDays.map((peak) {
                final day = peak['day'] as String? ?? '';
                final count = peak['count'] as int? ?? 0;
                return Padding(
                  padding: const EdgeInsets.only(bottom: 4),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(day, style: const TextStyle(fontSize: 12)),
                      Text('$count', style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
                    ],
                  ),
                );
              }),
            ],
          ],
        ),
      ),
    );
  }

  /// Build detection occurrence card
  Widget _buildDetectionOccurrenceCard() {
    final visitFreq = _behavioralData!['visit_frequency'] as Map<String, dynamic>?;
    if (visitFreq == null) return const SizedBox.shrink();

    final isInstantDetection = _dataSource == 'instant_detection';
    final title = isInstantDetection ? 'Visit Frequency' : 'Detection Occurence';
    
    final newVisitors = visitFreq['new_visitors'] as int? ?? 0;
    final returning = visitFreq['returning_visitors'] as int? ?? 0;
    final frequent = visitFreq['frequent_visitors'] as int? ?? 0;
    final total = newVisitors + returning + frequent;
    
    return Card(
      elevation: 1,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.repeat, color: Colors.purple.shade600, size: 20),
                const SizedBox(width: 8),
                Text(
                  title,
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            if (isInstantDetection) ...[
              _buildFrequencyUnavailableRow('New'),
              const SizedBox(height: 8),
              _buildFrequencyUnavailableRow('Returning'),
              const SizedBox(height: 8),
              _buildFrequencyUnavailableRow('Frequent'),
            ] else ...[
              _buildFrequencyRow('Single Pass', newVisitors, total, Colors.blue.shade400),
              const SizedBox(height: 8),
              _buildFrequencyRow('Double Pass', returning, total, Colors.green.shade400),
              const SizedBox(height: 8),
              _buildFrequencyRow('Frequent', frequent, total, Colors.orange.shade400),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildFrequencyUnavailableRow(String label) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(label, style: const TextStyle(fontSize: 12)),
        const Text(
          'N/A',
          style: TextStyle(fontSize: 12, fontWeight: FontWeight.w500),
        ),
      ],
    );
  }

  /// Build frequency row with progress bar
  Widget _buildFrequencyRow(String label, int count, int total, Color color) {
    final percentage = total > 0 ? (count / total * 100).round() : 0;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(label, style: const TextStyle(fontSize: 12)),
            Text('$count ($percentage%)', style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w500)),
          ],
        ),
        const SizedBox(height: 4),
        LinearProgressIndicator(
          value: total > 0 ? count / total : 0,
          backgroundColor: Colors.grey.shade200,
          valueColor: AlwaysStoppedAnimation<Color>(color),
        ),
      ],
    );
  }

  /// Build camera comparison chart
  Widget _buildCameraComparisonChart() {
    final comparison = _behavioralData!['camera_comparison'] as List? ?? [];
    if (comparison.isEmpty) return const SizedBox.shrink();
    
    // Find max for scaling
    final maxPeople = comparison.fold<int>(0, (max, cam) {
      final count = cam['total_people'] as int? ?? 0;
      return count > max ? count : max;
    });
    
    return Card(
      elevation: 1,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.leaderboard, color: Colors.indigo.shade600, size: 20),
                const SizedBox(width: 8),
                const Text(
                  'Top Active Cameras',
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            ...comparison.map((cam) {
              final cameraId = cam['camera_id'] as String? ?? '';
              final cameraName = (cam['camera_name'] as String?)?.trim();
              final cameraLabel = (cameraName != null && cameraName.isNotEmpty) ? cameraName : cameraId;
              final totalPeople = cam['total_people'] as int? ?? 0;
              final barWidth = maxPeople > 0 ? (totalPeople / maxPeople) : 0.0;
              
              return Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Expanded(
                          child: Text(
                            cameraLabel,
                            style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w500),
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        Text(
                          '$totalPeople people',
                          style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold),
                        ),
                      ],
                    ),
                    const SizedBox(height: 4),
                    LinearProgressIndicator(
                      value: barWidth,
                      backgroundColor: Colors.grey.shade200,
                      valueColor: AlwaysStoppedAnimation<Color>(Colors.indigo.shade400),
                      minHeight: 8,
                    ),
                  ],
                ),
              );
            }),
          ],
        ),
      ),
    );
  }

  /// Show filter dialog
  Future<void> _showFilterDialog() async {
    final result = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (context) => _FilterDialog(
        currentTimeFilter: _timeFilter,
        selectedCollectionIds: _selectedCollectionIds,
        selectedGenders: _selectedGenders,
        selectedAgeGroups: _selectedAgeGroups,
        dataSource: _dataSource,
        autoRefresh: _autoRefresh,
        cameras: _cameras,
        startDate: _startDate,
        endDate: _endDate,
      ),
    );

    if (result != null && mounted) {
      setState(() {
        _timeFilter = result['timeFilter'] as String;
        _selectedCollectionIds = result['collectionIds'] as List<String>;
        _selectedGenders = result['genders'] as List<String>;
        _selectedAgeGroups = result['ageGroups'] as List<String>;
        _dataSource = result['dataSource'] as String? ?? 'recording';
        _autoRefresh = result['autoRefresh'] as bool;
        _startDate = result['startDate'] as DateTime?;
        _endDate = result['endDate'] as DateTime?;
      });
      await _persistDataSourcePreference();
      await _loadAnalytics();
    }
  }

  /// Show export dialog
  Future<void> _showExportDialog() async {
    if (_analyticsSummary == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('No analytics data to export')),
      );
      return;
    }

    await showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Export Analytics'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              leading: const Icon(Icons.table_chart, color: Colors.green),
              title: const Text('Excel Spreadsheet'),
              subtitle: const Text('Open with Excel, LibreOffice, etc.'),
              onTap: () {
                Navigator.pop(context);
                _exportToExcel();
              },
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
        ],
      ),
    );
  }

  int _exportCount(Map<String, dynamic>? data, String key) {
    return (data?[key] as num?)?.toInt() ?? 0;
  }

  double _exportPercentage(Map<String, dynamic>? data, String key) {
    return (data?[key] as num?)?.toDouble() ?? 0.0;
  }

  /// Export analytics data to Excel file
  Future<void> _exportToExcel() async {
    if (_analyticsSummary == null) return;

    try {
      // Show loading indicator
      if (mounted) {
        showDialog(
          context: context,
          barrierDismissible: false,
          builder: (context) => const Center(
            child: Card(
              child: Padding(
                padding: EdgeInsets.all(24.0),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    CircularProgressIndicator(),
                    SizedBox(height: 16),
                    Text('Generating Excel file...'),
                  ],
                ),
              ),
            ),
          ),
        );
      }

      // Create Excel workbook
      final excelFile = excel.Excel.createExcel();
      final sheet = excelFile['Analytics Summary'];
      excelFile.delete('Sheet1'); // Remove default sheet

      // Format time filter for display
      String timeFilterLabel = _getTimeFilterLabel();
      String collectionLabel = _selectedCollectionIds.isEmpty 
          ? 'All Collections' 
          : _selectedCollectionIds.length == 1
              ? _selectedCollectionIds.first
              : '${_selectedCollectionIds.length} Collections';

      // Title row
      sheet.appendRow([
        excel.TextCellValue('MVR Analytics Summary Report'),
      ]);

      // Report metadata
      sheet.appendRow([
        excel.TextCellValue('Collection: $collectionLabel'),
      ]);
      sheet.appendRow([
        excel.TextCellValue('Time Period: $timeFilterLabel'),
      ]);
      sheet.appendRow([
        excel.TextCellValue('Generated: ${DateFormat('yyyy-MM-dd HH:mm:ss').format(_analyticsSummary!.generatedAt)}'),
      ]);
      sheet.appendRow([]);

      // Summary section
      sheet.appendRow([
        excel.TextCellValue('SUMMARY METRICS'),
      ]);
      sheet.appendRow([
        excel.TextCellValue('Total People Detected'),
        excel.IntCellValue(_analyticsSummary!.totalPeople),
      ]);
      sheet.appendRow([
        excel.TextCellValue('Active Collections'),
        excel.IntCellValue(_analyticsSummary!.activeCameras),
      ]);
      sheet.appendRow([
        excel.TextCellValue('Total Videos Processed'),
        excel.IntCellValue(_analyticsSummary!.totalVideos),
      ]);
      sheet.appendRow([]);

      final demographicsData = _demographicsData;
      final genderData = demographicsData?['gender_distribution'] as Map<String, dynamic>?;
      final ageData = demographicsData?['age_distribution'] as Map<String, dynamic>?;
      final demographicsCameraBreakdown = (demographicsData?['camera_breakdown'] as List?)
          ?.whereType<Map>()
          .map((entry) => entry.cast<String, dynamic>())
          .toList();

      // Demographics section
      if (genderData != null || ageData != null) {

        sheet.appendRow([
          excel.TextCellValue('DEMOGRAPHICS'),
        ]);
        sheet.appendRow([
          excel.TextCellValue('Gender Distribution'),
        ]);
        sheet.appendRow([
          excel.TextCellValue('Male'),
          excel.IntCellValue(_exportCount(genderData, 'male')),
          excel.TextCellValue('${_exportPercentage(genderData, 'male_percentage').toStringAsFixed(1)}%'),
        ]);
        sheet.appendRow([
          excel.TextCellValue('Female'),
          excel.IntCellValue(_exportCount(genderData, 'female')),
          excel.TextCellValue('${_exportPercentage(genderData, 'female_percentage').toStringAsFixed(1)}%'),
        ]);
        sheet.appendRow([
          excel.TextCellValue('Unknown'),
          excel.IntCellValue(_exportCount(genderData, 'unknown')),
          excel.TextCellValue('${_exportPercentage(genderData, 'unknown_percentage').toStringAsFixed(1)}%'),
        ]);
        sheet.appendRow([]);

        sheet.appendRow([
          excel.TextCellValue('Age Distribution'),
        ]);
        sheet.appendRow([
          excel.TextCellValue('Young'),
          excel.IntCellValue(_exportCount(ageData, 'young')),
          excel.TextCellValue('${_exportPercentage(ageData, 'young_percentage').toStringAsFixed(1)}%'),
        ]);
        sheet.appendRow([
          excel.TextCellValue('Adult'),
          excel.IntCellValue(_exportCount(ageData, 'adult')),
          excel.TextCellValue('${_exportPercentage(ageData, 'adult_percentage').toStringAsFixed(1)}%'),
        ]);
        sheet.appendRow([
          excel.TextCellValue('Middle Aged'),
          excel.IntCellValue(_exportCount(ageData, 'middle_aged')),
          excel.TextCellValue('${_exportPercentage(ageData, 'middle_aged_percentage').toStringAsFixed(1)}%'),
        ]);
        sheet.appendRow([
          excel.TextCellValue('Elderly'),
          excel.IntCellValue(_exportCount(ageData, 'elderly')),
          excel.TextCellValue('${_exportPercentage(ageData, 'elderly_percentage').toStringAsFixed(1)}%'),
        ]);
        sheet.appendRow([
          excel.TextCellValue('Unknown'),
          excel.IntCellValue(_exportCount(ageData, 'unknown')),
          excel.TextCellValue('${_exportPercentage(ageData, 'unknown_percentage').toStringAsFixed(1)}%'),
        ]);
        sheet.appendRow([]);
      }

      // Collection breakdown
      if ((demographicsCameraBreakdown != null && demographicsCameraBreakdown.isNotEmpty) ||
          _analyticsSummary!.cameraBreakdown.isNotEmpty) {
        sheet.appendRow([
          excel.TextCellValue('COLLECTION BREAKDOWN'),
        ]);
        sheet.appendRow([
          excel.TextCellValue('Collection'),
          excel.TextCellValue('People'),
          excel.TextCellValue('Male'),
          excel.TextCellValue('Female'),
          excel.TextCellValue('Unknown Gender'),
          excel.TextCellValue('Young'),
          excel.TextCellValue('Adult'),
          excel.TextCellValue('Middle Aged'),
          excel.TextCellValue('Elderly'),
          excel.TextCellValue('Unknown Age'),
        ]);

        if (demographicsCameraBreakdown != null && demographicsCameraBreakdown.isNotEmpty) {
          for (final collection in demographicsCameraBreakdown) {
            final collectionLabel = ((collection['camera_name'] as String?)?.trim().isNotEmpty ?? false)
                ? (collection['camera_name'] as String).trim()
                : (collection['camera_id'] as String? ?? 'Unknown');
            final collectionGender = collection['gender'] as Map<String, dynamic>?;
            final collectionAge = collection['age'] as Map<String, dynamic>?;

            sheet.appendRow([
              excel.TextCellValue(collectionLabel),
              excel.IntCellValue(_exportCount(collection, 'total_people')),
              excel.IntCellValue(_exportCount(collectionGender, 'male')),
              excel.IntCellValue(_exportCount(collectionGender, 'female')),
              excel.IntCellValue(_exportCount(collectionGender, 'unknown')),
              excel.IntCellValue(_exportCount(collectionAge, 'young')),
              excel.IntCellValue(_exportCount(collectionAge, 'adult')),
              excel.IntCellValue(_exportCount(collectionAge, 'middle_aged')),
              excel.IntCellValue(_exportCount(collectionAge, 'elderly')),
              excel.IntCellValue(_exportCount(collectionAge, 'unknown')),
            ]);
          }
        } else {
          for (final collection in _analyticsSummary!.cameraBreakdown) {
            final demo = collection.demographics;
            final collectionLabel = (collection.cameraName != null && collection.cameraName!.trim().isNotEmpty)
                ? collection.cameraName!.trim()
                : collection.cameraId;
            sheet.appendRow([
              excel.TextCellValue(collectionLabel),
              excel.IntCellValue(collection.peopleCount),
              excel.IntCellValue(demo?.maleCount ?? 0),
              excel.IntCellValue(demo?.femaleCount ?? 0),
              const excel.IntCellValue(0),
              excel.IntCellValue(demo?.youngCount ?? 0),
              excel.IntCellValue(demo?.adultCount ?? 0),
              const excel.IntCellValue(0),
              excel.IntCellValue(demo?.elderlyCount ?? 0),
              const excel.IntCellValue(0),
            ]);
          }
        }
      }

      // Set column widths
      sheet.setColumnWidth(0, 30);
      sheet.setColumnWidth(1, 15);
      sheet.setColumnWidth(2, 15);
      sheet.setColumnWidth(3, 12);
      sheet.setColumnWidth(4, 12);
      sheet.setColumnWidth(5, 12);
      sheet.setColumnWidth(6, 12);
      sheet.setColumnWidth(7, 12);
      sheet.setColumnWidth(8, 12);
      sheet.setColumnWidth(9, 12);

      // Generate file
      final fileBytes = excelFile.encode();
      if (fileBytes == null) {
        throw Exception('Failed to encode Excel file');
      }

      if (mounted) Navigator.of(context).pop();

      final timestamp = DateTime.now().millisecondsSinceEpoch;
      final sanitizedFilter = timeFilterLabel.replaceAll(RegExp(r'[^a-zA-Z0-9_-]'), '_');
      final fileName = 'analytics_${sanitizedFilter}_$timestamp.xlsx';

      if (kIsWeb) {
        await downloadFileBytes(
          bytes: fileBytes,
          filename: fileName,
          mimeType:
              'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        );

        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Excel file downloaded successfully'),
              backgroundColor: Colors.green,
            ),
          );
        }
      } else {
        final directory = await getTemporaryDirectory();
        final filePath = '${directory.path}/$fileName';
        final file = File(filePath);
        await file.writeAsBytes(fileBytes);

        await Share.shareXFiles(
          [XFile(filePath)],
          subject: 'MVR Analytics Summary - $timeFilterLabel',
        );

        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Excel file ready to share'),
              backgroundColor: Colors.green,
            ),
          );
        }
      }
    } catch (e, stackTrace) {
      debugPrint('Error generating Excel file: $e');
      debugPrint('Stack trace: $stackTrace');

      if (mounted && Navigator.of(context).canPop()) {
        Navigator.of(context).pop();
      }

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to generate Excel: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  /// Build MVR Quality Metrics Section
  Widget _buildMvrQualitySection() {
    if (_mvrQualityMetrics == null) return const SizedBox();
    
    final metrics = _mvrQualityMetrics!;
    
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(
                color: Colors.deepPurple.withOpacity(0.1),
                borderRadius: BorderRadius.circular(4),
              ),
              child: const Text(
                'LEVEL 1.5',
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.bold,
                  color: Colors.deepPurple,
                ),
              ),
            ),
            const SizedBox(width: 8),
            const Text(
              'MVR Quality Metrics',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(width: 8),
            Tooltip(
              message: 'Quality metrics from MVR (Multi-Video Recognition) tracking system',
              child: Icon(Icons.info_outline, size: 18, color: Colors.grey.shade600),
            ),
          ],
        ),
        const SizedBox(height: 16),
        
        // Tracking sessions overview
        Card(
          elevation: 2,
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(Icons.track_changes, size: 20, color: Colors.deepPurple.shade700),
                    const SizedBox(width: 8),
                    Text(
                      'Tracking Sessions Overview',
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.w600,
                        color: Colors.grey.shade800,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                Row(
                  children: [
                    Expanded(
                      child: _buildQualityMetricTile(
                        label: 'Sessions',
                        value: metrics.trackingSessionsCount.toString(),
                        icon: Icons.collections,
                        color: Colors.blue,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: _buildQualityMetricTile(
                        label: 'Computed',
                        value: metrics.totalIndividuals.toString(),
                        icon: Icons.person,
                        color: Colors.green,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: _buildQualityMetricTile(
                        label: 'Detected',
                        value: metrics.totalMvrPeople.toString(),
                        icon: Icons.people_alt,
                        color: Colors.orange,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: _buildQualityMetricTile(
                        label: _dataSource == 'instant_detection' ? 'Sessions' : 'Videos',
                        value: metrics.totalVideosProcessed.toString(),
                        icon: _dataSource == 'instant_detection' ? Icons.visibility : Icons.video_library,
                        color: Colors.purple,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
        
        const SizedBox(height: 16),
        
        // Quality scores breakdown
        Card(
          elevation: 2,
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(Icons.analytics, size: 20, color: Colors.deepPurple.shade700),
                    const SizedBox(width: 8),
                    Text(
                      'Quality Scores',
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.w600,
                        color: Colors.grey.shade800,
                      ),
                    ),
                    const Spacer(),
                    if (metrics.qualityGrade != null)
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                        decoration: BoxDecoration(
                          color: _getQualityGradeColor(metrics.qualityGrade!).withOpacity(0.1),
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(
                            color: _getQualityGradeColor(metrics.qualityGrade!),
                            width: 2,
                          ),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(
                              _getQualityGradeIcon(metrics.qualityGrade!),
                              size: 16,
                              color: _getQualityGradeColor(metrics.qualityGrade!),
                            ),
                            const SizedBox(width: 6),
                            Text(
                              metrics.qualityGrade!,
                              style: TextStyle(
                                fontSize: 14,
                                fontWeight: FontWeight.bold,
                                color: _getQualityGradeColor(metrics.qualityGrade!),
                              ),
                            ),
                          ],
                        ),
                      ),
                  ],
                ),
                const SizedBox(height: 16),
                
                // Quality statistics
                if (metrics.hasQualityData) ...[
                  Row(
                    children: [
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Average Quality',
                              style: TextStyle(
                                fontSize: 14,
                                color: Colors.grey.shade600,
                              ),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              metrics.averageQuality?.toStringAsFixed(3) ?? '--',
                              style: const TextStyle(
                                fontSize: 24,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ],
                        ),
                      ),
                      Container(
                        width: 1,
                        height: 50,
                        color: Colors.grey.shade300,
                      ),
                      const SizedBox(width: 16),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Range',
                              style: TextStyle(
                                fontSize: 14,
                                color: Colors.grey.shade600,
                              ),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              '${metrics.minQuality?.toStringAsFixed(2) ?? '--'} → ${metrics.maxQuality?.toStringAsFixed(2) ?? '--'}',
                              style: const TextStyle(
                                fontSize: 18,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ],
                        ),
                      ),
                      Container(
                        width: 1,
                        height: 50,
                        color: Colors.grey.shade300,
                      ),
                      const SizedBox(width: 16),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Std Dev',
                              style: TextStyle(
                                fontSize: 14,
                                color: Colors.grey.shade600,
                              ),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              metrics.qualityStdDev?.toStringAsFixed(3) ?? '--',
                              style: const TextStyle(
                                fontSize: 18,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 20),
                  
                  // Data completeness progress bar
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text(
                            'Data Completeness',
                            style: TextStyle(
                              fontSize: 14,
                              color: Colors.grey.shade700,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                          Text(
                            '${metrics.qualityCompleteness.toStringAsFixed(1)}%',
                            style: TextStyle(
                              fontSize: 14,
                              color: Colors.grey.shade700,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      ClipRRect(
                        borderRadius: BorderRadius.circular(4),
                        child: LinearProgressIndicator(
                          value: metrics.qualityCompleteness / 100,
                          minHeight: 8,
                          backgroundColor: Colors.grey.shade200,
                          valueColor: AlwaysStoppedAnimation<Color>(
                            _getCompletenessColor(metrics.qualityCompleteness),
                          ),
                        ),
                      ),
                      const SizedBox(height: 8),
                      Row(
                        children: [
                          Expanded(
                            child: Text(
                              '${metrics.mvrWithQuality} with quality',
                              style: TextStyle(
                                fontSize: 12,
                                color: Colors.green.shade700,
                              ),
                            ),
                          ),
                          Text(
                            '${metrics.mvrWithoutQuality} without quality',
                            style: TextStyle(
                              fontSize: 12,
                              color: Colors.grey.shade600,
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ] else ...[
                  Center(
                    child: Padding(
                      padding: const EdgeInsets.all(24.0),
                      child: Column(
                        children: [
                          Icon(Icons.info_outline, size: 48, color: Colors.grey.shade400),
                          const SizedBox(height: 12),
                          Text(
                            'No quality data available for this time period',
                            style: TextStyle(
                              fontSize: 14,
                              color: Colors.grey.shade600,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildQualityMetricTile({
    required String label,
    required String value,
    required IconData icon,
    required Color color,
  }) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: color.withOpacity(0.05),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withOpacity(0.2)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, size: 20, color: color),
          const SizedBox(height: 8),
          Text(
            value,
            style: TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.bold,
              color: Colors.grey.shade800,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            label,
            style: TextStyle(
              fontSize: 12,
              color: Colors.grey.shade600,
            ),
          ),
        ],
      ),
    );
  }

  Color _getQualityGradeColor(String grade) {
    switch (grade.toLowerCase()) {
      case 'excellent':
        return Colors.green.shade700;
      case 'good':
        return Colors.lightGreen.shade700;
      case 'fair':
        return Colors.orange.shade700;
      case 'poor':
        return Colors.deepOrange.shade700;
      case 'very poor':
        return Colors.red.shade700;
      default:
        return Colors.grey.shade700;
    }
  }

  IconData _getQualityGradeIcon(String grade) {
    switch (grade.toLowerCase()) {
      case 'excellent':
        return Icons.stars;
      case 'good':
        return Icons.thumb_up;
      case 'fair':
        return Icons.horizontal_rule;
      case 'poor':
        return Icons.thumb_down;
      case 'very poor':
        return Icons.warning;
      default:
        return Icons.help_outline;
    }
  }

  Color _getCompletenessColor(double percentage) {
    if (percentage >= 80) return Colors.green;
    if (percentage >= 60) return Colors.lightGreen;
    if (percentage >= 40) return Colors.orange;
    if (percentage >= 20) return Colors.deepOrange;
    return Colors.red;
  }
}

/// Filter dialog for analytics
class _FilterDialog extends StatefulWidget {
  final String currentTimeFilter;
  final List<String> selectedCollectionIds;
  final List<String> selectedGenders;
  final List<String> selectedAgeGroups;
  final String dataSource;
  final bool autoRefresh;
  final List<Map<String, dynamic>> cameras;
  final DateTime? startDate;
  final DateTime? endDate;

  const _FilterDialog({
    required this.currentTimeFilter,
    required this.selectedCollectionIds,
    required this.selectedGenders,
    required this.selectedAgeGroups,
    this.dataSource = 'recording',
    required this.autoRefresh,
    required this.cameras,
    this.startDate,
    this.endDate,
  });

  @override
  State<_FilterDialog> createState() => _FilterDialogState();
}

class _FilterDialogState extends State<_FilterDialog> {
  late String _timeFilter;
  late List<String> _selectedCollectionIds;
  late List<String> _selectedGenders;
  late List<String> _selectedAgeGroups;
  late String _dataSource;
  late bool _autoRefresh;
  DateTime? _startDate;
  DateTime? _endDate;

  @override
  void initState() {
    super.initState();
    _timeFilter = widget.currentTimeFilter;
    _selectedCollectionIds = List.from(widget.selectedCollectionIds);
    _selectedGenders = List.from(widget.selectedGenders);
    _selectedAgeGroups = List.from(widget.selectedAgeGroups);
    _dataSource = widget.dataSource;
    _autoRefresh = widget.autoRefresh;
    _startDate = widget.startDate;
    _endDate = widget.endDate;
  }

  Future<void> _pickDateTime({required bool isStart}) async {
    final now = DateTime.now();
    final initialDate = isStart
        ? (_startDate ?? now.subtract(const Duration(days: 7)))
        : (_endDate ?? now);

    final date = await showDatePicker(
      context: context,
      initialDate: initialDate,
      firstDate: DateTime(2020),
      lastDate: now,
    );
    if (date == null) return;

    if (!mounted) return;
    final time = await showTimePicker(
      context: context,
      initialTime: TimeOfDay.fromDateTime(initialDate),
    );
    if (time == null) return;

    final picked = DateTime(date.year, date.month, date.day, time.hour, time.minute);
    setState(() {
      if (isStart) {
        _startDate = picked;
      } else {
        _endDate = picked;
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Filter Analytics'),
      content: SizedBox(
        width: 500,
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Data Source Filter
              const Text(
                'Data Source',
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                children: [
                  ChoiceChip(
                    label: const Text('Video Recording'),
                    selected: _dataSource == 'recording',
                    onSelected: (_) => setState(() => _dataSource = 'recording'),
                    selectedColor: Colors.blue.shade100,
                    avatar: _dataSource == 'recording'
                        ? const Icon(Icons.videocam, size: 18)
                        : const Icon(Icons.videocam_outlined, size: 18),
                  ),
                  ChoiceChip(
                    label: const Text('Instant Detection'),
                    selected: _dataSource == 'instant_detection',
                    onSelected: (_) => setState(() => _dataSource = 'instant_detection'),
                    selectedColor: Colors.orange.shade100,
                    avatar: _dataSource == 'instant_detection'
                        ? const Icon(Icons.visibility, size: 18)
                        : const Icon(Icons.visibility_outlined, size: 18),
                  ),
                ],
              ),
              const SizedBox(height: 4),
              Text(
                _dataSource == 'recording'
                    ? 'Analytics from video recording sessions (default)'
                    : 'Analytics from real-time instant detection sessions',
                style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
              ),
              const SizedBox(height: 20),
              // Time Range Filter
              const Text(
                'Time Range',
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 12),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  _buildFilterChip('Today', 'today'),
                  _buildFilterChip('Last Hour', 'last_hour'),
                  _buildFilterChip('Last 3 Hours', 'last_3_hours'),
                  _buildFilterChip('Last Week', 'last_week'),
                  _buildFilterChip('Last Month', 'last_month'),
                  _buildFilterChip('Custom Range', 'custom'),
                ],
              ),
              
              // Custom date range pickers
              if (_timeFilter == 'custom') ...[
                const SizedBox(height: 16),
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: () => _pickDateTime(isStart: true),
                        icon: const Icon(Icons.calendar_today, size: 16),
                        label: Text(
                          _startDate != null
                              ? DateFormat('MMM d, yyyy HH:mm').format(_startDate!)
                              : 'Start Date',
                          style: const TextStyle(fontSize: 13),
                        ),
                      ),
                    ),
                    const Padding(
                      padding: EdgeInsets.symmetric(horizontal: 8),
                      child: Icon(Icons.arrow_forward, size: 16, color: Colors.grey),
                    ),
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: () => _pickDateTime(isStart: false),
                        icon: const Icon(Icons.calendar_today, size: 16),
                        label: Text(
                          _endDate != null
                              ? DateFormat('MMM d, yyyy HH:mm').format(_endDate!)
                              : 'End Date',
                          style: const TextStyle(fontSize: 13),
                        ),
                      ),
                    ),
                  ],
                ),
                if (_timeFilter == 'custom' && (_startDate == null || _endDate == null))
                  Padding(
                    padding: const EdgeInsets.only(top: 8),
                    child: Text(
                      'Please select both start and end dates',
                      style: TextStyle(fontSize: 12, color: Colors.orange.shade700),
                    ),
                  ),
              ],
              
              const SizedBox(height: 24),
              
              // Collections Filter (Multi-select)
              Row(
                children: [
                  const Text(
                    'Collections',
                    style: TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const Spacer(),
                  TextButton(
                    onPressed: () {
                      setState(() {
                        _selectedCollectionIds.clear();
                      });
                    },
                    child: const Text('Clear'),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Text(
                _selectedCollectionIds.isEmpty
                    ? 'All collections (${widget.cameras.length})'
                    : '${_selectedCollectionIds.length} selected',
                style: TextStyle(
                  fontSize: 12,
                  color: Colors.grey.shade600,
                ),
              ),
              const SizedBox(height: 12),
              Container(
                constraints: const BoxConstraints(maxHeight: 200),
                decoration: BoxDecoration(
                  border: Border.all(color: Colors.grey.shade300),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: ListView(
                  shrinkWrap: true,
                  children: widget.cameras.map((camera) {
                    final id = (camera['id'] ?? camera['collection_name'] ?? camera['name'] ?? camera['uuid'] ?? camera['device_id'])?.toString() ?? '';
                    final name = (camera['name'] ?? camera['collection_name'] ?? camera['device_id'] ?? id).toString();
                    final isSelected = _selectedCollectionIds.contains(id);
                    
                    return CheckboxListTile(
                      dense: true,
                      title: Text(name),
                      value: isSelected,
                      onChanged: (checked) {
                        setState(() {
                          if (checked == true) {
                            if (!_selectedCollectionIds.contains(id)) {
                              _selectedCollectionIds.add(id);
                            }
                          } else {
                            _selectedCollectionIds.remove(id);
                          }
                        });
                      },
                    );
                  }).toList(),
                ),
              ),
              
              const SizedBox(height: 24),
              
              // Demographics Filter
              const Text(
                'Demographics',
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 12),
              
              // Gender Filter
              const Text(
                'Gender',
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w500,
                ),
              ),
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  _buildDemographicChip('Male', 'male', _selectedGenders),
                  _buildDemographicChip('Female', 'female', _selectedGenders),
                ],
              ),
              
              const SizedBox(height: 16),
              
              // Age Filter
              const Text(
                'Age Group',
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w500,
                ),
              ),
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  _buildDemographicChip('Young (0-25)', 'young', _selectedAgeGroups),
                  _buildDemographicChip('Adult (26-65)', 'adult', _selectedAgeGroups),
                  _buildDemographicChip('Elderly (65+)', 'elderly', _selectedAgeGroups),
                ],
              ),
              
              const SizedBox(height: 24),
              
              SwitchListTile(
                title: const Text('Auto-refresh (10 min)'),
                subtitle: const Text('Automatically update data'),
                value: _autoRefresh,
                onChanged: (value) {
                  setState(() {
                    _autoRefresh = value;
                  });
                },
              ),
            ],
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Cancel'),
        ),
        ElevatedButton(
          onPressed: () {
            if (_timeFilter == 'custom' && (_startDate == null || _endDate == null)) {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('Please select both start and end dates for custom range')),
              );
              return;
            }
            Navigator.pop(context, {
              'timeFilter': _timeFilter,
              'collectionIds': _selectedCollectionIds,
              'genders': _selectedGenders,
              'ageGroups': _selectedAgeGroups,
              'dataSource': _dataSource,
              'autoRefresh': _autoRefresh,
              'startDate': _timeFilter == 'custom' ? _startDate : null,
              'endDate': _timeFilter == 'custom' ? _endDate : null,
            });
          },
          child: const Text('Apply'),
        ),
      ],
    );
  }

  Widget _buildFilterChip(String label, String value) {
    final isSelected = _timeFilter == value;
    return ChoiceChip(
      label: Text(
        label,
        style: TextStyle(
          color: isSelected ? AppColors.primary : Colors.grey.shade700,
          fontWeight: isSelected ? FontWeight.w600 : FontWeight.normal,
        ),
      ),
      selected: isSelected,
      onSelected: (selected) {
        if (selected) {
          setState(() {
            _timeFilter = value;
          });
        }
      },
      selectedColor: AppColors.primary.withOpacity(0.1),
      backgroundColor: Colors.grey.shade200,
    );
  }

  Widget _buildDemographicChip(String label, String value, List<String> selectedList) {
    final isSelected = selectedList.contains(value);
    return FilterChip(
      label: Text(label),
      selected: isSelected,
      onSelected: (selected) {
        setState(() {
          if (selected) {
            selectedList.add(value);
          } else {
            selectedList.remove(value);
          }
        });
      },
      selectedColor: AppColors.primary.withOpacity(0.2),
      backgroundColor: Colors.grey.shade200,
      checkmarkColor: AppColors.primary,
    );
  }
}
