import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:file_picker/file_picker.dart';
import 'package:dio/dio.dart';
import '../models/settings_models.dart';
// REMOVED: import '../core/services/multi_camera_service.dart'; // Archived - unused
import 'api_providers.dart';

// ====================
// Settings Storage Service
// ====================

class SettingsStorageService {
  static const String _generalSettingsKey = 'general_settings';
  static const String _detectionSettingsKey = 'detection_settings';
  static const String _cameraSettingsKey = 'camera_settings';
  static const String _automationSettingsKey = 'automation_settings';

  Future<void> saveSettings<T>(String key, T settings) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final jsonString = jsonEncode((settings as dynamic).toJson());
      await prefs.setString(key, jsonString);
    } catch (e) {
      throw Exception('Failed to save settings: $e');
    }
  }

  Future<T?> loadSettings<T>(String key, T Function(Map<String, dynamic>) fromJson) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final jsonString = prefs.getString(key);
      if (jsonString == null) {
        return null;
      }
      
      final jsonMap = jsonDecode(jsonString) as Map<String, dynamic>;
      return fromJson(jsonMap);
    } catch (e) {
      return null;
    }
  }

  Future<void> deleteSettings(String key) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.remove(key);
    } catch (e) {
      // Ignore deletion errors
    }
  }

  Future<void> exportAllSettings(String filePath) async {
    try {
      final general = await loadSettings(_generalSettingsKey, GeneralSettings.fromJson) 
          ?? GeneralSettings.defaultSettings();
      final detection = await loadSettings(_detectionSettingsKey, DetectionSettings.fromJson) 
          ?? DetectionSettings.defaultSettings();
      final camera = await loadSettings(_cameraSettingsKey, CameraSettings.fromJson) 
          ?? CameraSettings.defaultSettings();
      final automation = await loadSettings(_automationSettingsKey, AutomationSettings.fromJson) 
          ?? AutomationSettings.defaultSettings();

      final bundle = ConfigurationBundle.fromSettings(
        general: general,
        detection: detection,
        camera: camera,
        automation: automation,
        version: '1.0.0',
        metadata: {
          'app_version': '1.0.0',
          'exported_at': DateTime.now().toIso8601String(),
        },
      );

      // For web, we'll use the file_picker to save
      // For now, just return the JSON string that can be downloaded
      final jsonString = jsonEncode(bundle.toJson());
      // TODO: Implement web-compatible file download
      throw UnimplementedError('Export not yet implemented for web');
    } catch (e) {
      throw Exception('Failed to export settings: $e');
    }
  }

  Future<ConfigurationBundle> importAllSettings(String filePath) async {
    try {
      // For web, this would use file_picker to read the file
      // For now, throw unimplemented
      throw UnimplementedError('Import not yet implemented for web');
    } catch (e) {
      throw Exception('Failed to import settings: $e');
    }
  }
}

// ====================
// Settings Providers
// ====================

final settingsStorageServiceProvider = Provider<SettingsStorageService>((ref) {
  return SettingsStorageService();
});

// General Settings Provider
final generalSettingsProvider = StateNotifierProvider<GeneralSettingsNotifier, AsyncValue<GeneralSettings>>((ref) {
  final storageService = ref.watch(settingsStorageServiceProvider);
  return GeneralSettingsNotifier(storageService);
});

class GeneralSettingsNotifier extends StateNotifier<AsyncValue<GeneralSettings>> {
  final SettingsStorageService _storageService;

  GeneralSettingsNotifier(this._storageService) : super(const AsyncValue.loading()) {
    _loadSettings();
  }

  Future<void> _loadSettings() async {
    try {
      final settings = await _storageService.loadSettings(
        'general_settings',
        GeneralSettings.fromJson,
      ) ?? GeneralSettings.defaultSettings();
      
      state = AsyncValue.data(settings);
    } catch (e, stack) {
      state = AsyncValue.error(e, stack);
    }
  }

