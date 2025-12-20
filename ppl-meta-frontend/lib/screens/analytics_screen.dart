import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:flutter/foundation.dart';
import 'dart:io';
import 'dart:convert';
import 'dart:typed_data';
import 'package:excel/excel.dart' as excel;
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';
import 'dart:js' as js if (dart.library.html) 'dart:js';
import '../core/theme/app_theme.dart';
import '../widgets/custom_app_bar.dart';
import '../models/analytics_models.dart';
import '../services/media_api_client.dart';
import '../core/providers/camera_providers.dart';

/// MVR Analytics Dashboard - showing people detection insights from camera collections
/// Based on MVRsearch cached results from camera cards endpoint
class AnalyticsScreen extends ConsumerStatefulWidget {
  const AnalyticsScreen({super.key});

  @override
  ConsumerState<AnalyticsScreen> createState() => _AnalyticsScreenState();
}

class _AnalyticsScreenState extends ConsumerState<AnalyticsScreen> {
  // Filter state
  String _timeFilter = 'today'; // today, last_hour, last_3_hours, last_week, last_month
  List<String> _selectedCollectionIds = []; // empty = all collections
  List<String> _selectedGenders = []; // empty = all genders (male, female)
  List<String> _selectedAgeGroups = []; // empty = all ages (young, adult, elderly)
  bool _autoRefresh = false;
  
  // Loading and error state
  bool _isLoading = false;
  String? _error;
  
  // Analytics data
  AnalyticsSummary? _analyticsSummary;
  List<Map<String, dynamic>> _cameras = [];

  @override
  void initState() {
    super.initState();
    _loadAnalytics();
  }

  Future<void> _loadAnalytics() async {
    setState(() {
      _isLoading = true;
      _error = null;
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
      
      // Load analytics summary from backend endpoint
      final response = await apiClient.getAnalyticsSummary(
        timeFilter: _timeFilter,
        cameraIds: _selectedCollectionIds.isNotEmpty ? _selectedCollectionIds : null,
        forceRefresh: false,
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
            // Section header
            Row(
              children: [
                const Icon(Icons.analytics, color: AppColors.primary),
                const SizedBox(width: 8),
                const Text(
                  'MVR People Detection Analytics',
                  style: TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const Spacer(),
                OutlinedButton.icon(
                  onPressed: _showExportDialog,
                  icon: const Icon(Icons.download, size: 18),
                  label: const Text('Export'),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: AppColors.primary,
                  ),
                ),
              ],
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
            
            // Level 1: Basic Metrics (placeholder)
            _buildBasicMetricsSection(),
            
            const SizedBox(height: 24),
            
            // Coming soon placeholder
            _buildComingSoonPlaceholder(),
          ],
        ),
      ),
    );
  }

