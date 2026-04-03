// Settings models for the PPL Meta frontend application
import 'package:json_annotation/json_annotation.dart';

part 'settings_models.g.dart';

// ====================
// General Settings
// ====================

@JsonSerializable()
class GeneralSettings {
  final bool darkTheme;
  final bool autoRefresh;
  final int refreshInterval; // seconds
  final bool enableNotifications;
  final int maxLogEntries;
  final bool debugMode;
  final bool performanceMonitoring;
  final String mergeIndividualsRule; // 'none', 'semi', or 'auto'
  final double mergeIndividualsThreshold; // 0.0-1.0

  GeneralSettings({
    required this.darkTheme,
    required this.autoRefresh,
    required this.refreshInterval,
    required this.enableNotifications,
    required this.maxLogEntries,
    required this.debugMode,
    required this.performanceMonitoring,
    required this.mergeIndividualsRule,
    required this.mergeIndividualsThreshold,
  });

  factory GeneralSettings.fromJson(Map<String, dynamic> json) =>
      _$GeneralSettingsFromJson(json);

  Map<String, dynamic> toJson() => _$GeneralSettingsToJson(this);

  factory GeneralSettings.defaultSettings() {
    return GeneralSettings(
      darkTheme: false,
      autoRefresh: true,
      refreshInterval: 30,
      enableNotifications: true,
      maxLogEntries: 1000,
      debugMode: false,
      performanceMonitoring: true,
      mergeIndividualsRule: 'semi',
      mergeIndividualsThreshold: 0.70,
    );
  }

  GeneralSettings copyWith({
    bool? darkTheme,
    bool? autoRefresh,
    int? refreshInterval,
    bool? enableNotifications,
    int? maxLogEntries,
    bool? debugMode,
    bool? performanceMonitoring,
    String? mergeIndividualsRule,
    double? mergeIndividualsThreshold,
  }) {
    return GeneralSettings(
      darkTheme: darkTheme ?? this.darkTheme,
      autoRefresh: autoRefresh ?? this.autoRefresh,
      refreshInterval: refreshInterval ?? this.refreshInterval,
      enableNotifications: enableNotifications ?? this.enableNotifications,
      maxLogEntries: maxLogEntries ?? this.maxLogEntries,
      debugMode: debugMode ?? this.debugMode,
      performanceMonitoring: performanceMonitoring ?? this.performanceMonitoring,
      mergeIndividualsRule: mergeIndividualsRule ?? this.mergeIndividualsRule,
      mergeIndividualsThreshold:
          mergeIndividualsThreshold ?? this.mergeIndividualsThreshold,
    );
  }
}

// ====================
// Detection Settings
// ====================

@JsonSerializable()
class DetectionSettings {
  final String defaultMethod;
  final List<String> availableMethods;
  final double confidenceThreshold;
  final bool saveResults;
  final bool realTimeProcessing;
  final int batchSize;
  final int maxConcurrentDetections;
  final String? customModelPath;
  final bool useGpuAcceleration;

  DetectionSettings({
    required this.defaultMethod,
    required this.availableMethods,
    required this.confidenceThreshold,
    required this.saveResults,
    required this.realTimeProcessing,
    required this.batchSize,
    required this.maxConcurrentDetections,
    this.customModelPath,
    required this.useGpuAcceleration,
  });

  factory DetectionSettings.fromJson(Map<String, dynamic> json) =>
      _$DetectionSettingsFromJson(json);

  Map<String, dynamic> toJson() => _$DetectionSettingsToJson(this);

  factory DetectionSettings.defaultSettings() {
    return DetectionSettings(
      defaultMethod: 'opencv',
      availableMethods: ['opencv', 'dlib', 'mtcnn', 'retinaface'],
      confidenceThreshold: 0.7,
      saveResults: true,
      realTimeProcessing: true,
      batchSize: 10,
      maxConcurrentDetections: 4,
      customModelPath: null,
      useGpuAcceleration: false,
    );
  }

