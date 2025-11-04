import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:file_picker/file_picker.dart';
import '../providers/settings_providers.dart';
import '../models/settings_models.dart';

class SettingsScreen extends ConsumerStatefulWidget {
  const SettingsScreen({super.key});

  @override
  ConsumerState<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends ConsumerState<SettingsScreen>
    with TickerProviderStateMixin {
  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 5, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Settings & Configuration'),
        bottom: TabBar(
          controller: _tabController,
          tabs: const [
            Tab(icon: Icon(Icons.person), text: 'General'),
            Tab(icon: Icon(Icons.face), text: 'Detection'),
            Tab(icon: Icon(Icons.videocam), text: 'Cameras'),
            Tab(icon: Icon(Icons.smart_toy), text: 'Automation'),
            Tab(icon: Icon(Icons.import_export), text: 'Import/Export'),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tabController,
        children: const [
          GeneralSettingsTab(),
          DetectionSettingsTab(),
          CameraSettingsTab(),
          AutomationSettingsTab(),
          ImportExportTab(),
        ],
      ),
    );
  }
}

// ====================
// General Settings Tab
// ====================

class GeneralSettingsTab extends ConsumerWidget {
  const GeneralSettingsTab({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final settings = ref.watch(generalSettingsProvider);
    final notifier = ref.watch(generalSettingsProvider.notifier);

    return settings.when(
      data: (data) => SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildSectionHeader('User Preferences'),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  children: [
                    SwitchListTile(
                      title: const Text('Dark Theme'),
                      subtitle: const Text('Use dark theme for the interface'),
                      value: data.darkTheme,
                      onChanged: (value) => notifier.updateDarkTheme(value),
                    ),
                    const Divider(),
                    SwitchListTile(
                      title: const Text('Auto Refresh'),
                      subtitle: const Text('Automatically refresh data'),
                      value: data.autoRefresh,
                      onChanged: (value) => notifier.updateAutoRefresh(value),
                    ),
                    const Divider(),
                    ListTile(
                      title: const Text('Refresh Interval'),
                      subtitle: Text('${data.refreshInterval} seconds'),
                      trailing: SizedBox(
                        width: 100,
                        child: TextFormField(
                          initialValue: data.refreshInterval.toString(),
                          keyboardType: TextInputType.number,
                          onFieldSubmitted: (value) {
                            final interval = int.tryParse(value) ?? 30;
                            notifier.updateRefreshInterval(interval);
                          },
                        ),
                      ),
                    ),
                    const Divider(),
                    SwitchListTile(
                      title: const Text('Enable Notifications'),
                      subtitle: const Text('Show system notifications'),
                      value: data.enableNotifications,
                      onChanged: (value) => notifier.updateNotifications(value),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 24),
            _buildSectionHeader('Cross-Video Tracking'),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  children: [
                    ListTile(
                      leading: const Icon(Icons.merge_type),
                      title: const Text('Merge Individuals Rules'),
                      subtitle: const Text('How to handle duplicate individuals'),
                    ),
                    RadioListTile<String>(
                      title: const Text('No automatic merging'),
                      subtitle: const Text('Manual selection only'),
                      value: 'none',
                      groupValue: data.mergeIndividualsRule,
                      onChanged: (value) {
                        if (value != null) {
                          notifier.updateMergeIndividualsRule(value);
                        }
                      },
                    ),
                    RadioListTile<String>(
                      title: const Text('Semi-automatic merging'),
                      subtitle: const Text('Suggest merges, require confirmation'),
                      value: 'semi',
                      groupValue: data.mergeIndividualsRule,
                      onChanged: (value) {
                        if (value != null) {
                          notifier.updateMergeIndividualsRule(value);
                        }
                      },
                    ),
                    RadioListTile<String>(
                      title: const Text('Automatic merging'),
                      subtitle: const Text('Automatically merge similar individuals'),
                      value: 'auto',
                      groupValue: data.mergeIndividualsRule,
                      onChanged: (value) {
                        if (value != null) {
                          notifier.updateMergeIndividualsRule(value);
                        }
                      },
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 24),
            _buildSectionHeader('System Configuration'),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  children: [
                    ListTile(
                      title: const Text('Max Log Entries'),
                      subtitle: Text('${data.maxLogEntries} entries'),
                      trailing: SizedBox(
                        width: 100,
                        child: TextFormField(
                          initialValue: data.maxLogEntries.toString(),
                          keyboardType: TextInputType.number,
                          onFieldSubmitted: (value) {
                            final max = int.tryParse(value) ?? 1000;
                            notifier.updateMaxLogEntries(max);
                          },
                        ),
                      ),
                    ),
                    const Divider(),
                    SwitchListTile(
                      title: const Text('Debug Mode'),
                      subtitle: const Text('Enable detailed logging'),
                      value: data.debugMode,
                      onChanged: (value) => notifier.updateDebugMode(value),
                    ),
                    const Divider(),
                    SwitchListTile(
                      title: const Text('Performance Monitoring'),
                      subtitle: const Text('Track system performance'),
                      value: data.performanceMonitoring,
                      onChanged: (value) => notifier.updatePerformanceMonitoring(value),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (error, stack) => Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.error, size: 64, color: Colors.red),
            const SizedBox(height: 16),
            Text('Error loading settings: $error'),
          ],
        ),
      ),
    );
  }

  Widget _buildSectionHeader(String title) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 16),
      child: Text(
        title,
        style: const TextStyle(
          fontSize: 20,
          fontWeight: FontWeight.bold,
        ),
      ),
    );
  }
}

