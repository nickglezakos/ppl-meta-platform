// API Models for Orchestrator API Client
import 'package:json_annotation/json_annotation.dart';

part 'api_models.g.dart';

// ====================
// Authentication Models
// ====================

@JsonSerializable()
class LoginRequest {
  final String username;
  final String password;

  LoginRequest({
    required this.username,
    required this.password,
  });

  factory LoginRequest.fromJson(Map<String, dynamic> json) =>
      _$LoginRequestFromJson(json);

  Map<String, dynamic> toJson() => _$LoginRequestToJson(this);
}

@JsonSerializable()
class AuthResponse {
  final String token;
  final String tokenType;
  final int expiresIn;
  final UserProfile user;

  AuthResponse({
    required this.token,
    required this.tokenType,
    required this.expiresIn,
    required this.user,
  });

  factory AuthResponse.fromJson(Map<String, dynamic> json) =>
      _$AuthResponseFromJson(json);

  Map<String, dynamic> toJson() => _$AuthResponseToJson(this);
}

@JsonSerializable()
class UserProfile {
  final String id;
  final String username;
  final String email;
  final List<String> roles;

  UserProfile({
    required this.id,
    required this.username,
    required this.email,
    required this.roles,
  });

  factory UserProfile.fromJson(Map<String, dynamic> json) =>
      _$UserProfileFromJson(json);

  Map<String, dynamic> toJson() => _$UserProfileToJson(this);
}

// ====================
// Camera Models
// ====================

@JsonSerializable()
class CameraDevice {
  final String id;
  final String name;
  final String type;
  final String status;
  final String? ipAddress;
  final String? streamUrl;
  final CameraSettings settings;
  final DateTime lastSeen;
  final Map<String, dynamic>? metadata;

  CameraDevice({
    required this.id,
    required this.name,
    required this.type,
    required this.status,
    this.ipAddress,
    this.streamUrl,
    required this.settings,
    required this.lastSeen,
    this.metadata,
  });

  factory CameraDevice.fromJson(Map<String, dynamic> json) =>
      _$CameraDeviceFromJson(json);

  Map<String, dynamic> toJson() => _$CameraDeviceToJson(this);

  bool get isOnline => status == 'online' || status == 'streaming';
  bool get isRecording => status == 'recording';
}

@JsonSerializable()
class CameraSettings {
  final String resolution;
  final int frameRate;
  final String format;
  final int quality;
  final bool autoExposure;
  final int? exposure;
  final bool autoWhiteBalance;
  final String? whiteBalance;

  CameraSettings({
    required this.resolution,
    required this.frameRate,
    required this.format,
    required this.quality,
    required this.autoExposure,
    this.exposure,
    required this.autoWhiteBalance,
    this.whiteBalance,
  });

  factory CameraSettings.fromJson(Map<String, dynamic> json) =>
      _$CameraSettingsFromJson(json);

  Map<String, dynamic> toJson() => _$CameraSettingsToJson(this);
}

@JsonSerializable()
class CameraUpdateRequest {
  final String? name;
  final CameraSettings? settings;
  final Map<String, dynamic>? metadata;

  CameraUpdateRequest({
    this.name,
    this.settings,
    this.metadata,
  });

  factory CameraUpdateRequest.fromJson(Map<String, dynamic> json) =>
      _$CameraUpdateRequestFromJson(json);

  Map<String, dynamic> toJson() => _$CameraUpdateRequestToJson(this);
}

// ====================
// Recording Models
// ====================

@JsonSerializable()
class RecordingRequest {
  final String? filename;
  final int? duration;
  final String? format;
  final Map<String, dynamic>? settings;

  RecordingRequest({
    this.filename,
    this.duration,
    this.format,
    this.settings,
  });

  factory RecordingRequest.fromJson(Map<String, dynamic> json) =>
      _$RecordingRequestFromJson(json);

  Map<String, dynamic> toJson() => _$RecordingRequestToJson(this);
}

@JsonSerializable()
class RecordingSession {
  final String id;
  final String cameraId;
  final String filename;
  final String status;
  final DateTime startTime;
  final DateTime? endTime;
  final int? duration;
  final int? fileSize;
  final String? format;

  RecordingSession({
    required this.id,
    required this.cameraId,
    required this.filename,
    required this.status,
    required this.startTime,
    this.endTime,
    this.duration,
    this.fileSize,
    this.format,
  });

  factory RecordingSession.fromJson(Map<String, dynamic> json) =>
      _$RecordingSessionFromJson(json);

