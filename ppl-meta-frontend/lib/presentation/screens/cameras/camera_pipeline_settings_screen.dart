import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/models/camera.dart';
import '../../../core/models/camera_pipeline_settings.dart';
import '../../../core/services/camera_service.dart';
import '../../../core/providers/camera_providers.dart';
import '../../../core/theme/app_theme.dart';
import '../../../utils/offline_fonts.dart';
import '../../../widgets/custom_app_bar.dart';

/// Pipeline settings screen for per-camera configuration
class CameraPipelineSettingsScreen extends ConsumerStatefulWidget {
  final Camera camera;

  const CameraPipelineSettingsScreen({
    super.key,
    required this.camera,
  });

  @override
  ConsumerState<CameraPipelineSettingsScreen> createState() =>
      _CameraPipelineSettingsScreenState();
}

class _CameraPipelineSettingsScreenState
    extends ConsumerState<CameraPipelineSettingsScreen> {
  bool _isLoading = false;
  bool _isSaving = false;
  String? _error;

  // Pipeline settings state
  late bool _instantDetectionEnabled;
  late bool _recordingPipelineEnabled;
  late int _instantDetectionInterval;
  late int _segmentDuration;
  late int _storageMultiple;
  late int _trackingSessionDurationMinutes;

  // Workflow settings state
  late bool _autoFaceDetection;
  late List<String> _detectionMethods;
  late double _confidenceThreshold;
  late int _tolerancePercent;
  late bool _enablePerformanceOptimization;
  late bool _showPerformanceIndicators;
  late String _defaultPlaybackMode;
  late double _mvrQualityThreshold;

  // Show advanced settings
  bool _showAdvanced = false;
  bool _showWorkflowSettings = false;

  @override
  void initState() {
    super.initState();
    // Initialize with camera's current settings
    _instantDetectionEnabled = widget.camera.instantDetectionEnabled;
    _recordingPipelineEnabled = widget.camera.recordingPipelineEnabled;
    _instantDetectionInterval = widget.camera.instantDetectionIntervalSeconds;
    _segmentDuration = widget.camera.segmentDurationSeconds;
    _storageMultiple = widget.camera.storageMultiple;
    _trackingSessionDurationMinutes = widget.camera.trackingSessionDurationMinutes;
    
    // Initialize workflow settings
    _autoFaceDetection = widget.camera.autoFaceDetection;
    _detectionMethods = List<String>.from(widget.camera.detectionMethods);
    _confidenceThreshold = widget.camera.confidenceThreshold;
    _tolerancePercent = 20; // Default value
    _enablePerformanceOptimization = widget.camera.enablePerformanceOptimization;
    _showPerformanceIndicators = widget.camera.showPerformanceIndicators;
    _defaultPlaybackMode = widget.camera.defaultPlaybackMode;
    _mvrQualityThreshold = widget.camera.mvrQualityThreshold;
    
    // Load latest settings from server
    _loadSettings();
  }

  Future<void> _loadSettings() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final cameraService = ref.read(cameraServiceProvider);
      
      // Load pipeline settings
      final pipelineSettings = await cameraService.getPipelineSettings(widget.camera.deviceId);
      
      // Load workflow settings
      final workflowSettings = await cameraService.getWorkflowSettings(widget.camera.deviceId);

      if (mounted) {
        setState(() {
          // Pipeline settings
          _instantDetectionEnabled = pipelineSettings['instant_detection_enabled'] as bool? ?? true;
          _recordingPipelineEnabled = pipelineSettings['recording_pipeline_enabled'] as bool? ?? true;
          _instantDetectionInterval = pipelineSettings['instant_detection_interval_seconds'] as int? ?? 5;
          _segmentDuration = pipelineSettings['segment_duration_seconds'] as int? ?? 30;
          _storageMultiple = pipelineSettings['storage_multiple'] as int? ?? 1;
          _trackingSessionDurationMinutes = pipelineSettings['tracking_session_duration_minutes'] as int? ?? 0;
          
          // Workflow settings
          _autoFaceDetection = workflowSettings['auto_face_detection'] as bool? ?? false;
          _detectionMethods = (workflowSettings['detection_methods'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? ['opencv', 'dlib'];
          _confidenceThreshold = (workflowSettings['confidence_threshold'] as num?)?.toDouble() ?? 0.7;
          _tolerancePercent = workflowSettings['tolerance_percent'] as int? ?? 20;
          _enablePerformanceOptimization = workflowSettings['enable_performance_optimization'] as bool? ?? true;
          _showPerformanceIndicators = workflowSettings['show_performance_indicators'] as bool? ?? true;
          _defaultPlaybackMode = workflowSettings['default_playback_mode'] as String? ?? 'auto';
          _mvrQualityThreshold = (workflowSettings['mvr_quality_threshold'] as num?)?.toDouble() ?? 0.20;
          
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = 'Failed to load settings: $e';
          _isLoading = false;
        });
      }
    }
  }

  Future<void> _saveSettings() async {
    // Validation
    if (!_instantDetectionEnabled && !_recordingPipelineEnabled) {
      _showError('At least one pipeline must be enabled');
      return;
    }

    if (_instantDetectionInterval < 1 || _instantDetectionInterval > 60) {
      _showError('Instant detection interval must be between 1 and 60 seconds');
      return;
    }

    if (_segmentDuration < 5 || _segmentDuration > 300) {
      _showError('Segment duration must be between 5 and 300 seconds');
      return;
    }

    setState(() {
      _isSaving = true;
      _error = null;
    });

    try {
      final cameraService = ref.read(cameraServiceProvider);
      
      // Save pipeline settings
      await cameraService.updatePipelineSettings(
        widget.camera.deviceId,
        instantDetectionEnabled: _instantDetectionEnabled,
        recordingPipelineEnabled: _recordingPipelineEnabled,
        instantDetectionIntervalSeconds: _instantDetectionInterval,
        segmentDurationSeconds: _segmentDuration,
        storageMultiple: _storageMultiple,
        trackingSessionDurationMinutes: _trackingSessionDurationMinutes,
      );

      // Save workflow settings
      await cameraService.updateWorkflowSettings(
        widget.camera.deviceId,
        autoFaceDetection: _autoFaceDetection,
        detectionMethods: _detectionMethods,
        confidenceThreshold: _confidenceThreshold,
        tolerancePercent: _tolerancePercent,
        enablePerformanceOptimization: _enablePerformanceOptimization,
        showPerformanceIndicators: _showPerformanceIndicators,
        defaultPlaybackMode: _defaultPlaybackMode,
        mvrQualityThreshold: _mvrQualityThreshold,
      );

      // Refresh camera list to get updated settings
      await ref.read(cameraListProvider.notifier).loadCameras();

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Settings saved successfully'),
            backgroundColor: Colors.green,
          ),
        );
        Navigator.of(context).pop(true);
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = 'Failed to save settings: $e';
        });
        _showError('Failed to save settings: $e');
      }
    } finally {
      if (mounted) {
        setState(() {
          _isSaving = false;
        });
      }
    }
  }

  void _showError(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: Colors.red,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: const CustomAppBar(
        title: 'Pipeline Settings',
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : SingleChildScrollView(
              padding: const EdgeInsets.all(16.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Camera info card
                  _buildCameraInfoCard(),
                  const SizedBox(height: 24),

                  // Pipeline toggles
                  _buildPipelineTogglesCard(),
                  const SizedBox(height: 24),

                  // Advanced settings
                  _buildAdvancedSettingsCard(),
                  const SizedBox(height: 24),

                  // Workflow settings (Face Detection & Performance)
                  _buildWorkflowSettingsCard(),
                  const SizedBox(height: 24),

                  // Mode description
                  _buildModeDescriptionCard(),
                  const SizedBox(height: 24),

                  // Error display
                  if (_error != null) ...[
                    _buildErrorCard(),
                    const SizedBox(height: 24),
                  ],

                  // Save button
                  _buildSaveButton(),
                  const SizedBox(height: 16),

                  // Resource info
                  _buildResourceInfoCard(),
                ],
              ),
            ),
    );
  }

  Widget _buildCameraInfoCard() {
    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  widget.camera.type == CameraType.mobile
                      ? Icons.phone_android
                      : widget.camera.type == CameraType.rtsp
                          ? Icons.videocam
                          : Icons.usb,
                  color: AppColors.primary,
                  size: 32,
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        widget.camera.name,
                        style: OfflineFonts.inter(
                          fontSize: 18,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        widget.camera.deviceId,
                        style: OfflineFonts.inter(
                          fontSize: 12,
                          color: AppColors.textSecondary,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            if (widget.camera.resolution != null) ...[
              const SizedBox(height: 12),
              Text(
                'Resolution: ${widget.camera.resolution}',
                style: OfflineFonts.inter(
                  fontSize: 14,
                  color: AppColors.textSecondary,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildPipelineTogglesCard() {
    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Pipelines',
              style: OfflineFonts.inter(
                fontSize: 18,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 16),

            // Instant Detection Toggle
            _buildToggleRow(
              icon: Icons.bolt,
              iconColor: Colors.orange,
              title: 'Instant Detection',
              subtitle: 'Real-time person detection with triggers',
              value: _instantDetectionEnabled,
              onChanged: (value) {
                setState(() {
                  _instantDetectionEnabled = value;
                });
              },
            ),
            const Divider(height: 32),

            // Recording Pipeline Toggle
            _buildToggleRow(
              icon: Icons.fiber_manual_record,
              iconColor: Colors.red,
              title: 'Recording Pipeline',
              subtitle: 'Video segments with face detection',
              value: _recordingPipelineEnabled,
              onChanged: (value) {
                setState(() {
                  _recordingPipelineEnabled = value;
                });
              },
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildToggleRow({
    required IconData icon,
    required Color iconColor,
    required String title,
    required String subtitle,
    required bool value,
    required ValueChanged<bool> onChanged,
  }) {
    return Row(
      children: [
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: iconColor.withOpacity(0.1),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Icon(icon, color: iconColor, size: 24),
        ),
        const SizedBox(width: 16),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: OfflineFonts.inter(
                  fontSize: 16,
                  fontWeight: FontWeight.w500,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                subtitle,
                style: OfflineFonts.inter(
                  fontSize: 12,
                  color: AppColors.textSecondary,
                ),
              ),
            ],
          ),
        ),
        Switch(
          value: value,
          onChanged: onChanged,
          activeColor: AppColors.primary,
        ),
      ],
    );
  }

  Widget _buildAdvancedSettingsCard() {
    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Column(
        children: [
          InkWell(
            onTap: () {
              setState(() {
                _showAdvanced = !_showAdvanced;
              });
            },
            child: Padding(
              padding: const EdgeInsets.all(16.0),
              child: Row(
                children: [
                  Icon(Icons.tune, color: AppColors.primary),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      'Advanced Settings',
                      style: OfflineFonts.inter(
                        fontSize: 16,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                  Icon(
                    _showAdvanced ? Icons.expand_less : Icons.expand_more,
                    color: AppColors.textSecondary,
                  ),
                ],
              ),
            ),
          ),
          if (_showAdvanced) ...[
            const Divider(height: 1),
            Padding(
              padding: const EdgeInsets.all(16.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Instant Detection section
                  if (_instantDetectionEnabled) ...[
                    Text(
                      'Instant Detection',
                      style: OfflineFonts.inter(
                        fontSize: 16,
                        fontWeight: FontWeight.w700,
                        color: AppColors.primary,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'Settings for real-time people detection',
                      style: OfflineFonts.inter(
                        fontSize: 12,
                        color: AppColors.textSecondary,
                      ),
                    ),
                    const SizedBox(height: 16),
                    Text(
                      'Detection Interval: $_instantDetectionInterval seconds',
                      style: OfflineFonts.inter(
                        fontSize: 14,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Slider(
                      value: _instantDetectionInterval.toDouble(),
                      min: 1,
                      max: 60,
                      divisions: 59,
                      label: '$_instantDetectionInterval sec',
                      onChanged: (value) {
                        setState(() {
                          _instantDetectionInterval = value.round();
                        });
                      },
                      activeColor: AppColors.primary,
                    ),
                    Text(
                      'How often to detect people (1-60 seconds)',
                      style: OfflineFonts.inter(
                        fontSize: 12,
                        color: AppColors.textSecondary,
                      ),
                    ),
                    const SizedBox(height: 24),

                    // Storage Multiple
                    Text(
                      'Storage Multiple: $_storageMultiple',
                      style: OfflineFonts.inter(
                        fontSize: 14,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Slider(
                      value: _storageMultiple.toDouble(),
                      min: 1,
                      max: 12,
                      divisions: 11,
                      label: '$_storageMultiple',
                      onChanged: (value) {
                        setState(() {
                          _storageMultiple = value.round();
                        });
                      },
                      activeColor: AppColors.primary,
                    ),
                    Text(
                      'Persist every Nth detection cycle to MVR storage (1 = every cycle)',
                      style: OfflineFonts.inter(
                        fontSize: 12,
                        color: AppColors.textSecondary,
                      ),
                    ),
                    const SizedBox(height: 24),

                    // Tracking Session Duration
                    Text(
                      'Session Duration: ${_trackingSessionDurationMinutes == 0 ? 'Unlimited' : '$_trackingSessionDurationMinutes min'}',
                      style: OfflineFonts.inter(
                        fontSize: 14,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Slider(
                      value: _trackingSessionDurationMinutes.toDouble(),
                      min: 0,
                      max: 480,
                      divisions: 48,
                      label: _trackingSessionDurationMinutes == 0 ? 'Unlimited' : '$_trackingSessionDurationMinutes min',
                      onChanged: (value) {
                        setState(() {
                          _trackingSessionDurationMinutes = value.round();
                        });
                      },
                      activeColor: AppColors.primary,
                    ),
                    Text(
                      'Auto-rotate tracking session after N minutes (0 = no rotation)',
                      style: OfflineFonts.inter(
                        fontSize: 12,
                        color: AppColors.textSecondary,
                      ),
                    ),
                    const SizedBox(height: 24),
                  ],

                  // Recording Pipeline section
                  if (_recordingPipelineEnabled) ...[
                    Text(
                      'Recording Pipeline',
                      style: OfflineFonts.inter(
                        fontSize: 16,
                        fontWeight: FontWeight.w700,
                        color: AppColors.primary,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'Settings for video segment recording',
                      style: OfflineFonts.inter(
                        fontSize: 12,
                        color: AppColors.textSecondary,
                      ),
                    ),
                    const SizedBox(height: 16),
                    Text(
                      'Segment Duration: $_segmentDuration seconds',
                      style: OfflineFonts.inter(
                        fontSize: 14,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Slider(
                      value: _segmentDuration.toDouble(),
                      min: 5,
                      max: 300,
                      divisions: 59,
                      label: '$_segmentDuration sec',
                      onChanged: (value) {
                        setState(() {
                          _segmentDuration = value.round();
                        });
                      },
                      activeColor: AppColors.primary,
                    ),
                    Text(
                      'Length of each video segment (5-300 seconds)',
                      style: OfflineFonts.inter(
                        fontSize: 12,
                        color: AppColors.textSecondary,
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildWorkflowSettingsCard() {
    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Column(
        children: [
          InkWell(
            onTap: () {
              setState(() {
                _showWorkflowSettings = !_showWorkflowSettings;
              });
            },
            borderRadius: const BorderRadius.vertical(top: Radius.circular(12)),
            child: Padding(
              padding: const EdgeInsets.all(16.0),
              child: Row(
                children: [
                  Icon(Icons.auto_awesome, color: AppColors.primary),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Workflow Settings',
                          style: OfflineFonts.inter(
                            fontSize: 16,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          'Face detection and performance optimization',
                          style: OfflineFonts.inter(
                            fontSize: 12,
                            color: AppColors.textSecondary,
                          ),
                        ),
                      ],
                    ),
                  ),
                  Icon(
                    _showWorkflowSettings ? Icons.expand_less : Icons.expand_more,
                    color: AppColors.textSecondary,
                  ),
                ],
              ),
            ),
          ),
          if (_showWorkflowSettings) ...[
            const Divider(height: 1),
            Padding(
              padding: const EdgeInsets.all(16.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Auto Face Detection Toggle
                  SwitchListTile(
                    contentPadding: EdgeInsets.zero,
                    title: Text(
                      'Auto Face Detection',
                      style: OfflineFonts.inter(
                        fontSize: 14,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                    subtitle: Text(
                      'Automatically detect and track faces in recordings',
                      style: OfflineFonts.inter(
                        fontSize: 12,
                        color: AppColors.textSecondary,
                      ),
                    ),
                    value: _autoFaceDetection,
                    activeColor: AppColors.primary,
                    onChanged: (value) {
                      setState(() {
                        _autoFaceDetection = value;
                      });
                    },
                  ),
                  const SizedBox(height: 16),

                  // Confidence Threshold
                  Text(
                    'Confidence Threshold: ${(_confidenceThreshold * 100).toStringAsFixed(0)}%',
                    style: OfflineFonts.inter(
                      fontSize: 14,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Slider(
                    value: _confidenceThreshold,
                    min: 0.0,
                    max: 1.0,
                    divisions: 10,
                    label: '${(_confidenceThreshold * 100).toStringAsFixed(0)}%',
                    onChanged: (value) {
                      setState(() {
                        _confidenceThreshold = value;
                      });
                    },
                    activeColor: AppColors.primary,
                  ),
                  Text(
                    'Minimum confidence for face detection (lower = more faces, higher = more accurate)',
                    style: OfflineFonts.inter(
                      fontSize: 12,
                      color: AppColors.textSecondary,
                    ),
                  ),
                  const SizedBox(height: 24),

                  // Tolerance Percent (Movement Detection Sensitivity)
                  Text(
                    'Movement Detection Tolerance: $_tolerancePercent%',
                    style: OfflineFonts.inter(
                      fontSize: 14,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Slider(
                    value: _tolerancePercent.toDouble(),
                    min: 10.0,
                    max: 50.0,
                    divisions: 8,
                    label: '$_tolerancePercent%',
                    onChanged: (value) {
                      setState(() {
                        _tolerancePercent = value.toInt();
                      });
                    },
                    activeColor: AppColors.primary,
                  ),
                  Text(
                    'IoU threshold for grouping detected faces across frames into person objects (Lower = more sensitive, groups faces with less overlap)',
                    style: OfflineFonts.inter(
                      fontSize: 12,
                      color: AppColors.textSecondary,
                    ),
                  ),
                  const SizedBox(height: 24),

                  // MVR Quality Threshold
                  Text(
                    'MVR Quality Threshold: ${(_mvrQualityThreshold * 100).toStringAsFixed(0)}%',
                    style: OfflineFonts.inter(
                      fontSize: 14,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Slider(
                    value: _mvrQualityThreshold,
                    min: 0.0,
                    max: 1.0,
                    divisions: 20,
                    label: '${(_mvrQualityThreshold * 100).toStringAsFixed(0)}%',
                    onChanged: (value) {
                      setState(() {
                        _mvrQualityThreshold = value;
                      });
                    },
                    activeColor: AppColors.primary,
                  ),
                  Text(
                    'Minimum quality threshold for creating MVR people from detected faces',
                    style: OfflineFonts.inter(
                      fontSize: 12,
                      color: AppColors.textSecondary,
                    ),
                  ),
                  const SizedBox(height: 24),

                  // Detection Methods
                  Text(
                    'Detection Methods',
                    style: OfflineFonts.inter(
                      fontSize: 14,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 8),
                  ..._buildDetectionMethodCheckboxes(),
                  const SizedBox(height: 24),

                  // Performance Settings
                  SwitchListTile(
                    contentPadding: EdgeInsets.zero,
                    title: Text(
                      'Performance Optimization',
                      style: OfflineFonts.inter(
                        fontSize: 14,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                    subtitle: Text(
                      'Use Workflow 5 for CPU reduction during playback',
                      style: OfflineFonts.inter(
                        fontSize: 12,
                        color: AppColors.textSecondary,
                      ),
                    ),
                    value: _enablePerformanceOptimization,
                    activeColor: AppColors.primary,
                    onChanged: (value) {
                      setState(() {
                        _enablePerformanceOptimization = value;
                      });
                    },
                  ),
                  const SizedBox(height: 8),
                  SwitchListTile(
                    contentPadding: EdgeInsets.zero,
                    title: Text(
                      'Show Performance Indicators',
                      style: OfflineFonts.inter(
                        fontSize: 14,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                    subtitle: Text(
                      'Display CPU usage and performance metrics',
                      style: OfflineFonts.inter(
                        fontSize: 12,
                        color: AppColors.textSecondary,
                      ),
                    ),
                    value: _showPerformanceIndicators,
                    activeColor: AppColors.primary,
                    onChanged: (value) {
                      setState(() {
                        _showPerformanceIndicators = value;
                      });
                    },
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }

  List<Widget> _buildDetectionMethodCheckboxes() {
    const availableMethods = [
      {'value': 'opencv', 'label': 'OpenCV', 'description': 'Fast, good for real-time'},
      {'value': 'dlib', 'label': 'Dlib', 'description': 'High accuracy, slower'},
      {'value': 'mtcnn', 'label': 'MTCNN', 'description': 'Best accuracy, slowest'},
      {'value': 'yolo', 'label': 'YOLO', 'description': 'Balanced speed/accuracy'},
    ];

    return availableMethods.map((method) {
      final isSelected = _detectionMethods.contains(method['value']);
      return CheckboxListTile(
        contentPadding: EdgeInsets.zero,
        title: Text(
          method['label'] as String,
          style: OfflineFonts.inter(fontSize: 14),
        ),
        subtitle: Text(
          method['description'] as String,
          style: OfflineFonts.inter(
            fontSize: 12,
            color: AppColors.textSecondary,
          ),
        ),
        value: isSelected,
        activeColor: AppColors.primary,
        onChanged: (selected) {
          setState(() {
            if (selected == true) {
              _detectionMethods.add(method['value'] as String);
            } else {
              _detectionMethods.remove(method['value']);
            }
          });
        },
      );
    }).toList();
  }

  Widget _buildModeDescriptionCard() {
    final mode = _getModeDescription();
    final modeColor = _getModeColor();

    return Card(
      elevation: 2,
      color: modeColor.withOpacity(0.1),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Row(
          children: [
            Icon(Icons.info_outline, color: modeColor),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Current Mode',
                    style: OfflineFonts.inter(
                      fontSize: 12,
                      color: AppColors.textSecondary,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    mode,
                    style: OfflineFonts.inter(
                      fontSize: 16,
                      fontWeight: FontWeight.w600,
                      color: modeColor,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    _getModeExplanation(),
                    style: OfflineFonts.inter(
                      fontSize: 13,
                      color: AppColors.textSecondary,
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

  Widget _buildErrorCard() {
    return Card(
      elevation: 2,
      color: Colors.red.shade50,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Row(
          children: [
            const Icon(Icons.error_outline, color: Colors.red),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                _error!,
                style: OfflineFonts.inter(
                  fontSize: 14,
                  color: Colors.red.shade900,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSaveButton() {
    return SizedBox(
      width: double.infinity,
      height: 50,
      child: ElevatedButton(
        onPressed: _isSaving ? null : _saveSettings,
        style: ElevatedButton.styleFrom(
          backgroundColor: AppColors.primary,
          foregroundColor: Colors.white,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
          elevation: 2,
        ),
        child: _isSaving
            ? const SizedBox(
                height: 20,
                width: 20,
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                ),
              )
            : Text(
                'Save Settings',
                style: OfflineFonts.inter(
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                ),
              ),
      ),
    );
  }

  Widget _buildResourceInfoCard() {
    return Card(
      elevation: 1,
      color: Colors.blue.shade50,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.lightbulb_outline, color: Colors.blue.shade700, size: 20),
                const SizedBox(width: 8),
                Text(
                  'Resource Impact',
                  style: OfflineFonts.inter(
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                    color: Colors.blue.shade900,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            _buildResourceImpact(),
          ],
        ),
      ),
    );
  }

  Widget _buildResourceImpact() {
    if (_instantDetectionEnabled && _recordingPipelineEnabled) {
      return Text(
        'Both pipelines: Full monitoring with real-time alerts and video evidence. Highest resource usage (CPU, disk, network).',
        style: OfflineFonts.inter(
          fontSize: 12,
          color: Colors.blue.shade900,
        ),
      );
    } else if (_instantDetectionEnabled) {
      return Text(
        'Instant detection only: Real-time alerts without video storage. Saves 80-90% disk space and reduces network usage.',
        style: OfflineFonts.inter(
          fontSize: 12,
          color: Colors.blue.shade900,
        ),
      );
    } else if (_recordingPipelineEnabled) {
      return Text(
        'Recording only: Video archival without real-time processing. Reduces CPU usage by 30-40% compared to both pipelines.',
        style: OfflineFonts.inter(
          fontSize: 12,
          color: Colors.blue.shade900,
        ),
      );
    } else {
      return Text(
        'Both pipelines disabled: Camera will not function. At least one pipeline must be enabled.',
        style: OfflineFonts.inter(
          fontSize: 12,
          color: Colors.red.shade900,
          fontWeight: FontWeight.w600,
        ),
      );
    }
  }

  String _getModeDescription() {
    if (_instantDetectionEnabled && _recordingPipelineEnabled) {
      return 'Both Pipelines Active';
    } else if (_instantDetectionEnabled) {
      return 'Instant Detection Only';
    } else if (_recordingPipelineEnabled) {
      return 'Recording Only';
    } else {
      return 'Disabled';
    }
  }

  String _getModeExplanation() {
    if (_instantDetectionEnabled && _recordingPipelineEnabled) {
      return 'Real-time person detection with triggers and continuous video recording with face detection.';
    } else if (_instantDetectionEnabled) {
      return 'Real-time person detection and triggers without video storage. Privacy-conscious mode.';
    } else if (_recordingPipelineEnabled) {
      return 'Continuous video recording without real-time detection. Archival mode.';
    } else {
      return 'Both pipelines disabled. Camera will not function until at least one pipeline is enabled.';
    }
  }

  Color _getModeColor() {
    if (_instantDetectionEnabled && _recordingPipelineEnabled) {
      return Colors.green;
    } else if (_instantDetectionEnabled) {
      return Colors.orange;
    } else if (_recordingPipelineEnabled) {
      return Colors.blue;
    } else {
      return Colors.red;
    }
  }
}