// ====================
// Detection Settings Tab
// ====================

class DetectionSettingsTab extends ConsumerWidget {
  const DetectionSettingsTab({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final settings = ref.watch(detectionSettingsProvider);
    final notifier = ref.watch(detectionSettingsProvider.notifier);

    return settings.when(
      data: (data) => SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildSectionHeader('Detection Methods'),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  children: [
                    DropdownButtonFormField<String>(
                      value: data.defaultMethod,
                      decoration: const InputDecoration(
                        labelText: 'Default Detection Method',
                        border: OutlineInputBorder(),
                      ),
                      items: data.availableMethods.map((method) {
                        return DropdownMenuItem(
                          value: method,
                          child: Text(method.toUpperCase()),
                        );
                      }).toList(),
                      onChanged: (value) {
                        if (value != null) {
                          notifier.updateDefaultMethod(value);
                        }
                      },
                    ),
                    const SizedBox(height: 16),
                    Text(
                      'Confidence Threshold: ${(data.confidenceThreshold * 100).toStringAsFixed(0)}%',
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    Slider(
                      value: data.confidenceThreshold,
                      min: 0.1,
                      max: 1.0,
                      divisions: 9,
                      label: '${(data.confidenceThreshold * 100).toStringAsFixed(0)}%',
                      onChanged: (value) => notifier.updateConfidenceThreshold(value),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 24),
            _buildSectionHeader('Processing Options'),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  children: [
                    SwitchListTile(
                      title: const Text('Save Detection Results'),
                      subtitle: const Text('Store detection images and metadata'),
                      value: data.saveResults,
                      onChanged: (value) => notifier.updateSaveResults(value),
                    ),
                    const Divider(),
                    SwitchListTile(
                      title: const Text('Real-time Processing'),
                      subtitle: const Text('Process frames in real-time'),
                      value: data.realTimeProcessing,
                      onChanged: (value) => notifier.updateRealTimeProcessing(value),
                    ),
                    const Divider(),
                    ListTile(
                      title: const Text('Batch Size'),
                      subtitle: Text('${data.batchSize} frames'),
                      trailing: SizedBox(
                        width: 100,
                        child: TextFormField(
                          initialValue: data.batchSize.toString(),
                          keyboardType: TextInputType.number,
                          onFieldSubmitted: (value) {
                            final size = int.tryParse(value) ?? 10;
                            notifier.updateBatchSize(size);
                          },
                        ),
                      ),
                    ),
                    const Divider(),
                    ListTile(
                      title: const Text('Max Concurrent Detections'),
                      subtitle: Text('${data.maxConcurrentDetections} parallel'),
                      trailing: SizedBox(
                        width: 100,
                        child: TextFormField(
                          initialValue: data.maxConcurrentDetections.toString(),
                          keyboardType: TextInputType.number,
                          onFieldSubmitted: (value) {
                            final max = int.tryParse(value) ?? 4;
                            notifier.updateMaxConcurrentDetections(max);
                          },
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 24),
            _buildSectionHeader('Advanced Settings'),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  children: [
                    TextFormField(
                      initialValue: data.customModelPath ?? '',
                      decoration: const InputDecoration(
                        labelText: 'Custom Model Path',
                        border: OutlineInputBorder(),
                        suffixIcon: Icon(Icons.folder),
                      ),
                      onFieldSubmitted: (value) {
                        notifier.updateCustomModelPath(value.isEmpty ? null : value);
                      },
                    ),
                    const SizedBox(height: 16),
                    SwitchListTile(
                      title: const Text('GPU Acceleration'),
                      subtitle: const Text('Use GPU for processing (if available)'),
                      value: data.useGpuAcceleration,
                      onChanged: (value) => notifier.updateGpuAcceleration(value),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (error, stack) => Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.error, size: 64, color: Colors.red),
            const SizedBox(height: 16),
            Text('Error loading detection settings: $error'),
          ],
        ),
      ),
    );
  }

  Widget _buildSectionHeader(String title) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 16),
      child: Text(
        title,
        style: const TextStyle(
          fontSize: 20,
          fontWeight: FontWeight.bold,
        ),
      ),
    );
  }
}

// ====================
// Camera Settings Tab
// ====================

class CameraSettingsTab extends ConsumerWidget {
  const CameraSettingsTab({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final settings = ref.watch(cameraSettingsProvider);
    final notifier = ref.watch(cameraSettingsProvider.notifier);

    return settings.when(
      data: (data) => SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildSectionHeader('Default Camera Settings'),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  children: [
                    DropdownButtonFormField<String>(
                      value: data.defaultResolution,
                      decoration: const InputDecoration(
                        labelText: 'Default Resolution',
                        border: OutlineInputBorder(),
                      ),
                      items: data.availableResolutions.map((res) {
                        return DropdownMenuItem(
                          value: res,
                          child: Text(res),
                        );
                      }).toList(),
                      onChanged: (value) {
                        if (value != null) {
                          notifier.updateDefaultResolution(value);
                        }
                      },
                    ),
                    const SizedBox(height: 16),
                    DropdownButtonFormField<int>(
                      value: data.defaultFrameRate,
                      decoration: const InputDecoration(
                        labelText: 'Default Frame Rate',
                        border: OutlineInputBorder(),
                      ),
                      items: data.availableFrameRates.map((rate) {
                        return DropdownMenuItem(
                          value: rate,
                          child: Text('$rate fps'),
                        );
                      }).toList(),
                      onChanged: (value) {
                        if (value != null) {
                          notifier.updateDefaultFrameRate(value);
                        }
                      },
                    ),
                    const SizedBox(height: 16),
                    DropdownButtonFormField<String>(
                      value: data.defaultFormat,
                      decoration: const InputDecoration(
                        labelText: 'Default Format',
                        border: OutlineInputBorder(),
                      ),
                      items: data.availableFormats.map((format) {
                        return DropdownMenuItem(
                          value: format,
                          child: Text(format.toUpperCase()),
                        );
                      }).toList(),
                      onChanged: (value) {
                        if (value != null) {
                          notifier.updateDefaultFormat(value);
                        }
                      },
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 24),
            _buildSectionHeader('Recording Settings'),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  children: [
                    SwitchListTile(
                      title: const Text('Auto Record'),
                      subtitle: const Text('Start recording when motion detected'),
                      value: data.autoRecord,
                      onChanged: (value) => notifier.updateAutoRecord(value),
                    ),
                    const Divider(),
                    ListTile(
                      title: const Text('Max Recording Duration'),
                      subtitle: Text('${data.maxRecordingDuration} minutes'),
                      trailing: SizedBox(
                        width: 100,
                        child: TextFormField(
                          initialValue: data.maxRecordingDuration.toString(),
                          keyboardType: TextInputType.number,
                          onFieldSubmitted: (value) {
                            final duration = int.tryParse(value) ?? 60;
                            notifier.updateMaxRecordingDuration(duration);
                          },
                        ),
                      ),
                    ),
                    const Divider(),
                    TextFormField(
                      initialValue: data.recordingPath,
                      decoration: const InputDecoration(
                        labelText: 'Recording Storage Path',
                        border: OutlineInputBorder(),
                        suffixIcon: Icon(Icons.folder),
                      ),
                      onFieldSubmitted: (value) {
                        notifier.updateRecordingPath(value);
                      },
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 24),
            _buildSectionHeader('Connection Settings'),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  children: [
                    ListTile(
                      title: const Text('Connection Timeout'),
                      subtitle: Text('${data.connectionTimeout} seconds'),
                      trailing: SizedBox(
                        width: 100,
                        child: TextFormField(
                          initialValue: data.connectionTimeout.toString(),
                          keyboardType: TextInputType.number,
                          onFieldSubmitted: (value) {
                            final timeout = int.tryParse(value) ?? 30;
                            notifier.updateConnectionTimeout(timeout);
                          },
                        ),
                      ),
                    ),
                    const Divider(),
                    ListTile(
                      title: const Text('Retry Attempts'),
                      subtitle: Text('${data.retryAttempts} times'),
                      trailing: SizedBox(
                        width: 100,
                        child: TextFormField(
                          initialValue: data.retryAttempts.toString(),
                          keyboardType: TextInputType.number,
                          onFieldSubmitted: (value) {
                            final attempts = int.tryParse(value) ?? 3;
                            notifier.updateRetryAttempts(attempts);
                          },
                        ),
                      ),
                    ),
                    const Divider(),
                    SwitchListTile(
                      title: const Text('Auto Reconnect'),
                      subtitle: const Text('Automatically reconnect on disconnect'),
                      value: data.autoReconnect,
                      onChanged: (value) => notifier.updateAutoReconnect(value),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (error, stack) => Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.error, size: 64, color: Colors.red),
            const SizedBox(height: 16),
            Text('Error loading camera settings: $error'),
          ],
        ),
      ),
    );
  }

  Widget _buildSectionHeader(String title) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 16),
      child: Text(
        title,
        style: const TextStyle(
          fontSize: 20,
          fontWeight: FontWeight.bold,
        ),
      ),
    );
  }
}

