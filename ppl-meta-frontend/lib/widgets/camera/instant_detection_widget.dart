import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../utils/offline_fonts.dart';
import '../../core/theme/app_theme.dart';
import '../../core/providers/camera_providers.dart';

/// Live instant detection strip: face people + body tracks (either/both may be on).
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
  List<Map<String, dynamic>>? _bodyPersons;
  List<Map<String, dynamic>>? _objects;
  Map<String, dynamic>? _demographics;
  bool _isLoading = false;
  bool _isInstantDetectionRunning = false;
  int? _cachedIteration;
  double? _ageSeconds;
  Timer? _fastPollTimer;
  Timer? _lazyCheckTimer;
  Duration _refreshInterval = const Duration(seconds: 5);

  int get _faceCount => _personObjects?.length ?? 0;
  int get _bodyCount => _bodyPersons?.length ?? 0;
  int get _objectCount => _objects?.length ?? 0;
  bool get _hasDetections =>
      _faceCount > 0 || _bodyCount > 0 || _objectCount > 0;

  @override
  void initState() {
    super.initState();
    _loadRefreshInterval();
  }

  Future<void> _loadRefreshInterval() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final intervalSeconds = prefs.getInt('instant_detection_interval') ?? 5;
      if (!mounted) return;
      setState(() {
        _refreshInterval = Duration(seconds: intervalSeconds);
      });
    } catch (_) {}
  }

  void _clearResults() {
    _personObjects = null;
    _bodyPersons = null;
    _objects = null;
    _demographics = null;
    _isInstantDetectionRunning = false;
    _cachedIteration = null;
    _ageSeconds = null;
    _isLoading = false;
  }

  void _startLazyChecking() {
    _lazyCheckTimer?.cancel();
    _lazyCheckTimer = Timer.periodic(const Duration(seconds: 10), (_) {
      if (mounted && !_isInstantDetectionRunning) {
        _fetchInstantResults();
      }
    });
    _fetchInstantResults();
  }

  void _stopAllPolling() {
    _lazyCheckTimer?.cancel();
    _lazyCheckTimer = null;
    _fastPollTimer?.cancel();
    _fastPollTimer = null;
    if (mounted) {
      setState(_clearResults);
    }
  }

  @override
  void dispose() {
    _fastPollTimer?.cancel();
    _lazyCheckTimer?.cancel();
    super.dispose();
  }

  void _startAutoRefresh() {
    _lazyCheckTimer?.cancel();
    _fastPollTimer?.cancel();
    _fetchInstantResults();
    _fastPollTimer = Timer.periodic(_refreshInterval, (_) {
      if (mounted) {
        _fetchInstantResults();
      }
    });
  }

  void _stopAutoRefresh() {
    _fastPollTimer?.cancel();
    _fastPollTimer = null;

    if (mounted) {
      setState(_clearResults);
      final detectionState =
          ref.read(cameraInstantDetectionProvider(widget.cameraId));
      if (detectionState.isDetecting) {
        _startLazyChecking();
      }
    }
  }

  Future<void> _fetchInstantResults() async {
    if (!mounted) return;

    setState(() => _isLoading = true);

    try {
      final cameraService = ref.read(cameraServiceProvider);
      final response =
          await cameraService.getInstantDetectionResults(widget.cameraId);

      if (!mounted) return;

      if (response != null && response['success'] == true) {
        setState(() {
          _personObjects = (response['person_objects'] as List?)
              ?.map((e) => Map<String, dynamic>.from(e as Map))
              .toList();
          _bodyPersons = (response['body_persons'] as List?)
              ?.map((e) => Map<String, dynamic>.from(e as Map))
              .toList();
          // Fallback: body_count alone if body_persons omitted
          if ((_bodyPersons == null || _bodyPersons!.isEmpty) &&
              response['body_count'] is int &&
              (response['body_count'] as int) > 0) {
            _bodyPersons = List.generate(
              response['body_count'] as int,
              (_) => <String, dynamic>{},
            );
          }
          _objects = (response['objects'] as List?)
              ?.map((e) => Map<String, dynamic>.from(e as Map))
              .toList();
          if ((_objects == null || _objects!.isEmpty) &&
              response['object_count'] is int &&
              (response['object_count'] as int) > 0) {
            _objects = List.generate(
              response['object_count'] as int,
              (_) => <String, dynamic>{},
            );
          }
          _demographics = response['demographics'] as Map<String, dynamic>?;
          _isInstantDetectionRunning = true;

          final metadata = response['_metadata'] as Map<String, dynamic>?;
          if (metadata != null) {
            _cachedIteration = metadata['iteration'] as int?;
            final age = metadata['age_seconds'];
            _ageSeconds = age is num ? age.toDouble() : null;
          }

          _isLoading = false;
        });

        if (_fastPollTimer == null && mounted) {
          _startAutoRefresh();
        }
      } else {
        setState(_clearResults);
        if (_fastPollTimer != null) {
          _stopAutoRefresh();
        }
      }
    } catch (_) {
      if (mounted) {
        setState(_clearResults);
        if (_fastPollTimer != null) {
          _stopAutoRefresh();
        }
      }
    }
  }

  String _liveCountLabel() {
    final parts = <String>[];
    if (_faceCount > 0) {
      parts.add('$_faceCount ${_faceCount == 1 ? 'person' : 'people'}');
    }
    if (_bodyCount > 0) {
      parts.add('$_bodyCount ${_bodyCount == 1 ? 'body' : 'bodies'}');
    }
    if (_objectCount > 0) {
      parts.add('$_objectCount ${_objectCount == 1 ? 'object' : 'objects'}');
    }
    if (parts.isEmpty) {
      return '0 detections';
    }
    return parts.join(' · ');
  }

  Color _accentColor() {
    if (_objectCount > 0) return Colors.orange.shade800;
    if (_faceCount > 0 && _bodyCount > 0) return Colors.blue.shade700;
    if (_bodyCount > 0) return Colors.cyan.shade700;
    if (_faceCount > 0) return Colors.blue.shade700;
    return Colors.grey.shade600;
  }

  @override
  Widget build(BuildContext context) {
    final detectionState =
        ref.watch(cameraInstantDetectionProvider(widget.cameraId));

    ref.listen(cameraInstantDetectionProvider(widget.cameraId),
        (previous, next) {
      if (next.isDetecting && previous?.isDetecting != true) {
        _startLazyChecking();
      } else if (!next.isDetecting && previous?.isDetecting == true) {
        _stopAllPolling();
      }
    });

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

    final accent = _accentColor();

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: _isInstantDetectionRunning
            ? (_hasDetections
                ? (_bodyCount > 0 && _faceCount == 0
                    ? Colors.cyan.withOpacity(0.05)
                    : Colors.blue.withOpacity(0.05))
                : Colors.grey.withOpacity(0.03))
            : Colors.grey.withOpacity(0.02),
        border: Border(
          top: BorderSide(
            color: _isInstantDetectionRunning
                ? (_hasDetections
                    ? (_bodyCount > 0 && _faceCount == 0
                        ? Colors.cyan.withOpacity(0.2)
                        : Colors.blue.withOpacity(0.2))
                    : Colors.grey.withOpacity(0.2))
                : Colors.grey.withOpacity(0.1),
            width: 1,
          ),
        ),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Expanded(
            child: Row(
              children: [
                Icon(
                  _isInstantDetectionRunning
                      ? Icons.fiber_manual_record
                      : Icons.radio_button_unchecked,
                  size: 12,
                  color: _isInstantDetectionRunning
                      ? (_hasDetections ? accent : Colors.grey)
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
                        Row(
                          children: [
                            Text(
                              'Live: ',
                              style: OfflineFonts.inter(
                                fontSize: 11,
                                color: AppColors.textSecondary,
                              ),
                            ),
                            Flexible(
                              child: Text(
                                _liveCountLabel(),
                                style: OfflineFonts.inter(
                                  fontSize: 12,
                                  fontWeight: FontWeight.w600,
                                  color: accent,
                                ),
                                overflow: TextOverflow.ellipsis,
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
                        if (_faceCount > 0 && _demographics != null)
                          _buildDemographicsRow(),
                        if (_bodyCount > 0) _buildBodySummaryRow(),
                        if (_objectCount > 0) _buildObjectSummaryRow(),
                      ],
                    ),
                  ),
              ],
            ),
          ),
          if (_cachedIteration != null)
            Tooltip(
              message:
                  'Iteration #$_cachedIteration\nFaces: $_faceCount · Bodies: $_bodyCount · Objects: $_objectCount',
              child: Icon(
                Icons.autorenew,
                size: 14,
                color: _objectCount > 0
                    ? Colors.orange.shade400
                    : _bodyCount > 0 && _faceCount == 0
                        ? Colors.cyan.shade400
                        : Colors.blue.shade400,
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildObjectSummaryRow() {
    final objects = _objects;
    if (objects == null || objects.isEmpty) {
      return const SizedBox.shrink();
    }
    final labels = <String>[];
    for (final o in objects) {
      final label = (o['class_label'] as String?)?.trim();
      if (label != null && label.isNotEmpty) {
        labels.add(label);
      }
    }
    final summary = labels.isEmpty
        ? '$_objectCount object pin(s)'
        : labels.take(4).join(', ') + (labels.length > 4 ? '…' : '');
    return Padding(
      padding: const EdgeInsets.only(top: 4),
      child: Row(
        children: [
          Icon(Icons.luggage, size: 12, color: Colors.orange.shade800),
          const SizedBox(width: 4),
          Flexible(
            child: Text(
              summary,
              style: OfflineFonts.inter(
                fontSize: 10,
                color: Colors.orange.shade800,
              ),
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildBodySummaryRow() {
    final persons = _bodyPersons;
    if (persons == null || persons.isEmpty) {
      return const SizedBox.shrink();
    }

    var upright = 0;
    var horizontal = 0;
    var uncertain = 0;
    for (final p in persons) {
      final posture = (p['posture'] as String?)?.toLowerCase() ?? 'uncertain';
      if (posture == 'upright') {
        upright++;
      } else if (posture == 'horizontal') {
        horizontal++;
      } else {
        uncertain++;
      }
    }

    final chips = <Widget>[];
    void addChip(IconData icon, String label, Color color) {
      if (chips.isNotEmpty) {
        chips.add(const SizedBox(width: 8));
      }
      chips.addAll([
        Icon(icon, size: 12, color: color),
        const SizedBox(width: 2),
        Text(
          label,
          style: OfflineFonts.inter(fontSize: 11, color: color),
        ),
      ]);
    }

    if (upright > 0) {
      addChip(Icons.accessibility_new, 'Upright: $upright', Colors.cyan.shade700);
    }
    if (horizontal > 0) {
      addChip(Icons.airline_seat_flat, 'Horizontal: $horizontal',
          Colors.orange.shade700);
    }
    if (uncertain > 0 && (upright > 0 || horizontal > 0)) {
      addChip(Icons.help_outline, 'Uncertain: $uncertain', Colors.grey.shade700);
    } else if (uncertain > 0 && upright == 0 && horizontal == 0) {
      addChip(Icons.accessibility, '$_bodyCount tracked', Colors.cyan.shade700);
    }

    if (chips.isEmpty) {
      return const SizedBox.shrink();
    }

    return Padding(
      padding: const EdgeInsets.only(top: 2),
      child: Row(children: chips),
    );
  }

  Widget _buildDemographicsRow() {
    if (_demographics == null) {
      return const SizedBox.shrink();
    }

    final maleCount = _demographics!['total_male'] as int? ?? 0;
    final femaleCount = _demographics!['total_female'] as int? ?? 0;
    final unknownGenderCount =
        _demographics!['total_unknown_gender'] as int? ?? 0;
    final youngCount = _demographics!['total_young'] as int? ?? 0;
    final adultCount = _demographics!['total_adult'] as int? ?? 0;
    final unknownAgeCount = _demographics!['total_unknown_age'] as int? ?? 0;

    final malePercent = _demographics!['percent_male'] as num? ?? 0;
    final femalePercent = _demographics!['percent_female'] as num? ?? 0;
    final unknownGenderPercent =
        _demographics!['percent_unknown_gender'] as num? ?? 0;
    final youngPercent = _demographics!['percent_young'] as num? ?? 0;
    final adultPercent = _demographics!['percent_adult'] as num? ?? 0;
    final unknownAgePercent = _demographics!['percent_unknown_age'] as num? ?? 0;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (maleCount > 0 || femaleCount > 0 || unknownGenderCount > 0)
          Row(
            children: [
              if (maleCount > 0) ...[
                Icon(Icons.male, size: 12, color: Colors.blue.shade600),
                const SizedBox(width: 2),
                Text(
                  'Male: $maleCount (${malePercent.toStringAsFixed(0)}%)',
                  style: OfflineFonts.inter(
                    fontSize: 11,
                    color: Colors.blue.shade700,
                  ),
                ),
                if (femaleCount > 0 || unknownGenderCount > 0)
                  const SizedBox(width: 8),
              ],
              if (femaleCount > 0) ...[
                Icon(Icons.female, size: 12, color: Colors.pink.shade600),
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
              if (unknownGenderCount > 0) ...[
                Icon(Icons.help_outline, size: 12, color: Colors.grey.shade600),
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
        if (youngCount > 0 || adultCount > 0 || unknownAgeCount > 0) ...[
          if (maleCount > 0 || femaleCount > 0 || unknownGenderCount > 0)
            const SizedBox(height: 2),
          Row(
            children: [
              if (youngCount > 0) ...[
                Icon(Icons.child_care, size: 12, color: Colors.orange.shade600),
                const SizedBox(width: 2),
                Text(
                  'Young: $youngCount (${youngPercent.toStringAsFixed(0)}%)',
                  style: OfflineFonts.inter(
                    fontSize: 11,
                    color: Colors.orange.shade700,
                  ),
                ),
                if (adultCount > 0 || unknownAgeCount > 0)
                  const SizedBox(width: 8),
              ],
              if (adultCount > 0) ...[
                Icon(Icons.person, size: 12, color: Colors.green.shade600),
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
              if (unknownAgeCount > 0) ...[
                Icon(Icons.help_outline, size: 12, color: Colors.grey.shade600),
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