  Map<String, dynamic> toJson() => _$RecordingSessionToJson(this);

  bool get isActive => status == 'recording' || status == 'starting';
  String get durationText {
    if (duration != null) {
      final minutes = duration! ~/ 60;
      final seconds = duration! % 60;
      return '${minutes}:${seconds.toString().padLeft(2, '0')}';
    }
    return 'N/A';
  }
}

// ====================
// Face Detection Models
// ====================

@JsonSerializable()
class FaceDetectionRequest {
  final String? method;
  final double? confidenceThreshold;
  final bool? saveResult;
  final Map<String, dynamic>? options;

  FaceDetectionRequest({
    this.method,
    this.confidenceThreshold,
    this.saveResult,
    this.options,
  });

  factory FaceDetectionRequest.fromJson(Map<String, dynamic> json) =>
      _$FaceDetectionRequestFromJson(json);

  Map<String, dynamic> toJson() => _$FaceDetectionRequestToJson(this);
}

@JsonSerializable()
class FaceDetectionResult {
  final String id;
  final String cameraId;
  final DateTime timestamp;
  final List<DetectedFace> faces;
  final String? imageUrl;
  final Map<String, dynamic>? metadata;

  FaceDetectionResult({
    required this.id,
    required this.cameraId,
    required this.timestamp,
    required this.faces,
    this.imageUrl,
    this.metadata,
  });

  factory FaceDetectionResult.fromJson(Map<String, dynamic> json) =>
      _$FaceDetectionResultFromJson(json);

  Map<String, dynamic> toJson() => _$FaceDetectionResultToJson(this);
}

@JsonSerializable()
class DetectedFace {
  final FaceBox boundingBox;
  final double confidence;
  final Map<String, dynamic>? landmarks;
  final Map<String, dynamic>? attributes;

  DetectedFace({
    required this.boundingBox,
    required this.confidence,
    this.landmarks,
    this.attributes,
  });

  factory DetectedFace.fromJson(Map<String, dynamic> json) =>
      _$DetectedFaceFromJson(json);

  Map<String, dynamic> toJson() => _$DetectedFaceToJson(this);
}

@JsonSerializable()
class FaceBox {
  final double x;
  final double y;
  final double width;
  final double height;

  FaceBox({
    required this.x,
    required this.y,
    required this.width,
    required this.height,
  });

  factory FaceBox.fromJson(Map<String, dynamic> json) =>
      _$FaceBoxFromJson(json);

  Map<String, dynamic> toJson() => _$FaceBoxToJson(this);
}

// ====================
// Workflow Models
// ====================

@JsonSerializable()
class WorkflowTemplate {
  final String id;
  final String name;
  final String description;
  final List<WorkflowStep> steps;
  final Map<String, dynamic>? defaultParams;
  final DateTime createdAt;

  WorkflowTemplate({
    required this.id,
    required this.name,
    required this.description,
    required this.steps,
    this.defaultParams,
    required this.createdAt,
  });

  factory WorkflowTemplate.fromJson(Map<String, dynamic> json) =>
      _$WorkflowTemplateFromJson(json);

  Map<String, dynamic> toJson() => _$WorkflowTemplateToJson(this);
}

@JsonSerializable()
class WorkflowStep {
  final String id;
  final String type;
  final String name;
  final Map<String, dynamic> parameters;
  final List<String>? dependencies;

  WorkflowStep({
    required this.id,
    required this.type,
    required this.name,
    required this.parameters,
    this.dependencies,
  });

  factory WorkflowStep.fromJson(Map<String, dynamic> json) =>
      _$WorkflowStepFromJson(json);

  Map<String, dynamic> toJson() => _$WorkflowStepToJson(this);
}

@JsonSerializable()
class WorkflowCreateRequest {
  final String templateId;
  final String? name;
  final Map<String, dynamic>? parameters;
  final DateTime? scheduledTime;

  WorkflowCreateRequest({
    required this.templateId,
    this.name,
    this.parameters,
    this.scheduledTime,
  });

  factory WorkflowCreateRequest.fromJson(Map<String, dynamic> json) =>
      _$WorkflowCreateRequestFromJson(json);

  Map<String, dynamic> toJson() => _$WorkflowCreateRequestToJson(this);
}

@JsonSerializable()
class WorkflowExecution {
  final String id;
  final String templateId;
  final String name;
  final WorkflowStatus status;
  final DateTime createdAt;
  final DateTime? startedAt;
  final DateTime? completedAt;
  final List<StepExecution> steps;
  final Map<String, dynamic>? result;
  final String? error;