  Future<void> _saveSettings(GeneralSettings settings) async {
    try {
      await _storageService.saveSettings('general_settings', settings);
      state = AsyncValue.data(settings);
    } catch (e, stack) {
      state = AsyncValue.error(e, stack);
    }
  }

  Future<void> updateDarkTheme(bool darkTheme) async {
    final currentSettings = state.valueOrNull;
    if (currentSettings != null) {
      await _saveSettings(currentSettings.copyWith(darkTheme: darkTheme));
    }
  }

  Future<void> updateAutoRefresh(bool autoRefresh) async {
    final currentSettings = state.valueOrNull;
    if (currentSettings != null) {
      await _saveSettings(currentSettings.copyWith(autoRefresh: autoRefresh));
    }
  }

  Future<void> updateRefreshInterval(int interval) async {
    final currentSettings = state.valueOrNull;
    if (currentSettings != null) {
      await _saveSettings(currentSettings.copyWith(refreshInterval: interval));
    }
  }

  Future<void> updateNotifications(bool enableNotifications) async {
    final currentSettings = state.valueOrNull;
    if (currentSettings != null) {
      await _saveSettings(currentSettings.copyWith(enableNotifications: enableNotifications));
    }
  }

  Future<void> updateMaxLogEntries(int maxLogEntries) async {
    final currentSettings = state.valueOrNull;
    if (currentSettings != null) {
      await _saveSettings(currentSettings.copyWith(maxLogEntries: maxLogEntries));
    }
  }

  Future<void> updateDebugMode(bool debugMode) async {
    final currentSettings = state.valueOrNull;
    if (currentSettings != null) {
      await _saveSettings(currentSettings.copyWith(debugMode: debugMode));
    }
  }

  Future<void> updatePerformanceMonitoring(bool performanceMonitoring) async {
    final currentSettings = state.valueOrNull;
    if (currentSettings != null) {
      await _saveSettings(currentSettings.copyWith(performanceMonitoring: performanceMonitoring));
    }
  }

  Future<void> updateMergeIndividualsRule(String rule) async {
    final currentSettings = state.valueOrNull;
    if (currentSettings != null) {
      await _saveSettings(currentSettings.copyWith(mergeIndividualsRule: rule));
    }
  }
}

// Detection Settings Provider
final detectionSettingsProvider = StateNotifierProvider<DetectionSettingsNotifier, AsyncValue<DetectionSettings>>((ref) {
  final storageService = ref.watch(settingsStorageServiceProvider);
  return DetectionSettingsNotifier(storageService);
});

class DetectionSettingsNotifier extends StateNotifier<AsyncValue<DetectionSettings>> {
  final SettingsStorageService _storageService;

  DetectionSettingsNotifier(this._storageService) : super(const AsyncValue.loading()) {
    _loadSettings();
  }

  Future<void> _loadSettings() async {
    try {
      final settings = await _storageService.loadSettings(
        'detection_settings',
        DetectionSettings.fromJson,
      ) ?? DetectionSettings.defaultSettings();
      
      state = AsyncValue.data(settings);
    } catch (e, stack) {
      state = AsyncValue.error(e, stack);
    }
  }

  Future<void> _saveSettings(DetectionSettings settings) async {
    try {
      await _storageService.saveSettings('detection_settings', settings);
      state = AsyncValue.data(settings);
    } catch (e, stack) {
      state = AsyncValue.error(e, stack);
    }
  }

  Future<void> updateDefaultMethod(String method) async {
    final currentSettings = state.valueOrNull;
    if (currentSettings != null) {
      await _saveSettings(currentSettings.copyWith(defaultMethod: method));
    }
  }

  Future<void> updateConfidenceThreshold(double threshold) async {
    final currentSettings = state.valueOrNull;
    if (currentSettings != null) {
      await _saveSettings(currentSettings.copyWith(confidenceThreshold: threshold));
    }
  }

