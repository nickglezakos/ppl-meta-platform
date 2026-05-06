// GENERATED CODE - DO NOT MODIFY BY HAND
// Manual implementation (build_runner has pre-existing errors)

part of 'settings_models.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

GeneralSettings _$GeneralSettingsFromJson(Map<String, dynamic> json) =>
    GeneralSettings(
      darkTheme: json['darkTheme'] as bool? ?? false,
      autoRefresh: json['autoRefresh'] as bool? ?? true,
      refreshInterval:
          (json['refreshInterval'] as num?)?.toInt() ?? 30,
      enableNotifications:
          json['enableNotifications'] as bool? ?? true,
      maxLogEntries:
          (json['maxLogEntries'] as num?)?.toInt() ?? 1000,
      debugMode: json['debugMode'] as bool? ?? false,
      performanceMonitoring:
          json['performanceMonitoring'] as bool? ?? true,
      mergeIndividualsRule:
          json['mergeIndividualsRule'] as String? ?? 'semi',
      mergeIndividualsThreshold:
          (json['mergeIndividualsThreshold'] as num?)?.toDouble() ??
              0.70,
      mvrStoredComparison:
          json['mvrStoredComparison'] as bool? ?? false,
    );

Map<String, dynamic> _$GeneralSettingsToJson(
        GeneralSettings instance) =>
    <String, dynamic>{
      'darkTheme': instance.darkTheme,
      'autoRefresh': instance.autoRefresh,
      'refreshInterval': instance.refreshInterval,
      'enableNotifications': instance.enableNotifications,
      'maxLogEntries': instance.maxLogEntries,
      'debugMode': instance.debugMode,
      'performanceMonitoring': instance.performanceMonitoring,
      'mergeIndividualsRule': instance.mergeIndividualsRule,
      'mergeIndividualsThreshold':
          instance.mergeIndividualsThreshold,
    'mvrStoredComparison': instance.mvrStoredComparison,
    };

DetectionSettings _$DetectionSettingsFromJson(
        Map<String, dynamic> json) =>
    DetectionSettings(
      defaultMethod:
          json['defaultMethod'] as String? ?? 'opencv',
      availableMethods: (json['availableMethods'] as List<dynamic>?)
              ?.map((e) => e as String)
              .toList() ??
          const [],
      confidenceThreshold:
          (json['confidenceThreshold'] as num?)?.toDouble() ?? 0.7,
      saveResults: json['saveResults'] as bool? ?? true,
      realTimeProcessing:
          json['realTimeProcessing'] as bool? ?? true,
      batchSize: (json['batchSize'] as num?)?.toInt() ?? 10,
      maxConcurrentDetections:
          (json['maxConcurrentDetections'] as num?)?.toInt() ?? 4,
      customModelPath: json['customModelPath'] as String?,
      useGpuAcceleration:
          json['useGpuAcceleration'] as bool? ?? false,
    );

Map<String, dynamic> _$DetectionSettingsToJson(
        DetectionSettings instance) =>
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

CameraSettings _$CameraSettingsFromJson(
        Map<String, dynamic> json) =>
    CameraSettings(
      defaultResolution:
          json['defaultResolution'] as String? ?? '1920x1080',
      availableResolutions:
          (json['availableResolutions'] as List<dynamic>?)
                  ?.map((e) => e as String)
                  .toList() ??
              const [],
      defaultFrameRate:
          (json['defaultFrameRate'] as num?)?.toInt() ?? 30,
      availableFrameRates:
          (json['availableFrameRates'] as List<dynamic>?)
                  ?.map((e) => (e as num).toInt())
                  .toList() ??
              const [],
      defaultFormat:
          json['defaultFormat'] as String? ?? 'mp4',
      availableFormats:
          (json['availableFormats'] as List<dynamic>?)
                  ?.map((e) => e as String)
                  .toList() ??
              const [],
      autoRecord: json['autoRecord'] as bool? ?? false,
      maxRecordingDuration:
          (json['maxRecordingDuration'] as num?)?.toInt() ?? 60,
      recordingPath:
          json['recordingPath'] as String? ?? './recordings',
      connectionTimeout:
          (json['connectionTimeout'] as num?)?.toInt() ?? 30,
      retryAttempts:
          (json['retryAttempts'] as num?)?.toInt() ?? 3,
      autoReconnect: json['autoReconnect'] as bool? ?? true,
    );

Map<String, dynamic> _$CameraSettingsToJson(
        CameraSettings instance) =>
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

