import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../utils/offline_fonts.dart';
import '../../core/theme/app_theme.dart';
import '../../services/media_api_client.dart';
import '../../models/api_models.dart';
import '../../core/providers/camera_providers.dart';

/// Separate counter widget with auto-refresh capability.
/// 
/// This widget is isolated from camera streaming to prevent
/// stream interruptions when the counter updates.
/// 
/// Features:
/// - Auto-refresh every 5 minutes (default)
/// - Manual refresh button with force_refresh
/// - Cache indicator
/// - Loading states
/// - Error handling
class CameraCounterWidget extends ConsumerStatefulWidget {
  final String cameraId;
  final Duration refreshInterval;

  const CameraCounterWidget({
    super.key,
    required this.cameraId,
    this.refreshInterval = const Duration(minutes: 5),
  });

  @override
  ConsumerState<CameraCounterWidget> createState() =>
      _CameraCounterWidgetState();
}

class _CameraCounterWidgetState extends ConsumerState<CameraCounterWidget> {
  int? _mvrPeopleCount;
  int? _videoCount;
  Map<String, dynamic>? _demographics;
  bool _isLoadingCount = false;
  bool _isCached = false;
  DateTime? _cachedAt;
  Timer? _refreshTimer;
  DateTime? _lastRefreshed;
  String _selectedTimeFilter = 'today';

  @override
  void initState() {
    super.initState();
    _fetchCount();
    _startAutoRefresh();
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    super.dispose();
  }

  void _startAutoRefresh() {
    _refreshTimer = Timer.periodic(widget.refreshInterval, (_) {
      if (mounted) {
        debugPrint(
          '🔄 Auto-refreshing counter for camera: ${widget.cameraId}'
        );
        _fetchCount();
      }
    });
  }