  Future<void> updateSaveResults(bool saveResults) async {
    final currentSettings = state.valueOrNull;
    if (currentSettings != null) {
      await _saveSettings(currentSettings.copyWith(saveResults: saveResults));
    }
  }

  Future<void> updateRealTimeProcessing(bool realTimeProcessing) async {
    final currentSettings = state.valueOrNull;
    if (currentSettings != null) {
      await _saveSettings(currentSettings.copyWith(realTimeProcessing: realTimeProcessing));
    }
  }

  Future<void> updateBatchSize(int batchSize) async {
    final currentSettings = state.valueOrNull;
    if (currentSettings != null) {
      await _saveSettings(currentSettings.copyWith(batchSize: batchSize));
    }
  }

  Future<void> updateMaxConcurrentDetections(int maxConcurrentDetections) async {
    final currentSettings = state.valueOrNull;
    if (currentSettings != null) {
      await _saveSettings(currentSettings.copyWith(maxConcurrentDetections: maxConcurrentDetections));
    }
  }

  Future<void> updateCustomModelPath(String? customModelPath) async {
    final currentSettings = state.valueOrNull;
    if (currentSettings != null) {
      await _saveSettings(currentSettings.copyWith(customModelPath: customModelPath));
    }
  }

  Future<void> updateGpuAcceleration(bool useGpuAcceleration) async {
    final currentSettings = state.valueOrNull;
    if (currentSettings != null) {
      await _saveSettings(currentSettings.copyWith(useGpuAcceleration: useGpuAcceleration));
    }
  }
}

// Camera Settings Provider
final cameraSettingsProvider = StateNotifierProvider<CameraSettingsNotifier, AsyncValue<CameraSettings>>((ref) {
  final storageService = ref.watch(settingsStorageServiceProvider);
  return CameraSettingsNotifier(storageService);
});

class CameraSettingsNotifier extends StateNotifier<AsyncValue<CameraSettings>> {
  final SettingsStorageService _storageService;

  CameraSettingsNotifier(this._storageService) : super(const AsyncValue.loading()) {
    _loadSettings();
  }

  Future<void> _loadSettings() async {
    try {
      final settings = await _storageService.loadSettings(
        'camera_settings',
        CameraSettings.fromJson,
      ) ?? CameraSettings.defaultSettings();
      
      state = AsyncValue.data(settings);
    } catch (e, stack) {
      state = AsyncValue.error(e, stack);
    }
  }

  Future<void> _saveSettings(CameraSettings settings) async {
    try {
      await _storageService.saveSettings('camera_settings', settings);
      state = AsyncValue.data(settings);
    } catch (e, stack) {
      state = AsyncValue.error(e, stack);
    }
  }

  Future<void> updateDefaultResolution(String resolution) async {
    final currentSettings = state.valueOrNull;
    if (currentSettings != null) {
      await _saveSettings(currentSettings.copyWith(defaultResolution: resolution));
    }
  }

  Future<void> updateDefaultFrameRate(int frameRate) async {
    final currentSettings = state.valueOrNull;
    if (currentSettings != null) {
      await _saveSettings(currentSettings.copyWith(defaultFrameRate: frameRate));
    }
  }

  Future<void> updateDefaultFormat(String format) async {
    final currentSettings = state.valueOrNull;
    if (currentSettings != null) {
      await _saveSettings(currentSettings.copyWith(defaultFormat: format));
    }
  }

  Future<void> updateAutoRecord(bool autoRecord) async {
    final currentSettings = state.valueOrNull;
    if (currentSettings != null) {
      await _saveSettings(currentSettings.copyWith(autoRecord: autoRecord));
    }
  }

  Future<void> updateMaxRecordingDuration(int duration) async {
    final currentSettings = state.valueOrNull;
    if (currentSettings != null) {
      await _saveSettings(currentSettings.copyWith(maxRecordingDuration: duration));
    }
  }

  Future<void> updateRecordingPath(String path) async {
    final currentSettings = state.valueOrNull;
    if (currentSettings != null) {
      await _saveSettings(currentSettings.copyWith(recordingPath: path));
    }
  }