  WorkflowExecution({
    required this.id,
    required this.templateId,
    required this.name,
    required this.status,
    required this.createdAt,
    this.startedAt,
    this.completedAt,
    required this.steps,
    this.result,
    this.error,
  });

  factory WorkflowExecution.fromJson(Map<String, dynamic> json) =>
      _$WorkflowExecutionFromJson(json);

  Map<String, dynamic> toJson() => _$WorkflowExecutionToJson(this);

  double get progress {
    if (steps.isEmpty) return 0.0;
    final completedSteps = steps.where((s) => s.status == StepStatus.completed).length;
    return completedSteps / steps.length;
  }

  Duration? get duration {
    if (startedAt != null && completedAt != null) {
      return completedAt!.difference(startedAt!);
    }
    return null;
  }
}

@JsonSerializable()
class StepExecution {
  final String id;
  final String stepId;
  final String name;
  final StepStatus status;
  final DateTime? startedAt;
  final DateTime? completedAt;
  final Map<String, dynamic>? result;
  final String? error;

  StepExecution({
    required this.id,
    required this.stepId,
    required this.name,
    required this.status,
    this.startedAt,
    this.completedAt,
    this.result,
    this.error,
  });

  factory StepExecution.fromJson(Map<String, dynamic> json) =>
      _$StepExecutionFromJson(json);

  Map<String, dynamic> toJson() => _$StepExecutionToJson(this);
}

enum WorkflowStatus {
  @JsonValue('pending')
  pending,
  @JsonValue('running')
  running,
  @JsonValue('completed')
  completed,
  @JsonValue('failed')
  failed,
  @JsonValue('cancelled')
  cancelled,
}

enum StepStatus {
  @JsonValue('pending')
  pending,
  @JsonValue('running')
  running,
  @JsonValue('completed')
  completed,
  @JsonValue('failed')
  failed,
  @JsonValue('skipped')
  skipped,
}

// ====================
// Automation Models
// ====================

@JsonSerializable()
class AutomationRule {
  final String id;
  final String name;
  final String description;
  final bool enabled;
  final RuleTrigger trigger;
  final List<RuleCondition> conditions;
  final List<RuleAction> actions;
  final DateTime createdAt;
  final DateTime? lastExecuted;
  final int executionCount;

  AutomationRule({
    required this.id,
    required this.name,
    required this.description,
    required this.enabled,
    required this.trigger,
    required this.conditions,
    required this.actions,
    required this.createdAt,
    this.lastExecuted,
    required this.executionCount,
  });

  factory AutomationRule.fromJson(Map<String, dynamic> json) =>
      _$AutomationRuleFromJson(json);

  Map<String, dynamic> toJson() => _$AutomationRuleToJson(this);
}

@JsonSerializable()
class RuleTrigger {
  final String type;
  final Map<String, dynamic> parameters;

  RuleTrigger({
    required this.type,
    required this.parameters,
  });

  factory RuleTrigger.fromJson(Map<String, dynamic> json) =>
      _$RuleTriggerFromJson(json);

  Map<String, dynamic> toJson() => _$RuleTriggerToJson(this);
}

@JsonSerializable()
class RuleCondition {
  final String type;
  final String operator;
  final dynamic value;
  final Map<String, dynamic>? parameters;

  RuleCondition({
    required this.type,
    required this.operator,
    required this.value,
    this.parameters,
  });

  factory RuleCondition.fromJson(Map<String, dynamic> json) =>
      _$RuleConditionFromJson(json);

  Map<String, dynamic> toJson() => _$RuleConditionToJson(this);
}

@JsonSerializable()
class RuleAction {
  final String type;
  final Map<String, dynamic> parameters;

  RuleAction({
    required this.type,
    required this.parameters,
  });

  factory RuleAction.fromJson(Map<String, dynamic> json) =>
      _$RuleActionFromJson(json);

  Map<String, dynamic> toJson() => _$RuleActionToJson(this);
}

@JsonSerializable()
class AutomationRuleCreateRequest {
  final String name;
  final String description;
  final bool enabled;
  final RuleTrigger trigger;
  final List<RuleCondition> conditions;
  final List<RuleAction> actions;

  AutomationRuleCreateRequest({
    required this.name,
    required this.description,
    required this.enabled,
    required this.trigger,
    required this.conditions,
    required this.actions,
  });

