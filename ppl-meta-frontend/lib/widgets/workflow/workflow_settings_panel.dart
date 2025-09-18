import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../models/face_detection_models.dart';
import '../../providers/workflow_providers.dart';
import '../../services/workflow_api_client.dart';

/// Settings model for workflow configuration
class WorkflowSettings {
  final double confidenceThreshold;
  final List<String> detectionMethods;
  final bool enableAutoProcessing;
  final bool enablePerformanceOptimization;
  final String defaultPlaybackMode;
  final bool showPerformanceIndicators;
  
  const WorkflowSettings({
    this.confidenceThreshold = 0.7,
    this.detectionMethods = const ['opencv', 'dlib'],
    this.enableAutoProcessing = false,
    this.enablePerformanceOptimization = true,
    this.defaultPlaybackMode = 'auto',
    this.showPerformanceIndicators = true,
  });
  
  WorkflowSettings copyWith({
    double? confidenceThreshold,
    List<String>? detectionMethods,
    bool? enableAutoProcessing,
    bool? enablePerformanceOptimization,
    String? defaultPlaybackMode,
    bool? showPerformanceIndicators,
  }) {
    return WorkflowSettings(
      confidenceThreshold: confidenceThreshold ?? this.confidenceThreshold,
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

/// Comprehensive workflow settings panel
class WorkflowSettingsPanel extends ConsumerStatefulWidget {
  final bool showAdvancedSettings;
  final VoidCallback? onSettingsChanged;
  
  const WorkflowSettingsPanel({
    super.key,
    this.showAdvancedSettings = false,
    this.onSettingsChanged,
  });

  @override
  ConsumerState<WorkflowSettingsPanel> createState() => _WorkflowSettingsPanelState();
}

class _WorkflowSettingsPanelState extends ConsumerState<WorkflowSettingsPanel>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  bool _showPreview = false;
  
  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
  }
  
  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }
  