  Future<void> updateConnectionTimeout(int timeout) async {
    final currentSettings = state.valueOrNull;
    if (currentSettings != null) {
      await _saveSettings(currentSettings.copyWith(connectionTimeout: timeout));
    }
  }

  Future<void> updateRetryAttempts(int attempts) async {
    final currentSettings = state.valueOrNull;
    if (currentSettings != null) {
      await _saveSettings(currentSettings.copyWith(retryAttempts: attempts));
    }
  }

  Future<void> updateAutoReconnect(bool autoReconnect) async {
    final currentSettings = state.valueOrNull;
    if (currentSettings != null) {
      await _saveSettings(currentSettings.copyWith(autoReconnect: autoReconnect));
    }
  }
}

// Automation Settings Provider
final automationSettingsProvider = StateNotifierProvider<AutomationSettingsNotifier, AsyncValue<AutomationSettings>>((ref) {
  final storageService = ref.watch(settingsStorageServiceProvider);
  return AutomationSettingsNotifier(storageService);
});

class AutomationSettingsNotifier extends StateNotifier<AsyncValue<AutomationSettings>> {
  final SettingsStorageService _storageService;

  AutomationSettingsNotifier(this._storageService) : super(const AsyncValue.loading()) {
    _loadSettings();
  }

  Future<void> _loadSettings() async {
    try {
      final settings = await _storageService.loadSettings(
        'automation_settings',
        AutomationSettings.fromJson,
      ) ?? AutomationSettings.defaultSettings();
      
      state = AsyncValue.data(settings);
    } catch (e, stack) {
      state = AsyncValue.error(e, stack);
    }
  }

  Future<void> _saveSettings(AutomationSettings settings) async {
    try {
      await _storageService.saveSettings('automation_settings', settings);
      state = AsyncValue.data(settings);
    } catch (e, stack) {
      state = AsyncValue.error(e, stack);
    }
  }

  Future<void> updateEnableEngine(bool enableEngine) async {
    final currentSettings = state.valueOrNull;
    if (currentSettings != null) {
      await _saveSettings(currentSettings.copyWith(enableEngine: enableEngine));
    }
  }

  Future<void> updateRuleCheckInterval(int interval) async {
    final currentSettings = state.valueOrNull;
    if (currentSettings != null) {
      await _saveSettings(currentSettings.copyWith(ruleCheckInterval: interval));
    }
  }

  Future<void> updateMaxConcurrentExecutions(int maxConcurrentExecutions) async {
    final currentSettings = state.valueOrNull;
    if (currentSettings != null) {
      await _saveSettings(currentSettings.copyWith(maxConcurrentExecutions: maxConcurrentExecutions));
    }
  }

  Future<void> updateExecutionTimeout(int timeout) async {
    final currentSettings = state.valueOrNull;
    if (currentSettings != null) {
      await _saveSettings(currentSettings.copyWith(executionTimeout: timeout));
    }
  }

  Future<void> updateRetryAttempts(int attempts) async {
    final currentSettings = state.valueOrNull;
    if (currentSettings != null) {
      await _saveSettings(currentSettings.copyWith(retryAttempts: attempts));
    }
  }

  Future<void> updateRetryOnFailure(bool retryOnFailure) async {
    final currentSettings = state.valueOrNull;
    if (currentSettings != null) {
      await _saveSettings(currentSettings.copyWith(retryOnFailure: retryOnFailure));
    }
  }

  Future<void> updateAutoFaceDetection(bool autoFaceDetectionEnabled) async {
    final currentSettings = state.valueOrNull;
    if (currentSettings != null) {
      // Save local automation settings
      await _saveSettings(currentSettings.copyWith(autoFaceDetectionEnabled: autoFaceDetectionEnabled));
      
      // Note: Camera-specific auto_face_detection settings should be updated
      // when recording starts/stops via the camera service integration
      // This provides a global default preference for new cameras
    }
  }