  factory AutomationRuleCreateRequest.fromJson(Map<String, dynamic> json) =>
      _$AutomationRuleCreateRequestFromJson(json);

  Map<String, dynamic> toJson() => _$AutomationRuleCreateRequestToJson(this);
}

@JsonSerializable()
class AutomationRuleUpdateRequest {
  final String? name;
  final String? description;
  final bool? enabled;
  final RuleTrigger? trigger;
  final List<RuleCondition>? conditions;
  final List<RuleAction>? actions;

  AutomationRuleUpdateRequest({
    this.name,
    this.description,
    this.enabled,
    this.trigger,
    this.conditions,
    this.actions,
  });

  factory AutomationRuleUpdateRequest.fromJson(Map<String, dynamic> json) =>
      _$AutomationRuleUpdateRequestFromJson(json);

  Map<String, dynamic> toJson() => _$AutomationRuleUpdateRequestToJson(this);
}

@JsonSerializable()
class AutomationExecution {
  final String id;
  final String ruleId;
  final String ruleName;
  final DateTime executedAt;
  final bool successful;
  final String? error;
  final Map<String, dynamic>? result;
  final Duration duration;

  AutomationExecution({
    required this.id,
    required this.ruleId,
    required this.ruleName,
    required this.executedAt,
    required this.successful,
    this.error,
    this.result,
    required this.duration,
  });

  factory AutomationExecution.fromJson(Map<String, dynamic> json) =>
      _$AutomationExecutionFromJson(json);

  Map<String, dynamic> toJson() => _$AutomationExecutionToJson(this);
}

// ====================
// Analytics Models
// ====================

@JsonSerializable()
class AnalyticsOverview {
  final int totalDetections;
  final int totalCameras;
  final int activeWorkflows;
  final int automationRules;
  final double avgConfidence;
  final DateTime periodStart;
  final DateTime periodEnd;

  AnalyticsOverview({
    required this.totalDetections,
    required this.totalCameras,
    required this.activeWorkflows,
    required this.automationRules,
    required this.avgConfidence,
    required this.periodStart,
    required this.periodEnd,
  });

  factory AnalyticsOverview.fromJson(Map<String, dynamic> json) =>
      _$AnalyticsOverviewFromJson(json);

  Map<String, dynamic> toJson() => _$AnalyticsOverviewToJson(this);
}

@JsonSerializable()
class DetectionTrend {
  final DateTime timestamp;
  final int detectionCount;
  final double avgConfidence;
  final String? cameraId;

  DetectionTrend({
    required this.timestamp,
    required this.detectionCount,
    required this.avgConfidence,
    this.cameraId,
  });

  factory DetectionTrend.fromJson(Map<String, dynamic> json) =>
      _$DetectionTrendFromJson(json);

  Map<String, dynamic> toJson() => _$DetectionTrendToJson(this);
}

@JsonSerializable()
class SystemMetrics {
  final double cpuUsage;
  final double memoryUsage;
  final double diskUsage;
  final int queueLength;
  final double avgProcessingTime;
  final DateTime timestamp;

  SystemMetrics({
    required this.cpuUsage,
    required this.memoryUsage,
    required this.diskUsage,
    required this.queueLength,
    required this.avgProcessingTime,
    required this.timestamp,
  });

  factory SystemMetrics.fromJson(Map<String, dynamic> json) =>
      _$SystemMetricsFromJson(json);

  Map<String, dynamic> toJson() => _$SystemMetricsToJson(this);
}

// ====================
// Health & Status Models
// ====================

@JsonSerializable()
class HealthStatus {
  final String status;
  final DateTime timestamp;
  final Map<String, ServiceHealth> services;

  HealthStatus({
    required this.status,
    required this.timestamp,
    required this.services,
  });

  factory HealthStatus.fromJson(Map<String, dynamic> json) =>
      _$HealthStatusFromJson(json);

  Map<String, dynamic> toJson() => _$HealthStatusToJson(this);

  bool get isHealthy => status == 'healthy';
}

@JsonSerializable()
class ServiceHealth {
  final String status;
  final String? message;
  final DateTime? lastCheck;

  ServiceHealth({
    required this.status,
    this.message,
    this.lastCheck,
  });

  factory ServiceHealth.fromJson(Map<String, dynamic> json) =>
      _$ServiceHealthFromJson(json);

  Map<String, dynamic> toJson() => _$ServiceHealthToJson(this);

  bool get isHealthy => status == 'healthy';
}