  DetectionSettings copyWith({
    String? defaultMethod,
    List<String>? availableMethods,
    double? confidenceThreshold,
    bool? saveResults,
    bool? realTimeProcessing,
    int? batchSize,
    int? maxConcurrentDetections,
    String? customModelPath,
    bool? useGpuAcceleration,
  }) {
    return DetectionSettings(
      defaultMethod: defaultMethod ?? this.defaultMethod,
      availableMethods: availableMethods ?? this.availableMethods,
      confidenceThreshold: confidenceThreshold ?? this.confidenceThreshold,
      saveResults: saveResults ?? this.saveResults,
      realTimeProcessing: realTimeProcessing ?? this.realTimeProcessing,
      batchSize: batchSize ?? this.batchSize,
      maxConcurrentDetections: maxConcurrentDetections ?? this.maxConcurrentDetections,
      customModelPath: customModelPath ?? this.customModelPath,
      useGpuAcceleration: useGpuAcceleration ?? this.useGpuAcceleration,
    );
  }
}

// ====================
// Camera Settings
// ====================

@JsonSerializable()
class CameraSettings {
  final String defaultResolution;
  final List<String> availableResolutions;
  final int defaultFrameRate;
  final List<int> availableFrameRates;
  final String defaultFormat;
  final List<String> availableFormats;
  final bool autoRecord;
  final int maxRecordingDuration; // minutes
  final String recordingPath;
  final int connectionTimeout; // seconds
  final int retryAttempts;
  final bool autoReconnect;

  CameraSettings({
    required this.defaultResolution,
    required this.availableResolutions,
    required this.defaultFrameRate,
    required this.availableFrameRates,
    required this.defaultFormat,
    required this.availableFormats,
    required this.autoRecord,
    required this.maxRecordingDuration,
    required this.recordingPath,
    required this.connectionTimeout,
    required this.retryAttempts,
    required this.autoReconnect,
  });

  factory CameraSettings.fromJson(Map<String, dynamic> json) =>
      _$CameraSettingsFromJson(json);

  Map<String, dynamic> toJson() => _$CameraSettingsToJson(this);

  factory CameraSettings.defaultSettings() {
    return CameraSettings(
      defaultResolution: '1920x1080',
      availableResolutions: ['640x480', '1280x720', '1920x1080', '2560x1440', '3840x2160'],
      defaultFrameRate: 30,
      availableFrameRates: [15, 24, 30, 60],
      defaultFormat: 'mp4',
      availableFormats: ['mp4', 'avi', 'mov', 'mkv'],
      autoRecord: false,
      maxRecordingDuration: 60,
      recordingPath: './recordings',
      connectionTimeout: 30,
      retryAttempts: 3,
      autoReconnect: true,
    );
  }

  CameraSettings copyWith({
    String? defaultResolution,
    List<String>? availableResolutions,
    int? defaultFrameRate,
    List<int>? availableFrameRates,
    String? defaultFormat,
    List<String>? availableFormats,
    bool? autoRecord,
    int? maxRecordingDuration,
    String? recordingPath,
    int? connectionTimeout,
    int? retryAttempts,
    bool? autoReconnect,
  }) {
    return CameraSettings(
      defaultResolution: defaultResolution ?? this.defaultResolution,
      availableResolutions: availableResolutions ?? this.availableResolutions,
      defaultFrameRate: defaultFrameRate ?? this.defaultFrameRate,
      availableFrameRates: availableFrameRates ?? this.availableFrameRates,
      defaultFormat: defaultFormat ?? this.defaultFormat,
      availableFormats: availableFormats ?? this.availableFormats,
      autoRecord: autoRecord ?? this.autoRecord,
      maxRecordingDuration: maxRecordingDuration ?? this.maxRecordingDuration,
      recordingPath: recordingPath ?? this.recordingPath,
      connectionTimeout: connectionTimeout ?? this.connectionTimeout,
      retryAttempts: retryAttempts ?? this.retryAttempts,
      autoReconnect: autoReconnect ?? this.autoReconnect,
    );
  }
}