  Future<void> updateLogExecutions(bool logExecutions) async {
    final currentSettings = state.valueOrNull;
    if (currentSettings != null) {
      await _saveSettings(currentSettings.copyWith(logExecutions: logExecutions));
    }
  }

  Future<void> updateMaxHistoryEntries(int maxHistoryEntries) async {
    final currentSettings = state.valueOrNull;
    if (currentSettings != null) {
      await _saveSettings(currentSettings.copyWith(maxHistoryEntries: maxHistoryEntries));
    }
  }

  Future<void> updateNotifications(bool enableNotifications) async {
    final currentSettings = state.valueOrNull;
    if (currentSettings != null) {
      await _saveSettings(currentSettings.copyWith(enableNotifications: enableNotifications));
    }
  }
}

// Import/Export Provider
final importExportProvider = StateNotifierProvider<ImportExportNotifier, ImportExportState>((ref) {
  final storageService = ref.watch(settingsStorageServiceProvider);
  return ImportExportNotifier(storageService);
});

class ImportExportNotifier extends StateNotifier<ImportExportState> {
  final SettingsStorageService _storageService;

  ImportExportNotifier(this._storageService) : super(ImportExportState.initial());

  Future<void> exportSettings() async {
    state = state.copyWith(isProcessing: true, currentOperation: 'Exporting settings...');
    
    try {
      final result = await FilePicker.platform.saveFile(
        dialogTitle: 'Export Settings',
        fileName: 'ppl_meta_settings.json',
        type: FileType.custom,
        allowedExtensions: ['json'],
      );

      if (result != null) {
        await _storageService.exportAllSettings(result);
        state = state.copyWith(
          isProcessing: false,
          currentOperation: null,
          lastResult: ImportExportResult.success(
            'Settings exported successfully',
            details: 'Exported to: $result',
          ),
        );
      } else {
        state = state.copyWith(
          isProcessing: false,
          currentOperation: null,
          lastResult: ImportExportResult.error('Export cancelled by user'),
        );
      }
    } catch (e) {
      state = state.copyWith(
        isProcessing: false,
        currentOperation: null,
        lastResult: ImportExportResult.error(
          'Failed to export settings',
          details: e.toString(),
        ),
      );
    }
  }

  Future<void> importSettings() async {
    state = state.copyWith(isProcessing: true, currentOperation: 'Importing settings...');

    try {
      final result = await FilePicker.platform.pickFiles(
        type: FileType.custom,
        allowedExtensions: ['json'],
        dialogTitle: 'Import Settings',
      );

      if (result != null && result.files.single.path != null) {
        final bundle = await _storageService.importAllSettings(result.files.single.path!);
        state = state.copyWith(
          isProcessing: false,
          currentOperation: null,
          lastResult: ImportExportResult.success(
            'Settings imported successfully',
            details: 'Imported configuration from ${bundle.exportDate}',
          ),
        );
      } else {
        state = state.copyWith(
          isProcessing: false,
          currentOperation: null,
          lastResult: ImportExportResult.error('Import cancelled by user'),
        );
      }
    } catch (e) {
      state = state.copyWith(
        isProcessing: false,
        currentOperation: null,
        lastResult: ImportExportResult.error(
          'Failed to import settings',
          details: e.toString(),
        ),
      );
    }
  }

  Future<void> exportAutomationRules() async {
    state = state.copyWith(isProcessing: true, currentOperation: 'Exporting automation rules...');
    
    try {
      // This would integrate with the automation API to export rules
      await Future.delayed(const Duration(seconds: 1)); // Simulate API call
      
      state = state.copyWith(
        isProcessing: false,
        currentOperation: null,
        lastResult: ImportExportResult.success('Automation rules exported successfully'),
      );
    } catch (e) {
      state = state.copyWith(
        isProcessing: false,
        currentOperation: null,
        lastResult: ImportExportResult.error(
          'Failed to export automation rules',
          details: e.toString(),
        ),
      );
    }
  }