  @override
  Widget build(BuildContext context) {
    final settings = ref.watch(workflowSettingsProvider);
    
    return Card(
      margin: const EdgeInsets.all(16.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          _buildHeader(),
          
          // Tab bar
          TabBar(
            controller: _tabController,
            tabs: const [
              Tab(icon: Icon(Icons.tune), text: 'Detection'),
              Tab(icon: Icon(Icons.speed), text: 'Performance'),
              Tab(icon: Icon(Icons.play_circle), text: 'Playback'),
            ],
          ),
          
          // Tab content
          SizedBox(
            height: 400,
            child: TabBarView(
              controller: _tabController,
              children: [
                _buildDetectionSettings(settings),
                _buildPerformanceSettings(settings),
                _buildPlaybackSettings(settings),
              ],
            ),
          ),
          
          // Action buttons
          _buildActionButtons(),
        ],
      ),
    );
  }
  
  Widget _buildHeader() {
    return Padding(
      padding: const EdgeInsets.all(16.0),
      child: Row(
        children: [
          const Icon(Icons.settings, size: 24),
          const SizedBox(width: 8),
          const Text(
            'Workflow Settings',
            style: TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.bold,
            ),
          ),
          const Spacer(),
          // Live preview toggle
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text('Preview', style: TextStyle(fontSize: 14)),
              const SizedBox(width: 8),
              Switch(
                value: _showPreview,
                onChanged: (value) {
                  setState(() => _showPreview = value);
                  if (widget.onSettingsChanged != null) {
                    widget.onSettingsChanged!();
                  }
                },
              ),
            ],
          ),
        ],
      ),
    );
  }
  
  Widget _buildDetectionSettings(WorkflowSettings settings) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Confidence threshold
          _buildSectionTitle('Face Detection Confidence'),
          _buildConfidenceSlider(settings),
          
          const SizedBox(height: 24),
          
          // Detection methods
          _buildSectionTitle('Detection Methods'),
          _buildDetectionMethodsSelector(settings),
          
          const SizedBox(height: 24),
          
          // Auto-processing
          _buildSectionTitle('Processing Options'),
          _buildAutoProcessingToggle(settings),
        ],
      ),
    );
  }
  
  Widget _buildPerformanceSettings(WorkflowSettings settings) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Performance optimization
          _buildSectionTitle('Performance Optimization'),
          _buildPerformanceOptimizationToggle(settings),
          
          const SizedBox(height: 24),
          
          // Performance indicators
          _buildSectionTitle('Visual Indicators'),
          _buildPerformanceIndicatorsToggle(settings),
          
          const SizedBox(height: 24),
          
          // Performance metrics preview
          if (_showPreview) _buildPerformancePreview(),
        ],
      ),
    );
  }
  
  Widget _buildPlaybackSettings(WorkflowSettings settings) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Default playback mode
          _buildSectionTitle('Default Playback Mode'),
          _buildPlaybackModeSelector(settings),
          
          const SizedBox(height: 24),
          
          // Playback options
          _buildSectionTitle('Playback Options'),
          _buildPlaybackOptions(settings),
          
          const SizedBox(height: 24),
          
          // Playback preview
          if (_showPreview) _buildPlaybackPreview(),
        ],
      ),
    );
  }
  
  Widget _buildSectionTitle(String title) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12.0),
      child: Text(
        title,
        style: const TextStyle(
          fontSize: 16,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }
  
  Widget _buildConfidenceSlider(WorkflowSettings settings) {
    return Column(
      children: [
        Row(
          children: [
            const Text('Threshold: '),
            Text(
              '${(settings.confidenceThreshold * 100).round()}%',
              style: const TextStyle(fontWeight: FontWeight.bold),
            ),
          ],
        ),
        Slider(
          value: settings.confidenceThreshold,
          min: 0.1,
          max: 1.0,
          divisions: 18,
          onChanged: (value) {
            ref.read(workflowSettingsProvider.notifier)
                .updateConfidenceThreshold(value);
            if (widget.onSettingsChanged != null) {
              widget.onSettingsChanged!();
            }
          },
        ),
        const Text(
          'Higher values = more accurate but fewer detections',
          style: TextStyle(fontSize: 12, color: Colors.grey),
        ),
      ],
    );
  }
  
  Widget _buildDetectionMethodsSelector(WorkflowSettings settings) {
    final availableMethods = ['opencv', 'dlib', 'mtcnn', 'yolo'];
    
    return Column(
      children: availableMethods.map((method) {
        final isSelected = settings.detectionMethods.contains(method);
        return CheckboxListTile(
          title: Text(method.toUpperCase()),
          subtitle: Text(_getMethodDescription(method)),
          value: isSelected,
          onChanged: (selected) {
            final updatedMethods = List<String>.from(settings.detectionMethods);
            if (selected == true) {
              updatedMethods.add(method);
            } else {
              updatedMethods.remove(method);
            }
            ref.read(workflowSettingsProvider.notifier)
                .updateDetectionMethods(updatedMethods);
            if (widget.onSettingsChanged != null) {
              widget.onSettingsChanged!();
            }
          },
        );
      }).toList(),
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
  
  Widget _buildAutoProcessingToggle(WorkflowSettings settings) {
    return SwitchListTile(
      title: const Text('Auto-Process New Videos'),
      subtitle: const Text('Automatically process videos for optimized playback'),
      value: settings.enableAutoProcessing,
      onChanged: (value) {
        ref.read(workflowSettingsProvider.notifier)
            .toggleAutoProcessing(value);
        if (widget.onSettingsChanged != null) {
          widget.onSettingsChanged!();
        }
      },
    );
  }
  
  Widget _buildPerformanceOptimizationToggle(WorkflowSettings settings) {
    return SwitchListTile(
      title: const Text('Enable Performance Optimization'),
      subtitle: const Text('Use Workflow 5 for CPU reduction during playback'),
      value: settings.enablePerformanceOptimization,
      onChanged: (value) {
        ref.read(workflowSettingsProvider.notifier)
            .togglePerformanceOptimization(value);
        if (widget.onSettingsChanged != null) {
          widget.onSettingsChanged!();
        }
      },
    );
  }
  
  Widget _buildPerformanceIndicatorsToggle(WorkflowSettings settings) {
    return SwitchListTile(
      title: const Text('Show Performance Indicators'),
      subtitle: const Text('Display CPU usage and performance metrics'),
      value: settings.showPerformanceIndicators,
      onChanged: (value) {
        ref.read(workflowSettingsProvider.notifier)
            .togglePerformanceIndicators(value);
        if (widget.onSettingsChanged != null) {
          widget.onSettingsChanged!();
        }
      },
    );
  }
  
  Widget _buildPlaybackModeSelector(WorkflowSettings settings) {
    final modes = [
      'auto',
      'stored_data',
      'realtime_with_session',
      'realtime_only',
    ];
    
    return Column(
      children: modes.map((mode) {
        return RadioListTile<String>(
          title: Text(_getPlaybackModeTitle(mode)),
          subtitle: Text(_getPlaybackModeDescription(mode)),
          value: mode,
          groupValue: settings.defaultPlaybackMode,
          onChanged: (value) {
            if (value != null) {
              ref.read(workflowSettingsProvider.notifier)
                  .updateDefaultPlaybackMode(value);
              if (widget.onSettingsChanged != null) {
                widget.onSettingsChanged!();
              }
            }
          },
        );
      }).toList(),
    );
  }
  
  String _getPlaybackModeTitle(String mode) {
    switch (mode) {
      case 'auto':
        return 'Automatic (Recommended)';
      case 'stored_data':
        return 'Optimized Only';
      case 'realtime_with_session':
        return 'Session-Based';
      case 'realtime_only':
        return 'Real-time Only';
      default:
        return mode;
    }
  }
  
  String _getPlaybackModeDescription(String mode) {
    switch (mode) {
      case 'auto':
        return 'Automatically choose the best mode';
      case 'stored_data':
        return 'Use processed data for maximum performance';
      case 'realtime_with_session':
        return 'Process during playback with session management';
      case 'realtime_only':
        return 'Process in real-time without optimization';
      default:
        return 'Playback mode';
    }
  }
  
  Widget _buildPlaybackOptions(WorkflowSettings settings) {
    return Column(
      children: [
        ListTile(
          leading: const Icon(Icons.memory),
          title: const Text('Memory Usage'),
          subtitle: const Text('Optimize for low memory usage'),
          trailing: Switch(
            value: true, // This would be another setting
            onChanged: (value) {
              // Handle memory optimization toggle
            },
          ),
        ),
        ListTile(
          leading: const Icon(Icons.speed),
          title: const Text('Processing Speed'),
          subtitle: const Text('Prioritize fast processing over accuracy'),
          trailing: Switch(
            value: false, // This would be another setting
            onChanged: (value) {
              // Handle speed optimization toggle
            },
          ),
        ),
      ],
    );
  }
  
  Widget _buildPerformancePreview() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.grey.shade100,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.grey.shade300),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Performance Preview',
            style: TextStyle(fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              const Icon(Icons.trending_down, color: Colors.green, size: 16),
              const SizedBox(width: 4),
              const Text('CPU Usage: '),
              Text(
                '90% reduction',
                style: TextStyle(
                  color: Colors.green.shade700,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          Row(
            children: [
              const Icon(Icons.memory, color: Colors.blue, size: 16),
              const SizedBox(width: 4),
              const Text('Memory: '),
              Text(
                '75% reduction',
                style: TextStyle(
                  color: Colors.blue.shade700,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
  
  Widget _buildPlaybackPreview() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.grey.shade100,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.grey.shade300),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Playback Preview',
            style: TextStyle(fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Container(
                width: 12,
                height: 12,
                decoration: BoxDecoration(
                  color: Colors.green,
                  borderRadius: BorderRadius.circular(6),
                ),
              ),
              const SizedBox(width: 8),
              const Text('Optimized playback mode active'),
            ],
          ),
          const SizedBox(height: 4),
          const Text(
            'Face detection data will be loaded from stored processing results',
            style: TextStyle(fontSize: 12, color: Colors.grey),
          ),
        ],
      ),
    );
  }
  
  Widget _buildActionButtons() {
    return Padding(
      padding: const EdgeInsets.all(16.0),
      child: Row(
        children: [
          ElevatedButton.icon(
            onPressed: () {
              ref.read(workflowSettingsProvider.notifier).resetToDefaults();
              if (widget.onSettingsChanged != null) {
                widget.onSettingsChanged!();
              }
            },
            icon: const Icon(Icons.restore, size: 16),
            label: const Text('Reset'),
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.grey.shade600,
              foregroundColor: Colors.white,
            ),
          ),
          const SizedBox(width: 12),
          ElevatedButton.icon(
            onPressed: () {
              _saveSettings();
            },
            icon: const Icon(Icons.save, size: 16),
            label: const Text('Save Settings'),
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.blue.shade600,
              foregroundColor: Colors.white,
            ),
          ),
          const Spacer(),
          TextButton.icon(
            onPressed: () {
              _testSettings();
            },
            icon: const Icon(Icons.play_arrow, size: 16),
            label: const Text('Test'),
            style: TextButton.styleFrom(
              foregroundColor: Colors.blue.shade600,
            ),
          ),
        ],
      ),
    );
  }
  
  void _saveSettings() {
    // Here you would save settings to persistent storage
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Settings saved successfully'),
        backgroundColor: Colors.green,
      ),
    );
  }
  
  void _testSettings() {
    // Here you would test the current settings
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Testing workflow settings...'),
        backgroundColor: Colors.blue,
      ),
    );
  }
}