AutomationSettings _$AutomationSettingsFromJson(
        Map<String, dynamic> json) =>
    AutomationSettings(
      enableEngine: json['enableEngine'] as bool? ?? true,
      ruleCheckInterval:
          (json['ruleCheckInterval'] as num?)?.toInt() ?? 10,
      maxConcurrentExecutions:
          (json['maxConcurrentExecutions'] as num?)?.toInt() ?? 5,
      executionTimeout:
          (json['executionTimeout'] as num?)?.toInt() ?? 300,
      retryAttempts:
          (json['retryAttempts'] as num?)?.toInt() ?? 2,
      retryOnFailure:
          json['retryOnFailure'] as bool? ?? true,
      logExecutions: json['logExecutions'] as bool? ?? true,
      maxHistoryEntries:
          (json['maxHistoryEntries'] as num?)?.toInt() ?? 1000,
      enableNotifications:
          json['enableNotifications'] as bool? ?? true,
      autoFaceDetectionEnabled:
          json['autoFaceDetectionEnabled'] as bool? ?? false,
      notificationsEnabled:
          json['notificationsEnabled'] as bool? ?? true,
    );

Map<String, dynamic> _$AutomationSettingsToJson(
        AutomationSettings instance) =>
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
      'autoFaceDetectionEnabled':
          instance.autoFaceDetectionEnabled,
      'notificationsEnabled': instance.notificationsEnabled,
    };

ImportExportState _$ImportExportStateFromJson(
        Map<String, dynamic> json) =>
    ImportExportState(
      isProcessing: json['isProcessing'] as bool? ?? false,
      currentOperation: json['currentOperation'] as String?,
      lastResult: json['lastResult'] == null
          ? null
          : ImportExportResult.fromJson(
              json['lastResult'] as Map<String, dynamic>),
      autoBackup: json['autoBackup'] as bool? ?? false,
      backupLocation: json['backupLocation'] as String?,
    );

Map<String, dynamic> _$ImportExportStateToJson(
        ImportExportState instance) =>
    <String, dynamic>{
      'isProcessing': instance.isProcessing,
      'currentOperation': instance.currentOperation,
      'lastResult': instance.lastResult?.toJson(),
      'autoBackup': instance.autoBackup,
      'backupLocation': instance.backupLocation,
    };

ImportExportResult _$ImportExportResultFromJson(
        Map<String, dynamic> json) =>
    ImportExportResult(
      isSuccess: json['isSuccess'] as bool? ?? false,
      message: json['message'] as String? ?? '',
      details: json['details'] as String?,
      timestamp: json['timestamp'] == null
          ? DateTime.now()
          : DateTime.parse(json['timestamp'] as String),
    );

Map<String, dynamic> _$ImportExportResultToJson(
        ImportExportResult instance) =>
    <String, dynamic>{
      'isSuccess': instance.isSuccess,
      'message': instance.message,
      'details': instance.details,
      'timestamp': instance.timestamp.toIso8601String(),
    };

ConfigurationBundle _$ConfigurationBundleFromJson(
        Map<String, dynamic> json) =>
    ConfigurationBundle(
      general: GeneralSettings.fromJson(
          json['general'] as Map<String, dynamic>),
      detection: DetectionSettings.fromJson(
          json['detection'] as Map<String, dynamic>),
      camera: CameraSettings.fromJson(
          json['camera'] as Map<String, dynamic>),
      automation: AutomationSettings.fromJson(
          json['automation'] as Map<String, dynamic>),
      version: json['version'] as String? ?? '1.0.0',
      exportDate: json['exportDate'] == null
          ? DateTime.now()
          : DateTime.parse(json['exportDate'] as String),
      metadata: json['metadata'] as Map<String, dynamic>?,
    );

Map<String, dynamic> _$ConfigurationBundleToJson(
        ConfigurationBundle instance) =>
    <String, dynamic>{
      'general': instance.general.toJson(),
      'detection': instance.detection.toJson(),
      'camera': instance.camera.toJson(),
      'automation': instance.automation.toJson(),
      'version': instance.version,
      'exportDate': instance.exportDate.toIso8601String(),
      'metadata': instance.metadata,
    };

WorkflowSettings _$WorkflowSettingsFromJson(
        Map<String, dynamic> json) =>
    WorkflowSettings(
      velocitySensitivity:
          (json['velocitySensitivity'] as num?)?.toDouble() ?? 20.0,
      minValue: (json['minValue'] as num?)?.toDouble() ?? 5.0,
      maxValue: (json['maxValue'] as num?)?.toDouble() ?? 50.0,
      description: json['description'] as String? ?? '',
      recommendation: json['recommendation'] as String?,
    );

Map<String, dynamic> _$WorkflowSettingsToJson(
        WorkflowSettings instance) =>
    <String, dynamic>{
      'velocitySensitivity': instance.velocitySensitivity,
      'minValue': instance.minValue,
      'maxValue': instance.maxValue,
      'description': instance.description,
      'recommendation': instance.recommendation,
    };