// ====================
// Automation Settings
// ====================

@JsonSerializable()
class AutomationSettings {
  final bool enableEngine;
  final int ruleCheckInterval; // seconds
  final int maxConcurrentExecutions;
  final int executionTimeout; // seconds
  final int retryAttempts;
  final bool retryOnFailure;
  final bool logExecutions;
  final int maxHistoryEntries;
  final bool enableNotifications;
  final bool autoFaceDetectionEnabled;
  final bool notificationsEnabled;

  AutomationSettings({
    required this.enableEngine,
    required this.ruleCheckInterval,
    required this.maxConcurrentExecutions,
    required this.executionTimeout,
    required this.retryAttempts,
    required this.retryOnFailure,
    required this.logExecutions,
    required this.maxHistoryEntries,
    required this.enableNotifications,
    required this.autoFaceDetectionEnabled,
    required this.notificationsEnabled,
  });

  factory AutomationSettings.fromJson(Map<String, dynamic> json) =>
      _$AutomationSettingsFromJson(json);

  Map<String, dynamic> toJson() => _$AutomationSettingsToJson(this);

  factory AutomationSettings.defaultSettings() {
    return AutomationSettings(
      enableEngine: true,
      ruleCheckInterval: 10,
      maxConcurrentExecutions: 5,
      executionTimeout: 300,
      retryAttempts: 2,
      retryOnFailure: true,
      logExecutions: true,
      maxHistoryEntries: 1000,
      enableNotifications: true,
      autoFaceDetectionEnabled: false,
      notificationsEnabled: true,
    );
  }

  AutomationSettings copyWith({
    bool? enableEngine,
    int? ruleCheckInterval,
    int? maxConcurrentExecutions,
    int? executionTimeout,
    int? retryAttempts,
    bool? retryOnFailure,
    bool? logExecutions,
    int? maxHistoryEntries,
    bool? enableNotifications,
    bool? autoFaceDetectionEnabled,
    bool? notificationsEnabled,
  }) {
    return AutomationSettings(
      enableEngine: enableEngine ?? this.enableEngine,
      ruleCheckInterval: ruleCheckInterval ?? this.ruleCheckInterval,
      maxConcurrentExecutions: maxConcurrentExecutions ?? this.maxConcurrentExecutions,
      executionTimeout: executionTimeout ?? this.executionTimeout,
      retryAttempts: retryAttempts ?? this.retryAttempts,
      retryOnFailure: retryOnFailure ?? this.retryOnFailure,
      logExecutions: logExecutions ?? this.logExecutions,
      maxHistoryEntries: maxHistoryEntries ?? this.maxHistoryEntries,
      enableNotifications: enableNotifications ?? this.enableNotifications,
      autoFaceDetectionEnabled: autoFaceDetectionEnabled ?? this.autoFaceDetectionEnabled,
      notificationsEnabled: notificationsEnabled ?? this.notificationsEnabled,
    );
  }
}

// ====================
// Import/Export Models
// ====================

@JsonSerializable()
class ImportExportState {
  final bool isProcessing;
  final String? currentOperation;
  final ImportExportResult? lastResult;
  final bool autoBackup;
  final String? backupLocation;

  ImportExportState({
    required this.isProcessing,
    this.currentOperation,
    this.lastResult,
    required this.autoBackup,
    this.backupLocation,
  });

  factory ImportExportState.fromJson(Map<String, dynamic> json) =>
      _$ImportExportStateFromJson(json);

  Map<String, dynamic> toJson() => _$ImportExportStateToJson(this);

  factory ImportExportState.initial() {
    return ImportExportState(
      isProcessing: false,
      currentOperation: null,
      lastResult: null,
      autoBackup: false,
      backupLocation: null,
    );
  }

