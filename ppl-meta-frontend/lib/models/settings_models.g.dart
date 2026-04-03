// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'settings_models.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

GeneralSettings _$GeneralSettingsFromJson(Map<String, dynamic> json) =>
    GeneralSettings(
      darkTheme: json['darkTheme'] as bool,
      autoRefresh: json['autoRefresh'] as bool,
      refreshInterval: (json['refreshInterval'] as num).toInt(),
      enableNotifications: json['enableNotifications'] as bool,
      maxLogEntries: (json['maxLogEntries'] as num).toInt(),
      debugMode: json['debugMode'] as bool,
      performanceMonitoring: json['performanceMonitoring'] as bool,
      mergeIndividualsRule: json['mergeIndividualsRule'] as String? ?? 'semi',
      mergeIndividualsThreshold:
          (json['mergeIndividualsThreshold'] as num?)?.toDouble() ?? 0.70,
    );

Map<String, dynamic> _$GeneralSettingsToJson(GeneralSettings instance) =>
    <String, dynamic>{
      'darkTheme': instance.darkTheme,
      'autoRefresh': instance.autoRefresh,
      'refreshInterval': instance.refreshInterval,
      'enableNotifications': instance.enableNotifications,
      'maxLogEntries': instance.maxLogEntries,
      'debugMode': instance.debugMode,
      'performanceMonitoring': instance.performanceMonitoring,
      'mergeIndividualsRule': instance.mergeIndividualsRule,
      'mergeIndividualsThreshold': instance.mergeIndividualsThreshold,
    };

DetectionSettings _$DetectionSettingsFromJson(Map<String, dynamic> json) =>
    DetectionSettings(
      defaultMethod: json['defaultMethod'] as String,
      availableMethods: (json['availableMethods'] as List<dynamic>)
          .map((e) => e as String)
          .toList(),
      confidenceThreshold: (json['confidenceThreshold'] as num).toDouble(),
      saveResults: json['saveResults'] as bool,
      realTimeProcessing: json['realTimeProcessing'] as bool,
      batchSize: (json['batchSize'] as num).toInt(),
      maxConcurrentDetections: (json['maxConcurrentDetections'] as num).toInt(),
      customModelPath: json['customModelPath'] as String?,
      useGpuAcceleration: json['useGpuAcceleration'] as bool,
    );

Map<String, dynamic> _$DetectionSettingsToJson(DetectionSettings instance) =>
    <String, dynamic>{
      'defaultMethod': instance.defaultMethod,
      'availableMethods': instance.availableMethods,
      'confidenceThreshold': instance.confidenceThreshold,
      'saveResults': instance.saveResults,
      'realTimeProcessing': instance.realTimeProcessing,
      'batchSize': instance.batchSize,
      'maxConcurrentDetections': instance.maxConcurrentDetections,
      'customModelPath': instance.customModelPath,
      'useGpuAcceleration': instance.useGpuAcceleration,
    };

CameraSettings _$CameraSettingsFromJson(Map<String, dynamic> json) =>
    CameraSettings(
      defaultResolution: json['defaultResolution'] as String,
      availableResolutions: (json['availableResolutions'] as List<dynamic>)
          .map((e) => e as String)
          .toList(),
      defaultFrameRate: (json['defaultFrameRate'] as num).toInt(),
      availableFrameRates: (json['availableFrameRates'] as List<dynamic>)
          .map((e) => (e as num).toInt())
          .toList(),
      defaultFormat: json['defaultFormat'] as String,
      availableFormats: (json['availableFormats'] as List<dynamic>)
          .map((e) => e as String)
          .toList(),
      autoRecord: json['autoRecord'] as bool,
      maxRecordingDuration: (json['maxRecordingDuration'] as num).toInt(),
      recordingPath: json['recordingPath'] as String,
      connectionTimeout: (json['connectionTimeout'] as num).toInt(),
      retryAttempts: (json['retryAttempts'] as num).toInt(),
      autoReconnect: json['autoReconnect'] as bool,
    );

Map<String, dynamic> _$CameraSettingsToJson(CameraSettings instance) =>
    <String, dynamic>{
      'defaultResolution': instance.defaultResolution,
      'availableResolutions': instance.availableResolutions,
      'defaultFrameRate': instance.defaultFrameRate,
      'availableFrameRates': instance.availableFrameRates,
      'defaultFormat': instance.defaultFormat,
      'availableFormats': instance.availableFormats,
      'autoRecord': instance.autoRecord,
      'maxRecordingDuration': instance.maxRecordingDuration,
      'recordingPath': instance.recordingPath,
      'connectionTimeout': instance.connectionTimeout,
      'retryAttempts': instance.retryAttempts,
      'autoReconnect': instance.autoReconnect,
    };