  /// Build Level 1: Basic metrics section
  Widget _buildBasicMetricsSection() {
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
            final isWide = constraints.maxWidth > 800;
            final crossAxisCount = isWide ? 4 : 2;
            
            return GridView.count(
              crossAxisCount: crossAxisCount,
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              mainAxisSpacing: 16,
              crossAxisSpacing: 16,
              childAspectRatio: isWide ? 1.5 : 1.2,
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
                  title: 'Videos Analyzed',
                  value: _analyticsSummary?.totalVideos.toString() ?? '--',
                  icon: Icons.movie,
                  color: Colors.orange,
                  subtitle: 'In time range',
                ),
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
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
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
            const SizedBox(height: 12),
            Text(
              value,
              style: const TextStyle(
                fontSize: 28,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              title,
              style: TextStyle(
                fontSize: 14,
                color: Colors.grey.shade700,
                fontWeight: FontWeight.w500,
              ),
            ),
            if (subtitle != null)
              Text(
                subtitle,
                style: TextStyle(
                  fontSize: 12,
                  color: Colors.grey.shade500,
                ),
              ),
          ],
        ),
      ),
    );
  }

  /// Build coming soon placeholder
  Widget _buildComingSoonPlaceholder() {
    return Card(
      elevation: 1,
      child: Container(
        padding: const EdgeInsets.all(32),
        decoration: BoxDecoration(
          border: Border.all(color: Colors.grey.shade300, width: 2),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Column(
          children: [
            Icon(Icons.construction, size: 48, color: Colors.grey.shade400),
            const SizedBox(height: 16),
            Text(
              'Advanced Analytics Coming Soon',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w600,
                color: Colors.grey.shade700,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'Time-based trends, demographics, behavioral analysis, and more',
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 14,
                color: Colors.grey.shade600,
              ),
            ),
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
        autoRefresh: _autoRefresh,
        cameras: _cameras,
      ),
    );

    if (result != null && mounted) {
      setState(() {
        _timeFilter = result['timeFilter'] as String;
        _selectedCollectionIds = result['collectionIds'] as List<String>;
        _selectedGenders = result['genders'] as List<String>;
        _selectedAgeGroups = result['ageGroups'] as List<String>;
        _autoRefresh = result['autoRefresh'] as bool;
      });
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

      // Demographics section
      if (_analyticsSummary!.demographics != null) {
        final demo = _analyticsSummary!.demographics!;

        sheet.appendRow([
          excel.TextCellValue('DEMOGRAPHICS'),
        ]);
        sheet.appendRow([
          excel.TextCellValue('Gender Distribution'),
        ]);
        sheet.appendRow([
          excel.TextCellValue('Male'),
          excel.IntCellValue(demo.maleCount),
          excel.TextCellValue('${demo.malePercentage.toStringAsFixed(1)}%'),
        ]);
        sheet.appendRow([
          excel.TextCellValue('Female'),
          excel.IntCellValue(demo.femaleCount),
          excel.TextCellValue('${demo.femalePercentage.toStringAsFixed(1)}%'),
        ]);
        sheet.appendRow([]);

        sheet.appendRow([
          excel.TextCellValue('Age Distribution'),
        ]);
        sheet.appendRow([
          excel.TextCellValue('Young (0-25)'),
          excel.IntCellValue(demo.youngCount),
          excel.TextCellValue('${demo.youngPercentage.toStringAsFixed(1)}%'),
        ]);
        sheet.appendRow([
          excel.TextCellValue('Adult (26-65)'),
          excel.IntCellValue(demo.adultCount),
          excel.TextCellValue('${demo.adultPercentage.toStringAsFixed(1)}%'),
        ]);
        sheet.appendRow([
          excel.TextCellValue('Elderly (65+)'),
          excel.IntCellValue(demo.elderlyCount),
          excel.TextCellValue('${demo.elderlyPercentage.toStringAsFixed(1)}%'),
        ]);
        sheet.appendRow([]);
      }

      // Collection breakdown
      if (_analyticsSummary!.cameraBreakdown.isNotEmpty) {
        sheet.appendRow([
          excel.TextCellValue('COLLECTION BREAKDOWN'),
        ]);
        sheet.appendRow([
          excel.TextCellValue('Collection ID'),
          excel.TextCellValue('People'),
          excel.TextCellValue('Videos'),
          excel.TextCellValue('Male'),
          excel.TextCellValue('Female'),
          excel.TextCellValue('Young'),
          excel.TextCellValue('Adult'),
          excel.TextCellValue('Elderly'),
        ]);

        for (final collection in _analyticsSummary!.cameraBreakdown) {
          final demo = collection.demographics;
          sheet.appendRow([
            excel.TextCellValue(collection.cameraId),
            excel.IntCellValue(collection.peopleCount),
            excel.IntCellValue(collection.videoCount),
            excel.IntCellValue(demo?.maleCount ?? 0),
            excel.IntCellValue(demo?.femaleCount ?? 0),
            excel.IntCellValue(demo?.youngCount ?? 0),
            excel.IntCellValue(demo?.adultCount ?? 0),
            excel.IntCellValue(demo?.elderlyCount ?? 0),
          ]);
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
        final base64 = base64Encode(fileBytes);
        js.context.callMethod('eval', [
          '''
          (function() {
            var byteCharacters = atob('$base64');
            var byteNumbers = new Array(byteCharacters.length);
            for (var i = 0; i < byteCharacters.length; i++) {
              byteNumbers[i] = byteCharacters.charCodeAt(i);
            }
            var byteArray = new Uint8Array(byteNumbers);
            var blob = new Blob([byteArray], {type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'});
            var url = URL.createObjectURL(blob);
            var a = document.createElement('a');
            a.href = url;
            a.download = '$fileName';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
          })();
        '''
        ]);

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
}

/// Filter dialog for analytics
class _FilterDialog extends StatefulWidget {
  final String currentTimeFilter;
  final List<String> selectedCollectionIds;
  final List<String> selectedGenders;
  final List<String> selectedAgeGroups;
  final bool autoRefresh;
  final List<Map<String, dynamic>> cameras;

  const _FilterDialog({
    required this.currentTimeFilter,
    required this.selectedCollectionIds,
    required this.selectedGenders,
    required this.selectedAgeGroups,
    required this.autoRefresh,
    required this.cameras,
  });

  @override
  State<_FilterDialog> createState() => _FilterDialogState();
}

class _FilterDialogState extends State<_FilterDialog> {
  late String _timeFilter;
  late List<String> _selectedCollectionIds;
  late List<String> _selectedGenders;
  late List<String> _selectedAgeGroups;
  late bool _autoRefresh;

  @override
  void initState() {
    super.initState();
    _timeFilter = widget.currentTimeFilter;
    _selectedCollectionIds = List.from(widget.selectedCollectionIds);
    _selectedGenders = List.from(widget.selectedGenders);
    _selectedAgeGroups = List.from(widget.selectedAgeGroups);
    _autoRefresh = widget.autoRefresh;
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
                ],
              ),
              
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
                    final id = camera['device_id'] as String? ?? camera['id'] as String;
                    final name = camera['name'] as String? ?? camera['device_id'] as String? ?? id;
                    final isSelected = _selectedCollectionIds.contains(id);
                    
                    return CheckboxListTile(
                      dense: true,
                      title: Text(name),
                      value: isSelected,
                      onChanged: (checked) {
                        setState(() {
                          if (checked == true) {
                            _selectedCollectionIds.add(id);
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
            Navigator.pop(context, {
              'timeFilter': _timeFilter,
              'collectionIds': _selectedCollectionIds,
              'genders': _selectedGenders,
              'ageGroups': _selectedAgeGroups,
              'autoRefresh': _autoRefresh,
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
      label: Text(label),
      selected: isSelected,
      onSelected: (selected) {
        if (selected) {
          setState(() {
            _timeFilter = value;
          });
        }
      },
      selectedColor: AppColors.primary.withOpacity(0.2),
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