  ImportExportState copyWith({
    bool? isProcessing,
    String? currentOperation,
    ImportExportResult? lastResult,
    bool? autoBackup,
    String? backupLocation,
  }) {
    return ImportExportState(
      isProcessing: isProcessing ?? this.isProcessing,
      currentOperation: currentOperation,
      lastResult: lastResult ?? this.lastResult,
      autoBackup: autoBackup ?? this.autoBackup,
      backupLocation: backupLocation ?? this.backupLocation,
    );
  }
}

@JsonSerializable()
class ImportExportResult {
  final bool isSuccess;
  final String message;
  final String? details;
  final DateTime timestamp;

  ImportExportResult({
    required this.isSuccess,
    required this.message,
    this.details,
    required this.timestamp,
  });

  factory ImportExportResult.fromJson(Map<String, dynamic> json) =>
      _$ImportExportResultFromJson(json);

  Map<String, dynamic> toJson() => _$ImportExportResultToJson(this);

  factory ImportExportResult.success(String message, {String? details}) {
    return ImportExportResult(
      isSuccess: true,
      message: message,
      details: details,
      timestamp: DateTime.now(),
    );
  }

  factory ImportExportResult.error(String message, {String? details}) {
    return ImportExportResult(
      isSuccess: false,
      message: message,
      details: details,
      timestamp: DateTime.now(),
    );
  }
}

// ====================
// Configuration Bundle
// ====================

@JsonSerializable()
class ConfigurationBundle {
  final GeneralSettings general;
  final DetectionSettings detection;
  final CameraSettings camera;
  final AutomationSettings automation;
  final String version;
  final DateTime exportDate;
  final Map<String, dynamic>? metadata;

  ConfigurationBundle({
    required this.general,
    required this.detection,
    required this.camera,
    required this.automation,
    required this.version,
    required this.exportDate,
    this.metadata,
  });

  factory ConfigurationBundle.fromJson(Map<String, dynamic> json) =>
      _$ConfigurationBundleFromJson(json);

  Map<String, dynamic> toJson() => _$ConfigurationBundleToJson(this);

  factory ConfigurationBundle.fromSettings({
    required GeneralSettings general,
    required DetectionSettings detection,
    required CameraSettings camera,
    required AutomationSettings automation,
    String? version,
    Map<String, dynamic>? metadata,
  }) {
    return ConfigurationBundle(
      general: general,
      detection: detection,
      camera: camera,
      automation: automation,
      version: version ?? '1.0.0',
      exportDate: DateTime.now(),
      metadata: metadata,
    );
  }
}

// ====================
// Settings Validation
// ====================

class SettingsValidation {
  static ValidationResult validateGeneralSettings(GeneralSettings settings) {
    final errors = <String>[];

    if (settings.refreshInterval < 5) {
      errors.add('Refresh interval must be at least 5 seconds');
    }

    if (settings.maxLogEntries < 100) {
      errors.add('Max log entries must be at least 100');
    }

    return ValidationResult(
      isValid: errors.isEmpty,
      errors: errors,
    );
  }

  static ValidationResult validateDetectionSettings(DetectionSettings settings) {
    final errors = <String>[];

    if (settings.confidenceThreshold < 0.1 || settings.confidenceThreshold > 1.0) {
      errors.add('Confidence threshold must be between 0.1 and 1.0');
    }

    if (settings.batchSize < 1 || settings.batchSize > 100) {
      errors.add('Batch size must be between 1 and 100');
    }

    if (settings.maxConcurrentDetections < 1 || settings.maxConcurrentDetections > 20) {
      errors.add('Max concurrent detections must be between 1 and 20');
    }

    if (!settings.availableMethods.contains(settings.defaultMethod)) {
      errors.add('Default method must be one of the available methods');
    }

    return ValidationResult(
      isValid: errors.isEmpty,
      errors: errors,
    );
  }