// ====================
// Automation Settings Tab
// ====================

class AutomationSettingsTab extends ConsumerWidget {
  const AutomationSettingsTab({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final settings = ref.watch(automationSettingsProvider);
    final notifier = ref.watch(automationSettingsProvider.notifier);

    return settings.when(
      data: (data) => SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildSectionHeader('Engine Configuration'),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  children: [
                    SwitchListTile(
                      title: const Text('Enable Automation Engine'),
                      subtitle: const Text('Allow automatic rule execution'),
                      value: data.enableEngine,
                      onChanged: (value) => notifier.updateEnableEngine(value),
                    ),
                    const Divider(),
                    ListTile(
                      title: const Text('Rule Check Interval'),
                      subtitle: Text('${data.ruleCheckInterval} seconds'),
                      trailing: SizedBox(
                        width: 100,
                        child: TextFormField(
                          initialValue: data.ruleCheckInterval.toString(),
                          keyboardType: TextInputType.number,
                          onFieldSubmitted: (value) {
                            final interval = int.tryParse(value) ?? 10;
                            notifier.updateRuleCheckInterval(interval);
                          },
                        ),
                      ),
                    ),
                    const Divider(),
                    ListTile(
                      title: const Text('Max Concurrent Executions'),
                      subtitle: Text('${data.maxConcurrentExecutions} parallel'),
                      trailing: SizedBox(
                        width: 100,
                        child: TextFormField(
                          initialValue: data.maxConcurrentExecutions.toString(),
                          keyboardType: TextInputType.number,
                          onFieldSubmitted: (value) {
                            final max = int.tryParse(value) ?? 5;
                            notifier.updateMaxConcurrentExecutions(max);
                          },
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 24),
            _buildSectionHeader('Execution Settings'),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  children: [
                    ListTile(
                      title: const Text('Execution Timeout'),
                      subtitle: Text('${data.executionTimeout} seconds'),
                      trailing: SizedBox(
                        width: 100,
                        child: TextFormField(
                          initialValue: data.executionTimeout.toString(),
                          keyboardType: TextInputType.number,
                          onFieldSubmitted: (value) {
                            final timeout = int.tryParse(value) ?? 300;
                            notifier.updateExecutionTimeout(timeout);
                          },
                        ),
                      ),
                    ),
                    const Divider(),
                    ListTile(
                      title: const Text('Retry Attempts'),
                      subtitle: Text('${data.retryAttempts} times'),
                      trailing: SizedBox(
                        width: 100,
                        child: TextFormField(
                          initialValue: data.retryAttempts.toString(),
                          keyboardType: TextInputType.number,
                          onFieldSubmitted: (value) {
                            final attempts = int.tryParse(value) ?? 2;
                            notifier.updateRetryAttempts(attempts);
                          },
                        ),
                      ),
                    ),
                    const Divider(),
                    SwitchListTile(
                      title: const Text('Retry on Failure'),
                      subtitle: const Text('Automatically retry failed executions'),
                      value: data.retryOnFailure,
                      onChanged: (value) => notifier.updateRetryOnFailure(value),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 24),
            _buildSectionHeader('Logging & History'),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  children: [
                    SwitchListTile(
                      title: const Text('Log Executions'),
                      subtitle: const Text('Keep execution history'),
                      value: data.logExecutions,
                      onChanged: (value) => notifier.updateLogExecutions(value),
                    ),
                    const Divider(),
                    ListTile(
                      title: const Text('Max History Entries'),
                      subtitle: Text('${data.maxHistoryEntries} entries'),
                      trailing: SizedBox(
                        width: 100,
                        child: TextFormField(
                          initialValue: data.maxHistoryEntries.toString(),
                          keyboardType: TextInputType.number,
                          onFieldSubmitted: (value) {
                            final max = int.tryParse(value) ?? 1000;
                            notifier.updateMaxHistoryEntries(max);
                          },
                        ),
                      ),
                    ),
                    const Divider(),
                    SwitchListTile(
                      title: const Text('Enable Notifications'),
                      subtitle: const Text('Notify on automation events'),
                      value: data.enableNotifications,
                      onChanged: (value) => notifier.updateNotifications(value),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (error, stack) => Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.error, size: 64, color: Colors.red),
            const SizedBox(height: 16),
            Text('Error loading automation settings: $error'),
          ],
        ),
      ),
    );
  }

  Widget _buildSectionHeader(String title) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 16),
      child: Text(
        title,
        style: const TextStyle(
          fontSize: 20,
          fontWeight: FontWeight.bold,
        ),
      ),
    );
  }
}

