import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../utils/offline_fonts.dart';
import '../../core/theme/app_theme.dart';
import '../../core/providers/camera_providers.dart';

/// Autonomous instant detection widget that displays real-time face detection results
/// from the camera's instant detection memory cache.
/// 
/// Features:
/// - Auto-refresh every 5 seconds (matches backend sampling rate)
/// - Displays person count with age/gender
/// - Real-time status indicator
/// - Lightweight and independent
class InstantDetectionWidget extends ConsumerStatefulWidget {
  final String cameraId;
  final Duration refreshInterval;

  const InstantDetectionWidget({
    super.key,
    required this.cameraId,
    this.refreshInterval = const Duration(seconds: 5),  // ML inference needs time
  });

  @override
  ConsumerState<InstantDetectionWidget> createState() =>
      _InstantDetectionWidgetState();
}

class _InstantDetectionWidgetState
    extends ConsumerState<InstantDetectionWidget> {
  List<Map<String, dynamic>>? _personObjects;
  Map<String, dynamic>? _demographics;  // NEW: Demographics from backend
  bool _isLoading = false;
  bool _isInstantDetectionRunning = false;
  int? _cachedIteration;
  double? _ageSeconds;
  Timer? _fastPollTimer;  // Fast polling when detection is active (3s)
  Timer? _lazyCheckTimer; // Lazy checking when inactive (10s)

  @override
  void initState() {
    super.initState();
    print('🔍 [INSTANT_DETECTION_WIDGET] initState called for device: ${widget.cameraId}');
    print('🔍 [INSTANT_DETECTION_WIDGET] Configured refresh interval: ${widget.refreshInterval.inSeconds} seconds');
    // Start lazy checking - check every 10 seconds if instant detection started
    _startLazyChecking();
  }

  void _startLazyChecking() {
    // Check periodically (every 10s) if instant detection has started
    _lazyCheckTimer?.cancel();
    _lazyCheckTimer = Timer.periodic(const Duration(seconds: 10), (_) {
      if (mounted && !_isInstantDetectionRunning) {
        _fetchInstantResults(); // This will auto-start fast polling if detection is active
      }
    });
  }

  @override
  void dispose() {
    _fastPollTimer?.cancel();
    _lazyCheckTimer?.cancel();
    super.dispose();
  }

  void _startAutoRefresh() {
    print('🔍 [INSTANT_DETECTION_WIDGET] _startAutoRefresh called');
    print('🔍 [INSTANT_DETECTION_WIDGET] Using refresh interval: ${widget.refreshInterval.inSeconds} seconds');
    // Stop lazy checking, start fast polling
    _lazyCheckTimer?.cancel();
    _fastPollTimer?.cancel();
    _fetchInstantResults(); // Fetch immediately when starting
    _fastPollTimer = Timer.periodic(widget.refreshInterval, (_) {
      if (mounted) {
        print('🔍 [INSTANT_DETECTION_WIDGET] Periodic fetch tick (${widget.refreshInterval.inSeconds}s interval)');
        _fetchInstantResults();
      }
    });
  }

  void _stopAutoRefresh() {
    // Stop fast polling, resume lazy checking
    _fastPollTimer?.cancel();
    _fastPollTimer = null;
    if (mounted) {
      setState(() {
        _personObjects = null;
        _isInstantDetectionRunning = false;
        _isLoading = false;
      });
      // Resume lazy checking
      _startLazyChecking();
    }
  }

  Future<void> _fetchInstantResults() async {
    if (!mounted) return;

    setState(() => _isLoading = true);

    try {
      final cameraService = ref.read(cameraServiceProvider);
      final response = await cameraService.getInstantDetectionResults(widget.cameraId);

      if (!mounted) return;

      if (response != null && response['success'] == true) {
        setState(() {
          _personObjects = (response['person_objects'] as List?)
              ?.cast<Map<String, dynamic>>();
          _demographics = response['demographics'] as Map<String, dynamic>?;  // NEW: Extract demographics
          _isInstantDetectionRunning = true;
          
          // DEBUG: Log what we received
          print('🔍 Instant detection response: people=${_personObjects?.length}, demographics=$_demographics');
          
          // Extract metadata if available
          final metadata = response['_metadata'] as Map<String, dynamic>?;
          if (metadata != null) {
            _cachedIteration = metadata['iteration'] as int?;
            _ageSeconds = metadata['age_seconds'] as double?;
          }
          
          _isLoading = false;
        });
        
        // If we weren't polling before, start now
        if (_fastPollTimer == null && mounted) {
          _startAutoRefresh();
        }
      } else {
        // Silently handle 404/no results - instant detection may not be started yet
        setState(() {
          _personObjects = null;
          _isInstantDetectionRunning = false;
          _isLoading = false;
        });
        
        // Stop polling if instant detection stopped
        if (_fastPollTimer != null) {
          _stopAutoRefresh();
        }
      }
    } catch (e) {
      // Silent fail - instant detection is optional and may not be running
      if (mounted) {
        setState(() {
          _personObjects = null;
          _isInstantDetectionRunning = false;
          _isLoading = false;
        });
        
        // Stop polling on error
        if (_fastPollTimer != null) {
          _stopAutoRefresh();
        }
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final personCount = _personObjects?.length ?? 0;
    final hasDetections = personCount > 0;

    // If not running and not loading, show minimal "inactive" state
    if (!_isInstantDetectionRunning && !_isLoading) {
      return Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        decoration: BoxDecoration(
          color: Colors.grey.withOpacity(0.02),
          border: Border(
            top: BorderSide(
              color: Colors.grey.withOpacity(0.1),
              width: 1,
            ),
          ),
        ),
        child: Row(
          children: [
            Icon(
              Icons.visibility_off,
              size: 13,
              color: Colors.grey.shade400,
            ),
            const SizedBox(width: 6),
            Text(
              'Instant detection inactive',
              style: OfflineFonts.inter(
                fontSize: 11,
                color: Colors.grey.shade500,
              ),
            ),
            const Spacer(),
            InkWell(
              onTap: _fetchInstantResults,
              child: Padding(
                padding: const EdgeInsets.all(4),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.refresh, size: 14, color: Colors.grey.shade600),
                    const SizedBox(width: 4),
                    Text(
                      'Check',
                      style: OfflineFonts.inter(
                        fontSize: 11,
                        color: Colors.grey.shade600,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      );
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: _isInstantDetectionRunning
            ? (hasDetections
                ? Colors.blue.withOpacity(0.05)
                : Colors.grey.withOpacity(0.03))
            : Colors.grey.withOpacity(0.02),
        border: Border(
          top: BorderSide(
            color: _isInstantDetectionRunning
                ? (hasDetections
                    ? Colors.blue.withOpacity(0.2)
                    : Colors.grey.withOpacity(0.2))
                : Colors.grey.withOpacity(0.1),
            width: 1,
          ),
        ),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          // Left side: Status and count
          Expanded(
            child: Row(
              children: [
                // Real-time indicator
                Icon(
                  _isInstantDetectionRunning
                      ? Icons.fiber_manual_record
                      : Icons.radio_button_unchecked,
                  size: 12,
                  color: _isInstantDetectionRunning
                      ? (hasDetections ? Colors.blue : Colors.grey)
                      : Colors.grey.shade400,
                ),
                const SizedBox(width: 8),
                if (_isLoading)
                  SizedBox(
                    width: 14,
                    height: 14,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      color: AppColors.primary,
                    ),
                  )
                else
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        // Main count row
                        Row(
                          children: [
                            Text(
                              'Live: ',
                              style: OfflineFonts.inter(
                                fontSize: 11,
                                color: AppColors.textSecondary,
                              ),
                            ),
                            Text(
                              '$personCount ${personCount == 1 ? 'person' : 'people'}',
                              style: OfflineFonts.inter(
                                fontSize: 12,
                                fontWeight: FontWeight.w600,
                                color: hasDetections
                                    ? Colors.blue.shade700
                                    : Colors.grey.shade600,
                              ),
                            ),
                            if (_ageSeconds != null) ...[
                              Text(
                                ' • ${_ageSeconds!.toStringAsFixed(1)}s ago',
                                style: OfflineFonts.inter(
                                  fontSize: 10,
                                  color: Colors.grey.shade500,
                                ),
                              ),
                            ],
                          ],
                        ),
                        // Demographics row (using backend aggregation)
                        if (hasDetections && _demographics != null)
                          _buildDemographicsRow(),
                      ],
                    ),
                  ),
              ],
            ),
          ),
          // Right side: Refresh indicator
          if (_cachedIteration != null)
            Tooltip(
              message: 'Iteration #$_cachedIteration\nRefreshes every 5s',
              child: Icon(
                Icons.autorenew,
                size: 14,
                color: Colors.blue.shade400,
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildDemographicsRow() {
    if (_demographics == null) {
      return const SizedBox.shrink();
    }

    // Get counts and percentages from backend demographics aggregation
    final maleCount = _demographics!['total_male'] as int? ?? 0;
    final femaleCount = _demographics!['total_female'] as int? ?? 0;
    final youngCount = _demographics!['total_young'] as int? ?? 0;
    final adultCount = _demographics!['total_adult'] as int? ?? 0;
    
    final malePercent = _demographics!['percent_male'] as num? ?? 0;
    final femalePercent = _demographics!['percent_female'] as num? ?? 0;
    final youngPercent = _demographics!['percent_young'] as num? ?? 0;
    final adultPercent = _demographics!['percent_adult'] as num? ?? 0;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Gender row
        if (maleCount > 0 || femaleCount > 0)
          Row(
            children: [
              // Male
              if (maleCount > 0) ...[
                Icon(
                  Icons.male,
                  size: 12,
                  color: Colors.blue.shade600,
                ),
                const SizedBox(width: 2),
                Text(
                  'Male: $maleCount (${malePercent.toStringAsFixed(0)}%)',
                  style: OfflineFonts.inter(
                    fontSize: 11,
                    color: Colors.blue.shade700,
                  ),
                ),
                if (femaleCount > 0) const SizedBox(width: 8),
              ],
              // Female
              if (femaleCount > 0) ...[
                Icon(
                  Icons.female,
                  size: 12,
                  color: Colors.pink.shade600,
                ),
                const SizedBox(width: 2),
                Text(
                  'Female: $femaleCount (${femalePercent.toStringAsFixed(0)}%)',
                  style: OfflineFonts.inter(
                    fontSize: 11,
                    color: Colors.pink.shade700,
                  ),
                ),
              ],
            ],
          ),
        // Age row
        if (youngCount > 0 || adultCount > 0) ...[
          if (maleCount > 0 || femaleCount > 0) const SizedBox(height: 2),
          Row(
            children: [
              // Young
              if (youngCount > 0) ...[
                Icon(
                  Icons.child_care,
                  size: 12,
                  color: Colors.orange.shade600,
                ),
                const SizedBox(width: 2),
                Text(
                  'Young: $youngCount (${youngPercent.toStringAsFixed(0)}%)',
                  style: OfflineFonts.inter(
                    fontSize: 11,
                    color: Colors.orange.shade700,
                  ),
                ),
                if (adultCount > 0) const SizedBox(width: 8),
              ],
              // Adult
              if (adultCount > 0) ...[
                Icon(
                  Icons.person,
                  size: 12,
                  color: Colors.green.shade600,
                ),
                const SizedBox(width: 2),
                Text(
                  'Adult (≥21): $adultCount (${adultPercent.toStringAsFixed(0)}%)',
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
    );
  }
}
