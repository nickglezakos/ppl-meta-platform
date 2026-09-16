import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/models/camera.dart';
import '../../../core/models/camera_pipeline_settings.dart';
import '../../../core/services/camera_service.dart';
import '../../../core/services/models_catalog_client.dart';
import '../../../core/providers/camera_providers.dart';
import '../../../core/theme/app_theme.dart';
import '../../../utils/offline_fonts.dart';
import '../../../widgets/custom_app_bar.dart';
import '../../widgets/camera/edit_camera_name_dialog.dart';
import '../../widgets/camera/rtsp_camera_dialog.dart';

/// Pipeline settings screen for per-camera configuration
class CameraPipelineSettingsScreen extends ConsumerStatefulWidget {
  final Camera camera;

  /// Whether to render the screen's own app bar. Set to [false] when the
  /// settings form is embedded inline (e.g. inside a master/detail content
  /// pane) where the surrounding layout already provides the header.
  final bool showAppBar;

  const CameraPipelineSettingsScreen({
    super.key,
    required this.camera,
    this.showAppBar = true,
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
  late bool _autoBodyDetection;
  late List<String> _detectionMethods;
  late double _confidenceThreshold;
  late int _tolerancePercent;
  late bool _enablePerformanceOptimization;
  late bool _showPerformanceIndicators;
  late String _defaultPlaybackMode;
  late double _mvrQualityThreshold;
  late bool _mvrPeriodicSchedulerEnabled;
  late double _mvrPeriodicSchedulerThreshold;
  late int _mvrPeriodicSchedulerFrequencySeconds;
  _PathPipelineDraft _faceInstant = _PathPipelineDraft.faceDefaults();
  _PathPipelineDraft _faceBulk = _PathPipelineDraft.faceDefaults(twoStage: true);
  _PathPipelineDraft _bodyInstant = _PathPipelineDraft.bodyDefaults();
  _PathPipelineDraft _bodyBulk = _PathPipelineDraft.bodyDefaults(twoStage: true);
  List<Map<String, dynamic>> _faceModels = const [];
  List<Map<String, dynamic>> _bodyModels = const [];
  List<Map<String, dynamic>> _faceRecipes = const [];
  List<Map<String, dynamic>> _bodyRecipes = const [];

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
    _autoBodyDetection = false;
    _detectionMethods = List<String>.from(widget.camera.detectionMethods);
    _confidenceThreshold = widget.camera.confidenceThreshold;
    _tolerancePercent = 20; // Default value
    _enablePerformanceOptimization = widget.camera.enablePerformanceOptimization;
    _showPerformanceIndicators = widget.camera.showPerformanceIndicators;
    _defaultPlaybackMode = widget.camera.defaultPlaybackMode;
    _mvrQualityThreshold = widget.camera.mvrQualityThreshold;
    _mvrPeriodicSchedulerEnabled = widget.camera.mvrPeriodicSchedulerEnabled;
    _mvrPeriodicSchedulerThreshold = widget.camera.mvrPeriodicSchedulerThreshold;
    _mvrPeriodicSchedulerFrequencySeconds = widget.camera.mvrPeriodicSchedulerFrequencySeconds;
    
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
      List<Map<String, dynamic>> faceModels = const [];
      List<Map<String, dynamic>> bodyModels = const [];
      List<Map<String, dynamic>> faceRecipes = const [];
      List<Map<String, dynamic>> bodyRecipes = const [];
      try {
        final client = ref.read(modelsCatalogClientProvider);
        final catalog = await client.listModels();
        final allModels = catalog
            .map((item) => Map<String, dynamic>.from(item as Map))
            .toList();
        faceModels = allModels
            .where((model) => model['capability'] == 'face_detection')
            .toList();
        bodyModels = allModels
            .where((model) => model['capability'] == 'body_detection')
            .toList();
        faceRecipes = (await client.listRecipes(capability: 'face_detection'))
            .map((item) => Map<String, dynamic>.from(item as Map))
            .toList();
        bodyRecipes = (await client.listRecipes(capability: 'body_detection'))
            .map((item) => Map<String, dynamic>.from(item as Map))
            .toList();
      } catch (_) {}

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
          _autoBodyDetection = workflowSettings['auto_body_detection'] as bool? ?? false;
          _detectionMethods = (workflowSettings['detection_methods'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? ['opencv', 'dlib'];
          _confidenceThreshold = (workflowSettings['confidence_threshold'] as num?)?.toDouble() ?? 0.7;
          _tolerancePercent = workflowSettings['tolerance_percent'] as int? ?? 20;
          _enablePerformanceOptimization = workflowSettings['enable_performance_optimization'] as bool? ?? true;
          _showPerformanceIndicators = workflowSettings['show_performance_indicators'] as bool? ?? true;
          _defaultPlaybackMode = workflowSettings['default_playback_mode'] as String? ?? 'auto';
          _mvrQualityThreshold = (workflowSettings['mvr_quality_threshold'] as num?)?.toDouble() ?? 0.20;
          _mvrPeriodicSchedulerEnabled = workflowSettings['mvr_periodic_scheduler_enabled'] as bool? ?? false;
          _mvrPeriodicSchedulerThreshold = (workflowSettings['mvr_periodic_scheduler_threshold'] as num?)?.toDouble() ?? 0.70;
          _mvrPeriodicSchedulerFrequencySeconds = workflowSettings['mvr_periodic_scheduler_frequency_seconds'] as int? ?? 300;
          _faceModels = faceModels;
          _bodyModels = bodyModels;
          _faceRecipes = faceRecipes;
          _bodyRecipes = bodyRecipes;
          _faceInstant = _PathPipelineDraft.fromSaved(
            workflowSettings['pipeline_face_instant'],
            fallbackRecipeId: workflowSettings['assigned_recipe_id_face_instant']?.toString(),
            legacyModelId: _nullableModelId(
              workflowSettings['assigned_model_id_instant'] ??
                  workflowSettings['assigned_model_id'],
            ),
            defaults: _PathPipelineDraft.faceDefaults(),
            recipes: faceRecipes,
          );
          _faceBulk = _PathPipelineDraft.fromSaved(
            workflowSettings['pipeline_face_bulk'],
            fallbackRecipeId: workflowSettings['assigned_recipe_id_face_bulk']?.toString(),
            legacyModelId: _nullableModelId(
              workflowSettings['assigned_model_id_bulk'] ??
                  workflowSettings['assigned_model_id'],
            ),
            defaults: _PathPipelineDraft.faceDefaults(twoStage: true),
            recipes: faceRecipes,
          );
          _bodyInstant = _PathPipelineDraft.fromSaved(
            workflowSettings['pipeline_body_instant'],
            fallbackRecipeId: workflowSettings['assigned_recipe_id_body_instant']?.toString(),
            defaults: _PathPipelineDraft.bodyDefaults(),
            recipes: bodyRecipes,
          );
          _bodyBulk = _PathPipelineDraft.fromSaved(
            workflowSettings['pipeline_body_bulk'],
            fallbackRecipeId: workflowSettings['assigned_recipe_id_body_bulk']?.toString(),
            defaults: _PathPipelineDraft.bodyDefaults(twoStage: true),
            recipes: bodyRecipes,
          );
          
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

    if (_mvrPeriodicSchedulerFrequencySeconds < 30 ||
        _mvrPeriodicSchedulerFrequencySeconds > 86400) {
      _showError('Periodic scheduler frequency must be between 30 and 86400 seconds');
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
        autoBodyDetection: _autoBodyDetection,
        detectionMethods: _detectionMethods,
        confidenceThreshold: _confidenceThreshold,
        tolerancePercent: _tolerancePercent,
        enablePerformanceOptimization: _enablePerformanceOptimization,
        showPerformanceIndicators: _showPerformanceIndicators,
        defaultPlaybackMode: _defaultPlaybackMode,
        mvrQualityThreshold: _mvrQualityThreshold,
        mvrPeriodicSchedulerEnabled: _mvrPeriodicSchedulerEnabled,
        mvrPeriodicSchedulerThreshold: _mvrPeriodicSchedulerThreshold,
        mvrPeriodicSchedulerFrequencySeconds: _mvrPeriodicSchedulerFrequencySeconds,
        detectionPipelines: {
          'face_detection': {
            'instant': _faceInstant.toJson(),
            'bulk': _faceBulk.toJson(),
          },
          'body_detection': {
            'instant': _bodyInstant.toJson(),
            'bulk': _bodyBulk.toJson(),
          },
        },
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
        if (widget.showAppBar && Navigator.of(context).canPop()) {
          Navigator.of(context).pop(true);
        }
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

  String? _nullableModelId(dynamic value) {
    final text = value?.toString();
    if (text == null || text.isEmpty) return null;
    return text;
  }

  String _readyVersionFor(List<Map<String, dynamic>> models, String? modelId) {
    if (modelId == null) return '1.0.0';
    final match = models.where((model) => model['model_id'] == modelId);
    if (match.isEmpty) return '1.0.0';
    final versions = List<dynamic>.from(match.first['versions'] as List? ?? const []);
    for (final raw in versions) {
      final version = Map<String, dynamic>.from(raw as Map);
      if (version['status']?.toString() == 'ready') {
        return version['version']?.toString() ?? '1.0.0';
      }
    }
    if (versions.isEmpty) return '1.0.0';
    return Map<String, dynamic>.from(versions.first as Map)['version']?.toString() ??
        '1.0.0';
  }

  Widget _buildPathPipelineEditor({
    required String title,
    required _PathPipelineDraft draft,
    required List<Map<String, dynamic>> models,
    required List<Map<String, dynamic>> recipes,
    required ValueChanged<_PathPipelineDraft> onChanged,
  }) {
    final readyModels = models.where((model) {
      final versions = List<dynamic>.from(model['versions'] as List? ?? const []);
      return versions.any((raw) {
        final version = Map<String, dynamic>.from(raw as Map);
        return version['status']?.toString() == 'ready' ||
            version['status']?.toString() == 'builtin' ||
            model['origin']?.toString() == 'builtin';
      });
    }).toList();
    final modelIds = readyModels
        .map((model) => model['model_id']?.toString())
        .whereType<String>()
        .toList();
    final recipeIds = recipes
        .map((recipe) => recipe['recipe_id']?.toString())
        .whereType<String>()
        .toList();

    return Card(
      margin: EdgeInsets.zero,
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: OfflineFonts.inter(fontSize: 13, fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 8),
            DropdownButtonFormField<String>(
              value: draft.seedRecipeId != null && recipeIds.contains(draft.seedRecipeId)
                  ? draft.seedRecipeId
                  : '',
              decoration: const InputDecoration(
                labelText: 'Use seeded recipe (optional)',
                isDense: true,
              ),
              items: [
                const DropdownMenuItem(value: '', child: Text('Custom composition')),
                ...recipes.map(
                  (recipe) => DropdownMenuItem(
                    value: recipe['recipe_id']?.toString(),
                    child: Text(
                      '${recipe['display_name']} (${recipe['kind']})',
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ),
              ],
              onChanged: (value) {
                if (value == null || value.isEmpty) {
                  onChanged(draft.copyWith(clearSeed: true));
                  return;
                }
                final match = recipes.firstWhere(
                  (recipe) => recipe['recipe_id'] == value,
                  orElse: () => <String, dynamic>{},
                );
                onChanged(draft.applyRecipe(match));
              },
            ),
            const SizedBox(height: 8),
            DropdownButtonFormField<String>(
              value: draft.kind,
              decoration: const InputDecoration(labelText: 'Kind', isDense: true),
              items: const [
                DropdownMenuItem(value: 'single', child: Text('Single stage')),
                DropdownMenuItem(value: 'two_stage', child: Text('Two-stage')),
              ],
              onChanged: draft.seedRecipeId != null
                  ? null
                  : (value) {
                      if (value == null) return;
                      onChanged(draft.copyWith(kind: value, clearSeed: true));
                    },
            ),
            const SizedBox(height: 8),
            if (draft.kind == 'single')
              DropdownButtonFormField<String>(
                value: draft.modelId != null && modelIds.contains(draft.modelId)
                    ? draft.modelId
                    : (modelIds.isEmpty ? null : modelIds.first),
                decoration: const InputDecoration(labelText: 'Model', isDense: true),
                items: readyModels
                    .map(
                      (model) => DropdownMenuItem(
                        value: model['model_id']?.toString(),
                        child: Text(
                          model['display_name']?.toString() ??
                              model['model_id'].toString(),
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                    )
                    .toList(),
                onChanged: draft.seedRecipeId != null
                    ? null
                    : (value) {
                        onChanged(
                          draft.copyWith(
                            modelId: value,
                            version: _readyVersionFor(readyModels, value),
                            clearSeed: true,
                          ),
                        );
                      },
              )
            else ...[
              DropdownButtonFormField<String>(
                value: draft.proposalModelId != null &&
                        modelIds.contains(draft.proposalModelId)
                    ? draft.proposalModelId
                    : (modelIds.isEmpty ? null : modelIds.first),
                decoration: const InputDecoration(
                  labelText: 'Proposal (light)',
                  isDense: true,
                ),
                items: readyModels
                    .map(
                      (model) => DropdownMenuItem(
                        value: model['model_id']?.toString(),
                        child: Text(
                          model['display_name']?.toString() ??
                              model['model_id'].toString(),
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                    )
                    .toList(),
                onChanged: draft.seedRecipeId != null
                    ? null
                    : (value) {
                        onChanged(
                          draft.copyWith(
                            proposalModelId: value,
                            proposalVersion: _readyVersionFor(readyModels, value),
                            clearSeed: true,
                          ),
                        );
                      },
              ),
              const SizedBox(height: 8),
              DropdownButtonFormField<String>(
                value: draft.refineModelId != null &&
                        modelIds.contains(draft.refineModelId)
                    ? draft.refineModelId
                    : (modelIds.length > 1
                        ? modelIds[1]
                        : (modelIds.isEmpty ? null : modelIds.first)),
                decoration: const InputDecoration(
                  labelText: 'Refine (quality)',
                  isDense: true,
                ),
                items: readyModels
                    .map(
                      (model) => DropdownMenuItem(
                        value: model['model_id']?.toString(),
                        child: Text(
                          model['display_name']?.toString() ??
                              model['model_id'].toString(),
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                    )
                    .toList(),
                onChanged: draft.seedRecipeId != null
                    ? null
                    : (value) {
                        onChanged(
                          draft.copyWith(
                            refineModelId: value,
                            refineVersion: _readyVersionFor(readyModels, value),
                            clearSeed: true,
                          ),
                        );
                      },
              ),
            ],
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: widget.showAppBar
          ? const CustomAppBar(
              title: 'Pipeline Settings',
            )
          : null,
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

                  // Rename camera
                  _buildRenameCard(),
                  const SizedBox(height: 24),

                  // RTSP connection editing (RTSP cameras only)
                  if (widget.camera.type == CameraType.rtsp) ...[
                    _buildRTSPCard(),
                    const SizedBox(height: 24),
                  ],

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

  Widget _buildRenameCard() {
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
                Icon(Icons.edit, color: AppColors.primary, size: 20),
                const SizedBox(width: 8),
                Text(
                  'Rename Camera',
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              "Update this camera's display name. Names must be unique.",
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: AppColors.textSecondary,
              ),
            ),
            const SizedBox(height: 12),
            OutlinedButton.icon(
              onPressed: _openRenameDialog,
              icon: const Icon(Icons.drive_file_rename_outline),
              label: const Text('Rename camera'),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _openRenameDialog() async {
    final result = await showDialog<bool>(
      context: context,
      builder: (context) => EditCameraNameDialog(camera: widget.camera),
    );
    if (result == true && mounted) {
      // Reload so the list and this form pick up the new name.
      await ref.read(cameraListProvider.notifier).loadCameras();
    }
  }

  Widget _buildRTSPCard() {
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
                Icon(Icons.videocam, color: AppColors.primary, size: 20),
                const SizedBox(width: 8),
                Text(
                  'RTSP Connection',
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              'Configure the RTSP URL and authentication for this camera.',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: AppColors.textSecondary,
              ),
            ),
            const SizedBox(height: 12),
            OutlinedButton.icon(
              onPressed: _openRTSPDialog,
              icon: const Icon(Icons.settings_ethernet),
              label: const Text('Edit RTSP connection'),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _openRTSPDialog() async {
    final result = await showDialog<bool>(
      context: context,
      builder: (context) => RTSPCameraDialog(
        camera: widget.camera,
        isEditing: true,
      ),
    );
    if (result == true && mounted) {
      await ref.read(cameraListProvider.notifier).loadCameras();
    }
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
                      'How often to start a new detection cycle (1–60 seconds). '
                      'Each cycle samples 3 frames; if the previous Celery job is '
                      'still running, the next submit is skipped until this interval elapses. '
                      'Does not change Vision time per frame. Higher values reduce load '
                      '(recommended 15–30s for high-res RTSP on Lima).',
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
                  Text(
                    'Detection pipelines',
                    style: OfflineFonts.inter(
                      fontSize: 14,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  Text(
                    'Choose Face and Body pipelines for Instant and Bulk. '
                    'Full catalog lives under Models.',
                    style: OfflineFonts.inter(
                      fontSize: 12,
                      color: AppColors.textSecondary,
                    ),
                  ),
                  SwitchListTile(
                    contentPadding: EdgeInsets.zero,
                    title: Text(
                      'Enable Face detection',
                      style: OfflineFonts.inter(
                        fontSize: 14,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                    subtitle: Text(
                      'Assign face recipes for this camera',
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
                  if (_autoFaceDetection) ...[
                    _buildPathPipelineEditor(
                      title: 'Face · Instant',
                      draft: _faceInstant,
                      models: _faceModels,
                      recipes: _faceRecipes,
                      onChanged: (next) => setState(() => _faceInstant = next),
                    ),
                    const SizedBox(height: 8),
                    _buildPathPipelineEditor(
                      title: 'Face · Bulk / recording',
                      draft: _faceBulk,
                      models: _faceModels,
                      recipes: _faceRecipes,
                      onChanged: (next) => setState(() => _faceBulk = next),
                    ),
                  ],
                  SwitchListTile(
                    contentPadding: EdgeInsets.zero,
                    title: Text(
                      'Enable Body detection',
                      style: OfflineFonts.inter(
                        fontSize: 14,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                    subtitle: Text(
                      'Runs YOLO-pose body detection for instant and recordings; creates MVR People Body with posture/height',
                      style: OfflineFonts.inter(
                        fontSize: 12,
                        color: AppColors.textSecondary,
                      ),
                    ),
                    value: _autoBodyDetection,
                    activeColor: AppColors.primary,
                    onChanged: (value) {
                      setState(() {
                        _autoBodyDetection = value;
                      });
                    },
                  ),
                  if (_autoBodyDetection) ...[
                    _buildPathPipelineEditor(
                      title: 'Body · Instant',
                      draft: _bodyInstant,
                      models: _bodyModels,
                      recipes: _bodyRecipes,
                      onChanged: (next) => setState(() => _bodyInstant = next),
                    ),
                    const SizedBox(height: 8),
                    _buildPathPipelineEditor(
                      title: 'Body · Bulk / recording',
                      draft: _bodyBulk,
                      models: _bodyModels,
                      recipes: _bodyRecipes,
                      onChanged: (next) => setState(() => _bodyBulk = next),
                    ),
                  ],
                  Padding(
                    padding: const EdgeInsets.only(top: 4, bottom: 8),
                    child: Text(
                      'More detections coming soon (e.g. plate)',
                      style: OfflineFonts.inter(
                        fontSize: 12,
                        color: AppColors.textSecondary,
                      ).copyWith(fontStyle: FontStyle.italic),
                    ),
                  ),
                  const SizedBox(height: 8),

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

                  // Periodic MVR scheduler controls
                  SwitchListTile(
                    contentPadding: EdgeInsets.zero,
                    title: Text(
                      'Periodic MVR Merge Scheduler',
                      style: OfflineFonts.inter(
                        fontSize: 14,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                    subtitle: Text(
                      'Run scheduled MVR merge cycles for this camera',
                      style: OfflineFonts.inter(
                        fontSize: 12,
                        color: AppColors.textSecondary,
                      ),
                    ),
                    value: _mvrPeriodicSchedulerEnabled,
                    activeColor: AppColors.primary,
                    onChanged: (value) {
                      setState(() {
                        _mvrPeriodicSchedulerEnabled = value;
                      });
                    },
                  ),
                  const SizedBox(height: 12),
                  Text(
                    'Scheduler Merge Threshold: ${(_mvrPeriodicSchedulerThreshold * 100).toStringAsFixed(0)}%',
                    style: OfflineFonts.inter(
                      fontSize: 14,
                      fontWeight: FontWeight.w500,
                      color: _mvrPeriodicSchedulerEnabled
                          ? AppColors.textPrimary
                          : AppColors.textSecondary,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Slider(
                    value: _mvrPeriodicSchedulerThreshold,
                    min: 0.30,
                    max: 0.95,
                    divisions: 13,
                    label:
                        '${(_mvrPeriodicSchedulerThreshold * 100).toStringAsFixed(0)}%',
                    onChanged: _mvrPeriodicSchedulerEnabled
                        ? (value) {
                            setState(() {
                              _mvrPeriodicSchedulerThreshold = value;
                            });
                          }
                        : null,
                    activeColor: AppColors.primary,
                  ),
                  Text(
                    'Similarity threshold used by periodic merge runs',
                    style: OfflineFonts.inter(
                      fontSize: 12,
                      color: AppColors.textSecondary,
                    ),
                  ),
                  const SizedBox(height: 16),
                  Text(
                    'Scheduler Frequency: ${_mvrPeriodicSchedulerFrequencySeconds}s',
                    style: OfflineFonts.inter(
                      fontSize: 14,
                      fontWeight: FontWeight.w500,
                      color: _mvrPeriodicSchedulerEnabled
                          ? AppColors.textPrimary
                          : AppColors.textSecondary,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Slider(
                    value: _mvrPeriodicSchedulerFrequencySeconds.toDouble(),
                    min: 30,
                    max: 3600,
                    divisions: 119,
                    label: '${_mvrPeriodicSchedulerFrequencySeconds}s',
                    onChanged: _mvrPeriodicSchedulerEnabled
                        ? (value) {
                            setState(() {
                              _mvrPeriodicSchedulerFrequencySeconds =
                                  (value / 30).round() * 30;
                            });
                          }
                        : null,
                    activeColor: AppColors.primary,
                  ),
                  Text(
                    'How often the periodic scheduler runs for this camera',
                    style: OfflineFonts.inter(
                      fontSize: 12,
                      color: AppColors.textSecondary,
                    ),
                  ),
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

class _PathPipelineDraft {
  _PathPipelineDraft({
    required this.kind,
    this.seedRecipeId,
    this.modelId,
    this.version = '1.0.0',
    this.proposalModelId,
    this.proposalVersion = '1.0.0',
    this.refineModelId,
    this.refineVersion = '1.0.0',
  });

  final String kind;
  final String? seedRecipeId;
  final String? modelId;
  final String version;
  final String? proposalModelId;
  final String proposalVersion;
  final String? refineModelId;
  final String refineVersion;

  factory _PathPipelineDraft.faceDefaults({bool twoStage = false}) {
    if (twoStage) {
      return _PathPipelineDraft(
        kind: 'two_stage',
        seedRecipeId: 'face-two-stage-haar-dlib',
        proposalModelId: 'face-haar-builtin',
        refineModelId: 'face-dlib-builtin',
      );
    }
    return _PathPipelineDraft(
      kind: 'single',
      seedRecipeId: 'face-haar-only',
      modelId: 'face-haar-builtin',
    );
  }

  factory _PathPipelineDraft.bodyDefaults({bool twoStage = false}) {
    if (twoStage) {
      return _PathPipelineDraft(
        kind: 'two_stage',
        seedRecipeId: 'body-two-stage-placeholder',
        proposalModelId: 'body-proposal-placeholder',
        refineModelId: 'body-refine-placeholder',
      );
    }
    return _PathPipelineDraft(
      kind: 'single',
      seedRecipeId: 'body-yolo-pose-only',
      modelId: 'body-yolo-pose-os',
    );
  }

  factory _PathPipelineDraft.fromSaved(
    dynamic raw, {
    String? fallbackRecipeId,
    String? legacyModelId,
    required _PathPipelineDraft defaults,
    List<Map<String, dynamic>> recipes = const [],
  }) {
    if (raw is Map) {
      final map = Map<String, dynamic>.from(raw);
      return _PathPipelineDraft(
        kind: map['kind']?.toString() ?? defaults.kind,
        seedRecipeId: map['recipe_id']?.toString(),
        modelId: map['model_id']?.toString() ?? defaults.modelId,
        version: map['version']?.toString() ?? '1.0.0',
        proposalModelId:
            map['proposal_model_id']?.toString() ?? defaults.proposalModelId,
        proposalVersion: map['proposal_version']?.toString() ?? '1.0.0',
        refineModelId:
            map['refine_model_id']?.toString() ?? defaults.refineModelId,
        refineVersion: map['refine_version']?.toString() ?? '1.0.0',
      );
    }
    if (fallbackRecipeId != null && fallbackRecipeId.isNotEmpty) {
      final match = recipes.where((recipe) => recipe['recipe_id'] == fallbackRecipeId);
      if (match.isNotEmpty) {
        return defaults.applyRecipe(match.first);
      }
      return defaults.copyWith(seedRecipeId: fallbackRecipeId);
    }
    if (legacyModelId != null && legacyModelId.isNotEmpty) {
      return _PathPipelineDraft(
        kind: 'single',
        modelId: legacyModelId,
        version: '1.0.0',
      );
    }
    return defaults;
  }

  _PathPipelineDraft copyWith({
    String? kind,
    String? seedRecipeId,
    String? modelId,
    String? version,
    String? proposalModelId,
    String? proposalVersion,
    String? refineModelId,
    String? refineVersion,
    bool clearSeed = false,
  }) {
    return _PathPipelineDraft(
      kind: kind ?? this.kind,
      seedRecipeId: clearSeed ? null : (seedRecipeId ?? this.seedRecipeId),
      modelId: modelId ?? this.modelId,
      version: version ?? this.version,
      proposalModelId: proposalModelId ?? this.proposalModelId,
      proposalVersion: proposalVersion ?? this.proposalVersion,
      refineModelId: refineModelId ?? this.refineModelId,
      refineVersion: refineVersion ?? this.refineVersion,
    );
  }

  _PathPipelineDraft applyRecipe(Map<String, dynamic> recipe) {
    final kind = recipe['kind']?.toString() ?? 'single';
    final stages = List<dynamic>.from(recipe['stages'] as List? ?? const []);
    String? modelId;
    String? proposal;
    String? refine;
    String version = '1.0.0';
    String proposalVersion = '1.0.0';
    String refineVersion = '1.0.0';
    for (final raw in stages) {
      final stage = Map<String, dynamic>.from(raw as Map);
      final role = stage['role']?.toString();
      if (role == 'single') {
        modelId = stage['model_id']?.toString();
        version = stage['version']?.toString() ?? '1.0.0';
      } else if (role == 'proposal') {
        proposal = stage['model_id']?.toString();
        proposalVersion = stage['version']?.toString() ?? '1.0.0';
      } else if (role == 'refine') {
        refine = stage['model_id']?.toString();
        refineVersion = stage['version']?.toString() ?? '1.0.0';
      }
    }
    return _PathPipelineDraft(
      kind: kind,
      seedRecipeId: recipe['recipe_id']?.toString(),
      modelId: modelId ?? proposal,
      version: version,
      proposalModelId: proposal ?? modelId,
      proposalVersion: proposalVersion,
      refineModelId: refine,
      refineVersion: refineVersion,
    );
  }

  Map<String, dynamic> toJson() {
    if (seedRecipeId != null && seedRecipeId!.isNotEmpty) {
      return {
        'kind': kind,
        'recipe_id': seedRecipeId,
        'model_id': modelId,
        'version': version,
        'proposal_model_id': proposalModelId,
        'proposal_version': proposalVersion,
        'refine_model_id': refineModelId,
        'refine_version': refineVersion,
      };
    }
    return {
      'kind': kind,
      'model_id': modelId,
      'version': version,
      'proposal_model_id': proposalModelId,
      'proposal_version': proposalVersion,
      'refine_model_id': refineModelId,
      'refine_version': refineVersion,
    };
  }
}