// ====================
// Import/Export Tab
// ====================

class ImportExportTab extends ConsumerWidget {
  const ImportExportTab({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final importExportState = ref.watch(importExportProvider);
    final notifier = ref.watch(importExportProvider.notifier);

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildSectionHeader('Export Configuration'),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                children: [
                  ElevatedButton.icon(
                    onPressed: () => notifier.exportSettings(),
                    icon: const Icon(Icons.download),
                    label: const Text('Export All Settings'),
                    style: ElevatedButton.styleFrom(
                      minimumSize: const Size(double.infinity, 48),
                    ),
                  ),
                  const SizedBox(height: 16),
                  ElevatedButton.icon(
                    onPressed: () => notifier.exportAutomationRules(),
                    icon: const Icon(Icons.smart_toy),
                    label: const Text('Export Automation Rules'),
                    style: ElevatedButton.styleFrom(
                      minimumSize: const Size(double.infinity, 48),
                    ),
                  ),
                  const SizedBox(height: 16),
                  ElevatedButton.icon(
                    onPressed: () => notifier.exportCameraConfiguration(),
                    icon: const Icon(Icons.videocam),
                    label: const Text('Export Camera Configuration'),
                    style: ElevatedButton.styleFrom(
                      minimumSize: const Size(double.infinity, 48),
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 24),
          _buildSectionHeader('Import Configuration'),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                children: [
                  ElevatedButton.icon(
                    onPressed: () => notifier.importSettings(),
                    icon: const Icon(Icons.upload),
                    label: const Text('Import Settings'),
                    style: ElevatedButton.styleFrom(
                      minimumSize: const Size(double.infinity, 48),
                    ),
                  ),
                  const SizedBox(height: 16),
                  ElevatedButton.icon(
                    onPressed: () => notifier.importAutomationRules(),
                    icon: const Icon(Icons.smart_toy),
                    label: const Text('Import Automation Rules'),
                    style: ElevatedButton.styleFrom(
                      minimumSize: const Size(double.infinity, 48),
                    ),
                  ),
                  const SizedBox(height: 16),
                  OutlinedButton.icon(
                    onPressed: () => notifier.resetToDefaults(),
                    icon: const Icon(Icons.restore),
                    label: const Text('Reset to Defaults'),
                    style: OutlinedButton.styleFrom(
                      minimumSize: const Size(double.infinity, 48),
                      foregroundColor: Colors.orange,
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 24),
          if (importExportState.isProcessing) ...[
            _buildSectionHeader('Progress'),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  children: [
                    const LinearProgressIndicator(),
                    const SizedBox(height: 16),
                    Text(importExportState.currentOperation ?? 'Processing...'),
                  ],
                ),
              ),
            ),
          ],
          if (importExportState.lastResult != null) ...[
            _buildSectionHeader('Last Operation Result'),
            Card(
              color: importExportState.lastResult!.isSuccess
                  ? Colors.green.shade50
                  : Colors.red.shade50,
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(
                          importExportState.lastResult!.isSuccess
                              ? Icons.check_circle
                              : Icons.error,
                          color: importExportState.lastResult!.isSuccess
                              ? Colors.green
                              : Colors.red,
                        ),
                        const SizedBox(width: 8),
                        Text(
                          importExportState.lastResult!.isSuccess
                              ? 'Success'
                              : 'Error',
                          style: TextStyle(
                            fontWeight: FontWeight.bold,
                            color: importExportState.lastResult!.isSuccess
                                ? Colors.green
                                : Colors.red,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Text(importExportState.lastResult!.message),
                    if (importExportState.lastResult!.details != null) ...[
                      const SizedBox(height: 8),
                      Text(
                        importExportState.lastResult!.details!,
                        style: const TextStyle(fontSize: 12, color: Colors.grey),
                      ),
                    ],
                  ],
                ),
              ),
            ),
          ],
          const SizedBox(height: 24),
          _buildSectionHeader('Backup Options'),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                children: [
                  SwitchListTile(
                    title: const Text('Auto Backup'),
                    subtitle: const Text('Automatically backup settings daily'),
                    value: importExportState.autoBackup,
                    onChanged: (value) => notifier.updateAutoBackup(value),
                  ),
                  const Divider(),
                  ListTile(
                    title: const Text('Backup Location'),
                    subtitle: Text(importExportState.backupLocation ?? 'Default'),
                    trailing: IconButton(
                      icon: const Icon(Icons.folder),
                      onPressed: () => notifier.selectBackupLocation(),
                    ),
                  ),
                  const Divider(),
                  ElevatedButton.icon(
                    onPressed: () => notifier.createManualBackup(),
                    icon: const Icon(Icons.backup),
                    label: const Text('Create Manual Backup'),
                    style: ElevatedButton.styleFrom(
                      minimumSize: const Size(double.infinity, 48),
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

  Widget _buildSectionHeader(String title) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 16),
      child: Text(
        title,
        style: const TextStyle(
          fontSize: 20,
          fontWeight: FontWeight.bold,
        ),
      ),
    );
  }
}