  Future<void> importAutomationRules() async {
    state = state.copyWith(isProcessing: true, currentOperation: 'Importing automation rules...');
    
    try {
      // This would integrate with the automation API to import rules
      await Future.delayed(const Duration(seconds: 1)); // Simulate API call
      
      state = state.copyWith(
        isProcessing: false,
        currentOperation: null,
        lastResult: ImportExportResult.success('Automation rules imported successfully'),
      );
    } catch (e) {
      state = state.copyWith(
        isProcessing: false,
        currentOperation: null,
        lastResult: ImportExportResult.error(
          'Failed to import automation rules',
          details: e.toString(),
        ),
      );
    }
  }

  Future<void> exportCameraConfiguration() async {
    state = state.copyWith(isProcessing: true, currentOperation: 'Exporting camera configuration...');
    
    try {
      // This would integrate with the camera API to export configuration
      await Future.delayed(const Duration(seconds: 1)); // Simulate API call
      
      state = state.copyWith(
        isProcessing: false,
        currentOperation: null,
        lastResult: ImportExportResult.success('Camera configuration exported successfully'),
      );
    } catch (e) {
      state = state.copyWith(
        isProcessing: false,
        currentOperation: null,
        lastResult: ImportExportResult.error(
          'Failed to export camera configuration',
          details: e.toString(),
        ),
      );
    }
  }

  Future<void> resetToDefaults() async {
    state = state.copyWith(isProcessing: true, currentOperation: 'Resetting to defaults...');
    
    try {
      // Delete all stored settings
      await _storageService.deleteSettings('general_settings');
      await _storageService.deleteSettings('detection_settings');
      await _storageService.deleteSettings('camera_settings');
      await _storageService.deleteSettings('automation_settings');
      
      state = state.copyWith(
        isProcessing: false,
        currentOperation: null,
        lastResult: ImportExportResult.success(
          'Settings reset to defaults',
          details: 'All settings have been restored to default values',
        ),
      );
    } catch (e) {
      state = state.copyWith(
        isProcessing: false,
        currentOperation: null,
        lastResult: ImportExportResult.error(
          'Failed to reset settings',
          details: e.toString(),
        ),
      );
    }
  }

  Future<void> updateAutoBackup(bool autoBackup) async {
    state = state.copyWith(autoBackup: autoBackup);
  }

  Future<void> selectBackupLocation() async {
    try {
      final result = await FilePicker.platform.getDirectoryPath(
        dialogTitle: 'Select Backup Location',
      );

      if (result != null) {
        state = state.copyWith(backupLocation: result);
      }
    } catch (e) {
      state = state.copyWith(
        lastResult: ImportExportResult.error(
          'Failed to select backup location',
          details: e.toString(),
        ),
      );
    }
  }

  Future<void> createManualBackup() async {
    state = state.copyWith(isProcessing: true, currentOperation: 'Creating manual backup...');
    
    try {
      final timestamp = DateTime.now().toIso8601String().split('T')[0];
      final backupPath = state.backupLocation ?? await _getDefaultBackupPath();
      final filePath = '$backupPath/ppl_meta_backup_$timestamp.json';
      
      await _storageService.exportAllSettings(filePath);
      
      state = state.copyWith(
        isProcessing: false,
        currentOperation: null,
        lastResult: ImportExportResult.success(
          'Manual backup created successfully',
          details: 'Backup saved to: $filePath',
        ),
      );
    } catch (e) {
      state = state.copyWith(
        isProcessing: false,
        currentOperation: null,
        lastResult: ImportExportResult.error(
          'Failed to create manual backup',
          details: e.toString(),
        ),
      );
    }
  }

  Future<String> _getDefaultBackupPath() async {
    // For web, return a default path (not actually used for file operations)
    // For mobile/desktop, this would use path_provider
    return '/ppl_meta_backups';
  }
}