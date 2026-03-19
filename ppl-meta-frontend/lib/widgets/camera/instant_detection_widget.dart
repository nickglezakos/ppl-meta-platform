import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../utils/offline_fonts.dart';
import '../../core/theme/app_theme.dart';
import '../../core/providers/camera_providers.dart';

/// Autonomous instant detection widget that displays real-time face detection results
/// from the camera's instant detection memory cache.
/// 
/// Features:
/// - Auto-refresh interval configurable from settings (default 5 seconds)
/// - Displays person count with age/gender demographics
/// - Real-time status indicator
/// - Lightweight and independent
class InstantDetectionWidget extends ConsumerStatefulWidget {
  final String cameraId;

  const InstantDetectionWidget({
    super.key,
    required this.cameraId,
  });

  @override
  ConsumerState<InstantDetectionWidget> createState() =>
      _InstantDetectionWidgetState();
}

class _InstantDetectionWidgetState
    extends ConsumerState<InstantDetectionWidget> {
  List<Map<String, dynamic>>? _personObjects;
  Map<String, dynamic>? _demographics;  // Demographics from backend
  bool _isLoading = false;
  bool _isInstantDetectionRunning = false;
  int? _cachedIteration;
  double? _ageSeconds;
  Timer? _fastPollTimer;  // Fast polling when detection is active
  Timer? _lazyCheckTimer; // Lazy checking when inactive (10s)
  Duration _refreshInterval = const Duration(seconds: 5); // Loaded from settings

  @override
  void initState() {
    super.initState();
    print('🔍 [INSTANT_DETECTION_WIDGET] initState called for device: ${widget.cameraId}');
    _loadRefreshInterval();
    
    // Initial detection state check will happen in build method via ref.listen
  }

  Future<void> _loadRefreshInterval() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final intervalSeconds = prefs.getInt('instant_detection_interval') ?? 5;
      setState(() {
        _refreshInterval = Duration(seconds: intervalSeconds);
      });
      print('🔍 [INSTANT_DETECTION_WIDGET] Loaded refresh interval: $intervalSeconds seconds');
    } catch (e) {
      print('⚠️ [INSTANT_DETECTION_WIDGET] Failed to load refresh interval: $e');
    }
  }

  void _startLazyChecking() {
    // Check periodically (every 10s) if instant detection has started
    _lazyCheckTimer?.cancel();
    _lazyCheckTimer = Timer.periodic(const Duration(seconds: 10), (_) {
      if (mounted && !_isInstantDetectionRunning) {
        _fetchInstantResults(); // This will auto-start fast polling if detection is active
      }
    });
    
    // Immediate check
    _fetchInstantResults();
  }
  
  void _stopAllPolling() {
    // Stop both lazy check and fast poll timers
    _lazyCheckTimer?.cancel();
    _lazyCheckTimer = null;
    _fastPollTimer?.cancel();
    _fastPollTimer = null;
    
    if (mounted) {
      setState(() {
        _personObjects = null;
        _demographics = null;
        _isInstantDetectionRunning = false;
        _isLoading = false;
      });
    }
  }

  @override
  void dispose() {
    _fastPollTimer?.cancel();
    _lazyCheckTimer?.cancel();
    super.dispose();
  }

  void _startAutoRefresh() {
    print('🔍 [INSTANT_DETECTION_WIDGET] _startAutoRefresh called');
    print('🔍 [INSTANT_DETECTION_WIDGET] Using refresh interval: ${_refreshInterval.inSeconds} seconds');
    // Stop lazy checking, start fast polling
    _lazyCheckTimer?.cancel();
    _fastPollTimer?.cancel();
    _fetchInstantResults(); // Fetch immediately when starting
    _fastPollTimer = Timer.periodic(_refreshInterval, (_) {
      if (mounted) {
        print('🔍 [INSTANT_DETECTION_WIDGET] Periodic fetch tick (${_refreshInterval.inSeconds}s interval)');
        _fetchInstantResults();
      }
    });
  }

  void _stopAutoRefresh() {
    // Stop fast polling, resume lazy checking only if detection is active
    _fastPollTimer?.cancel();
    _fastPollTimer = null;
    
    if (mounted) {
      setState(() {
        _personObjects = null;
        _demographics = null;
        _isInstantDetectionRunning = false;
        _isLoading = false;
      });
      
      // Resume lazy checking only if detection is still active
      final detectionState = ref.read(cameraInstantDetectionProvider(widget.cameraId));
      if (detectionState.isDetecting) {
        print('🔍 [INSTANT_DETECTION_WIDGET] Resuming lazy checking (detection still active)');
        _startLazyChecking();
      } else {
        print('🔍 [INSTANT_DETECTION_WIDGET] Not resuming lazy checking (detection not active)');
      }
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
        // DEBUG: Log full response structure
        print('🔍 [INSTANT_DETECTION_WIDGET] Full response keys: ${response.keys.toList()}');
        print('🔍 [INSTANT_DETECTION_WIDGET] Demographics raw: ${response['demographics']}');
        print('🔍 [INSTANT_DETECTION_WIDGET] Demographics type: ${response['demographics']?.runtimeType}');
        
        setState(() {
          _personObjects = (response['person_objects'] as List?)
              ?.cast<Map<String, dynamic>>();
          _demographics = response['demographics'] as Map<String, dynamic>?;  // NEW: Extract demographics
          _isInstantDetectionRunning = true;
          
          // DEBUG: Log what we stored
          print('🔍 [INSTANT_DETECTION_WIDGET] Stored people count: ${_personObjects?.length}');
          print('🔍 [INSTANT_DETECTION_WIDGET] Stored demographics: $_demographics');
          print('🔍 [INSTANT_DETECTION_WIDGET] Demographics is null? ${_demographics == null}');
          print('🔍 [INSTANT_DETECTION_WIDGET] Demographics keys: ${_demographics?.keys}');
          print('🔍 [INSTANT_DETECTION_WIDGET] hasDetections: ${_personObjects?.isNotEmpty ?? false}');
          print('🔍 [INSTANT_DETECTION_WIDGET] Will show demographics row? ${(_personObjects?.isNotEmpty ?? false) && _demographics != null}');
          
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
    final detectionState = ref.watch(cameraInstantDetectionProvider(widget.cameraId));
    
    // Debug: Log state on every build
    print('🎨 [BUILD] hasDetections=$hasDetections, _demographics=${_demographics != null ? "EXISTS" : "NULL"}, personCount=$personCount');
    
    // Set up detection state listener - MUST be in build method for Riverpod
    ref.listen(cameraInstantDetectionProvider(widget.cameraId), (previous, next) {
      print('🔍 [INSTANT_DETECTION_WIDGET] Detection state changed: prev=${previous?.isDetecting}, next=${next.isDetecting}');
      
      if (next.isDetecting && previous?.isDetecting != true) {
        // Detection JUST started - begin checking for results
        print('🔍 [INSTANT_DETECTION_WIDGET] Detection JUST started, starting lazy checks');
        _startLazyChecking();
      } else if (!next.isDetecting && previous?.isDetecting == true) {
        // Detection JUST stopped - stop all polling
        print('🔍 [INSTANT_DETECTION_WIDGET] Detection JUST stopped, stopping all polling');
        _stopAllPolling();
      }
    });

    // If detection not active, show message to start detection
    if (!detectionState.isDetecting) {
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
              'Start detection to see live results',
              style: OfflineFonts.inter(
                fontSize: 11,
                color: Colors.grey.shade500,
              ),
            ),
          ],
        ),
      );
    }

    // If detection is active but backend hasn't returned results yet, show waiting state
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
              Icons.visibility,
              size: 13,
              color: Colors.blue.shade300,
            ),
            const SizedBox(width: 6),
            Text(
              'Waiting for detection results...',
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
    print('📊 [_buildDemographicsRow] Called - _demographics: $_demographics');
    
    if (_demographics == null) {
      print('⚠️ [_buildDemographicsRow] Demographics is null, returning empty');
      return const SizedBox.shrink();
    }

    // Get counts and percentages from backend demographics aggregation
    final maleCount = _demographics!['total_male'] as int? ?? 0;
    final femaleCount = _demographics!['total_female'] as int? ?? 0;
    final unknownGenderCount = _demographics!['total_unknown_gender'] as int? ?? 0;
    final youngCount = _demographics!['total_young'] as int? ?? 0;
    final adultCount = _demographics!['total_adult'] as int? ?? 0;
    final unknownAgeCount = _demographics!['total_unknown_age'] as int? ?? 0;
    
    final malePercent = _demographics!['percent_male'] as num? ?? 0;
    final femalePercent = _demographics!['percent_female'] as num? ?? 0;
    final unknownGenderPercent = _demographics!['percent_unknown_gender'] as num? ?? 0;
    final youngPercent = _demographics!['percent_young'] as num? ?? 0;
    final adultPercent = _demographics!['percent_adult'] as num? ?? 0;
    final unknownAgePercent = _demographics!['percent_unknown_age'] as num? ?? 0;
    
    print('📊 [_buildDemographicsRow] Counts - M:$maleCount F:$femaleCount U:$unknownGenderCount | Y:$youngCount A:$adultCount U:$unknownAgeCount');

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Gender row
        if (maleCount > 0 || femaleCount > 0 || unknownGenderCount > 0)
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
                if (femaleCount > 0 || unknownGenderCount > 0) const SizedBox(width: 8),
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
                if (unknownGenderCount > 0) const SizedBox(width: 8),
              ],
              // Unknown Gender
              if (unknownGenderCount > 0) ...[
                Icon(
                  Icons.help_outline,
                  size: 12,
                  color: Colors.grey.shade600,
                ),
                const SizedBox(width: 2),
                Text(
                  'Unknown: $unknownGenderCount (${unknownGenderPercent.toStringAsFixed(0)}%)',
                  style: OfflineFonts.inter(
                    fontSize: 11,
                    color: Colors.grey.shade700,
                  ),
                ),
              ],
            ],
          ),
        // Age row
        if (youngCount > 0 || adultCount > 0 || unknownAgeCount > 0) ...[
          if (maleCount > 0 || femaleCount > 0 || unknownGenderCount > 0) const SizedBox(height: 2),
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
                if (adultCount > 0 || unknownAgeCount > 0) const SizedBox(width: 8),
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
                if (unknownAgeCount > 0) const SizedBox(width: 8),
              ],
              // Unknown Age
              if (unknownAgeCount > 0) ...[
                Icon(
                  Icons.help_outline,
                  size: 12,
                  color: Colors.grey.shade600,
                ),
                const SizedBox(width: 2),
                Text(
                  'Unknown: $unknownAgeCount (${unknownAgePercent.toStringAsFixed(0)}%)',
                  style: OfflineFonts.inter(
                    fontSize: 11,
                    color: Colors.grey.shade700,
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