  static ValidationResult validateCameraSettings(CameraSettings settings) {
    final errors = <String>[];

    if (!settings.availableResolutions.contains(settings.defaultResolution)) {
      errors.add('Default resolution must be one of the available resolutions');
    }

    if (!settings.availableFrameRates.contains(settings.defaultFrameRate)) {
      errors.add('Default frame rate must be one of the available frame rates');
    }

    if (!settings.availableFormats.contains(settings.defaultFormat)) {
      errors.add('Default format must be one of the available formats');
    }

    if (settings.maxRecordingDuration < 1 || settings.maxRecordingDuration > 1440) {
      errors.add('Max recording duration must be between 1 and 1440 minutes');
    }

    if (settings.connectionTimeout < 5 || settings.connectionTimeout > 300) {
      errors.add('Connection timeout must be between 5 and 300 seconds');
    }

    if (settings.retryAttempts < 0 || settings.retryAttempts > 10) {
      errors.add('Retry attempts must be between 0 and 10');
    }

    return ValidationResult(
      isValid: errors.isEmpty,
      errors: errors,
    );
  }

  static ValidationResult validateAutomationSettings(AutomationSettings settings) {
    final errors = <String>[];

    if (settings.ruleCheckInterval < 1 || settings.ruleCheckInterval > 3600) {
      errors.add('Rule check interval must be between 1 and 3600 seconds');
    }

    if (settings.maxConcurrentExecutions < 1 || settings.maxConcurrentExecutions > 50) {
      errors.add('Max concurrent executions must be between 1 and 50');
    }

    if (settings.executionTimeout < 10 || settings.executionTimeout > 3600) {
      errors.add('Execution timeout must be between 10 and 3600 seconds');
    }

    if (settings.retryAttempts < 0 || settings.retryAttempts > 10) {
      errors.add('Retry attempts must be between 0 and 10');
    }

    if (settings.maxHistoryEntries < 10 || settings.maxHistoryEntries > 10000) {
      errors.add('Max history entries must be between 10 and 10000');
    }

    return ValidationResult(
      isValid: errors.isEmpty,
      errors: errors,
    );
  }
}

// ====================
// Workflow Settings
// ====================

@JsonSerializable()
class WorkflowSettings {
  final double velocitySensitivity;
  final double minValue;
  final double maxValue;
  final String description;
  final String? recommendation;

  WorkflowSettings({
    required this.velocitySensitivity,
    required this.minValue,
    required this.maxValue,
    required this.description,
    this.recommendation,
  });

  factory WorkflowSettings.fromJson(Map<String, dynamic> json) =>
      _$WorkflowSettingsFromJson(json);

  Map<String, dynamic> toJson() => _$WorkflowSettingsToJson(this);

  factory WorkflowSettings.defaultSettings() {
    return WorkflowSettings(
      velocitySensitivity: 20.0,
      minValue: 5.0,
      maxValue: 50.0,
      description: 'Face tracking tolerance percentage for temporal grouping',
      recommendation: 'Recommended for normal walking speed (default)',
    );
  }

  WorkflowSettings copyWith({
    double? velocitySensitivity,
    double? minValue,
    double? maxValue,
    String? description,
    String? recommendation,
  }) {
    return WorkflowSettings(
      velocitySensitivity: velocitySensitivity ?? this.velocitySensitivity,
      minValue: minValue ?? this.minValue,
      maxValue: maxValue ?? this.maxValue,
      description: description ?? this.description,
      recommendation: recommendation ?? this.recommendation,
    );
  }

  String getRecommendationForValue(double value) {
    if (value < 10.0) {
      return 'Recommended for very slow-moving or stationary subjects';
    } else if (value < 15.0) {
      return 'Recommended for slow-moving subjects';
    } else if (value < 25.0) {
      return 'Recommended for normal walking speed (default)';
    } else if (value < 35.0) {
      return 'Recommended for fast-moving subjects or running';
    } else {
      return 'Recommended for very fast movement or sports scenarios';
    }
  }
}

class ValidationResult {
  final bool isValid;
  final List<String> errors;

  ValidationResult({
    required this.isValid,
    required this.errors,
  });

  String get errorMessage => errors.join('\n');
}