import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/theme/app_theme.dart';
import '../../../models/face_detection_models.dart';
import '../../../providers/workflow_providers.dart';

/// Settings model for workflow configuration
class WorkflowSettings {
  final double confidenceThreshold;
  final double mvrQualityThreshold;
  final List<String> detectionMethods;
  final bool enableAutoProcessing;
  final bool enablePerformanceOptimization;
  final String defaultPlaybackMode;
  final bool showPerformanceIndicators;
  
  const WorkflowSettings({
    this.confidenceThreshold = 0.7,
    this.mvrQualityThreshold = 0.60,
    this.detectionMethods = const ['opencv', 'dlib'],
    this.enableAutoProcessing = false,
    this.enablePerformanceOptimization = true,
    this.defaultPlaybackMode = 'auto',
    this.showPerformanceIndicators = true,
  });
  
  WorkflowSettings copyWith({
    double? confidenceThreshold,
    double? mvrQualityThreshold,
    List<String>? detectionMethods,
    bool? enableAutoProcessing,
    bool? enablePerformanceOptimization,
    String? defaultPlaybackMode,
    bool? showPerformanceIndicators,
  }) {
    return WorkflowSettings(
      confidenceThreshold: confidenceThreshold ?? this.confidenceThreshold,
      mvrQualityThreshold: mvrQualityThreshold ?? this.mvrQualityThreshold,
      detectionMethods: detectionMethods ?? this.detectionMethods,
      enableAutoProcessing: enableAutoProcessing ?? this.enableAutoProcessing,
      enablePerformanceOptimization: enablePerformanceOptimization ?? this.enablePerformanceOptimization,
      defaultPlaybackMode: defaultPlaybackMode ?? this.defaultPlaybackMode,
      showPerformanceIndicators: showPerformanceIndicators ?? this.showPerformanceIndicators,
    );
  }
}

/// Provider for workflow settings state
final workflowSettingsProvider = StateNotifierProvider<WorkflowSettingsNotifier, WorkflowSettings>((ref) {
  return WorkflowSettingsNotifier();
});

class WorkflowSettingsNotifier extends StateNotifier<WorkflowSettings> {
  WorkflowSettingsNotifier() : super(const WorkflowSettings());
  
  void updateConfidenceThreshold(double threshold) {
    state = state.copyWith(confidenceThreshold: threshold);
  }
  
  void updateMvrQualityThreshold(double threshold) {
    state = state.copyWith(mvrQualityThreshold: threshold);
  }
  
  void updateDetectionMethods(List<String> methods) {
    state = state.copyWith(detectionMethods: methods);
  }
  
  void toggleAutoProcessing(bool enabled) {
    state = state.copyWith(enableAutoProcessing: enabled);
  }
  
  void togglePerformanceOptimization(bool enabled) {
    state = state.copyWith(enablePerformanceOptimization: enabled);
  }
  
  void updateDefaultPlaybackMode(String mode) {
    state = state.copyWith(defaultPlaybackMode: mode);
  }
  
  void togglePerformanceIndicators(bool enabled) {
    state = state.copyWith(showPerformanceIndicators: enabled);
  }
  
  void resetToDefaults() {
    state = const WorkflowSettings();
  }
}

/// Workflow settings section for the main settings screen
class WorkflowSettingsSection extends ConsumerStatefulWidget {
  const WorkflowSettingsSection({super.key});

  @override
  ConsumerState<WorkflowSettingsSection> createState() => _WorkflowSettingsSectionState();
}

class _WorkflowSettingsSectionState extends ConsumerState<WorkflowSettingsSection> {
  bool _isExpanded = false;
  