AutomationSettings _$AutomationSettingsFromJson(Map<String, dynamic> json) =>
    AutomationSettings(
      enableEngine: json['enableEngine'] as bool,
      ruleCheckInterval: (json['ruleCheckInterval'] as num).toInt(),
      maxConcurrentExecutions: (json['maxConcurrentExecutions'] as num).toInt(),
      executionTimeout: (json['executionTimeout'] as num).toInt(),
      retryAttempts: (json['retryAttempts'] as num).toInt(),
      retryOnFailure: json['retryOnFailure'] as bool,
      logExecutions: json['logExecutions'] as bool,
      maxHistoryEntries: (json['maxHistoryEntries'] as num).toInt(),
      enableNotifications: json['enableNotifications'] as bool,
      autoFaceDetectionEnabled: json['autoFaceDetectionEnabled'] as bool,
      notificationsEnabled: json['notificationsEnabled'] as bool,
    );

Map<String, dynamic> _$AutomationSettingsToJson(AutomationSettings instance) =>
    <String, dynamic>{
      'enableEngine': instance.enableEngine,
      'ruleCheckInterval': instance.ruleCheckInterval,
      'maxConcurrentExecutions': instance.maxConcurrentExecutions,
      'executionTimeout': instance.executionTimeout,
      'retryAttempts': instance.retryAttempts,
      'retryOnFailure': instance.retryOnFailure,
      'logExecutions': instance.logExecutions,
      'maxHistoryEntries': instance.maxHistoryEntries,
      'enableNotifications': instance.enableNotifications,
      'autoFaceDetectionEnabled': instance.autoFaceDetectionEnabled,
      'notificationsEnabled': instance.notificationsEnabled,
    };

ImportExportState _$ImportExportStateFromJson(Map<String, dynamic> json) =>
    ImportExportState(
      isProcessing: json['isProcessing'] as bool,
      currentOperation: json['currentOperation'] as String?,
      lastResult: json['lastResult'] == null
          ? null
          : ImportExportResult.fromJson(
              json['lastResult'] as Map<String, dynamic>),
      autoBackup: json['autoBackup'] as bool,
      backupLocation: json['backupLocation'] as String?,
    );

Map<String, dynamic> _$ImportExportStateToJson(ImportExportState instance) =>
    <String, dynamic>{
      'isProcessing': instance.isProcessing,
      'currentOperation': instance.currentOperation,
      'lastResult': instance.lastResult,
      'autoBackup': instance.autoBackup,
      'backupLocation': instance.backupLocation,
    };

ImportExportResult _$ImportExportResultFromJson(Map<String, dynamic> json) =>
    ImportExportResult(
      isSuccess: json['isSuccess'] as bool,
      message: json['message'] as String,
      details: json['details'] as String?,
      timestamp: DateTime.parse(json['timestamp'] as String),
    );

Map<String, dynamic> _$ImportExportResultToJson(ImportExportResult instance) =>
    <String, dynamic>{
      'isSuccess': instance.isSuccess,
      'message': instance.message,
      'details': instance.details,
      'timestamp': instance.timestamp.toIso8601String(),
    };

ConfigurationBundle _$ConfigurationBundleFromJson(Map<String, dynamic> json) =>
    ConfigurationBundle(
      general:
          GeneralSettings.fromJson(json['general'] as Map<String, dynamic>),
      detection:
          DetectionSettings.fromJson(json['detection'] as Map<String, dynamic>),
      camera: CameraSettings.fromJson(json['camera'] as Map<String, dynamic>),
      automation: AutomationSettings.fromJson(
          json['automation'] as Map<String, dynamic>),
      version: json['version'] as String,
      exportDate: DateTime.parse(json['exportDate'] as String),
      metadata: json['metadata'] as Map<String, dynamic>?,
    );

Map<String, dynamic> _$ConfigurationBundleToJson(
        ConfigurationBundle instance) =>
    <String, dynamic>{
      'general': instance.general,
      'detection': instance.detection,
      'camera': instance.camera,
      'automation': instance.automation,
      'version': instance.version,
      'exportDate': instance.exportDate.toIso8601String(),
      'metadata': instance.metadata,
    };

WorkflowSettings _$WorkflowSettingsFromJson(Map<String, dynamic> json) =>
    WorkflowSettings(
      velocitySensitivity: (json['velocitySensitivity'] as num).toDouble(),
      minValue: (json['minValue'] as num).toDouble(),
      maxValue: (json['maxValue'] as num).toDouble(),
      description: json['description'] as String,
      recommendation: json['recommendation'] as String?,
    );

Map<String, dynamic> _$WorkflowSettingsToJson(WorkflowSettings instance) =>
    <String, dynamic>{
      'velocitySensitivity': instance.velocitySensitivity,
      'minValue': instance.minValue,
      'maxValue': instance.maxValue,
      'description': instance.description,
      'recommendation': instance.recommendation,
    };