  Future<void> _fetchCount({bool forceRefresh = false}) async {
    if (!mounted) return;

    setState(() => _isLoadingCount = true);

    try {
      final mediaApiClient = ref.read(mediaApiClientProvider);

      // Call cached endpoint with time filter
      final response = await mediaApiClient.getCameraMVRCountCached(
        cameraId: widget.cameraId,
        timeFilter: _selectedTimeFilter,
        forceRefresh: forceRefresh,
      );

      if (!mounted) return;

      if (response.success && response.data != null) {
        final data = response.data!;
        setState(() {
          _mvrPeopleCount = data['count'] as int? ?? 0;
          _videoCount = data['video_count'] as int? ?? 0;
          _demographics = data['demographics'] as Map<String, dynamic>?;
          _isCached = data['cached'] as bool? ?? false;
          _lastRefreshed = DateTime.now();

          // Parse cached_at if available
          if (data['cached_at'] != null) {
            try {
              _cachedAt = DateTime.parse(data['cached_at']);
            } catch (e) {
              _cachedAt = null;
            }
          }

          _isLoadingCount = false;
        });

        debugPrint(
          '   ✅ Counter updated: $_mvrPeopleCount people '
          '($_videoCount videos, cached: $_isCached)'
        );
      } else {
        debugPrint('   ❌ Counter fetch failed: ${response.error}');
        if (mounted) {
          setState(() {
            _mvrPeopleCount = 0;
            _videoCount = 0;
            _isLoadingCount = false;
          });
        }
      }
    } catch (e) {
      debugPrint('❌ Error fetching counter: $e');
      if (mounted) {
        setState(() {
          _mvrPeopleCount = 0;
          _videoCount = 0;
          _isLoadingCount = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final count = _mvrPeopleCount ?? 0;
    final hasDetections = count > 0;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: hasDetections
            ? Colors.green.withOpacity(0.05)
            : Colors.grey.withOpacity(0.05),
        border: Border(
          top: BorderSide(
            color: hasDetections
                ? Colors.green.withOpacity(0.2)
                : Colors.grey.withOpacity(0.2),
            width: 1,
          ),
        ),
      ),
      child: Column(
        children: [
          // Time filter dropdown
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Time Period:',
                style: OfflineFonts.inter(
                  fontSize: 11,
                  color: AppColors.textSecondary,
                ),
              ),
              DropdownButton<String>(
                value: _selectedTimeFilter,
                underline: Container(),
                isDense: true,
                style: OfflineFonts.inter(
                  fontSize: 11,
                  color: AppColors.textPrimary,
                ),
                items: const [
                  DropdownMenuItem(value: 'today', child: Text('Today')),
                  DropdownMenuItem(value: 'last_hour', child: Text('Last Hour')),
                  DropdownMenuItem(value: 'last_3_hours', child: Text('Last 3 Hours')),
                  DropdownMenuItem(value: 'last_week', child: Text('Last Week')),
                  DropdownMenuItem(value: 'last_month', child: Text('Last Month')),
                ],
                onChanged: _isLoadingCount ? null : (value) {
                  if (value != null && value != _selectedTimeFilter) {
                    setState(() => _selectedTimeFilter = value);
                    _fetchCount();
                  }
                },
              ),
            ],
          ),
          const SizedBox(height: 8),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              // Counter display
              Expanded(
                child: Row(
                  children: [
                    Icon(
                      Icons.person_outline,
                      size: 16,
                      color: hasDetections
                          ? Colors.green.shade700
                          : Colors.grey.shade600,
                    ),
                    const SizedBox(width: 6),
                    if (_isLoadingCount)
                      Row(
                        children: [
                          SizedBox(
                            width: 14,
                            height: 14,
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                              color: AppColors.primary,
                            ),
                          ),
                          const SizedBox(width: 6),
                          Text(
                            'Loading...',
                            style: OfflineFonts.inter(
                              fontSize: 12,
                              color: AppColors.textSecondary,
                            ),
                          ),
                        ],
                      )
                    else
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                        // Total count
                        Row(
                          children: [
                            Text(
                              'Total: ',
                              style: OfflineFonts.inter(
                                fontSize: 12,
                                color: AppColors.textSecondary,
                              ),
                            ),
                            Text(
                              '$count ${count == 1 ? 'person' : 'people'}',
                              style: OfflineFonts.inter(
                                fontSize: 12,
                                fontWeight: FontWeight.w600,
                                color: hasDetections
                                    ? Colors.green.shade700
                                    : Colors.grey.shade600,
                              ),
                            ),
                            if (_videoCount != null && _videoCount! > 0) ...[
                          Text(
                            ' • ',
                            style: OfflineFonts.inter(
                              fontSize: 12,
                              color: AppColors.textSecondary,
                            ),
                          ),
                              Text(
                                '$_videoCount ${_videoCount == 1 ? 'video' : 'videos'}',
                                style: OfflineFonts.inter(
                                  fontSize: 11,
                                  color: AppColors.textSecondary,
                                ),
                              ),
                            ],
                            // Cache indicator
                            if (_isCached) ...[
                              const SizedBox(width: 6),
                              Tooltip(
                                message: 'Cached result\nUpdates every 5 minutes',
                                child: Icon(
                                  Icons.cached,
                                  size: 12,
                                  color: Colors.blue.shade600,
                                ),
                              ),
                            ],
                          ],
                        ),
                        // Demographics display
                        if (_demographics != null && count > 0) ...[
                          const SizedBox(height: 4),
                          Row(
                            children: [
                              // Gender breakdown with labels (matching instant detection)
                              if (_demographics!['total_male'] != null && _demographics!['total_male'] > 0) ...[
                                Icon(
                                  Icons.male,
                                  size: 12,
                                  color: Colors.blue.shade600,
                                ),
                                const SizedBox(width: 2),
                                Text(
                                  'Male: ${_demographics!['total_male']} (${_demographics!['percent_male']?.toStringAsFixed(0) ?? '0'}%)',
                                  style: OfflineFonts.inter(
                                    fontSize: 11,
                                    color: Colors.blue.shade700,
                                  ),
                                ),
                                const SizedBox(width: 8),
                              ],
                              if (_demographics!['total_female'] != null && _demographics!['total_female'] > 0) ...[
                                Icon(
                                  Icons.female,
                                  size: 12,
                                  color: Colors.pink.shade600,
                                ),
                                const SizedBox(width: 2),
                                Text(
                                  'Female: ${_demographics!['total_female']} (${_demographics!['percent_female']?.toStringAsFixed(0) ?? '0'}%)',
                                  style: OfflineFonts.inter(
                                    fontSize: 11,
                                    color: Colors.pink.shade700,
                                  ),
                                ),
                              ],
                            ],
                          ),
                          const SizedBox(height: 2),
                          Row(
                            children: [
                              // Age breakdown with labels (matching instant detection)
                              if (_demographics!['total_young'] != null && _demographics!['total_young'] > 0) ...[
                                Icon(
                                  Icons.child_care,
                                  size: 12,
                                  color: Colors.orange.shade600,
                                ),
                                const SizedBox(width: 2),
                                Text(
                                  'Young: ${_demographics!['total_young']} (${_demographics!['percent_young']?.toStringAsFixed(0) ?? '0'}%)',
                                  style: OfflineFonts.inter(
                                    fontSize: 11,
                                    color: Colors.orange.shade700,
                                  ),
                                ),
                                const SizedBox(width: 8),
                              ],
                              if (_demographics!['total_adult'] != null && _demographics!['total_adult'] > 0) ...[
                                Icon(
                                  Icons.person,
                                  size: 12,
                                  color: Colors.green.shade600,
                                ),
                                const SizedBox(width: 2),
                                Text(
                                  'Adult (≥21): ${_demographics!['total_adult']} (${_demographics!['percent_adult']?.toStringAsFixed(0) ?? '0'}%)',
                                  style: OfflineFonts.inter(
                                    fontSize: 11,
                                    color: Colors.green.shade700,
                                  ),
                                ),
                              ],
                            ],
                          ),
                        ],
                      ],
                    ),
                  ),
                  ],
                ),
              ),

              // Manual refresh button
              IconButton(
                icon: Icon(
                  Icons.refresh,
                  size: 18,
                  color: _isLoadingCount
                      ? Colors.grey.shade400
                      : AppColors.primary,
                ),
                padding: EdgeInsets.zero,
                constraints: const BoxConstraints(),
                onPressed: _isLoadingCount
                    ? null
                    : () {
                        debugPrint(
                          '🔄 Manual refresh triggered for camera: ${widget.cameraId}'
                        );
                        _fetchCount(forceRefresh: true);
                      },
                tooltip: 'Refresh count (force live query)',
              ),
            ],
          ),
        ],
      ),
    );
  }
}