  @override
  Widget build(BuildContext context) {
    final settings = ref.watch(workflowSettingsProvider);
    
    return Card(
      color: AppColors.cardBackground,
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Column(
        children: [
          // Header with expand/collapse
          ListTile(
            leading: Icon(
              Icons.auto_awesome,
              color: AppColors.primary,
            ),
            title: Text(
              'Workflow Settings',
              style: AppTextStyles.h6.copyWith(
                color: AppColors.textPrimary,
                fontWeight: FontWeight.w600,
              ),
            ),
            subtitle: Text(
              'Face detection and performance optimization',
              style: AppTextStyles.bodyMedium.copyWith(
                color: AppColors.textSecondary,
              ),
            ),
            trailing: IconButton(
              icon: Icon(
                _isExpanded ? Icons.expand_less : Icons.expand_more,
                color: AppColors.textSecondary,
              ),
              onPressed: () {
                setState(() => _isExpanded = !_isExpanded);
              },
            ),
          ),
          
          // Expandable content
          if (_isExpanded) ...[
            const Divider(),
            Padding(
              padding: const EdgeInsets.all(16.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Face Detection Settings
                  _buildSectionHeader('Face Detection'),
                  const SizedBox(height: 12),
                  _buildConfidenceSlider(settings),
                  const SizedBox(height: 16),
                  _buildDetectionMethodsToggle(settings),
                  
                  const SizedBox(height: 24),
                  
                  // MVR People Settings
                  _buildSectionHeader('MVR People Creation'),
                  const SizedBox(height: 12),
                  _buildMvrQualitySlider(settings),
                  
                  const SizedBox(height: 24),
                  
                  // Performance Settings
                  _buildSectionHeader('Performance'),
                  const SizedBox(height: 12),
                  _buildPerformanceSettings(settings),
                  
                  const SizedBox(height: 24),
                  
                  // Playback Settings
                  _buildSectionHeader('Playback'),
                  const SizedBox(height: 12),
                  _buildPlaybackSettings(settings),
                  
                  const SizedBox(height: 24),
                  
                  // Action buttons
                  _buildActionButtons(),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }
  
  Widget _buildSectionHeader(String title) {
    return Text(
      title,
      style: AppTextStyles.h6.copyWith(
        color: AppColors.textPrimary,
        fontWeight: FontWeight.w600,
      ),
    );
  }
  
  Widget _buildConfidenceSlider(WorkflowSettings settings) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppColors.divider),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Confidence Threshold',
                style: AppTextStyles.bodyLarge.copyWith(
                  color: AppColors.textPrimary,
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: AppColors.primary.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Text(
                  '${(settings.confidenceThreshold * 100).round()}%',
                  style: AppTextStyles.caption.copyWith(
                    color: AppColors.primary,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          SliderTheme(
            data: SliderTheme.of(context).copyWith(
              activeTrackColor: AppColors.primary,
              inactiveTrackColor: AppColors.divider,
              thumbColor: AppColors.primary,
              overlayColor: AppColors.primary.withOpacity(0.2),
            ),
            child: Slider(
              value: settings.confidenceThreshold,
              min: 0.1,
              max: 1.0,
              divisions: 18,
              onChanged: (value) {
                ref.read(workflowSettingsProvider.notifier)
                    .updateConfidenceThreshold(value);
              },
            ),
          ),
          Text(
            'Higher values = more accurate but fewer detections',
            style: AppTextStyles.caption.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
        ],
      ),
    );
  }
  
  Widget _buildMvrQualitySlider(WorkflowSettings settings) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppColors.divider),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Minimum Face Quality',
                style: AppTextStyles.bodyLarge.copyWith(
                  color: AppColors.textPrimary,
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: AppColors.primary.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Text(
                  '${(settings.mvrQualityThreshold * 100).round()}%',
                  style: AppTextStyles.caption.copyWith(
                    color: AppColors.primary,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          SliderTheme(
            data: SliderTheme.of(context).copyWith(
              activeTrackColor: AppColors.primary,
              inactiveTrackColor: AppColors.divider,
              thumbColor: AppColors.primary,
              overlayColor: AppColors.primary.withOpacity(0.2),
            ),
            child: Slider(
              value: settings.mvrQualityThreshold,
              min: 0.5,
              max: 0.95,
              divisions: 9,
              onChanged: (value) {
                ref.read(workflowSettingsProvider.notifier)
                    .updateMvrQualityThreshold(value);
              },
            ),
          ),
          Text(
            'Minimum quality threshold for creating MVR people from detected faces',
            style: AppTextStyles.caption.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
        ],
      ),
    );
  }
  
  Widget _buildDetectionMethodsToggle(WorkflowSettings settings) {
    final availableMethods = ['opencv', 'dlib', 'mtcnn', 'yolo'];
    
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppColors.divider),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Detection Methods',
            style: AppTextStyles.bodyLarge.copyWith(
              color: AppColors.textPrimary,
            ),
          ),
          const SizedBox(height: 12),
          ...availableMethods.map((method) {
            final isSelected = settings.detectionMethods.contains(method);
            return CheckboxListTile(
              contentPadding: EdgeInsets.zero,
              title: Text(
                method.toUpperCase(),
                style: AppTextStyles.bodyMedium.copyWith(
                  color: AppColors.textPrimary,
                ),
              ),
              subtitle: Text(
                _getMethodDescription(method),
                style: AppTextStyles.caption.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
              value: isSelected,
              activeColor: AppColors.primary,
              onChanged: (selected) {
                final updatedMethods = List<String>.from(settings.detectionMethods);
                if (selected == true) {
                  updatedMethods.add(method);
                } else {
                  updatedMethods.remove(method);
                }
                ref.read(workflowSettingsProvider.notifier)
                    .updateDetectionMethods(updatedMethods);
              },
            );
          }),
        ],
      ),
    );
  }
  
  String _getMethodDescription(String method) {
    switch (method) {
      case 'opencv':
        return 'Fast, good for real-time processing';
      case 'dlib':
        return 'High accuracy, slower processing';
      case 'mtcnn':
        return 'Best accuracy, slowest processing';
      case 'yolo':
        return 'Balanced speed and accuracy';
      default:
        return 'Face detection method';
    }
  }
  
  Widget _buildPerformanceSettings(WorkflowSettings settings) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppColors.divider),
      ),
      child: Column(
        children: [
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: Text(
              'Performance Optimization',
              style: AppTextStyles.bodyLarge.copyWith(
                color: AppColors.textPrimary,
              ),
            ),
            subtitle: Text(
              'Use Workflow 5 for CPU reduction during playback',
              style: AppTextStyles.caption.copyWith(
                color: AppColors.textSecondary,
              ),
            ),
            value: settings.enablePerformanceOptimization,
            activeColor: AppColors.primary,
            onChanged: (value) {
              ref.read(workflowSettingsProvider.notifier)
                  .togglePerformanceOptimization(value);
            },
          ),
          const Divider(),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: Text(
              'Show Performance Indicators',
              style: AppTextStyles.bodyLarge.copyWith(
                color: AppColors.textPrimary,
              ),
            ),
            subtitle: Text(
              'Display CPU usage and performance metrics',
              style: AppTextStyles.caption.copyWith(
                color: AppColors.textSecondary,
              ),
            ),
            value: settings.showPerformanceIndicators,
            activeColor: AppColors.primary,
            onChanged: (value) {
              ref.read(workflowSettingsProvider.notifier)
                  .togglePerformanceIndicators(value);
            },
          ),
          const Divider(),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: Text(
              'Auto-Process New Videos',
              style: AppTextStyles.bodyLarge.copyWith(
                color: AppColors.textPrimary,
              ),
            ),
            subtitle: Text(
              'Automatically process videos for optimized playback',
              style: AppTextStyles.caption.copyWith(
                color: AppColors.textSecondary,
              ),
            ),
            value: settings.enableAutoProcessing,
            activeColor: AppColors.primary,
            onChanged: (value) {
              ref.read(workflowSettingsProvider.notifier)
                  .toggleAutoProcessing(value);
            },
          ),
        ],
      ),
    );
  }
  
  Widget _buildPlaybackSettings(WorkflowSettings settings) {
    final modes = [
      ('auto', 'Automatic (Recommended)', 'Automatically choose the best mode'),
      ('stored_data', 'Optimized Only', 'Use processed data for maximum performance'),
      ('realtime_with_session', 'Session-Based', 'Process during playback with session management'),
      ('realtime_only', 'Real-time Only', 'Process in real-time without optimization'),
    ];
    
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppColors.divider),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Default Playback Mode',
            style: AppTextStyles.bodyLarge.copyWith(
              color: AppColors.textPrimary,
            ),
          ),
          const SizedBox(height: 12),
          ...modes.map((mode) {
            final (value, title, description) = mode;
            return RadioListTile<String>(
              contentPadding: EdgeInsets.zero,
              title: Text(
                title,
                style: AppTextStyles.bodyMedium.copyWith(
                  color: AppColors.textPrimary,
                ),
              ),
              subtitle: Text(
                description,
                style: AppTextStyles.caption.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
              value: value,
              groupValue: settings.defaultPlaybackMode,
              activeColor: AppColors.primary,
              onChanged: (newValue) {
                if (newValue != null) {
                  ref.read(workflowSettingsProvider.notifier)
                      .updateDefaultPlaybackMode(newValue);
                }
              },
            );
          }),
        ],
      ),
    );
  }
  
  Widget _buildActionButtons() {
    return Row(
      children: [
        Expanded(
          child: ElevatedButton.icon(
            onPressed: () {
              ref.read(workflowSettingsProvider.notifier).resetToDefaults();
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(
                  content: const Text('Settings reset to defaults'),
                  backgroundColor: AppColors.primary,
                ),
              );
            },
            icon: const Icon(Icons.restore, size: 16),
            label: const Text('Reset'),
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.surface,
              foregroundColor: AppColors.textPrimary,
              side: BorderSide(color: AppColors.divider),
            ),
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: ElevatedButton.icon(
            onPressed: () {
              _saveSettings();
            },
            icon: const Icon(Icons.save, size: 16),
            label: const Text('Save'),
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.primary,
              foregroundColor: Colors.white,
            ),
          ),
        ),
      ],
    );
  }
  
  void _saveSettings() {
    // Here you would save settings to persistent storage
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: const Text('Workflow settings saved successfully'),
        backgroundColor: AppColors.success ?? Colors.green,
      ),
    );
  }
}